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
(inferred: a dance-music app, its full name is in compressed text). There is no
Snake and no Bantumi. The MCU also holds a game engine for downloadable games
(`engine_app_isa.c`, `engine_download_isa.c`, `engine_scoresend_isa.c`,
`application/x-NokiaGameData`, code around `0x01428000`–`0x0142c600`); the
built-in games are native code, not engine data.

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
message handlers. The two read so far (Kart Racing and D2M) switch on the
same messages: 3, 7, 9, 10, 0xb, 0xd, 0xe, 0x11 and 0x12. Each game calls `0x0142d174` exactly once,
with its own id in `r0`:

| Handler | Id | Game |
|---|---|---|
| `0x01418c58` | `0x30` | Bumper |
| `0x01422a70` | `0x3b` | D2M |
| `0x0142144c` | `0x3d` | Link5 |
| `0x0140e758` | `0x43` | Space Impact |
| `0x014047f0` | `0x4b` | Kart Racing |

Bumper, Space Impact and Link5 are pinned by the code matches above. Inferred:
the ids rise in the PPM's tune order, which places D2M and Kart Racing; an
alphabetical order would put Space Impact last, which the code match rules
out. That makes `0x0142d174` a tune or resource lookup by id
(`game_tune_id_142d174`), not yet read.

Layout, inferred from the handlers and the matches: Kart Racing
`0x01404000`–`0x0140e000` (the largest, and new), Space Impact to
`0x01416700`, Bumper to `0x0141ce00`, Link5 to `0x01422a00`, D2M to about
`0x01428000`, then the download engine and a shared game library at
`0x0142d000`–`0x01430000` that every game calls. In that library,
`0x0142df7a` matches the first 48 bytes of the 3410's
`game_vibrator_3b25d4`. The 3410's whole `game_sound_3b2510` (54 bytes) is
byte-identical at `0x011de8d8`, but the games
reach sound through the library, not directly.

## Next

- Name the shared game library at `0x0142d000` (drawing, keys, timers, sound),
  since everything a Unicorn harness has to stub goes through it.
- Map Space Impact first, pairing functions with the 3410's
  (`games_si_3410_functions.md`), then Kart Racing, which has no reference.
