# Snake II on the 3310: application map

This document maps Snake II, game id 0 of the 3310's Games menu, to the
level needed to re-implement it in portable C and check the result against
the firmware in MAME. It is the companion of `games_applications_3310.md`,
which maps Space Impact and the layers the games share (dispatch, event
codes, return codes, timers, sprite engine, sounds, vibration, settings
record); those descriptions are not repeated here.

Addresses apply to one image only: NHM-5 v6.39, 2 MiB at flash base
`0x200000` (hashes in `games_applications_3310.md`).

Each conclusion is marked **static** (read from code or data), **runtime**
(seen in MAME) or **inferred**. Nothing derived from the firmware is in the
tree: names for this game are in `run_games_3310/symbols_snake2.csv`,
evidence notes in `run_games_3310/notes_snake2.json`, and decompiled text
stays under the ignored `run_games_3310/`. The maze walls, bitmaps and
tables are described, not reproduced; a port reads them from the user's
dump at the addresses given.

## Reaching the game and its menus

Runtime. From idle:

```
enter, enter            wake, open the main menu
up x5, enter            Games: Snake II is the first entry
enter                   Snake II title animation
enter                   skips the title; the next enter starts the game
```

```
make run-keys GAMES_PRODUCT=3310 RUN_DIR=$PWD/run_snake2 SECONDS=40 \
  KEYS=enter,wait1000,enter,wait1200,up,up,up,up,up,wait800,enter,wait1000,enter,wait3000,enter,wait20000
```

The game starts at 16.62 s on that timeline. The game menu (`8-1-1` ..
`8-1-5`, a scrolling list with Select) is below, with the language-pack
indexes of its English strings; runtime, in English (switched first with
`enter, enter, 6, 2, 1, up, enter` and five `c` back to idle, after which
one `enter` opens the main menu):

| Item | String | What it does |
|---|---|---|
| New game | 560 | starts a game (event `0x2b`) |
| Level | 556 | page "Level:" (538, small bold at x = 5) with nine bars: bar i (0..8) at x = 5 + 8i, rows 29 - 2i .. 34, 4 wide, filled up to the level, each with a 1-pixel shadow at x + 5 from the row below its top to row 35 and along row 36 from x + 1 to x + 5; OK soft key; up/down change the level by one, clamped at 1 and 9; OK stores it and returns to the menu with no note |
| Mazes | 533 | list No maze (544), Maze 1 .. Maze 5 (539..543) with a scrollbar, path `8-1-3-n`, the stored one selected, wrapping; OK stores it and shows "%U selected" (546) as the maze's name on one line and "selected" on the next in the large font, with the Settings Done note's tick and timing, then the menu |
| Top score | 553 | the record's +2, the same page and animation as Space Impact's |
| Instructions | 554 | help text 1331 over four pages with More, wrapping |

During a game `enter` suspends it into the same menu with Continue (552)
first. These pages are the shared games menu code around `0x298xxx`, not
Snake II's handler, and were not mapped further.

Where the settings live (static, `games_ctx_load_2dbc7c`; runtime: writing
the bytes from Lua changes the game's level and maze):

- Level: `games_records_10f9e0` + 4 (Snake II is record 0), a byte 0..8.
  The game sees ctx+0x16 = level + 1, 1..9.
- Maze: record +0x28, a byte 0..5. The game sees ctx+0x17 = maze + 1;
  1 is No maze, 2..6 are Maze 1 .. Maze 5.
- Top score: record +2, u16.
- Record +0x2a, u16: a collection mask (see Bonus creatures), loaded into
  `snake2_globals_10c9b0` +0 with bit 15 replaced by whether the byte
  `games_setting_111507` is nonzero.

Runtime: on this image's fresh NVRAM the record reads level 9 (byte 8),
No maze, top score 27, which come from the PMM dump like Space Impact's
4075.

Title (static, `snake2_title_handler_2d780e`, id `0x80`): events `0x24` and
`0x2b` save ctx+0xc and +0xe, set a 250 ms tick and build an 84x48
picture (`snake2_title_pictures_318318`) and five hidden overlays of about
48x33 at x = 6; each tick shows the next overlay and hides the previous;
the sixth tick sets a 1200 ms period; the next tick, or any other event
such as a key, restores the saved timers and returns `0x10`, which ends the
title. The state lives in `games_title_state_110d60`, shared with the
other titles.

## Event handling and return codes

Static; runtime where noted. `snake2_handler_275aa4(event, ctx)`:

| Event | Action | Returns |
|---:|---|---|
| `0x2b` | new game with full reset (`snake2_new_game_2762e0`) | 1; 2 if an allocation fails |
| `0x24` | the same but without resetting the ring, filling the maze or setting the mode byte (state+0x2a5); never seen at runtime | 1 |
| `0x01` | tick (see One tick) | `0x21`, `0x16`, `0x1b`, `0x1f`, `0x18`; 1 if the mode byte is not 1 |
| `0x00` | one-shot timer: one blink step | `0x20`; `0x16` on the tenth |
| `0x0a`..`0x12`, `0x14`, `0x16`, `0x04`, `0x05` | keys (see Keys) | 1 |
| `0x09`, `0x0e`, codes + `0x80` | keys `0` and `5`, and every key repeat: ignored | 1 |
| `0x13`, `0x15`, `0x17`, `0x18`, `0x1a` | crash state 0: return 5; otherwise ctx+0x14 = 0, vibrate, free the board, return `0x18` | 5 or `0x18` |
| `0x1c` | crash state 2: free the board, return `0x1d`; otherwise clear the crash state, return 5 | |
| `0x33` | state query: ctx+4 = `snake2_state_10c9bc`, ctx+0 = `0x2b0` | 1 |
| `0x34` | suspend: free the board, pack the ring (`snake2_suspend_pack_27553c`), then as `0x33` | 1 |
| `0x35` | resume: new sprite engine and board, rebuild everything (`snake2_resume_build_275788`); ctx+0xc = the level period (0 if dead), ctx+0xe = 0 | 1 |

`games_app_handler_2dbdd4` does not send `0x13`..`0x1c`; where they come
from was not traced. Runtime: Continue sends `0x33` then `0x35`, and the
game then stands still until the first key, after which ticks resume at
the level period (the framework arms the tick on that key).

Return codes (static, `games_app_handler_2dbdd4`; `0x1f` and `0x20` are new
relative to the Space Impact map):

| Return | Effect |
|---:|---|
| `0x01` | nothing; no redraw |
| `0x05`, `0x1d` | not in the switch: nothing, no redraw |
| `0x16` | cancel and restart the tick from ctx+0xc; redraw |
| `0x18` | game over: post `0x5133` with the score in ctx+0x10, cancel the tick, one-shot and repeat timers |
| `0x1b` | play sound ctx+0x14 if Sounds is on; re-arm the tick if the event was a tick; redraw |
| `0x1f` | cancel and restart the one-shot from ctx+0xe; play sound ctx+0x14 if Sounds is on; re-arm the tick if the event was a tick; redraw |
| `0x20` | cancel and restart the one-shot from ctx+0xe; re-arm the tick if the event was a tick; redraw |
| `0x21` | redraw; re-arm the tick if the event was a tick |

Runtime: plain moves return `0x21`, meals `0x1b` with sound `0x1f`; a crash
returns `0x16` (period 100), then `0x1f` (period 2100, sound `0x20`), nine
blink events return `0x20`, then a tick returns `0x18`.

## Keys

Static; runtime: every key below was pressed at level 1 and moved the
snake as listed, and `5`, `0`, `8` while moving up and `6` while moving left
did nothing. Directions: 0 left, 1 up, 2 right, 3 down. A key writes the
pending direction (state+0x2a3), judged against the current direction
(snake +0x10); the tick copies pending into current before it moves.
Because the test is always against the current direction, no sequence of
keys within one tick can reverse the snake; the last key wins.

| Key | Event | Pending direction |
|---|---|---|
| `2` | `0x0b` | up, unless moving down |
| `8` | `0x11` | down, unless moving up |
| `4` | `0x0d` | left, unless moving right |
| `6` | `0x0f` | right, unless moving left |
| `1` | `0x0a` | left when moving vertically, up when moving horizontally |
| `3` | `0x0c` | right when moving vertically, up when moving horizontally |
| `7` | `0x10` | left when moving vertically, down when moving horizontally |
| `9` | `0x12` | right when moving vertically, down when moving horizontally |
| `#`, scroll `0x04` | `0x14`, `0x04` | (current + 1) mod 4: clockwise |
| `*`, scroll `0x05` | `0x16`, `0x05` | (current + 3) mod 4: anticlockwise |

Keys return 1: nothing is redrawn until the next tick.

## State

Static; runtime: the fields below were followed every frame with a Lua
probe. `snake2_state_10c9bc`, `0x2b0` bytes, fixed RAM, multi-byte fields
big-endian. A new game sets only the fields it needs; the rest keeps its
value.

The first `0x26c` bytes are a snake record, reached through the pointer
at +0x26c (which points at the state itself). The collision test takes a
snake index and multiplies it by `0x26c`, so the code allows more than one
snake, but only snake 0 exists.

| Offset | Size | Field |
|---:|---:|---|
| +0x000 | u16 | tail index into the ring |
| +0x002 | u16 | head index |
| +0x004 | u16 | ring modulus n = 299 |
| +0x008 | s8, s8 | head cell x, y |
| +0x00c | s8, s8 | tail cell x, y |
| +0x010 | u8 | current direction |
| +0x011 | u8 | direction of the previous step |
| +0x012 | 300 x u16 | ring of segment sprite ids, tail to head (packed cells while suspended) |
| +0x26c | ptr | the snake record (= state) |
| +0x270 | s8, s8 | board width 20, height 9 |
| +0x274 | ptr | occupancy bitmap (heap) |
| +0x278 | ptr | maze record in ROM |
| +0x27c | s8, s8 | food cell; -1, -1 when no free cell was found |
| +0x284 | 4 x 4 bytes | creature cells {x, y, 0, 0}; -1 when unused |
| +0x294 | u16 | food sprite |
| +0x296 | u16 | creature sprite (its kind 0..5 while suspended) |
| +0x298 | u16 | first of the four score digit sprites |
| +0x29a | u16 | countdown units digit sprite; +1 tens digit, +4 creature icon |
| +0x29c | u16 | the level's tick period, ms |
| +0x29e | u8 | food eaten on the last step: the tail stays once |
| +0x29f | u8 | creature counter: +4 per food while none is out, then ticks left |
| +0x2a0 | u8 | swallow flag: draw the next neck fat |
| +0x2a1 | u8 | a creature is out |
| +0x2a2 | u8 | crash state: 0 alive, 1 blocked once, 2 dead |
| +0x2a3 | u8 | pending direction |
| +0x2a4 | u8 | cleared by new game; no reader found |
| +0x2a5 | u8 | mode, 1 after new game `0x2b`; ticks do nothing unless it is 1 (inferred: one player) |
| +0x2a6 | u8 | cleared by new game; no reader found |
| +0x2a9 | u8 | blink counter |
| +0x2aa | u8 | the large creature was eaten; blocks another; never cleared by the game |
| +0x2ab | u8 | the creature out is the large animated one |
| +0x2ac | u8 | its animation frame, 0 or 1 |

`snake2_globals_10c9b0`: +0 u16 collection mask (bit 15 enables the large
creature, bits 0..9 collected), +2 s16 board x offset, +4 s16 board y
offset, +8 the state pointer (`snake2_state_ptr_10c9b8`). New game sets the
offsets to (81 - 4 w) / 2 and (37 - 4 h) / 2 with C division, 0 and 0 for
the 20 x 9 board. Runtime: the mask is 0x8000 from the boot init table
(`snake2_globals_init_2f4224`) and becomes 0 when the Games menu loads the
record.

## Board

Static; runtime: geometry checked on captured frames with and without a
maze.

- `snake2_board_dims_274296(84, 48)`: width (84 - 6) / 4 = 19, plus one as
  (84 - 2) mod 4 is not 0, so 20; height (48 - 14) / 4 = 8, plus one, so 9.
- Cell (x, y), 4 x 4 pixels, is drawn at pixel (2 + 4x, 10 + 4y): the cell
  area is x 2..81, y 10..45.
- The frame (fill sprites, mode 4): y = 8 from x = 0, 83 wide; x = 0 from
  y = 8, 39 high; x = 83 from y = 8, 40 high; y = 47 from x = 0, 83 wide.
  Inside is x 1..82, y 9..46, one blank pixel around the cell area.
- A rectangle sprite draws the line y = 6 across the screen. The score is
  four 4x5 HUD digits (`game_digit_sprites_10db68`) at x = 0, 4, 8, 12,
  y = 0, with leading zeros. The creature countdown is two digits at x = 75
  (tens) and 79 (units), y = 0, with the creature's 8x4 icon at (66, 1),
  shown only while a creature is out.
- Occupancy: one bit per cell in the LCD band layout, byte
  `[(y >> 3) * width + x]`, bit `y & 7`, 40 bytes, allocated zeroed at new
  game and resume. Walls and segments set bits; food and creatures do not.
- Edges wrap: a step is ((x + dx + w) mod w, (y + dy + h) mod h). Runtime:
  the snake leaves at x 0 and enters at x 19, leaves at y 8 and enters at
  y 0. Without a maze only the snake's own body kills it.

## Mazes

Static; runtime: No maze, Maze 1, Maze 2 and Maze 3 seen drawn as
described. `snake2_mazes_328108` holds six 16-byte records, indexed by
ctx+0x17 - 1:

| Offset | Field |
|---:|---|
| +0 | number of wall segments: 1, 4, 10, 4, 8, 8 |
| +4 | u32 pointer to the segments, in `snake2_maze_segments_327fe4` |
| +8, +9 | start cell of the snake |
| +12, +13 | two bytes no Snake II function reads |

A segment is 8 bytes, two cells `{x1, y1, 0, 0}`, `{x2, y2, 0, 0}`, a
horizontal run (y1 = y2, x1 <= x2; tested first) or a vertical one
(x1 = x2, y1 <= y2). `snake2_maze_build_2750dc` sets the occupancy bit of
every cell of every run and calls `snake2_walls_draw_274f0c`, which draws
the frame and then one fill sprite per run: horizontal at
(3 + 4 x1, 11 + 4 y), 4 (x2 - x1) + 2 wide, 2 high; vertical at
(3 + 4 x, 11 + 4 y1), 2 wide, 4 (y2 - y1) + 2 high. Walls are therefore
2-pixel lines through the cell centres.

- No maze is one segment at (-1, -1): the bit computed for it is a shift
  by 255, which sets nothing, and its sprite lands at x = 255, which is not
  drawn.
- Maze 1 is the border of the 20 x 9 board, so the snake no longer wraps.
- Mazes 2 to 5 are, in words: corner brackets plus two short horizontal
  bars in the middle, with openings on all four sides; two vertical and two
  horizontal bars in a pinwheel; a border with gaps in the middle of the
  left and right sides and two vertical bars inside; and horizontal bands
  with gaps, joined by two short vertical pieces.
- Start cells: (4, 4), except Maze 2 (0, 4), Maze 3 (0, 5) and Maze 4
  (4, 7). The snake always starts heading right.

## New game

Static, `snake2_new_game_2762e0` (reached with `bl` from the handler and
leaving through the handler's exit); runtime: the first frame.

1. Board 20 x 9, offsets 0; period = `snake2_level_speeds_3280fc`[level - 1]
   x 10 ms into ctx+0xc and state+0x29c; ctx+0xe = 0; score ctx+0x10 = 0.
2. Maze record from ctx+0x17; head and tail cell = start cell, and the
   head and tail ring indices both = the start cell's x (4, or 0 for Maze
   2 and Maze 3), which decides when the ring goes round; direction right
   in +0x10 and +0x11; swallow flag and crash state 0.
3. Occupancy bitmap allocated zeroed; sprite engine with w * h + 29
   sprites. For `0x2b` only: mode 1, ring modulus 299, all 300 ring slots
   zeroed, the maze filled in and drawn.
4. Blink counter 0. The start cell is marked occupied and gets a segment
   sprite, left at (-1, -1).
5. Seven head steps to the right, each with a new sprite, then one tail
   removal, which drops the off-screen sprite: the visible snake is seven
   segments, cells start + 1 .. start + 7, head on the right. Runtime:
   with No maze it covers cells 5..11 of row 4, the head at pixel x 46.
   Static: these calls pass four of the head step's seven arguments, so
   its food and creature checks read whatever the registers and stack
   hold; a re-implementation that checks against no food and no creature
   draws the phone's first frame (runtime, in the port).
6. Pending direction = right; food eaten flag 0.
7. Food sprite created and placed at random (Food); creature cells
   cleared; creature sprite created off screen; counter 0; no creature out.
8. HUD and the line at y = 6.

## One tick

Static, event 1, in order. Runtime: the sequence of states and returns
matches over several hundred ticks at levels 1, 3, 5 and 9.

1. Crash state 2: free the board, ctx+0x14 = 0, vibrate, return `0x18`.
2. Mode byte not 1: return 1.
3. Large creature out: flip its frame, set its picture and its icon's.
4. current direction = pending direction.
5. Collision test (`snake2_blocked_2753f2`): the cell ahead (with wrap) is
   blocked if its occupancy bit is set, except that the tail's cell is free
   unless the snake grows on this step (food eaten flag set).
6. Blocked, crash state 0: crash state 1, ctx+0xc = 100, return `0x16`. The
   snake stands for one 100 ms tick in which a turn can save it. Blocked,
   crash state 1: vibrate, crash state 2, ctx+0xc = 2100, ctx+0x14 = `0x20`,
   return `0x1f` (death sound, blink starts).
7. Not blocked and crash state 1: crash state 0, ctx+0xc = the level
   period, and the tick will return `0x16`.
8. Food eaten flag clear: remove the tail (`snake2_tail_remove_274844`):
   clear the tail cell's bit, advance the tail, give the new tail segment
   the tail picture, and hand the old tail sprite to the head step.
   Flag set: no removal and the head step creates a sprite, so the snake
   grows by one, one step after eating.
9. Head step (`snake2_head_step_274b98`, see Drawing). If the ring is full
   (head + 2 = tail mod 299) it returns 100 instead: score + 100, score
   redrawn, ctx+0x14 = `0x22`, board freed, return `0x18`. A 180-cell board
   cannot fill a 299-slot ring, so this does not happen.
10. Creature out and the head on one of its cells: eaten (Bonus creatures).
    Otherwise, if the counter is nonzero and the creature's first cell is
    valid, the counter drops by one; at 0 the creature disappears (cells
    cleared, sprite off screen, flags cleared) and the countdown is hidden,
    otherwise the countdown shows the counter.
11. Food eaten flag = whether the head is on the food.
12. Neither: return `0x16` if step 7 applied, else `0x21`.
13. Food or creature: vibrate. Food: score += level; new food; if no
    creature is out the counter goes up by 4, and once it reaches 20 with
    no creature cells in use a creature is spawned, its lifetime being the
    counter's 20 (a failed spawn resets the counter to 0); the countdown is
    updated. Creature: see Bonus creatures.
14. Swallow flag = 1, score redrawn, ctx+0x14 = `0x1f`, crash state 0, and
    return `0x16` if step 7 applied, else `0x1b`.

Runtime: at level 9 the counter read 4, 8, 12, 16 after the first four
foods and the creature appeared on the tick of the fifth with countdown 20,
then counted down one per tick. The tail index stood still on the tick after
each food and not after the creature.

## Food

Static, `snake2_food_place_27436e`; runtime: the positions repeat from run
to run (seed 1).

- Up to 100 tries: x = `game_rand16` mod width, then y = `game_rand16` mod
  height. A try is accepted when the cell's bit is clear and x differs from
  the x of every creature cell and y from every y (cells at -1 never
  match): food never shares a row or column with a creature.
- After 100 failures, the first free cell in row-major order from (0, 0),
  without the creature test. None: food at (-1, -1), sprite hidden.
- The food is a 3x3 diamond (`snake2_food_desc_327e10`), mode 1.
- Runtime: after boot the first food of a game is at (2, 5).

## Bonus creatures

Static (`snake2_creature_spawn_2744a8`); runtime for the small creature.

- r = `game_rand16` mod 50. If r is 0, the mask's bit 15 is set, the mode
  byte is 1 and state+0x2aa is 0, the large creature is tried; otherwise a
  small one.
- Small: 2 x 1 cells. Up to 100 tries of x = rand mod (width - 1), then
  y = rand mod height; cells (x, y) and (x + 1, y) (stored twice, as cells
  0, 1 and 2, 3) must be free and share no row or column with the food.
  Then kind = rand mod 6 picks one of six 8x4 pictures
  (`snake2_creatures_327e1c`) for the board sprite and the HUD icon, also
  when no place was found; in that case the sprite goes to (-1, -1) and the
  spawn fails.
- Static: a failed spawn (small or large) leaves the cells of its last try
  in place. The counter goes back to 0, but the next spawn needs cell 0 to
  be -1, so no creature comes again in that game, food keeps out of those
  rows and columns, and a head that enters one of those cells finds a
  creature to eat while none is shown.
- Large: 2 x 2 cells, x = rand mod (width - 1), y = rand mod (height - 1),
  all four free and clear of the food's row and column; two 8x8 frames
  (`snake2_big_creature_327e94`) and two 8x4 icon frames
  (`snake2_big_icon_327eac`), alternating every tick. Inferred: on this
  image the large creature needs `0x111507` set, which it is not in MAME,
  so it was not seen.
- The creature sprite is mode 1 at its first cell's pixel position.
- Entering: the head step hides the sprite and clears the two cells on the
  far side from the direction of travel (moving left cells 0 and 2, up 0
  and 1, right 1 and 3, down 2 and 3); the head is on one of the other two,
  so the tick then finds it eaten.
- Eaten: score += 5 x level + 5 + 2 x counter, where the counter is the
  ticks left (it is not decremented on the eating tick). All cells cleared,
  sprite off screen, counter 0, countdown hidden. Large creature also:
  `snake2_collect_bit_2754b6` sets a random clear bit 0..9 of the mask (and
  would loop forever with all ten set) and sets state+0x2aa; animation
  flags cleared. Eating a creature draws a fat neck but does not grow the
  snake.
- Runtime: at level 9 a creature eaten with 13 ticks left scored 76
  (45 + 5 + 26).

## Tail removal

Static, `snake2_tail_remove_274844`. The direction the tail moves, and the
picture the new tail gets, are worked out from the segments' sprite
positions in pixels, not from cells: a difference of more than 4 pixels
is taken as the way round the edge. The first segment of a game sits at
(-1, -1), which is 255, 255 as a byte position, and so counts as left of
everything: the first tail move, from it to start + 1, reads as to the
right, which is where start + 1 is. A re-implementation that uses cells
must make the same exception.

## Scoring

Static; runtime at levels 3, 5 and 9.

- Food: + level (1..9). Runtime: +3, +5, +9.
- Creature: + 5 x level + 5 + 2 x ticks left.
- Ring full: + 100 (unreachable).
- The score is a u32 at ctx+0x10. The HUD shows its low 16 bits
  (`snake2_draw_score_2741e0` reads the s16 at ctx+0x12) as four decimal
  digits. The framework copies ctx+0x12 into record +0 after every event.

## Levels and speed

Static; runtime at levels 1, 3, 5 and 9. `snake2_level_speeds_3280fc`
holds nine bytes; period = byte x 10 ms:

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Period (ms) | 660 | 480 | 380 | 300 | 230 | 180 | 140 | 110 | 90 |
| Timer units | 82 | 60 | 47 | 37 | 28 | 22 | 17 | 13 | 11 |

Timer units are ms / 7.96875, truncated. Runtime: ticks came 635, 364, 217
and 85 ms apart in MAME at levels 1, 3, 5 and 9 (7.74 ms a unit there), a
unit or so later now and then after a meal, since a timer restarts when
its event has been handled. The speed never changes during a game; the
level also sets the points per food.

## Drawing

Static. Every segment is its own 4x4 sprite (mode 4, layer 1); the frame,
walls and line are fill and rectangle sprites; food and creature are mode 1
bitmaps; the HUD digits mode 4. Picture sets are four 12-byte descriptors
indexed by direction (0 left, 1 up, 2 right, 3 down) unless noted; bitmaps
are 4x4 in the LCD band layout.

| Address | Use |
|---|---|
| `0x327ec4` | head, mouth closed, by direction of travel |
| `0x327f84` | head, mouth open: chosen when the cell ahead holds the food or a creature cell (`snake2_mouth_open_274a58`) |
| `0x327ef4` | tail, by the direction from the tail to the next segment |
| `0x327f24` | straight body, by direction |
| `0x327f54` | straight body, fat |
| `0x327e64` | corners, in the order: up then right, or left then down; up then left, or right then down; left then up, or down then right; right then up, or down then left |
| `0x327fb4` | the same four corners, fat |
| `0x327f3c` | the picture a new segment sprite is created with, before its real one is set |
| `0x327e10` | food, 3x3 |
| `0x327e1c` | six small creatures, 8x4 |
| `0x327e94`, `0x327eac` | large creature 8x8, its icon 8x4, two frames each |

At each step the new head sprite gets the head picture (open or closed)
and moves to its cell. The neck, the previous head, gets a body picture
chosen from the previous step's direction (+0x11), the new direction (+0x10)
and the swallow flag: straight when they are equal, otherwise the corner,
fat when the flag is set; then the flag is cleared and +0x11 = +0x10. So
the fat segment is the one the head leaves on the step after a meal, and it
travels down the body. The tail segment is re-pictured when the tail moves.
All bitmaps are in `snake2_bitmaps_327d4c`..`0x327dff` and the descriptors
run to `0x327fe3`, about 1.2 KiB of game data with the mazes and speeds.

## Sounds

Static ids; runtime: logged with Sounds forced on and traced on the buzzer
(the first two meals of a run played as `0x20` and `0x22`).

| Id | When | Notes, as hertz x timer units |
|---:|---|---|
| `0x1f` | food or creature eaten | 2637x1 (the Space Impact bonus blip) |
| `0x20` | death | 440x2 then a rest of 2, three times (script command `0x05` with 3 ... `0x06`, inferred to be a repeat) |
| `0x22` | ring full (unreachable) | 523x15, rest 3, 784x56 |

Runtime: `0x20` sounded as three 15 ms beeps 15.5 ms apart, `0x22` as
523 Hz for 115 ms and 784 Hz for 434 ms.

## Vibration

Static: `game_vibrate_2dd70e`, with the checks described for Space Impact,
is called for every food or creature eaten, on the second blocked tick, on
the game-over tick and when events `0x13`..`0x1a` end a game. Runtime: one
call per meal, one at the death and one at game over.

## Top score and game over

- Death (static and runtime): blocked tick, 100 ms wait, second blocked
  tick with sound `0x20` and the period set to 2100 ms. Its return arms the
  one-shot with ctx+0xe = 0, which fires on the next timer unit (7 ms). Each
  one-shot event toggles every segment between mode 4 and mode 6 (hidden),
  sets ctx+0xe = 250 and returns `0x20`, so the snake blinks every 250 ms
  (240 ms in MAME). Nine blinks fit before the 2100 ms tick (2036 ms in
  MAME), which returns `0x18`; the snake is hidden at that moment.
- The blink walks the ring from the tail index to the head index and does
  nothing when tail > head, so a snake whose ring has wrapped round slot
  299 does not blink (static). A tenth blink would set ctx+0xe = 0,
  restore the level period unless ctx+0x18 is set, and return `0x16`; a
  death never gets there.
- After `0x18` the framework takes over (runtime). With a new top score the
  screen inverts and shows a fireworks animation for about 2.95 s, then
  "Game over! TOP SCORE:" and the score (string 576) for about 2.95 s, then
  the game menu with New game selected. Otherwise "Game over! Your score:"
  and the score (578) is written over the game screen for about 2.95 s,
  then the menu. Which code compares and stores the top score was not
  traced.

## Random numbers

Static: only `game_rand16_2dd7d0` is used: food x then y, creature choice
(mod 50), position, kind (mod 6), collection bit (mod 10). Runtime: the
seed is 1 after boot in MAME, so scripted runs repeat exactly.

## Timing

- Tick: ctx+0xc, the level period; 100 ms for the grace tick; 2100 ms
  after a death. The first tick comes one period after New game.
- One-shot: only the blink, 0 ms and then 250 ms.
- Key repeats are ignored; a turn shows on the next tick.
- After Continue the game stands until a key is pressed (runtime).

## Suspend and resume

Static. Suspend frees the board and packs each ring entry, tail to head,
into a u16: bits 0..4 cell x, 5..10 cell y, 11..12 the picture's index in
its set, 13..15 the kind (0 straight, 1 corner, 2 fat straight, 3 fat
corner, 4 head, 6 open head, 7 tail), found by comparing the sprite's
bitmap pointer with the picture sets; the creature's kind replaces its
sprite id. Resume rebuilds the maze, each segment sprite and its occupancy
bit from the packed words, the HUD, the score, the food, the creature and
the countdown. Runtime: suspend and Continue restored the picture as it
was.

## Probe

`mame_nokia_3310_snake2_probe.lua` logs every handler event with the CPU
cycle count (13 MHz), each return code and sound, and the state each
frame, and can steer the snake to the food by writing the pending direction;
the level, maze and top score can be planted in the record (environment
variables at the top of the script). Pass it to `make run-keys` as
`RUN_EXTRA_ARGS="-autoboot_script $PWD/mame_nokia_3310_snake2_probe.lua -debug -debugger none"`.
The runs used for this document were made with it. Each write of the
pending direction is logged as `S2KEY d`, which a replay turns into the
key for that direction; `S2_IGNORE_CREATURE=1` leaves creatures to run
out and `S2_SAVE_ONCE=1` turns the snake free the first time it is
blocked.

## Check against a re-implementation

Runtime. The C port in `nokia-3310-games` replays the events the
firmware's handler received in three probe-steered games (the `S2KEY`
writes as keys) and every picture it draws appears, in order, among the
frames MAME captured: level 5 with no maze, 30 meals and a death after
the ring had gone round (tail index 272, head 8), so that the dead snake
did not blink; level 9 on Maze 2, 14 meals; and level 2 with a creature
left to run out and a blocked snake turned free in its 100 ms tick. That
confirms the tick, the keys, food and creature placement with the random
generator, the countdown, scoring, the pictures and their order, the
walls, the death and the blink as described here. The menus' Level,
Mazes, maze note, Instructions and Game over pages equal the port's to
the pixel in English.

## Not done

- The menu pages (Level bars, Mazes list, Top score, Instructions) belong to
  the shared games menu code and are described from screenshots only.
- The code that compares the score with the top score and stores it, and
  the fireworks animation, were not traced; neither was what writes the
  collection mask back to record +0x2a.
- The large creature, the collection mask and `0x111507` are static only;
  `0x111507`'s meaning is a guess.
- Events `0x13`, `0x15`, `0x17`, `0x18`, `0x1a` and `0x1c`: who sends them is
  not known. Event `0x24` (new game without reset) was never seen.
- Level 4, 6, 7 and 8 periods are static only; Mazes 4 and 5 were not
  run.
- The large creature and a failed spawn were not reached in any run.
- The title animation is summarised, not specified frame by frame.
- `0x20`'s `0x05`/`0x06` commands are read as a repeat from what the buzzer
  did, not from the tone task's code.

## Address map

Names are in `run_games_3310/symbols_snake2.csv` and notes in
`run_games_3310/notes_snake2.json`; this table is generated from them. The
shared functions it relies on (`games_dispatch_2dbd2a`,
`games_app_handler_2dbdd4`, `games_ctx_load_2dbc7c`, `game_rand16_2dd7d0`,
`game_vibrate_2dd70e`, `game_alloc_zeroed_2dd6dc`, the sprite engine,
`game_digit_sprites_10db68`, `sound_play_2ec8ca`, `rt_smod_2f04fc`,
`rt_umod_2f0998`, `memcpy_2f1158`, `heap_free_29a74e`) are in
`ghidra/symbols/3310.csv` and `games_applications_3310.md`.

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x10c9b0` | label | `snake2_globals_10c9b0` | Snake II globals: +0 u16 collection mask (bit 15 enables the large creature, bits 0..9 collected; loaded from record +0x2a by games_ctx_load with bit 15 = (0x111507 != 0)), +2 s16 board x offset, +4 s16 board y offset (both 0), +8 pointer to the state. Runtime: 0x80 written to +0 at boot (init table 0x2f4224), 0 at the Games menu. |
| `0x10c9b8` | label | `snake2_state_ptr_10c9b8` | Pointer to the Snake II state (0x10c9bc), set by new game and by event 0x33. |
| `0x10c9bc` | label | `snake2_state_10c9bc` | Snake II state, 0x2b0 bytes (event 0x33/0x34 hands this address and size). +0 tail index, +2 head index, +4 ring modulus 299, +8/+9 head cell, +0xc/+0xd tail cell, +0x10 direction, +0x11 previous direction, +0x12 ring of 300 sprite ids, +0x270 board w/h, +0x274 occupancy ptr, +0x278 maze record, +0x27c food, +0x284 creature cells, +0x294.. sprite ids, +0x29c period, +0x29e..+0x2ac flags; layout in docs/games_snake2_3310.md. Runtime: fields traced with a frame-polling Lua probe. |
| `0x10f9e0` | label | `games_records_10f9e0` | Per-game record, 0x2c bytes each. Snake II (id 0): +0 result word, +2 u16 top score, +4 level 0..8 (ctx+0x16 = +4 + 1), +0x28 maze 0..5 (ctx+0x17 = +0x28 + 1), +0x2a u16 collection mask. Runtime: writing +4 and +0x28 from Lua changes the game's level and maze. |
| `0x110d60` | label | `games_title_state_110d60` | Title-animation state shared by the games' title handlers (0x2d76f6, 0x2d780e, 0x2d7974, 0x2d7b3c): +2 step counter, +4 picture sprite, +0x14/+0x16 saved ctx tick/one-shot, +0x18.. overlay sprite ids. |
| `0x111507` | label | `games_setting_111507` | Games setting byte next to Sounds (0x111505) and Shakes (0x111506); games_ctx_load copies whether it is nonzero into bit 15 of the Snake II collection mask, which the large creature requires. Meaning inferred only; 0 in MAME. |
| `0x2741e0` | function | `snake2_draw_score_2741e0` | (ctx, first digit sprite): draws the s16 at ctx+0x12 (low half of the score) as four decimal digits into sprites first+3 (units) .. first+0, using game_digit_sprites_10db68. |
| `0x27421c` | function | `snake2_draw_countdown_27421c` | (units sprite, value): value > 0 shows sprites id, id+1 and id+4 (mode 4) and sets the units and tens digits; value <= 0 hides them (mode 6). The creature countdown and icon. |
| `0x274296` | function | `snake2_board_dims_274296` | (84, 48, out) -> board size in 4-px cells: w = (84-6)/4 + ((84-2)%4 != 0) = 20, h = (48-14)/4 + ((48-2)%4 != 0) = 9. |
| `0x2742d6` | function | `snake2_first_free_cell_2742d6` | (out, board) -> first cell with a clear occupancy bit in row-major order from (0,0); returns 0 when the board is full. |
| `0x27436e` | function | `snake2_food_place_27436e` | Food placement (board, food sprite, creature cells, out): up to 100 tries of x = rand16 % w, y = rand16 % h, accepted when the cell is free and shares no row or column with any creature cell; then the first free cell; none: (-1,-1) and the sprite hidden. Sprite at (2+4x, 10+4y). Runtime: positions reproduce from seed 1. |
| `0x2744a8` | function | `snake2_creature_spawn_2744a8` | Creature spawn (board, &sprite, cells, food, icon sprite \| mode<<16): rand16 % 50 == 0 with mask bit 15, mode 1 and state+0x2aa == 0 tries the 2x2 animated creature, else a 2x1 creature with kind rand16 % 6 (pictures 0x327e1c). 100 tries each, cells free and clear of the food's row and column. Returns 1 when placed. Runtime: spawned on the 5th food with countdown 20. |
| `0x274844` | function | `snake2_tail_remove_274844` | Tail removal (snake, board): clears the tail cell's occupancy bit, advances the tail index mod 299, moves the tail cell to the next segment's, gives that segment the tail image (0x327ef4 + direction to the next segment) and returns the old tail sprite for reuse as the head. |
| `0x274a58` | function | `snake2_mouth_open_274a58` | (board, snake, food, creature cells) -> 1 when the cell ahead of the head (with wrap) is the food or a creature cell: the head is drawn with its mouth open (0x327f84). |
| `0x274b98` | function | `snake2_head_step_274b98` | Head step (snake, board, sprite or 0, &swallow flag, food, creature cells, creature sprite): ring full (head+2 == tail mod 299) -> returns 100; creates a sprite when none is passed (growth); moves the head with wrap, sets its occupancy bit, head image (closed or open), stores the sprite in the ring; on a creature cell hides the creature and clears the two cells away from the travel direction; re-images the neck (straight/corner, fat when the swallow flag is set) and clears the flag. |
| `0x274f0c` | function | `snake2_walls_draw_274f0c` | (maze, board): draws the playfield frame (four fill sprites around x 0..83, y 8..47) and one 2-px fill sprite per maze segment through the cell centres. |
| `0x2750dc` | function | `snake2_maze_build_2750dc` | (board, maze record): sets the occupancy bit of every cell of every wall segment (horizontal or vertical runs of 8-byte {x1,y1,0,0,x2,y2,0,0}), then draws with 0x274f0c. |
| `0x2752b0` | function | `snake2_hud_create_2752b0` | HUD: four score digit sprites at x 0,4,8,12 (mode 4), countdown digits at x 79,75,71,67 and the creature icon at (66,1) (mode 6, hidden), and the rectangle line at y 6. |
| `0x27533e` | function | `snake2_food_init_27533e` | Food and creature init at new game: food sprite (0x327e10, mode 1) then a random placement, creature cells cleared, creature sprite (mode 1) off screen, counter and active flag 0. |
| `0x2753f2` | function | `snake2_blocked_2753f2` | (state, snake index, board, &food-eaten flag) -> nonzero when the cell ahead (with wrap) is blocked: its occupancy bit, except that the tail's cell is blocked only when the snake grows this step. Snake records are 0x26c bytes apart; only snake 0 exists. Runtime: walls and the body block. |
| `0x2754b6` | function | `snake2_collect_bit_2754b6` | Large creature eaten: sets a random clear bit 0..9 (rand16 % 10, retried while set) in the collection mask at 0x10c9b0 and sets state+0x2aa. Loops forever if all ten bits are set. |
| `0x275502` | function | `snake2_board_free_275502` | Frees the occupancy bitmap (state+0x274) if allocated. |
| `0x27553c` | function | `snake2_suspend_pack_27553c` | Suspend: packs each ring entry tail to head into a u16 (x bits 0-4, y bits 5-10, image index bits 11-12, kind bits 13-15 found by comparing the sprite's bitmap pointer with the image sets) and the creature's kind into state+0x296. |
| `0x275788` | function | `snake2_resume_build_275788` | Resume: rebuilds maze, every segment sprite and its occupancy bit from the packed ring, HUD, score, food sprite, creature sprite and countdown. |
| `0x275aa4` | function | `snake2_handler_275aa4` | Game id 0 entry (Snake II). 0x2b/0x24 new game, 1 tick, 0 blink step, keys via the jump table at 0x275b28, 0x33/0x34/0x35 state query/suspend/resume, 0x13/0x15/0x17/0x18/0x1a end a dying game, 0x1c. Runtime: returns 0x21, 0x1b (eat, sound 0x1f), 0x16 (grace 100 ms), 0x1f (death, sound 0x20), 0x20 (blink), 0x18 (game over). |
| `0x275b28` | label | `snake2_key_jumptable_275b28` | Jump table for game events 0x0a..0x16 (keys 1..9, 0x13, #, 0x15, *). Keys set the pending direction at state+0x2a3 from the current one; runtime-verified for all of 1-9, # and *. |
| `0x2762e0` | function | `snake2_new_game_2762e0` | New game (reached by bl from the handler, returns through 0x276642): board 20x9, period = level table * 10 ms, maze record, start cell, direction right, occupancy and sprite engine (w*h+29), event 0x2b also resets the ring and fills the maze; seven head steps then one tail removal leave 7 visible segments. Runtime: first frame shows cells 5..11 of row 4. |
| `0x276472` | label | `snake2_new_game_fail_276472` | Inside new game: allocation-failure exit returning 2; the code after it is the rest of new game. |
| `0x276640` | label | `snake2_return_1_276640` | Handler exit returning 1 (movs r7,#1 falling into 0x276642); reached by bl as a long branch. |
| `0x276642` | label | `snake2_return_276642` | Common handler exit: returns r7. |
| `0x2d7724` | function | `snake2_title_build_2d7724` | Snake II title build: allocates 6 sprites, creates the 84x48 picture 0x318318 and five hidden overlays (0x318324..0x318354) at x 6. |
| `0x2d77b2` | function | `snake2_title_step_2d77b2` | Snake II title step: on a tick shows the next overlay and hides the previous; at step 6 sets a 1200 ms period; afterwards, or on any other event, restores the saved ctx timers, frees sprites and returns 0x10. |
| `0x2d780e` | function | `snake2_title_handler_2d780e` | Handler for id 0x80, the Snake II title: on 0x24/0x2b saves ctx+0xc/+0xe, sets a 250 ms tick and builds the title; other events step it. |
| `0x2f4224` | label | `snake2_globals_init_2f4224` | Entry of a RAM-init table: address 0x10c9b0, value 0x80 (the collection mask starts as 0x8000 at boot). |
| `0x318318` | label | `snake2_title_pictures_318318` | Snake II title pictures: 12-byte descriptors, an 84x48 picture then five overlays of about 48x33. |
| `0x327d4c` | label | `snake2_bitmaps_327d4c` | Snake II bitmaps (LCD band layout), 0x327d4c..0x327dff: food, six small creatures, large creature frames and icons, 4x4 segment pictures. |
| `0x327e10` | label | `snake2_food_desc_327e10` | Food descriptor, 3x3 diamond. |
| `0x327e1c` | label | `snake2_creatures_327e1c` | Six 8x4 small creature descriptors, indexed by kind 0..5; also the HUD icon. |
| `0x327e64` | label | `snake2_corners_327e64` | Four corner segment descriptors (up->right/left->down, up->left/right->down, left->up/down->right, right->up/down->left). |
| `0x327e94` | label | `snake2_big_creature_327e94` | Large creature, two 8x8 frames. |
| `0x327eac` | label | `snake2_big_icon_327eac` | Large creature HUD icon, two 8x4 frames. |
| `0x327ec4` | label | `snake2_heads_327ec4` | Head descriptors, mouth closed, by direction 0 left, 1 up, 2 right, 3 down. |
| `0x327ef4` | label | `snake2_tails_327ef4` | Tail descriptors by direction toward the next segment. |
| `0x327f24` | label | `snake2_body_327f24` | Straight body descriptors by direction. |
| `0x327f3c` | label | `snake2_new_segment_327f3c` | Four 4x4 descriptors; the first is used to create a new segment sprite before its real image is set. |
| `0x327f54` | label | `snake2_body_fat_327f54` | Fat straight body descriptors (swallowed food), by direction. |
| `0x327f84` | label | `snake2_heads_open_327f84` | Head descriptors with the mouth open, by direction. |
| `0x327fb4` | label | `snake2_corners_fat_327fb4` | Fat corner descriptors, same order as 0x327e64. |
| `0x327fe4` | label | `snake2_maze_segments_327fe4` | Maze wall segments, 8 bytes each ({x1,y1,0,0},{x2,y2,0,0}), 0x327fe4..0x3280fb, 35 segments for the six records. |
| `0x3280fc` | label | `snake2_level_speeds_3280fc` | Nine bytes: tick period / 10 ms for levels 1..9 (660, 480, 380, 300, 230, 180, 140, 110, 90 ms). Runtime: levels 1, 3, 5, 9 tick at 82, 47, 28, 11 timer units. |
| `0x328108` | label | `snake2_mazes_328108` | Six 16-byte maze records (No maze, Maze 1..5): +0 segment count, +4 segment pointer, +8/+9 start cell, +12/+13 unused by the game. Runtime: Maze 1 and 3 drawn as decoded. |
| `0x328168` | label | `snake2_no_cell_328168` | Four bytes ff ff 00 00: the 'no cell' value food placement starts from. |
