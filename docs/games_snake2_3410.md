# Snake II on the 3410: application map

Snake II is the first entry of the 3410's Select game list. It is the
3310's game (`games_snake2_3310.md`) on a bigger board and in the 3410's
games framework (`games_applications_3410.md`). This document gives what
differs, to the level needed to re-implement it; what it does not mention
is as on the 3310.

Addresses apply to one image only: NHM-2 v5.46 with PPM E and the virgin
PMM, flash base `0x200000` (hashes in `games_applications_3410.md`). Each
conclusion is marked **static**, **runtime** or **inferred**. Names live in
`ghidra/symbols/3410.csv`; decompiled text and frames stay under the ignored
`run_games_3410/` and `run_3410_*/`.

## Check against a re-implementation

Runtime. The C port in `nokia-gb-games/3410` replays the events the handler
received in three probe-steered games (`mame_nokia_3410_snake2_probe.lua`,
its `S3KEY` writes as keys) and every picture it draws appears, in order,
among the frames MAME captured: level 5 with no maze and 20 meals; level 9
on Tunnel, 10 meals and a crash into a wall; level 2 with a creature left to
run out and a blocked snake turned free in its 100 ms tick. Its menu pages
(Select game, Snake II's menu, Game options, Mazes, Level) equal the
phone's to the pixel. That confirms what follows.

## Reaching the game and its menus

Runtime. Games (main menu entry 7), Select game, Snake II; the title
animation (below) ends by itself into the game's menu: New game,
High scores, Options, Instructions, and Continue first while a game is
paused. Options opens Game options: Mazes (No maze, Box, Tunnel, Spiral,
Blockade, Twisted) and Level (nine bars). Fresh NVRAM starts at level 1
and No maze. Lists move their highlight in a short slide.

The menu pages, static and runtime (font names as the port extracts the
language pack's first six fonts):

- Header: the title in tiny plain at x = (93 - width) / 2, y 0, its width
  counting the space after the last letter; a line on y 3 from x 0 to
  three columns before it and from just after it to x 88; the entry number
  in tiny plain at 96 - its width. The Select game list's header is
  "Games".
- Rows: three, 15 rows apart from y 9; text in medium bold at x 1, two rows
  down; the selection inverted over x 0..91.
- Scrollbar: a line on x 94 from y 9 to 53; the thumb is 43 / n rows tall
  (at least 6) at y 10 + i (43 - height) / (n - 1), its middle column
  cleared and its two side columns drawn.
- Soft keys: small bold at y 56, the left at x 0 and the right ending at
  the screen's edge.
- Level page: "Level" in medium bold at (5, 0); bar i's line at
  x 10 + 9i from y 38 - 3i (37 for the first) to 39, a shadow on y 40 from
  x 5 + 9i to 10 + 9i, and the bars up to the level filled from the row
  above the line's top to y 38, five columns from x 4 + 9i.

## Framework and events

Static, runtime. `snake2_handler_24f8ec(event, a, b)`; its state is behind
`*(0x12e238 + 0x10)`, the mode byte at `0x12e238 + 3` (6 while playing). The
title, the menus and the game share the handler: events `0x0e` (chosen,
title), `0x0a` with a = 1 then `0x14` then `0x0c` (New game), `0x00` (the
timer: title frames, the game's ticks, the dead snake's blinks), `0x01`
with the key code in a (keys), `0x03` (Enter: pause). `0x3b2546(ms)` sets
the timer's period.

Keys (runtime): the same as the 3310's, by key code: 2, 4, 6, 8 steer,
1, 3, 7, 9 turn by the direction of travel, # (`0x0b`) clockwise, *
(`0x0a`) anticlockwise; a turn back is ignored.

## State

Static, runtime with the probe. The state, S below, is on the heap:

| Offset | Field |
|---:|---|
| +0x000 | u32 score (the HUD shows +2, its low half) |
| +0x008 | ptr occupancy bitmap, as on the 3310 |
| +0x00c, +0x00d | board width 23, height 13 |
| +0x010 | ptr maze record |
| +0x014.. | sprite ids: four score digits, countdown digits (+0x24, +0x28) |
| +0x034 | the snake record: ring of 299 sprite pointers, then tail index (+0x4b4), head index (+0x4b6), ring size w x h (+0x4b8) |
| +0x4e4, +0x4e5 | head cell; +0x4e6, +0x4e7 tail cell |
| +0x4ee, +0x4ef | direction, previous direction |
| +0x4f4, +0x4f5 | food cell |
| +0x4f8..+0x4fb | creature cells, two {x, y}; -1 when unused |
| +0x4fc, +0x500, +0x504 | food, creature and icon sprites |
| +0x514, +0x516 | the level's period, the period now |
| +0x519, +0x51a | the screen's size the board is worked out from |
| +0x51b | game mode: 1 a game; 2 and 4 the High scores page's demos (inferred) |
| +0x51c | level 1..9 |
| +0x51e, +0x51f | board offset 0, 1 |
| +0x520 | the timer blinks the dead snake |
| +0x521 | crash state 0, 1, 2 |
| +0x523 | grow on the next step |
| +0x525 | creature counter |
| +0x526 | swallow: the next neck is fat |
| +0x527 | a creature is out |
| +0x528 | pending direction |
| +0x529 | 1 once a game has started |
| +0x52a | blink counter |

The generator is the ANSI C one, `rand()` at `0x3f903c` (state `0x12ebac`,
1 at power-on), reduced with an unsigned modulo.

## Board and drawing

Static, runtime. `0x24b82e(96, 65)` gives 23 x 13 cells; the offsets put
cell (x, y) at pixel (2 + 4x, 11 + 4y). The frame is the outline of x 0..95,
y 9..64; the line is y 6 across. The score's four digits are the 3310's
4x5 glyphs (`0x49017c`), shown at x 1, 5, 9, 13 (their lit columns); the
creature countdown's at x 92 (units) and 88, the icon at (78, 1). Walls are
2-pixel lines through the cell centres, horizontal at (3 + 4 x1, 12 + 4y),
vertical at (3 + 4x, 12 + 4 y1).

Pictures: `0x4b2e50..0x4b323b`, the 3310's bitmaps without the large
creature's, then 35 descriptors of 24 bytes {u16 w, u16 h, u16 0, u16 1,
u32 bitmap, ...} in the 3310's order: food `0x4b2ef4`, creatures
`0x4b2f0c`, corners `0x4b2f9c`, heads `0x4b2ffc`, tails `0x4b305c`, body
`0x4b30bc`, new segment `0x4b30ec`, fat body `0x4b311c`, open heads
`0x4b317c`, fat corners `0x4b31dc`.

## Mazes

Static, runtime. Records at `0x497458`, 12 bytes: u32 walls, the first
snake's start cell (+4, +5), a second snake's (+6, +7), two bytes, the
number of walls (+10). Walls are 4 bytes {x1, y1, x2, y2} from `0x4973b8`.
Counts 0, 4, 10, 4, 12, 9 for No maze, Box, Tunnel, Spiral, Blockade,
Twisted. Maze numbers 6 and up are files (downloaded mazes, `0x24b904`).

Runtime: the edges wrap as on the 3310. With No maze a snake left to run
right at level 1 leaves the board at x 22 and comes back at x 0; with Box,
whose walls are the board's border, it crashes into the right wall and the
game ends.

## New game

Static, runtime: speeds as the 3310's (`0x4bef64`, level 1..9); the first
segment is made on the start cell, not off the screen, and the ring indices
start at 0; seven steps and a tail move leave the 3310's seven segments;
food at the middle, then placed.

## One tick and what differs

Static, runtime.

- Food: 50 tries (the 3310 makes 100), x = rand mod w, y = rand mod h.
- Creature: no large creature and no roll of 50. Up to 50 tries of
  x = rand mod w, y = rand mod h, cells (x, y), (x + 1, y), x + 1 < w, both
  free, x and x + 1 off the food's column, y off its row; only a placed
  creature draws its kind, rand mod 6. Entering it going left frees its
  left cell, going right its right cell.
- A creature eaten makes the snake grow, as food does.
- Ring full: score + 100, then the snake dies as below.
- Death: blocked, a 100 ms tick; blocked again, crash state 2, the death
  sound (`0x3b2510(0xfa1)`) and the vibrator on (`0x3b25d4(1)`); the next
  tick sets 500 ms and turns the vibrator on again; each tick then turns
  every segment on or off, the ring gone round or not, and the second
  turns the vibrator off; the eighth ends the game (`0x24b77e`) before the
  LCD shows it.
- Sounds and the vibrator (static, inferred from where they are called):
  `0x3b2510(id)` plays a tone when the games' sounds are on (`0x3f7ebe`):
  `0xfa0` a meal, `0xfa1` the death, `0xfa2` game over, `0xfa4` a new top
  score; records `0x1f`, `0x20`, `0x21` and `0x23` of the sound table at
  `0x4a9078` (`games_si_3410.md`, "Sounds and the vibrator"). `0x3b25d4(on)` switches the vibrator, which a meal does not run.

## Title

Static, runtime (every picture equal to MAME's frames). Event `0x0e`
(`0x24b484`) shows the picture of descriptor `0x4986a0` (96x65, bitmap
`0x4974a0`) and sets a 200 ms timer. Each timer event (`0x24eb2c`) counts a
step: steps 1 to 5 show the pictures of the five descriptors from
`0x4986b8`, bitmaps `0x4977a0` + `0x300` n, over it (each is whole, so it
replaces it), steps 6 to 8 nothing, step 9 the game's menu. The bitmaps are
`0x300` bytes apart, eight bands, so a picture's ninth band, its 65th row,
is the first of the next (of the last, the start of the descriptors); the
phone shows that row. The Navi key ends the title into the menu, C leaves
Snake II.

## Game over

Static, runtime (both states of three games' pictures equal to MAME's
frames, scores 22, 168, 255). `0x24b77e` shows the title's first picture,
compares the score with the record's (`0x24b4ec`; one top score for each
of the six mazes, and a `rand()` drawn), plays `0xfa4` for a new top score
or `0xfa2`, draws the score box (`0x24b5c8`) and sets a 100 ms timer with a
count of 30 at S+0x525 (`0x24eae2` counts it down; the Navi key ends it
early).

The box: x 51..95, y 50..61, set; its two 6x12 ends (descriptors
`0x4b4918`, `0x4b4930`, bitmaps `0x4b47d4`, `0x4b47e0`) drawn inverted at
x 51 and 88; between them rows 50, 60 and 61 clear; then the score's
digits, 6x8 (descriptors from `0x4b4948`, bitmaps from `0x4b47ec`, light
with a dark figure), from the right at x 81, 73, 65 .., y 51, without
leading zeros, at most four. A plus or minus sign (`0x4bef4c`, `0x4bef34`)
is not drawn for Snake II. With a new top score the digits blink (the
sprite mode `0x14`, `0x12` otherwise): runtime, the slots show empty
first, the digits 0.50 s later, then every 0.48 s, and the menu comes
3.28 s after the game ended.

## High scores

Static, runtime (every picture of two runs equal to MAME's: no game played
yet, and after a game on the same maze). The menu's High scores sends
event `0x0b`; `0x24d204` sets up the page and a 200 ms timer, and each
timer event steps it (`0x24f63c`, mode `0x0a`). Nothing of it is the game:

- `0x3b268a(5, 1, score, 0)` draws the chosen maze's top score in a box at
  the top: its ends are the game-over box's (`0x4b4918`, `0x4b4930`, drawn
  as they are, at x = (96 - 50) / 2 and 67, y 1), lines on rows 1, 11 and
  12 between them, the five digits from x 29, y 2, 8 apart, leading zeros
  shown, and the 11x11 medal (`0x4b4ad8`, bitmap `0x4b4ab0`) at (1, 1) and
  (84, 1). When the last game was played on this maze (the record
  `0x24b4ec` keeps), a second box at y 46 without medals shows its score,
  and the snake runs on row 26 instead of 32.
- A snake of seven sprites, head (`0x4b302c`), five body (`0x4b30ec`) and
  tail (`0x4b308c`), from x -4 leftwards 4 apart, and a creature
  (`0x4b2f0c` + 24 x `rand()` mod 6) at x 48 on the same row.
- Each step every segment moves 4 right. Until the head reaches x 44 the
  creature bobs, a row down and back up in turn; then the mouth opens
  (`0x4b31ac`) for a step, the creature goes, and over the next six steps
  the fat body (`0x4b314c`) moves from the first body segment to the
  tail. The snake carries on off the screen and the page stands, the timer
  still running, until a key.

## Not done

- Game modes 2 and 4 (S+0x51b), not seen; the High scores page is not
  one of them.
- A game over that is not a new top score, whose digits are inferred not
  to blink.
- The main menu's Games icon: not found as a plain strip bitmap.
- The highlight's slide in the lists.
