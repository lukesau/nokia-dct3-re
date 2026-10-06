# 5110 games in Unicorn

The Nokia 5110 (NSE-1) offers Memory, Snake and Logic. The `noki5110` MAME
machine expects v5.30 plus the ROM4 DSP research inputs and a NokiX EEPROM
(`roms/README.md`). The firmware used here is v5.28, which stops at CONTACT
SERVICE in MAME without those files. `tools/dct3_5110_game_harness.py`
therefore runs the games' own code in Unicorn and replaces the phone
services underneath them.

## Firmware

`Nse-1_v5.27-5.28.exe` from
[Internet Archive's Nokia DCT3 collection](https://archive.org/download/Nokia_DCT3_firmwares)
is a self-extracting zip (`7zz x` opens it). Its `NSE-1/nse1v528/` folder is a
Wintesla package: MCU `nse1nx05.280` (ROM4 flash) and `nse1nx_5.270` (ROM3),
with PPMs `.28a`..`.28e` and `.27a`..`.27d`; `nse-1.ini` maps regions to
PPMs.

```sh
python3 tools/extract_dct3_wintesla.py --mcu nse1nx05.280 --ppm nse1nx05.28a \
  --flash-output roms/noki5110/5110f528a.fls
```

This writes a 1 MiB image, SHA-1 `a623b59d0a5a35ef5d984a30eb54235fd997b602`.
The flash is big-endian Thumb at `0x200000`, the same layout as the 3210.

## Map (v5.28)

| Address | What |
|---|---|
| `0x2a79cc` | game table: three 12-byte `{handler, list, params}` records |
| `0x258c80` | Memory handler (index 0): keys 2/4/6/8, `*`, `#`, 5 |
| `0x258558` | Snake handler (index 1): keys 2/4/6/8 |
| `0x257c40` | Logic handler (index 2): keys 2/4/8, 5, `*` |
| `0x258f3e` | draw dispatcher: `game_table[index].handler(0x57)` |
| `0x2793e0`.. | games framework: New game, resume, timer, keys |
| `0x10fd5a` | current game index (u8) |
| `0x10a62c` | game records, 8 bytes each: `+0` score, `+2` top score, `+4` level, `+5` menu state, `+6` in play |
| `0x2a7c3c` | Snake speed table `66 48 38 30 23 18 14 11 9`, as on the 3210 |
| `0x10a6a8` | Snake board size, 20 x 11 cells, from the data-init chain |
| `0x107610` | LCD framebuffer: 84x48, six 84-byte pages, bit `y & 7` |
| `0x293fe0`..`0x29475c` | data-init chain: 102 `{u32 len, u32 dest, data}` records, 4-byte padded |

Event codes match the 3210's: `0x49` init, `0x53` resume, `0x54` tick, `0x57`
draw, keys as ASCII. Games menu item 1, New game (`0x2790fc`), sets record
`+6` = 1 and `+5` = 0. The framework then calls init and resume (`0x279456`).
A running game posts scheduler event `0x2a` through `0x25416a` with a delay
in ticks. When that event fires, the framework calls the handler with `0x54`.
Snake's delay is `10 * speed / 7.78125` ticks; level 0 is 82 ticks.

Logic is dispatched on this product. Its level formulas are the same as the
dormant Logic in the 3210 (`games_applications.md`).

## Native and replaced

Native: the three games and their helpers (`0x2576fc..0x25a400`), the LCD
fill/blit/put-pixel routines (`0x252cac..0x253400`, clipped to 84x48), and the
C runtime (`0x2921fc..0x294000`: divmod, software float, memcpy, `rand`).
These were matched to the named 3210 functions by masked instruction
patterns.

Replaced in Python:

| Address | 3210 counterpart | Stub |
|---|---|---|
| `0x2559e0` | `rtos_mem_alloc_26afe0` | bump allocator |
| `0x2555b8` | `rtos_mem_free_26abf8` | no-op |
| `0x25416a` | `sched_post_event_delay_2697aa` | records the event and its due time |
| `0x234c24` | `games_ui_refresh_243170` | no-op |
| `0x290108` | `display_type2_post_2b1f24` | logs the tone id |
| `0x28d9ae` | `task5_sequence_expand_status_with_payload_2af798` | logs the status; Snake posts `0x5132`/`0x11` at game over |

## Runs

```sh
python tools/dct3_5110_game_harness.py --game snake --level 4 --ms 6000 \
  --keys "700:2 1500:6 2600:2 3200:4" --out run_5110/snake
```

`--keys` takes `ms:key` pairs. The run writes one PNG per frame and a contact
sheet. Snake steers, eats and dies against the wall. Memory deals and flips
cards. Logic places symbols, checks a row with `*` and plays tone `0x10`.

Not yet covered: the framework's menus, game-over and top-score screens, NV
saving of records, and Memory and Logic win conditions.
