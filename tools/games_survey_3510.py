#!/usr/bin/env python3
"""Locate the 3510 v5.02 games statically, against the mapped 3410 v5.46 games.

The 3510 is DCT4 big-endian Thumb at 0x01000000 (roms/3510-nhm8-v502/flash.bin
from tools/dct4_decrypt.py); the 3410 image is MAME-order little-endian at
0x200000. The 3510 image is turned into little-endian half-words first so the
two can be compared window by window, with Thumb BL pairs masked in both.

Prints, for each 3410 game's code range, how many 12-byte windows occur in the
3510 and on which 4 KB pages; then the games handler table and the per-game id
each handler passes to the shared game library (sorted, these follow the PPM's
"GameBG" tune order: Bumper, D2M, Link5, SI tune, Car Racing). Nothing is run.
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
GAME_ID_CALL = 0x0142d174   # called once per game with its id in r0
TUNES = ["Bumper", "D2M", "Link5", "SI tune", "Car Racing"]  # PPM order


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
    """The last `movs r0, #imm` in the five half-words before offset i."""
    imm = None
    for j in range(i - 10, i, 2):
        h = int.from_bytes(b[j:j + 2], "big")
        if h & 0xFF00 == 0x2000:
            imm = h & 0xFF
    return imm


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

    o = HANDLERS_3510 - BASE_3510
    handlers = [int.from_bytes(raw[o + 4 * n:o + 4 * n + 4], "big") & ~1 for n in range(5)]
    ids = {}
    for i in range(0x3E0000, 0x430000, 2):
        if bl_target(raw, i) == GAME_ID_CALL:
            ids[BASE_3510 + i] = r0_constant(raw, i)
    print(f"\nGames handler table at {HANDLERS_3510:#x}:")
    rows = []
    for site, gid in ids.items():
        # Each game's code follows its handler, so a call belongs to the
        # nearest handler below it.
        h = max(x for x in handlers if x <= site)
        rows.append((gid, h, site))
    for rank, (gid, h, site) in enumerate(sorted(rows)):
        print(f"  handler {h:#010x}: game id {gid:#04x} (call at {site:#x}) -> GameBG {TUNES[rank]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
