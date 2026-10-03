#!/usr/bin/env python3
"""Compare the 3310 v6.39 games with the 3410 v5.46 flash, statically.

Prints, for each 3310 symbol family in ghidra/symbols/3310.csv, the share of
its bytes found anywhere in the 3410 image, then locates the screen-size
tables described in docs/games_survey_3410.md. Nothing is run in MAME.

Matching uses 12-byte windows at even offsets. Thumb BL pairs are masked in
both images first, since call targets move between builds.
"""

import argparse
import collections
import csv
import re
import sys

BASE = 0x200000
WINDOW = 12


def mask_bl(data):
    out = bytearray(data)
    for i in range(0, len(out) - 3, 2):
        if out[i] & 0xF8 == 0xF0 and out[i + 2] & 0xF8 == 0xF8:
            out[i:i + 4] = b"\xf0\x00\xf8\x00"
    return bytes(out)


def family_coverage(a, b, symbols_path):
    am, bm = mask_bl(a), mask_bl(b)
    windows = {bm[i:i + WINDOW] for i in range(0, len(bm) - WINDOW, 2)}
    with open(symbols_path) as f:
        syms = sorted((int(r[0], 16), r[1], r[2]) for r in csv.reader(f)
                      if int(r[0], 16) >= BASE)
    totals = collections.defaultdict(lambda: [0, 0])
    rows = []
    for n, (addr, kind, name) in enumerate(syms):
        nxt = syms[n + 1][0] if n + 1 < len(syms) else addr + 0x200
        end = min(nxt, addr + 0x800)
        if end - addr < WINDOW + 2:
            continue
        ws = [am[i:i + WINDOW] for i in range(addr - BASE, end - BASE - WINDOW, 2)]
        hit = sum(w in windows for w in ws)
        family = name.split("_")[0]
        totals[(family, kind)][0] += hit
        totals[(family, kind)][1] += len(ws)
        rows.append((name, kind, end - addr, hit / len(ws)))
    return totals, rows


def find(b, needle):
    i = b.find(needle)
    return None if i < 0 else i + BASE


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--a", default="roms/noki3310/3310f639e.fls")
    p.add_argument("--b", default="roms/noki3410/3410f546e.fls")
    p.add_argument("--symbols", default="ghidra/symbols/3310.csv")
    p.add_argument("--labels", action="store_true", help="also list each data label")
    args = p.parse_args()
    a = open(args.a, "rb").read()
    b = open(args.b, "rb").read()

    totals, rows = family_coverage(a, b, args.symbols)
    print("3310 bytes found in the 3410 image, by symbol family:")
    for (family, kind), (hit, total) in sorted(totals.items()):
        print(f"  {family:10} {kind:9} {total:6} windows {hit / total:6.1%}")
    if args.labels:
        for name, kind, size, frac in rows:
            if kind == "label":
                print(f"  {frac:5.0%} {size:5} {name}")

    def at(addr, n):
        return a[addr - BASE:addr - BASE + n]

    print("\nSpace Impact y-path tables (84 entries on the 3310):")
    for name, addr in [("wave_abs", 0x312104), ("wave_rel", 0x312158),
                       ("fall", 0x3121AC), ("rise", 0x312200)]:
        table = at(addr, 84)
        hit = find(b, table[:24])
        if hit is None:
            print(f"  {name:9} not found")
            continue
        o = hit - BASE
        same = next((i for i in range(84) if b[o + i] != table[i]), 84)
        print(f"  {name:9} {hex(hit)}, first {same} of 84 entries identical")

    print("\nSnake maze tables (4-byte segments, No maze first):")
    # No maze, then the four sides of Maze 1: {x1, y1, x2, y2} per wall.
    border = rb"\xff\xff\xff\xff\x00\x00\x00(.)\x00\x00(.)\x00\2\x00\2\1\x00\1\2\1"
    for m in re.finditer(border, b, re.S):
        h, w = m.group(1)[0] + 1, m.group(2)[0] + 1
        if w > 1 and h > 1:
            print(f"  {hex(m.start() + BASE)}: Maze 1 border, board {w} x {h}")

    print("\nBantumi pit tables (14 x then 14 y):")
    for m in re.finditer(rb"(.)\1{5}(.)(.)\3{5}\2", b, re.S):
        o = m.start()
        xs = b[o - 14:o]
        if (o >= 14 and xs[0] < xs[1] < xs[2] < xs[3] < xs[4] < xs[5]
                and xs[7] > xs[8] > xs[9] > xs[10] > xs[11] > xs[12]):
            print(f"  {hex(o - 14 + BASE)}: x {list(xs)} y {list(b[o:o + 14])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
