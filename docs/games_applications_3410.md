# The 3410's games: application map

The Nokia 3410 Games menu offers Select game, Download game, Settings and
More games; Select game lists Snake II, Space Impact, Bumper, Bantumi and
Link5. This document maps how they are reached and dispatched, as the
starting point for one map per game. It is the 3410 counterpart of
`games_applications_3310.md`; `games_survey_3410.md` compares the two phones'
games statically. Snake II has its own map, `games_snake2_3410.md`.

Addresses apply to one image only: NHM-2 v5.46 with PPM E and the virgin PMM,
`0x370000` bytes at flash base `0x200000` (`make normalize-3410`).

| | |
|---|---|
| SHA-1 | `e650b8a289b434f2c8260c68e44e70e84e41b4cc` |

Each conclusion is marked **static** (read from code or data), **runtime**
(seen in MAME) or **inferred**. Nothing derived from the firmware is in the
tree: names live in `ghidra/symbols/3410.csv`, evidence notes in
`docs/data/games_function_notes_3410.json`, and decompiled text and frames
stay under the ignored `run_games_3410/` and `run_3410_*/`.

## Reaching the games

Runtime. The 3410 runs with the radio disabled, as its menu gate does; the
UI takes keys from 16 s after boot and the first `enter` opens the main
menu at Messages. Games is entry 7, four `up`s away (Services 10, Extras 9,
Applications 8, Games 7):

```
enter                   main menu (Messages)
up x4                   Games
enter                   Games: Select game, Download game, Settings, More games
enter                   Select game: Snake II, Space Impact, Bumper, Bantumi, Link5
down x n, enter         the game's title animation
```

Each title then gives way to the game's own menu (Snake II: New game, High
scores, Options; Bumper: New game, High scores, Tables; Bantumi and Link5:
New game, Options, Instructions), and Enter during play pauses into it with
Continue first.

```
make run-keys GAMES_PRODUCT=3410 RUN_DIR=run_3410 SECONDS=40 \
  KEYS=enter,wait1500,up,wait300,up,wait300,up,wait300,up,wait1000,enter,wait1500,enter,wait1500,enter,wait3000,enter,wait3000,enter,wait4000
```

starts Snake II and pauses it; add `down,wait500` pairs before the third
`enter` for the others. `mame_nokia_3410_games_probe.lua` (as
`RUN_EXTRA_ARGS='-debug -debugger none -autoboot_script
../mame_nokia_3410_games_probe.lua'`) logs every handler call.

## Dispatch

Static, confirmed at runtime. There is no shared games dispatcher as on the
3310. Each game is an application with its own handler,
`handler(event, a, b)`, listed in `games_handlers_4c57ec` in the Select game
order and ending with 0:

| Handler | Game |
|---|---|
| `snake2_handler_24f8ec` | Snake II |
| `si_handler_25c974` | Space Impact |
| `bumper_handler_2d6d1c` | Bumper |
| `bantumi_handler_2e9bc8` | Bantumi |
| `link5_handler_32ae6e` | Link5 |

`games_broadcast_3bf990` walks the table and calls every handler with event
7 (runtime: once, 3.6 s after boot). Inferred: the games load their saved
settings there. The games share helpers around `0x3b24fc`..`0x3b29f4`
(static: called by all five).

Bumper was missing from the static survey: it has no 3310 counterpart.

## Events

Runtime, the same for all five games:

| Event | Seen |
|---:|---|
| `0x07` | the boot broadcast |
| `0x0e` | the game chosen in Select game; its title starts |
| `0x00` | timer: the title's frames, then the game's ticks |
| `0x0a` (a = 1), `0x14`, `0x0c` | New game chosen in the game's menu, in that order within 1 ms |
| `0x03` | Enter during play (pause), or Enter on the title (Link5) |

The handlers also switch on `0x09`, `0x0b`, `0x0d`, `0x11`, `0x12` and
`0x16` (static), not yet seen.

Intervals between `0x00` events after New game, from one run each and before
the levels are known (runtime, approximate):

| Game | Interval |
|---|---|
| Snake II | 217 ms |
| Space Impact | 108..109 ms |
| Bumper | 77 ms, with longer gaps |
| Bantumi | 85..101 ms |
| Link5 | about 290 ms |
