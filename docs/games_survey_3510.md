# The 3510's games: a first static survey

Where the Nokia 3510's built-in games are, found by comparing its flash with the
3410 games mapped in `games_survey_3410.md`. The 3510 is DCT4, so nothing here
can be run in MAME; every conclusion is **static** (read from the images) or
**inferred**.

Image: 3510 NHM-8 v5.02, PPM E, decrypted and merged by
`tools/dct4_decrypt.py` into `roms/3510-nhm8-v502/flash.bin` (see
`roms/README.md`): big-endian Thumb, flash at `0x01000000`, PPM at
`0x015a0000`. Ghidra project `nokia3510`, symbols in
`ghidra/symbols/3510.csv`. `tools/games_survey_3510.py` reproduces every
figure below.

## What the 3510 has

Static: the PPM's tone list has a background tune per game, in this order:
`GameBG Bumper`, `GameBG D2M`, `GameBG Link5`, `GameBG SI tune`,
`GameBG Car Racing`. They sit next to the shared game effects (`Game tick`,
`Game fanfare`, `Game bhit`…). The PPM's menu text is compressed, but proper
nouns are stored as plain UTF-16 and give `Bumper`, `Kart` / `…acing`,
`Space` / `…mpact`, `Link5` and `Dance` / `…usic`.

So the built-in games are Bumper, Kart Racing, Space Impact, Link5 and D2M
("Dance 2 Music", static: its title bitmaps spell it). There is no Snake and no
Bantumi. The MCU also holds a game engine for downloadable games
(`engine_app_isa.c`, `engine_download_isa.c`, `engine_scoresend_isa.c`,
`application/x-NokiaGameData`, code from about `0x014247dc` to `0x0142c600`).
The built-in games are native code, but they run inside that engine: they are
registered as its apps and draw, play tones and save through it, by way of the
shared game library described in `games_library_3510.md`.

## Where they are

12-byte windows of each 3410 game's code, with Thumb BL pairs masked and the
3510 turned into little-endian half-words, found in the 3510 MCU:

| 3410 game | Windows found | Densest 3510 pages |
|---|---:|---|
| Snake II | 1.1% | scattered |
| Space Impact | 6.3% | `0x0140e000`–`0x01415000` |
| Bumper | 12.4% | `0x01418000`–`0x0141a000` |
| Bantumi | 2.1% | scattered |
| Link5 | 6.7% | `0x01421000` |

The figures are low even for the games that are there, so (inferred, as for
the 3310 → 3410 comparison) the 3510 was built with another compiler; the
clusters, not the percentages, are the evidence.

Static: a table of five Thumb pointers at `0x01511ebc` holds the games'
message handlers. Each game starts its background tune once with
`game_sound_loop_142df3a(id)`, and the engine maps the id to a PPM tone through
the halfword table `game_tone_ids_1511e88` (`0x01511e88 + (id - 4000) * 2`),
just before the handler table:

| Handler | Tune call | Tune id | PPM tone | Game |
|---|---|---|---|---|
| `0x01418c58` | `0x01418e0c` | `0xfb4` | `0x25` GameBG Bumper | Bumper |
| `0x01422a70` | `0x01423cb0` | `0xfb5` | `0x26` GameBG D2M | D2M |
| `0x0142144c` | `0x0142180a` | `0xfb6` | `0x27` GameBG Link5 | Link5 |
| `0x0140e758` | `0x0140efca` | `0xfb7` | `0x28` GameBG SI tune | Space Impact |
| `0x014047f0` | `0x01408ada` | `0xfb8` | `0x29` GameBG Car Racing | Kart Racing |

The three games pinned by the code matches land on their own tunes, which
checks the table. The bitmaps agree (static, rendered from the 0x18-byte
descriptors `{u16 w, u16 h, u32 depth, u32 data, …}`, 1 bpp packed vertically,
8 rows per byte, LSB at the top):

- Kart Racing (`kart_sprites_1504bf8`, `kart_title_bitmaps_1508f10`): the
  player's kart from behind at 12, 16 and 20 px, six 120 x 20 horizon
  backdrops, opponent karts, roadside objects at four fixed sizes, a 72 x 16
  start-lights panel, and "KART" / "RACING" title logos with a checkered flag.
- D2M (`d2m_bitmaps_150320c`, `d2m_bitmaps_15034fc`): a 96 x 65 spotlight
  stage, "Dance 2" and "Music" logos, dancer poses (43 x 59), a panda and a
  4-3-2-1 countdown.

Each game also registers itself once with `game_app_define_142d174(app_id,
name_text, …, save_size, …)`. The app ids are Bumper `0x30`, D2M `0x3b`, Link5
`0x3d`, Space Impact `0x43` and Kart Racing `0x4b`.

Layout, from the handlers and the matches: Kart Racing
`0x01404000`–`0x0140e000` (the largest, and new), Space Impact to
`0x01416700`, Bumper to `0x0141ce00`, Link5 to `0x01422a00` and D2M to about
`0x014247dc`. Then come the download engine and the shared game library at
`0x0142c616`–`0x0142edd4`. Above that, to `0x01430000`, is WAP session code
(`wsp_ses.c`), not games. Outside the library the games call only the ARM
divides (`0x012fb028`, `0x012fb0d8`) and memcpy (`0x0148af8e`), plus one
direct call each from D2M and Bumper. The 3410's `game_sound_3b2510` is
byte-identical at `0x011de8d8` (`tone_play_3410_twin_11de8d8`), but on the
3510 it is a firmware tone routine that the games do not call.

## How Kart Racing draws

Static, from `kart_road_draw_1406144` and the setup around `0x0140afde`.
Everything is drawn as retained objects in the library's scene tree (see
`games_library_3510.md`):

- The horizon is a 120 x 20 bitmap at (0, 4), moved sideways with
  `game_obj_move_142e638`, so it can shift about 12 px either way on the 96 px
  screen. Inferred: one backdrop per track.
- The road is 65 rows of two 1-pixel-tall line objects (RAM `0x0003cc74`,
  `row * 8 + side * 4`). Each frame the renderer walks the rows from `0x40` up
  to a horizon row (`0x1c`, `0xd` or `0x17` by segment type). It computes the
  left and right road edges with curvature from a per-row depth table
  (`kart_row_depth_150912c`), then sets or hides each row's lines. That is a
  pseudo-3D road, Outrun style, drawn one scanline at a time.
- Karts and roadside objects are sprites picked from four pre-drawn sizes by
  distance (thresholds 5, 15 and 25). Nothing is scaled at run time.

Inferred, for the port: this suits the Game Boy. The road can be a line-by-line
scroll effect over a pre-drawn road band, as in F-1 Race, or a road band redrawn
into tiles each frame. The horizon becomes a scrolled background strip, and
every sprite is 20 px or smaller.

## Next

- Kart Racing is the first port target. Map it: the track format, the
  segment and curvature math, opponent logic, laps and timing.
- Build the Unicorn harness at the library boundary
  (`games_library_3510.md`), so Kart Racing can be run for reference frames.
