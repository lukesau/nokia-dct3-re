# Space Impact on the 3310: application map

The Nokia 3310 Games menu offers Snake II, Space Impact, Bantumi and
Pairs II. This document maps Space Impact and the layers it sits on, to the
level needed to re-implement the game and check the result frame for frame
against the firmware in MAME. It is the 3310 counterpart of
`games_applications.md` and follows its conventions. The other three games
have their own maps: `games_snake2_3310.md`, `games_bantumi_3310.md` and
`games_pairs2_3310.md`, the last with the four title screens.

Addresses apply to one image only: NHM-5 v6.39 with PPM E and the v.2 PMM,
2 MiB at flash base `0x200000`.

| | |
|---|---|
| SHA-256 | `975ec791205f026d647254ee772d7fa32691fa50c72a68eecdaff7c8a5921442` |
| SHA-1 | `d5da65f417595200314eb0115bf46ca1fbf53128` |

Each conclusion is marked **static** (read from code or data), **runtime**
(seen in MAME) or **inferred**. Nothing derived from the firmware is in the
tree: names live in `ghidra/symbols/3310.csv`, evidence notes in
`docs/data/games_function_notes_3310.json`, and decompiled text stays under
the ignored `run_games_3310/`.

## Reaching the game

Runtime. The UI takes keys from 6 s after boot; the first key only wakes it.
From idle, with the exerciser's key names:

```
enter, enter            wake, open the main menu (Phone book)
up x5                   Games is entry 8; the menu wraps
enter                   Games list: Snake II, Space impact, Bantumi, Pairs II, Settings
down, enter             Space impact title animation
enter                   skips the title and starts a new game
```

The title also ends on its own into a menu (New game, Top score,
Instructions). In the game, `enter` pauses into that menu with Continue
first. The game runs on this image without any driver or NV change.

```
make run-keys GAMES_PRODUCT=3310 RUN_DIR=run_3310 SECONDS=40 \
  KEYS=enter,wait1000,enter,wait1200,up,up,up,up,up,wait800,enter,wait1500,down,wait600,enter,wait2500,enter,wait4000
```

The game starts at 17.6 s on that timeline and its first tick is at 17.8 s.

## Dispatch and event interface

Static, with the event codes confirmed at runtime.

`games_table_33016c` has five 16-byte records `{four parameter bytes, Thumb
handler, text pointer, u16 flags, u16 0}`. Unlike the 3210's table, every
record names the same handler, `games_app_handler_2dbdd4`; the game is chosen
by `games_dispatch_2dbd2a(game id, event)`, a compare chain with direct
calls:

| Id | Handler | Game |
|---:|---|---|
| 0 | `snake2_handler_275aa4` | Snake II |
| 1 | `si_handler_25a52a` | Space Impact |
| 2 | `bantumi_handler_2b2398` | Bantumi |
| 3, 4 | `pairs2_handler_2da004` | Pairs II: 3 Time trial, 4 Puzzle, each with its own record |
| 0x80..0x84 | `0x2d780e`, `si_title_handler_2d76f6`, `0x2d7b3c`, `0x2d7974` (0x83 and 0x84) | the games' title screens, in the same order |

The id is `games_current_id_11fd57`. Handlers are called as
`handler(event, ctx)` with `game_ctx_111218` for the games and a second
context at `0x1111f8` for the titles.

`games_app_handler` receives the same outer events as the 3210 games (`0x49`
init, `0x54` tick, `0x55` start or resume, `0x56` suspend, `0x57` draw, keys
as ASCII) and translates them to a game event code:

| Game event | Meaning |
|---:|---|
| `0x00` | one-shot timer expired |
| `0x01` | tick |
| `0x04`, `0x05` | scroll down, scroll up |
| `0x09` | key `0` |
| `0x0a`..`0x12` | keys `1`..`9` |
| `0x14`, `0x16` | `#`, `*` |
| code + `0x80` | key repeat, sent every 12 timer units while the key is held |
| `0x24`, `0x2b` | start a new game |
| `0x33` | state query: handler stores its state address at ctx+4 and size at ctx+0 |
| `0x34` | suspend: as `0x33`, after saving what a resume needs |
| `0x35` | resume |

Snake II decodes the same key codes, which confirms the enumeration
independently of Space Impact.

Context fields the game uses:

| Offset | Size | Use |
|---:|---:|---|
| +0x0c | u16 | tick period in ms |
| +0x0e | u16 | one-shot delay in ms |
| +0x10 | u32 | score handed back at game over |
| +0x14 | u16 | sound to play |

The handler's return value tells the framework what to do next:

| Return | Effect |
|---:|---|
| `0x01` | nothing; no redraw |
| `0x21` | redraw; re-arm the tick if the event was a tick |
| `0x13` | restart the tick and the one-shot timer from ctx+0xc and ctx+0xe |
| `0x16` | restart the tick with the period now in ctx+0xc |
| `0x1b` | play sound ctx+0x14 if game sounds are on, then as `0x21` |
| `0x18` | game over: post message `0x5133`; the score is in ctx+0x10 |
| `0x1f` | restart the one-shot timer from ctx+0xe, play sound ctx+0x14 if game sounds are on, re-arm the tick (Snake II's death; see `games_snake2_3310.md`) |
| `0x20` | as `0x1f` without the sound |
| `0x05` | returned for events `0x13`, `0x15`, `0x17`, `0x18`, `0x1a`, `0x1c`, `0x1d`; meaning not traced |

## Timing

- Static: the tick period is the constant 100 in ctx+0xc during play, and
  800 on the continue screen. It does not change with level.
- Static: the framework converts milliseconds to timer units by dividing by
  7.96875 (255/32) and dropping the fraction: 100 ms is 12 units, the
  3000 ms shield 376. The key-repeat timer is 12 units. A timer is
  restarted when its event has been handled.
- Runtime: ticks arrive 92.9 ms apart in MAME (225 of 239 intervals at 93 ms,
  the rest 91..96), measured on writes to the scroll position, which makes
  a unit 7.74 ms there. The first one-shot event of a game comes between
  ticks 32 and 33 and the next 31 ticks later, as 376 units predicts.
- Static: a key press plays a sound through a pending return code
  (state+0x2b). The handler returns a pending code before it looks at the
  event, so when a code was left by a tick (a collision sound) the next
  event is consumed returning it. If that event is a tick, no game step
  runs for it. A re-implementation must reproduce this to stay in step.

## One tick

Static, from `si_event_25a200` in phase 10 (playing):

1. `tilemap_render(state, scroll)` draws the terrain.
2. The scroll position advances by 1 px, modulo 512, while the level script
   still has entries and its delay counter is running. It stops for the
   boss. Level 7 scrolls on until the final boss appears.
3. `si_spawn_step` runs the level script.
4. `si_objects_step` animates and moves every object.
5. `si_collisions` resolves hits.
6. The fire cooldown advances: a shot blocks firing for two ticks.

Everything is in screen pixels on the 84x48 display. Objects move in whole
pixels per tick. The logic is tied to the screen size throughout: spawn at
x = 84, free at x = 0, y-path tables of 84 entries indexed by x.

## State

`si_state_109ec4`, `0x34c` bytes, multi-byte fields big-endian in memory.
Static unless noted; the values in the last column were read from a RAM
dump during level 0.

| Offset | Size | Field | Level 0 |
|---:|---:|---|---|
| +0x000 | 0x24 | terrain layer: +0 width in tiles (16), +1 rows (2), +4 tilemap, +8 top flag (0 or `0x2b`), +0xc bitmap, +0x10 sprite id, +0x14 sprite descriptor, +0x20 tile pointers | |
| +0x024 | u16 | terrain sprite id | 15 |
| +0x026 | u16 | background fill sprite; also a countdown in level 7 | |
| +0x028 | u16 | beam sprite id | |
| +0x02a | u8 | object count, capped at 40 | |
| +0x02b | u8 | pending return code | |
| +0x02c | u8 | level, 0..7 | 0 |
| +0x02e | u16 | first score digit sprite | 10 |
| +0x030 | u16 | first special-count digit sprite | 8 |
| +0x032 | u16 | special icon sprite | 7 |
| +0x034 | 5 x u16 | life icon sprites | 2..6 |
| +0x046 | u8 | beam column, 0 when no beam | |
| +0x047 | u8 | boss state | |
| +0x048 | 60 x 12 | object records, indexed by sprite id | |
| +0x318 | u8, u8 | vertical play limits | 32, 6 |
| +0x31c | 16 | working copy of the level header | |
| +0x328 | u8 | checkpoint: spawns remaining when it was passed | |
| +0x329 | u8 | level polarity, 1 or 2 | 2 |
| +0x32a | u8 | spawn entries remaining | |
| +0x32b | u8 | ticks until the next spawn entry | |
| +0x32c | u8 | phase: 10 playing, `0x14` continue screen, `0x1e` level exit | 10 |
| +0x32e | u16 | scroll position, 0..511 | |
| +0x330 | s8 | continue countdown, from 5 | |
| +0x332 | 2 x u16 | final boss part sprites | |
| +0x336 | u16 | boss sprite id | |
| +0x338 | u32 | score | |
| +0x33c | u8 | ship destroyed, waiting for its explosion | |
| +0x33d | u8 | fire cooldown | |
| +0x33e | u8 | repeat-fire count, capped at 5 | |
| +0x33f | s8 | lives, start 3, at most 5 | 3 |
| +0x340 | u8 | shot type (1) | 1 |
| +0x341 | u8 | special weapon: 10 missile, 9 wall, `0x16` beam | 10 |
| +0x342 | s8 | special count, start 3 | 3 |
| +0x344 | u16 | ship sprite id | 16 |
| +0x346 | u16 | shield sprite id, 0 when off | 17 |
| +0x348 | u16 | missile target | |
| +0x34a | s8 | continues counter, start 4 | 4 |
| +0x34b | u8 | level-exit step | |

Object record, 12 bytes, at state + `0x48` + id * 12:

| Offset | Field |
|---:|---|
| +0 | frame count |
| +1 | current frame |
| +2 | type; `0x32` marks a free record |
| +3 | hit points |
| +4 | shots left |
| +5 | movement pattern |
| +6 | pattern argument, the speed in px per tick for most patterns |
| +7 | fire chance: fires with probability 1/N; 0 and `0x7f` never |
| +8, +9 | x, y saved at suspend |
| +10 | 1 for boss projectiles, which give no score |

Positions are not in the record. They live in the sprite engine.

## Sprite engine

Static. Shared by the games; `sprite_engine_111af0` points at a heap array
of `0x1c`-byte sprites linked in draw order (allocated per game, 60 for
Space Impact, freed on suspend).

| Offset | Field |
|---:|---|
| +0x00 | u16 next sprite id, 0 ends the list |
| +0x02 | flags: bits 0..2 kind (0 bitmap, 1 rectangle, 2 fill), bits 3..5 draw mode, bits 6..7 layer |
| +0x04, +0x05 | x, y |
| +0x08, +0x09 | previous x, y |
| +0x0c | 12-byte image descriptor: u32 bitmap pointer, u32 0, u8 width, u8 height, u16 0 |
| +0x18 | dirty flags |

Bitmaps are in the LCD's native layout: bands of 8 rows, one byte per
column, bit 0 the top row of the band. The byte for pixel (x, y) is
`bitmap[width * (y >> 3) + x]`, bit `y & 7`. No word packing or shifting is
involved, so the format is byte-order neutral.

`sprite_render_2dfd88` erases and redraws only what moved, marking every
sprite that overlaps a redrawn one, so the result is the list drawn in
order onto a cleared screen. The draw mode chooses the pixel operation for
a bitmap's set bits and for its clear bits (static):

| Mode | Set bits | Clear bits |
|---:|---|---|
| 0 | leave | clear |
| 1 | set | leave |
| 2 | flip | leave |
| 3 | clear | set |
| 4 | set | clear |
| 5 | set | clear, and marked in the blink plane |
| 6, 7 | not drawn | |

A sprite whose right or bottom edge has wrapped past 255 is not drawn.

The level polarity (state+0x329) is used directly as the draw mode of the
game's objects: polarity 2 levels put a full-screen fill sprite (mode 4)
behind everything and flip the sprites out of it, polarity 1 levels set
them on a clear screen. The HUD is always mode 2. Pixel-exact collision
tests read the bitmaps with the matching sense.

## Player

Static; key names confirmed at runtime.

| Keys | Event | Action |
|---|---|---|
| `8` | `0x11` | up 1 px; 2 px per repeat |
| `0` | `0x09` | down |
| `*` | `0x16` | left, not past x = 1 |
| `#` | `0x14` | right, not past x = 73 |
| `1`, `3` | `0x0a`, `0x0c` | fire a shot (type 1) from (x + 6, y + 3); sound `0x18` |
| `4`, `6` | `0x0d`, `0x0f` | use the special weapon if any are left |

Keys `2`, `5`, `7`, `9` and the scroll keys reach the handler and are
ignored. These are the labels of the fork's 3310 keypad matrix, which types
the right digits at idle; they have not been compared with a real phone.

- The ship is 10x7 and starts at (5, 20). With ground terrain y runs from 6
  to 41; in levels 4 and 5, where the terrain is on the ceiling, from 1
  to 35.
- A new or respawned ship has a shield (type 8) for the one-shot delay:
  3000 ms, or 1500 ms after a resume. Event 0 removes it.
- Shots travel right at 2 px per tick. Holding fire repeats, at most 5
  repeats per press.
- Special weapons: missile (type 10, homes on the enemy with the most hit
  points, 2 px per tick), wall (type 9, an expanding 7-frame burst attached
  to the ship, takes 4 hit points per hit), beam (type `0x16`, a full-height
  rectangle sweeping right 2 px per tick; within 3 px of its column it
  destroys ordinary enemies and takes 2 hit points from a boss). The game
  starts with 3 missiles.
- Bonus pickup (type `0x11`): `game_rand16() & 3` chooses an extra life
  (re-rolled at 5 lives), missiles, walls or the beam. Picking the weapon
  already held adds 3 (beam: 1); a different one replaces it with 3
  (beam: 1). Type `0x21` adds 3 to the special count.
- Losing the ship: explosion, then one life less and a respawn. At zero
  lives the continues counter is checked: at 2 or more it drops by one and
  the continue screen counts down from 5 at 800 ms per step. Keys 1, 3, 4
  or 6 restart the level with 3 lives and 3 missiles. Otherwise the game
  ends with return `0x18`. The level restarts from its beginning: the
  checkpoint byte is recorded as the script runs, but the reload clears it
  before it is read.

## Levels

Static. Levels are data. There are 8, indexed 0..7 by state+0x2c.

Level header, 16 bytes, at `si_level_headers_312084` + 16 * level, reached
through `si_level_table_10a2a4` (ROM image `si_level_table_init_2f30d4`):

| Offset | Field |
|---:|---|
| +0 | number of spawn entries |
| +4 | u32 pointer to the spawn list |
| +8..+11 | checkpoints, as a count of entries consumed (4, 0, 0, 0 in every level) |
| +13 | polarity: 2 for levels 0, 4, 5; 1 for the rest |

Spawn entry, 12 bytes, in `si_spawn_lists_311820`:

| Offset | Field |
|---:|---|
| +0 | group size |
| +1 | object type |
| +2 | x spacing between group members |
| +3 | pattern argument |
| +4 | movement pattern |
| +5 | ticks to wait before the next entry |
| +6 | y; `0x3f` picks a random row with `rand_2f1b44` |
| +7 | fire chance |
| +8 | shots |
| +9 | hit points |

Group members appear at x = 84 + n * spacing, or at x = -n * spacing for
pattern 5. Entry counts are 20, 23, 23, 20, 19, 40, 28, 6; the last entry of
each level is its boss with pattern 23. The last two of level 5's 40
entries are empty.

A level ends when its boss is destroyed (`si_boss_destroyed_2593a4`, +100):
phase `0x1e` lines the ship up, flies it off to the right, and loads the
next header. After level 7 the handler returns `0x18`, the same as game
over. Level 7's boss (type `0x22`, 38x38, with two type `0x23` parts) is
not spawned by the script but by `si_final_boss_spawn_258400` at scroll
positions `0x7a`, `0x13a` and `0x1ba`.

Terrain: `si_level_tilemaps_109ea0[level]` gives a 32-byte map, 2 rows of
16 tile ids, each tile 32x8, so the terrain is 512 px long and wraps.
`si_level_tilesets_109e68[level]` gives the tile pointers. The layer sits at
the bottom of the screen except in levels 4 and 5. Level 0's map is empty.

Movement patterns, the switch at `0x259718` in `si_objects_step_2596a0`:

| Pattern | Function | Motion |
|---:|---|---|
| 1 | `si_move_path_258d8e` | left; y from `si_ypath_wave_abs_312104` |
| 2 | `si_move_descend_25924c` | left, descending between x 29 and 56 |
| 3 | `si_move_track_ship_259200` | left, 1 px per tick toward the ship's y |
| 4 | `si_move_climb_259190` | left, climbing between x 29 and 56 |
| 5 | `si_move_right_259154` | right; player shots |
| 6 | `si_move_left_259120` | straight left |
| 7 | `si_move_dive_25903c` | left, then to the ship's row near x 40 |
| 9 | `si_move_missile_258f44` | homing missile |
| 10..13 | `si_move_path_258d8e` | left; `si_ypath_wave_rel_312158` plus 35, 11, 14, 25 |
| 14 | `si_move_path_258d8e` | left; the same table plus 18 |
| 15, 16 | `si_move_path_258d8e` | left along `si_ypath_rise_312200`, `si_ypath_fall_3121ac` |
| 17, 18 | `si_move_slope_258d18` | left along the ceiling, the floor |
| 22 | `si_move_boss_part_258c68` | final boss part |
| 23 | `si_move_boss_258b0c` | boss, behaviour chosen by level |
| 24 | inline | bounce at the right, then become pattern 3 |

Patterns 8 and 19..21 do nothing.

## Collisions and scoring

Static, from `si_collisions_259d30`.

- Ship against terrain: pixel test (`tilemap_collide_2e7036`). Ship against
  an object: bounding boxes first, then a pixel test
  (`si_ship_pixel_collide_259ab4`); enemy bullets (type 4) need only the
  box. Either destroys the ship unless the shield is up. A rammed enemy
  loses 1 hit point.
- Shots, missiles, the wall and enemy bullets are removed when they touch
  the terrain. A shield touching the terrain pushes the ship 2 px away
  from it.
- Player objects against an enemy, first match by bounding box
  (`si_find_hit_259a60`): a shot takes 1 hit point, a missile or wall 4,
  and the shield destroys an ordinary enemy outright and takes 1 from a
  boss. Bosses are tested per pixel (`si_boss_pixel_hit_259c62`) and flash
  when hit.
- Score: +5 for a hit that does not destroy, +10 for a kill, +100 for a
  boss. Boss projectiles score nothing. The score stops below 31500.
- A destroyed enemy turns into an explosion (type 2, 5 frames) in place.

## Assets

Static. All addresses are in the image, so a build can read them from the
user's dump.

| Address | Size | Content |
|---|---:|---|
| `0x311740` | 224 | 7 tilemaps |
| `0x311820` | 2148 | 179 spawn entries |
| `0x312084` | 128 | 8 level headers |
| `0x312104` | 336 | 4 y-path tables of 84 bytes |
| `0x312254`..`0x3129a3` | | 30 terrain tiles of 32 bytes in per-level sets of 3 to 6, interleaved with sprite bitmaps |
| `0x3122d4`..`0x312dd7` | | sprite bitmaps |
| `0x312dd8`..`0x31317f` | | sprite descriptors, 12 bytes each |
| `0x313180` | 60 | HUD icon descriptors |
| `0x3131bc` | 444 | 37 object templates |
| `0x2f3108` | 148 | type to descriptor-array pointers |
| `0x2f30d4` | 32 | level header pointers |
| `0x2f2320`, `0x2f2350` | 40, 120 | HUD digit glyphs (4x5) and their descriptors |

The whole game data set is about 6 KiB. Object types: 0 ship, 1 shot,
2 explosion, 4 enemy bullet, 8 shield, 9 wall, 10 missile, `0x11` and
`0x21` bonus, `0x15` boss projectile that tracks the ship, `0x16` beam,
`0x24` final-level explosion; bosses 7, `0x12`, `0x13`, `0x14`, `0x17`,
`0x18`, `0x19`, `0x22`; the rest are enemies. The largest sprite is the
final boss at 38x38.

The tile pointers and tilemap pointers are not tables in ROM:
`si_new_game_257b48` stores them one by one from its literal pool.

## Sounds

The game stores an id in ctx+0x14 and returns `0x1b`; the framework calls
`sound_play_2ec8ca(0, 0xf1, id)` when the games' sounds are on (static).

| Id | Event | Script | Notes, as hertz x timer units |
|---:|---|---|---|
| `0x17` | ship destroyed | `0x321bac` | 880x2 4186x6 932x2 4186x6 988x2 4186x6 |
| `0x18` | shot | `0x321bc8` | 440x5 466x5 494x5 523x5 |
| `0x19` | missile or wall | `0x321bd4` | 4186x8 3951x2 3729x2 3520x2 3322x2 3136x2 2960x2 2794x2 2637x2 |
| `0x1a` | beam | `0x321bf0` | 1397x2 then 988, 932, 880, 831, 784, 740, 698, 659, 622, 587, each x2 and each followed by 1397x2, except that the 1397 after 880 is 1568 and none follows 587 |
| `0x1f` | bonus collected | `0x321cbc` | 2637x1 |

- Static: `sound_play_2ec8ca` posts an 8-byte message to task 6, the tone
  task (its loop is around `0x2ca540`): +0 a pointer to the sound's
  8-byte record in `sound_table_321e6c` (ids `0`..`0x3c`), +4 the id,
  +5 the value 2, +7 the caller's second argument.
- Static: a table record is a pointer to a tone script, a tone class
  `0`..`3` at +4 and flags at +5. The games' five sounds are class 0 with
  no flags; the keypad tones are class 1.
- Static: the five scripts are a `0x00` byte, the command `0x09`, pairs
  of note and length, and the end command `0x0b`. Other sounds in the
  table use more commands (`0x02`, `0x05`..`0x07`, `0x0a` with an
  argument, and note `0x40`, which looks like a rest); they were not
  traced, nor was what `0x09` does.
- Runtime: a note byte n sounds at 440 Hz x 2^((n - 0x7c) / 12): the
  buzzer dividers written for the shot's `0x7c`..`0x7f` are 29545, 27897,
  26316 and 24857 of 13 MHz, and those of every other note in the five
  scripts fit the same scale. Each note is first written with a divider a
  little off and corrected within the same instant.
- Runtime: a length is in the units of the games' timers. Notes of length
  2 last 15.5 ms and of length 5 38.7 ms in MAME, 7.73 ms a unit, the
  unit the game's tick measures there (see Timing). Adjacent notes of the
  same pitch run together: the 4186 Hz groups of `0x17` and the start of
  `0x19` are single tones. The first note of a sound comes out up to a
  unit short, the 1-unit bonus blip at 3.6 ms.
- Runtime: a sound asked for while another plays replaces it.
- Static: the tone task plays a sound only if its class is switched on,
  the byte at +0xe of the class's `0x1c`-byte record in
  `sound_class_state_11072c`, or the record's flags have bit 0. For class
  0 `sound_classes_init_2ec82c` sets the switch to whether byte 6 of the
  profile block is 4. Inferred: that is the profile's Warning and game
  tones setting.
- Runtime: on a fresh NVRAM both that switch and the games' own setting
  (`0x111505`; Games, Settings, Sounds) are off, and no game makes a
  sound. `mame_nokia_3310_game_sound_log.lua` sets both in RAM, logs
  every sound asked for, and can play given ids in place of the first
  sounds of a run; `tools/game_sound_trace.py` lists the notes from the
  log:

  ```
  make run-keys GAMES_PRODUCT=3310 RUN_DIR=$PWD/run_3310_sound SECONDS=40 KEYS=<the golden run's> \
      RUN_ENV=NOKIA_3310_GAME_SOUND_AS=1a,1f,19,17,18 \
      RUN_EXTRA_ARGS="-verbose -autoboot_script $PWD/mame_nokia_3310_game_sound_log.lua -debug -debugger none"
  python3 tools/game_sound_trace.py run_3310_sound/error.log
  ```

## Vibration

- Static: `game_vibrate_2dd70e` is called on ship hits, enemy explosions
  that destroy the ship and boss explosions. It starts the vibrator
  (`vibrator_on_2e93de`) and timer `0x39` for `0x3e` = 62 units, about
  480 ms, when four checks pass: Games, Settings, Shakes (`0x111506`) is
  on; `vibra_present_11fcbd` is nonzero; `vibra_profile_2e944e` returns 1
  (the profile's setting at `0x111a79` is not `0x40` or `0x41`); and
  `charger_state_2d7f82` returns 0. Each call restarts the 62-unit timer;
  nothing checks whether a vibration is already running.
- Runtime: on a fresh NVRAM `0x11fcbd` is 0 and no vibration ever starts;
  inferred to be the presence of a vibra battery, which MAME does not
  model. `mame_nokia_3310_game_vibra_log.lua` sets Shakes and that byte
  in RAM, logs every call with the bytes checked, and logs the driver's
  vibration output as it changes:

  ```
  make run-keys GAMES_PRODUCT=3310 RUN_DIR=$PWD/run_3310_vib SECONDS=45 KEYS=<a game left to be hit> \
      RUN_EXTRA_ARGS="-autoboot_script $PWD/mame_nokia_3310_game_vibra_log.lua -debug -debugger none"
  grep 'GVIB\|VIB' run_3310_vib/error.log
  ```

  Two hits in a run each vibrated for 0.52 s (26.183 to 26.700 s and
  32.983 to 33.500 s, read at frame rate), a little over the timer's
  62 units; `vibrator_on` itself keeps a second timer, `0xf`, at 11
  units.
- Static: `vibrator_on` sets the PUP's vibrator mode `0x60` with a level
  computed from `0x2d8094`'s result, clipped to 2..`0x1c`, through
  `0x2f13e8`.

## Settings pages

Runtime. Games, Settings (`8-6`) is four pages scrolled with up and down,
each showing the setting's name in the small bold font at the top left
and its value in the plain font at the bottom right, with a scrollbar for
the four and a Select key: Sounds (`0x111505`), Lights, Shakes
(`0x111506`) and Club Nokia ID. On a fresh NVRAM they read Off, On, On
and No ID. Select on the first three opens a list of Off and On (`8-6-N-1`
and `8-6-N-2`, OK key) with the current value selected; OK shows the Done
note for 1.47 s: "Done" in the large font with a box at the top right
(`done_tick_pictures_2f9e50`, three 22x32 pictures in the LCD's strip
layout, 88 bytes each) drawn empty, half ticked after 0.70 s and ticked
after 0.92 s. The port in `nokia-3310-games` draws these pages to the
pixel.

## Random numbers

- `game_rand16_2dd7d0`: `seed = (seed * 0x625f + 0x3623) mod 0xfff1`, seed
  at `game_rand_seed_10da5c` (static). Used for enemy fire, bonus choice
  and explosion frames.
- `rand_2f1b44`: ANSI `rand`, seed at `rand_seed_111bf0` (static). Used only
  for spawn rows with y = `0x3f`.
- Runtime: `game_rand_seed` is 1 after boot. `sprite_engine_init` reseeds it
  from the clock only when the clock is set, which it is not in MAME, so
  the title animation draws from seed 1 and scripted runs are
  deterministic: two runs of the golden command below produced identical
  frame sets.

## Settings record

- Static: `games_records_10f9e0` holds a `0x2c`-byte record per game id.
  `games_ctx_load_2dbc7c` copies the u16 at +0 into ctx+0x10 before a game
  starts, and `games_app_handler` writes ctx+0x12 back to it after every
  event.
- Runtime: the Top score screen shows 4075 on a fresh NVRAM, and the
  Space Impact record at `0x10fa0c` holds `0x0feb` at +2.
- Static: +2 is the top score. The Top score page at `0x298710` formats
  the u16 at +2, and the save routine at `0x2981ba` packs the record into
  a `0x28`-byte NV record (key `0x750`, indexed by game id): +0 big-endian
  top score from record +2, +2 level from +4, +3 three 11-byte strings
  from +7, +0x12 and +0x1d, +0x24 and +0x25 from +0x28 and +0x29, +0x26
  u16 from +0x2a.
- Static: 4075 is not a firmware default. The only copy is in the PMM
  dump, where the five records start at `0x3e15be`: top scores 27, 4075,
  0, 1706 and 197 with levels 8, 0, 4, 6 and 6, the rest of each record
  being stack leftovers (return addresses, RAM pointers) behind the
  strings. They are scores saved on the phone the PMM was read from. The
  `0x0feb` at `0x32e022` is an entry in an ascending id table, unrelated.
  The code that compares the score after message `0x5133` was not traced.

## Check against a re-implementation

Runtime. The C port in `nokia-3310-games` replays the event sequence the
firmware's handler received during the golden run below (logged with a
breakpoint on `games_dispatch_2dbd2a`) and draws 231 distinct pictures;
all of them appear, in order, among the frames MAME captured. That
confirms, for the first 20 s of level 0, the event interface, the pending
return code, the sprite order and draw modes, the HUD, the player's keys,
the spawn script, straight-line movement, shot collisions and scoring as
described here. Terrain, enemy fire, the path patterns and everything
from the first boss on are not covered by it.

## Golden run

Runtime. A deterministic 40 s run through the start of level 0:

```
make run-keys GAMES_PRODUCT=3310 RUN_DIR=run_3310_g1 SECONDS=40 \
  KEYS=enter,wait1000,enter,wait1200,up,up,up,up,up,wait800,enter,wait1500,down,wait600,enter,wait2500,enter,wait4000,1,wait400,1,wait400,8,8,8,1,wait400,0,0,0,0,1,wait300,3,wait300,4,wait2000,1,wait500,1,wait6000
```

It writes 343 LCD frames. The frames are derived from the firmware and
stay outside this tree.

## Address map

Names are in `ghidra/symbols/3310.csv`; the tables are generated from it and
the notes file by `make games-doc GAMES_PRODUCT=3310`.

<!-- address map: generated by tools/games_doc_tables.py -->

### Space Impact

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x109df0` | label | `si_work_109df0` | Scratch block outside the saved state: +0 s8 vertical-bounce direction, +1 final-boss volley counter, +2 burst pause for pattern-20 fire, +4 u16 sprite currently flashed, +8 pointer to the active y-path table, +0xc boss-fire cooldown, +0x10.. tile pointer arrays filled by si_new_game. |
| `0x109e68` | label | `si_level_tilesets_109e68` | 8 pointers, one per level, to that level's array of 32-byte tile bitmap pointers (inside si_work). Filled by si_new_game. |
| `0x109ea0` | label | `si_level_tilemaps_109ea0` | 8 pointers, one per level, to a 32-byte tilemap in ROM (0x311740..0x31181f; levels 2 and 3 share 0x311760). Filled by si_new_game. |
| `0x109ec4` | label | `si_state_109ec4` | Space Impact state, 0x34c bytes; event 0x33/0x34 hands this address and size to the framework. Layout in docs/games_applications_3310.md. |
| `0x10a210` | label | `si_type_frames_10a210` | RAM copy of si_type_frames_init_2f3108: per object type, pointer to its array of 12-byte sprite descriptors. |
| `0x10a2a4` | label | `si_level_table_10a2a4` | RAM copy of si_level_table_init_2f30d4: 8 pointers to the 16-byte level headers. |
| `0x2576a0` | function | `si_objects_clear_2576a0` | Marks all 60 object records free (type 0x32) and clears the object count at state+0x2a. |
| `0x2576ce` | function | `si_draw_number_2576ce` | Writes a decimal number into a chain of digit sprites: (first sprite id, value, digits). Follows the sprite next links, so digit sprites must be created consecutively. |
| `0x257748` | function | `si_set_play_bounds_257748` | Sets the vertical play limits at state+0x318/+0x319: (0x20, 6) with ground terrain, (0x2a, 0x10) when the terrain is on the ceiling (arg 0x2b). |
| `0x257764` | function | `si_hud_create_257764` | Creates the HUD sprites (5 life icons, special icon, 2-digit special count, 5-digit score) and the terrain layer via tilemap_init; levels 4 and 5 put the terrain at the top. |
| `0x2578de` | function | `si_level_load_2578de` | Copies a 16-byte level header to state+0x31c, resets sprites and objects, rebuilds the HUD, sets phase 10. |
| `0x25793a` | function | `si_object_spawn_25793a` | (type, draw mode, x, y) -> sprite id. Creates the sprite with the type's first frame and copies the 12-byte template. Refuses when 40 objects exist. |
| `0x2579ac` | function | `si_hud_refresh_2579ac` | Redraws special count, score and the life icons (shown for index < lives). |
| `0x257a18` | function | `si_ship_spawn_257a18` | (ctx, 10 = new ship \| 0x14 = respawn). Places the ship at (5, 20) with a shield sprite (type 8) at (3, 18); sets ctx period 100 and one-shot 3000 ms, which is the shield time. |
| `0x257b48` | function | `si_new_game_257b48` | Events 0x24/0x2b. Allocates 60 sprites, fills the tile and tilemap pointer tables, lives 3, special 3 x missile, continues counter 4, loads level 0. |
| `0x257ce0` | function | `si_continue_key_257ce0` | On the continue screen (phase 0x14), keys 1/3/4/6 restart the current level from its beginning with 3 lives and 3 missiles. The level load clears the checkpoint byte before this function reads it. |
| `0x257e1c` | function | `si_key_257e1c` | Key handler while playing. 8/0 move up/down, */# left/right (1 px, repeat codes 2 px), 1/3 fire, 4/6 special. Sets ctx+0x14 to the sound and the pending return to 0x1b. |
| `0x258114` | function | `si_continue_enter_258114` | Builds the continue screen: remaining continues as icons, a countdown digit, tick period 800 ms, phase 0x14. |
| `0x2581f8` | function | `si_resume_2581f8` | Event 0x35. Re-allocates the sprite engine and recreates every sprite from the saved object records and their saved x/y. |
| `0x258400` | function | `si_final_boss_spawn_258400` | Level 7: spawns the final boss (type 0x22) and its two parts (type 0x23) when the scroll position reaches 0x7a, 0x13a or 0x1ba. |
| `0x2584c8` | function | `si_object_is_boss_2584c8` | True for types 7, 0x12, 0x13, 0x14, 0x17, 0x18, 0x19, 0x22. |
| `0x258508` | function | `si_spawn_step_258508` | Runs the level script: counts down the delay, then spawns the next entry's group and records checkpoints. y 0x3f picks a random row with the ANSI rand. |
| `0x25865a` | function | `si_enemy_fire_roll_25865a` | Returns 1 with probability 1/N, N the object's fire byte (0 and 0x7f never fire), using game_rand16. |
| `0x2586b2` | function | `si_enemy_fire_2586b2` | Spawns an enemy bullet (type 4) at the object's left edge if it has shots left (bosses have unlimited shots). |
| `0x25871c` | function | `si_move_bounce_25871c` | Vertical bounce between the play limits and off the terrain; may fire. |
| `0x258808` | function | `si_boss_fire_258808` | Boss shot: spawns the given projectile type at an offset, with a 6-tick cooldown. |
| `0x258882` | function | `si_boss_enter_258882` | Moves a boss left 1 px per tick until x <= 0x38; returns 1 once in place. |
| `0x2588c8` | function | `si_final_boss_step_2588c8` | Final boss state machine on state+0x47 (0x32, 0x3c, 0x46, 0x50). |
| `0x258a04` | function | `si_boss_charge_258a04` | Boss charge and retreat state machine on state+0x47 (10, 0x14, 0x1e, 0x28). |
| `0x258aec` | function | `si_sprite_mode_restore_258aec` | Restores a sprite's draw mode for the level polarity after a hit flash. |
| `0x258b0c` | function | `si_move_boss_258b0c` | Pattern 23. Per-level boss behaviour: levels 0-1 bounce, 2 charge, 3 bounce and fire type 0x15, 4-6 charge and fire, 7 the final boss. |
| `0x258c68` | function | `si_move_boss_part_258c68` | Pattern 22: bobs a final-boss part with the boss animation frame. |
| `0x258cac` | function | `si_object_free_258cac` | Frees the sprite and the object record; clears the missile target and boss part ids that pointed at it. |
| `0x258cf6` | function | `si_object_free_at_left_258cf6` | Frees the object when its x is 0 or has wrapped (>= 0xfb). |
| `0x258d18` | function | `si_move_slope_258d18` | Patterns 17/18: move left, sliding along the ceiling or the floor. |
| `0x258d8e` | function | `si_move_path_258d8e` | Patterns 1 and 10..16: move left by the speed and take y from the active y-path table indexed by x mod 84. |
| `0x258e64` | function | `si_object_is_player_side_258e64` | True for types 0, 1, 2, 8, 9, 10, 0x16, 0x24: objects that are not targets. |
| `0x258ea4` | function | `si_missile_pick_target_258ea4` | Returns the enemy with the most hit points. |
| `0x258f1c` | function | `si_object_free_at_right_258f1c` | Frees the object when x + width passes 84. |
| `0x258f44` | function | `si_move_missile_258f44` | Pattern 9: the missile moves right 2 px per tick and steers 1 px per tick toward its target's centre. |
| `0x25903c` | function | `si_move_dive_25903c` | Pattern 7: move left, climb to the ship's row around x 40..42 and fire when level with it. |
| `0x259120` | function | `si_move_left_259120` | Pattern 6: move left by the speed. |
| `0x259154` | function | `si_move_right_259154` | Pattern 5: move right by the speed (player bullets). |
| `0x259190` | function | `si_move_climb_259190` | Pattern 4: move left, climbing between x 0x1d and 0x38. |
| `0x259200` | function | `si_move_track_ship_259200` | Pattern 3: move left and step 1 px toward the ship's y. |
| `0x25924c` | function | `si_move_descend_25924c` | Pattern 2: move left, descending between x 0x1d and 0x38. |
| `0x2592b0` | function | `si_award_2592b0` | (kind, amount, ctx). 0x11 bonus: random life/missile/wall/beam; 0x21: +3 specials; 0x31: add score, capped below 31500. |
| `0x2593a4` | function | `si_boss_destroyed_2593a4` | Boss kill: explosions, +100, state+0x47 = 0x7f, phase 0x1e (level exit). |
| `0x259534` | function | `si_beam_scan_259534` | Beam special: damages every enemy within 3 px of the beam column as it sweeps. |
| `0x2596a0` | function | `si_objects_step_2596a0` | Per-tick walk of the object list: animation, explosion end, ship death, then the 24-entry movement pattern switch at 0x259718. |
| `0x259a0e` | function | `si_sprites_overlap_259a0e` | Bounding-box overlap of two sprites. |
| `0x259a60` | function | `si_find_hit_259a60` | First non-player object whose box overlaps the given sprite. |
| `0x259ab4` | function | `si_ship_pixel_collide_259ab4` | Pixel-exact overlap between the ship and an object, honouring the level polarity. |
| `0x259c62` | function | `si_boss_pixel_hit_259c62` | Tests a shot against a boss bitmap along its row; returns the row distance or 0. |
| `0x259cfe` | function | `si_boss_flash_259cfe` | Hit flash: hides the sprite for a tick (mode 6) and remembers its id. |
| `0x259d30` | function | `si_collisions_259d30` | Per-tick collisions: ship against terrain and enemies, then every player shot against terrain and enemies, with damage and scoring. |
| `0x25a200` | function | `si_event_25a200` | All events except start. 1 = tick, 0 = one-shot timer (shield off), 0x33/0x34 state query/suspend, 0x35 resume; keys go to si_key or si_continue_key first. |
| `0x25a52a` | function | `si_handler_25a52a` | Game id 1 entry called by games_dispatch: 0x24/0x2b start a new game, everything else goes to si_event. |
| `0x2d7538` | function | `si_title_start_2d7538` | Builds the Space Impact title: 37-sprite pool, full-screen fill, 30 random 1x1 stars (mode 3), ship 0x31889c at (0,18), hidden 0x3188a8/0x3188b4/0x3188c0, logo halves 0x3188cc (7,1) and 0x3188d8 (3,32). Runtime frames match. |
| `0x2d7624` | function | `si_title_step_2d7624` | Step k: logo halves to y k+1 and 32-k; k 1..5 ship to x 4k; k 6..8 swap to the next hidden picture. |
| `0x2d7694` | function | `si_title_event_2d7694` | SI title events: tick steps 1..8, 9 sets 700 ms, then ends (0x10); keys end it. |
| `0x2d76f6` | function | `si_title_handler_2d76f6` | Title id 0x81 (Space Impact): saves ctx+0xc/+0xe, period 210 ms (0xd2), si_title_start; other events to si_title_event. Runtime: steps ~0.2 s apart, menu 0.9 s after the last. |
| `0x2f30d4` | label | `si_level_table_init_2f30d4` | Initialised-data image of si_level_table_10a2a4 (8 pointers 0x312084..0x3120f4). |
| `0x2f3108` | label | `si_type_frames_init_2f3108` | Initialised-data image of si_type_frames_10a210 (37 pointers, type 0x16 is null). |
| `0x311740` | label | `si_tilemaps_311740` | Seven 32-byte tilemaps (2 rows x 16 tile ids, 0 = empty), 0x311740..0x31181f. |
| `0x311820` | label | `si_spawn_lists_311820` | Spawn entries, 12 bytes each, 179 entries for the 8 levels, 0x311820..0x312083. |
| `0x312084` | label | `si_level_headers_312084` | Eight 16-byte level headers: spawn count, spawn list pointer, four checkpoint bytes, draw polarity. |
| `0x312104` | label | `si_ypath_wave_abs_312104` | 84 signed y values indexed by x: absolute sine path (pattern 1). |
| `0x312158` | label | `si_ypath_wave_rel_312158` | 84 signed y offsets (-4..4) indexed by x (patterns 10..14). |
| `0x3121ac` | label | `si_ypath_fall_3121ac` | 84 y values rising 6..33 with x (pattern 16). |
| `0x312200` | label | `si_ypath_rise_312200` | 84 y values falling 33..6 with x (pattern 15). |
| `0x312254` | label | `si_tiles_312254` | Terrain tiles, 32 bytes each (32x8, one byte per column, bit 0 top), 0x312254..0x3129a3. |
| `0x313180` | label | `si_hud_icons_313180` | Sprite descriptors for the HUD: life icon, then the three special-weapon icons at 0x313198 (missile), 0x3131a4 (wall), 0x3131b0 (beam). |
| `0x3131bc` | label | `si_type_templates_3131bc` | 37 object templates, 12 bytes each, indexed by type; copied into the object record at spawn. |
| `0x318618` | label | `si_title_pictures_318618` | Space Impact title bitmaps; descriptors at 0x31889c, star 0x3188e4. |

### Snake II (games_snake2_3310.md)

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x10c9b0` | label | `snake2_globals_10c9b0` | Snake II globals: +0 u16 collection mask (bit 15 enables the large creature, bits 0..9 collected; loaded from record +0x2a by games_ctx_load with bit 15 = (0x111507 != 0)), +2 s16 board x offset, +4 s16 board y offset (both 0), +8 pointer to the state. Runtime: 0x80 written to +0 at boot (init table |
| `0x10c9b8` | label | `snake2_state_ptr_10c9b8` | Pointer to the Snake II state (0x10c9bc), set by new game and by event 0x33. |
| `0x10c9bc` | label | `snake2_state_10c9bc` | Snake II state, 0x2b0 bytes (event 0x33/0x34 hands this address and size). +0 tail index, +2 head index, +4 ring modulus 299, +8/+9 head cell, +0xc/+0xd tail cell, +0x10 direction, +0x11 previous direction, +0x12 ring of 300 sprite ids, +0x270 board w/h, +0x274 occupancy ptr, +0x278 maze record, +0x |
| `0x2741e0` | function | `snake2_draw_score_2741e0` | (ctx, first digit sprite): draws the s16 at ctx+0x12 (low half of the score) as four decimal digits into sprites first+3 (units) .. first+0, using game_digit_sprites_10db68. |
| `0x27421c` | function | `snake2_draw_countdown_27421c` | (units sprite, value): value > 0 shows sprites id, id+1 and id+4 (mode 4) and sets the units and tens digits; value <= 0 hides them (mode 6). The creature countdown and icon. |
| `0x274296` | function | `snake2_board_dims_274296` | (84, 48, out) -> board size in 4-px cells: w = (84-6)/4 + ((84-2)%4 != 0) = 20, h = (48-14)/4 + ((48-2)%4 != 0) = 9. |
| `0x2742d6` | function | `snake2_first_free_cell_2742d6` | (out, board) -> first cell with a clear occupancy bit in row-major order from (0,0); returns 0 when the board is full. |
| `0x27436e` | function | `snake2_food_place_27436e` | Food placement (board, food sprite, creature cells, out): up to 100 tries of x = rand16 % w, y = rand16 % h, accepted when the cell is free and shares no row or column with any creature cell; then the first free cell; none: (-1,-1) and the sprite hidden. Sprite at (2+4x, 10+4y). Runtime: positions r |
| `0x2744a8` | function | `snake2_creature_spawn_2744a8` | Creature spawn (board, &sprite, cells, food, icon sprite \| mode<<16): rand16 % 50 == 0 with mask bit 15, mode 1 and state+0x2aa == 0 tries the 2x2 animated creature, else a 2x1 creature with kind rand16 % 6 (pictures 0x327e1c). 100 tries each, cells free and clear of the food's row and column. Retur |
| `0x274844` | function | `snake2_tail_remove_274844` | Tail removal (snake, board): clears the tail cell's occupancy bit, advances the tail index mod 299, moves the tail cell to the next segment's, gives that segment the tail image (0x327ef4 + direction to the next segment) and returns the old tail sprite for reuse as the head. |
| `0x274a58` | function | `snake2_mouth_open_274a58` | (board, snake, food, creature cells) -> 1 when the cell ahead of the head (with wrap) is the food or a creature cell: the head is drawn with its mouth open (0x327f84). |
| `0x274b98` | function | `snake2_head_step_274b98` | Head step (snake, board, sprite or 0, &swallow flag, food, creature cells, creature sprite): ring full (head+2 == tail mod 299) -> returns 100; creates a sprite when none is passed (growth); moves the head with wrap, sets its occupancy bit, head image (closed or open), stores the sprite in the ring; |
| `0x274f0c` | function | `snake2_walls_draw_274f0c` | (maze, board): draws the playfield frame (four fill sprites around x 0..83, y 8..47) and one 2-px fill sprite per maze segment through the cell centres. |
| `0x2750dc` | function | `snake2_maze_build_2750dc` | (board, maze record): sets the occupancy bit of every cell of every wall segment (horizontal or vertical runs of 8-byte {x1,y1,0,0,x2,y2,0,0}), then draws with 0x274f0c. |
| `0x2752b0` | function | `snake2_hud_create_2752b0` | HUD: four score digit sprites at x 0,4,8,12 (mode 4), countdown digits at x 79,75,71,67 and the creature icon at (66,1) (mode 6, hidden), and the rectangle line at y 6. |
| `0x27533e` | function | `snake2_food_init_27533e` | Food and creature init at new game: food sprite (0x327e10, mode 1) then a random placement, creature cells cleared, creature sprite (mode 1) off screen, counter and active flag 0. |
| `0x2753f2` | function | `snake2_blocked_2753f2` | (state, snake index, board, &food-eaten flag) -> nonzero when the cell ahead (with wrap) is blocked: its occupancy bit, except that the tail's cell is blocked only when the snake grows this step. Snake records are 0x26c bytes apart; only snake 0 exists. Runtime: walls and the body block. |
| `0x2754b6` | function | `snake2_collect_bit_2754b6` | Large creature eaten: sets a random clear bit 0..9 (rand16 % 10, retried while set) in the collection mask at 0x10c9b0 and sets state+0x2aa. Loops forever if all ten bits are set. |
| `0x275502` | function | `snake2_board_free_275502` | Frees the occupancy bitmap (state+0x274) if allocated. |
| `0x27553c` | function | `snake2_suspend_pack_27553c` | Suspend: packs each ring entry tail to head into a u16 (x bits 0-4, y bits 5-10, image index bits 11-12, kind bits 13-15 found by comparing the sprite's bitmap pointer with the image sets) and the creature's kind into state+0x296. |
| `0x275788` | function | `snake2_resume_build_275788` | Resume: rebuilds maze, every segment sprite and its occupancy bit from the packed ring, HUD, score, food sprite, creature sprite and countdown. |
| `0x275aa4` | function | `snake2_handler_275aa4` | Game id 0 entry (Snake II). 0x2b/0x24 new game, 1 tick, 0 blink step, keys via the jump table at 0x275b28, 0x33/0x34/0x35 state query/suspend/resume, 0x13/0x15/0x17/0x18/0x1a end a dying game, 0x1c. Runtime: returns 0x21, 0x1b (eat, sound 0x1f), 0x16 (grace 100 ms), 0x1f (death, sound 0x20), 0x20 (b |
| `0x275b28` | label | `snake2_key_jumptable_275b28` | Jump table for game events 0x0a..0x16 (keys 1..9, 0x13, #, 0x15, *). Keys set the pending direction at state+0x2a3 from the current one; runtime-verified for all of 1-9, # and *. |
| `0x2762e0` | function | `snake2_new_game_2762e0` | New game (reached by bl from the handler, returns through 0x276642): board 20x9, period = level table * 10 ms, maze record, start cell, direction right, occupancy and sprite engine (w*h+29), event 0x2b also resets the ring and fills the maze; seven head steps then one tail removal leave 7 visible se |
| `0x276472` | label | `snake2_new_game_fail_276472` | Inside new game: allocation-failure exit returning 2; the code after it is the rest of new game. |
| `0x276640` | label | `snake2_return_1_276640` | Handler exit returning 1 (movs r7,#1 falling into 0x276642); reached by bl as a long branch. |
| `0x276642` | label | `snake2_return_276642` | Common handler exit: returns r7. |
| `0x2d7724` | function | `snake2_title_build_2d7724` | Snake II title build: allocates 6 sprites, creates the 84x48 picture 0x318318 and five hidden overlays (0x318324..0x318354) at x 6. |
| `0x2d77b2` | function | `snake2_title_step_2d77b2` | Ticks 1..5 show the frame at +0x18+2k and hide the previous (0x318324 never shown, runtime-confirmed), 6 sets 1200 ms, then ends. |
| `0x2d780e` | function | `snake2_title_handler_2d780e` | Handler for id 0x80, the Snake II title: on 0x24/0x2b saves ctx+0xc/+0xe, sets a 250 ms tick and builds the title; other events step it. |
| `0x2f4224` | label | `snake2_globals_init_2f4224` | Entry of a RAM-init table: address 0x10c9b0, value 0x80 (the collection mask starts as 0x8000 at boot). |
| `0x317ca8` | label | `snake2_title_pictures_317ca8` | Snake II title bitmaps; descriptors at 0x318318. |
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

### Bantumi (games_bantumi_3310.md)

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x10e178` | label | `bantumi_ui_10e178` | Bantumi drawing block: +0 player-won flag, +1 sound pending (return 0x1b), +2..+4 intro slide step/toggle/board frame, +5 winner digits draw mode, +8/+0xc hand mask/image sprite ids, +0xa board sprite, +0xe thinking sprite, +0x10 hand closed, +0x14..+0x43 four RAM hand descriptors, +0x44 hand animat |
| `0x10e1f8` | label | `bantumi_state_10e1f8` | Bantumi game state, 0x28 bytes (the block saved on suspend, events 0x33/0x34): pits[14] (0..5 player, 6 player store, 7..12 computer, 13 computer store), +0xe cursor, +0xf computer's chosen pit, +0x10 hand pit (0xff while thinking), +0x14 u32 turn (0 intro, 1/2 hand to pit, 3 player, 4 computer, 5 g |
| `0x10e2e0` | label | `bantumi_digit_sprites_10e2e0` | 14 x {u16 units digit sprite, u16 tens digit sprite}, one per pit, digits from game_digit_sprites_10db68 in draw mode 2. |
| `0x10f404` | label | `bantumi_ai_10f404` | Bantumi search block: +0 u8 chosen pit, +1 u8 depth remaining, +4 root node, +8 current node. Nodes are 0x20-byte heap records: +0 side (3 player, 4 computer), +4 alpha, +6 beta, +8 best (s16), +0xa pits[14], +0x18 first move (0xe none), +0x19 counter, +0x1c parent. |
| `0x2b1520` | function | `bantumi_draw_hand_2b1520` | (arg) Draws the hand: arg 0 frees the old pair first. Open hand (0x10e188 == 0) 18x16 from 0x31d120/0x31d0f0 (bottom row, state+0x10 <= 6) or 0x31d138/0x31d108 (top); closed hand 11x13 from 0x31d198/0x31d150 or 0x31d180/0x31d168. Bitmaps are copied to RAM, shifted up and shortened when y < 0; mask s |
| `0x2b1732` | function | `bantumi_side_empty_2b1732` | Returns 1 when pits 0..5 or pits 7..12 are all empty. |
| `0x2b1764` | function | `bantumi_set_pit_2b1764` | (pit, n): sets the pit's count and updates its digit sprites. One digit at (x+4, y+2) for pits, (x+5, y+5) for stores; with two digits the tens sprite is created at (x+1 / x+2) and the units moved 4 px right; going back below 10 frees the tens sprite. |
| `0x2b1898` | function | `bantumi_turn_end_2b1898` | (arg) End of a move: hand idle, hand sprites freed; arg 1 passes the turn (3 <-> 4), arg 0 keeps it (last seed in the store). If a row is empty, sweeps each row into its owner's store, sets the won flag or blinks the computer's store (mode 5) and turn 5. Else: player's turn draws the open hand at th |
| `0x2b1a04` | function | `bantumi_hand_path_2b1a04` | (from, to) Starts a hand animation: state 1, counter 2, start and target positions from the pit table 0x31d1ec with row-dependent offsets (bottom row y-14 start, y-4 pick-up / y-11 sow target; top row y+10 start, y / y+7 / y+10 target); special starts at the stores when turning a corner. |
| `0x2b1ad0` | function | `bantumi_pick_2b1ad0` | (pit) Picks up a pit's seeds: next pit = pit + 1, hand animation, frees the thinking sprite (computer) or the hand pair (player), closed hand, seeds in hand = pit count, pit emptied, sow sub-state 1. Runtime: logged at each pick-up. |
| `0x2b1b34` | function | `bantumi_draw_board_2b1b34` | (frame) Resets all sprites and draws board frame 0x31d0c0 + 12*frame at (0,0), mode 4, layer 0. Frame 0 also draws the hand (or the thinking sprite when state+0x10 is 0xff) and creates the 14 digit sprites. Used by new game (frame 3), the intro (2, 1, 0) and resume. |
| `0x2b1c10` | function | `bantumi_new_game_2b1c10` | New game: 45 sprites, cursor 0, turn 0, four seeds per pit, stores 0, level = ctx+0x16, game-over countdown 40, closed board (frame 3) at x = 40, tick 120 ms; returns 0x16 (2 when the sprites cannot be allocated). |
| `0x2b1cc0` | function | `bantumi_event_2b1cc0` | Bantumi event handler: tick (hand animation states, sowing and captures, intro, search steps, game over), keys 4/6 and scroll (cursor), 5/0/event 8 (sow), * (hint at level 1), suspend/resume; returns 0x1b when a seed was dropped (sound 0x1b) and 0x1e at game over with ctx+0x10 = pit 6 - pit 13. |
| `0x2b2398` | function | `bantumi_handler_2b2398` | Game id 2 (Bantumi). Events 0x24/0x2b: ctx+0xc = 120, new game 0x2b1c10; others to 0x2b1cc0. Runtime: called through games_dispatch_2dbd2a with id 2 when Bantumi is played. |
| `0x2d79b0` | function | `bantumi_title_create_2d79b0` | Creates the title picture 0x3185c4 (mode 4) and six hidden overlay sprites (mode 6) at (23,18), (34,23), (37,33), (45,19), (53,15), (62,27). |
| `0x2d7a38` | function | `bantumi_title_init_2d7a38` | Title init: 7 sprites; draws the title unless the event was 0x24. |
| `0x2d7a64` | function | `bantumi_title_step_2d7a64` | Title step: hides the previous overlay, shows the current one (mode 4); returns 0x16. |
| `0x2d7a9c` | function | `bantumi_title_event_2d7a9c` | Title events: each tick advances the overlay (70 ms after step 3, 250 ms otherwise), two passes, 700 ms on the last frame, then returns 0x10 restoring ctx+0xc/+0xe; keys end it at once. Runtime: two rounds from 14.85 to 17.18 s in a scripted run. |
| `0x2d7b3c` | function | `bantumi_title_handler_2d7b3c` | Game id 0x82: Bantumi title. Static: games_dispatch_2dbd2a calls it for id 0x82 with context 0x1111f8. Saves ctx+0xc/+0xe, sets a 250 ms tick. |
| `0x2dd1c0` | function | `bantumi_ai_evaluate_2dd1c0` | (terminal) Evaluates the current node: pit 13 - pit 6; terminal nodes add computer row - player row and +-50; negated for side 3. Runtime: model matches all logged searches. |
| `0x2dd214` | function | `bantumi_ai_close_2dd214` | (node, terminal) Closes a node: evaluate if terminal or depth 0; negate when the side differs from the parent's; raise parent best (records the chosen pit at the root), parent alpha = max(alpha, best); depth + 1; frees the node. |
| `0x2dd28e` | function | `bantumi_ai_child_2dd28e` | (parent, pit) Makes a child: copies pits, sows (computer skips 6, player wraps at 13); store landing keeps side and window, else side flips with (-beta, -alpha) and captures. Quirk: the computer's capture tests the live board 0x10e1f8 and is credited to pit 6. Runtime: child order logged and matched |
| `0x2dd3bc` | function | `bantumi_ai_start_2dd3bc` | Starts a search from the live board: computer side 4 with depth 2*level-1 (9 becomes 8), or for the hint (turn 6) side 3 depth 5. Root alpha -32000, beta 32000. |
| `0x2dd438` | function | `bantumi_ai_first_move_2dd438` | First move heuristic: a pit that ends in the store (scanning down from the store, which itself matches when empty), else the last pit with the largest capture value read at 13-(k+c), else the fullest pit. |
| `0x2dd554` | function | `bantumi_ai_next_move_2dd554` | Next move of the current node: the heuristic pick first, then pits in order skipping it; +7 for the computer. |
| `0x2dd5ac` | function | `bantumi_ai_step_2dd5ac` | One tick of search: up to 100 iterations; at the end the computer's choice goes to state+0xf/+0x10, turn 2 and a hand animation, or for a hint into the cursor with turn 3. Runtime: tick counts match the model (1 to 242 ticks). |
| `0x2dd698` | function | `bantumi_ai_abort_2dd698` | Frees every node of a running search (used before restarting it on interrupting events). |
| `0x318360` | label | `bantumi_title_pictures_318360` | Bantumi title bitmaps; descriptors at 0x3185c4. |
| `0x3185c4` | label | `bantumi_title_descs_3185c4` | Bantumi title: seven 12-byte descriptors, the 84x48 picture then six overlays (11x7, 7x10, 11x14, 8x12, 13x10, 11x8). |
| `0x31d0c0` | label | `bantumi_board_descs_31d0c0` | Four 12-byte descriptors of 84x48 board pictures: 0 open board, 1 and 2 opening frames, 3 closed box (intro slide). |
| `0x31d0f0` | label | `bantumi_hand_open_bottom_31d0f0` | Open hand image, bottom row, 18x16 (two bands of 18 bytes); drawn in mode 1. |
| `0x31d108` | label | `bantumi_hand_open_top_31d108` | Open hand image, top row, 18x16; mode 1. |
| `0x31d120` | label | `bantumi_hand_open_bottom_mask_31d120` | Open hand mask, bottom row, 18x16; mode 0 (inferred role). |
| `0x31d138` | label | `bantumi_hand_open_top_mask_31d138` | Open hand mask, top row, 18x16; mode 0 (inferred role). |
| `0x31d150` | label | `bantumi_hand_closed_bottom_31d150` | Closed hand image, bottom row, 11 wide, 13 rows used; mode 1. |
| `0x31d168` | label | `bantumi_hand_closed_top_31d168` | Closed hand image, top row; mode 1. |
| `0x31d180` | label | `bantumi_hand_closed_top_mask_31d180` | Closed hand mask, top row; mode 0 (inferred role). |
| `0x31d198` | label | `bantumi_hand_closed_bottom_mask_31d198` | Closed hand mask, bottom row; mode 0 (inferred role). |
| `0x31d1ec` | label | `bantumi_pit_xy_31d1ec` | Pit box positions: 14 x then 14 y bytes. x 4,17,30,44,57,70,68,70,57,44,30,17,4,3; y 36 x6, 16, 3 x6, 16. |
| `0x31d22c` | label | `bantumi_think_descs_31d22c` | Eight 12-byte descriptors of the 16x16 thinking animation, shown at (34,16) while a search runs. |

### Pairs II (games_pairs2_3310.md)

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x1090dc` | label | `pairs2_sprite_ids_1090dc` | Sprite ids outside the saved state (static, from every create/free): +0 door (TT intro), +2 flame, +4 saloon / Puzzle picture / explosion, +6 dynamite, +8 fuse rectangle, +0xa cursor, +0xc first and +0xe second enlarged picture, +0x10 eight top and +0x20 eight bottom wipe strips. |
| `0x109190` | label | `pairs2_state_109190` | Pairs II state, 0x564 bytes; events 0x33/0x34 hand back this address and size (literal 0x564 at 0x2da064). Layout in docs/games_pairs2_3310.md. Runtime: +0 time 0x32 at board 0, +2 card count 4, +0xd phase 2/0/8/4. |
| `0x1096b4` | label | `pairs2_column_order_1096b4` | state+0x524: card indices in column order, built by pairs2_column_order_2e9eb2, walked by keys 2/8. |
| `0x1096f4` | label | `pairs2_card_sprites_1096f4` | One u16 sprite id per card (state+0x564, not saved; rebuilt on resume). |
| `0x2c6478` | function | `pairs2_layout_puzzle_2c6478` | (rows, cols): x0 = 7*((12-cols)>>1), y0 = 9*((5-rows)>>1) + 4 if rows even (lsrs/bhs at 0x2c6498); cards row by row on a 7x9 pitch, card back 0x31afc4 mode 4 layer 1 created at (0x27,0x14); state +0x25 = 8; Puzzle picture 0x31afb8 at (0,0) layer 0 into 0x1090e0. Runtime: level 1 first card at (35,13 |
| `0x2c6574` | function | `pairs2_board_puzzle_2c6574` | Puzzle board from level (state+0xc): 2x2 at level 1, else cols = 2(L-1), rows = L/2+2; deal(rows*cols), shuffle, layout, column list. |
| `0x2c65b2` | function | `pairs2_layout_tt_2c65b2` | Time trial layout: 10 column-mask bytes at 0x32fe74 + 10*board; bit r of byte c puts a card at (12+7c, 1+9r); stores the count at state+2. Runtime: board 0 cards at (33,10),(54,10),(33,28),(54,28). |
| `0x2c6674` | function | `pairs2_board_tt_2c6674` | Time trial board: deal(count from 0x32fee4[board]), shuffle, layout, column list; saloon 0x31afac (mode 4, layer 0) at (0,0) into 0x1090e0, door 0x31afa0 at (0x20,0x11) into 0x1090dc. |
| `0x2c66ba` | function | `pairs2_fuse_step_2c66ba` | Per play tick: fuse top (state+5) += 1 when time % state+4 == 0; flame frame toggles (0x31af7c + 12*toggle); fuse rectangle remade (mode 1, layer 3, x 4, y 0x1e..top); flame moved to (0, top-5). Runtime: top 8 -> 9 at time 48 on board 0. |
| `0x2c6740` | function | `pairs2_tick_2c6740` | Event 1. Puzzle in phase 4/7: period 200 (0x16 if changed), removal animation per card (frames 0x31ad60, state 0..7 -> 9; 0x18 in phase 7 when done). Phases 2/3: deal step. Time trial only: countdowns (phase 0 -> 8, phase 1 -> next board or 0x18 after board 8, bonus time/2), wipe (phase 8), HUD remo |
| `0x2c6b36` | function | `pairs2_clamp_x_2c6b36` | clamp(x, 0, 0x4c). |
| `0x2c6b4c` | function | `pairs2_clamp_y_2c6b4c` | clamp(y - 1, 0, 0x25). |
| `0x2c6b70` | function | `pairs2_show_second_2c6b70` | Second enlarged picture (8x11, mode 4, layer 2, id at 0x1090ea); if it would overlap the first (\|dx\| < 8 and \|dy\| < 11) it is pushed clear and the clamp shortfall moves the first (0x1090e8). |
| `0x2c6ccc` | function | `pairs2_after_match_2c6ccc` | After a pair: if a card is still face down, cursor to the next one (2e9fca(3)); else Time trial: free cursor, target := current position, phase 9; Puzzle: phase 7. Clears state+3, +0xa. |
| `0x2c6d38` | function | `pairs2_open_second_2c6d38` | Key 5 with one card open. Returns 0 (miss: state+0xa = 2) or 1 (pair: TT frees both sprites, state 9; Puzzle starts the removal animation, state 0). Runtime: return 0x1b with sound 0x1c and +5 at level 1. |
| `0x2c6e28` | function | `pairs2_show_first_2c6e28` | (card): enlarged picture 0x31adc0 + 12*picture at (clamp_x(x), clamp_y(y)), mode 4 layer 2, id into 0x1090e8. Runtime: card at (33,10) shows its picture at (33,9). |
| `0x2c6e64` | function | `pairs2_open_first_2c6e64` | Key 5 with no card open: show picture, face up, first card := cursor, cursor to the next face-down card; state+0xa = 1. Runtime: cursor 0 -> 1. |
| `0x2d783c` | function | `pairs2_title_start_2d783c` | Builds the Pairs II title: 9-sprite pool, background 0x318f20 (card backs). |
| `0x2d786e` | function | `pairs2_title_step_2d786e` | Jump table on step 1..8: adds 0x318f2c (6,7), 0x318f38 (3,1), 0x318f44 (3,1), 0x318f50 (19,1), 0x318f5c (35,1), 0x318f68 (38,1), 0x318f74 (35,1), 0x318f80 (35,25), mode 4 layer 0. Runtime: frames match the stacked composites. |
| `0x2d7904` | function | `pairs2_title_event_2d7904` | Pairs II title events: steps 1..8, step 9 sets 1400 ms, then ends (0x10); keys end it. |
| `0x2d7974` | function | `pairs2_title_handler_2d7974` | Title ids 0x83 and 0x84 (Pairs II), period 200 ms. Runtime: receives 0x2b, ticks, then a key (event 9 for Select) and 0x34. |
| `0x2d9a94` | function | `pairs2_shuffle_2d9a94` | For i in 0..n-1 swap the 20-byte card record i with record game_rand16() % n. |
| `0x2d9aea` | function | `pairs2_deal_step_2d9aea` | Moves each card's current x/y (+0x28/+0x2c) 1 px toward its place (+0x30/+0x34) and its sprite; in phase 3 frees cards already in place; returns 1 if any moved. Runtime: 15 ticks on board 0. |
| `0x2d9ba4` | function | `pairs2_all_face_up_2d9ba4` | Returns 0 if any card has +0x26 == 0. |
| `0x2d9bc6` | function | `pairs2_special_effect_2d9bc6` | Dead code (no caller, no pointer): picture 0x21 phase 6 for 40 ticks, 0x22 shows every card, 0x23 adds 30 ticks to the time (max 150). |
| `0x2d9c54` | function | `pairs2_deal_2d9c54` | (n): count, phase 2, cursor 0, time = 0x32fed0[board], fuse divisor time/25, fuse top 8; cards 0..n/2-1 and n/2..n-1 get pictures 0..n/2-1, state 8, face down. |
| `0x2d9cdc` | function | `pairs2_special_pair_2d9cdc` | Dead code: from board 2, the pair with picture rand16 % n becomes picture 0x21..0x23. |
| `0x2d9d2c` | function | `pairs2_new_game_2d9d2c` | sprite_engine_init(90), reset, reseed, first board by mode; returns 2 for 0x24 or failure, 1 for 0x2b. |
| `0x2d9d68` | function | `pairs2_resume_2d9d68` | Event 0x35: recreates background (and TT HUD), cards on the board, cursor; between boards deals the next one; Puzzle phase 7 returns 0x18. |
| `0x2d9ee0` | function | `pairs2_event_2d9ee0` | Every event but start: tick, keys 2/4/5/6/8 in phase 4 (0xb, 0xd, 0xe, 0xf, 0x11), 0x33/0x34 state, 0x35 resume; match: ctx+0x14 0x1c, score += level+4; miss: 0x1e, score -= 1 if > 0; return 0x1b. Runtime-confirmed. |
| `0x2da004` | function | `pairs2_handler_2da004` | Game ids 3 (Time trial, ctx+0x17 = 0) and 4 (Puzzle, ctx+0x17 = 1). 0x24/0x2b: ctx+0xc 200, score 0, board 0, mode, level; else pairs2_event. |
| `0x2e9df4` | function | `pairs2_first_card_2e9df4` | Start of the column list: the first card (index 0). |
| `0x2e9e2a` | function | `pairs2_card_below_2e9e2a` | (card): first card with the same x and a greater y, else 0xffff. |
| `0x2e9e6a` | function | `pairs2_next_column_2e9e6a` | (card): card with the smallest x greater than the card's (lowest index among equals), else 0xffff. |
| `0x2e9eb2` | function | `pairs2_column_order_2e9eb2` | Builds the column list at 0x1096b4: down each column, then the top of the next. |
| `0x2e9eea` | function | `pairs2_close_pair_2e9eea` | When state+0xa == 2: both cards face down again, enlarged pictures freed, cursor mode 2. |
| `0x2e9f4a` | function | `pairs2_cursor_column_2e9f4a` | (0 up, 1 down): steps through the column list with wrap, skipping face-up cards. Runtime: up from card 2 of a 12x5 grid to 49, down from 50 to 3. |
| `0x2e9fca` | function | `pairs2_cursor_row_2e9fca` | (2 left, 3 right): index -1/+1 with wrap, skipping face-up cards. |
| `0x3188f0` | label | `pairs2_title_pictures_3188f0` | Pairs II title bitmaps; descriptors at 0x318f20..0x318f8b. |
| `0x319fc4` | label | `pairs2_pictures_319fc4` | Pairs II bitmaps 0x319fc4..0x31ad23: Puzzle picture, saloon, card back, cursor, 34 card pictures 8x11, removal frames, dynamite, flames, door, explosions, wipe strips. |
| `0x31ad24` | label | `pairs2_descriptors_31ad24` | Descriptors: wipe strips 0x31ad24/0x31ad30, explosions 0x31ad3c/48/54. |
| `0x31ad60` | label | `pairs2_removal_frames_31ad60` | 8 descriptors 7x9; frames 0..6 used by the Puzzle removal animation. |
| `0x31adc0` | label | `pairs2_pictures_31adc0` | Card picture descriptors, 8x11, indexed by picture; 0..33 set, 0x22/0x23 empty. |
| `0x31af70` | label | `pairs2_hud_31af70` | Descriptors: dynamite 9x18, flames 0x31af7c/88/94 9x5, door 0x31afa0 19x23, saloon 0x31afac, Puzzle picture 0x31afb8, card back 0x31afc4, cursor 0x31afd0. |
| `0x32fe74` | label | `pairs2_board_masks_32fe74` | 9 Time trial boards x 10 column bytes, bit r = card in row r. |
| `0x32fed0` | label | `pairs2_board_times_32fed0` | 9 u16 board times in ticks (50 for board 0, runtime). |
| `0x32fee4` | label | `pairs2_board_counts_32fee4` | 9 card counts (4 for board 0, runtime). |

### Games framework

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x10da5c` | label | `game_rand_seed_10da5c` | Seed of game_rand16_2dd7d0. 1 after boot; sprite_engine_init reseeds it from the clock when the clock is set (runtime: stays unseeded in MAME). |
| `0x10db68` | label | `game_digit_sprites_10db68` | RAM copy of 0x2f2350: ten 12-byte sprite descriptors for the 4x5 HUD digits, glyphs at 0x10dbe0 (ROM image 0x2f2320). |
| `0x10f9e0` | label | `games_records_10f9e0` | Per-game record, 0x2c bytes each. Snake II (id 0): +0 result word, +2 u16 top score, +4 level 0..8 (ctx+0x16 = +4 + 1), +0x28 maze 0..5 (ctx+0x17 = +0x28 + 1), +0x2a u16 collection mask. Runtime: writing +4 and +0x28 from Lua changes the game's level and maze. |
| `0x110d60` | label | `games_title_state_110d60` | Title handlers' state: +0 Bantumi second-round flag, +1 step counter (SI, Bantumi, Pairs II at 0x110d61), +2 Snake II step, +0x14/+0x16 saved ctx+0xc/+0xe, sprite ids from +4 (Snake II), +6 (SI), +0x24 (Bantumi). |
| `0x1111ec` | label | `games_app_state_1111ec` | Framework state: +0 suspended flag, +2 u16 last key code \| 0x80 for repeat, +4 u16 game id, +8 pointer to the active context. |
| `0x1111f8` | label | `title_ctx_1111f8` | Context passed by games_dispatch_2dbd2a to the title handlers (ids 0x80..0x84). |
| `0x111218` | label | `game_ctx_111218` | Context passed to every game handler in r1. +0xc u16 tick period ms, +0xe u16 one-shot delay ms, +0x10 u32 score/result, +0x14 u16 sound id, +0x16/+0x17 settings. |
| `0x111507` | label | `games_setting_111507` | Games setting byte next to Sounds (0x111505) and Shakes (0x111506); games_ctx_load copies whether it is nonzero into bit 15 of the Snake II collection mask, which the large creature requires. Meaning inferred only; 0 in MAME. |
| `0x11fd57` | label | `games_current_id_11fd57` | Index of the selected game (0 Snake II, 1 Space Impact, 2 Bantumi, 3/4 Pairs II). |
| `0x2dbc7c` | function | `games_ctx_load_2dbc7c` | (id, ctx): loads the per-game record into the context: ctx+0x10 result word (+0), ctx+0x16 level + 1 (+4), ctx+0x17 = 0 for id 3 and 1 for id 4 (Pairs II's Time trial and Puzzle), else record +0x28 + 1 (Snake II's maze). For games whose table flags have bit 3, copies the collection mask at record +0 |
| `0x2dbd2a` | function | `games_dispatch_2dbd2a` | (game id, event) -> handler(event, ctx). Ids 0..4 are the games with game_ctx_111218; 0x80..0x84 are their title screens with a second context at 0x1111f8. |
| `0x2dbdd4` | function | `games_app_handler_2dbdd4` | Application handler shared by all games. Translates phone events to game events and acts on the handler's return code (timers, sound, game over). |
| `0x2dd6dc` | function | `game_alloc_zeroed_2dd6dc` | Heap allocation followed by a clear. |
| `0x2dd70e` | function | `game_vibrate_2dd70e` | Starts a short vibration: timer 0x39 at 0x3e = 62 units, when Shakes (0x111506), vibra_present_11fcbd, vibra_profile_2e944e == 1 and charger_state_2d7f82 == 0 allow it. Called on ship hits and boss explosions; each call restarts the timer. Runtime: about 0.5 s of vibration in MAME. |
| `0x2dd7d0` | function | `game_rand16_2dd7d0` | seed = (seed * 0x625f + 0x3623) mod 0xfff1; returns the seed. |
| `0x2dd8f6` | function | `title_sprites_alloc_2dd8f6` | (n): allocates a private pool of n sprites for a title, saving the game's engine header. |
| `0x2dd9aa` | function | `title_sprites_free_2dd9aa` | Frees a title's pool and restores the saved engine header. |
| `0x2f9e50` | label | `done_tick_pictures_2f9e50` | Three pictures of the Done note's tick, 22x32 in the LCD's strip layout (22 bytes per 8 rows), 88 bytes each: the empty box, the half tick and the tick. Runtime: shown at 0, 0.70 and 0.92 s of the note's 1.47 s. |
| `0x33016c` | label | `games_table_33016c` | Game table, 16-byte records: four parameter bytes, Thumb handler pointer (games_app_handler for all five), text pointer, u16 flags. Five records. |

### Sprite and tilemap engine

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x111af0` | label | `sprite_engine_111af0` | Sprite engine: +0 u16 free-list head, +2 u16 sprite count, +4 pointer to the 0x1c-byte sprite records (heap), +8 dirty flag. |
| `0x2dd748` | function | `sprite_set_image_2dd748` | (id, descriptor): copies a 12-byte sprite descriptor into the sprite and marks it dirty. |
| `0x2dd77e` | function | `sprite_engine_reseed_2dd77e` | Sets game_rand_seed from 0x2cc440 (clock) unless it returns the unset value. |
| `0x2dd790` | function | `sprite_free_2dd790` | Unlinks a sprite and returns it to the free list. |
| `0x2dd7e8` | function | `sprite_move_2dd7e8` | (id, x, y). |
| `0x2dd82c` | function | `sprite_set_rect_2dd82c` | (id, x, y, w, h) for rectangle sprites (the beam). |
| `0x2dd8ae` | function | `sprite_reset_all_2dd8ae` | Clears every sprite and rebuilds the free list. |
| `0x2dd936` | function | `sprite_engine_init_2dd936` | Allocates n sprites of 0x1c bytes; reseeds game_rand16 from the clock if it is set. Returns 1 on success. |
| `0x2dd97c` | function | `sprite_full_redraw_2dd97c` | (flag) Writes 0x111af9 in the sprite engine block. Inferred: requests a full redraw; Bantumi calls it with 1 while the hand moves and on thinking frames. |
| `0x2dd9da` | function | `sprite_set_mode_2dd9da` | (id, mode): draw mode in bits 3..5 of the flags byte. 0 clear bits clear; 1 set; 2 flip; 3 inverse; 4 opaque; 5 opaque and blink; 6 hidden. |
| `0x2dda1c` | function | `sprite_alloc_2dda1c` | Takes a sprite from the free list and links it in layer order. |
| `0x2dda8c` | function | `sprite_create_2dda8c` | (descriptor, mode, layer, x, y) -> id. |
| `0x2ddad8` | function | `sprite_create_rect_2ddad8` | Creates a rectangle sprite (kind 1). |
| `0x2ddbac` | function | `sprite_create_fill_2ddbac` | Creates a fill sprite (kind 2); used for the full-screen background on inverted levels. |
| `0x2dfd88` | function | `sprite_render_2dfd88` | Called by games_app_handler after each handled event. Erases and redraws the sprites that changed and every sprite overlapping them (0x2dfa0a), in list order (0x2dfbe4), or everything when the engine's dirty flag is set. |
| `0x2e6e98` | function | `tilemap_render_2e6e98` | (layer, scroll x): draws rows of 32x8 tiles into the layer bitmap, 84 px wide, wrapping at width * 32. |
| `0x2e6f9a` | function | `tilemap_init_2e6f9a` | (layer, width in tiles, rows, map, top flag, tile pointers, mode): allocates rows * 84 bytes and creates the layer sprite at the top (0x2b) or bottom of the 48-row screen. |
| `0x2e7036` | function | `tilemap_collide_2e7036` | Pixel overlap between a sprite and the terrain layer. |

### Runtime services used by the games

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x11072c` | label | `sound_class_state_11072c` | Four 0x1c-byte records, one per tone class. +0xe: the class is switched on; +0x14: the script being played. Class 0 is the games' sounds, class 1 the keypad tones. |
| `0x111bf0` | label | `rand_seed_111bf0` | Seed of the ANSI rand at 0x2f1b44. |
| `0x11fcbd` | label | `vibra_present_11fcbd` | Byte game_vibrate_2dd70e requires nonzero before vibrating. Runtime: 0 on a fresh NVRAM in MAME, so no game vibration starts there; inferred to be the presence of a vibra battery. |
| `0x299450` | function | `timer_cancel_299450` | Inferred from its use with timer ids 0x32, 0x37, 0x38. |
| `0x2995ea` | function | `timer_start_2995ea` | (id, ticks). Inferred. 0x32 game tick, 0x37 one-shot, 0x38 key repeat (12 ticks). |
| `0x29a74e` | function | `heap_free_29a74e` | Inferred. |
| `0x29a810` | function | `heap_alloc_29a810` | Inferred. |
| `0x2ca926` | function | `vibra_present_2ca926` | Returns the byte at vibra_present_11fcbd. |
| `0x2d7f82` | function | `charger_state_2d7f82` | Returns the byte at 0x11fe97 after writing it to NV key 0x5b0d. The game vibrates only when it is 0; inferred to be a charger's presence. |
| `0x2e93de` | function | `vibrator_on_2e93de` | Starts the vibrator: cancels timer 0xf, derives a level from 0x2d8094's result clipped to 2..0x1c, writes PUP vibrator mode 0x60 with it through 0x2f13e8, and starts timer 0xf at 11 units. |
| `0x2e944e` | function | `vibra_profile_2e944e` | Returns 1 unless the profile byte at 0x111a79 is 0x40 or 0x41, then 2, and writes the result to NV key 0x7501. The game vibrates only on 1. |
| `0x2ec82c` | function | `sound_classes_init_2ec82c` | Sets the tone classes' switches from the profile block. Class 0 is on when the block's byte 6 is 4; inferred to be Warning and game tones. |
| `0x2ec8ca` | function | `sound_play_2ec8ca` | (0, class argument, id): posts the sound's record in sound_table to the tone task. Games call it as (0, 0xf1, ctx+0x14) on return code 0x1b/0x1f when their sounds are on (0x111505). |
| `0x2f04fc` | function | `rt_smod_2f04fc` | Signed remainder in r0 (quotient in r1). |
| `0x2f0998` | function | `rt_umod_2f0998` | Unsigned remainder in r0. |
| `0x2f1158` | function | `memcpy_2f1158` |  |
| `0x2f1b44` | function | `rand_2f1b44` | ANSI rand: seed = seed * 0x41c64e6d + 0x3039; returns (seed & 0x7fffffff) >> 16. |
| `0x2f1c8c` | function | `memset_2f1c8c` |  |
| `0x321e6c` | label | `sound_table_321e6c` | 0x3d 8-byte records by sound id: tone script pointer, tone class at +4, flags at +5. |

<!-- end address map -->

## Not done

- The per-level boss behaviours in `si_move_boss_258b0c` and the final boss
  state machine are named and summarised, not specified step by step.
- The 800 ms continue period was not measured.
- No run has reached a boss, a level change, a game over or a top-score
  update, so those paths are static only.
- Three candidate entries inside the game range (`0x259c46`, `0x259ddc`,
  `0x25a340`) are mid-function addresses, not functions.
