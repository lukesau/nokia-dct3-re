# Space Impact on the 3410: application map

The Nokia 3410's Space Impact, mapped to re-implement it in C and check the
result against the firmware in MAME. It is the 3310's game
(`games_applications_3310.md`) rebuilt: the same eight levels, now
"chapters", the same movement patterns and objects, on the 3410's graphics
library and a 96 x 65 screen, with its levels kept in a chapter file of the
format the phone can also download. The game is mapped; its re-implementation is checked against MAME.

Addresses apply to one image only: NHM-2 v5.46 with PPM E and the virgin
PMM (`make normalize-3410`). Each conclusion is marked **static** (read from
code or data), **runtime** (seen in MAME) or **inferred**. Nothing derived
from the firmware is in the tree; decompiled text and frames stay under the
ignored `run_games_3410/` and `run_3410_*/`.

## Reaching the game

Runtime. Games, Select game, then Space Impact, the second entry:

```
make run-keys GAMES_PRODUCT=3410 RUN_DIR=$PWD/run_3410_si SECONDS=60 \
  KEYS=enter,wait1500,up,wait300,up,wait300,up,wait300,up,wait1000,enter,wait1500,enter,wait1500,down,wait500,enter,wait5000,enter,wait3000 \
  RUN_EXTRA_ARGS="-autoboot_script $PWD/mame_nokia_3410_games_probe.lua -debug -debugger none"
```

The title ends by itself into the game's menu: New game, High scores,
Chapters (Continue first while a game is paused). The last `enter` starts a
game; another `enter` pauses it.

## Events

Runtime, `si_handler_25c974(event, a, b)` (see `games_applications_3410.md`
for the events all five games share):

| Event | Meaning |
|---:|---|
| `0x00` | timer: the game's tick, about 108 ms apart after New game |
| `0x01`, `0x02` | key down, key up; a = the key's code: 1..9 for the digits |
| `0x03` | pause (Enter during play) |
| `0x07` | boot broadcast |
| `0x09` | a demo, a = 1 to 3 |
| `0x0a` (a = 1) | New game; `0x14` and `0x0c` follow and do nothing |
| `0x0b` | the High scores page, b = the record |
| `0x0d` | Continue: a = 0x5a8, b = the state saved at the pause; it follows a `0x0a` |
| `0x0e` | chosen in Select game: the title |
| `0x11`, `0x12` | a chapter file received, or chosen in the Chapters menu |

Runtime: each digit press arrived as four down/up pairs in a run with the
input exerciser.

Static: events below 3 go to `si_tick_25c274` unless the High scores page
(`0x11ddc6` = 1, `0x259aec`), the demo (`0x11ddca`,
`si_demo_25c6d4`) or another mode (`0x11dded`) is running.

## State

Static. `si_state_11d848`, `0x5a8` bytes, cleared at New game and saved
whole (`0x3b2922(0x5a8, state)`) when the game is paused.

| Offset | Size | Field |
|---:|---:|---|
| +0x000 | 0x34 | terrain layer: +0 tilemap width, +1 rows, +4 tilemap, +8 0 (floor) or 100 (ceiling), +0xc bitmap, +0x10 picture, +0x14 bitmap size, +0x2c tiles |
| +0x03c | u8 | object count, at most 40 |
| +0x03d | u8 | |
| +0x03e | u8 | chapter |
| +0x040 | 5 x u32 | score digit pictures |
| +0x054 | 2 x u32 | special count digit pictures |
| +0x05c | u32 | special weapon icon |
| +0x060 | 5 x u32 | lives (hearts) |
| +0x08c | u8 | beam column |
| +0x090 | 60 x 20 | object records |
| +0x540 | 2 x u8 | vertical play limits |
| +0x544 | 0x14 | the chapter's record (below) and its script position: +0xc the checkpoint, +0x10 entries left, +0x11 ticks to the next entry |
| +0x558 | u8 | phase: 10 playing, `0x14` continue screen, `0x1e` chapter exit, `0x32` game over, `0x3c` the end |
| +0x55a | s16 | scroll position |
| +0x55c | s8 | continue countdown |
| +0x560 | u16 | score |
| +0x562 | u8 | ship destroyed, waiting for its explosion |
| +0x563 | u8 | fire cooldown |
| +0x564 | u8 | repeat-fire count |
| +0x565 | u8 | special key held |
| +0x566 | s8 | lives, start 3 |
| +0x567 | u8 | shot type (4) |
| +0x568 | u8 | special weapon: 6 wall, 7 missile, 8 beam; 3 walls at New game and after a continue |
| +0x569 | s8 | special count, start 3 |
| +0x56c | u32 | the ship's picture |
| +0x570 | u8 | the shield's object, `0xff` when none |
| +0x574 | u8 | the ship's object |
| +0x588 | 0x1c | the high-score record |

Object record, 20 bytes, at state + `0x90` + n * 20, copied from a template
at spawn:

| Offset | Field |
|---:|---|
| +0 | frame count |
| +1 | current frame |
| +2 | type; `0x7f` marks a free record |
| +3 | hit points |
| +4 | movement pattern |
| +5 | pattern argument, the speed |
| +6 | fire chance |
| +8 | u32 picture |
| +0xc, +0xd | x, y saved at pause |
| +0xe | 1 for boss projectiles |
| +0xf | side: `0x0a` for the player's |
| +0x10 | 1 for a boss |

## Chapter file

Static. The built-in chapters are a file of 3113 bytes at `0x49f3e0`, in
the format the phone accepts for downloaded chapters. New game copies it to
RAM and `si_chapters_parse_35cf30` builds `si_chapters_11ddf0` from it.
Numbers are big-endian except where noted.

| Part | Content |
|---|---|
| header | u8 n, n x u16; u32; u8; u8 flags; u8 |
| flags | bit 0 chapters, bit 1 terrain tiles, bit 2 tilemaps, bit 3 chapter settings, bit 4 the file's own pictures (else the phone's 34 at `0x4c1ae4`) |
| tile sets | u8 count, then each set's number of tiles |
| chapters | u8 count (at most 16), then each chapter's number of spawn entries |
| tilemaps | two u16 (little-endian), u8 count, then each map's width and rows |
| chapter records | 6 bytes each: entries, four bytes, polarity (`0x12` or `0x20`, the draw mode) |
| tiles | 32 bytes each (32 x 8 in the LCD's layout) |
| tilemap data | width x rows tile numbers each, 0 for none |
| spawn scripts | 9 bytes an entry |
| chapter settings | 9 bytes each |

The built-in file has flags `0x0f`: eight chapters with 20, 24, 23, 20, 19,
38, 28 and 6 spawn entries (the 3310's levels have 20, 23, 23, 20, 19, 40,
28 and 6), tile sets of 3, 4, 4, 4, 4, 4, 6 and 5 tiles, and eight 16 x 2
tilemaps. Chapter 0 has no terrain; chapters 4 and 5 have it on the
ceiling. The polarity is `0x12` for chapters 0, 4 and 5, `0x20` for the
rest.

Spawn entry (static, `si_spawn_step_25a3f4`):

| Byte | Field |
|---:|---|
| 0 | group size |
| 1 | object type |
| 2 | x spacing between group members |
| 3 | pattern argument (speed) |
| 4 | movement pattern |
| 5 | ticks to wait before the next entry |
| 6 | row; `0x3f` a random one |
| 7 | fire chance |
| 8 | hit points |

The patterns are the 3310's numbers (1, 2, 4, 6, 7, 10..18, 23 for bosses,
24). Types below 20 are the game's own (templates at `0x4ace3c`); 20 and
up are the enemies.

## Pictures

Static, runtime (read from RAM in a game). `si_tables_11d7a0` +0x14 points
to `si_type_pictures_12a120`, by object type, each a 24-byte descriptor
{u16 width, u16 height, u16 0, u16 frames, u32 bitmap, ...} in the
3410's format. Types 0..7 are the game's own: 0 the ship (10 x 7), 1
(13 x 11), 2 (7 x 7), 3 (8 x 7), 4 and 5 (2 x 1, the shots), 6 (5 x 5),
7 (5 x 3). Types 20..53 are the enemies from the chapter file's table
(the phone's own, `0x4c1ae4`, when the file has no pictures): their sizes
are the 3310's, the final boss 38 x 38 (type 44); types 45..53 are not
spawned by the built-in chapters. The bitmaps lie at `0x490004`..`0x4916e3`
in the LCD's band layout.

The HUD (static, `si_hud_create_259030`): the top and bottom bars
(`0x4ac1d8`, `0x4ac1a8`, only on a 96-column screen), a heart per life
(`0x490104`), digits (`0x4901a4`) for the score and the special count, and
the special weapon's icon: missile `0x490134`, wall `0x49014c`, beam
`0x490164`.

y paths (static): `si_tables_11d7a0` +0x1c..+0x2c and +0x44 point at
tables chosen by the screen's width: `0x4ad094`, `0x4ad268`, `0x4ad214`, `0x4ad0f4`, `0x4ad154` and the relative wave
`0x4ad1b4`; the second and third are the 84-column rise and fall, which on
96 columns `0x4ad31c` (rise) and `0x4ad2bc` (fall) replace.

## Draw modes

Static. The game draws through the 3410's graphics library: pictures are
objects in a tree (type 4 an animated bitmap, with its frame list at
+0x10, frame count +0x18 and frame +0x1a; type 2 a line; types 5..8
other shapes, the full-screen fill among them), each with a 16-bit draw
mode at +2 (`0x3daad6` sets it). The renderer around `0x3602ae` (Thumb
code Ghidra had not made a function of; found with a read watchpoint on
the ship's mode in MAME) skips an object whose mode is 0 and otherwise
calls `0x365780` with the mode, which `0x3652c0` turns into an operation:
the high nibble 1 or 2 gives 1 or 2 and any other gives 0, nothing drawn;
a low nibble of 2 gives 4 whatever the high nibble, 1 adds `0x10` and 4
adds `0x20` (the latter also marks the drawn rows in the LCD's blink
plane). The phone's blitter `0x2828b0` then combines the picture's bits
with the screen by the operation (masked with `0x5f`):

| Operation | Pixels |
|---:|---|
| 1 | copy: set bits set, clear bits clear |
| 2 | or: set bits set, clear bits leave |
| 4, `0x11`, `0x18` | xor: set bits flip |
| 8 | and: clear bits clear, set bits leave |
| `0x40` | set bits clear |
| 0 | nothing |

So the game's modes are:

| Mode | Use | Draws as |
|---:|---|---|
| `0x10` | the full-screen fill of `0x12` chapters; a boss, set after every step (`0x25ad28`) | copy (the 3310's mode 4) |
| `0x12` | everything in chapters 0, 4 and 5, the HUD | xor (the 3310's mode 2) |
| `0x20` | everything in the other chapters | or (the 3310's mode 1) |
| `0x30` | the shield in `0x20` chapters | nothing |
| 0 | hidden (a hit flash, a spent icon) | nothing |

Runtime: chapter 0's boss (type 31, 20 x 23) is stored with its
background set and its outline clear, so drawn by copy on the black fill
it shows as a white outline with no box, as MAME's frames show it.

The chapter record's last byte is that mode; it is the 3310's level
polarity re-expressed: 2 there is `0x12` here, 1 is `0x20`.

## Draw order

Static, runtime. Every picture of the game is a child of one object, the
screen root at `0x12d2c4` (`0x3fa0bc` returns it; +0 child count, +4 first
child, +8 last). A child has +4 its parent, +8 the next sibling and +0xc
the previous; the renderer draws the list from the first child to the
last, each over what is there.

- Creating a picture (`0x3f0948(parent, mode, &pos, frames, count)`)
  appends it: `0x3d64e2` inserts it after the parent's last child.
- `0x3daa22(object, 0, after)` moves an object to just after `after`, or
  to the head when `after` is 0 (`0x3d63ea`). The game moves the
  full-screen fill to the head (`si_tick_25c274`, every tick), and the
  boss to just after the fill, or to the head when there is none; so the
  boss is drawn under everything but the fill.
- Freeing a picture (`0x3dac10`) unlinks it; a new object made in a freed
  record is appended at the end, not put back where the old one was.

Runtime, the list in chapter 0 a few seconds into a game (RAM dump):

| # | Object | Mode |
|---:|---|---|
| 0 | the full-screen fill (type 7, 96 x 65) | `0x10` |
| 1 | the terrain picture (its descriptor is state +0x14), at (0, 38) | `0x12` |
| 2, 3 | the top bar at (0, 0), the bottom bar at (0, 54) | `0x12` |
| 4..8 | the hearts at x 16, 22, 28, 34, 40, y 3; those beyond the lives in mode 0 | `0x12` |
| 9..13 | the score's digits at x 56, 60, 64, 68, 72, y 2 | `0x12` |
| 14..16 | the special weapon's icon at (40, 58), its count's digits at x 51, 55, y 58 | `0x12` |
| 17.. | the game's objects, in the order they were made | `0x12` |

A digit is changed by giving its picture another descriptor (the digits'
descriptors are 24 bytes apart from `0x4901a4`), not by drawing it again.

## Movement patterns

Static: the switch in `si_objects_step_25b750` is a jump table at
`0x25b7d0` of 24 cases (the decompiler stops at it; the cases were read
from a listing). r4 is the object, r6 its speed (+5).

| Pattern | Code | 3310 counterpart |
|---:|---|---|
| 1 | path `+0x1c`, `0x25af08(obj, speed, 0, 0x12)` | path, wave_abs |
| 2 | path `+0x28`, as 1 | descend |
| 3 | `0x25b37c` | track the ship |
| 4 | path `+0x2c`, as 1 | climb |
| 5 | `0x25b34c` | right (player shots) |
| 6 | `0x25b318` | left |
| 7 | `0x25b1c4` | dive |
| 9 | `0x25b0f0` | missile |
| 10..13 | relative wave, `0x25af08(obj, speed, 0x80, 0x23 / 0xb / 0xe / 0x19)` | wave_rel plus 35, 11, 14, 25 |
| 14 | relative wave plus 18 | the same |
| 15, 16 | path `+0x20`, `+0x24` | rise, fall |
| 17, 18 | `0x25ae30(obj, speed, 100 / 0)` | ceiling, floor |
| 23 | `0x25ad28` | boss |
| 24 | inline: bounce at the right, then pattern 3 with speed 1 | the same |

Patterns 8 and 19..22 do nothing, as on the 3310.

## Sounds and the vibrator

Static, runtime. The game asks for a sound with `0x3b2510(id)`, which
plays it when the games' sounds are on (`0x3f7ebe`). `0x3f7d0e` looks the
id up in the halfwords at `0x4c3538` and posts the value to the tone task
(`0x2aacdc`, message `0xf1`), which indexes the sound table from
`0x4a9060` (`0x3e57d0`): three records before `0x4a9078`, so the value
less 3 is the record. The ids come out as the 3310's sounds renumbered
(the 3310's `0x17`..`0x1a` are the 3410's `0x13`..`0x16`; from `0x1e` on
the tables agree):

| Id | Value | Record | When |
|---|---|---|---|
| `0xfa0` | `0x22` | `0x1f` | a bonus picked up (`0x25b418`); Snake II's meal |
| `0xfa1` | `0x23` | `0x20` | Snake II's death |
| `0xfa2` | `0x24` | `0x21` | the game-over picture (`0x25c484`) |
| `0xfa4` | `0x26` | `0x23` | the same, the score not below the top score (`0x25c48c`) |
| `0xfa5` | `0x17` | `0x14` | a shot (`0x25a2be`) |
| `0xfa6` | `0x18` | `0x15` | a wall or a missile (`0x25a3c6`) |
| `0xfa7` | `0x16` | `0x13` | the ship lost, to the terrain or a hit (`0x25bd7e`, `0x25be1c`) |
| `0xfa8` | `0x19` | `0x16` | the beam (`0x25a3c6`) |

In the demo (`0x11ddca` set) the handler fires from a key going down
instead (`0x259d30`), with the same three sounds; in play only the held
keys' poll (`0x25a110`) fires.

`0x3b25d4(1)` turns the vibrator on when the ship is lost, a shield is
hit and a boss is destroyed, if the byte at `0x11ddc5` is 0, and sets it
to 3; each tick counts it down and
turns the vibrator off at 0 (`0x25c3a2`). The continue screen turns it off
too (`0x258c58`).

## Instructions

Runtime, around the game: the games framework that shows the pages is not
traced. Instructions shows four texts (1962..1965) a page of four lines at
a time. More, or Down, past the last page of each of the first three
starts its demo (event 9 with a = 1, 2, 3; `games_si_3410_functions.md`,
"Demos"); the demo runs full screen and the page stays up until its first
tick, since the start draws nothing. When a demo closes the game, or at any
key during it (the framework sends event 3, a pause, not a key), the next
text follows; C goes back to the game's menu with Instructions selected.
The fourth text ("... to download new chapters.") has Exit and no More:
Navi does nothing there, Down and Up page. Up and Down page within a text
too. Up during a demo was once seen to be ignored and a second Up to end
it; not looked into.

`make golden-si-demos` records the three demos, each to its end, into
`golden/si-i`; the re-implementation's frames and sounds match all of
them, and those of demos cut short by Navi, C, 8 and Up.

## Recording games

Runtime. `mame_nokia_3410_si_bot.lua` plays the game with the phone's
keys and logs what a replay needs: every call of `si_handler_25c974` with
its event, arguments, cycle count and the ANSI generator's state
(`SIEV`), the tick period it sets (`SIPER`, `0x3b2546`), the sounds it asks
for (`SISND`, `0x3b2510`) and the vibrator (`SIVIB`, `0x3b25d4`). It steers
the ship toward the row of the nearest enemy ahead by holding 8 or 0 and
fires with 1, with switches for the special weapon, a pause, continuing,
and standing still without firing. The game polls the keys it holds every
tick (`0x3b29d0`) as well as taking their events, so the bot presses real
keys rather than writing the game's state.

The game is deterministic in MAME: two runs of the same recording gave
the same events, generator states and LCD frames, all 1051 of them. The
generator is 0x87991a45 at New game after the title and menus.

`make golden-si` in nokia-gb-games/3410 records four games into its ignored
`golden/si-*` and turns each log into `events.txt` and `sounds.txt`, the
sound and vibrator calls by event (`tools/si_events.py`):
a, two minutes on through the continues; b, the special weapon three times
and a pause; c, the ship left where it starts without firing, through the
continue screen's countdown to the game-over picture; d, 22 minutes with
`SI_IMMORTAL=1`, which sets the lives back to 3 at the handler's second
instruction whenever one is lost (logged as `SIPOKE`, made again by the
replay before the same event), so that it plays through all eight
chapters and beats the final boss, at whose middle the autopilot aims.

## Re-implementation

`nokia-gb-games/3410/core/si.c` re-implements the game function by function
(every function of `0x2589d0`..`0x25c974` paired with its 3310 counterpart
in `games_si_3410_functions.md`, with collisions, bosses, the continue
screen, the chapter settings, sounds, timing and the generator's draws),
and `core/si_pic.c` the part of the graphics library it draws with. Its
`make check-golden` replays the recorded games: four, the longest 22 minutes
through all eight chapters, the final boss, the flight off and the game-over
picture, match MAME's frames, every one in order. What the replays showed
that reading the code had not:

- the game polls the held keys in play (`0x3b29d0`, a byte per key code
  from `0x12d298`), which the keyboard interrupt can change after the
  handler was entered: the autopilot logs them as polled (`SIKEYS`);
- the shield of the chapters drawn with `0x20` is drawn, in mode `0x30`;
- a picture starting in the screen's last column or row is not drawn, one
  partly off the left or right edge otherwise is;
- leaving a chapter, the ship is judged off the screen (x > 116) by where it
  was before its step;
- part of an object left of the screen reads the terrain's bitmap from
  before its row, and from before the bitmap the heap's own bytes, which a
  big-endian block size of 0xc8 (192 bytes and an 8-byte header) fits
  (inferred: a bullet at x -1 beside the terrain is taken on bit 3 of the
  byte before the bitmap, a projectile there is not on bits 0 and 1);
- the game-over picture's score box is Snake II's pieces (two 6x12 ends,
  6x8 digits 8 apart, inverted) in a 51 x 12 box at (23, 26).

The replays' sound and vibrator calls equal the phone's in every recorded
game, the last call of each event, and so do they in a 150 s game with the
special weapon's key held 13 times, long enough for the poll to see it
(three walls or missiles and a beam fired before the specials ran out).

## Not done

The framework around the game: the Instructions' pages, measured above.
