# Space Impact on the 3310: application map

The Nokia 3310 Games menu offers Snake II, Space Impact, Bantumi and
Pairs II. This document maps Space Impact and the layers it sits on, to the
level needed to re-implement the game and check the result frame for frame
against the firmware in MAME. It is the 3310 counterpart of
`games_applications.md` and follows its conventions. The other three games
are located but not mapped.

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
| 2 | `bantumi_handler_2b2398` | Bantumi (inferred from menu order) |
| 3, 4 | `pairs2_handler_2da004` | Pairs II (inferred) |
| 0x80..0x84 | `0x2d780e`, `si_title_handler_2d76f6`, `0x2d7b3c`, `0x2d7974` | the games' title screens |

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

Static for the ids, inferred for the player. The game stores an id in
ctx+0x14 and returns `0x1b`; the framework calls
`sound_play_2ec8ca(0, 0xf1, id)` when game sounds are enabled.

| Id | Event |
|---:|---|
| `0x17` | ship destroyed |
| `0x18` | shot |
| `0x19` | missile or wall |
| `0x1a` | beam |
| `0x1f` | bonus collected |

`game_vibrate_2dd70e` is called on ship hits and boss explosions.

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
- Inferred: +2 is the top score. Its default appears twice in the image,
  at `0x32e022` and in the PMM at `0x3e15e4`. The code that compares the
  score after message `0x5133` and writes the record back was not traced.

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
| `0x2d76f6` | function | `si_title_handler_2d76f6` | Handler for id 0x81: the Space Impact title animation. Runtime: receives 0x2b then 0x34 when the title is shown and left. |
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

### Games framework

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x10da5c` | label | `game_rand_seed_10da5c` | Seed of game_rand16_2dd7d0. 1 after boot; sprite_engine_init reseeds it from the clock when the clock is set (runtime: stays unseeded in MAME). |
| `0x10db68` | label | `game_digit_sprites_10db68` | RAM copy of 0x2f2350: ten 12-byte sprite descriptors for the 4x5 HUD digits, glyphs at 0x10dbe0 (ROM image 0x2f2320). |
| `0x10f9e0` | label | `games_records_10f9e0` | Per-game record, 0x2c bytes each, indexed by game id: +0 u16 result word (ctx+0x12 after every event), +2 u16 top score (runtime: Space Impact shows 4075 from 0x10fa0e), +4 level setting. |
| `0x1111ec` | label | `games_app_state_1111ec` | Framework state: +0 suspended flag, +2 u16 last key code \| 0x80 for repeat, +4 u16 game id, +8 pointer to the active context. |
| `0x111218` | label | `game_ctx_111218` | Context passed to every game handler in r1. +0xc u16 tick period ms, +0xe u16 one-shot delay ms, +0x10 u32 score/result, +0x14 u16 sound id, +0x16/+0x17 settings. |
| `0x11fd57` | label | `games_current_id_11fd57` | Index of the selected game (0 Snake II, 1 Space Impact, 2 Bantumi, 3/4 Pairs II). |
| `0x275aa4` | function | `snake2_handler_275aa4` | Game id 0 entry (Snake II). Not mapped. |
| `0x2b2398` | function | `bantumi_handler_2b2398` | Game id 2 entry. Inferred from the menu order; not mapped. |
| `0x2da004` | function | `pairs2_handler_2da004` | Game ids 3 and 4 entry. Inferred from the menu order; not mapped. |
| `0x2dbc7c` | function | `games_ctx_load_2dbc7c` | Loads the per-game record into the context: ctx+0x10 result word, +0x16 level + 1, +0x17 option. |
| `0x2dbd2a` | function | `games_dispatch_2dbd2a` | (game id, event) -> handler(event, ctx). Ids 0..4 are the games with game_ctx_111218; 0x80..0x84 are their title screens with a second context at 0x1111f8. |
| `0x2dbdd4` | function | `games_app_handler_2dbdd4` | Application handler shared by all games. Translates phone events to game events and acts on the handler's return code (timers, sound, game over). |
| `0x2dd6dc` | function | `game_alloc_zeroed_2dd6dc` | Heap allocation followed by a clear. |
| `0x2dd70e` | function | `game_vibrate_2dd70e` | Starts a short vibration when a setting at 0x111506 allows it. Inferred from the checks and the timer it starts; called on hits and explosions. |
| `0x2dd7d0` | function | `game_rand16_2dd7d0` | seed = (seed * 0x625f + 0x3623) mod 0xfff1; returns the seed. |
| `0x33016c` | label | `games_table_33016c` | Game table, 16-byte records: four parameter bytes, Thumb handler pointer (games_app_handler for all five), text pointer, u16 flags. Five records. |

### Sprite and tilemap engine

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x111af0` | label | `sprite_engine_111af0` | Sprite engine: +0 u16 free-list head, +2 u16 sprite count, +4 pointer to the 0x1c-byte sprite records (heap), +8 dirty flag. |
| `0x2dd748` | function | `sprite_set_image_2dd748` | (id, descriptor): copies a 12-byte sprite descriptor into the sprite and marks it dirty. |
| `0x2dd790` | function | `sprite_free_2dd790` | Unlinks a sprite and returns it to the free list. |
| `0x2dd7e8` | function | `sprite_move_2dd7e8` | (id, x, y). |
| `0x2dd82c` | function | `sprite_set_rect_2dd82c` | (id, x, y, w, h) for rectangle sprites (the beam). |
| `0x2dd8ae` | function | `sprite_reset_all_2dd8ae` | Clears every sprite and rebuilds the free list. |
| `0x2dd936` | function | `sprite_engine_init_2dd936` | Allocates n sprites of 0x1c bytes; reseeds game_rand16 from the clock if it is set. Returns 1 on success. |
| `0x2dd9da` | function | `sprite_set_mode_2dd9da` | (id, mode): draw mode in bits 3..5 of the flags byte. 0 clear bits clear; 1 set; 2 flip; 3 inverse; 4 opaque; 5 opaque and blink; 6 hidden. |
| `0x2dda1c` | function | `sprite_alloc_2dda1c` | Takes a sprite from the free list and links it in layer order. |
| `0x2dda8c` | function | `sprite_create_2dda8c` | (descriptor, mode, layer, x, y) -> id. |
| `0x2ddad8` | function | `sprite_create_rect_2ddad8` | Creates a rectangle sprite (kind 1). |
| `0x2ddbac` | function | `sprite_create_fill_2ddbac` | Creates a fill sprite (kind 2); used for the full-screen background on inverted levels. |
| `0x2dfd88` | function | `sprite_render_2dfd88` | Called by games_app_handler after each handled event. Erases and redraws the sprites that changed and every sprite overlapping them (0x2dfa0a), in list order (0x2dfbe4), or everything when the engine's dirty flag is set. |
| `0x2e6e98` | function | `tilemap_render_2e6e98` | (layer, scroll x): draws rows of 32x8 tiles into the layer bitmap, 84 px wide, wrapping at width * 32. |
| `0x2e6f9a` | function | `tilemap_init_2e6f9a` | (layer, width in tiles, rows, map, top flag, tile pointers, mode): allocates rows * 84 bytes and creates the layer sprite at the top (0x2b) or bottom of the 48-row screen. |
| `0x2e7036` | function | `tilemap_collide_2e7036` | Pixel overlap between a sprite and the terrain layer. |

### Runtime services used by Space Impact

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x111bf0` | label | `rand_seed_111bf0` | Seed of the ANSI rand at 0x2f1b44. |
| `0x299450` | function | `timer_cancel_299450` | Inferred from its use with timer ids 0x32, 0x37, 0x38. |
| `0x2995ea` | function | `timer_start_2995ea` | (id, ticks). Inferred. 0x32 game tick, 0x37 one-shot, 0x38 key repeat (12 ticks). |
| `0x29a74e` | function | `heap_free_29a74e` | Inferred. |
| `0x29a810` | function | `heap_alloc_29a810` | Inferred. |
| `0x2ec8ca` | function | `sound_play_2ec8ca` | Called as (0, 0xf1, ctx+0x14) on return code 0x1b/0x1f when game sounds are on (0x111505). Inferred. |
| `0x2f04fc` | function | `rt_smod_2f04fc` | Signed remainder in r0 (quotient in r1). |
| `0x2f0998` | function | `rt_umod_2f0998` | Unsigned remainder in r0. |
| `0x2f1158` | function | `memcpy_2f1158` |  |
| `0x2f1b44` | function | `rand_2f1b44` | ANSI rand: seed = seed * 0x41c64e6d + 0x3039; returns (seed & 0x7fffffff) >> 16. |
| `0x2f1c8c` | function | `memset_2f1c8c` |  |

<!-- end address map -->

## Not done

- Bantumi, Pairs II and Snake II are located only.
- The per-level boss behaviours in `si_move_boss_258b0c` and the final boss
  state machine are named and summarised, not specified step by step.
- The 800 ms continue period was not measured.
- No run has reached a boss, a level change, a game over or a top-score
  update, so those paths are static only.
- Three candidate entries inside the game range (`0x259c46`, `0x259ddc`,
  `0x25a340`) are mid-function addresses, not functions.
