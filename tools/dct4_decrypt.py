#!/usr/bin/env python3
"""Decrypt a Nokia DCT4 MCU or PPM flash file into a flat flash image.

DCT4 flash content is stored encrypted and the UPP decrypts it on the bus.
Each 16-bit half-word goes through an address-dependent XOR, a fixed GF(2)
linear map, and a per-image 16-bit base code. The tables and the base-code
auto-detection are the public reverse-engineered DCT4Crypt algorithm (decr.c
by g3gg0, github.com/g3gg0/DCT4Crypt), as carried by dct4decrypt in
gitlab.com/Postrediori/mobile-phone-tools and the JavaScript port in
github.com/RobyRew/retro-phone-tools (js/dct4.js). This is an independent
Python reimplementation.

File container: 0xA2, u32 BE header length, TLV header, then blocks of
  0x14, u32 BE address, u8 data checksum, u24 BE length, u8 header checksum, data.
The data checksum is the negated byte sum of the (encrypted) data and the
header checksum is ~sum(bytes 1..8), so both check the file, not the
decryption. The decryption is checked by the base code read at the auto offset.

The MCU image starts at 0x01000000 and is plain below 0x01000084; the PPM is
encrypted throughout. Gaps between blocks are filled with 0xFF.
"""
import argparse
import hashlib
import sys

MCU_FLASH_START = 0x01000000
MCU_CRYPT_START = 0x84
AUTO = {'mcu': (0x84, 0xFFFF), 'ppm': (0x00, 0x5050)}  # (offset, plaintext there)
BLOCK = 0x4000  # bytes per decode block; the base code is learnt in the first

MBIT = [0x1221, 0xa91a, 0x52a5, 0x0908, 0xa918, 0x1020, 0xffff, 0x52a1,
        0x0100, 0x1220, 0xad1a, 0x0900, 0x1000, 0x2908, 0x5221, 0xa908]
MADDR = [0x0fae, 0x3e7f, 0xc99f, 0xd6f7, 0xa71b, 0x14c4, 0x52a5, 0xcbb1,
         0x4285, 0xefdf, 0xdff7, 0x5080, 0xee9f, 0x0000, 0x8432, 0x5221,
         0x4084, 0xa91a, 0x56e7, 0xb93a, 0x5b21, 0xa818, 0x0000, 0xefdf]
MADDR_ADJ = [
    (0x00140, 0x1000), (0x00220, 0x52a1), (0x00480, 0x1221), (0x00600, 0xb928),
    (0x00810, 0x5221), (0x00840, 0x1220), (0x00900, 0x2008), (0x01020, 0x1221),
    (0x01080, 0x0908), (0x01100, 0x52a1), (0x02020, 0x0100), (0x02080, 0xfbbd),
    (0x04010, 0xa91a), (0x04040, 0xa908), (0x08008, 0x2908), (0x09000, 0x1000),
    (0x0a000, 0xbd3a), (0x10010, 0xad1a), (0x10040, 0x5221), (0x10400, 0x0908),
    (0x20200, 0x53a5), (0x40040, 0xa91a), (0x44000, 0x1b20), (0x80100, 0xa918),
    (0x800000, 0xb908),
]


def build_decode_table():
    de = [0] * 0x10000
    for c in range(0x10000):
        nc = 0
        for i in range(16):
            if c >> i & 1:
                nc ^= MBIT[i]
        de[nc] = c
    return de


def address_xor(addr):
    x = 0
    for bits, v in MADDR_ADJ:
        if addr & bits == bits:
            x ^= v
    for i in range(24):
        if addr >> (i + 1) & 1:
            x ^= MADDR[i]
    return x


_LOW = None
_HIGH = {}


def addr_xor(addr):
    """address_xor() via a low-16-bit table plus per-64K corrections.

    The function is a degree-2 polynomial in the address bits, so
    f(hi | lo) = f(hi) ^ f(lo) ^ (terms pairing one high and one low bit).
    """
    global _LOW
    if _LOW is None:
        _LOW = [address_xor(a) for a in range(0x10000)]
    hi = addr & ~0xFFFF
    t = _HIGH.get(hi)
    if t is None:
        cross = [(bits & 0xFFFF, v) for bits, v in MADDR_ADJ
                 if bits & 0xFFFF and bits & ~0xFFFF and hi & bits == bits & ~0xFFFF]
        h = address_xor(hi)
        t = _HIGH[hi] = [_LOW[a] ^ h ^ _cross(a, cross) for a in range(0x10000)]
    return t[addr & 0xFFFF]


def _cross(a, cross):
    x = 0
    for m, v in cross:
        if a & m == m:
            x ^= v
    return x


def read_blocks(data):
    if data[0] != 0xA2:
        raise ValueError('not a DCT4 flash file (first byte %#04x)' % data[0])
    p = 5 + int.from_bytes(data[1:5], 'big')
    blocks = []
    while p < len(data):
        if data[p] != 0x14:
            raise ValueError('unexpected block type %#04x at %#x' % (data[p], p))
        addr = int.from_bytes(data[p + 1:p + 5], 'big')
        length = int.from_bytes(data[p + 6:p + 9], 'big')
        x = data[p + 10:p + 10 + length]
        if (sum(x) + data[p + 5]) & 0xFF or (sum(data[p + 1:p + 10]) + 1) & 0xFF:
            raise ValueError('bad checksum in block at %#x (address %#010x)' % (p, addr))
        blocks.append((addr, data[p + 5], x))
        p += 10 + length
    return blocks


def decrypt(data, kind=None, base=None):
    blocks = read_blocks(data)
    start = blocks[0][0]
    end = max(a + len(x) for a, _, x in blocks)
    kind = kind or ('mcu' if start == MCU_FLASH_START else 'ppm')
    img = bytearray(b'\xff' * (end - start))
    for a, _, x in blocks:
        img[a - start:a - start + len(x)] = x

    de = build_decode_table()
    lo = MCU_CRYPT_START if kind == 'mcu' else 0
    out = bytearray(img)
    for off in range(lo, len(img) & ~1, 2):
        c = img[off] << 8 | img[off + 1]
        c = de[c ^ addr_xor(start + off)]
        out[off] = c >> 8
        out[off + 1] = c & 0xFF

    auto_off, auto_val = AUTO[kind]
    if base is None:
        base = (out[auto_off] << 8 | out[auto_off + 1]) ^ auto_val
    for off in range(lo, len(out) & ~1, 2):
        out[off] ^= base >> 8
        out[off + 1] ^= base & 0xFF
    return start, bytes(out), base, kind, blocks


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--kind', choices=('mcu', 'ppm'))
    ap.add_argument('--base', type=lambda s: int(s, 0), help='16-bit base code (default: auto)')
    a = ap.parse_args()
    data = open(a.input, 'rb').read()
    start, img, base, kind, blocks = decrypt(data, a.kind, a.base)
    open(a.output, 'wb').write(img)
    print('%s %s: %d blocks, %#010x..%#010x, base code %#06x, sha256 %s'
          % (kind, a.input, len(blocks), start, start + len(img), base,
             hashlib.sha256(img).hexdigest()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
