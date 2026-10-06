#!/usr/bin/env python3
"""Run a 3510 (DCT4) built-in game's own code in Unicorn.

The game, the shared game library and the engine's scene renderer all run
natively from the decrypted flash (roms/3510-nhm8-v502/flash.bin, big-endian
Thumb at 0x01000000). Only firmware services below them are replaced, in
Python: the heap, OS messages and timers, tones, saved data and whatever else
the run reaches. A basic-block hook stops at any function outside the code
known to be safe to run natively, so the stub boundary is explicit (see
NATIVE and the stubs in Harness).

The harness drives the game the way the engine does (docs/games_library_3510.md,
"Engine to game interface"): it calls the game's handler with a message, then
acts on the request word at 0x3d710 (bit 0 exit, bit 1 redraw, bit 2 new tick
period).
"""

import argparse
import struct
import sys

from unicorn import (UC_ARCH_ARM, UC_HOOK_BLOCK, UC_HOOK_MEM_FETCH_UNMAPPED,
                     UC_HOOK_MEM_READ_UNMAPPED, UC_HOOK_MEM_WRITE_UNMAPPED,
                     UC_MODE_BIG_ENDIAN, UC_MODE_THUMB, Uc, UcError)
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

FLASH = 0x01000000
RAM_SIZE = 0x00200000          # game data lives below 0x40000
HEAP = (0x00100000, 0x001e0000)
STACK_TOP = 0x000ff000
TRAP = 0x001f0000              # return address that ends a call
INIT_CHAIN = (0x01520734, 0x01537980)   # [u32 len][u32 dest][len bytes], 4-aligned

# Engine RAM (static: literal pools of 0x0142819c and 0x01428124).
ENGINE_STATE = 0x3d730   # u32
APP_TABLE = 0x3d704      # -> array of app records
APP_COUNT = 0x3d708      # u16
APP_CUR = 0x3d741        # u8
APP_MODE = 0x3d740       # u8
REQUESTS = 0x3d710       # u32: bit 0 exit, bit 1 redraw, bit 2 new period
PERIOD = 0x3d70c         # u32 ms
KEYS = 0x3d714           # u8[26]
FEATURES = 0x3d78c       # u8[]: [0] sound, [2] vibrator
TONE_SERVER = 0x3d5b8    # u32, non-zero once the tone server is up (0x0142bffc)

W, H = 96, 65

ENGINE_POOLS_INIT = 0x014254d2
ENGINE_SESSION_RESET = 0x01425584
ENGINE_APP_NEW = 0x01425b8e
ENGINE_LCD_BEGIN = 0x01428ac0
ENGINE_RENDER = 0x01428808
ENGINE_LCD_FLUSH = 0x01428ac8

ARGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)

# Code run natively: the games, the download engine and the game library, plus
# pure firmware helpers. Anything else that executes must be a stub.
NATIVE = [
    (0x013fc000, 0x0142edd4, "games, engine, game library"),
    (0x012fb028, 0x012fb1a0, "ARM runtime divides"),
    (0x0148af8e, 0x0148b4a0, "memcpy, memset"),
]


class Stop(Exception):
    pass


class Harness:
    def __init__(self, image, verbose=False):
        self.img = open(image, "rb").read()
        self.verbose = verbose
        mu = self.mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_BIG_ENDIAN)
        mu.mem_map(FLASH, (len(self.img) + 0xFFF) & ~0xFFF)
        mu.mem_write(FLASH, self.img)
        mu.mem_map(0, RAM_SIZE)
        self._init_ram()
        self.heap_next = HEAP[0]
        self.heap_sizes = {}
        self.stubs = {}
        self.log = []
        self.events = []
        self.stopped = None
        self.exited = False
        self.period = 100
        self.seed = 0
        self.oslog = []
        self.trace = []
        self.ticks = 0
        self.settings = {1: 1, 2: 2, 3: 1, 4: 0, 5: 0}
        self.records = {}
        self.sounds = []
        self.record_log = []
        self.frames = []
        self.draws = []
        self.fb = [[0] * W for _ in range(H)]
        mu.hook_add(UC_HOOK_BLOCK, self._block)
        mu.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED
                    | UC_HOOK_MEM_FETCH_UNMAPPED, self._unmapped)
        self._install_stubs()

    # --- memory helpers -------------------------------------------------
    def _init_ram(self):
        p, end = INIT_CHAIN
        while p < end:
            n, dest = struct.unpack(">II", self.img[p - FLASH:p - FLASH + 8])
            self.mu.mem_write(dest, self.img[p - FLASH + 8:p - FLASH + 8 + n])
            p += 8 + ((n + 3) & ~3)

    def r32(self, a):
        return struct.unpack(">I", self.mu.mem_read(a, 4))[0]

    def w32(self, a, v):
        self.mu.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))

    def r16(self, a):
        return struct.unpack(">H", self.mu.mem_read(a, 2))[0]

    def r8(self, a):
        return self.mu.mem_read(a, 1)[0]

    def w8(self, a, v):
        self.mu.mem_write(a, bytes([v & 0xFF]))

    def reg(self, r):
        return self.mu.reg_read(r)

    def arg(self, n):
        """Argument n (0-based) of the stubbed call: r0..r3, then the stack."""
        if n < 4:
            return self.reg(ARGS[n])
        return self.r32(self.reg(UC_ARM_REG_SP) + 4 * (n - 4))

    # --- calls ----------------------------------------------------------
    def call(self, fn, *args, limit=50_000_000):
        mu = self.mu
        sp = STACK_TOP
        extra = list(args[4:])
        sp -= 4 * len(extra)
        for i, v in enumerate(extra):
            self.w32(sp + 4 * i, v)
        mu.reg_write(UC_ARM_REG_SP, sp)
        for r, v in zip(ARGS, args[:4]):
            mu.reg_write(r, v & 0xFFFFFFFF)
        mu.reg_write(UC_ARM_REG_LR, TRAP | 1)
        try:
            mu.emu_start(fn | 1, TRAP, count=limit)
        except UcError as e:
            raise Stop(f"{e} at pc={self.reg(UC_ARM_REG_PC):#x} lr={self.reg(UC_ARM_REG_LR):#x}")
        pc = self.reg(UC_ARM_REG_PC)
        if pc != TRAP:
            raise Stop(f"call {fn:#x} did not return (pc={pc:#x}, instruction limit?)")
        return self.reg(UC_ARM_REG_R0)

    def _ret(self, value=0):
        mu = self.mu
        if value is not None:
            mu.reg_write(UC_ARM_REG_R0, value & 0xFFFFFFFF)
        mu.reg_write(UC_ARM_REG_PC, self.reg(UC_ARM_REG_LR))

    def _block(self, mu, addr, size, _):
        self.trace.append(addr)
        if len(self.trace) > 64:
            del self.trace[0]
        if addr == TRAP:
            return
        stub = self.stubs.get(addr)
        if stub is not None:
            name, fn = stub
            value = fn()
            if self.verbose:
                self.log.append(f"{name}{self._argstr()} -> {value}")
            self._ret(value)
            return
        for lo, hi, _ in NATIVE:
            if lo <= addr < hi:
                return
        mu.emu_stop()
        self.stopped = (f"unclassified code at {addr:#x} (lr={self.reg(UC_ARM_REG_LR):#x}, "
                        f"args {self._argstr()})")

    def _argstr(self):
        return "(" + ", ".join(f"{self.arg(i):#x}" for i in range(4)) + ")"

    def _unmapped(self, mu, access, addr, size, value, _):
        self.stopped = f"unmapped access {access} at {addr:#x} (pc={self.reg(UC_ARM_REG_PC):#x})"
        return False

    # --- stubs ------------------------------------------------------------
    def stub(self, addr, name):
        def deco(fn):
            self.stubs[addr] = (name, fn)
            return fn
        return deco

    def malloc(self, n):
        a = (self.heap_next + 7) & ~7
        if a + n > HEAP[1]:
            raise Stop("heap exhausted")
        self.heap_next = a + n
        self.heap_sizes[a] = n
        self.mu.mem_write(a, b"\xa5" * n)  # poison: the firmware heap does not clear
        return a

    def _install_stubs(self):
        h = self
        self._install_draw_stubs()
        self._install_record_stubs()

        @h.stub(0x012ef746, "fw_alloc")
        def _():
            return h.malloc(h.arg(0))

        @h.stub(0x012efa34, "fw_free")
        def _():
            h.heap_sizes.pop(h.arg(0), None)
            return 0

        for addr, name in ((0x012c79ca, "os_send"), (0x012c399a, "os_send_server")):
            def logged(name=name):
                h.oslog.append((name, h.arg(0), h.arg(1), h.arg(2), h.arg(3)))
                return 0
            h.stubs[addr] = (name, logged)

        # Tones (srvtone_toneobject_nrt.c): logged with the tick they happen on.
        for addr, name in ((0x0127257c, "tone_play"), (0x01272632, "tone_stop"),
                           (0x01272678, "tone_play_data")):
            def tone(name=name):
                # tone_play's argument (0x0142bffc): +2 u16 PPM tone index,
                # +5 u8 repeat (0xff = loop, 1 = once)
                req = h.arg(0)
                tone_index = h.r16(req + 2) if name == "tone_play" else None
                repeat = h.r8(req + 5) if name == "tone_play" else None
                h.sounds.append((h.ticks, name, tone_index, repeat))
                return 1
            h.stubs[addr] = (name, tone)

        @h.stub(0x012fae6e, "fw_time")  # game_srand's seed source
        def _():
            return h.seed

    # --- drawing ----------------------------------------------------------
    # The engine's renderer (0x01428808) walks the scene tree natively and
    # calls three draw wrappers with absolute positions and a clip rectangle.
    # They are replaced here; the firmware GDI below them needs a screen canvas
    # that the display driver sets up at boot, which this harness does not run.
    #
    # Pixel rules (I, not traced to the LCD): 1 = black. Flags & 0xf000 0x1000
    # draws, 0x2000 draws inverted, anything else nothing; flag bit 2 XORs.
    # Sprites: a second plane is a mask (1 = opaque); without one, flag bit 0
    # draws only the black pixels. Lines and rects draw in colour a & 1.

    def _pt(self, addr):
        x, y = struct.unpack(">hh", self.mu.mem_read(addr, 4))
        return x, y

    def _clip(self, addr):
        x0, y0, x1, y1 = struct.unpack(">hhhh", self.mu.mem_read(addr, 8))
        return max(x0, 0), max(y0, 0), min(x1, W - 1), min(y1, H - 1)

    def _plot(self, x, y, v, flags, clip, surface=None):
        surface = self.fb if surface is None else surface
        x0, y0, x1, y1 = clip
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return
        kind = flags & 0xF000
        if kind not in (0x1000, 0x2000):
            return
        if flags & 4:
            if v:
                surface[y][x] ^= 1
            return
        surface[y][x] = v ^ (kind == 0x2000)

    def _install_draw_stubs(self):
        h = self

        @h.stub(0x0142a26c, "draw_bitmap")
        def _():
            # (dst, src, pos*, a4, plane, a6, flags<<16|..., size*). dst and src are
            # {s16 x0, y0, x1, y1, w, h, u32 depth, u32 data}; dst 0 is the screen,
            # and then src's x0..y1 is the clip rectangle. With flags 0x2000 the
            # engine asks the GDI for mode 8 when a4 == 1 (taken here as a plain
            # copy; it is how the library writes mask planes) and mode 2 otherwise.
            dst, info = h.arg(0), h.arg(1)
            w, hh = struct.unpack(">hh", h.mu.mem_read(info + 8, 4))
            depth, data = struct.unpack(">II", h.mu.mem_read(info + 12, 8))
            px, py = h._pt(h.arg(2))
            a4, plane = h.arg(3), h.arg(4)
            flags = h.arg(6) >> 16
            if flags & 0x2000 and a4 == 1:
                flags = (flags & ~0xF000) | 0x1000
            if dst:
                dw, dh = struct.unpack(">hh", h.mu.mem_read(dst + 8, 4))
                ddata = struct.unpack(">I", h.mu.mem_read(dst + 16, 4))[0]
                target = (ddata, dw, dh)
                clip = (0, 0, dw - 1, dh - 1)
            else:
                target = None
                clip = h._clip(info)
                h.draws.append(("bitmap", px, py, w, hh, data, plane, flags))
            if depth != 1 or not data:
                return 0
            bands = (hh + 7) // 8
            pix = h.mu.mem_read(data, bands * w)
            mask = h.mu.mem_read(plane, bands * w) if plane else None
            if target:
                tdata, tw, th = target
                buf = bytearray(h.mu.mem_read(tdata, ((th + 7) // 8) * tw))
                surface = [[buf[(y // 8) * tw + x] >> (y % 8) & 1 for x in range(tw)] for y in range(th)]
            else:
                surface = h.fb
            for y in range(hh):
                for x in range(w):
                    o = (y // 8) * w + x
                    b = pix[o] >> (y % 8) & 1
                    if mask is not None:
                        if not mask[o] >> (y % 8) & 1:
                            continue
                    elif flags & 1 and not b:
                        continue
                    h._plot(px + x, py + y, b, flags, clip, surface)
            if target:
                for y in range(th):
                    for x in range(tw):
                        o = (y // 8) * tw + x
                        bit = 1 << (y % 8)
                        buf[o] = (buf[o] | bit) if surface[y][x] else (buf[o] & ~bit)
                h.mu.mem_write(tdata, bytes(buf))
            return 0

        @h.stub(0x0142a438, "draw_line")
        def _():
            # (0, clip, offset*, p1*, p2*, colour, {a7,a6}|0, flags<<16|style)
            ox, oy = h._pt(h.arg(2))
            x1, y1 = h._pt(h.arg(3))
            x2, y2 = h._pt(h.arg(4))
            colour = h.arg(5) & 1
            flags = h.arg(7) >> 16
            clip = h._clip(h.arg(1))
            x1, y1, x2, y2 = x1 + ox, y1 + oy, x2 + ox, y2 + oy
            h.draws.append(("line", x1, y1, x2, y2, colour, flags))
            n = max(abs(x2 - x1), abs(y2 - y1))
            for i in range(n + 1):
                x = x1 + ((x2 - x1) * i // n if n else 0)
                y = y1 + ((y2 - y1) * i // n if n else 0)
                h._plot(x, y, colour, flags, clip)
            return 0

        @h.stub(0x0142a5b4, "draw_rect")
        def _():
            # (0, clip, offset*, pos*, size*, colour, {a8,a7}|0, flags<<16|style)
            ox, oy = h._pt(h.arg(2))
            x, y = h._pt(h.arg(3))
            w, hh = h._pt(h.arg(4))
            colour = h.arg(5) & 1
            flags = h.arg(7) >> 16
            clip = h._clip(h.arg(1))
            x += ox
            y += oy
            h.draws.append(("rect", x, y, w, hh, colour, flags, h.arg(7) & 0xFFFF))
            for yy in range(y, y + hh):
                for xx in range(x, x + w):
                    h._plot(xx, yy, colour, flags, clip)
            return 0

    # --- settings and saved data ----------------------------------------------
    # The library's record calls end in the engine's record store and PMM
    # flash; they are replaced at the library entry points by an in-memory
    # store. Settings are what the engine's menus would have written.

    def _out_buffer(self, out, data):
        if not out:
            return 0
        if data is None:
            return 0
        a = self.malloc(max(len(data), 1))
        self.mu.mem_write(a, data)
        self.w32(out, a)
        return 1

    def _install_record_stubs(self):
        h = self

        @h.stub(0x0142dd84, "game_setting_get")       # (key, u32* out)
        def _():
            key, out = h.arg(0), h.arg(1)
            if key not in h.settings:
                return 0
            h.w32(out, h.settings[key])
            return 1

        @h.stub(0x0142ddac, "game_app_setting_get")   # (app, key, u32* out)
        def _():
            return 0

        @h.stub(0x0142ddd8, "game_setting_set")       # (app, key, value, item, mode)
        def _():
            h.settings[h.arg(1)] = h.arg(2)
            return 1

        def writer(kind):
            def fn():
                size, data = h.arg(0), h.arg(1)
                h.records[kind] = bytes(h.mu.mem_read(data, size)) if size else b""
                h.record_log.append((kind, len(h.records[kind])))
                return 1
            return fn

        def reader(kind):
            def fn():
                return h._out_buffer(h.arg(1), h.records.get(kind) or None)
            return fn

        for addr, name, kind in ((0x0142de30, "game_savegame_write", "save"),
                                 (0x0142de6c, "game_modedata_write", "mode"),
                                 (0x0142e260, "game_appdata_write", "app")):
            h.stubs[addr] = (name, writer(kind))
        for addr, name, kind in ((0x0142def2, "game_modedata_read", "mode"),
                                 (0x0142e28c, "game_appdata_read", "app")):
            h.stubs[addr] = (name, reader(kind))

        @h.stub(0x0142de5e, "game_savegame_clear")
        def _():
            h.records.pop("save", None)
            return 0

        @h.stub(0x0142ec7e, "game_gamedata_read")     # no downloaded data
        def _():
            return 0

        @h.stub(0x0142ebe4, "game_gamedata_store")
        def _():
            return 0

    # --- driving the game like the engine -----------------------------------
    def boot(self, handler):
        """Engine start-up for one app: object pools, an app record, then
        message 7 (registration) in engine state 2."""
        self.handler = handler
        self.call(ENGINE_POOLS_INIT)
        self.call(ENGINE_SESSION_RESET)
        self.call(ENGINE_APP_NEW)
        self.w8(FEATURES + 0, 1)   # sound on
        self.w8(FEATURES + 2, 1)   # vibrator on
        self.w32(TONE_SERVER, 1)   # tone server handle, set at boot on the phone
        self.w32(ENGINE_STATE, 2)
        self.w8(APP_CUR, 0)
        self.send(7)

    def send(self, msg, a1=0, a2=0):
        r = self.call(self.handler, msg, a1, a2)
        self.events.append(("msg", msg, a1, a2, r))
        req = self.r32(REQUESTS)
        if req & 1:
            self.exited = True
        if req & 2:
            self.fb = [[0] * W for _ in range(H)]
            self.draws = []
            self.call(ENGINE_LCD_BEGIN)
            self.call(ENGINE_RENDER)
            self.call(ENGINE_LCD_FLUSH)
            self.frames.append((len(self.events), [r[:] for r in self.fb]))
            req &= ~2
        if req & 4:
            self.period = self.r32(PERIOD)
            req &= ~4
        self.w32(REQUESTS, req & ~1)
        return r

    def key(self, k, down):
        """A key event as the engine sends it in play: key array first
        (down -> (s & 0xf8) | 6, up -> | 5), then msg 1 / 2 with the key."""
        s = self.r8(KEYS + k)
        self.w8(KEYS + k, (s & 0xF8) | (6 if down else 5))
        return self.send(1 if down else 2, k)

    def tick(self):
        """Timer expiry: msg 0, then every key's "changed" bit is cleared."""
        r = self.send(0)
        for k in range(26):
            self.w8(KEYS + k, self.r8(KEYS + k) & ~4)
        self.ticks += 1
        return r


KEY_NAMES = {"left": 0x13, "right": 0xf, "gas": 0x14, "brake": 0x15,
             "fire": 0x16, "turbo": 0x17}


def parse_script(text):
    """'10:gas+ 12:gas- 40:left+' -> {tick: [(key, down), ...]}."""
    out = {}
    for item in text.split():
        t, k = item.split(":")
        name, sign = k[:-1], k[-1]
        key = KEY_NAMES[name] if name in KEY_NAMES else int(name, 0)
        out.setdefault(int(t), []).append((key, sign == "+"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", default="roms/3510-nhm8-v502/flash.bin")
    ap.add_argument("--ticks", type=int, default=40)
    ap.add_argument("--keys", default="", help="key script, e.g. '10:gas+ 11:gas- 30:gas+' (names: "
                    + ", ".join(KEY_NAMES) + ", or a key id)")
    ap.add_argument("--mode", type=int, default=1, help="menu item (setting 3): 1 cup, 2 challenge")
    ap.add_argument("--level", type=int, default=2, help="setting 2 (difficulty)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", help="directory for frame PNGs and a contact sheet")
    ap.add_argument("--every", type=int, default=1, help="keep every n-th frame on the sheet")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    script = parse_script(a.keys)
    h = Harness(a.image, a.verbose)
    h.seed = a.seed
    h.settings[3] = a.mode
    h.settings[2] = a.level
    try:
        h.boot(0x014047f0)
        h.w32(ENGINE_STATE, 7)
        h.w8(APP_MODE, a.mode)
        h.send(0xa, a.mode)
        h.send(0x14)
        h.send(0xc)
        for t in range(a.ticks):
            for k, down in script.get(t, []):
                h.key(k, down)
            h.tick()
            if h.exited:
                print(f"game exited at tick {t}")
                break
    except Stop as e:
        print("stop:", e)
        print("last blocks:", " ".join(f"{x:x}" for x in h.trace[-24:]))
    if h.stopped:
        print("stop:", h.stopped)
    if a.verbose:
        print("\n".join(h.log[-40:]))
    print(f"{h.ticks} ticks, {len(h.frames)} frames, period {h.period} ms")
    for t, name, tone, repeat in h.sounds:
        what = f"PPM tone {tone:#x}, {'loop' if repeat == 0xff else 'once'}" if tone is not None else ""
        print(f"  tick {t}: {name} {what}")
    if a.out:
        save_frames(h, a.out, a.every)
    return 0


def save_frames(h, out, every):
    import os
    from dct4_bitmaps import write_png
    os.makedirs(out, exist_ok=True)
    for n, (_, fb) in enumerate(h.frames):
        write_png(os.path.join(out, f"frame_{n:04d}.png"),
                  [[0 if p else 255 for p in r for _ in range(3)] for r in fb for _ in range(3)])
    keep = h.frames[::every]
    if not keep:
        return
    cols = 6
    rows = []
    for i in range(0, len(keep), cols):
        band = keep[i:i + cols]
        for y in range(H):
            line = []
            for _, fb in band:
                line += [0 if p else 255 for p in fb[y]] + [128] * 2
            line += [128] * ((W + 2) * (cols - len(band)))
            rows.append([v for v in line for _ in range(2)])
        rows.append([128] * ((W + 2) * cols * 2))
    write_png(os.path.join(out, "sheet.png"), [r for r in rows for _ in range(2)])


if __name__ == "__main__":
    sys.exit(main())
