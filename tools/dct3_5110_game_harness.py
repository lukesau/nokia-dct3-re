#!/usr/bin/env python3
"""Run a 5110 (NSE-1 v5.28) built-in game's own code in Unicorn.

The game handlers, the LCD fill/blit routines and the C runtime helpers run
natively from the flash (roms/noki5110/5110f528a.fls, big-endian Thumb at
0x200000). Firmware services below them are replaced in Python: the RTOS
heap, the scheduler's delayed events (the game tick), tones, the task-5
status posts (game over) and the UI refresh. A basic-block hook stops at any
code outside NATIVE that has no stub, so the boundary stays explicit.

The harness drives a game the way the games framework does (0x2793e0..):
New game calls the handler with 0x49 init then 0x53 resume; the game posts
scheduler event 0x2a with a delay, which the framework turns into 0x54 tick;
keys arrive as ASCII; 0x57 draws (dispatcher at 0x258f3e).
"""

import argparse
import os
import struct
import sys
import zlib

from unicorn import (UC_ARCH_ARM, UC_HOOK_BLOCK, UC_HOOK_MEM_FETCH_UNMAPPED,
                     UC_HOOK_MEM_READ_UNMAPPED, UC_HOOK_MEM_WRITE_UNMAPPED,
                     UC_MODE_BIG_ENDIAN, UC_MODE_THUMB, Uc, UcError)
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

FLASH = 0x200000
RAM_SIZE = 0x200000            # MAD2 I/O at 0x20000, RAM at 0x100000
TRACE_PORT = 0x600000          # the allocator writes trace bytes here
HEAP = (0x180000, 0x1f0000)
STACK_TOP = 0x17f000
INIT_CHAIN = (0x293fe0, 0x29475c)  # [u32 len][u32 dest][len bytes], 4-aligned
EV_GAME_TIMER = 0x2a           # scheduler event the games post; framework sends tick
TRAP = 0x1ff000                # return address that ends a call

GAME_TABLE = 0x2a79cc          # 12-byte {handler, list, params}
GAME_INDEX = 0x10fd5a          # u8
GAME_COUNT = 3
GAME_RECORDS = 0x10a62c        # 8 bytes per game: +0 score, +2 top, +4 level,
                               # +5 menu state, +6 in play
FB = 0x107610                  # 84x48, 6 pages of 84 bytes, bit y & 7
W, H = 84, 48
TICK_MS = 255 / 32.768         # one scheduler tick (games_applications.md)
GAMES = {0: "memory", 1: "snake", 2: "logic"}

EV_INIT, EV_RESUME, EV_TICK, EV_DRAW = 0x49, 0x53, 0x54, 0x57

ARGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)

# Code run natively. Anything else that executes must be a stub.
NATIVE = [
    (0x2576fc, 0x25a400, "games"),
    (0x252cac, 0x253400, "LCD fill rect, blit, put pixel"),
    (0x2921fc, 0x294000, "C runtime: divmod, float, memcpy, rand"),
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
        mu.mem_map(TRACE_PORT, 0x1000)
        self._init_ram()
        self.heap_next = HEAP[0]
        self.stubs = {}
        self.log = []
        self.stopped = None
        self.now = 0.0             # ms
        self.pending = None        # (event, due ms) posted by the game
        self.sounds = []
        self.statuses = []
        self.frames = []
        mu.hook_add(UC_HOOK_BLOCK, self._block)
        mu.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED
                    | UC_HOOK_MEM_FETCH_UNMAPPED, self._unmapped)
        self._install_stubs()

    # --- memory helpers -------------------------------------------------
    def _init_ram(self):
        p, end = INIT_CHAIN
        while p < end:
            o = p - FLASH
            n, dest = struct.unpack(">II", self.img[o:o + 8])
            self.mu.mem_write(dest, self.img[o + 8:o + 8 + n])
            p += 8 + ((n + 3) & ~3)

    def r32(self, a):
        return struct.unpack(">I", self.mu.mem_read(a, 4))[0]

    def w32(self, a, v):
        self.mu.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))

    def r8(self, a):
        return self.mu.mem_read(a, 1)[0]

    def w8(self, a, v):
        self.mu.mem_write(a, bytes([v & 0xFF]))

    def reg(self, r):
        return self.mu.reg_read(r)

    def arg(self, n):
        if n < 4:
            return self.reg(ARGS[n])
        return self.r32(self.reg(UC_ARM_REG_SP) + 4 * (n - 4))

    # --- calls ----------------------------------------------------------
    def call(self, fn, *args, limit=20_000_000):
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
            if self.stopped is None:
                self.stopped = f"{e} at pc={self.reg(UC_ARM_REG_PC):#x}"
        if self.stopped:
            raise Stop(self.stopped)
        return self.reg(UC_ARM_REG_R0)

    def _return(self, value=None):
        if value is not None:
            self.mu.reg_write(UC_ARM_REG_R0, value & 0xFFFFFFFF)
        self.mu.reg_write(UC_ARM_REG_PC, self.reg(UC_ARM_REG_LR))

    def _block(self, mu, addr, size, _):
        addr &= ~1
        if addr == TRAP:
            return
        stub = self.stubs.get(addr)
        if stub:
            name, fn = stub
            args = [self.arg(i) for i in range(4)]
            value = fn()
            if self.verbose:
                print(f"  {name}({', '.join(hex(a) for a in args)}) -> {value}")
            self._return(value)
            return
        for lo, hi, _ in NATIVE:
            if lo <= addr < hi:
                return
        lr = self.reg(UC_ARM_REG_LR)
        self.stopped = (f"unstubbed code at {addr:#x} (lr {lr:#x}), args "
                        + ", ".join(hex(self.arg(i)) for i in range(4)))
        mu.emu_stop()

    def _unmapped(self, mu, access, addr, size, value, _):
        self.stopped = (f"unmapped access {addr:#x} at "
                        f"pc={self.reg(UC_ARM_REG_PC):#x}")
        return False

    # --- stubs ----------------------------------------------------------
    def _install_stubs(self):
        def stub(addr, name):
            def deco(fn):
                self.stubs[addr] = (name, fn)
                return fn
            return deco

        @stub(0x2559e0, "rtos_mem_alloc")
        def _alloc():
            size = self.arg(0)
            p = self.heap_next
            self.heap_next = (p + size + 8 + 7) & ~7
            if self.heap_next > HEAP[1]:
                raise Stop("heap exhausted")
            self.mu.mem_write(p, bytes(size))
            return p

        @stub(0x2555b8, "rtos_mem_free")
        def _free():
            return 0

        @stub(0x25416a, "sched_post_event_delay")
        def _post_delay():
            event, delay = self.arg(0), self.arg(1)
            self.pending = (event, self.now + delay * TICK_MS)
            self.log.append(f"{self.now:9.1f} post event {event:#x} in {delay} ticks")
            return 0

        @stub(0x234c24, "games_ui_refresh")
        def _refresh():
            return 0

        @stub(0x28d9ae, "task5_status_post")
        def _status():
            self.log.append(f"{self.now:9.1f} status {self.arg(0):#x} {self.arg(1):#x}")
            self.statuses.append((self.now, self.arg(0), self.arg(1)))
            return 0

        @stub(0x290108, "display_type2_post")
        def _tone():
            self.sounds.append((self.now, self.arg(1), self.arg(2)))
            return 0

    # --- driving --------------------------------------------------------
    def handler(self, index):
        return self.r32(GAME_TABLE + 12 * index)

    def event(self, index, code):
        self.w8(GAME_INDEX, index)
        return self.call(self.handler(index), code)

    def set_level(self, index, level):
        self.w8(GAME_RECORDS + 8 * index + 4, level)

    def framebuffer(self):
        data = self.mu.mem_read(FB, W * H // 8)
        return [[(data[(y >> 3) * W + x] >> (y & 7)) & 1 for x in range(W)]
                for y in range(H)]

    def snap(self):
        self.frames.append((self.now, self.framebuffer()))

    def run(self, index, ms, keys):
        """Init, then tick on the game's own posted delays for ms, pressing
        keys = [(ms, key char)] in order. Draws after every event."""
        self.w8(GAME_INDEX, index)
        # Games menu "New game" (0x2790fc): +6 = 1 (in play), +5 = 0 (new).
        self.w8(GAME_RECORDS + 8 * index + 6, 1)
        self.w8(GAME_RECORDS + 8 * index + 5, 0)
        self.event(index, EV_INIT)
        self.event(index, EV_RESUME)
        self.event(index, EV_DRAW)
        self.snap()
        keys = sorted(keys)
        while self.now < ms:
            due = self.pending[1] if self.pending else ms
            if keys and keys[0][0] <= due:
                t, k = keys.pop(0)
                self.now = max(self.now, t)
                self.event(index, ord(k))
            elif self.pending:
                event = self.pending[0]
                self.now = due
                self.pending = None
                if event != EV_GAME_TIMER:
                    raise Stop(f"unexpected scheduler event {event:#x}")
                self.event(index, EV_TICK)
            else:
                self.now = ms
                break
            self.event(index, EV_DRAW)
            self.snap()


def write_png(path, rows):
    """8-bit greyscale PNG from equal-length rows of 0..255."""
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(r) for r in rows)

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def save_frames(frames, out, every=1, scale=3, cols=6):
    os.makedirs(out, exist_ok=True)
    for n, (_, fb) in enumerate(frames):
        write_png(os.path.join(out, f"frame_{n:04d}.png"),
                  [[0 if p else 255 for p in r for _ in range(scale)]
                   for r in fb for _ in range(scale)])
    keep = frames[::every]
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
    if rows:
        write_png(os.path.join(out, "sheet.png"), [r for r in rows for _ in range(2)])


def parse_keys(text):
    """'500:2 900:6' -> [(500, '2'), (900, '6')] (ms:key)."""
    out = []
    for item in text.split():
        t, k = item.split(":")
        out.append((float(t), k))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", default="roms/noki5110/5110f528a.fls")
    ap.add_argument("--game", default="snake", help="snake, memory, logic or 0..2")
    ap.add_argument("--level", type=int, default=0, help="level index 0..8")
    ap.add_argument("--ms", type=float, default=3000, help="emulated time")
    ap.add_argument("--keys", default="", help="key script, e.g. '500:2 900:6' (ms:key)")
    ap.add_argument("--out", help="directory for frame PNGs and a contact sheet")
    ap.add_argument("--every", type=int, default=1, help="keep every n-th frame on the sheet")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    names = {v: k for k, v in GAMES.items()}
    index = names[a.game] if a.game in names else int(a.game)
    h = Harness(a.image, a.verbose)
    h.set_level(index, a.level)
    print(f"{GAMES[index]}: handler {h.handler(index):#x}")
    status = 0
    try:
        h.run(index, a.ms, parse_keys(a.keys))
    except Stop as e:
        print("stopped:", e)
        status = 1
    print("\n".join(h.log[-12:]))
    print(f"{len(h.frames)} frames to {h.now:.0f} ms")
    for t, kind, tone in h.sounds:
        print(f"  {t:9.1f} ms: tone post {kind:#x} id {tone:#x}")
    if a.out:
        save_frames(h.frames, a.out, a.every)
    return status


if __name__ == "__main__":
    sys.exit(main())
