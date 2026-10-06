# Kart Racing (Nokia 3510): the map

Kart Racing is the 3510's largest built-in game and the first 3510 port target
(requested in lukesau/nokia-gb-games issue 2). It is mapped statically from the
decrypted v5.02 flash (`roms/3510-nhm8-v502/flash.bin`, big-endian Thumb at
`0x01000000`). The 3510 is DCT4 and nothing here has been run; every claim in
these docs is marked **S** (static: read from code or data, checked in the
disassembly where it matters) or **I** (inferred).

The map is in four parts:

| Doc | Covers |
|---|---|
| this file | what the game is, the layout of its code, how the slices fit together, porting notes |
| `games_kart_3510_shell.md` | the message handler, registration, menus, title, instruction demos, best results, saved data, downloaded tracks |
| `games_kart_3510_race.md` | the tick, input, physics, opponents and AI, items, collisions, laps and timing, start and finish, random numbers, **the state layout** |
| `games_kart_3510_road.md` | the pseudo-3D road renderer, track format, horizon, roadside sprites, with every table and all five built-in tracks dumped |

The shared game library the game calls is in `games_library_3510.md`, and how
the games were found is in `games_survey_3510.md`. Names are in
`ghidra/symbols/3510.csv` (219 `kart_` names); `tools/dct4_bitmaps.py` renders
any bitmap mentioned.

## The game

- **Two modes** (S for the data, I for the names):
  - Item 1, a cup: 6 karts, 3 laps, the four race tracks in order, points
    10/6/4/3/2/1, the final total scaled by the difficulty.
  - Item 2, a challenge: 4 karts, 1 lap, on a fifth track, scored on time or
    points against a target (built-in: a 20 s limit with 2 s extensions).
- **Five built-in tracks**, 7 to 17 segments, 1275 to 2200 units long. They
  use three of the six horizon backdrops (0, 2 and 3). Downloaded tracks
  (`application/x-NokiaGameData`) can add karts, tracks, sprites and
  backdrops, and are listed in the menus as extra options.
- **Eight karts**, three unlocked at first; racing unlocks the rest (saved as a
  one-byte mask, default 0x78). Each kart has four stats at levels 1..6: max
  speed, acceleration, brake and steering.
- **Items** from boxes on the track: a homing missile or a mine (weapon box) and
  a 5-tick turbo at twice top speed (turbo box).
- **Screens**: an animated title, kart selection, the race with start lights and
  a HUD, results and standings, a best-results screen, and four scripted
  instruction demos. There is no pause screen in the game's code, and no
  vibration anywhere.

## Code layout

Exactly 132 functions, `0x014047f0`..`0x0140d9a8`, all reached from
`kart_handler_14047f0` (static: call closure including stored function
pointers), plus `0x0140cba8`, which nothing references. Space Impact starts at
`0x0140d9e0`; the functions just below `0x014047f0` belong to another module.

| Slice | Entry | Functions |
|---|---|---|
| Shell | `kart_handler_14047f0` and every message path except the race | registration `0x0140d910`, title, demos, best results, save/continue, track and download loading (`0x0140c94c`..`0x0140d0dc`) |
| Race | `kart_tick_140873c` (msgs 0 and 1 while racing) | kart select, race setup, `kart_race_step_1409204`, AI, items, collisions, ranks, results |
| Road | `kart_road_draw_1406144`, called once per tick by the race | road rows, horizon, the sprite draw list, the HUD |

## How the slices fit together

Three agents mapped the three slices in parallel. Where they overlapped:

- **The runtime divide.** `0x012fb028` (signed) and `0x012fb0d8` (unsigned) return
  the remainder in r0 and the quotient in r1. Both road and race agents found it
  in the disassembly, and it was confirmed by running the routine in Unicorn
  ((100, 7) → r0 2, r1 14). Ghidra reads the two results the other way round, so
  its decompiles of any formula with a divide are wrong; every formula in these
  docs was re-read from the disassembly.
- **Kart `+0x12`** is one field with two uses: the race code's steering momentum
  (±2 per tick, the kart moves once it reaches ±6), and the road code's player
  sprite offset, drawn at `+0x12 − w/2 + 48` (S: `ldrsh` at `0x01407178`). So
  the player's kart slides up to 6 px sideways on screen as it starts and stops
  turning.
- **The road is rectangles, not lines.** The race scene (`kart_scene_build_1405534`)
  makes each road row from two 1-pixel-tall rects (type 7) at RAM `0x3cc74`. The
  line-object road (type 6) belongs to the instruction demo
  (`kart_demo_start_140af18`, a fixed downhill road); `game_rect_set_size` refuses
  lines, so the renderer only works on the race scene. `games_survey_3510.md` said
  lines; it is corrected.
- **Track numbering** is 0-based (`kart_track0_1509594`..`kart_track3_1509744`,
  plus `kart_track_mode2_15097d4`). State `+4` counts cup races done (0..4) and
  picks the track; 4 or more picks `rand() & 3`.
- **The level setting** (`*0x3cc54 + 0xe`, 1..3) is the difficulty: the AI's look-ahead,
  whether it holds items, missile targeting and the cup multiplier.
- **`kart_patterns_1509568`** is used by both the road (the id-102 gate banner)
  and the instruction demos.

## Porting notes (Game Boy)

- **Timing**: one tick is 50 ms (I: the only period the race sets). All motion is
  per tick, so the port should run the logic at 20 Hz and keep the arithmetic
  exactly (24.8 positions, s16 speeds, truncating divides).
- **Keys**: the race reads key ids 0x13 left, 0xf right, 0x14 gas, 0x15 brake
  (only while gas is up), 0x16 weapon and 0x17 turbo, the last two on press (S).
  Which phone keys those are is inferred from the keypad-help table only: the
  race layout marks 4 left, 5 right, 6 gas, 9 brake, 1 weapon and 2 turbo. On a
  Game Boy the mapping is the port's choice.
- **Random numbers**: `game_rand` is the MSVC LCG. In a race only two draws matter:
  the opponents' kart types (`rand() % 7`, repeated until distinct, first race of
  a series) and the weapon box (`rand() & 1`). The track loader may draw first
  (track choice past race 4). A port that keeps this order replays exactly.
- **Original bugs to keep** (S, listed in `games_kart_3510_race.md`): the
  finish-time estimate does not reset its distance total between racers; the
  AI's turbo check can never fire on a real track; the rubber band on a level-6
  stat reads past its table (only a custom kart can have level 6).
- **One segment per tick**: the race advances at most one segment a tick. The
  shortest built-in segment is 50 units and the fastest speed (turbo, 2 × 0x440)
  covers 8.5 units a tick, so the built-in tracks are safe; a downloaded track
  with very short segments would not be.
- **Drawing**: everything is retained scene objects (`games_library_3510.md`).
  The road per row, the horizon sliding ±12 px and sprites at four fixed sizes
  map onto GB scanline scroll effects, a background strip and hardware sprites
  (I; see `games_survey_3510.md`).

## Open questions

Merged from the three slices; details are at the end of each.

1. The physical keys behind key ids 0x13/0xf/0x14/0x15/0x16/0x17 (only the
   keypad-help table suggests them).
2. Colours: a rect drawn with style 1 is taken to be black on a white screen
   that is cleared before each render. Neither is traced to the LCD.
3. Which way a curve bends on screen for each direction bit, and which hill class
   (0 or 1) is uphill.
4. The strings behind the text ids `0xfdf`..`0xfea` (the PPM text is compressed).
5. The tick period during the instruction demos (nothing sets it; probably the
   engine's 100 ms default).
6. The exact meaning of result phases 3..9, and the range of the level setting
   beyond 1..3.
7. The message meanings come from the engine's dispatch switch (`0x01427d14`)
   and menu-action switch (`0x014261c6`), read statically in
   `games_kart_3510_shell.md`; the harness should confirm them by driving the
   handler the way the engine does.

All of these, and every formula, can be checked once the Unicorn harness runs the
game against the library boundary.
