# 5110 Games menus

How the Nokia 5110 v5.28 draws its Games menus, and where that differs from
the 3210 v6.00. Everything here comes from the firmware: the pages were drawn
by the phone's own menu engine, applications, widget layer and fonts running
in Unicorn (`tools/dct3_5110_menu_harness.py`, below), and the numbers were
read from those frames and from the code. MAME cannot reach these pages on
v5.28 (CONTACT SERVICE).

Ticks are scheduler ticks, 7.78125 ms (`games_applications.md`).

## Summary against the 3210

| | 5110 v5.28 | 3210 v6.00 |
|---|---|---|
| Games in the main menu | entry 6 of 9 | entry 6 |
| Main menu icon | one 64x14 picture, not animated | 13 pictures, 64x16, animated |
| Main menu scrollbar thumb on Games | 14 | 12 |
| Games list | Memory, Snake, Logic | Rotation, Snake, Memory |
| List pages, scrollbar, fonts, softkeys | same | |
| A game's menu | same entries and rules; Logic has no Top score | |
| Level page | striped bars on a 7-pixel pitch | outlined bars on an 8-pixel pitch |
| Top score page | plain note, no sparkle, closes after 376 ticks | sparkle, closes after 771 ticks |
| Game over note | same texts and layout, menu returns after 376 ticks | 385 ticks |
| Instructions | same layout, 3 lines, More | |

## Main menu

The main menu is the static menu `0x2a0a7c` (table `0x2a09a0`, 20-byte
entries: text, argument, picture, type, softkey, flags). One entry per page.

| # | Entry | Picture |
|---:|---|---|
| 1 | Phone book | `0x33` |
| 2 | Messages | `0x34` |
| 3 | Call register | `0x35` |
| 4 | Settings | `0x37` |
| 5 | Call divert | `0x36` |
| 6 | Games | `0x38` |
| 7 | Calculator | `0x39` |
| 8 | Clock | `0x3a` |
| 9 | Tones | `0x3b` |
| 10 | Net monitor | `0x3c` |

Net monitor is hidden unless enabled (mask word at `0x10b602`), so a normal
phone shows 9 entries and Games is 6 of 9. The scrollbar thumb is
`(n - 1) * 23 / (count - 1)` as on the 3210: 14 for Games, its top at y 21.

The Games page:

- Path `6` in the top right, tiny font, as on the 3210. Right after the Menu
  key the number entry is open and the corner shows `_` instead; after a
  scroll it shows the number.
- Title `Games` in the large bold font, centered over the 78 columns left of
  the scrollbar, top at y 7 (`Games` spans x 20..55, y 7..17). The main menu
  descriptor gets this style; it is the 3210's title.
- Icon: picture `0x38`, one picture, no animation. 64x14, 128 bytes at
  `0x2a13fc`, two 64-byte pages, bit `y & 7` (the picture table is `0x2a1748`,
  12-byte entries `{data, ?, width, height}`, indexed through `0x2a1ab0`).
  Drawn at x 10, y 23, the 3210's position. It is a different drawing from
  any of the 3210's 13.
- Softkey `Select`, small bold, centered, y 40.

## Games list

Static menu `0x2a93cc` (table `0x2a937c`, flags `0xc0`: a list). Path `6-n`
for the selected game, three rows: Memory, Snake, Logic, entry arguments 0, 1, 2, which are
the game indices (`0x2a79c8` table order). Same geometry as the 3210's lists:
rows at y 7, 17, 27, 10 high, text in the small bold font at x 2, the
selected row inverted across x 0..77, scrollbar at x 81 (y 7..36, thumb 7
high), softkey `Select`.

## A game's menu

The games application (`0x27907c`, application `0x58`) builds level 2 with
`0x278f78`, which is the 3210's `0x29a038` instruction for instruction. Entries,
in this order:

| Entry | Id | Shown when |
|---|---:|---|
| Level | 3 | the game has two or more levels |
| Continue | 6 | record `+5` is 1 (left during play) |
| Last view | 6 | record `+5` is 3 (the game has ended) |
| New game | 1 | always (game flags bit 1 clear; set would give `1 player` / `2 players`) |
| Top score | 4 | the game's score field is above 1 |
| Instructions | 5 | always |

Per game, from the 12-byte records at `0x2a79c8` (`flags, levels, u16 score
field, handler, instructions text`):

| Game | Levels | Score field | Entries |
|---|---:|---:|---|
| Memory | 5 | 75 | Level, [Continue / Last view], New game, Top score, Instructions |
| Snake | 9 | 2000 | Level, [Continue / Last view], New game, Top score, Instructions |
| Logic | 8 | 0 | Level, [Continue / Last view], New game, Instructions |

Opening a game from the list resets record `+5` unless it is 1, so the list
leads to Continue but never to Last view. Last view shows when a game that
has ended goes back to its menu. The menu opens on its second entry (New
game, or Continue / Last view when present) drawn on the top row, Level
scrolled out above it. Path `6-g-n`. Layout as the games list.

Choosing an entry posts status `0x5e0` (start application) with:

| Entry | Application |
|---|---|
| New game, Continue, Last view | `0x59`, play (`0x2792cc`); New game sets record `+6` = 1, `+5` = 0 |
| Level | `0x5a` (`0x278dc8`) |
| Instructions | `0x5b` (`0x278efa`) |
| Top score | no application: note `0x26` straight away, menu underneath |

The application table is `0x2a6e18`, 8 bytes per id: handler, then the softkey id at `+4`.

## Level page

Application `0x5a`. Widgets: `0x15` the title `Level:`, `0x16` a bar graph
`{chosen + 1, levels}`, `0x17`; softkey `OK`.

- Title `Level:` in the small bold font at x 5, y 0, as on the 3210.
- One bar per level. Bar i (from 0): x `5 + 7i`, 5 wide, rows `28 - 2i`
  through 36, so 9 pixels high for the first and 2 more for each next.
- Bars up to the chosen one: the left column and every other row from the
  top (rows top, top + 2, ..., 36), 5 wide. Bars after it: the left column
  and the top row only.
- Softkey `OK`, small bold, centered, y 40.

Snake at level 3 (index 2), rows 12..36, x 0..67:

```
.............................................................#####..
.............................................................#......
......................................................#####..#......
......................................................#......#......
...............................................#####..#......#......
...............................................#......#......#......
........................................#####..#......#......#......
........................................#......#......#......#......
.................................#####..#......#......#......#......
.................................#......#......#......#......#......
..........................#####..#......#......#......#......#......
..........................#......#......#......#......#......#......
...................#####..#......#......#......#......#......#......
...................#......#......#......#......#......#......#......
............#####..#####..#......#......#......#......#......#......
............#......#......#......#......#......#......#......#......
.....#####..#####..#####..#......#......#......#......#......#......
.....#......#......#......#......#......#......#......#......#......
.....#####..#####..#####..#......#......#......#......#......#......
.....#......#......#......#......#......#......#......#......#......
.....#####..#####..#####..#......#......#......#......#......#......
.....#......#......#......#......#......#......#......#......#......
.....#####..#####..#####..#......#......#......#......#......#......
.....#......#......#......#......#......#......#......#......#......
.....#####..#####..#####..#......#......#......#......#......#......
```

Keys: Up (status `0x367`) raises the level, Down (`0x366`) lowers it, with a
`0x290108(0, 3, 0)` post each step, and `(0, 8, ..)` at the top or `(0, 9, ..)`
at the bottom instead when it cannot move (the games' tones are `(0, 0xf1, id)`;
these are the phone's key and limit sounds, not mapped further). It stops at
the ends. `OK` (`0x348`) returns to the menu; when the level changed it first
saves it (record `+4` and the NV record) and clears record `+5`, so a paused
game loses Continue. C (`0xca`) returns without saving.

Logic has 8 bars; its level formulas are in `games_harness_5110.md`.

## Top score

Note type `0x26` (note table `0x2a66b8`, 20 bytes per type) with
`Top score:\n%N`:

- Large bold font, line tops at y 3 and 18 (15 apart), x 0, as the 3210's
  `draw_note`. No softkey.
- No picture and no animation: the 5110 has no sparkle. The 3210's type
  `0x28` carries the sparkle and a 771-tick (`0x303`) timeout; the 5110's
  `0x26` has picture `0x43` (none) and a 376-tick (`0x178`) timeout, posted as
  event `0x29`.
- Memory and Snake only.

## Game over

When a game posts status `0x1132` with an argument (`0x5132`), the play
application marks the record `+5` = 2, shows note `0x25` and posts event
`0x2a` for 376 ticks (`0x178`; the 3210 posts 385). The note itself has no
timeout. Then the menu returns with Last view, which is selected.

The text, from `0x2791c8` (the 3210's `0x29a2a0`):

| Case | Text | Tone |
|---|---|---|
| In play, score field 0 (Logic) | `Game over!` | the game's argument |
| In play, score not above the top score | `Game over!\nYour score:\n%N` | the game's argument |
| In play, new top score (saved) | `Game over!\nTOP SCORE:\n%N` | `0x14` |
| Not in play, score above 0 | `Game over!\nYOU WON!` | `0x13` |
| Not in play, score below 0 | `Game over!\nYou lost,\nsorry!` | the argument |

The last two are for two-player games, which these three are not. The
arguments the games post: Snake `0x11`; Memory `0x13` with a score above 0,
else 0 (no tone); Logic `0x13` (it only ends when solved, so the note always
reads `Game over!`). Layout as Top score: large bold, line tops at y 3, 18,
33.

## Instructions

Application `0x5b` opens the phone's text viewer (`0x241444`) on the game's
text (record `+8`: Memory `0x2a4e04`, Snake `0x2a4e07`, Logic `0x2a4e01`).
First page: small plain font, x 0, line tops at y 7, 16, 25 (9 apart),
three lines, softkey `More`; the 3210 port's layout. Paging through the text
viewer was not traced (its key path is outside the games code).

Logic's text: "Try to guess the right combination of figures. Move the cursor
with keys 2, 4 and 8, select a figure with key 5. Check your guess with *. A
right figure in the right place is marked with a rectangle, a right figure in
a wrong place with a line." Memory's and Snake's match the 3210's.

## Strings

Text records are 3 bytes, `04 hi lo`; the string is number `hi:lo - 0x2e`
in the language block (English at `0x2b51b0`: 16-byte header, 848 length
bytes, then the text). Games strings are records `0x2a46ed..0x2a4723`:
`Game over!`, `Top score:\n%N`, `Level:`, `Logic`, `Memory`, `Games`,
`1 player`, `2 players`, `Continue`, `Top score`, `Instructions`, `Last
view`, `Level`, `New game`, `Snake`, then the four game-over texts above.

## Harness

`tools/dct3_5110_menu_harness.py` runs the whole flash natively on top of the
game harness. It keeps the game harness's stubs, answers the phone state
query `0x28ee7e` with 3, runs the font setup `0x253a4c`, and writes what boot
would have set:

| Address | Value | What |
|---|---|---|
| `0x10fcf0` | 1 | language, English |
| `0x10fd55` | 1 | script flags, Latin (`0x08` right to left, `0x16` others) |
| `0x106f80` | `0x2b0050` | character map for the English block |
| `0x10fd57` | 3 | most rows a list shows |
| `0x10b602` | `0x01ff` | main menu entries shown |
| `0x108e54` | slot `+4` = `0x16` | 22 free indicator slots |

The game harness now selects an ARMv4T core (TI925T): the firmware returns
from `mov lr, pc` calls with `pop {pc}`, which Unicorn's default core takes
as a switch to ARM. Game runs are unchanged by it.

```sh
python tools/dct3_5110_menu_harness.py main --ascii
python tools/dct3_5110_menu_harness.py menu --game logic --resume lastview --out run_5110/menus/logic
python tools/dct3_5110_menu_harness.py level --game snake --level 4 --keys "up up"
python tools/dct3_5110_menu_harness.py gameover --game snake --score 157 --top 100
```

Pages: `main`, `games`, `menu`, `level`, `instructions`, `topscore`,
`gameover`. Each writes PNGs and a contact sheet with `--out`.
