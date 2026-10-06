#!/usr/bin/env python3
"""Locate the 3510 v5.02 games statically, against the mapped 3410 v5.46 games.

The 3510 is DCT4 big-endian Thumb at 0x01000000 (roms/3510-nhm8-v502/flash.bin
from tools/dct4_decrypt.py); the 3410 image is MAME-order little-endian at
0x200000. The 3510 image is turned into little-endian half-words first so the
two can be compared window by window, with Thumb BL pairs masked in both.

Prints, for each 3410 game's code range, how many 12-byte windows occur in the
3510 and on which 4 KB pages; then the games handler table and, for each
handler, the background tune its game starts: the id passed to game_sound_loop
goes through the engine's tone-id table to a PPM tone record, whose name is
printed. Nothing is run.
"""

import argparse
import collections
import sys

BASE_3410 = 0x200000
BASE_3510 = 0x01000000
MCU_END_3510 = 0x01537984
WINDOW = 12

# Code ranges of the 3410's games (GAMES_INNER for GAMES_PRODUCT=3410).
GAMES_3410 = [
    ("Snake II", 0x24b000, 0x250000),
    ("Space Impact", 0x258000, 0x25d000),
    ("Bumper", 0x2d5000, 0x2d7000),
    ("Bantumi", 0x2e8000, 0x2ea000),
    ("Link5", 0x32a000, 0x32b000),
]
HANDLERS_3510 = 0x01511ebc  # five Thumb pointers
GAME_SOUND_LOOP = 0x0142df3a  # game_sound_loop(tone_id), once per game
TONE_IDS = 0x01511e88         # u16 PPM tone index per tone id, from id 4000
PPM = (0x015a0000, 0x016bd5b8)


def mask_bl(d):
    o = bytearray(d)
    for i in range(0, len(o) - 3, 2):
        if o[i + 1] & 0xF8 == 0xF0 and o[i + 3] & 0xF8 == 0xF8:
            o[i:i + 4] = b"\x00\xf0\x00\xf8"
    return bytes(o)


def swap16(d):
    o = bytearray(len(d) & ~1)
    o[0::2] = d[1:len(o):2]
    o[1::2] = d[0:len(o):2]
    return bytes(o)


def bl_target(b, i):
    """Target of a big-endian Thumb BL pair at image offset i, else None."""
    h = int.from_bytes(b[i:i + 2], "big")
    l = int.from_bytes(b[i + 2:i + 4], "big")
    if h & 0xF800 != 0xF000 or l & 0xF800 != 0xF800:
        return None
    off = (h & 0x7FF) << 12 | (l & 0x7FF) << 1
    if off & 0x400000:
        off -= 0x800000
    return BASE_3510 + i + 4 + off


def r0_constant(b, i):
    """r0 as set by the last `movs r0, #imm` or `ldr r0, [pc, #imm]` in the
    six half-words before offset i."""
    value = None
    for j in range(i - 12, i, 2):
        h = int.from_bytes(b[j:j + 2], "big")
        if h & 0xFF00 == 0x2000:
            value = h & 0xFF
        elif h & 0xFF00 == 0x4800:
            lit = ((j + 4) & ~3) + (h & 0xFF) * 4
            value = int.from_bytes(b[lit:lit + 4], "big")
    return value


def tone_name(img, index):
    """Name of PPM tone record `index`: u32 index, u32 size, 4CC, u32 0,
    u16, u16, then a NUL-terminated UTF-16BE name."""
    lo, hi = PPM[0] - BASE_3510, PPM[1] - BASE_3510
    head = index.to_bytes(4, "big")
    p = img.find(head, lo, hi)
    while p >= 0:
        cc = img[p + 8:p + 12]
        if all(0x30 <= c < 0x5b for c in cc) and img[p + 12:p + 16] == bytes(4):
            q = p + 0x14
            end = q
            while img[end:end + 2] != b"\0\0":
                end += 2
            return cc.decode(), img[q:end].decode("utf-16-be")
        p = img.find(head, p + 1, hi)
    return None, None


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--a", default="roms/3410f546e_swap16.bin")
    p.add_argument("--b", default="roms/3510-nhm8-v502/flash.bin")
    args = p.parse_args()
    a = mask_bl(open(args.a, "rb").read())
    raw = open(args.b, "rb").read()[:MCU_END_3510 - BASE_3510]
    b = mask_bl(swap16(raw))

    index = collections.defaultdict(list)
    for i in range(0, len(b) - WINDOW, 2):
        w = b[i:i + WINDOW]
        if len(set(w)) > 3:
            index[w].append(i)

    print("3410 game code windows found in the 3510 MCU (BL masked):")
    for name, lo, hi in GAMES_3410:
        total = found = 0
        pages = collections.Counter()
        for o in range(lo - BASE_3410, hi - BASE_3410 - WINDOW, 2):
            w = a[o:o + WINDOW]
            if len(set(w)) <= 3:
                continue
            total += 1
            hits = index.get(w)
            if hits and len(hits) < 4:
                found += 1
                for h in hits:
                    pages[(BASE_3510 + h) & ~0xFFF] += 1
        top = ", ".join(f"{k:#x} ({v})" for k, v in pages.most_common(4))
        print(f"  {name:13} {found:4}/{total:5} {found / total:6.1%}   {top}")

    img = open(args.b, "rb").read()
    o = HANDLERS_3510 - BASE_3510
    handlers = [int.from_bytes(raw[o + 4 * n:o + 4 * n + 4], "big") & ~1 for n in range(5)]
    print(f"\nGames handler table at {HANDLERS_3510:#x}, with each game's background tune:")
    for i in range(0x3E0000, 0x430000, 2):
        if bl_target(raw, i) != GAME_SOUND_LOOP:
            continue
        site = BASE_3510 + i
        # Each game's code follows its handler: the call belongs to the
        # nearest handler below it.
        h = max(x for x in handlers if x <= site)
        tid = r0_constant(raw, i)
        t = TONE_IDS - BASE_3510 + (tid - 4000) * 2
        tone = int.from_bytes(raw[t:t + 2], "big")
        cc, name = tone_name(img, tone)
        print(f"  handler {h:#010x}: tune id {tid:#x} at {site:#x} -> PPM tone {tone:#x} {cc} \"{name}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
