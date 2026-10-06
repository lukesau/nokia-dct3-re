# Bantumi on the 3310: application map

Bantumi is the third entry of the 3310 Games menu: a six-pit mancala
(kalah) against the computer. This document maps it to the level needed to
re-implement it in C and check the result against the firmware in MAME. It
follows the conventions of `games_applications_3310.md` (Space Impact),
which describes the games framework, the sprite engine, the sound path and
the settings records the game shares; those are not repeated here.

Addresses apply to one image only: NHM-5 v6.39 with PPM E and the v.2 PMM,
2 MiB at flash base `0x200000`. Each conclusion is marked **static** (read
from code or data), **runtime** (seen in MAME) or **inferred**. Nothing
derived from the firmware is in the tree: names live in
`run_games_3310/symbols_bantumi.csv`, evidence notes in
`run_games_3310/notes_bantumi.json` (both fragments for the shared symbol
and notes files), and disassembly and frames stay outside the tree.

## Reaching the game

Runtime. From idle, with the exerciser's key names:

```
enter, enter            wake, open the main menu
up x5                   Games
enter                   Games list: Snake II, Space impact, Bantumi, Pairs II, Settings
down, down, enter       Bantumi title animation
enter                   skips the title into the game menu
enter                   New game
```

```
make run-keys GAMES_PRODUCT=3310 RUN_DIR=$PWD/run_bantumi SECONDS=60 \
  KEYS=enter,wait1000,enter,wait1200,up,up,up,up,up,wait800,enter,wait1000,down,down,wait500,enter,wait1500,enter,wait1500,enter,wait30000
```

With that timeline the game's new-game event arrives at 18.3 s and the
player can move at 19.8 s. Without a language change the phone runs in
Russian; nothing in the game depends on the language.

There is no two-player mode (static): the game has only two sides, the
player (turn value 3) and the computer (4), and every computer turn starts
the search. The strings '1 player' / '2 players' are not used by it.

## Menus and the level setting

- Runtime: the game menu has New game, Level and Instructions (three
  entries, English and Russian). There is no Top score entry. `enter`
  during a game pauses it (framework event `0x34`, suspend) into a menu
  with Continue first; Continue sends `0x33` and `0x35` (resume) and the
  game goes on where it was.
- Runtime: the title ends on its own about 3.3 s after it starts and opens
  the menu; `enter` skips it.
- Runtime: Level shows the 'Level:' page with five bars (`down` lowers,
  OK stores and returns to the menu); the setting is
  kept in the game's record (`games_records_10f9e0` + 2 * `0x2c`, the byte
  at +4, `0x10fa3c`), 0..4. `games_ctx_load_2dbc7c` hands it to the game as
  ctx+0x16 = setting + 1, so the game sees levels 1..5 (state+0x19).
  Runtime: on this image's NV the setting is 4 (level 5, the hardest),
  from the PMM's saved record; choosing the lowest bar gave level 1.
- Static: the level changes only the computer's search depth (below) and
  whether `*` gives a hint (level 1 only). Nothing else reads it.
- Runtime: Instructions are one text in pages (More cycles through them,
  `c` leaves). It says: play against the phone, 4 and 6 pick a pot, 5
  sows; ending in your big pot gives another go, ending in your empty pot
  takes the opponent's pot; most beans win.
- The title handler for id `0x82` is `bantumi_title_handler_2d7b3c`
  (static, from the compare chain in `games_dispatch_2dbd2a`). See Title.

## Dispatch, events and return codes

Static. `bantumi_handler_2b2398(event, ctx)`: events `0x24` and `0x2b`
(new game) set ctx+0xc = 120 and call `bantumi_new_game_2b1c10`; every other
event goes to `bantumi_event_2b1cc0`.

| Game event | Action | Returns |
|---:|---|---|
| `0x24`, `0x2b` | new game | `0x16` (start the 120 ms tick), `2` if the 45 sprites cannot be allocated |
| `0x01` tick | everything that moves; see One tick | `0x21`, `1`, `0x1b`, `0x1e` |
| `0x04` scroll down, `0x0d` key 4 | cursor one pit left, if > 0 | `0x21` |
| `0x05` scroll up, `0x0f` key 6 | cursor one pit right, if < 5 | `0x21` |
| `0x0e` key 5, `0x09` key 0, `0x08` | sow the pit under the cursor, if it is not empty | `0x16` with ctx+0xc = 120 |
| `0x16` key `*` | hint, level 1 only | `0x21` |
| `0x13`, `0x15`, `0x17`, `0x18`, `0x1a`, `0x1c`, `0x1d` | if a search is running (turn 4 or 6), throw it away and start it again from the root | `5` |
| `0x33`, `0x34` | ctx+4 = `0x10e1f8`, ctx+0 = `0x28`: only the game state is saved | `1` |
| `0x35` resume | re-allocate 45 sprites, redraw (`bantumi_draw_board_2b1b34(0)`), ctx+0xe = 0, ctx+0xc = 120 unless the game is over | `1` |
| anything else, key repeats (code + `0x80`) | ignored | `1` |

- Runtime: in English, key 6 gave event `0x0f`, `down` `0x04`, `up`
  `0x05`, `*` `0x16` (a hint), `#` `0x14` (ignored) and `0` `0x09`, which
  sowed the pit under the cursor. A held key also sends its code + `0x80`
  every 12 timer units; those are ignored.
- Keys act only on the player's turn (state+0x14 = 3) with no hand
  animation running (`0x10e1bc` = 0); everything else is ignored, so there
  is no key buffering.
- No key produces game event `0x08` in `games_app_handler_2dbdd4`'s
  translation (inferred from the translation table); it is handled like
  key 5.
- The `#` key does nothing.
- The cursor is not moved by the game: after a move (or an extra move)
  the open hand comes back over the pit last chosen, empty or not
  (runtime: frames after an extra turn from pit 2). Only a hint moves it.
- Return `0x1e` is game over for this game: the framework stops the
  timers and posts message `0x5134` (`0x18`, used by the other games, posts
  `0x5133`). ctx+0x10 holds the result (see Game over).
- A sound is returned as a pending flag (`0x10e179`): when it is set at the
  end of the event, the handler clears it and returns `0x1b` with the sound
  id in ctx+0x14 instead of the code it was going to return (`0x21`).

## State

Two RAM blocks. Multi-byte fields are big-endian.

Game state `bantumi_state_10e1f8`, `0x28` bytes, the block the framework
saves on suspend (static, with the pits, turn and level confirmed at
runtime):

| Offset | Size | Field |
|---:|---:|---|
| +0x00 | 14 x s8 | pits: 0..5 the player's row left to right, 6 the player's store (right), 7..12 the computer's row right to left, 13 the computer's store (left) |
| +0x0e | u8 | cursor, 0..5 |
| +0x0f | u8 | the computer's chosen pit (7..12) |
| +0x10 | u8 | pit the hand is at; chooses the hand's row (<= 6 bottom); `0xff` while the computer thinks |
| +0x14 | u32 | turn: 0 intro, 1 player's hand going to a pit (pick-up or capture), 2 the computer's, 3 player's turn and sowing, 4 computer thinking and sowing, 5 game over pause, 6 hint search, 7 finished |
| +0x18 | u8 | game-over countdown, 40 ticks |
| +0x19 | u8 | level 1..5 (ctx+0x16) |
| +0x1a, +0x1b | u8 | a toggle flipped every 5 ticks on the player's turn (from 5); nothing reads it, but it forces a `0x21` return |
| +0x1c | u8 | pit being sown into |
| +0x1d | u8 | seeds in the hand |
| +0x1e | u8 | thinking animation frame, 0..7 |
| +0x1f | u8 | ticks to the next thinking frame (2) |
| +0x20 | u32 | sowing sub-state: 0 idle, 1 sowing, 2 capture with a non-empty opposite pit, 3 capture into the store |
| +0x24 | u8 | store that receives the capture (6 or 13) |

Drawing block `bantumi_ui_10e178` (static):

| Address | Field |
|---|---|
| `0x10e178` | u8: the player won (blink the player's store) |
| `0x10e179` | u8: sound pending |
| `0x10e17a` | u8: intro slide step, 0..5 |
| `0x10e17b` | u8: intro toggle |
| `0x10e17c` | u8: intro board frame, 3..0 |
| `0x10e17d` | u8: draw mode of the winner's store digits, 2 or 6 |
| `0x10e180`, `0x10e184` | u16: hand mask and hand image sprite ids |
| `0x10e182` | u16: board sprite id |
| `0x10e186` | u16: thinking sprite id |
| `0x10e188` | u32: hand closed (carrying seeds) |
| `0x10e18c`, `0x10e198` | RAM image descriptors of the open hand's mask and image (bitmaps at `0x10e274` and `0x10e220`, 12 x 2 bands each; 36 bytes are copied) |
| `0x10e1a4`, `0x10e1b0` | RAM descriptors of the closed hand's mask and image (bitmaps at `0x10e1c8` and `0x10e1e0`, 11 x 2 bands) |
| `0x10e1bc` | u32: hand animation state, 0 idle, 1 wait, 2 move, 3 arrive, 4 act |
| `0x10e1c0` | u8: hand animation counter |
| `0x10e1c1`, `0x10e1c2` | s8: hand x, y |
| `0x10e1c3`, `0x10e1c4` | s8: hand target x, y |
| `0x10e2e0` | 14 x {u16 units digit sprite, u16 tens digit sprite}, by pit |

Search block `bantumi_ai_10f404` (static): +0 u8 chosen pit, +1 u8 depth
remaining, +4 root node, +8 current node. Nodes are `0x20`-byte heap
records (`game_alloc_zeroed_2dd6dc`): +0 u32 side (3 player, 4 computer),
+4 s16 alpha, +6 s16 beta, +8 s16 best, +0xa 14 pits, +0x18 u8 first move
(`0x0e` = not chosen yet), +0x19 u8 move counter, +0x1c parent.

## Rules as implemented

Static, from `bantumi_event_2b1cc0`'s tick path, `bantumi_turn_end_2b1898`
and `bantumi_pick_2b1ad0`. Runtime: applying these rules to the pit
picked reproduces the board and the extra-move flag logged at the end of
every one of 157 moves (player and computer, with captures and extra
moves) in the five logged games.

- Start: four seeds in each of the twelve pits, stores empty. The player
  always moves first.
- A move takes all seeds of one of the mover's non-empty pits and drops
  one in each following pit counter-clockwise: the player 0..5, 6, 7..12,
  skipping 13; the computer 7..12, 13, 0..5, skipping 6. The emptied
  pit is sown into again on a lap of 13 or more seeds.
- Last seed in the mover's own store: the mover moves again
  (`bantumi_turn_end_2b1898(0)`).
- Last seed in an empty pit of the mover's own row (the pit holds 1
  afterwards): that seed and all seeds of the opposite pit (12 - p) go to
  the mover's store, even when the opposite pit is empty (then only the
  one seed moves). The turn then passes.
- Otherwise the turn passes.
- After every move, including extra moves, the game ends when either row
  is empty: each row's remaining seeds go to its owner's store
  (`bantumi_side_empty_2b1732`), then the stores are compared.
- There are no other rules: no limit on laps, no forfeit, no choice of who
  starts.

## The computer player

Runtime-verified exactly: a Python model of the search below reproduced
the firmware's sequence of generated child positions, the number of ticks
and the chosen pit for all 110 computer searches of five logged games
(one per level, 2 to 10698 nodes each) and two hint searches (835 nodes);
112 of 112 agree. The logs
come from breakpoints on `bantumi_ai_child_2dd28e`, `bantumi_ai_step_2dd5ac`
and the end of the search.

The search is a depth-limited negamax with alpha-beta pruning over an
explicit node stack, run incrementally: 100 iterations per tick.

**Start** (`bantumi_ai_start_2dd3bc`, called at the end of the player's
move and on `*`): the root copies the live board. For the computer the
root's side is 4 and the depth is 2 x level - 1, with 9 replaced by 8:
levels 1..5 search 1, 3, 5, 7 and 8 plies. For a hint the side is 3 and
the depth 5 at any level. Root alpha -32000, beta 32000, best -32000; every
node starts with best -32000, first = none, counter 0.

A ply is one move; an extra move is a ply of the same side.

**Iteration** (`bantumi_ai_step_2dd5ac`), with `depth` a single global
counter (decremented when a child is made, incremented when a node is
closed):

```
if depth != 0 and cur.counter < 6 and cur.best < cur.beta:
    if cur.pits[0..5] all 0 or cur.pits[7..12] all 0:
        cur = close(cur, terminal=1)
    else:
        m = next_move(cur)
        if cur.counter <= 6 and cur.pits[m] != 0:
            cur = make_child(cur, m)
elif cur is not root:
    cur = close(cur, terminal=0)
else:
    the search is finished
```

**Move order** (`bantumi_ai_next_move_2dd554`, `bantumi_ai_first_move_2dd438`):
the first move tried is a heuristic pick; the others follow in pit order
(0..5, or 7..12 for the computer), skipping the heuristic one. With base
0 and store 6 for the player, base 7 and store 13 for the computer, the
heuristic pick is the first that applies of:

1. scanning k from the store down to the base, the first k whose seed
   count equals store - k (the move ends in the store). k = store itself
   matches when the store is empty; that "move" is then skipped as an
   empty pit, so with an empty store the order is plain pit order;
2. among the pits k (in increasing order) with c = pits[k] > 0,
   k + c < store and pits[k + c] = 0, the last one with the greatest
   pits[13 - (k + c)] (ties go to the later pit; note 13 - j, one past the
   true opposite pit 12 - j);
3. the pit with the most seeds, the first one on ties (if all are empty,
   the base pit).

`next_move` returns the heuristic pick on its first call; afterwards
i = counter++, and if i equals the pick, i = counter++ again; the
computer's moves add 7. The step skips a move when the counter has passed
6 or the pit is empty.

**Child** (`bantumi_ai_child_2dd28e`): copy the parent's pits, empty pit m
and sow its seeds as in the game (the computer skips 6 and wraps after
13; the player wraps after 12). If the last seed lands in the mover's
store the child keeps the parent's side, alpha and beta. Otherwise the
side flips, child alpha = -parent beta, child beta = -parent alpha, and
the capture is applied, with two bugs that a port must keep:

- player's move (side 3): if the child's pit p (< 6) now holds 1,
  child pit 6 += child pit (12 - p) + 1 and both pits are emptied
  (correct);
- computer's move (side 4): the test reads the **live game board**, not
  the child: if board[p] == 1 and p > 6, then child pit **6** (the
  player's store) += child pit (12 - p) + 1 and both are emptied. The
  computer credits its own captures to the player and only sees them where
  the real board happens to hold one seed.

**Evaluation** (`bantumi_ai_evaluate_2dd1c0`), from the computer's side:
v = pit 13 - pit 6; for a terminal node (a row empty) also add the
computer's row and subtract the player's row, then add 50 if v > 0 and
subtract 50 if v < 0. Negate for a side-3 node. 16-bit signed arithmetic.

**Close** (`bantumi_ai_close_2dd214`): if the node is terminal or depth is
0, best = evaluate(node, terminal). If the node's side differs from its
parent's, best = -best. If best > parent.best: parent.best = best, and if
the parent is the root, chosen = the move that produced the node (first
pick or counter - 1, + 7 for the computer). Then parent.alpha =
max(parent.alpha, parent.best), depth += 1, free the node, continue with
the parent. Strict comparisons: on ties the first move searched wins.

**Finish**: the root is freed. For the computer: turn = 2, state+0x10 =
state+0xf = chosen, open hand, and the hand animation to the chosen pit
starts. For a hint: the cursor is set to the chosen pit (0..5), turn = 3,
the thinking sprite is freed and the hand is drawn there; the player still
has to press 5.

**Delay**: the search starts when the player's move ends and runs 100
iterations per tick in turn 4, ending in the tick that reaches the
finish; the computer's move then starts on the next tick. The tick is
120 ms except on a game's first player turn, where it is 0 (see One tick):
a hint asked for then ran its 20 steps in 1.2 s instead of 2.4 s. Measured search lengths for the
opening reply (4 seeds per pit, player opened with pit 0): level 1 one
tick, level 2 two ticks, level 3 14, level 4 94, level 5 242 ticks
(31.5 s in MAME). Later positions in the logged level 5 game took 28 to
147 ticks.

**Hint**: `*` on the player's turn at level 1 only (state+0x19 == 1), when
no animation runs: turn = 6, the thinking animation starts, the hand
disappears and a depth-5 search for the player runs on the ticks.

## One tick

Static; tick period 120 ms (ctx+0xc = `0x78`), the same at every level.
The handler first looks at the hand animation (`0x10e1bc`), then at the
turn:

| Hand state | Action per tick |
|---:|---|
| 1 wait | counter (from 2) - 1; at 0 draw the hand at its start and go to 2 |
| 2 move | move x and y each at most 6 px toward the target; counter = 2; full redraw; at the target go to 3 |
| 3 arrive | first tick: hand closed if turn is 1 or 2 (grab), open otherwise (drop); redraw. Second tick: the action (below) |
| 4 act | one sowing step (below) |

Hand state 3, second tick: in turn 1 or 2 with a capture under way, move
the hand from the pit to the capturing store and empty the pit; turn back
to 3 or 4. In turn 1 or 2 otherwise (the pick-up), turn = 3 (state+0x10 =
cursor) or 4 (state+0x10 = chosen pit) and `bantumi_pick_2b1ad0` takes the
seeds: closed hand, pit emptied, seeds in hand, next pit = pit + 1, hand
animation to it, sub-state 1. In turns 3 and 4: closed hand, go to state 4.

Hand state 4, sub-state 1 (sow one seed): the current pit gets one seed,
the hand one less, sound `0x1b`. If the hand is now empty: in a store, the
same side moves again; in an empty own pit, a capture (sub-state 2 if the
opposite pit has seeds, 3 if not; turn 1 or 2; hand animation onto the pit
itself); else the turn passes. If seeds remain: next pit (skipping the
opponent's store, wrapping at 14) and a hand animation to it. Sub-state 2:
the capturing seed goes to the store, the hand moves to the opposite pit
and takes its seeds (sub-state 3); it is drawn open there with
`draw_hand(0)` (the branch at `0x2b20d4` goes to `0x2b200a`, past the
`movs r0, #1` before it), which frees the closed hand at the store. Sub-state 3: the seeds in hand go to
the store, the turn passes.

With no animation running:

| Turn | Per tick |
|---:|---|
| 0 | intro: board slide 5 ticks, then frames 2, 1, 0 every other tick; then ctx+0xc = 0 and turn 3 |
| 3 | nothing visible |
| 4 | state+0x10 = `0xff`; thinking frame every 2 ticks; 100 search iterations |
| 6 | the same for the hint |
| 5 | countdown from 40; when the player won, the player's store digits toggle between draw modes 2 and 6 every tick; at 0 turn 7, tick period 120 |
| 7 | game over: ctx+0xc = 0, ctx+0x10 = pit 6 - pit 13, return `0x1e` |

- Runtime: a seed costs 8 ticks (wait 2, move 3 for adjacent pits 13 px
  apart, arrive 2, act 1), 56 frames in MAME at 60 Hz; the pick-up of the
  chosen pit takes 6 ticks; the first seed lands 8 ticks after the pick-up.
- Static, runtime: after the intro the tick period is 0, so on the first
  player turn of a game ticks arrive about twice per 60 Hz frame (logged
  in MAME); they do nothing visible. The first sow key restores 120 ms for
  the rest of the game.

## Drawing

Static unless noted; positions in screen pixels on 84 x 48. All sprites
use the shared engine (45 sprites per game).

- Board: one full-screen 84 x 48 bitmap, mode 4 (opaque), layer 0, at
  (0, 0). Four variants in the descriptor array `bantumi_board_descs_31d0c0`
  (12-byte descriptors): 0 the open board, 1 and 2 opening frames, 3 the
  closed box used for the slide.
- Intro (runtime-confirmed in frames): new game draws the closed box (3)
  at x = 40, then each tick moves it to 40, 32, 24, 16, 8; then every other
  tick the board is rebuilt with frame 2, 1 and finally 0 with the digits
  and the hand.
- Pit positions: `bantumi_pit_xy_31d1ec`, 14 x bytes then 14 y bytes (the
  top-left of each pit box): pits 0..5 at x 4, 17, 30, 44, 57, 70, y 36;
  store 6 at (68, 16); pits 7..12 at x 70, 57, 44, 30, 17, 4, y 3; store
  13 at (3, 16).
- Seed counts are drawn with the shared 4 x 5 digits
  (`game_digit_sprites_10db68`), mode 2 (flip), layer 2, units sprite
  first. Pits: one digit at (x + 4, y + 2); two digits: tens at (x + 1),
  units at (x + 5). Stores: one digit at (x + 5, y + 5); two digits: tens
  at (x + 2), units at (x + 6). `bantumi_set_pit_2b1764(pit, n)` updates
  the digits and stores n.
- Hand: two sprites at the same position, a mask in mode 0 and the image in
  mode 1, layer 3. Open hand 12 x 16: mask `0x31d120`, image `0x31d0f0`
  in the bottom row (state+0x10 <= 6), mask `0x31d138`, image `0x31d108`
  in the top row. Closed hand 11 x 13: mask `0x31d198`, image `0x31d150`
  bottom, mask `0x31d180`, image `0x31d168` top. The bitmaps are copied to
  RAM and shifted up when the hand's y is negative, so the hand is clipped
  at the top edge (a shift of more than 8 rows loses the picture
  altogether: ARM shifts by the register's low byte). There is one RAM
  copy and one descriptor per picture, so every hand sprite made from it
  shows what was copied last, at the height set last. `draw_hand(0)`
  frees the old pair first; `draw_hand(1)` does not, and the old pair
  stays in the list. Runtime (the port's replay): the widths, 12 and 11,
  and the mask/image roles agree with every frame of four MAME games.
  `bantumi_draw_hand_2b1520`.
- Hand positions (`bantumi_hand_path_2b1a04(from, to)`), with (X, Y) the
  pit table: start (X[from] - 1, Y[from] - 14) and target (X[to] - 1,
  Y[to] - 4) when picking up (turn 1, 2) or Y[to] - 11 when sowing, for a
  hand in the bottom row; start (X[from] - 1, Y[from] + 10) and target
  Y[to] (picking up), Y[to] + 10 (from store 13) or Y[to] + 7 in the top
  row. A hand leaving 13, or 12 on the player's turn, starts at (X[13],
  Y[13]); leaving 6, or 5 on the computer's turn, at (X[6], Y[6]).
- On the player's turn the open hand is at (X[cursor] - 1, Y[cursor] - 14).
- Thinking: a 16 x 16 animation of 8 frames (`bantumi_think_descs_31d22c`),
  mode 4, layer 2, at (34, 16), next frame every 2 ticks; shown while the
  computer or the hint searches.
- Bitmap format as in the Space Impact map: bands of 8 rows, one byte per
  column, bit 0 the top row. Descriptors are {u32 bitmap, u32 0, u8 width,
  u8 height, u16 0}, big-endian.
- Game over: when the player lost, the computer's store digits get draw
  mode 5 (blinking plane); when the player won, the player's store digits
  toggle between modes 2 and 6 each tick (runtime: the losing case blinks
  the left store in MAME frames).

## Title

Static. `bantumi_title_handler_2d7b3c` (event `0x24`/`0x2b`) saves ctx+0xc
and ctx+0xe, sets a 250 ms tick and draws a full-screen 84 x 48 picture
(`0x3185c4`, mode 4) with six small sprites over it, hidden (mode 6)
(descriptors `0x3185d0`..`0x31860c`; at (23, 18), (34, 23), (37, 33),
(45, 19), (53, 15), (62, 27)). Each tick shows the next one and hides the
previous; the third overlay stays 70 ms, the others 250 ms. After the
sixth the sequence runs once more, the last frame holds 700 ms, and the
next tick ends the title (return `0x10`, which makes the framework post
message `0x5e8`) into the game menu. Runtime: the logged return times
follow this (14, 15, 5, 14, ... frames apart, 41 frames for the 700 ms
hold); the title lasts 3.3 s. Any key (events
4..`0x18`, `0x1a`, `0x1c`, `0x1d`) ends it at once.

## Sounds

Static, runtime: the only sound is `0x1b`, played for every seed sown
(not for the seeds a capture moves to the store), through the pending flag and
return `0x1b`. 135 of them were logged in one game, all with class
argument `0xf1`. Its record in `sound_table_321e6c` points to the script
at `0x321c1c`, class 0, no flags (static): notes `0x8b` x 3 units, then
`0x7f` x 3 twice, which on the scale measured for Space Impact is
1047 Hz for 3 units and 523 Hz for 6 (inferred; not measured for this
sound). Like the other game sounds it is silent unless both the game
sounds setting and the profile's warning and game tones are on. No sound marks game
over or a capture.

## Game over and top score

- Static: the countdown is 40 ticks (4.8 s at 120 ms) on the final board;
  then the game returns `0x1e` with ctx+0x10 = player's store - computer's
  store (signed) and the framework posts message `0x5134`.
- Runtime: for each sign of the result the framework (message `0x5134`,
  not traced) shows a different end; each text stays about 3 s and then
  the game menu opens:
  - result > 0: the games' fireworks (the pictures and timing in
    `games_snake2_3310.md`, Game over), with sound `0x22` as they start
    and again with the text, then 'Game over!' 'YOU WON!' (579);
  - result = 0: 'Game over!' (536) only, no sound;
  - result < 0: 'Game over!' 'You lost, sorry!' (577), no sound.

  Seen in English runs that set the board on the first intro tick to one
  move from the end (one seed in pit 5 and in pit 7): returns `0x1e` with
  ctx+0x10 = 26, 0 and -38, 286 frames (41 ticks) after the last move.
- Runtime: the losing store blinks through the LCD's blink plane (about
  0.47 s per phase in MAME); the winning store's digits flip on and off
  every tick.
- Bantumi keeps no top score: there is no Top score page and the code
  never writes the record's +2 (static; the PMM dump's Bantumi record has
  top score 0 and level 4).

## Random numbers

Static: none. The game and the search are deterministic; the same moves
give the same replies at a given level.

## Not done

- The message `0x5134` handler was not traced; what it shows is known
  from runs (see Game over and top score, and the fireworks in
  `games_snake2_3310.md`).
- A C port exists (nokia-gb-games/3310, `core/bantumi.c`) and replays four
  games the firmware played in MAME frame for frame: levels 1 (with
  hints), 2, 3 (paused) and 5, two of them to the end. The games were
  played by `mame_nokia_3310_bantumi_bot.lua`, which presses 4, 6, 5 and
  `*` and logs every event the game is handed (`GEV 2 <event>`).
- The RAM descriptors' bitmap pointers and widths (set outside the game
  code) were not read; the port's frames fix the widths at 12 and 11.
- The breakpoint scripts used here are
  `mame_nokia_3310_bantumi_probe.lua` (logs events, pits, pick-ups, turn
  ends, search nodes and returns; sets the level; auto-plays the lowest
  pit) and `mame_nokia_3310_bantumi_board.lua` (sets a board on the first
  intro tick). `tools/bantumi_ai_model.py` is a Python model of the search
  that replays a probe log and compares every search with the firmware's:
  `python3 tools/bantumi_ai_model.py RUN_DIR/error.log`.
- Resume while the computer is thinking (state+0x10 = `0xff`) and the
  interrupting events `0x13`..`0x1d` are static only.
- `sprite_full_redraw_2dd97c`'s flag at `0x111af9` is named from its use.

## Address map

Names are in `run_games_3310/symbols_bantumi.csv`, evidence in
`run_games_3310/notes_bantumi.json`.

| Address | Kind | Name | Evidence |
|---|---|---|---|
| `0x10e178` | label | `bantumi_ui_10e178` | Bantumi drawing block: +0 player-won flag, +1 sound pending (return 0x1b), +2..+4 intro slide step/toggle/board frame, +5 winner digits draw mode, +8/+0xc hand mask/image sprite ids, +0xa board sprite, +0xe thinking sprite, +0x10 hand closed, +0x14..+0x43 four RAM hand descriptors, +0x44 hand animation state (1 wait, 2 move, 3 arrive, 4 act), +0x48 counter, +0x49..+0x4c hand x,y and target x,y, +0x50/+0x68 closed-hand bitmaps. |
| `0x10e1f8` | label | `bantumi_state_10e1f8` | Bantumi game state, 0x28 bytes (the block saved on suspend, events 0x33/0x34): pits[14] (0..5 player, 6 player store, 7..12 computer, 13 computer store), +0xe cursor, +0xf computer's chosen pit, +0x10 hand pit (0xff while thinking), +0x14 u32 turn (0 intro, 1/2 hand to pit, 3 player, 4 computer, 5 game over pause, 6 hint, 7 done), +0x18 game-over countdown 40, +0x19 level 1..5, +0x1c sow pit, +0x1d seeds in hand, +0x1e/+0x1f thinking frame/countdown, +0x20 sow sub-state, +0x24 capture store. Runtime: pits, turn and level logged in MAME. |
| `0x10e2e0` | label | `bantumi_digit_sprites_10e2e0` | 14 x {u16 units digit sprite, u16 tens digit sprite}, one per pit, digits from game_digit_sprites_10db68 in draw mode 2. |
| `0x10f404` | label | `bantumi_ai_10f404` | Bantumi search block: +0 u8 chosen pit, +1 u8 depth remaining, +4 root node, +8 current node. Nodes are 0x20-byte heap records: +0 side (3 player, 4 computer), +4 alpha, +6 beta, +8 best (s16), +0xa pits[14], +0x18 first move (0xe none), +0x19 counter, +0x1c parent. |
| `0x110d60` | label | `games_title_state_110d60` | Bantumi title state: +0 second-pass flag, +1 step, +0x14/+0x16 saved ctx+0xc/+0xe, +0x24.. sprite ids of the picture and six overlays. |
| `0x2b1520` | function | `bantumi_draw_hand_2b1520` | (arg) Draws the hand: arg 0 frees the old pair first. Open hand (0x10e188 == 0) 12x16 from 0x31d120/0x31d0f0 (bottom row, state+0x10 <= 6) or 0x31d138/0x31d108 (top); closed hand 11x13 from 0x31d198/0x31d150 or 0x31d180/0x31d168. Bitmaps are copied to RAM, shifted up and shortened when y < 0; mask sprite mode 0 then image mode 1, layer 3, at (0x10e1c1, 0x10e1c2). |
| `0x2b1732` | function | `bantumi_side_empty_2b1732` | Returns 1 when pits 0..5 or pits 7..12 are all empty. |
| `0x2b1764` | function | `bantumi_set_pit_2b1764` | (pit, n): sets the pit's count and updates its digit sprites. One digit at (x+4, y+2) for pits, (x+5, y+5) for stores; with two digits the tens sprite is created at (x+1 / x+2) and the units moved 4 px right; going back below 10 frees the tens sprite. |
| `0x2b1898` | function | `bantumi_turn_end_2b1898` | (arg) End of a move: hand idle, hand sprites freed; arg 1 passes the turn (3 <-> 4), arg 0 keeps it (last seed in the store). If a row is empty, sweeps each row into its owner's store, sets the won flag or blinks the computer's store (mode 5) and turn 5. Else: player's turn draws the open hand at the cursor; computer's turn starts the search (0x2dd3bc) and the thinking sprite at (34,16). Runtime: logged at every move end. |
| `0x2b1a04` | function | `bantumi_hand_path_2b1a04` | (from, to) Starts a hand animation: state 1, counter 2, start and target positions from the pit table 0x31d1ec with row-dependent offsets (bottom row y-14 start, y-4 pick-up / y-11 sow target; top row y+10 start, y / y+7 / y+10 target); special starts at the stores when turning a corner. |
| `0x2b1ad0` | function | `bantumi_pick_2b1ad0` | (pit) Picks up a pit's seeds: next pit = pit + 1, hand animation, frees the thinking sprite (computer) or the hand pair (player), closed hand, seeds in hand = pit count, pit emptied, sow sub-state 1. Runtime: logged at each pick-up. |
| `0x2b1b34` | function | `bantumi_draw_board_2b1b34` | (frame) Resets all sprites and draws board frame 0x31d0c0 + 12*frame at (0,0), mode 4, layer 0. Frame 0 also draws the hand (or the thinking sprite when state+0x10 is 0xff) and creates the 14 digit sprites. Used by new game (frame 3), the intro (2, 1, 0) and resume. |
| `0x2b1c10` | function | `bantumi_new_game_2b1c10` | New game: 45 sprites, cursor 0, turn 0, four seeds per pit, stores 0, level = ctx+0x16, game-over countdown 40, closed board (frame 3) at x = 40, tick 120 ms; returns 0x16 (2 when the sprites cannot be allocated). |
| `0x2b1cc0` | function | `bantumi_event_2b1cc0` | Bantumi event handler: tick (hand animation states, sowing and captures, intro, search steps, game over), keys 4/6 and scroll (cursor), 5/0/event 8 (sow), * (hint at level 1), suspend/resume; returns 0x1b when a seed was dropped (sound 0x1b) and 0x1e at game over with ctx+0x10 = pit 6 - pit 13. |
| `0x2b2398` | function | `bantumi_handler_2b2398` | Game id 2 (Bantumi). Events 0x24/0x2b: ctx+0xc = 120, new game 0x2b1c10; others to 0x2b1cc0. Runtime: called through games_dispatch_2dbd2a with id 2 when Bantumi is played. |
| `0x2d79b0` | function | `bantumi_title_create_2d79b0` | Creates the title picture 0x3185c4 (mode 4) and six hidden overlay sprites (mode 6) at (23,18), (34,23), (37,33), (45,19), (53,15), (62,27). |
| `0x2d7a38` | function | `bantumi_title_init_2d7a38` | Title init: 7 sprites; draws the title unless the event was 0x24. |
| `0x2d7a64` | function | `bantumi_title_step_2d7a64` | Title step: hides the previous overlay, shows the current one (mode 4); returns 0x16. |
| `0x2d7a9c` | function | `bantumi_title_event_2d7a9c` | Title events: each tick advances the overlay (70 ms after step 3, 250 ms otherwise), two passes, 700 ms on the last frame, then returns 0x10 restoring ctx+0xc/+0xe; keys end it at once. |
| `0x2d7b3c` | function | `bantumi_title_handler_2d7b3c` | Game id 0x82: Bantumi title. Static: games_dispatch_2dbd2a calls it for id 0x82 with context 0x1111f8. Saves ctx+0xc/+0xe, sets a 250 ms tick. |
| `0x2dd1c0` | function | `bantumi_ai_evaluate_2dd1c0` | (terminal) Evaluates the current node: pit 13 - pit 6; terminal nodes add computer row - player row and +-50; negated for side 3. Runtime: model matches all logged searches. |
| `0x2dd214` | function | `bantumi_ai_close_2dd214` | (node, terminal) Closes a node: evaluate if terminal or depth 0; negate when the side differs from the parent's; raise parent best (records the chosen pit at the root), parent alpha = max(alpha, best); depth + 1; frees the node. |
| `0x2dd28e` | function | `bantumi_ai_child_2dd28e` | (parent, pit) Makes a child: copies pits, sows (computer skips 6, player wraps at 13); store landing keeps side and window, else side flips with (-beta, -alpha) and captures. Quirk: the computer's capture tests the live board 0x10e1f8 and is credited to pit 6. Runtime: child order logged and matched by the model. |
| `0x2dd3bc` | function | `bantumi_ai_start_2dd3bc` | Starts a search from the live board: computer side 4 with depth 2*level-1 (9 becomes 8), or for the hint (turn 6) side 3 depth 5. Root alpha -32000, beta 32000. |
| `0x2dd438` | function | `bantumi_ai_first_move_2dd438` | First move heuristic: a pit that ends in the store (scanning down from the store, which itself matches when empty), else the last pit with the largest capture value read at 13-(k+c), else the fullest pit. |
| `0x2dd554` | function | `bantumi_ai_next_move_2dd554` | Next move of the current node: the heuristic pick first, then pits in order skipping it; +7 for the computer. |
| `0x2dd5ac` | function | `bantumi_ai_step_2dd5ac` | One tick of search: up to 100 iterations; at the end the computer's choice goes to state+0xf/+0x10, turn 2 and a hand animation, or for a hint into the cursor with turn 3. Runtime: tick counts match the model (1 to 242 ticks). |
| `0x2dd698` | function | `bantumi_ai_abort_2dd698` | Frees every node of a running search (used before restarting it on interrupting events). |
| `0x2dd97c` | function | `sprite_full_redraw_2dd97c` | (flag) Writes 0x111af9 in the sprite engine block. Inferred: requests a full redraw; Bantumi calls it with 1 while the hand moves and on thinking frames. |
| `0x3185c4` | label | `bantumi_title_descs_3185c4` | Bantumi title: seven 12-byte descriptors, the 84x48 picture then six overlays (11x7, 7x10, 11x14, 8x12, 13x10, 11x8). |
| `0x31d0c0` | label | `bantumi_board_descs_31d0c0` | Four 12-byte descriptors of 84x48 board pictures: 0 open board, 1 and 2 opening frames, 3 closed box (intro slide). |
| `0x31d0f0` | label | `bantumi_hand_open_bottom_31d0f0` | Open hand image, bottom row, 12x16 (two bands of 12 bytes); drawn in mode 1. |
| `0x31d108` | label | `bantumi_hand_open_top_31d108` | Open hand image, top row, 12x16; mode 1. |
| `0x31d120` | label | `bantumi_hand_open_bottom_mask_31d120` | Open hand mask, bottom row, 12x16; mode 0. |
| `0x31d138` | label | `bantumi_hand_open_top_mask_31d138` | Open hand mask, top row, 12x16; mode 0. |
| `0x31d150` | label | `bantumi_hand_closed_bottom_31d150` | Closed hand image, bottom row, 11 wide, 13 rows used; mode 1. |
| `0x31d168` | label | `bantumi_hand_closed_top_31d168` | Closed hand image, top row; mode 1. |
| `0x31d180` | label | `bantumi_hand_closed_top_mask_31d180` | Closed hand mask, top row; mode 0 (inferred role). |
| `0x31d198` | label | `bantumi_hand_closed_bottom_mask_31d198` | Closed hand mask, bottom row; mode 0 (inferred role). |
| `0x31d1ec` | label | `bantumi_pit_xy_31d1ec` | Pit box positions: 14 x then 14 y bytes. x 4,17,30,44,57,70,68,70,57,44,30,17,4,3; y 36 x6, 16, 3 x6, 16. |
| `0x31d22c` | label | `bantumi_think_descs_31d22c` | Eight 12-byte descriptors of the 16x16 thinking animation, shown at (34,16) while a search runs. |

Shared names used above (defined in `ghidra/symbols/3310.csv`, mapped in
`games_applications_3310.md`): `games_dispatch_2dbd2a`,
`games_app_handler_2dbdd4`, `games_ctx_load_2dbc7c`,
`games_records_10f9e0`, `game_ctx_111218`, `games_current_id_11fd57`,
`game_alloc_zeroed_2dd6dc`, `game_digit_sprites_10db68`,
`sprite_create_2dda8c`, `sprite_move_2dd7e8`, `sprite_set_image_2dd748`,
`sprite_set_mode_2dd9da`, `sprite_free_2dd790`, `sprite_reset_all_2dd8ae`,
`sprite_engine_init_2dd936`, `sound_table_321e6c`, `sound_play_2ec8ca`,
`rt_smod_2f04fc`, `heap_free_29a74e`. Other addresses named: the RAM
level byte `0x10fa3c` (Bantumi's record +4), the hand bitmaps' RAM copies
`0x10e1c8`, `0x10e1e0`, `0x10e220`, `0x10e274`, the tone script
`0x321c1c`, and the title picture's descriptors `0x3185d0`..`0x31860c`.
