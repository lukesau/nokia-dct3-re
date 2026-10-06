# Running the 3510 games in Unicorn

The 3510 is DCT4 and has no emulator, so `tools/dct4_game_harness.py` runs a
built-in game's own code in Unicorn (big-endian Thumb) from the decrypted flash,
`roms/3510-nhm8-v502/flash.bin`. Its job is to check the static maps
(`games_kart_3510.md` and the slice docs) and to give reference frames and sound
logs for the ports. So far it drives Kart Racing from kart selection through a
race.

```
.venv/bin/python tools/dct4_game_harness.py --ticks 300 --keys "5:gas+ 6:gas- 60:gas+" --out run_3510_kart
```

`--keys` is a script of `tick:key+` / `tick:key-` events, with the key names
`left right gas brake fire turbo` (ids 0x13, 0xf, 0x14, 0x15, 0x16, 0x17; `gas`
is also select) or a raw id. `--mode` and `--level` are the menu settings (item 1 cup or
2 challenge; difficulty), and `--seed` is the value `game_srand` reads. `--out`
writes every frame as a PNG plus a contact sheet. The tones played are printed
with the tick they start on.

## What runs natively, what is replaced

Native, from flash: the game, the download engine and the shared game library
(`0x013fc000..0x0142edd4`, which includes the scene tree, sprites, key layout,
tone-id lookup and the engine's scene renderer `0x01428808`), the ARM runtime
divides and memcpy/memset. RAM is initialised by replaying the firmware's own
data-init chain (1100 `{u32 len, u32 dest, data}` records from `0x01520734` to
`0x01537980`), so tables such as Kart's track pointers at `0x3d090` hold their
boot values.

Replaced in Python (a block hook stops at any other code, so the list is complete
for what has been run):

| What | Where | How |
|---|---|---|
| Heap | `0x012ef746` alloc, `0x012efa34` free | bump allocator; new blocks are filled with 0xa5, so code that relies on cleared memory shows up |
| OS messages | `0x012c79ca`, `0x012c399a` | logged, return 0 |
| Time | `0x012fae6e` | returns `--seed` (the seed of `game_srand`) |
| Tones | `0x0127257c` play, `0x01272632` stop, `0x01272678` play data | logged: PPM tone index and loop/once |
| Drawing | the engine's draw wrappers `0x0142a26c` (bitmap), `0x0142a438` (line), `0x0142a5b4` (rect) | drawn into a 96 x 65 frame, or into the destination bitmap for the library's off-screen blits |
| Settings and saved data | the library entry points (`game_setting_get`, `game_*_write` / `_read`, game data) | an in-memory store; settings come from the command line |

The harness sets three engine variables the phone sets at start-up: the sound
and vibrator feature bytes (`0x3d78c[0]`, `[2]`) and the tone-server handle
`0x3d5b8`. Without the handle every tone request fails, and Kart's race step then
skips the frame (it returns early when the engine tone cannot start).

It drives the game the way the engine does (`games_library_3510.md`, "Engine to
game interface"): message 7 at boot, then 0xa (new game, a1 = item), 0x14 and 0xc,
then one message 0 per tick. A key event writes the key array at `0x3d714`
(down `(s & 0xf8) | 6`, up `| 5`) and sends message 1 or 2. After each tick every
key's "changed" bit is cleared. After each message the request word `0x3d710` is
acted on (exit, redraw through the native renderer, new period).

## What is inferred

The firmware GDI is not run: it needs a screen canvas (`0x16954`) that the
display driver fills at boot. The draw wrappers are replaced instead, so the tree
walk, positions, clipping, frames and order are the game's own, but the pixel
rules are the harness's:

- a set bit is black;
- flags `& 0xf000` 0x1000 draw, 0x2000 draw inverted, anything else nothing;
  flag bit 2 XORs;
- a sprite's second plane is a mask (1 = opaque, checked against the masked
  sprites' silhouettes); without one, flag bit 0 draws only the black pixels;
- with flags 0x2000 and the wrapper's fourth argument 1, the engine asks for GDI
  mode 8, taken as a plain copy (that is how the library writes mask planes);
- lines and rects draw in colour `a & 1`.

Frames are what the game asked to draw with those rules, not LCD captures.

## What the first runs showed

- Kart select (msg 1 with 0x14) highlights the kart for 20 ticks, shows the start
  picture for 20, then starts the race, as mapped.
- The race runs at the engine's default **100 ms** tick: nothing sets a period
  from kart select to the end of the race, and the race clock gains 1.0 s every
  10 ticks. The static map had inferred 50 ms; that is the best-results screen's
  period (corrected in `games_kart_3510_race.md`).
- Tones: the background loop (0xfb8 → PPM tone 0x29) and the start beep
  (0xfb2 → 0x2c) on the first race tick, then the engine sound (0xfb0 → 0x2a)
  when the gas is down, as mapped.
- Opponent kart sprites are built at run time into heap bitmaps through
  `game_bitmap_blit_scaled`.
