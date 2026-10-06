# Pairs II and the title screens on the 3310: application map

This maps Pairs II, the memory game of the 3310's Games menu, to the level
needed to re-implement it, and the title animations of all four games. It
follows `games_applications_3310.md`, which describes the framework the game
runs in (dispatch, event codes, return codes, timers, sprite engine, sound
and settings record); only what Pairs II adds or uses differently is
repeated here.

Addresses apply to one image only: NHM-5 v6.39 with PPM E and the v.2 PMM,
2 MiB at flash base `0x200000` (hashes in `games_applications_3310.md`).

Each conclusion is marked **static** (read from code or data), **runtime**
(seen in MAME) or **inferred**. Nothing derived from the firmware is in the
tree: names are in `run_games_3310/symbols_pairs2.csv`, evidence notes in
`run_games_3310/notes_pairs2.json`; pictures and tables are described, not
copied, and a port reads them from the user's dump at the addresses given.

## Reaching the game and its menus

Runtime. With the exerciser's key names, from idle:

```
enter, enter            wake, open the main menu
up x5, enter            Games: Snake II, Space impact, Bantumi, Pairs II, Settings
down x3, enter          Pairs II title animation (any key skips it)
                        then a list: Time trial (8-4-1), Puzzle (8-4-2)
enter / down, enter     the mode's menu: New game, Level, Top score, Instructions
enter                   New game
```

```
make run-keys GAMES_PRODUCT=3310 RUN_DIR=$PWD/run_pairs2_x SECONDS=40 \
  KEYS=enter,wait1000,enter,wait1200,up,up,up,up,up,wait800,enter,wait1000,down,down,down,wait500,enter,wait1500,enter,wait1000,enter,wait1200,enter,wait8000
```

That opens a Time trial game (insert `down,wait500,` before the third
`enter` from the end for Puzzle). The phone boots in Russian; the runs were
read in Russian, where the list reads На время / Без времени.

- Runtime: during a game `enter` pauses into a menu of Continue, New game,
  Level, Top score, Instructions (8-4-1-1..5). The handler receives `0x34`,
  `0x33`, and `0x35` on Continue.
- Runtime: Level is a page with a 7-step bar (values 1..7). Top score shows
  the mode's own record. Instructions is a scrolled text (Time trial: open
  the pictures to find the pairs, cursor with 2, 4, 6 and 8, open with 5,
  find all pairs before the dynamite's fuse burns down).
- Static: none of 'Last view' (555), '25 seconds' (530), '30 seconds' (531)
  or '5 seconds' (532) appears on these menus or is referenced by the Pairs
  II code; who uses them was not traced.
- The game over note is the framework's (string 578 'Game over!\nYour
  score:\n%N', runtime in Russian: Конец! Набрано N); 576 is inferred to be
  the new-top-score variant.

## Ids 3 and 4: the two modes

- Static: `games_dispatch_2dbd2a` sends ids 3 and 4 to
  `pairs2_handler_2da004`. `games_ctx_load_2dbc7c` sets ctx+0x17 to 0 for
  id 3 and 1 for id 4 (record +0x28 plus 1 for the other games), ctx+0x16 to
  the record's level byte (+4) plus 1, and ctx+0x10 to the record's word +0.
- Static: the handler copies ctx+0x17 to the mode byte (state+0x11) and
  ctx+0x16 to the level byte (state+0x0c). Mode 0 is **Time trial**, mode 1
  **Puzzle**.
- Runtime: the first list entry runs id 3 with ctx+0x17 = 0, the second
  id 4 with ctx+0x17 = 1. Their Top score pages show 1706 and 197 on a fresh
  NVRAM, the PMM dump's records 3 and 4 (see the Space Impact map).
- Each mode therefore has its own record in `games_records_10f9e0`
  (`0x2c` bytes per id): id 3 at `0x10fa64`, id 4 at `0x10fa90`; +2 top
  score, +4 level 0..6 (inferred to be written by the Level page; runtime:
  setting the byte in RAM made the next Puzzle game start at level 1). The
  code of the Level and Top score pages was not traced.

## Event handling and return codes

Static, `pairs2_handler_2da004` and `pairs2_event_2d9ee0`; codes confirmed
at runtime with a breakpoint log of every event and return.

| Event | Handling | Return |
|---|---|---|
| `0x24`, `0x2b` | new game: ctx+0xc = 200, ctx+0x10 = 0, board 0, mode and level from the context, `pairs2_new_game_2d9d2c` | `0x2b`: 1; `0x24`: 2 (only `0x2b` seen) |
| `0x01` tick | `pairs2_tick_2c6740` | `0x21`, `0x16` or `0x18` |
| `0x0b` key 2 | in phase 4: up (`pairs2_cursor_column_2e9f4a(0)`) | `0x21`; 1 outside phase 4 |
| `0x11` key 8 | in phase 4: down (`pairs2_cursor_column_2e9f4a(1)`) | `0x21`; 1 |
| `0x0d` key 4 | in phase 4: left (`pairs2_cursor_row_2e9fca(2)`) | `0x21`; 1 |
| `0x0f` key 6 | in phase 4: right (`pairs2_cursor_row_2e9fca(3)`) | `0x21`; 1 |
| `0x0e` key 5 | in phase 4: open a card, see Rules | `0x21` or `0x1b`; 1 |
| `0x13`, `0x15`, `0x17`, `0x18`, `0x1a`, `0x1c`, `0x1d` | | 5 |
| `0x33`, `0x34` | ctx+4 = `pairs2_state_109190`, ctx+0 = `0x564` | 1 |
| `0x35` | `sprite_engine_init(90)`, then `pairs2_resume_2d9d68` | 2 if the allocation fails, else 1 or `0x18` |
| anything else, key repeats (code + `0x80`) | ignored | 1 |

- Static: the game never uses the one-shot timer (ctx+0xe) or the pending
  return code mechanism of Space Impact. Return `0x16` is used whenever the
  tick period in ctx+0xc changes; `0x1b` plays ctx+0x14.
- Runtime: key repeats arrive as `0x8e`, `0x8f`, ... and return 1; keys
  outside phase 4 return 1.
- Static: suspend (`0x34`) saves nothing extra: the state block is
  self-contained and the sprites are rebuilt on resume.

## State

`pairs2_state_109190`, `0x564` bytes (the size handed back for `0x33`),
multi-byte fields big-endian. Static unless noted; runtime values from the
breakpoint log.

| Offset | Size | Field |
|---:|---:|---|
| +0x000 | u16 | time left, in ticks (Time trial); from `pairs2_board_times_32fed0[board]` |
| +0x002 | u8 | number of cards on the board |
| +0x003 | u8 | phase counter (countdowns, wipe position, explosion step) |
| +0x004 | u8 | fuse divisor: initial time / 25 (2 for board 0, runtime) |
| +0x005 | u8 | fuse top y, from 8 (runtime) |
| +0x006 | u8 | cursor: card index |
| +0x007 | u8 | first card opened |
| +0x008, +0x009 | u8 | special pair to blink (dead code, see below) |
| +0x00a | u8 | cards open: 0, 1, 2 (a non-matching pair is showing); 3 while the cursor is moved by the game |
| +0x00b | u8 | board 0..8 (Time trial) |
| +0x00c | u8 | level 1..7 |
| +0x00d | u8 | phase, below |
| +0x00e | u8 | blink toggle; 2 = off (dead code) |
| +0x011 | u8 | mode: 0 Time trial, 1 Puzzle |
| +0x012 | u8 | 1 while ctx+0xc holds the level's play period (Time trial) |
| +0x013 | u8 | flame frame, toggles every play tick |
| +0x014 | 16 x u8 | wipe strip flags |
| +0x024 | 64 x 20 | card records (at most 60 used) |
| +0x524 | 60 x u8 | card indices in column order, for up and down |

Card record, 20 bytes, at state + `0x24` + 20 * i:

| Offset | Size | Field |
|---:|---:|---|
| +0 | u8 | picture 0..29 (0..n/2-1); `0x21`..`0x23` would be special cards |
| +1 | u8 | 8 on the board; 0..7 removal animation step (Puzzle); 9 gone |
| +2 | u8 | face up (opened or matched) |
| +4, +8 | s32 | current x, y while dealt (starts at 39, 20) |
| +0xc, +0x10 | s32 | board x, y |

Phases (state+0x0d):

| Phase | Mode | Meaning |
|---:|---|---|
| 2 | both | deal: cards fly from (39, 20) to their places |
| 0 | TT | board shown behind the saloon door, 10 ticks |
| 8 | TT | wipe from the saloon picture to the play field, 8 ticks |
| 4 | both | play |
| 5 | TT | time out: explosion, then game over |
| 9 | TT | board cleared: HUD removed |
| 3 | TT | collect animation (moves nothing, 1 tick) |
| 1 | TT | 10 ticks, then the next board or game over |
| 7 | Puzzle | all pairs found, waiting for the last removal animation |
| 6 | | set only by the dead special-card code |

Outside the saved block (static): sprite ids at `pairs2_sprite_ids_1090dc`
(+0 door, +2 flame, +4 background or explosion, +6 dynamite, +8 fuse,
+0xa cursor, +0xc and +0xe the two enlarged pictures, +0x10 eight top and
+0x20 eight bottom wipe strips) and one u16 sprite id per card at
`pairs2_card_sprites_1096f4`.

## Rules

### Dealing

Static, `pairs2_deal_2d9c54(n)`, `pairs2_shuffle_2d9a94`; runtime-checked
on the first board of each mode.

- The deal sets n cards: cards 0..n/2-1 get pictures 0..n/2-1 and so do
  cards n/2..n-1, all on the board (state 8) and face down. It also sets
  phase 2, cursor 0, the time from the board table, the fuse divisor to
  time / 25 and the fuse top to 8.
- The shuffle swaps every card i = 0..n-1, in order, with card
  `game_rand16() % n` (whole 20-byte records). Positions are assigned after
  the shuffle, so only the pictures move.
- Runtime: `game_rand_seed` is 1 after boot and the new game reseeds it only
  when the clock is set (`sprite_engine_reseed_2dd77e`), so in MAME the
  first board is the same in every scripted run (pictures 0, 1, 1, 0 for 4
  cards).

### Layout

Static; runtime-checked pixel positions.

- Time trial: board b uses 10 bytes at `pairs2_board_masks_32fe74` + 10 b,
  one per column c = 0..9, bit r set for a card in row r = 0..4. Cards are
  numbered row by row, left to right, at x = 12 + 7c, y = 1 + 9r. Card
  counts per board (`pairs2_board_counts_32fee4`): 4, 8, 14, 22, 24, 30, 40,
  40, 50. Times (`pairs2_board_times_32fed0`, ticks): 50, 150, 500, 700, 800,
  1000, 1300, 1400, 1600. The shapes are symmetric figures (two pairs of
  cards, frames, stripes, full grid); the masks must be read from the dump.
- Puzzle: a full grid chosen by the level L: 2 x 2 for L = 1, otherwise
  cols = 2 (L - 1) and rows = L / 2 + 2 (integer division): 4, 6, 12, 24,
  32, 50, 60 cards. The grid starts at x0 = 7 ((12 - cols) / 2),
  y0 = 9 ((5 - rows) / 2), plus 4 when rows is even, which centres it;
  card (r, c) at (x0 + 7c, y0 + 9r), numbered row by row. Runtime: level 1
  puts the first card at (35, 13).
- Both: a card is a 7x9 sprite on a 7x9 pitch, so cards touch. Each card
  sprite is created at (39, 20) and flies to its place (below).

### Cursor and keys

Static, `pairs2_cursor_row_2e9fca`, `pairs2_cursor_column_2e9f4a`,
`pairs2_column_order_2e9eb2`; runtime: every key below moved the cursor as
described on a 60-card Puzzle board.

- 4 and 6 step the card index by -1 and +1, wrapping at the ends, skipping
  face-up cards: along a row, into the previous or next row.
- 2 and 8 step through the column list at state+0x524 the same way, skipping
  face-up cards: down a column, from its bottom to the top of the next
  column, and back. The list is built after the layout: start at card 0;
  next is the first card (lowest index) with the same x and a greater y; when
  there is none, the card with the smallest x greater than the current x
  (lowest index among equals); until there is none.
- Every cursor move first closes a non-matching pair that is showing.
- Static: the cursor starts on card 0, which is always face down then.

### Opening cards

Static, `pairs2_open_first_2c6e64`, `pairs2_open_second_2c6d38`,
`pairs2_after_match_2c6ccc`; runtime-verified scoring and sounds.

Key 5 in phase 4, by state+0x0a:

- 0 cards open: if the cursor card is face down, show its enlarged picture,
  mark it face up, remember it as the first card, and move the cursor to the
  next face-down card (as key 6). Now 1 open. Return `0x21`.
- 1 card open: show the second enlarged picture and mark the card face up.
  - Different pictures: 2 open. ctx+0x14 = `0x1e`; the score drops by 1
    unless it is 0. Return `0x1b`.
  - Same pictures: Time trial frees both card sprites (state 9); Puzzle sets
    both to removal step 0. If a face-down card is left, the cursor moves on
    (as key 6) and 0 are open. If not, the board is done: Time trial sets
    phase 9, Puzzle phase 7. Both enlarged pictures are removed.
    ctx+0x14 = `0x1c`; the score rises by level + 4. Return `0x1b`.
  - The card under the cursor is face up or gone: counted as a miss. It
    cannot happen through the keys, which skip such cards.
- 2 cards open (a miss showing): both are closed and the cursor moves on as
  key 6. Return `0x21`.

The non-matching pair stays open until the next key; there is no reveal
timer (static; runtime: the pair stayed open for the remaining 9 ticks of a
board until time ran out).

Runtime, Time trial level 1 board 0, keys 5, 6, 6, 5, 5, 5: score 5 after
the first pair and 10 after the second, sounds `0x1c`, `0x1c`. Puzzle
level 1 the same: 10, then game over. A miss at score 0 stayed 0.

### Time trial timing, time limit and score

Static, `pairs2_tick_2c6740`, `pairs2_fuse_step_2c66ba`; runtime log of a
cleared board 0 and a time-out.

- Outside play the tick is 200 ms. On the first tick of phase 4 ctx+0xc
  becomes the level's period and the handler returns `0x16`: 300, 267, 233,
  200, 167, 133, 100 ms for levels 1..7. Leaving phase 4 sets it back to
  200 (`0x16` again).
- Every later play tick takes one off the time; then, when the time is a
  multiple of the fuse divisor, the fuse top moves down 1 px; the flame frame
  toggles. At 0 the phase becomes 5. Board 0 at level 1 lasts 50 ticks of
  300 ms, 15 s (runtime: period `0x12c`, time 50 counting down one per
  tick, fuse top 8 → 9 at time 48).
- Time out: the explosion picture replaces the play field for 4 ticks
  (two pictures, 2 ticks each), then `0x18`.
- Board cleared (phase 9): next tick the fuse, flame and dynamite go and the
  saloon picture returns; phase 3 lasts one tick; phase 1 counts 10 ticks;
  then, unless this was board 8, the score rises by time left / 2 and the
  next board is dealt. After board 8 the game ends (`0x18`) without that
  bonus. Runtime: board 0 cleared with 26 ticks left took the score from
  10 to 23.
- Static quirks: the end of the phase-1 countdown frees the door's sprite id
  a second time (the door went at the end of phase 0); phase 3 calls the
  deal step, which frees the sprite of every card already in place, all of
  them freed at their match; a branch for a countdown value of 10 after the
  decrement can never run. A port can drop all three.
- Board start: the deal moves every card 1 px per tick on each axis, so it
  takes as many ticks as the largest distance; the tick that finds nothing
  to move starts the 10-tick door countdown, whose last tick removes the
  door and draws the first wipe strips; 7 more wipe ticks, then a tick that
  sets up play. Runtime on board 0: 15 deal ticks, then 10, 8 and 1.

### Puzzle

Static; runtime at level 1.

- No time limit: the tick stays at 200 ms and only drives the removal
  animation. Every tick each card in removal step k < 7 shows frame k of
  `pairs2_removal_frames_31ad60` and advances; at 7 its sprite is freed,
  uncovering the picture behind the board.
- After the last pair (phase 7) the game ends with `0x18` on the tick its
  animation finishes. Runtime: the 8th tick after the last key.
- Score: level + 4 per pair, -1 per miss down to 0. The level only sets the
  grid size.

### Resume

Static, `pairs2_resume_2d9d68`; runtime: Continue from the pause menu
resumes a Time trial board with the time where it stopped.

- Puzzle: the background is recreated. In phase 7 resume returns `0x18`
  at once.
- Time trial: the saloon picture is recreated hidden. In phases 9, 3 and 1
  (between boards) the next board is dealt (or `0x18` after board 8), with
  the time bonus. Otherwise the fuse, flame and dynamite are recreated.
- Both: unless the phase is 5 it becomes 4 (a resume during the deal or the
  wipe skips to play). Cards on the board are recreated at their board
  position on layer 2: face-up ones with their picture (8x11, at the card's
  own x, y, not the enlarged position), the rest face down; cards in a
  removal animation are dropped (state 9). The cursor is recreated. The two
  enlarged-picture sprites are not.

### Dead code

Static: `pairs2_special_pair_2d9cdc` (on boards 2 and later, turn the pair
with picture `game_rand16() % n` into picture `0x21`..`0x23`) and
`pairs2_special_effect_2d9bc6` (`0x21`: phase 6 for 40 ticks; `0x22`: show
every card; `0x23`: 30 ticks more time, at most 150) have no callers and no
pointer to them exists in the image. The open and tick code still checks
for pictures `0x21` and above (blinking pair at state+8/+9). Descriptors
for `0x22` and `0x23` are empty. A port can leave all of it out.

## Drawing

Static; sprite positions and draw modes runtime-checked against frames
(the enlarged picture at (33, 9), the cursor, the fuse). Engine: as Space
Impact, 90 sprites (`sprite_engine_init(0x5a)`); layers draw in order 0..3.
Draw modes as in the Space Impact map (2 flip, 4 opaque, 6 hidden, 1 set,
0 clear-only).

| Sprite | Picture | Size | Mode, layer | Position |
|---|---|---|---|---|
| card | `0x31afc4` (outlined card back) | 7x9 | 4, 1 (2 after resume) | card x, y |
| cursor | `0x31afd0` (filled card) | 7x9 | 2, 2 | cursor card x, y |
| enlarged picture | `0x31adc0` + 12 * picture | 8x11 | 4, 2 | see below |
| removal frames | `0x31ad60` + 12 * k, k 0..6 | 7x9 | the card's sprite | |
| TT saloon | `0x31afac` | 84x48 | 4, 0; hidden (6) during play | 0, 0 |
| TT door | `0x31afa0` | 19x23 | 4, 0 | 32, 17 |
| TT wipe strips | `0x31ad24`, `0x31ad30` | 84x6 | 0, 0 | (0, 6k), (0, 48 - 6k) |
| TT fuse | rectangle sprite | 1 px wide | 1, layer 2 when made at the end of the wipe, 3 when remade | x 4, from the fuse top to y 30 |
| TT flame | `0x31af7c` + 12 * toggle | 9x5 | 1, 0 | 0, fuse top - 5 |
| TT dynamite | `0x31af70` | 9x18 | 4, 2 | 0, 30 |
| TT explosion | `0x31ad48`, then `0x31ad3c` | 84x48 | 4, 2 | 0, 0 |
| Puzzle picture | `0x31afb8` | 84x48 | 4, 0 | 0, 0 |

- The cursor flips the card under it, so the current card is drawn filled;
  on a face-up card's enlarged picture it is not visible because the cursor
  never rests on one.
- Enlarged pictures: the first at (clamp(x, 0, 76), clamp(y - 1, 0, 37)).
  The second likewise, then, if the two would overlap (less than 8 apart in
  x and less than 11 in y), the second is pushed away from the first so they
  just touch: dx = 8 - (x2 - x1) when x2 > x1, (x1 - x2) - 8 when x2 < x1, 0
  when equal, and dy likewise with 11. The pushed position is clamped again;
  whatever the clamp removes is applied to the first picture in the opposite
  direction (`pairs2_show_second_2c6b70`).
- Wipe: on each of 8 ticks strip k = 0..7 is added at y = 6k and its mirror
  at y = 48 - 6k, mode 0, so each strip clears the saloon picture where it
  has clear bits; the tick after the eighth pair removes all 16 strips,
  hides the saloon and creates the fuse, flame, dynamite and cursor on the
  white play field.
- The fuse rectangle is recreated whenever the fuse top changes; runtime: a
  1-px black line at x = 4 from y = fuse top to the dynamite.
- Pictures (`0x31a3d4`..`0x31a5b3`): 34 pictures of 8x11 in the LCD strip
  layout, 16 bytes each, descriptors at `pairs2_pictures_31adc0`
  (12 bytes, index = picture). Pictures 0..29 are dealt; 33 belongs to the
  dead special card; 30..32 are unused.
- Unused: the third flame frame (`0x31af94`) and a third explosion picture
  (`0x31ad54`).
- The game's bitmaps are `0x319fc4`..`0x31ad23` (3424 bytes) and their
  12-byte descriptors `0x31ad24`..`0x31afdb`; the board tables at
  `0x32fe74`..`0x32feec` are 121 bytes.

## Sounds

Static, confirmed at runtime (`sound_play` called as (0, `0xf1`, id) on
return `0x1b` with the games' sounds switched on in RAM).

| Id | Event | Script | Notes, as hertz x timer units |
|---:|---|---|---|
| `0x1c` | pair found | `0x321c94` | 740x10 1480x10 880x21 |
| `0x1e` | miss | `0x321cac` | 523x7 740x7 494x7 698x7 466x7 659x14 |

No other sound, and no vibration.

## Timing

- Static: the handler sets ctx+0xc = 200 at a new game; Puzzle keeps it;
  Time trial switches to the level's period during play (see above).
- Runtime: in Time trial level 1, ticks were 286.5 ms apart during play
  and 193.6 ms outside (35 and 26 intervals measured on LCD writes): 37 and
  25 timer units of 7.74 ms, the unit MAME gives the games (see the Space
  Impact map). The firmware's nominal values are 300 and 200 ms.

## Title screens

Static, confirmed frame by frame at runtime (frames composed from the
listed pictures matched the captured ones exactly, Snake II and Pairs II;
Space Impact and Bantumi from separate title runs).

`games_dispatch_2dbd2a` sends 0x80 + game id to a title handler with the
title context at `0x1111f8`; ids 3 and 4 share Pairs II's. Each handler on
`0x24`/`0x2b` saves ctx+0xc/+0xe (in `games_title_state_110d60` +0x14/+0x16),
sets its period, takes a private sprite pool (`title_sprites_alloc_2dd8f6`,
n sprites) and builds the screen; it counts ticks in `games_title_state_110d60`
(+1 or +2); when it finishes, or on any key (events 4..`0x18`, `0x1a`,
`0x1c`, `0x1d`), it restores the period, frees the pool
(`title_sprites_free_2dd9aa`) and returns `0x10`, which ends the title and
shows the game's menu. Other events return 1.

- **Snake II** (`0x80`, `snake2_title_handler_2d780e`, 6 sprites, 250 ms):
  background `0x318318` (84x48, mode 4) and five hidden frames
  `0x318324`..`0x318354` (about 48x33, at x 6, y 16, 14, 13, 15, 15). Ticks
  1..4 show `0x318330`, `0x31833c`, `0x318348`, `0x318354` in turn, hiding
  the previous one; tick 5 hides the last (the background alone again) and
  shows nothing; tick 6 sets 1200 ms; tick 7 ends. `0x318324` is never
  shown (static: the index is off by one; runtime: it never appears).
- **Space Impact** (`0x81`, `si_title_handler_2d76f6`, 37 sprites, 210 ms):
  a full-screen fill (mode 4), 30 one-pixel stars (`0x3188e4`, mode 3) at
  (`game_rand16() % 84`, `game_rand16() % 48`) after reseeding, a ship
  `0x31889c` (61x9) at (0, 18), hidden `0x3188a8` (53x10) at (31, 18),
  `0x3188b4` (43x10) at (41, 18), `0x3188c0` (18x7) at (50, 19), and the two
  halves of the logo `0x3188cc` (70x13) at (7, 1) and `0x3188d8` (79x13) at
  (3, 32). Ticks 1..8 move the logo halves to y = tick + 1 and 32 - tick;
  ticks 1..5 move the ship to x = 4 * tick; ticks 6, 7, 8 replace it by the
  next of the three hidden pictures. Tick 9 sets 700 ms; tick 10 ends.
- **Bantumi** (`0x82`, `bantumi_title_handler_2d7b3c`, 7 sprites, 250 ms):
  background `0x3185c4` (84x48) and six hidden pictures `0x3185d0`..
  `0x31860c` (7..13 px) at (23, 18), (34, 23), (37, 33), (45, 19), (53, 15),
  (62, 27). Ticks 1..6 show them one at a time, hiding the previous; the
  third stays only 70 ms. After the sixth the sequence plays once more, then
  700 ms, then the title ends. The first frame is the background alone
  (runtime: 14.62 s, the two rounds 14.85..15.90 and 16.13..17.18 s, the menu
  at 18.08 s).
- **Pairs II** (`0x83`, `0x84`, `pairs2_title_handler_2d7974`, 9 sprites,
  200 ms): background `0x318f20` (84x48: two rows of card backs). Ticks 1..8
  add, without removing anything, `0x318f2c` (9x13) at (6, 7), `0x318f38` at
  (3, 1), `0x318f44` at (3, 1), `0x318f50` at (19, 1), `0x318f5c` at (35, 1),
  `0x318f68` at (38, 1), `0x318f74` at (35, 1), `0x318f80` (14x21) at
  (35, 25), turning cards one by one to spell PAIRS II (the jump table in
  `pairs2_title_step_2d786e`). Tick 9 sets 1400 ms; tick 10 ends. Runtime:
  steps 0.19..0.2 s apart, the menu 1.4 s after the last.

Static, from the build routines: Snake II's six sprites and Bantumi's
seven are all on layer 1, Pairs II's nine on layer 0. Space Impact's fill,
stars and the two logo halves are on layer 0 and the ship with its three
later pictures on layer 1, so the ship is drawn over the logo; the stars
are mode 3, cut white out of the fill, and the logo halves, drawn after
them, cover the stars under them. Space Impact's step returns `0x21`
(redraw, same period) for steps 1..8 and `0x16` with 700 ms on step 9;
Snake II's fifth step sets mode 4 on the sprite id stored past its five
frames (state +0x22), which is none of its own: nothing new appears.

Runtime, in the port (`nokia-gb-games/3310`, `core/title.c`): drawing each
title's sprites in this order and stepping them on these periods, every
distinct picture of all four titles appears in order among the frames of
MAME runs that opened the four games from boot, Space Impact's stars
drawn from seed 1 (the clock not being set, the reseed leaves it). The
phone's steps came 0.24 s apart for Snake II (250 ms) and 0.20 s for
Space Impact (210 ms), the menu 1.38 s and 0.70 s after the last step.

All title pictures are mode 4 on layer 0 or 1 unless stated. Bitmaps and
descriptors share `0x317ca8`..`0x318f8b`: Snake II's bitmaps from
`0x317ca8` (descriptors `0x318318`), Bantumi's from `0x318360`
(`0x3185c4`), Space Impact's from `0x318618` (`0x31889c`), Pairs II's from
`0x3188f0` (`0x318f20`).

## Autopilot and longer runs

`mame_nokia_3310_pairs2_bot.lua` plays the game in MAME: it reads the cards
(state + `0x24`, 20 bytes each: picture +0, state +2) and the column list
(state + `0x524`), steers the cursor the shortest way to the other card of
the open one's pair with all four keys, and opens it with 5. Its switches,
from the environment: `P2_LEVEL` (written to both modes' records),
`P2_MISS_EVERY` (open a wrong card every so many pairs), `P2_STOP_BOARD`
(stop playing on that Time trial board, so the time runs out),
`P2_PAUSE_AT` (pause into the menu and Continue once). It logs the
events, returns and sounds as the probe does, and each tick as `TICK` with
its time. It presses a key only once the LCD has shown the last tick's
change and at least 130 ms before the next tick, so that MAME's LCD shows
the tick's change and the key's apart (level 7's 100 ms leaves no such
time); the input exerciser counts the LCD's changes for it in
`nokia_dct3_lcd_dumps`.

Runtime, 968 ticks of a level-1 Time trial game: the LCD showed a tick's
change 0 to 167 ms after the tick, spread evenly, and a key's 30 to 100 ms
after it was pressed (held three frames). A key pressed a fixed time after
the tick could therefore land before the tick's picture and be drawn with
it, which is how the first recordings lost a picture.

Runtime, replayed through the 3310 port's core (`make golden-pairs` there),
every port picture found in order among MAME's:

- Time trial level 1, all nine boards: the deal of every shape, the time
  bonus after boards 0..7 and the game over straight after board 8;
- Time trial level 3, the time run out on board 1: the explosion;
- Time trial level 5, paused in phase 1 after board 1 and continued:
  `0x35` dealt board 2 at once (phase 2, time 500), as the resume code
  reads;
- Puzzle level 5 (32 cards), paused and continued, to the last pair.

After Continue the phone sends the game nothing until a key, which it
then hands the game as well; the autopilot presses one, outside play a
cursor key the game ignores.

Runtime, with the phone in English: the mode list is Time trial (8-4-1)
and Puzzle (8-4-2) and opens on Time trial after the title; Back from a
mode's menu returns to the list with that mode selected, Back from the
list to the Games list on Pairs II. The Level page is Snake II's with seven
bars (4 pixels wide on an 8-pixel pitch, each 2 pixels taller than the
last, with a shadow), its title "Level:" and OK; the menus' items are
8-4-m-1..4 (8-4-m-1..5 with Continue). Top score showed the PMM dump's
1706 for Time trial.

## Not done

- The menus (mode list, Level page, Top score, Instructions, pause menu)
  belong to the framework and were mapped from the screen only; the code
  that writes the Level byte and the top score after a game was not traced.
- What return codes 2 and 5 do in the framework, and when `0x24` rather
  than `0x2b` starts a game.
- No run played Puzzle above level 5 or Time trial at level 7, or resumed
  in phases 9 and 3; those paths are static only.
- `0x2dd97c` (sets a byte of the sprite engine after the deal step) was not
  identified.
- Which code uses strings 530..532 and 555.

## Address map

Pairs II and title names are in `run_games_3310/symbols_pairs2.csv`, notes
in `run_games_3310/notes_pairs2.json`. Framework names come from
`ghidra/symbols/3310.csv`.

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x1090dc` | label | `pairs2_sprite_ids_1090dc` | Sprite ids: +0 door, +2 flame, +4 background/explosion, +6 dynamite, +8 fuse, +0xa cursor, +0xc/+0xe enlarged pictures, +0x10/+0x20 wipe strips |
| `0x109190` | label | `pairs2_state_109190` | State, `0x564` bytes, handed back for `0x33`/`0x34` |
| `0x1096b4` | label | `pairs2_column_order_1096b4` | state+0x524: card indices in column order |
| `0x1096f4` | label | `pairs2_card_sprites_1096f4` | Sprite id per card |
| `0x10fa64` | label | (record 3 of `games_records_10f9e0`) | Time trial record |
| `0x10fa90` | label | (record 4 of `games_records_10f9e0`) | Puzzle record |
| `0x110d60` | label | `games_title_state_110d60` | Title handlers' state: +0 Bantumi second-round flag, +1/+2 step counters, +0x14/+0x16 saved periods, sprite ids |
| `0x1111f8` | label | `title_ctx_1111f8` | Context passed to title handlers |
| `0x2c6478` | function | `pairs2_layout_puzzle_2c6478` | (rows, cols): places a full grid, creates card sprites and the Puzzle picture |
| `0x2c6574` | function | `pairs2_board_puzzle_2c6574` | Grid size from the level; deal, shuffle, layout, column list |
| `0x2c65b2` | function | `pairs2_layout_tt_2c65b2` | Places cards from the board's column masks |
| `0x2c6674` | function | `pairs2_board_tt_2c6674` | Deal, shuffle, layout, column list; saloon and door |
| `0x2c66ba` | function | `pairs2_fuse_step_2c66ba` | Fuse top and flame frame per play tick |
| `0x2c6740` | function | `pairs2_tick_2c6740` | Tick: removal animation, deal, phases, time |
| `0x2c6b36` | function | `pairs2_clamp_x_2c6b36` | clamp(x, 0, 76) |
| `0x2c6b4c` | function | `pairs2_clamp_y_2c6b4c` | clamp(y - 1, 0, 37) |
| `0x2c6b70` | function | `pairs2_show_second_2c6b70` | Second enlarged picture, pushed clear of the first |
| `0x2c6ccc` | function | `pairs2_after_match_2c6ccc` | Next card, or board done (phase 9 / 7) |
| `0x2c6d38` | function | `pairs2_open_second_2c6d38` | Second card: compare, match or miss |
| `0x2c6e28` | function | `pairs2_show_first_2c6e28` | First enlarged picture |
| `0x2c6e64` | function | `pairs2_open_first_2c6e64` | First card |
| `0x2d76f6` | function | `si_title_handler_2d76f6` | Title 0x81 |
| `0x2d7538` | function | `si_title_start_2d7538` | Builds the Space Impact title |
| `0x2d7624` | function | `si_title_step_2d7624` | One Space Impact title step |
| `0x2d7694` | function | `si_title_event_2d7694` | Space Impact title events |
| `0x2d7724` | function | `snake2_title_build_2d7724` | Builds the Snake II title |
| `0x2d77b2` | function | `snake2_title_step_2d77b2` | Snake II title events |
| `0x2d780e` | function | `snake2_title_handler_2d780e` | Title 0x80 |
| `0x2d783c` | function | `pairs2_title_start_2d783c` | Builds the Pairs II title |
| `0x2d786e` | function | `pairs2_title_step_2d786e` | Adds the step's picture |
| `0x2d7904` | function | `pairs2_title_event_2d7904` | Pairs II title events |
| `0x2d7974` | function | `pairs2_title_handler_2d7974` | Titles 0x83 and 0x84 |
| `0x2d79b0` | function | `bantumi_title_create_2d79b0` | Creates the Bantumi title sprites |
| `0x2d7a38` | function | `bantumi_title_init_2d7a38` | Builds the Bantumi title |
| `0x2d7a64` | function | `bantumi_title_step_2d7a64` | Shows the step's picture |
| `0x2d7a9c` | function | `bantumi_title_event_2d7a9c` | Bantumi title events |
| `0x2d7b3c` | function | `bantumi_title_handler_2d7b3c` | Title 0x82 |
| `0x2d9a94` | function | `pairs2_shuffle_2d9a94` | Swap card i with card rand16 % n |
| `0x2d9aea` | function | `pairs2_deal_step_2d9aea` | Moves cards 1 px per axis toward their place |
| `0x2d9ba4` | function | `pairs2_all_face_up_2d9ba4` | 1 when no card is face down |
| `0x2d9bc6` | function | `pairs2_special_effect_2d9bc6` | Dead: special-card effects |
| `0x2d9c54` | function | `pairs2_deal_2d9c54` | (n): pictures, phase 2, time, fuse |
| `0x2d9cdc` | function | `pairs2_special_pair_2d9cdc` | Dead: makes a special pair |
| `0x2d9d2c` | function | `pairs2_new_game_2d9d2c` | Sprite engine, reseed, first board |
| `0x2d9d68` | function | `pairs2_resume_2d9d68` | Event 0x35 |
| `0x2d9ee0` | function | `pairs2_event_2d9ee0` | All events except start |
| `0x2da004` | function | `pairs2_handler_2da004` | Ids 3 and 4 |
| `0x2dd77e` | function | `sprite_engine_reseed_2dd77e` | Reseeds game_rand16 from the clock when it is set |
| `0x2dd8f6` | function | `title_sprites_alloc_2dd8f6` | Private sprite pool for a title |
| `0x2dd9aa` | function | `title_sprites_free_2dd9aa` | Frees it and restores the game pool |
| `0x2e9df4` | function | `pairs2_first_card_2e9df4` | Column list start (card 0) |
| `0x2e9e2a` | function | `pairs2_card_below_2e9e2a` | Next card down the column |
| `0x2e9e6a` | function | `pairs2_next_column_2e9e6a` | Top card of the next column |
| `0x2e9eb2` | function | `pairs2_column_order_2e9eb2` | Builds the column list |
| `0x2e9eea` | function | `pairs2_close_pair_2e9eea` | Closes a non-matching pair |
| `0x2e9f4a` | function | `pairs2_cursor_column_2e9f4a` | Keys 2/8 |
| `0x2e9fca` | function | `pairs2_cursor_row_2e9fca` | Keys 4/6 |
| `0x317ca8` | label | `snake2_title_pictures_317ca8` | Snake II title pictures; descriptors at `0x318318` |
| `0x318360` | label | `bantumi_title_pictures_318360` | Bantumi title pictures; descriptors at `0x3185c4` |
| `0x318618` | label | `si_title_pictures_318618` | Space Impact title pictures; descriptors at `0x31889c` |
| `0x3188f0` | label | `pairs2_title_pictures_3188f0` | Pairs II title pictures; descriptors at `0x318f20` |
| `0x319fc4` | label | `pairs2_pictures_319fc4` | Game pictures, to `0x31a6bf` |
| `0x31ad24` | label | `pairs2_descriptors_31ad24` | Strips, explosion, removal frames |
| `0x31ad60` | label | `pairs2_removal_frames_31ad60` | 8 descriptors, 7x9 |
| `0x31adc0` | label | `pairs2_pictures_31adc0` | 34 card picture descriptors, 8x11 |
| `0x31af70` | label | `pairs2_hud_31af70` | Dynamite, flame frames, door, saloon, Puzzle picture, card back, cursor |
| `0x32fe74` | label | `pairs2_board_masks_32fe74` | 9 x 10 column masks |
| `0x32fed0` | label | `pairs2_board_times_32fed0` | 9 u16 board times, ticks |
| `0x32fee4` | label | `pairs2_board_counts_32fee4` | 9 card counts |
| `0x321c94`, `0x321cac` | label | | Tone scripts of sounds `0x1c`, `0x1e` |
