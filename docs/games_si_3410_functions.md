# Space Impact 3410 (NHM-2 v5.46) against the 3310 and the 3310 port

Scope: every function file in `run_games_3410/decomp/` from `0x2589d0` to
`0x25c974` (68 files), read from the decompiles and, where Ghidra failed or
truncated, from a Thumb disassembly of the same bytes (capstone over
`roms/noki3410/3410f546e.fls`, base `0x200000`, big-endian; literal pools
resolved). Compared with the 3310 address map in
`docs/games_applications_3310.md` and the port in
`ports/nokia-gb-games/3310/core/{si.c,si_setup.c,si_base.c,sprite.c}`.

Marks: **static** = read from code or data here; **inferred** = my reading,
not checked; nothing below was checked in MAME.

Notation: `ST` = `si_state_11d848` (0x5a8 bytes), `TBL` = `si_tables_11d7a0`,
`CF` = the parsed chapter file `0x11ddf0`. Screen is W x H = 96 x 65 (the code
asks `0x3fa0b4()` / `0x3fa0c0()` every time and still carries 84-column
branches; only the 96 values are given unless noted). Positions are signed
16-bit `{x, y}` pairs, x first (big-endian, so in the decompiles `v >> 16` is x
and `(short)v` is y; Ghidra frequently swaps the halves in `CONCAT22`, so
those were checked in the disassembly).

Decompile defects that matter:
- `0x3f7586` (memcpy) marked noreturn truncates: `0x258bb4` (draw number),
  `0x3f0948` (create picture), `0x3ef324` (create fill), `0x3ea886` (create
  line), `0x3da9d0` (set position), `0x3dab66` (get position), `0x3ea7be`,
  `0x3ea83e`, `0x25cb9c` (score box). All were read from the disassembly.
- `si_handler_25c974`: event switch is a jump table Ghidra abandoned
  ("bad instruction data"); table at `0x25c998` read by hand.
- `0x25b750`: pattern switch jump table at `0x25b7d0` (24 entries) read by hand.
- `0x259ddc` and `0x25a340` are not functions: nothing branches to them; they
  are Ghidra-made fragments of the middles of `0x259d30` and `0x25a110`
  (decompiled with `unaff_` registers).

## Corrections to games_si_3410.md found on the way (now made there)

1. `ST+0x568` special weapon: **6 = wall, 7 = missile, 8 = beam** (doc says 6
   missile, 7 wall). Templates at `0x4ace3c`: type 6 = 7 frames, hp 0x20,
   pattern 0 (the 3310 wall, type 9); type 7 = 1 frame, hp 10, pattern 9
   speed 1 (the 3310 missile, type 10); pictures 0x49039c (5x5, = 3310 wall)
   and 0x49036c (5x3, = 3310 missile); HUD icon for 7 is 0x490134 (the 3310's
   missile icon bitmap), for 6 0x49014c (3310 wall icon), for 8 0x490164 (3310
   beam icon). New game and continue set `ST+0x568 = 6`: **the 3410 starts
   with 3 walls, not 3 missiles** (static, `0x259a4e`, `0x259f92`).
2. y paths: the default (84-column) values are `+0x20 = 0x4ad268`,
   `+0x24 = 0x4ad214` (84-entry tables, byte-identical to the 3310's rise and
   fall); **on 96 columns they are replaced by `0x4ad31c` (rise) and
   `0x4ad2bc` (fall)**, 96-entry tables. The doc has this reversed.
3. `ST+0x57e` (`0x11ddc6`) / `0x259aec` is **not the end sequence**: it is the
   High scores page (event `0x0b`, set up by `0x258a52`), with a small
   animation. There is no separate end sequence (see section 5).
4. `ghidra/symbols/3410.csv` names `0x259030` `si_ypath_user_259030`; it is
   the HUD/chapter screen builder (the doc's `si_hud_create_259030` is right).
5. Events: the handler's switch is on `event - 7`: `0x07` boot registration
   (`0x2589d0`); `0x09` demo with a = mode (`0x259a90`); **`0x0a` New game**
   (`0x2598b0(0)`); `0x0b` High scores page (`0x258a52(b)`); `0x0c` and
   `0x14` do nothing (return 1); `0x0d` Continue = resume from the saved state b
   (`0x259334`); `0x0e` title (`0x3db036`); `0x11` a chapter file received
   (parse, store, select); `0x12` a chapter file chosen in the Chapters menu;
   `0x08`, `0x0f`, `0x10`, `0x13` and > `0x14`: clear the state and close
   (`0x3b29de`).

## 1. Function table

Columns: 3410 address | suggested name | 3310 counterpart | port function |
confidence | differences that matter for a re-implementation.

| 3410 | Suggested name | 3310 | Port | Conf. | Differences |
|---|---|---|---|---|---|
| `0x2589d0` | `si_register_2589d0` | none (3310 framework `games_table`) | none | medium | Event 7 (boot broadcast). Clears ST (0x5a8), registers the app with the games framework: `0x34e6e8(2, 0xfc8, *TBL+0x48, 0x5a8, 0)` (saved-state size 0x5a8), menu `0x34dfaa(1, 0x4ad3ac)` (7 items, with Continue) when `0x3b29ea()` == 1 else `0x4ad3bc` (6 items), a settings list `0x34e42e(1, 0xfcd, 0, 4, TBL+0x58, 1)` (inferred: the Chapters list, setting 4). Not needed for the game itself. |
| `0x258a52` | `si_high_scores_page_258a52` | none (3310 Top score page `0x298710` is framework) | none | high | Event `0x0b`, b = the high-score record (section 9). Sets ST+0x57e = 1 (page active), ST+0x580 = 0 (step), period 100. If the current chapter file (setting 4) equals the last game's (rec+0x14): `0x3b268a(5, 0, rec+0xc, 0)` (last score box at the bottom, no medals), ST+0x5a4 = 1. Then `0x3b268a(5, 1, top, 0)` (top box with medals), top = rec+0 when setting 4 == 1 (built-in chapters), rec+4 when it equals rec+8, else 0. Creates, under the root: ship 0x490444 at (0, H/4 = 16) mode 0x10 → TBL+0x30; shot 0x49045c at (10, 16 + 3 = 19) mode 0 → TBL+0x34; enemy 0x490e74 (7x7, the 3310's type 0x1a picture) at ((W/3)*2 = 64, (H/5)*2 = 26) mode 0x10 → TBL+0x38; explosion 0x4902f4 (5 frames) at (64, 26) mode 0 → TBL+0x3c. |
| `0x258b70` | `si_chapter_file_select_258b70` | none | none | medium | (name, id): TBL+0x64 = id, TBL+0x60 = `0x34e850(2, name)`, `0x34e9ae(2, 1, 4, TBL+0x60)`. Inferred: updates the Chapters list entry / setting 4. |
| `0x258b94` | `si_objects_clear_258b94` | `si_objects_clear_2576a0` | `si_objects_clear` | high | 60 records of **20 bytes** at ST+0x90 (3310: 12 bytes at +0x48). Free mark **0x7f** (3310 0x32). Clears +0 frames, +1 frame, +0xe no-score, +0xf side; count ST+0x3c = 0. |
| `0x258bb4` | `si_draw_number_258bb4` | `si_draw_number_2576ce` | `si_draw_number` | high (asm) | (array of picture pointers, value, digits). Decompile truncated at memcpy; from asm: digit buffer zeroed (copy of 12 zero bytes at 0x4ad3cc), filled from the right by `value % 10`, then each digit picture gets `0x3f08ec(pic, 0x4901a4 + 24*d, 1)` (frame list = that digit's 24-byte descriptor). Leading zeros shown, as on the 3310. Pictures are an array of pointers, not a linked run of sprite ids. Value is the u16 score, so 0..65535. |
| `0x258c42` | `si_continue_enter_258c42` | `si_continue_enter_258114` | `si_continue_enter` | high | Frees every picture under the root (ST+0x578), clears records, **vibrator off** (`0x3b25d4(0)`). Fill (W x H, mode 0x10) into ST+0x34 when the chapter mode is 0x12 (3310: polarity 2). Four icons 0x490164 (the 3310's beam icon, as on the 3310) at (6i, 0), mode 0x12, ST+0x74..; hides i >= continues (ST+0x572) when continues < 4. Countdown digits at (W/2 - 6, H/2 - 4) = **(42, 28)** and (46, 28) (3310: (36, 20), (40, 20), same formula), mode 0x12, ST+0x84/0x88, showing 05. Phase 0x14, **period 800**, redraw. No `pending` result. |
| `0x258da0` | `si_terrain_create_258da0` | inside `tilemap_init_2e6f9a` (called by `si_hud_create_257764`) | `tilemap_init` (sprite.c) | high | (0 floor / 100 ceiling). Width and rows from CF's tilemap list for the chapter (16 x 2), map from TBL+0x18[ch], tiles from TBL+0x10[ch], mode = chapter mode low byte (ST+0x553). Allocates rows x W bytes (16 x 96... = 2 x 96 = 192) into ST+0xc. Descriptor at ST+0x14 {W, rows*8 = 16}. Position: floor **(0, H - 16 - 11 = 38)** (3310: (0, 32)); ceiling **(0, 10)** (3310: (0, 0)). Picture created under ST+0x578 with mode = chapter mode; stored at ST+0x10 and returned (also kept at ST+0x30). |
| `0x258ec8` | `si_terrain_render_258ec8` | `tilemap_render_2e6e98` | `tilemap_render` | high | Same tile walk with the scroll at ST+0x55a, 96 columns per row. Extra masking only when rows == H >> 3 (full-height maps; not the built-in ones). Then `0x3f08ec(terrain, ST+0x14, 1)` to refresh. |
| `0x258fc8` | `si_set_play_bounds_258fc8` | `si_set_play_bounds_257748` | `set_play_bounds` | high | ST+0x540 = bottom, ST+0x541 = top (same order as 3310 +0x318/+0x319). 96: floor **bottom H - 27 = 38, top 11**; ceiling **bottom 54, top 26**. (84: floor 21 / 6, ceiling H - 6 / 16.) 3310: floor 32 / 6, ceiling 42 / 16. |
| `0x259030` | `si_hud_create_259030` | `si_hud_create_257764` | `hud_create` | high | Frees all pictures under the root, sets ST+0x578 = root. Sets the y-path pointers (TBL+0x1c 0x4ad094, +0x20 0x4ad31c, +0x24 0x4ad2bc, +0x28 0x4ad0f4, +0x2c 0x4ad154 on 96 columns). Order of creation (= draw order): fill (W x H, mode 0x10, `0x3ef324`) if mode 0x12, moved to the head; top bar 0x4ac1d8 at (0, 0) and bottom bar 0x4ac1a8 at (0, H - 11 = 54) (96 only); five hearts 0x490104 at **(16 + 6i, 3)**, the 4th and 5th set to mode 0; five score digits 0x4901a4 at **(56 + 4i, 2)** i = 0..4; score drawn; special icon (by ST+0x568: 7 → 0x490134, 8 → 0x490164, else 0x49014c) at **(40, H - 7 = 58)**; two count digits at **(51, 58), (55, 58)**; count drawn; terrain (`0x258da0`), rendered, bounds set, terrain moved to the head. All HUD mode 0x12. 3310: hearts (6i, 0/43), icon (36, y), count (42/46, y), score (56..72, y), terrain created last. Ceiling flag = bit chapter of CF u16 `0x11de50` (= 0x0030, chapters 4, 5). |
| `0x2592aa` | `si_hud_refresh_2592aa` | `si_hud_refresh_2579ac` | `si_hud_refresh` | high | Same order: special count (2 digits), score (5), hearts mode 0x12 if i < lives else 0. |
| `0x259334` | `si_resume_259334` | `si_resume_2581f8` | none (port: not done) | high | Event `0x0d` (Continue). Copies the saved 0x5a8 bytes over ST (`0x3b2984`), restores the spawn-script pointer from TBL+0xc[ch]+4, period 100, **ST+0x57c = 10** (shield/exit counter, 1 s; 3310 1500 ms one-shot), ST+0x57d = 0. Phase 0x14: countdown 5, continue screen. Else HUD rebuilt, phase 0x1e hides the terrain, then every record re-created at its saved (+0xc, +0xd) with the chapter mode: type 0 → ST+0x56c; type 1 (shield) → ST+0x570 = index and **ST+0x57c = 0x5c** (92 ticks); type 2 with 5 frames (→ ship picture if ST+0x562 == 1); type 8 → line from (col, top) to (col, H - 1) (or (col, 0)..(col, bottom) when top == 0x10); boss (+0x10) → mode 0x10 if the chapter mode is 0x12, ST+0x55d = index. Note: a resumed shield in a 0x20 chapter gets mode 0x20 (visible), not 0x30. |
| `0x259518` | `si_chapter_load_259518` | `si_level_load_2578de` | `si_level_load` / `level_reload` | high | (20-byte record, 0xff = keep script pointer). Copies to ST+0x544; script pointer from TBL+0xc[ch]+4 unless 0xff; entries left (ST+0x554) = entries; checkpoint (ST+0x550) = 0; delay (ST+0x555) = 0x14; clears records; beam col 0; scroll 0; shield index 0xff; ship picture 0; ST+0x57d (vibration) = 0; HUD; **boss state ST+0x8d = 0**; phase 10; ST+0x3d = 0. No boss-part ids. |
| `0x259598` | `si_object_free_259598` | `si_object_free_258cac` | `object_free` | high | Frees the picture, count-- if nonzero, type 0x7f; clears the missile target ST+0x571 if it was this. Does not clear +0xe (3310 clears no_score) and has no boss parts. |
| `0x2595d8` | `si_respawn_position_2595d8` | none | none | high | Respawn position after a loss: if terrain rows < 10 (always, built-in) **(2, 12)** on floor chapters, **(2, H - 30 = 35)** on ceiling ones; else scans the terrain bitmap for a 7-row gap (downloaded maps). 3310 respawns at (5, 20) like a new ship. |
| `0x2596b2` | `si_record_find_free_2596b2` | none (sprite engine allocates) | none | high | First record 0..59 with type 0x7f, else -1. Records are reused lowest first, so the record index is not the draw order. |
| `0x2596dc` | `si_object_spawn_2596dc` | `si_object_spawn_25793a` | `si_object_spawn` | high | (type, mode, x, y) → record index, 0 when 40 objects exist (or no free record). Creates the picture first (`0x3f0948(ST+0x578, mode, &pos, TBL+0x14[type], template.frames)`), then copies the 20-byte template TBL+8[type] into the first free record, +8 = picture, count++. No layer argument; new pictures always go to the end of the draw list. |
| `0x25975c` | `si_row_adjust_25975c` | none (3410 glue) | none | high | On a 96-column screen adds 6 to a byte y, or 10 when the terrain is on the ceiling (ST+8 == 100). Applied to spawn rows (also random ones, after clamping), the new ship's y, path bases, dive limits. |
| `0x25978c` | `si_ship_spawn_25978c` | `si_ship_spawn_257a18` | `si_ship_spawn` | high | Clears ship-lost, ST+0x573 (move acceleration), ST+0x564 (fire count), ST+0x565 (special latch). New (10): ship at **(5, 20 + 6 = 26)** floor / (5, 30) ceiling, ST+0x56c/0x574 = picture/index, frees an old shield, ST+0x570 = 0xff, missile target 0. Respawn (0x14): frees the ship record, new ship at `0x2595d8`'s position. Shield (type 1): if none, spawned at **(3, 18)** (not adjusted; the tick moves it to ship - 2 at the end of the tick); else moved to (ship.x - 2, ship.y - 2). Shield mode **0x12** in 0x12 chapters, **0x30 (not drawn)** in 0x20 chapters (3310: XOR / SET, always visible). **ST+0x57c = 0x1e** (shield for 30 ticks; 3310: 3000 ms one-shot), **period 100**, HUD refresh. No chapter-0 opaque ship image (3310 swaps in 0x312dcc, mode 4, in level 0). |
| `0x2598b0` | `si_new_game_2598b0` | `si_new_game_257b48` | `si_new_game` | high | (0 = New game, 0xff = demo). Clears ST and the high-score copy; ST+0x3d = 0; countdown ST+0x55c = 5. Unless 0xff, reads the high-score record (`0x3b299c`) into ST+0x588. Loads the chapter file: built-in (`0x49f3e0`, 0xc29 bytes, copied to a heap buffer TBL+0x40) when setting 4 == 1, or on failure, or for a demo; else the downloaded file (`0x3f43b6`). Parses into CF (`0x35cf30`), sets TBL+8 (templates), +0xc (chapter records), +0x10 (tile sets), +0x18 (tilemaps); pictures for types 0..7 into TBL+0x14 (0x490444, 0x490294, 0x4902f4, 0x4902c4, 0x49045c, 0x49045c, 0x49039c, 0x49036c); copies templates 0..19 from 0x4ace3c. Then score 0, cooldown 0, lives 3, **continues ST+0x572 = 4**, target 0, **shot type 4**, **special 6 (wall)**, count 3, shield 0xff, terrain buffer 0, chapter 0, chapter load, ship (10). Period set by the ship spawn (100). |
| `0x259a90` | `si_demo_start_259a90` | none | none | high | Event 9 (a = mode 1..3): new game (0xff), ST+0x582 = mode, ST+0x584 = 0. Mode 3: replaces chapter 0 by the demo chapter record `0x4ad390` (2 entries at 0x4ad37c, both a type-3 bonus, mode 0x12) and a new ship. See section "Demos" below. |
| `0x259aec` | `si_high_scores_step_259aec` | none | none | high | High scores page events. Key down or pause (1 or 3): if a == 0x0c and ST+0x5a4 == 1, `0x3b25dc(2, rec+0x14, rec byte +0x1b, 0, rec+0x10, rec+0xc)` (inferred: submit the last score; the rand at rec+0x10 looks like a check value); then ST+0x57e = 0, ST+0x580 = 0, close. Tick, by step ST+0x580: 0: enemy bobs y -1/+1 alternately (TBL+0); ship x += 2; while ship.y <= enemy.y - 2 the ship moves down 3, else the shot is shown (mode 0x10, TBL+1 = 1); shot x += 2 (+2 more once fired), y = ship.y + 3; when shot.x > enemy.x - 4 → step 1. 1: hide shot and enemy, show the explosion, ship x += 3. 2..5: explosion frame step - 1, ship x += 3. >= 6: explosion hidden, ship x += 3 while x <= W. Redraw each event. |
| `0x259cc4` | `si_object_width_259cc4` | none (`sprites[id].image.w`) | `sprites[].image.w` | high | Width of the record's current frame: `*(u16*)(TBL+0x14[type] + 24*frame)`. |
| `0x259d30` | `si_key_event_259d30` | `si_key_257e1c` | `key()` | high (asm) | Key-down handler, **used only by the demos** (normal play polls, `0x25a110`). Codes: 0 down, 8 up, 10 (*) left, 11 (#) right, 1/3 fire, 4/6 special. Down: floor y < bottom + 9, ceiling y < bottom - 7; up: ceiling y >= 2, floor y > top; left: x > 2 (3310 x > 1); right: x < W - 10 = 86 (3310 x < 73); all 1 px. Fire: if cooldown ST+0x563 == 0 and ST+0x564 < 3: shot type ST+0x567 at (x + 6, y + 3), cooldown 1, count++, **sound 0xfa5**. Special: if cooldown 0 and count >= 1: beam (8) when column 0: column = x + ship width, line (col, top)-(col, H - 1) (or (col, 0)-(col, bottom) if top == 0x10), record from template 8 in the first free record (not counted), **sound 0xfa8**; else spawn type ST+0x568 at (x + 6, y + 3), **sound 0xfa6**; count--, cooldown 1, redraw count. Shield follows (x - 2, y - 2) if moved. |
| `0x259ddc` | (fragment of `0x259d30`) | — | — | high | Not a function. |
| `0x259f92` | `si_continue_key_259f92` | `si_continue_key_257ce0` | `si_continue_key` | high | **Keys 1 and 3 only** (3310: 1, 3, 4, 6). Cooldown 0, count 0, lives 3, target 0, shot 4, **special 6 (wall)** x 3; reloads the chapter from ST+0x544 (param 0), new ship; entries left = checkpoint (ST+0x550) or entries if 0, delay 0x14, phase 10; the caller sets the countdown back to 5. As on the 3310 the reload has already cleared the checkpoint, so the chapter restarts from its beginning. |
| `0x259ff4` | `si_high_score_save_259ff4` | none in SI (3310 framework saves the score after `0x18`) | none | high | Called entering the game-over/end screen (and entering phase 0x1e of the last chapter). See section 9. Draws **one rand()** (stored at rec+0x10). |
| `0x25a068` | `si_ship_clamp_y_25a068` | none (3310 checks per key) | none | high | s = 2 with a shield else 0. 96: y clamped to [10 + s, H - s - 19 = 46 - s]. (84: ceiling [s, H - s - 12], floor [s + 5, H - s - 7].) |
| `0x25a110` | `si_keys_poll_25a110` | `si_key_257e1c` | `key()` | high | Called every play tick (not in phase 0x1e) before spawning; reads held keys with `0x3b29d0(k)` (held when `(v & 0xf) >> 1 != 0`). Nothing if the ship is lost. Movement: 1 px while the acceleration count ST+0x573 < 3 (each 1-px move increments it), then 2 px; ST+0x573 is reset by a key-up of 0, 8, *, #. Down (0) then clamp; up (8) then clamp (1 px also when floor, 5 < y < 8 and no shield); left (*) only if x > step + s (1 px also when no shield and 0 < x < 3); right (#) only if x <= W - step - 10. Fire held (1 or 3): as `0x259d30` (cooldown 0, at most **3 shots per press**, ST+0x564 reset by key-up of 1/3; **sound 0xfa5 for every shot**). Special held (4 or 6): once per press (latch ST+0x565, released when neither is held); **no cooldown check and no cooldown set**; beam (record searched after the line is made) or spawn as in `0x259d30`, sounds 0xfa8 / 0xfa6; count redrawn. Clamp y if moved. 3310: event-driven, 1 px, 2 px on repeat events, up to 5 repeats, sound only on the first shot, special needs cooldown 0. |
| `0x25a340` | (fragment of `0x25a110`) | — | — | high | Not a function. |
| `0x25a3f4` | `si_spawn_step_25a3f4` | `si_spawn_step_258508` | `spawn_step` | high | Same delay/loop structure. Entry = 9 bytes (no shots byte). Checkpoints: ST+0x54c[0..3] (all 0 in the built-in file). **A new pattern-24 entry turns every live pattern-24 object into pattern 3** (new). Delay = e[5]. **Boss = the last entry (entries left == 1)**, not a type list: spawned with mode **0x10** in 0x12 chapters, **0x30** in 0x20 chapters, flagged +0x10 = 1, ST+0x8d = 1, ST+0x55d = index (3310: types 7/0x13/0x18 mode 4, boss by type). No final-boss skip (the 3410's final boss is an ordinary script entry). Row: e[6], or for 0x3f `top + rand() % bottom` (u8), at least top, at most bottom - height(frame 0 of the type); **then 0 on a floor chapter becomes top + 1; then +6 (+10 ceiling) on 96 columns**. x = W + n * e[2] (= 96 + ...), or -n * e[2] for pattern 5. Record: +4 = e[4], +5 = e[3], +3 = e[8] (hp), +6 = e[7] (fire). |
| `0x25a598` | `si_object_height_25a598` | none | `sprites[].image.h` | high | Height of the current frame (+2 of the descriptor). |
| `0x25a5d4` | `si_terrain_collide_25a5d4` | `tilemap_collide_2e7036` | `tilemap_collide` | medium | (record) → 0, 1 or 2. Pixel test of the object's **frame-0 bitmap** (TBL+0x14[type]+8) against the terrain bitmap (width W), object width/height from the current frame, terrain at its picture's y with height rows*8. Skips when ceiling and y > terrain bottom, or floor and y + h < terrain top. Returns 2 when the hit is in the lower half of the object (or in the "object above terrain top" case), 1 otherwise (inferred meaning; callers only test non-zero). Stops at x >= W. |
| `0x25a8c2` | `si_enemy_fire_roll_25a8c2` | `si_enemy_fire_roll_25865a` | `fire_roll` | high | fire (+6) 0 or 0x7f never; else `rand() % fire == 0` with the **ANSI rand** (3310: game_rand16). Pattern 0x14 burst pause at TBL+2 (pause > 0: pause--, no fire; else pause = rand() % 3 + 2). |
| `0x25a920` | `si_enemy_fire_25a920` | `si_enemy_fire_2586b2` | `enemy_fire` | high | (record, bullet type). If x <= W: spawn the type (5 for all ordinary callers) with the chapter mode at (x - 2, y + h/2). **No shots-left counter** (the 3410 entries have no shots byte); 3310: needs shots or a boss, x < 85. |
| `0x25a96e` | `si_move_bounce_25a96e` | `si_move_bounce_25871c` | `move_bounce` | medium | (record, unused, bullet type). Rewritten. State TBL+4 (latched direction), TBL+5 (direction), TBL+6 (latch age), TBL+0x50 (picture of the object last bounced): **a different object resets the direction to -1** (3310: one global direction). Floor & y <= top → dir +1; ceiling & y + h >= bottom → dir -1 (latch cleared). Else, inside the screen: terrain hit (`0x25a5d4`) → if no latch: dir = -dir, latch = dir, age 0; else age++ and the latch clears after 10. Off the screen (y < 0 or y + h >= H): dir toward the screen, latched, y clamped. Then fire roll → fire (type param, if nonzero); boss → ST+0x8d = 0x1e; y += (latch ? latch : dir). No level-0 bottom rule. |
| `0x25aaf2` | `si_boss_enter_25aaf2` | `si_boss_enter_258882` | `boss_enter` | high | Unless state 0x28/0x14: x > (W/3)*2 - 5 = **59** → x - 1, return 0 (3310: x > 56). |
| `0x25ab3e` | `si_boss_charge_25ab3e` | `si_boss_charge_258a04` | `boss_charge` | high | (record, bullet type, reach 100/150). State 10: x >= **59** → 0x1e, else x + 1 (3310: x >= 0x4a - width). 0x14: x <= W/8 = **12** → 10 (3310: x < 9); else x - 2 (100) or - 4, terrain hit → y -1 (floor) / +1. 0x28: x < W (96) → x + 1, else 0x14 (3310 x < 84). Else: bounce, then `rand() % 50 == 0` and top < y < bottom and x <= (W/3)*2 = **64** → 0x14 (100) or 0x28 (150) (3310: x <= 56). |
| `0x25ac44` | `si_boss_fire_25ac44` | `si_boss_fire_258808` | `boss_fire` | high | Driven by the chapter settings S (section 4): type S[2], offset (S[4], S[3]) (zeroed if larger than the boss's width/height), x = boss.x + dx - width(type), y = boss.y + dy; new record: **+0xe = 1 (no score), pattern S[5], speed S[6], hp 3**; cooldown TBL+3 = 6. Same roll/cooldown logic as the 3310. Fires in **every boss state** (3310 restricted it per level). |
| `0x25ad28` | `si_move_boss_25ad28` | `si_move_boss_258b0c` | `move_boss` | high | Nothing for state 0 or 0x7f. Enter (`0x25aaf2`), then by S[0]: 0 roll and fire S[1]; 1 bounce (fire S[1]); 2 charge 100; 3 charge 150; then boss fire if S[2]. **Always sets the boss mode 0x10** at the end (3310 restores OPAQUE or SET by polarity). No final-boss state machine, no parts. |
| `0x25adfa` | `si_object_free_at_left_25adfa` | `si_object_free_at_left_258cf6` | `free_at_left` | high | Frees when x < 1 or x > 250 (s16). |
| `0x25ae30` | `si_move_slope_25ae30` | `si_move_slope_258d18` | `move_slope` | high (asm) | (record, speed, 0 floor (pattern 18) / 100 ceiling (17)). x -= speed. Floor: x > W → y = bottom (38); else y > (H/5)*3 = **39** → y - 1, turned. Ceiling: x > W → y = top; else y < H/5 = **13** → y + 1, turned. Free at left; turned and roll → fire 5. 3310: >= 28 / <= 8. On 96 a floor-slope object placed at y = 38 never turns (38 > 39 false), so never fires (static; check in MAME). |
| `0x25af08` | `si_move_path_25af08` | `si_move_path_258d8e` (+ `si_move_descend_25924c`, `si_move_climb_259190`) | `move_path` | high | (record, speed, relative (0 / 0x80), offset). x = max(x - speed, 0). Base: relative → offset, else 10 (ceiling) / 0; **then +6 (+10 ceiling) on 96**. y = base + path[x % W] (TBL+0x44). Clamp: ceiling y + h <= H - 8 - 6 = **51**; floor y >= **10** (3310: y >= top). Free at left; fire roll only for pattern 1 at y == 0x1b or 9 (unchanged constants), 10..13 at path value ±4, 15/16 always. **Patterns 2 and 4 also use this function** (paths 0x4ad0f4, 0x4ad154), so they never fire (3310's descend/climb fire on turning). |
| `0x25b06c` | `si_missile_pick_target_25b06c` | `si_missile_pick_target_258ea4` | `missile_pick_target` | high | Over records 0..59: not free, type not 0 or 2, side (+0xf) != 0x0a, most hp (first kept on ties, start -99). Includes enemy bullets and bonuses. Record order, not draw order. |
| `0x25b0ae` | `si_object_free_at_right_25b0ae` | `si_object_free_at_right_258f1c` | `free_at_right` | high | Frees when x + width > W. |
| `0x25b0f0` | `si_move_missile_25b0f0` | `si_move_missile_258f44` | `move_missile` | high | Re-picks when the target ST+0x571 is 0 or left of the missile; **no re-pick when the target was freed/reused** (3310 also re-picks on FREE/SHIP). None: x + 1. Else y ±1 toward target.y + h/2 within (top, bottom), x + 2, free at right. |
| `0x25b1c4` | `si_move_dive_25b1c4` | `si_move_dive_25903c` | `move_dive` | high | Own limits: (top', bottom') = (5, 33) or, ceiling with rows < 3, (15, 43); each +6 (+10) → **(11, 39)** floor, (25, 53) ceiling. Free at left first. x > W/2: x > W - width → y = top', x - s; else x - s and y + s while y < bottom' - h. x in {48, 47, 46}: if top' < y: y - s and fire 5 when y == ship.y; else x - s (3310: x 40..42, speed + top < y). x < 46: x - s, y + s while y < bottom' (3310: y < bottom - speed). Clamp y <= bottom' - h. |
| `0x25b318` | `si_move_left_25b318` | `si_move_left_259120` | `move_left` | high | Same. |
| `0x25b34c` | `si_move_right_25b34c` | `si_move_right_259154` | `move_right` | high | Free at right else move; no second free (3310 frees twice on that path). |
| `0x25b37c` | `si_move_track_ship_25b37c` | `si_move_track_ship_259200` | `move_track_ship` | high | Same (y ±1 toward ship.y, x - speed, free at left). |
| `0x25b3ec` | `si_award_25b3ec` | `si_award_2592b0` | `award` | high | Kind **3** (bonus): **sound 0xfa0** (4000), then loop `rand() & 3`: 1 missile (7): +3 and icon mode 0x12 if held, else switch, count 3, icon replaced; 2 wall (6): switch with 3, or +3; 3 beam (8): switch with 1, or +1; 0 life, re-rolled while lives >= 5. Icon replacement = free + new picture (0x490134 / 0x49014c / 0x490164, mode 0x12) at the old position, **appended at the end of the draw list**. Kind **0x7e** (3310 0x31): score += amount, u16, **no 31500 cap**; score redrawn. No kind 0x21 (one bonus type). Always ends with the HUD refresh. |
| `0x25b4fa` | `si_explode_25b4fa` | none (3310 copies template 2 inline) | `explode` | high | Sets type 2 and the picture's frame list to the explosion's 5 descriptors (frame 0). **Keeps the rest of the record** (frames byte, hp, side, +0x10, pattern); 3310 copies the whole template. |
| `0x25b520` | `si_boss_destroyed_25b520` | `si_boss_destroyed_2593a4` | `boss_destroyed` | high | Frees the boss, ST+0x8d = 0x7f, **ST+0x57c = 0x1e** (chapter exit 30 ticks later; 3310 sets phase 0x1e at once). Explosions are always type 2 (3310 type 0x24 in level 7) with the chapter mode: one at the centre, then 5 pairs (6 in the last chapter) at ±(dx, dy): last chapter dx = rand()%20 + 1, dy = rand()%13 + 1; else dx = (rand() & 3) + 1, dy = 6. After each spawn `rand() % boss.frames` is written to **the freed boss record's +1** (not the new explosion's; no visible effect, but the rand calls happen: 1 + per pair 1 (2 last chapter) + 2). Score +100. Vibrator on for 3 ticks if not running. No sound. |
| `0x25b680` | `si_beam_scan_25b680` | `si_beam_scan_259534` | `beam_scan` | high | Records 0..59, not free, type not 0/2, side != 0x0a, |x - column| <= 3: bonus → award 3; non-boss → explode and +10; boss with hp < 3 → destroyed (no +10); boss → hp - 2 and +10. **Ignores +0xe** (boss projectiles and bullets score 10 when beamed; 3310 checks no_score). |
| `0x25b750` | `si_objects_step_25b750` | `si_objects_step_2596a0` | `objects_step` | high (asm) | **Records 0..58 in index order** (record 59 is never stepped; 3310 walks the sprite list). Every live record: frame stepped (`0x3f09c0(pic, 1)`, wraps), +1 = frame. Type 0 nothing. Type 2 at frame 4: the ship's → lives--, respawn (0x14) or, at 0 lives, continues < 2 → phase 0x3c, countdown 0x1e, save high score, return; else continues--, continue screen, return; others freed. Type 6 (wall): (ship.x + ship width + 2, ship.y - h/2 + 3), freed at frame 6. Type 8 (beam): column < W → **column += 2, line moved, then scanned** (3310 scans then advances: the 3410 beam is 2 px ahead); else freed (no count change), column 0. Others: pattern switch (section "Patterns"). No final-explosion type. |
| `0x25ba34` | `si_objects_overlap_25ba34` | `si_sprites_overlap_259a0e` | `sprites_overlap` | high | Inclusive box test on the **low bytes** of x/y with u8 wrap, sizes from the current frames. |
| `0x25bae6` | `si_find_hit_25bae6` | `si_find_hit_259a60` | `find_hit` | high | First record 0..59 (not free, type not 0/2, side != 0x0a) overlapping; 0 if none. Record order. |
| `0x25bb38` | `si_ship_pixel_collide_25bb38` | `si_ship_pixel_collide_259ab4` | `ship_pixel_collide` | high | Same overlap walk, solid = both clear (mode 0x12) / both set (0x20); **bitmaps are frame 0 of each type**, strides from the current frame widths. |
| `0x25bd24` | `si_ship_collisions_25bd24` | first part of `si_collisions_259d30` | `collisions()` first block | high | Unless ship lost: terrain (only chapters with their bit in CF u16 `0x11de52` = 0x00fd, i.e. all but chapter 1, like the 3310's level != 1) → ship lost, ship exploded, vibrator 3 ticks, **sound 0xfa7**. Then, without a shield, first hit k: type 5 or pixel hit → type 3: award + free; else hp--, at 0 non-boss explode (+10 unless +0xe), boss destroyed; ship exploded, ship lost, vibrator, **sound 0xfa7**. Ship mode unchanged (3310 sets polarity mode). No phase check (collisions are skipped in phase 0x1e by the tick). |
| `0x25be40` | `si_boss_pixel_hit_25be40` | `si_boss_pixel_hit_259c62` | `boss_pixel_hit` | high | Same row walk (dy = |shot.y - boss.y|, columns 0..shot width), boss **frame-0 bitmap**, stride = boss current width; solid by chapter mode. Returns dy or 0. |
| `0x25bf18` | `si_boss_weak_rows_25bf18` | none (3310 hard-codes 0x13..0x17 in level 7) | inside `collisions()` | high | Returns S[7], S[8] when both nonzero (chapter 7: 15, 24). |
| `0x25bf64` | `si_shot_collisions_25bf64` | loop part of `si_collisions_259d30` | `collisions()` loop | high | Records 0..59, not free, side != 0, not type 8. Terrain (flag chapters) and not the shield → freed, and **every later record skips its hit test this tick** (flag). The shield is not pushed off the terrain (3310 pushes ship and shield 2 px). Player side (0x0a) hit k: boss needs pixel dy != 0, or with weak rows S[7] < dy < S[8] (exclusive; 3310 0x13..0x17 inclusive); boss flash via TBL+0x54 (mode 0, alternate ticks). Shield (1): non-boss hp = 0, boss hp - 1; bonus → award, free, hp = 1 (so **+5**); **vibrator 3 ticks** (new). Shot (4): hp - 1. Wall/missile (6, 7): hp - 4 (min 0); hitting the missile target explodes the projectile. Then hp 0: non-boss non-bonus → explode, +10 unless +0xe; boss → destroyed; **a bonus at 0 hp is left alive**; hp != 0 → +5 unless +0xe. Projectile freed after a counted hit unless shield or wall (**missiles are freed too**). |
| `0x25c1a4` | `si_terrain_kills_25c1a4` | none (new) | none | high | Flag chapters: every enemy record (not free, type not 0/2, side != 0x0a, not a boss, pattern != 24) touching terrain explodes (no score). |
| `0x25c1f0` | `si_collisions_25c1f0` | `si_collisions_259d30` | `collisions` | high | Ship, shots, then terrain kills (flag chapters). |
| `0x25c218` | `si_next_chapter_25c218` | load part of the 3310 level exit (`si_event`) | in `level_exit_step` | high | Frees the fill, chapter++, chapter load (param 0), new ship (10). |
| `0x25c274` | `si_tick_25c274` | tick part of `si_event_25a200` | `tick()` + part of `si_handler` | high (asm) | See "One tick" below. |
| `0x25c6d4` | `si_demo_step_25c6d4` | none | none | high | Demo driver; see "Demos". |
| `0x25c974` | `si_handler_25c974` | `si_handler_25a52a` + `si_event_25a200` | `si_handler` | high (asm) | (event, a, b). Events < 3: High scores page (ST+0x57e == 1) → `0x259aec`; demo (ST+0x582) → `0x25c6d4`; title (ST+0x5a5) → `0x3daf94`; else `0x25c274`. Event 3 (pause): title → clear ST+0x582; High scores page → `0x259aec`; else save x/y of every live record (unless demo, phase 0x32 or 0x3c), free the terrain buffer, chapter data and all pictures, and save the state (`0x3b2922(0x5a8, ST)`) unless demo, phase 0x32, or phase 0x1e in the last chapter; ST+0x582 = 0; close. Others per the switch (corrections, item 5). No return-code protocol: the handler returns 1. |

Functions of the 3310 with no 3410 counterpart in this range:
`si_final_boss_spawn_258400`, `si_object_is_boss_2584c8` (replaced by +0x10),
`si_object_is_player_side_258e64` (replaced by +0xf side), `si_final_boss_step_2588c8`,
`si_move_boss_part_258c68`, `si_sprite_mode_restore_258aec` (inlined as mode 0x10),
`si_boss_flash_259cfe` (inlined in `0x25bf64`), `si_move_descend_25924c` and
`si_move_climb_259190` (replaced by path tables).

## 2. Types, records, state additions

Static (templates `0x4ace3c`, picture table image `0x405b88` → RAM `0x12a120`,
phone type table `0x4c1ae4` {frames, type, side, boss id} per type 20..53):

| 3410 type | What | 3310 type |
|---:|---|---|
| 0 | ship (10x7) | 0 |
| 1 | shield (13x11, 2 frames, hp 0x20, side 0x0a) | 8 |
| 2 | explosion (7x7, 5 frames) | 2 (and 0x24) |
| 3 | bonus (8x7, 2 frames, pattern 6 speed 1) | 0x11 and 0x21 (one type) |
| 4 | player shot (pattern 5 speed 2, side 0x0a) | 1 |
| 5 | enemy bullet (pattern 6 speed 3, +0xe = 1, side 0x14) | 4 |
| 6 | wall (5x5, 7 frames, hp 0x20, side 0x0a) | 9 |
| 7 | missile (5x3, hp 10, pattern 9, side 0x0a) | 10 |
| 8 | beam (line, hp 0x1e, pattern 5, side 0x0a) | 0x16 |
| 20, 21, 22, 23 | | 3, 5, 6, 7 |
| 24..29 | | 0xb..0x10 |
| 30, 31, 32 | | 0x12, 0x13, 0x14 |
| 33 (side 0x14 → +0xe = 1) | boss projectile | 0x15 |
| 34..43 | | 0x17..0x20 |
| 44 | final boss 38x38 | 0x22 |
| 45..53 | new pictures, unused by the built-in chapters | — |

The type table's 4th byte (+0x10) is a boss number (31 → 1, 32 → 2, 30 → 3,
34 → 4, 23 → 5, 35 → 6, 36 → 7, 44 → 8), but the spawn step overwrites +0x10
with 1 for the last entry; only zero/non-zero is tested.

Object record, 20 bytes: +0 frames, +1 frame (copied from the picture each
step), +2 type (0x7f free), +3 hp, +4 pattern, +5 speed, +6 fire chance,
+8 picture, +0xc/+0xd saved x/y, +0xe no score, +0xf side (0x0a player, 0x14
enemy bullets, 0 others), +0x10 boss.

State fields found beyond the doc: ST+0xc terrain bitmap, +0x10 terrain
picture (also +0x30), +0x14 terrain descriptor, +0x34 fill, +0x38 beam line,
+0x40 score digits (5), +0x54 count digits (2), +0x5c icon, +0x60 hearts (5),
+0x74 continue icons (4), +0x84/+0x88 countdown digits, +0x8d boss state,
+0x3d (cleared, use unknown), +0x54c four checkpoints, +0x550 checkpoint,
+0x552 chapter mode (u16), +0x55d boss record, +0x571 missile target,
+0x572 continues (start 4), +0x573 move acceleration, +0x578 root,
+0x57c shield / chapter-exit tick counter, +0x57d vibrator tick counter,
+0x57e High scores page active, +0x580 page step, +0x582 demo mode,
+0x584 demo counter, +0x588 high-score record (0x1c), +0x5a4 "last game
box shown", +0x5a5 title running. TBL: +2 burst pause, +3 boss-fire
cooldown, +4/+5/+6 bounce latch/direction/age, +8 templates, +0xc chapter
records, +0x10 tile sets, +0x14 pictures, +0x18 tilemaps, +0x1c..+0x2c paths,
+0x30..+0x3c High scores page pictures, +0x40 chapter-file buffer, +0x44
active path, +0x4c demo pointer picture, +0x50 last bounced picture, +0x54
flashed boss picture.

## Patterns (jump table 0x25b7d0, static)

| Pattern | 3410 | 3310 |
|---:|---|---|
| 1 | path TBL+0x1c (0x4ad094: the 3310's wave_abs extended to 96 entries), base 0 | same table |
| 2 | path TBL+0x28 (0x4ad0f4: 25 for x <= 38, 25→6 over x 39..57, 6 beyond), base 0; **no fire** | computed descend, fires when turning |
| 3 | track ship | same |
| 4 | path TBL+0x2c (0x4ad154: 7 → 25 over x 40..57), base 0; **no fire** | computed climb |
| 5 / 6 / 7 / 9 | right / left / dive / missile | same |
| 10..13 | rel path **0x4ad1b4** + 0x23 / 0xb / 0xe / 0x19 | 3310 wave_rel (±4, period 42) |
| 14 | rel path 0x4ad1b4 + 0x12 | same |
| 15, 16 | TBL+0x20 / +0x24 (0x4ad31c rise, 0x4ad2bc fall, 96 entries) | rise / fall 84 |
| 17, 18 | slope ceiling / floor | same |
| 8, 19..22 | nothing (22 was the boss part) | 22 boss part |
| 23 | boss | boss |
| 24 | x <= (W/3)*2 = 64 → bounce (fire 5) else x - 1; boss state set → pattern 3 speed 1 | x <= 56 |

**The relative wave is a different table**: `0x4ad1b4` is ±5 with a period of
about 13 px (2, 4, 5, 4, 3, 1, 0, -2, -4, -5, ...); the 3310's `0x312158` is
±4 with a period of 42. All bases and rows get the +6 (floor) / +10 (ceiling)
shift on 96 columns.

## One tick (`0x25c274`, event 0, static from asm)

1. Event 1 with a demo running → key handler `0x259d30(a)`. Event 2: key-up
   resets (1/3 → ST+0x564; 4/6 when neither held → ST+0x565; 0, 8, *, # →
   ST+0x573).
2. Phase 0x14: any key event goes to `0x259f92`; on a restart the countdown is
   5. Phase 0x32 on a tick: free chapter data and buffer, close.
3. Non-tick events return here.
4. ST+0x57c countdown: at 1 → 0, remove the shield (if any); if the boss is
   dead (0x7f): phase 0x1e, save the high score if this is the last chapter,
   hide the terrain picture.
5. ST+0x57d countdown: at 0 the vibrator goes off.
6. Phase 0x14: countdown--; < 0 → period 100, phase 0x3c, countdown 0x1e,
   save high score, return; else redraw the countdown, redraw, return.
   Phase 0x1e: ship x += x/5 + 1; when x > W + 20 = 116: next chapter, or the
   end (phase 0x3c, countdown 0x1e, save high score, return). Phase 0x3c: the
   game-over screen (section 3), return.
7. Terrain render at the current scroll; scroll + 1 (mod width*32) while the
   delay and the entries left are both nonzero. No last-level scrolling rule.
8. Unless phase 0x1e: keys (`0x25a110`).
9. Spawn step, objects step. Return if the phase became 0x14 or 0x3c.
10. Unless phase 0x1e: collisions.
11. Fire cooldown 1 → 2 → 0.
12. Fill to the head of the draw list; a live boss right after the fill (or
    to the head).
13. Shield to (ship.x - 2, ship.y - 2). Redraw.

3310 differences: keys are events between ticks; the level-exit line-up
step; collisions in phase 0x1e (minus ship-vs-object); the pending result
that swallows the next event.

## 1. Collisions and scoring

Identical to the port: bounding box then pixel test for the ship (bullets box
only); pixel sense by draw polarity; shots 1 hp, wall/missile 4, shield kills
ordinary enemies and takes 1 from a boss; bosses tested per row and flash on
alternate hits; +5 hit, +10 kill, +100 boss; boss projectiles score nothing
when shot; terrain removes projectiles in the same chapters as the 3310
(all but chapter 1).

Differences:
- Iteration is by record index 0..59, not the draw list; "first hit" is the
  lowest record.
- Pixel tests use the frame-0 bitmap of the type with current-frame widths.
- After a projectile is removed by terrain, no later projectile is tested in
  that tick.
- No shield push off the terrain.
- Weak rows of the final boss: 15 < dy < 24 from the chapter settings (3310:
  19..23 in level 7), no boss parts.
- Shield contact with an enemy vibrates (3 ticks); a bonus taken by the
  shield scores +5 as well.
- Shots do not collect bonuses: a bonus brought to 0 hp stays; further hits
  wrap its hp to 255 and score +5.
- Missiles are freed on a hit (3310 keeps them unless they hit their target).
- Enemies die on terrain in flag chapters (`0x25c1a4`); the 3310 lets them
  pass.
- Beam kills score 10 even for no-score objects; the beam is 2 px ahead.
- Score is u16 with no cap (3310 stops below 31500).
- Ship destroyed by terrain or contact: sound 0xfa7, vibrator 3 ticks.

## 2. Bosses

Static. The boss is the last script entry; behaviour comes from the chapter
settings (section 4), not from code per level. Every step ends with mode 0x10
(copy), and the tick puts the boss right after the fill.

| Ch. | Type (3310) | Boss hp 3410 / 3310 | Fire chance 3410 / 3310 | S[0] | S[2] projectile | Offset | Proj. pattern, speed |
|---:|---|---|---|---|---|---|---|
| 0 | 31 (0x13) | 25 / 25 | 45 / 40 | 1 bounce | — | — | — |
| 1 | 32 (0x14) | 50 / 40 | 20 / 20 | 1 bounce | — | — | — |
| 2 | 30 (0x12) | 70 / 60 | 30 / 30 | 2 charge 100 | — | — | — |
| 3 | 34 (0x17) | 75 / 50 | 10 / 10 | 1 bounce | 33 (0x15) | (7, 6) | 3, 3 |
| 4 | 23 (7) | 80 / 80 | 20 / 20 | 2 charge 100 | 29 (0x10) | (0, 12) | 6, 3 |
| 5 | 35 (0x18) | 80 / 60 | 5 / 15 | 3 charge 150 | 27 (0x0e) | (4, 6) | 6, 3 |
| 6 | 36 (0x19) | 45 / 45 | 15 / 15 | 3 charge 150 | 22 (6) | (6, 14) | 6, 3 |
| 7 | 44 (0x22) | 120 / 50 | 8 / 20 | 0 stand and fire | 40 (0x1d) | (6, 14) | 3, 4 |

Same as the port: enter at 1 px/tick, bounce/charge/back-off state values 10,
0x14, 0x1e, 0x28, charge 2 or 4 px, the 1-in-50 charge roll, boss projectile
cooldown 6, hp - 2 per beam pass, explosion pattern and +100.

Differences: thresholds from the screen (enter x 59, charge back at x 59,
return at x <= 12, back-off to x 96, charge only at x <= 64); bounce rewritten
(per-object direction, latch); projectiles always fire regardless of charge
state, hp 3, pattern/speed from settings (ch. 5's second offset for frames
>= 2 is gone); the boss's own bullets use S[1] = type 5; the final boss has no
parts, no back-off/wall cycle (3310 states 0x32..0x50, wall of type 0x1f), no
special scroll spawn, is in the script (row 7 + 6 = 13); its explosions are
ordinary type 2 (no type-0x24 lingering explosions and their vibration); boss
death waits 30 ticks (ST+0x57c) before the exit phase, during which play goes
on (the ship can still die); vibration 3 ticks, no sound.

## 3. Continue screen and game over

Same as the port: continues counter 4, continue screen only at >= 2 (then
decremented), four icons with the spent ones hidden, a two-digit countdown from
5 at 800 ms that shows 4..0 then ends, restart of the current chapter from its
beginning with 3 lives and 3 specials (checkpoint cleared before it is read).

Differences: only keys 1 and 3 restart; the restart gives walls (type 6), not
missiles; the vibrator is switched off on entry; positions (42, 28)/(46, 28).

Game over is a screen of the game's own (phase 0x3c, 30 ticks of 100 ms,
counted in ST+0x55c), not a return code:
- first tick (count 0x1e): read the high-score record (`0x3b299c`), free all
  pictures, full-screen fill (mode 0x10), 30 random stars (`0x3dafe8`, the
  title's: x = rand() % W, y = rand() % H, picture 0x4917a8, mode 0x12;
  60 rand() calls), a 50 x 20 box (`0x3ef324`, mode 0x10) at
  (W/2 - 25, H/2 - 6) = (23, 26); **sound 0xfa4** if the score is >= the
  (already updated) top score for this chapter file, else **0xfa2**; the score
  in the box and the two title logo halves (`0x3db102`: 0x4abd88 at
  ((W - 80)/2, 11) = (8, 11), 0x4abda0 at ((W - 89)/2, H - 25) = (3, 40); the
  score with `0x25cb9c(5, score, ..., pos)`, whose digits use mode 0x16
  when a stack flag is set, else 0x12; inferred: the flag is the new-top
  result `0x3db102` receives, so the digits blink on a new top score);
- counts 0x1d..0x17: upper half up 1, lower half down 1 (8 ticks);
- at 0: phase 0x32; the next tick frees everything and closes the game
  (`0x3b29de`) back to its menu.
Entered from: the last ship lost with continues < 2 (directly, period stays
100), the continue countdown expiring (period set back to 100), or the end
of the last chapter.

## 4. Chapter settings (9-byte records)

Static: file section after the spawn scripts, one per chapter, copied by
`0x35ce02` to CF+0x7c with file bytes 3 and 4 swapped. Stored layout S:

| S | Meaning | Built-in values ch0..7 |
|---:|---|---|
| 0 | boss behaviour: 0 stand and fire, 1 bounce, 2 charge (reach 100: 2 px), 3 charge (150: back off first, 4 px) | 1 1 2 1 2 3 3 0 |
| 1 | bullet type the boss fires through the ordinary fire roll | 5 for all |
| 2 | boss projectile type, 0 none | 0 0 0 33 29 27 22 40 |
| 3 | projectile dy from the boss's top (file byte 4) | — — — 6 12 6 14 14 |
| 4 | projectile dx from the boss's left (file byte 3) | — — — 7 0 4 6 6 |
| 5 | projectile movement pattern | 3 3 3 3 6 6 6 3 |
| 6 | projectile speed | 1 1 1 3 3 3 3 4 |
| 7, 8 | boss weak rows (exclusive bounds), 0 = whole picture | 0 … 15, 24 |

(Inferred only for S[5], S[6] of chapters without a projectile: unused.) The
file header's two little-endian u16 after the tilemap count are bitmasks by
chapter: `0x11de50` = 0x0030 terrain on the ceiling (chapters 4, 5),
`0x11de52` = 0x00fd terrain kills the ship, removes projectiles and
destroys enemies (all but chapter 1). The 6-byte chapter records give entries,
four checkpoint bytes (all 0) and the mode (0x12/0x20).

Script differences against the 3310 (static, entry by entry): the shots byte
is gone; type numbers remapped (section 2); bonus hp 99 → 0..2; chapter 1
has one more entry (a group of five type-20 at entry 4); boss hp/fire as in
the boss table; chapter 5's two empty entries dropped and its boss row 16
fire 5; chapter 6 entries 0, 2, 3 use patterns 13, 12, 13 (3310 10, 14, 10),
entry 4 delay 20 (0), entries 7..9 rows 27, 35, 18 and delays 12, 28, 6
(3310 32, 40, 18 and 12, 18, 23); chapter 0 entry 9 delay 60 (30), entry 13
delay 80 (50).

## 5. The end sequence

Static. After the last chapter's boss: the 30-tick delay, phase 0x1e (high
score saved on entry, terrain hidden), the ship flies right with dx = x/5 + 1
per tick (no vertical line-up first; the 3310 lines up with the top then
accelerates by +1 every x % 3 == 0, exiting at x > 104), at x > 116 the high
score is saved again (second rand()) and the game-over screen of section 3
runs (0xfa4 / 0xfa2). There is no separate ending picture. Pausing in phase
0x1e of the last chapter does not save the game.

## 6. Sounds and vibration

`0x3b2510(id)` plays at once (when game sounds are on, `0x3f7ebe`); there is
no pending-result mechanism, so no tick is ever skipped for a sound.

| Id | When | 3310 |
|---:|---|---|
| 0xfa0 | bonus collected (`0x25b3ec`, before the rolls) | 0x1f |
| 0xfa5 | every shot fired (also held repeats) | 0x18 (first shot of a press only) |
| 0xfa6 | wall or missile | 0x19 |
| 0xfa8 | beam | 0x1a |
| 0xfa7 | ship destroyed (terrain or contact) | 0x17 |
| 0xfa4 | game over / end with a new top score (>=) | none (framework) |
| 0xfa2 | game over / end otherwise | none |

The 3410 sound table is `sound_table_4a9078`; the scripts behind 0xfa0.. were
not traced (Snake II uses 0xfa0 for a meal and 0xfa1/0xfa2/0xfa4 too).

Vibrator `0x3b25d4(on)`: on (1) only when ST+0x57d is 0, then ST+0x57d = 3
(off after 3 ticks, about 300 ms): ship destroyed, shield hitting an enemy,
boss destroyed. Off (0) by the counter and on entering the continue screen.
3310: 62 timer units (about 480 ms) restarted on every call, also for each
final-level explosion; no shield vibration.

## 7. Tick periods (`0x3b2546`)

100 ms: ship spawn (new game, respawn, next chapter, continue restart),
resume, High scores page, continue countdown expiry. 800 ms: continue screen.
Title (outside the range): 210 ms (`0x3db036`), 700 ms at step 10
(`0x3daf94`). There is no one-shot timer: the shield (30 ticks, 10 or 92 after
a resume), the chapter-exit delay (30), the vibrator (3) and the game-over
screen (30) are tick counters.

## 8. Random numbers

Only the ANSI generator (`0x3b2958` → `rand_3f903c`, state `0x12ebac`,
`(seed & 0x7fffffff) >> 16` per the 3310's rand), reduced with unsigned
modulo `0x3f77e8` (or `& 3`). The 3310 used game_rand16 (LCG mod 0xfff1)
for everything except random rows. Order of draws inside a play tick:
1. spawn step: one per group member with row 0x3f (as on the 3310);
2. objects step, records 0..58 in index order: per object as its movement
   calls it — fire roll (`rand() % fire`, plus `rand() % 3` for a pattern-20
   burst reset) in bounce (every step, before the boss-state write), slope
   and path (when their condition holds), boss stand-and-fire, boss
   projectile roll, then charge `rand() % 50` after the bounce in the default
   state; beam record → beam scan → boss destroyed draws;
3. collisions: bonus award `rand() & 3` (repeated while lives >= 5 on a 0),
   boss destroyed draws (centre frame, then per pair dx/dy and two frames).
Outside play: one draw in each high-score save (twice at the end of the
last chapter), 60 on the game-over screen (stars), 60 on the title. Because
the walk is by record index and records are reused lowest first, the order
of fire rolls differs from the 3310's draw-list order.

## 9. High-score record and the Chapters menu

Record (0x1c bytes at ST+0x588, read with `0x3b299c`, written with
`0x3b289c(0x1c, rec)` then `0x3b29f4()`), filled by `0x259ff4`:

| Offset | Content |
|---:|---|
| +0x00 | top score with the built-in chapters (setting 4 == 1), replaced when greater |
| +0x04 | top score with a downloaded chapter file; replaced when greater, or whenever the file differs from +0x08 |
| +0x08 | id of the file +0x04 belongs to (also written after a built-in top) |
| +0x0c | last game's score |
| +0x10 | rand() at the save |
| +0x14 | last game's chapter-file id (setting 4) |
| +0x18 | CF+0x48, a header byte of the chapter file (1 for the built-in file) |

The High scores page (`0x258a52`, `0x259aec`) shows +0x00 or +0x04 with
medals and, when the selected file is the last game's, +0x0c in a second box,
then the animation; key 0x0c submits (inferred). The Chapters menu is the
choice of chapter file, game setting 4 (1 = built-in): event 0x12
(`0x258b70`), event 0x11 for a received file (parse with `0x35cf30`, store
with `0x3f4314`, select with `0x3b255c(2, 4, 1, 1, id)`); the menu itself is
framework code (`0x34e42e`, `0x34e9ae`), not in this range.

## Demos (`0x259a90`, `0x25c6d4`, static)

Event 9 with a = 1, 2 or 3 starts a game on the built-in chapters without
reading the high-score record and replays keys through the same tick/key code;
any key-down ends it. Counter c = ST+0x584 per tick event:
- 1 (fire): c < 20 plain tick; 20..37 and c % 3 == 0 key 8 (up) instead of a
  tick; c < 100 and c % 5 == 0 key 1 instead of a tick; c == 100 end.
- 2 (keys): picture 0x4b4a80 at (60, 21) and a pointer 0x4b4a98 at (68, 33),
  moved at c = 10 (68, 38), 20 (74, 38), 35 (62, 38), 50 (62, 23), 65 (74, 23),
  80 (62, 28), 100 (74, 28); key then tick: 8 for c < 12, 0 for < 20, # for
  < 35, * for < 50; 50..75 every 3rd: fire count reset and key 1 alone;
  85..109 every 15th: special latch reset and key 4 alone; end after 114.
- 3 (bonus): chapter record 0x4ad390 (two bonuses); c 31..50 key # then the
  tick; end after 59.

## 10. Graphics-library calls the game makes

All pictures are children of the screen root (`0x3fa0bc()` = `0x12d2c4`,
stored in ST+0x578). Static, from the callers and the library entry code.

| Call | Arguments | Meaning |
|---|---|---|
| `0x3fa0b4()`, `0x3fa0c0()` | | screen width 96, height 65 |
| `0x3f0948(parent, mode, &pos, frames, count)` | count on the stack | create an animated bitmap (object type 4): +2 mode, +0x10 frame list (array of 24-byte descriptors {u16 w, u16 h, u16 0, u16 1, u32 bitmap, 12 bytes 0}, consecutive frames 24 bytes apart), +0x14 x, +0x16 y, +0x18 count, +0x1a frame = 0; appended after the parent's last child (`0x3d64c4`, `0x3d64e2`) |
| `0x3ef324(parent, mode, &pos, w, h, 1, 0, 0, 0)` | | filled rectangle (types 5..8): full-screen fill, the game-over box; the trailing words are not decoded (inferred: fill on, no border) |
| `0x3ea886(parent, mode, &p0, &p1, 1, 0, 1, width)` | width 1 (beam), 1 or 2 in the score box | line (object type 6) |
| `0x3ea83e(line, &p0, &p1)`, `0x3ea7be(line, &p0, &p1)` | | get / set a line's end points |
| `0x3da9d0(obj, &pos)` | | set position (type 4 at +0x14, line +0x1c, type 3 +0x38, 5..8 +0x18) |
| `0x3dab66(obj, &pos)` | | get position |
| `0x3daaf4(obj, dx, dy)` | | move by |
| `0x3daad6(obj, mode)` | | set draw mode (0 hides; see the doc's mode table); refused for the root |
| `0x3daa22(obj, 0, after)` | | move in the sibling list: after `after`, or to the head when 0 |
| `0x3dac10(obj)` | | free the object, its children first (on the root: every game picture) |
| `0x3f08ec(obj, frames, count)` | | replace the frame list, frame = 0 (digits, explosion, terrain refresh) |
| `0x3f08c8(obj, n)` | | set the frame if n < count |
| `0x3f0922(obj, &n)` | | get the frame (u16) |
| `0x3f09c0(obj, 1)` | | next frame, wrapping to 0 (other values: previous, wrapping to count - 1) |
| `0x3b24fc()` | | request a redraw (flag 2 at 0x12d293) |
| `0x3b2546(ms)` | | set the tick period (flag 4) |
| `0x3b29de()` | | close the game back to its menu (flag 1 at 0x12d293; inferred) |
| `0x3b29d0(key)` | | key state; held when `(v & 0xf) >> 1 != 0` |
| `0x3b268a(digits, top, value, 0)` | | score box (shared with Snake II's High scores page) |
| `0x25cb9c(5, value, ?, &pos, newtop)` | | score in the game-over box (outside the range) |

For the C port: each record's picture becomes a sprite with {frame list,
count, frame, x, y, mode}; lines and fills are two more kinds; the list
order is creation order with the two explicit moves (fill to the head every
tick, the boss after it, the terrain to the head once per chapter); pixel
tests and widths read the descriptors as above (widths of the current frame,
bitmaps of frame 0).
