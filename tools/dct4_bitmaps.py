#!/usr/bin/env python3
"""Render 3510 (DCT4) game bitmaps to PNG.

A game bitmap is a 0x18-byte descriptor in the big-endian flash image:
  +0 u16 width, +2 u16 height, +4 u32 depth (1 or 2), +8 u32 data, +0xc u32
  second plane (nullable), +0x10, +0x14.
1-bit data is packed vertically: one byte per column per 8-row band, LSB at
the top, bands of `width` bytes. Frame arrays are contiguous descriptors.
Only depth 1 is rendered; other depths are listed and skipped.

  dct4_bitmaps.py 0x01504bf8 --count 40 --out run_3510_bitmaps/kart
  dct4_bitmaps.py 0x01504bf8 --count 40 --sheet kart_sprites.png
"""

import argparse
import os
import struct
import sys
import zlib

BASE = 0x01000000


def write_png(path, rows):
    """8-bit greyscale PNG from a list of equal-length rows of 0..255."""
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(r) for r in rows)

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def descriptor(img, addr):
    o = addr - BASE
    w, h, depth, data, plane = struct.unpack(">HHIII", img[o:o + 16])
    return w, h, depth, data, plane


def is_descriptor(img, addr):
    o = addr - BASE
    if not 0 <= o <= len(img) - 0x18:
        return False
    w, h, depth, data, _ = descriptor(img, addr)
    return 0 < w <= 256 and 0 < h <= 256 and depth in (1, 2) and BASE <= data < BASE + len(img)


def pixels(img, addr):
    """Rows of 0 (black) / 1 (white) for a depth-1 bitmap."""
    w, h, depth, data, _ = descriptor(img, addr)
    o = data - BASE
    return [[0 if img[o + (y // 8) * w + x] >> (y % 8) & 1 else 1 for x in range(w)]
            for y in range(h)]


def scaled(rows, scale):
    out = []
    for r in rows:
        line = [255 if p else 0 for p in r for _ in range(scale)]
        out += [line] * scale
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("addr", type=lambda s: int(s, 0), help="first descriptor")
    ap.add_argument("--count", type=int, default=1, help="contiguous descriptors (stops at a non-descriptor)")
    ap.add_argument("--image", default="roms/3510-nhm8-v502/flash.bin")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--out", help="directory for one PNG per bitmap")
    ap.add_argument("--sheet", help="one PNG with every bitmap, top to bottom")
    a = ap.parse_args()
    img = open(a.image, "rb").read()

    found = []
    for n in range(a.count):
        addr = a.addr + n * 0x18
        if not is_descriptor(img, addr):
            break
        w, h, depth, data, plane = descriptor(img, addr)
        print(f"{addr:#010x} {w:3} x {h:3} depth {depth} data {data:#010x} plane {plane:#010x}")
        if depth == 1:
            found.append((addr, pixels(img, addr)))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        for addr, rows in found:
            write_png(os.path.join(a.out, f"{addr:08x}.png"), scaled(rows, a.scale))
    if a.sheet and found:
        width = max(len(r[0]) for _, r in found)
        rows = []
        for _, r in found:
            rows += [line + [1] * (width - len(line)) for line in r] + [[1] * width] * 2
        write_png(a.sheet, scaled(rows, a.scale))
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
