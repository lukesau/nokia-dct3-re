# The 3410's games: a first static survey

A comparison of the Nokia 3410's built-in games with the 3310 games mapped in
`games_applications_3310.md`, `games_snake2_3310.md` and
`games_bantumi_3310.md`. It was made to decide how a 3410 port would start.
Nothing here was run in MAME; every conclusion is **static** (read from the
two images) or **inferred**.

Images: 3310 NHM-5 v6.39 (PPM E, `roms/noki3310/3310f639e.fls`) and 3410
NHM-2 v5.46 (PPM E, `roms/noki3410/3410f546e.fls` from `make
normalize-3410`), both at flash base `0x200000`, in MAME's byte order.
`tools/games_compare_3410.py` reproduces every figure below.

## What the 3410 has

- MCU flash names Space Impact, Snake, Bantumi and Link5. There is no
  "Pairs" string in either image, so Pairs II is not on this phone, and
  Link5 is new.
- One Java game, Munkiki's Castles (Nokia, `MIDlet-Name: Munkiki's
  Castles`), is a 40888-byte JAR in the virgin PMM, stored twice (at PMM
  offsets `0x31401` and `0x51410`, identical). It unzips cleanly: classes
  `a`, `b`, `c`, `d` and `KKM` (obfuscated), PNGs, level data and six
  languages. The phone's own Java classes are not files: the MCU flash only
  holds their names (`com/nokia/mid`, `javax/microedition`), so the VM's
  library is built into the image.

## Are the shared games the 3310's?

Inferred: they are the same games adapted to the 96 x 65 screen, not the
3310 binaries and not new games.

### Code

12-byte windows of each 3310 function, with Thumb BL pairs masked in both
images, found anywhere in the 3410 image:

| 3310 family | Functions | Data labels |
|---|---:|---:|
| Snake II (`snake2_`) | 0.6% | 10.6% |
| Space Impact (`si_`) | 2.7% | 24.7% |
| Bantumi (`bantumi_`) | 5.0% | 67.1% |
| `memcpy` | 42.0% | |

Even `memcpy` matches less than half, so the 3410 was most likely built with
another compiler; low code figures do not by themselves show rewritten logic.
Whether each function does the same thing has to be checked in Ghidra.

### Snake

Static. The maze table is at `0x4973b8`, in a new format: 4-byte walls
`{x1, y1, x2, y2}` instead of the 3310's 8-byte `{x1, y1, 0, 0}, {x2, y2, 0,
0}`. No maze is still the first entry (`ff ff ff ff`). Maze 1 is the border
of a **23 x 13** board, the size the 3310's `snake2_board_dims_274296` gives
for 96 x 65: (96 - 6) / 4 = 22, plus one; (65 - 14) / 4 = 12, plus one.

The five mazes are the 3310's five, redrawn for that board rather than scaled
(inferred, reading the walls in the 3310's order, whose descriptors give 1,
4, 10, 4, 8 and 8 walls; the 3410's descriptors were not decoded). Maze 2
keeps its eight corner stubs on the new corners, and its two bars,
(8, 3)-(12, 3) and (8, 5)-(12, 5) on the 3310, become (7, 4)-(15, 4) and
(7, 8)-(15, 8). Maze 3 is still four walls. Maze 4 has 12 walls where the
3310 has 8. 77% of `snake2_bitmaps_327d4c` is found unchanged.

### Bantumi

Static. The pit table at `0x4beccc` keeps the 3310 format (14 x then 14 y,
the top-left of each pit box) with new numbers:

| | Pits 0..5 x | y | Store 6 | Pits 7..12 x | y | Store 13 |
|---|---|---:|---|---|---:|---|
| 3310 | 4, 17, 30, 44, 57, 70 | 36 | (68, 16) | 70, 57, 44, 30, 17, 4 | 3 | (3, 16) |
| 3410 | 9, 23, 37, 51, 65, 79 | 44 | (74, 22) | 80, 66, 52, 37, 23, 9 | 7 | (5, 22) |

`bantumi_title_pictures_318360` is found whole and
`bantumi_think_descs_31d22c` mostly, so the pictures are largely kept.

### Space Impact

Static. The 3310's y-path tables (84 entries, one per screen column) sit
together at `0x4ad094`..: `wave_abs` and `fall` identical, `rise` identical
for its first 80 entries; `wave_rel` is not found. Around them are tables the
3310 does not have: a wave between y 7 and 37 just before `wave_abs` (the
3310's runs 9 to 27), a relative wave of +-5 at `0x4ad1b4` (the 3310's is
+-4), a level-then-ramp path (25, down to 6, back up to 25), and a longer
rise-and-fall after `rise`. Inferred: enemies use the taller screen.
Title pictures (7%), level headers and spawn lists do not match byte for
byte; these hold pointers and were not decoded.

## What this means for a port

- The 3310 port's C structure and data formats are a starting point.
- Every screen-dependent table has to be read from the 3410 image: mazes,
  board layout, y-paths, title pictures, level scripts.
- Space Impact's logic needs checking function by function before the 3310
  code is reused.
- Munkiki's Castles is decompiled Java, a separate kind of work, and Link5 is
  a new map.
