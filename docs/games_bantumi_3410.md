# Bantumi on the 3410: application map

The Nokia 3410's Bantumi, mapped to re-implement it in C and check the
result against the firmware in MAME. It is the 3310's game
(`games_bantumi_3310.md`) rebuilt on the 3410's graphics library (see
"Draw modes" and "Draw order" in `games_si_3410.md`) for a 96 x 65 screen:
the same rules, the same hand going from pit to pit and the same search
with its two mistakes, with a title, a board that slides in and out, a
choice of 3 to 5 beans, a pass on the first turn and five Instructions
demos. Only what differs from the 3310 is described here.

Addresses apply to one image only: NHM-2 v5.46 with PPM E and the virgin
PMM (`make normalize-3410`). Each conclusion is marked **static** (read from
code or data), **runtime** (seen in MAME) or **inferred**. Nothing derived
from the firmware is in the tree; decompiled text and frames stay under the
ignored `run_games_3410/` and `run_3410_*/`.

## Reaching the game

Runtime. Games, Select game, then Bantumi, the fourth entry:

```
make run-keys GAMES_PRODUCT=3410 RUN_DIR=$PWD/run_3410_bantumi SECONDS=120 \
  KEYS=enter,wait1500,up,wait300,up,wait300,up,wait300,up,wait1000,enter,wait1500,enter,wait1500,down,wait500,down,wait500,down,wait500,enter,wait5000,enter,wait3000 \
  RUN_ENV="B_LEVEL=2" \
  RUN_EXTRA_ARGS="-autoboot_script $PWD/mame_nokia_3410_bantumi_bot.lua -debug -debugger none"
```

`mame_nokia_3410_bantumi_bot.lua` plays the game with the phone's keys
(4, 6 and 5; * for hints at level 1, # to pass, Menu to pause and Continue)
and logs every handler call, period, sound and close for a replay; its
header lists its switches.

The title ends by itself into the game's menu: New game, Options,
Instructions (Continue first while a game is paused). Options is Game
options: No. of beans (3, 4 or 5 beans) and Level (five bars). Runtime: on
this image's NV the beans are 3.

## Handler and events

Static, runtime. `bantumi_handler_2e9bc8(event, a, b)`:

| Event | Action |
|---:|---|
| `0x00`, `0x01` | timer, key down (a: the key's code): the title (`game_title_tick_3eb6d4`) while its flag (state +0x2c) is set, a demo (`bantumi_demo_tick_2e9a10`) while state +0x28 is set, else the game (`bantumi_event_2e9340(event, a)`) |
| `0x03` | Menu: in a demo, the demo ends and the game closes; on the title, it closes; in a game, `bantumi_suspend_2e9118` |
| `0x07` | boot: the settings records (`bantumi_boot_2e9040`) |
| `0x09` | a demo, a = 1..5 (`bantumi_demo_start_2e8fbc`) |
| `0x0a` | New game (`bantumi_new_game_2e8efc(0)`) |
| `0x0c` | after New game: the closed box drawn (`bantumi_board_draw_2e899e(3)`) unless continued; period 100 |
| `0x0d` | Continue, b the saved state (`bantumi_resume_2e8dc4`); period 100 |
| `0x0e` | the title (`game_title_start_3eb790`) |

Runtime: Continue is `0x0a` then `0x0d` at once, and the game then stands
still until a key, which starts the timer again. Key codes are the digits,
10 for * and 11 for #; key up is event 2, which the game ignores.

The framework redraws the screen after every event (runtime: the board's
slide out shows although nothing asks for it), except the event that
closes the game, a demo's first event (its text stays up until the first
tick) and Menu.

## State

Static, runtime. Game state `bantumi_state_1272bc`, 0x30 bytes, the block
`bantumi_suspend_2e9118` saves: the 3310's layout (pits +0, cursor +0xe,
chosen +0xf, hand's pit +0x10, turn u32 +0x14, countdown +0x18, level
+0x19, pit sown +0x1a, beans in hand +0x1b, thinking frame +0x1c and ticks
+0x1d, sowing u32 +0x20, capture store +0x24), then +0x28 the demo, +0x2a
u16 its step, +0x2c the title's flag, +0x2d set at New game and cleared by
the first sow: # (code 11) then ends the turn (`bantumi_turn_end_2e8b84(1)`),
handing the first move to the phone.

Drawing state `bantumi_ui_12714c`: +0 continued, +1 the board's frame
(3 closed .. 0 open), +2 the slide's step, +3 a toggle, +4 and +5 the
winner's blink (shown, ticks), +8 hand closed, +0xc board, +0x10 hand,
+0x14 thinking picture, +0x1c the second demo's arrow, +0x20 the hand's
animation (the 3310's), +0x24 its counter, +0x25.. x, y, target x, y, and
from +0x44 the hands' four descriptors in RAM (open below, open above,
closed above, closed below). `bantumi_digit_pics_127240` holds each pit's
units and tens pictures.

Runtime: after power-on +4 is 0 and +5 is 5; nothing sets them at New
game, so the blink goes on from the last game.

## Pictures

Static. 24-byte descriptors, the graphics library's:

| Descriptors | Pictures |
|---|---|
| `0x4b4754` | the board: 96 x 60 open (`0x4b4454`), then three 84 x 48 frames of the box closing (`0x4a8434`, `0x4a862c`, `0x4a8824`) |
| `0x4b4828` | ten 3 x 5 digits from `0x4b47b4`, 3 bytes apart |
| `0x4becf8` | eight 16 x 16 thinking pictures from `0x4a8334` |
| RAM | hands, each with a mask: 12 x 16 open (`0x4a8a1c`/`0x4a8a4c` below, `0x4a8a34`/`0x4a8a64` above), 11 x 13 closed (`0x4a8a7c`/`0x4a8aac` below, `0x4a8a94`/`0x4a8ac4` above) |
| `0x4b4a80`, `0x4b4a98` | the second demo's keypad (21 x 24) and arrow (5 x 4) |
| `0x4b6384`, `0x4b639c` | the title's background (84 x 48) and its six small pictures |

The pit table `bantumi_pit_xy_4beccc` is the 3310's format with the
3410's places (see `games_survey_3410.md`).

Static, runtime: the hand is one picture in mode `0x10` through its mask:
where the mask is set the picture's bits are copied, elsewhere the screen
is left (the image's bits all lie within the mask's). The board, the
thinking picture and the phone's digits are `0x10` (copy); the player's
digits, its row and store, are `0x11`, which the blitter does as xor. The
winner's store: the player's blinks between modes 0 and `0x11` every sixth
tick of the game-over pause; the phone's gets `0x14` (copy and the blink
plane), which MAME's frames do not show blinking.

Order (`bantumi_restack_2e8718`, after every picture made): the board
first, the hand and the thinking picture last. `bantumi_hand_draw_2e879c`
frees the thinking picture, and the hand before unless told to keep it, in
which case the old one stays on the screen.

## The game, against the 3310's

Static, confirmed by the replays below:

- The search (`bantumi_ai_start_3b8180`, `bantumi_ai_step_3b8348`,
  `bantumi_ai_child_3b806c`, `bantumi_ai_close_3b7ff4`,
  `bantumi_ai_next_move_3b82f8`) is the 3310's, 0x20-byte nodes, 100 steps
  a tick, depth 2 x level - 1 and 8 at level 5, 5 for a hint, the phone's
  capture tested on the live board and given to the player's store. It
  checks the rows for empty on every step rather than once a node, which
  comes to the same.
- The tick is 100 ms throughout.
- The hand (`bantumi_hand_path_2e91c0`) goes as on the 3310 and, to a
  store, to (store x, store y - 4) from the player's row and (store x,
  store y + 7) from the phone's. Above the pits, arriving, the open hand
  stops 3 rows short and drops in as it closes.
- Digits (`bantumi_pit_draw_2e8830`): one at (x + 4, y + 2), (x + 6,
  y + 5) in a store; from ten, the tens at (x + 1, y + 2) and the units at
  (x + 5, y + 2), in a store (x + 3, y + 5) and (x + 7, y + 5).
- A bean dropped is sound `0xfa9` at once (record `0x17`, the 3310's
  `0x1b`). Every tick of the game-over pause sounds `0xfa4` when the
  player won, else `0xfa2`.
- The intro: the closed box is made at x 48 and moved to x 40 - 8 n over
  six ticks, then opens a frame every other tick; the player then moves.
  Over: after the 40-tick pause the digits are freed and the box closes a
  frame every other tick, then slides right 8 pixels a tick, a frame
  counted every other tick to 8, and the game closes back to its menu.
- Continue (`bantumi_resume_2e8dc4`): the board drawn afresh, the hand's
  animation, place and grip put back after it; a phone thinking starts its
  search again (`bantumi_turn_end_2e8b84(0)`), a hint likewise.

## Title

Static, runtime. `game_title_start_3eb790` frees every picture, makes the
background at (6, 8) and one small picture at the first of seven places in
RAM (`0x12e1dc`, read in MAME: (-10, -10), then the 3310's (23, 18),
(34, 23), (37, 33), (45, 19), (53, 15), (62, 27), not moved by the
background's offset), period 300. Each tick moves it to the next place
with frame step - 1, period 200 at step 3 and 300 at step 4; at step 7 the
title closes. A key closes it at once.

## Instructions

Runtime: five texts (strings 1943..1947), each followed by its demo,
event 9 with its number; a key during a demo ends it (event 3) and shows
the next text. After the fifth demo the first text comes again.

Static: `bantumi_demo_start_2e8fbc(n)` starts a game with 4 beans, the
board open and the player's turn, and for demo 4 every pit 2 but pit 2
with 12 and the stores 7, for demo 5 pits 1, 2, 7 and 8 with 1, 2, 2 and
3 and the stores 20. `bantumi_demo_tick_2e9a10` plays a script on the step
(state +0x2a), a key going down counting as a tick:

| Demo | Script |
|---:|---|
| 1 | sow the first pit, then ticks |
| 2 | the step counted first: 1 keypad at (60, 0), 5 arrow at (74, 7), 7 key 6, 19 arrow to (62, 7), 21 key 4, 33 arrow to (68, 7), 35 key 5, 47 arrow freed; else ticks |
| 3..5 | 7 and 20 key 6, 30 and 80 key 5, 70 key 4; else ticks, the step counted after |

A demo ends, closing the game, when the phone's turn comes.

## Replay

The port `ports/nokia-gb-games` (`common/bantumi/bantumi.c`, shared with
the 3310's) replays the handler calls the bot logs (`make golden-bantumi`,
`make golden-bantumi-demos`, `make check-golden` in its `3410/`): four
games (level 1 with hints and a pass, 2, 3 with a pause and Continue, 5),
the five demos twice round and the title, every frame found in MAME's and
every sound the same.
