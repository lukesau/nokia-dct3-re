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

## Munkiki's Castles

The one Java game is not in Select game, which is the five native handlers
above and never asks the Java application manager. It is under More games,
the fourth entry of the Games menu, listed by its suite folder's name
(runtime):

```
enter                   main menu (Messages)
up x4                   Games
enter                   Games: Select game, Download game, Settings, More games
down x3, enter          More games: Munkiki        (softkeys Options, Back)
enter                   Options: Open, WAP access, Check version
enter                   Open: the KVM starts the MIDlet; its title, then its
                        menu: New game, High scores, Instructions, Options
```

```
make run-keys GAMES_PRODUCT=3410 RUN_DIR=run_3410_munkiki SECONDS=70 \
  KEYS=enter,wait1500,up,wait300,up,wait300,up,wait300,up,wait1000,enter,wait1500,down,wait800,down,wait800,down,wait800,enter,wait2500,enter,wait1500,enter,wait4000,enter,wait4000,enter,wait4000,enter,wait4000
```

Applications → Select app. (main menu entry 8) asks the same manager for
the other folder, MyApps, which the virgin PMM leaves empty, so it shows
"(empty)". Both lists come from the phone's own file system; MAME needs
nothing beyond the virgin PMM image.

### The Java file system in the PMM

Static, from the virgin PMM (`3410 virgin eeprom 005f0000.fls`, which MAME
loads at flash offset `0x370000`). The PMMCAT blocks at `0x20000`,
`0x30000`, `0x40000` and `0x50000` of the file hold a small file system
among the other records (`tools/dct3_pmm_catalog.py`'s `parse_catalog` on
each 64 KiB block): type `0xf491` records are directory entries, a UTF-16
name with its length first, then fixed fields; type `0xf490` records are file
contents. Inferred from the entries: a directory's record ends in a list of
`(1, index)` pairs naming its children; a file's record carries the index of
its contents record and of its parent.

| Record | Name | What |
|---|---|---|
| `0xf491/1` | PMM | the root directory, child Java |
| `0xf491/2` | Java | children MyApps, JavaGames, preinstalled |
| `0xf491/3` | MyApps | empty |
| `0xf491/4` | JavaGames | child Munkiki |
| `0xf491/0` | Munkiki | children RMS, Munkiki.jar, Munkiki.jad |
| `0xf491/5` | RMS | the suite's record stores, empty |
| `0xf491/6` | Munkiki.jar | contents `0xf490/0`, 40888 bytes, the JAR |
| `0xf491/7` | Munkiki.jad | contents `0xf490/1`, 199 bytes, the manifest (`Nokia-MIDlet-Category: Game`) |
| `0xf491/8` | preinstalled | contents `0xf490/2`, the one byte `1` |

The virgin image has them spread over the `0x30000` and `0x40000` blocks.
Runtime: the first boot compacts the PMM, copying the live records into the
`0x20000` block and erasing the `0x40000` and `0x50000` ones; the Java
records survive it unchanged.

### The application manager

Static, confirmed at runtime with the breakpoints below. The manager runs
as task `0x44`; its event handler is `jam_handler_333ac8(event)`:

| Event | Does |
|---:|---|
| `0x5e2` | at boot: `fs_stat_31cfe0("/PMM/Java/preinstalled")`, and when it is missing, `fs_fopen_31d6da(path, "wb")`, writes `1`, closes |
| `0x5dc` | lists the current folder: `fs_stat_w_31cf3e` on it (must be a directory), then `jam_list_folder_3339ac`, which counts the entries with `fs_dir_count_w_31d28e(path, 2)`, walks them with `fs_find_first_w_31d7de(path, 2, &handle)` and posts one 28-byte entry per child to task `0x44`; with no entries it posts the "(empty)" entry from `jam_empty_entry_333350` |

The current folder is `jam_folder_path_12e078`, set by
`jam_set_folder_3dfc2c(mode)`: mode 1 is `java_games_path_4c3d8c`
("/PMM/Java/JavaGames", More games) and anything else
`my_apps_path_4c3d68` ("/PMM/Java/MyApps", Select app.), with the mode
kept in `jam_folder_is_games_12e07c`. The file API below the manager takes
UTF-16 paths (`fs_stat_w_31cf3e`, `fs_open_w_31cd76`,
`fs_find_first_w_31d7de`, `fs_dir_count_w_31d28e`); `fs_stat_31cfe0` and
`fs_fopen_31d6da` are ASCII wrappers that widen the path first.
`jam_jad_from_jar_333d30` (inferred) writes a suite's `.jad` next to its
`.jar` when the `.jad` is missing, from the JAR's manifest; the virgin PMM
already has it, so this is not seen.

To watch it, on top of the input exerciser with `-debug -debugger none`
(the exerciser's `-log` puts `logerror` in `error.log`):

```lua
dofile("../mame_nokia_dct3_input_exerciser.lua")
local dbg = manager.machine.devices[":maincpu"].debug
dbg:bpset(0x333ac8, "1", 'logerror "JAMEV %x\\n",r0; g')
dbg:bpset(0x31cf3e, "1", 'logerror "STATW %04x%04x%04x%04x%04x%04x%04x%04x\\n",maincpu.pw@(r0),maincpu.pw@(r0+2),maincpu.pw@(r0+4),maincpu.pw@(r0+6),maincpu.pw@(r0+8),maincpu.pw@(r0+0xa),maincpu.pw@(r0+0xc),maincpu.pw@(r0+0xe); g')
```

`maincpu.pw@` reads the MAD2's big-endian halfwords, so the dump reads as
the path's UTF-16. The debugger takes bare numbers as hex: `r0+10` is
`r0 + 0x10`. Name the link register `r14`: the debugger does not know
`lr`, and an action that uses it fails on its first hit and silences every
breakpoint in the script.
