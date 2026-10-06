# Kart Racing (3510): the shell (everything except the race tick)

Part of the Kart Racing map; start at `games_kart_3510.md`, which resolves the points where the slices disagreed. Names are in `ghidra/symbols/3510.csv`.

Image `roms/3510-nhm8-v502/flash.bin`, big-endian Thumb, base 0x01000000. App id 0x4b.
Every claim is marked **S** (static: read from code, literal pools or data) or **I** (inferred).
"msg" means the first argument of `kart_handler_14047f0(msg, a1, a2)`.
Points `{x, y}` are two s16, x first (the high half of a BE word; Ghidra's CONCAT22 shows it
as the high half).

Globals are RAM pointers (`*0x3cc54` = the state struct). The race and road agents own most of
the other `0x3cxxx` pointers; the ones this slice allocates or frees are in the table at the end.

## Functions

| Addr | Name | Signature | What it does | S/I |
|---|---|---|---|---|
| 0x014047f0 | kart_handler_14047f0 | `int (msg, u32 a1, void* a2)` | Message switch (see "Messages"). Always ends with `kart_deferred_run_140d980(0x3cffc)` | S |
| 0x0140491e | kart_session_init_140491e | `int ()` | Clears the scene (`game_obj_delete(root)`), zeroes the pointers 0x3cc3c..0x3cc5c and 0x3cc70, callocs the **0x18-byte state** into `*0x3cc54`, `game_srand`. Reads app data (1 byte; if absent, writes default 0x78) into +0xc, setting 3 → +0xd, setting 2 → +0xe, setting 4 (if +0xd==1) or 5 (if +0xd==2) → +0xf = (v≠0), +0x10 = v. +0x15 = 0 | S |
| 0x01404a56 | kart_session_free_1404a56 | `int ()` | Frees by phase (+0): phase 0 → `0x014079b8` + free `*0x3cc48`; phase 1..2 → `kart_race_free_1405f60`, `kart_track_free_1406084` if `*0x3cc40`, `0x01406a6c`; phase 3..9 → `0x014079b8`, `0x014084f4`, `0x014084b0`, `0x0140830c`, deletes objs `*0x3cff8`, `0x3ce94[0..1]`, frees `*0x3cc4c`. Then custom kart free if +8, frees the state, `*0x3cc44`, `*0x3cc70`, `*0x3cc68`, `*0x3cc6c`, `*0x3d0b8` | S |
| 0x01404b8c | kart_savegame_write_1404b8c | `uint ()` | Builds the save game by phase and calls `game_savegame_write` (layouts below). Returns 1 with no state | S |
| 0x01404fd8 | kart_savegame_restore_1404fd8 | `void (u32 size, u8* data)` | Frees everything, `game_srand`, key layout 0, (re)allocs the state and copies 0x18 bytes, loads the custom kart if +8, rebuilds the phase's data (phase 1..2: key layout 2, track via `kart_track_load_140c94c(+0xf)`, `kart_scene_build_1405534`, `kart_track_add_start_objs_1405ad6`, kart records, re-linked object pointers, the saved type-99 track objects). Ends with `kart_handler_14047f0(0,0,0)` (one tick) | S |
| 0x01405534 | kart_scene_build_1405534 | `int ()` | Two backdrop sprites side by side at y=0 (`kart_sprites_1504bf8`-area table 0x01504c40 + idx*0x18, or custom `*0x3d074` when track+3 bit 7), a rect at their right edge (w 0x60) → `*0x3ce9c`, 65x2 road rects (x -1 / 0x61) → `0x3cc74[row*2+side]`; then `kart_sprites_mirror_1405778` and zeroes the HUD/race arrays 0x3ce7c..0x3ce90, 0x3cf34, 0x3cff8, 0x3cf38/0x3cf14/0x3cf04[4], 0x3cea4[6][4], 0x3cf68[3][4] | S (I: rects are the per-row road spans the road agent drives) |
| 0x01405778 | kart_sprites_mirror_1405778 | `int ()` | mallocs 0x364 into `*0x3cc60` and a pixel buffer at +0x360; for 4 scales makes mirrored (`game_bitmap_blit_scaled`, xform 0x1000-flag call) copies of kart sets 0x015046a0 (4 descs), 0x015049a0 (7 per scale, stride 0x60) and 0x01504d30 → descriptors at `*0x3cc60` +0, +0x60.., +0x300 | S (I: left-turn frames from the right-turn ones) |
| 0x01405ad6 | kart_track_add_start_objs_1405ad6 | `int ()` | Appends two 0x14-byte objects to the track list `*(*0x3cc40+8)`: type 0x66, x byte 0xb5 then 0x4b, +5 = 1, +9 = 0xff; track+1 += 2 | S (I: the start/finish gantry posts) |
| 0x01405b68 | kart_custom_kart_load_1405b68 | `int ()` | If a downloaded kart exists (`kart_custom_kart_read_140d20a`): callocs 0x154 → `*0x3cc64` (+0x150 = 0x468 B pixels), builds 4 scales (8/12/16/20 px) x {frame, frame, mirrored} descriptors and 2 0x30x0x19 portraits; state+8 = 1; copies 4 stat bytes to `0x3d0b0..b3`. Else state+8 = 0 | S (I: stats = 4 x 3-bit kart attributes) |
| 0x01405e82 | kart_custom_kart_free_1405e82 | `void ()` | state+8 = 0, frees `*0x3cc64` and its buffer | S |
| 0x01405ebc | kart_new_game_1405ebc | `int ()` | msg 0xa: callocs 3 bytes → `*0x3cc48` (all 0), key layout 0, state+1 = 7, loads the custom kart, zeroes 0x3cf98[4], 0x3cf24[4], 0x3cfa8[4][5], `*0x3ce94`, `*0x3cea0`, `*0x3cc68`. Phase stays 0 | S (I: phase 0 = kart selection, `kart_?_140853c` draws 4 portraits per page and greys the ones whose bit is set in +0xc) |
| 0x01405f60 | kart_race_free_1405f60 | `int ()` | Frees `*0x3cc50`, `*0x3cc58`, `*0x3cc5c`, deletes backdrop sprites, `*0x3ce9c`, the 130 road rects, the `*0x3cc3c` object chain, `*0x3cc60`; frees custom sprites/bitmaps/backdrop; then `0x01407b24` | S |
| 0x01406084 | kart_track_free_1406084 | `void ()` | Frees the segment array (+4), the circular object list (+8) and the 12-byte track `*0x3cc40` | S |
| 0x0140c94c | kart_track_load_140c94c | `int (bool custom)` | custom == 0 → `kart_track_load_builtin_140cbfc(0)` (on failure state+1 = 6). Else loads game data (id = +0x10 & 0x7fff, type = +0xd) and builds the 12-byte track from variant `+4` (rand&3 if > 3): item 1 → laps 3, karts 6; item 2 → laps/karts/+0xe and the 16-byte `*0x3cc5c` rules from the data; then segments, objects, custom sprite sets, bitmaps, backdrop | S |
| 0x0140cbfc | kart_track_load_builtin_140cbfc | `int (int base=0)` | Item 1: track = `*0x3d090[base + (+4 or rand&3)]` (4 tracks); item 2: 0x015097d4. Track header {nseg, nobj, backdrop}. Item 1: laps 3, state+1 = 6. Item 2: laps 1, state+1 = 4, +0xe = 2, `*0x3cc5c` = {0, u16 0, 20000, 2000, 0} | S (I: 20000/2000 ms) |
| 0x0140ca96 | kart_track_segments_load_140ca96 | `int (u8* p)` | nseg x 4-byte {u16 len = p[0]*5, u8 p[1]} → track+4 | S |
| 0x0140caf0 | kart_track_objects_load_140caf0 | `int (u8* p)` | nobj x 5 bytes → 0x14-byte circular list nodes {u16 pos, u8, u8, s8 sign-magnitude x, u8 b4&0x1f, u8 (b4>>5)*5, 0, 0, 0xff, +0xc next, +0x10 prev} | S |
| 0x0140c530 / c5c0 | kart_custom_backdrop_load / free | `int (gd*)` / `void ()` | `*0x3d078` = a descriptor of the data's backdrop (w +0x39, h +0x38) | S |
| 0x0140c5dc / c6d4 | kart_custom_bitmaps_load / free | | up to 4 bitmaps (+0xb6) → `*0x3d074` (used when track+3 bit 7 is set) | S |
| 0x0140c702 | kart_bitmap_make_140c702 | `int (bmp* d, {w,h}*, data, mask)` | descriptor with malloc'd data + mask copies | S |
| 0x0140c75e | kart_bitmap_bytes_140c75e | `int ({w,h}*)` | w * ((h+7)>>3) | S |
| 0x0140c76e | kart_custom_spriteset_load_140c76e | `(dst, sizes*, bytes, u8** cursor)` | 4 scales (largest at dst+0x48 down to dst) from a {w,h}[4] template | S |
| 0x0140c7c6 / c7e2 / c7f2 / c7d4 | kart_custom_spriteset_a/b/c/d | | templates 0x01509860 (0xe8 B), 0x01509880 (0x110), 0x01509890 (0xf0), 0x01509870 (0x88) | S |
| 0x0140c804 / c914 | kart_custom_sprites_load / free | | `*0x3d07c` = {set a, set d, set c, set b, end}, counts +0xb2..+0xb5 | S (I: downloaded roadside objects) |
| 0x0140cfa0 | kart_gd_parse_140cfa0 | `int (gd* out0xb8, u8* data)` | Parses downloaded Kart game data (format below); returns bytes used | S |
| 0x0140cce8..0x0140cf66 | kart_gd_read_* | `u8* (dst, u8* p)` | the field readers of cfa0 | S |
| 0x0140d026 | kart_menu_option_add_140d026 | `(wchar* name, opt_id, u32 v, item)` | `game_menu_option_append(0x4b, item, opt_id, {add_string(name), v|0x8000})` | S |
| 0x0140d054 | kart_gd_list_in_menu_140d054 | `int (u32 id, gd*)` | type 1 → option 4 of item 1; type 2 → option 5 of item 2; type 3 → 1 (karts are not listed) | S |
| 0x0140d086 | kart_gd_load_140d086 | `int (u32 id, u8 type, gd*)` | `game_gamedata_read`, queues `game_free(buf)` on the deferred list, parses; fails unless version byte +0xb0 == 0 | S |
| 0x0140d0dc | kart_gamedata_receive_140d0dc | `int (msgparam*)` | msg 0x11: parses `a2+8`, `game_gamedata_store(0x4b, type, size, data)`, lists it (type 3: `*0x3d0bc` = id). If the matching item's track option is in use, `game_savegame_clear`; for item 2 also `kart_modedata_set_kind_140d588(+0x83)` | S |
| 0x0140d1b0 | kart_gamedata_relist_140d1b0 | `int (rec*, u16 type)` | msg 0x12: reloads one stored game-data record and lists it again (type 3 → `*0x3d0bc`) | S (I: called once per stored record at start-up) |
| 0x0140d20a | kart_custom_kart_read_140d20a | `int (gd*)` | if `*0x3d0bc` ≠ -1: `kart_gd_load(*0x3d0bc, 3, gd)` | S |
| 0x0140af18 | kart_demo_start_140af18 | `uint (u8 n)` | msg 9: state+5 = 1, mallocs the 0x2c demo struct `*0x3d0c0` with per-demo constants, a backdrop sprite at (0,4), 65x2 road lines, zeroes the HUD objs, mirrored sprites | S |
| 0x0140b0be | kart_demo_msg_140b0be | `int (msg, a1)` | msg 0: frame++ (until +4), scroll -= speed (wraps by 0x700), road, HUD, the demo's frame function; at the last frame or on msg 1 → `kart_demo_end_140b1a4`; other msgs → 0 | S |
| 0x0140b1a4 | kart_demo_end_140b1a4 | `int ()` | Deletes the demo objects and lines, frees, `game_exit`, `kart_session_free` | S |
| 0x0140b2c0 / b648 / b774 / c0fc | kart_demo{0..3}_frame | `int ()` | Frame-scripted sprite placements (see "Instructions") | S (meaning I) |
| 0x0140c19c | kart_demo_road_140c19c | `void ()` | straight-road spans for rows 0x40..0x17 from `kart_row_depth_150912c` and the scroll, alternating stripe widths 0x46/0x3c | S |
| 0x0140c2ac | kart_demo_hud_140c2ac | `int (p1, p2, p3, p4, u32 time)` | the HUD bar (see "Instructions") | S |
| 0x0140d234 | kart_best_show_140d234 | `int ()` | msg 0xb: state+7 = 1, reads mode data (inits it if +0x14 ≠ 1), `*0x3d06c` = best (+0xc built-in / +0x10 custom), keeps a second copy in `*0x3d070`, period 50 | S |
| 0x0140d2fa | kart_best_draw_140d2fa | `int ()` | redraws the best-score screen (layout below) | S |
| 0x0140d4fe | kart_best_msg_140d4fe | `int (msg)` | msg 0: counter `*0x3d068`++ and redraw; other msgs: nothing | S |
| 0x0140d520 / d554 | kart_modedata_init_a/b | `void (void** rec)` | the default 0x18-byte mode record (+8 = `game_rand()`, +0x14 = 1), written | S |
| 0x0140d588 | kart_modedata_set_kind_140d588 | `void (u8)` | mode record +5 = v, +0x10 = 0, +0 = 0 if +4 == 1 | S |
| 0x0140d5e4 | kart_record_save_140d5e4 | `int (u32 v)` | called by the race code (0x014087a8, 0x014088ae) after a race: last = v, +4 = +0xf, best per rules below | S |
| 0x0140d6a8 | kart_best_end_140d6a8 | `void ()` | deletes the screen, state+7 = 0, `kart_session_free`, `game_exit` | S |
| 0x0140d72c | kart_title_create_140d72c | `int ()` | flag 0x01508f10 (81x61) at (7,2); "KART" 0x01508f28 (96x19) at (-91,10); "RACING" 0x01508f40 (119x19) at (84,25) | S |
| 0x0140d798 | kart_title_show_140d798 | `int ()` | msg 0xe: state+6 = 1, clears `0x3d0a0[0x10]`, clears the scene, period 300, creates | S |
| 0x0140d7d6 | kart_title_animate_140d7d6 | `void ()` | logos to `0x01508f54[n]` and `0x01508f78[n]`, n = `*0x3d0ac` | S |
| 0x0140d7fc | kart_title_msg_140d7fc | `int (msg)` | msg 0: n++; n<9 animate; n==9 period 1500; n≥10 end. msg 1 → end | S |
| 0x0140d83e | kart_title_end_140d83e | `void ()` | deletes, state+6 = 0, `kart_session_free`, `game_exit` | S |
| 0x0140d910 | kart_register_140d910 | `void ()` | msg 7 (see "Registration") | S |
| 0x0140d8a0 / d8be / d8da | kart_register_item1 / item2 / options | | the three helpers | S |
| 0x0140d980 | kart_deferred_run_140d980 | `void (list*)` | runs and frees every `{fn, arg, next}` node (each `fn(arg)`), tail = 0 | S |
| 0x0140d9a8 | kart_deferred_add_140d9a8 | `bool (list*, fn, arg)` | appends a 0xc-byte node; used only to free game-data buffers after the message | S |
| 0x0140cba8 | kart_unknown_140cba8 | `int (u8** cur, wchar** out)` | reads a length-prefixed UCS-2 string; no callers; it indexes `out[i]` as if it were an array of pointers (buggy, dead) | S |

## Messages and the state machine

How the engine calls Kart (S, from `0x01427d14`, a switch on engine state `*0x3d730` with handlers
0: 0x01427d9e, 1: e2a, 2: ede, 3: ee2, 4: ee6, 5: f30, 6: 804c, 7: f9e, 8: 8084; and the menu
actions in `0x014261c6`, a 24-way switch on the menu entry's type):

| msg | Sent when | a1, a2 | Kart does | S/I |
|---|---|---|---|---|
| 7 | engine init (state 0 → 2), once per app in `games_handlers_1511ebc` | 0, 0 | registration | S |
| 0xe | menu entry type 5 (selecting the game: sets current app, item 0, mode 1) → state 4 | 0, 0 | init + title screen | S (I: the splash shown on entering Kart Racing) |
| 0xa | menu entry type 1 → outer event 0xa (only if mode 0x3d740 == 1): state 5, msg 0xa(a1 = mode), msg 0x14, msg 0xc → state 7 | mode, 0 | init + `kart_new_game_1405ebc` (phase 0), then 0x14/0xc go to the race tick | S (I: "New game") |
| 0xd | menu entry type 4 (only when save slot 1 has data) → state 5, msg 0xa (a1 = setting 1), msg 0xd, 0x14, 0xc → state 7 | size, data | `kart_savegame_restore_1404fd8` | S (I: "Continue") |
| 9 | an instructions page (`0x01428c14`) whose entry is {1, n} | n = 0..3 | init + `kart_demo_start_140af18(n)` | S (I: "Instructions") |
| 0xb | menu entry type 12 (mode data of (app, mode, item) read first) → state 4 | size, data | init + `kart_best_show_140d234` (re-reads mode data itself) | S (I: "Top score / best results") |
| 0x11 | engine state 1 → 3, received game data | `*0x3d780`, `*0x3d77c` | `kart_gamedata_receive_140d0dc(a2)` | S (I: download of `application/x-NokiaGameData`) |
| 0x12 | `0x014253fa`, a loop over stored game-data records | u16 type, rec* | `kart_gamedata_relist_140d1b0(a2, a1)` | S |
| 3 | Back/End/abort (state 4/5/7/8 events 3, 8, 0x18; in state 4 also any key-down other than key 0x14), then the engine exits the app | 0, 0 | per flag (below) then `kart_session_free_1404a56` | S |
| 0 | timer tick (state 4: plus redraw; state 7: if 0x3d784 bits 6,7 clear, then key "changed" bits cleared) | | default path | S |
| 1 / 2 | key down / up (state 7: key array updated first; state 4: only key 0x14 → msg 1) | key | default path | S |
| 0xc, 0x10, 0x14, 0x17 | start of play (0x14 then 0xc), state-8 keys, others | | default path (race tick) | S |

Default path (S): if the state exists, `+6 == 1` → `kart_title_msg_140d7fc(msg)`; else `+7 == 1` →
`kart_best_msg_140d4fe(msg)`; else `+5 == 1` → `kart_demo_msg_140b0be(msg, a1)`; otherwise
`0x0140873c(msg, a1, a2)` (the race tick). msg 3 checks the same flags in the same order
(+6 → title end, +7 → best end, +5 → demo end, none → `kart_savegame_write_1404b8c`), then
frees. For 9, 0xa, 0xb and 0xe the second call runs only if `kart_session_init_140491e` returned 1.

Screen flow (S, names I):
1. Games → Kart Racing: msg 0xe, title (≈3.9 s or any key), `game_exit` back to the engine menu.
2. Engine menu: item 1 (text 0xfe0) and item 2 (text 0xfe1), each with "New game", "Continue"
   (if saved), level (setting 2), track option (0xfe2), instructions, best results.
3. New game → msg 0xa: phase 0 (kart selection, race code) → phases 1/2 (race, item 1 or 2,
   set by `0x01405428` from +0xd) → phases 3..9 (results/standings, race code).
4. Quit during any phase: msg 3 saves (phase-specific layout) and exits.

Flags (S): +5 demo, +6 title, +7 best-results screen, +8 custom kart loaded. +0 is the game
phase: 0 kart select, 1..2 race (item), 3..9 post-race (I: results/standings screens, owned by
the race code; 6 and 7 are distinguished in `kart_record_save_140d5e4`).

## Registration (msg 7, `kart_register_140d910`)

- S: `game_app_define(0x4b, 0xfdf, 0, 1050, flag 0)`.
- S: `game_app_set_records({1,2,3}, {3300, 2000, 1000}, 3)` (0x01509558 / 0x01509560). I: extra
  data records for downloaded content (tracks, karts), by type.
- S: `game_menu_add_item(0xfe0, 1, 1)`, mode-1 descriptor 0x01509938; `game_menu_add_item(0xfe1, 2, 1)`,
  descriptor 0x01509948. Both descriptors: `{u32 0x10, entries 0x0003d004, count 10, u16 max mode data 0x18, u8 1, u8 3}`.
- S: `game_app_set_appdata_size(1)`.
- S: `game_menu_add_option(1, 0xfe2, 0, opt 4, 0x01509958, 1)` and `(2, 0xfe2, 0, opt 5, 0x01509960, 1)`;
  default entries {0, 0xfe3} and {0, 0xfe4}. Downloaded tracks are appended at run time as
  {string index, id | 0x8000}. The option value lands in setting 4/5 (engine `0x014265b8`).
- S: the 10 instruction entries (RAM 0x3d004, initialised from 0x015365dc), used by `0x01428c14`:
  `{0,0xfe5} {0,0xfe6} {1,0} {0,0xfe7} {1,1} {0,0xfe8} {1,2} {0,0xfe9} {1,3} {0,0xfea}`: text page,
  then demo n (msg 9, a1 = n), alternately. The same list serves both items.

## Menus and options

- S: settings Kart reads (`game_setting_get`, kind-3 record (app, mode, item)): key 1 = mode
  (engine menu types 7..9), key 2 = a number picked in the engine's spin box (`0x0142ada2`,
  value `+0x7c` ≤ `+0x7b`) → state+0xe, key 3 = item id (engine type 6) → +0xd, key 4 / 5 = the
  item's track option → +0xf/+0x10.
- I: item 1 (0xfe0) is a 4-race championship: 6 karts, 3 laps, the 4 built-in tracks in order
  (+4 = race index; points 10/6/4/3/2/1 in `0x01409bea`, multiplied by a level factor from
  +0xe). Track variant +4 > 3 → a random one of the four.
- I: item 2 (0xfe1) is a one-lap, 4-kart event on 0x015097d4 with rules `*0x3cc5c` = {0, 0,
  20000, 2000, 0} (I: a 20 s limit with 2 s extensions) and level forced to 2. A downloaded item-2
  track carries its own karts/level/laps/rules and a flag (+0x83) choosing time (lower is better)
  or score (higher is better) results.
- I: key 2 is a difficulty level. Its range is not established (descriptor bytes +0xe = 1,
  +0xf = 3 may be min and max).

## Title / intro (msg 0xe)

S: period 300 ms. Flag at (7,2). Each tick n = 1..8 moves "KART" to `0x01508f54[n]` =
(-91,10) (-74,10) (-60,10) (-43,10) (-28,10) (-12,10) (5,10) (20,10) and "RACING" to
`0x01508f78[n]` = (84,25) (70,25) (53,25) (38,25) (22,25) (5,25) (-10,25) (-27,25); tick 9 sets
1500 ms; tick 10 ends. msg 1 (key 0x14) ends at once; any other key ends it through msg 3.
Ending = delete, state+6 = 0, free, `game_exit`. No sound here.

## Instructions (msg 9, demos 0..3)

S: `*0x3d0c0` (0x2c bytes): +0 frame, +4 last frame, +8 s16 scroll, +0xa demo, +0xc u16 speed,
+0xe/+0xf/+0x10/+0x11 HUD params, +0x14 u32 time, +0x18 keypad sprite, +0x1c key marker,
+0x20 HUD "/" sprite, +0x24 backdrop sprite, +0x28 HUD blank rect.

| demo | frames | speed | +0xe | +0xf | +0x10 | +0x11 | time | Frame function |
|---|---|---|---|---|---|---|---|---|
| 0 | 0x55 | 0x300 | 1 | 2 | 0 | 0 | 100000 | b2c0 |
| 1 | 0x19 | 0x300 | 1 | 1 | 0 | 0 | 5000 | b648 |
| 2 | 0x48 | 0x300 | 3 | 1 | 1 | 1 | 10000 | b774 |
| 3 | 0x28 | 0 | 3 | 2 | 1 | 1 | 15000 | c0fc |

S: each tick redraws the straight road (`kart_demo_road_140c19c`), the HUD
(`kart_demo_hud_140c2ac`: bar 0x01504fd0 at (0,0); position digit `0x01513468 + p1*0x18` at
(0xd,3) or a blank rect at (2,1); icon 0x01504fe8 at (0x16,2) if p3; icon 0x01505000 at (0x23,2)
if p4; time via `0x0140808c` at (0x30,2); lap "p2/3": digit at (0x55,3), 0x01504f40 at (0x59,3),
digit 3 at (0x5b,3)), then the demo's script: the player's kart (body + driver sprites, normal
or mirrored) at frame-dependent positions, plus a keypad picture 0x0151376c (21x24) with a
pressed-key marker 0x01513784 (5x4).
- demo 0: keypad at (0x46,0x1e); marker on key 4 (frames 2..15, kart drifting left), key 5
  (17..30), key 9 (31..40, speed -0x3e), key 6 (48..59, speed +0x44); frames 0x41..0x44 show the
  four sizes of 0x01504460.. with fill patterns 0x01509568.
- demo 1: kart only; a small object (0x01504e08/20/38) approaches (frames 2..15); +0x10 blinks.
- demo 2: overtaking scene with opponents (0x01504640.., 0x01504760.., 0x01504970..); keypad at
  (1,0x1e).
- demo 3: no motion; the HUD elements blink in turn (+0xe, +0x10, +0x11, time 50000, +0xf).
I: the demos teach steering, items/boost and the HUD. Which key does what must come from the
race code; the marker positions here are exact.

## Setup of a race

S: msg 0xa → `kart_session_init_140491e` then `kart_new_game_1405ebc` (phase 0, `*0x3cc48`
= 3 zero bytes, state+1 = 7, custom kart). The race code then calls `0x01405428` (not in this
slice): `*0x3cc50` = 12 bytes {.., +9 = 6, +10 = 0}, phase = +0xd (1 or 2), track load,
race scene, `*0x3cc68[i]` = n - i, `*0x3cc6c` = 0, `0x01408dce(n, ..)`, start objects.

## Pause

S: no pause message or flag exists in this slice. The engine's pause, if any, is the state
4/5/7 events; msg 3 (quit) saves the game, and "Continue" restores it.

## Results / standings / best results (msg 0xb)

S: period 50 ms; counter `*0x3d068`. Scene, recreated every tick: medal 0x01513598 at (9,2) and
(0x4b,2); backdrop 0x01504c40 (120x20) at (0,0x14); kart 0x01505060 (18x16) at
((n-5)*2, 0x18), n reset to 0 when x > 0x5f. Item 1, or item 2 with no custom track / score
kind: best (`*0x3d06c`) as a number (`0x01408394`) at (0x26,4); if the last result's track flag
(+4) equals +0xf, the last result at (0x26,0x2e). Item 2 with a custom time-kind track: times
(`0x0140808c`) at (0x18,4) and (0x18,0x2e). Key 0x14 does nothing; other keys / Back → msg 3.
The standings screens after a race are race code (phases 3..9).

## Saved data (exact layouts)

1. **Save game** (kind 1, ≤ 1050 bytes, written on msg 3 while racing; S). Header = the 0x18-byte
   state. n = state+1, m = `*0x3cc50`+9, k = `*0x3cc50`+10.
   - phase 0: header + 3 bytes `*0x3cc48` (0x1b bytes).
   - phase 1..2: header; +0x18 12 bytes `*0x3cc50`; n bytes `*0x3cc68`; 2n bytes `*0x3cc6c`;
     n bytes `*0x3cc70`; (n + m) records of 0x44 bytes (`*0x3cc44`) each followed by 2 bytes:
     the list index of the track objects at record+0x2c and +0x30 (0xff = none); then k
     0x14-byte track objects whose u16 type == 99 (k counts down while saving). Size
     0x24 + 0x4a·n + 0x46·m + 0x14·k.
   - phase 3..9: header; 2 bytes `*0x3cc4c`; n; 2n; n bytes as above; n x 0x44 records.
     Size 0x1a + 0x48·n.
2. **App data** (kind 7, 1 byte; S): default 0x78 (written at first run), copied to state+0xc.
   I: a lock mask over the 8 kart choices (bit set = locked, `0x0140853c` shows
   `kart_portrait_locked_1504610` for it; bit 7 = the downloaded kart); the race code
   (`0x0140873c` near kart.c line 4006) writes it back, so racing unlocks karts.
3. **Mode data** (kind 6, per (mode, item), 0x18 bytes; S):

   | Off | Size | Meaning |
   |---|---|---|
   | 0 | u32 | last result |
   | 4 | u8 | +0xf (custom track?) of the last result |
   | 5 | u8 | kind: 1 = time (lower better), 0 = score (I) |
   | 8 | u32 | `game_rand()` at creation (I: an id for score sending) |
   | 0xc | u32 | best on the built-in track: maximum |
   | 0x10 | u32 | best on the custom track: phase 7 → maximum, phase 6 → minimum (0 = none) |
   | 0x14 | u8 | 1 = initialised |
4. **Settings** keys 1..5 as above (written by the engine).
5. **Game data** (kind 5, key = type 1/2/3; I: downloaded). Format (S, `kart_gd_parse_140cfa0`):
   u8 name length + UCS-2 name; u24 id (BE); u8 version (must be 0); u8 type. Type 3 (karts):
   u8 count (≤ 3) of {u8 n, n halfwords, 0x370 bytes of bitmaps, u16 four 3-bit stats}. Types
   1/2: four sprite sets (u8 count + count x 0xe8 / 0x110 / 0xf0 / 0x88 bytes), u8 count (≤ 4)
   of {u8 h, data w=0x14}, backdrop {u8 w, u8 h, data}, then 4 (type 1) or 1 (type 2) tracks
   {u8 name length, name, u8 backdrop, u8 nseg, nseg x {u8, u8}, u8 nobj, nobj x 5 bytes}, and
   for type 2 an 8-byte rules block (karts-1, level, laps, kind flag, then u8, u16, u16, u8).

## Text ids

S: 0xfdf game name; 0xfe0 item 1; 0xfe1 item 2; 0xfe2 option name (both items); 0xfe3 item-1
default option entry; 0xfe4 item-2 default; 0xfe5..0xfea six instruction pages. No text is
drawn by Kart itself; all text goes through the engine's menus. I: 0xfe2 = "Track" and
0xfe3/0xfe4 = the built-in track names. Not established: the strings themselves. The PPM text
is compressed (the plain UTF-16 hits for "Kart" at 0x015cd668 sit in compressed records);
`engine_rom_text_142b4f0` does the id → PPM mapping, not followed.

## State struct and allocation

S: `*0x3cc54`, 0x18 bytes, calloc'd by `kart_session_init_140491e` (msg 9/0xa/0xb/0xe) or
malloc'd + copied from the save by `kart_savegame_restore_1404fd8`; freed by
`kart_session_free_1404a56`. Engine RAM layout of the Kart globals: 0x3cc3c..0x3cc74 pointers,
0x3d004 instruction list, 0x3d068.. best-screen, 0x3d090 track table (4 pointers), 0x3d0a0..
title, 0x3d0b0 custom stats, 0x3d0b8 parsed name, 0x3d0bc custom kart id (init -1), 0x3d0c0
demo, 0x3cffc deferred list.

### State fields (shell)

Base pointer `*0x3cc54` unless stated.

| Off | Size | Meaning | Writers / readers | S/I |
|---|---|---|---|---|
| 0 | u8 | game phase: 0 select, 1/2 race (= item), 3..9 post-race | w: 491e, 5428, 873c; r: 4a56, 4b8c, 4fd8, 7b84, 873c, 9fb0, a468 | S (names I) |
| 1 | u8 | number of karts n (7 in select, 6 item 1, 4 item 2, data+1) | w: 491e, 5ebc, c94c, cbfc; r: many race fns | S |
| 2 | u8 | player's kart index | w: 491e, 8dce; r: race | I |
| 3 | u8 | ? (race) | w: 491e; r: 7620, 873c | S |
| 4 | u8 | race number in the cup / track variant (>3 random) | w: 491e, 9bea; r: 873c, 9bea, c94c, cbfc | S |
| 5 | u8 | demo flag | w: af18; r: handler | S |
| 6 | u8 | title flag | w: d798, d83e; r: handler | S |
| 7 | u8 | best-results flag | w: d234, d6a8; r: handler, 808c, 8394 | S |
| 8 | u8 | custom kart loaded | w: 5b68, 5e82; r: 4a56, 4fd8, 7620 | S |
| 0xa | u16 | ? (race) | w: 491e, 5428, 873c; r: 6828, 7620, 7a60, 873c | S |
| 0xc | u8 | app data byte (kart lock mask) | w: 491e; r: 7620, 853c, 873c | S (meaning I) |
| 0xd | u8 | item id (setting 3): 1 or 2 | w: 491e; r: 5428, 7e08, c94c, cbfc, d234, d2fa | S |
| 0xe | u8 | level (setting 2), item 2 forced/loaded | w: 491e, c94c, cbfc; r: 9bea, aa9c, ad78 | S (I: level) |
| 0xf | u8 | custom track selected (setting 4/5 ≠ 0) | w: 491e; r: 4fd8, 5428, d234, d2fa, d5e4 | S |
| 0x10 | u32 | setting 4/5 value: game-data id | 0x8000 | w: 491e; r: c94c | S |
| 0x14 | u8 | ? (race) | w: 491e, 873c; r: 873c | S |
| 0x15 | u8 | ? cleared on init/restore | w: 491e, 4fd8, 873c | S |

Other shell-owned structures: track `*0x3cc40` (12 B: +0 nseg, +1 nobj, +2 laps, +3 backdrop
(bit 7 custom), +4 segments, +8 object list); `*0x3cc5c` item-2 rules (0x10 B); `*0x3cc48`
phase-0 3 bytes; `*0x3cc4c` post-race 2 bytes (+1 a kart bitmask set in `0x01409bea`);
`*0x3cc50` race 12 bytes; `*0x3cc68` n bytes standings; `*0x3cc6c` n u16 points; `*0x3cc70`
n bytes; `*0x3cc44` (n+m) x 0x44 kart records (+0x15 finishing place, +0x2c/+0x30 track-object
pointers).

## Open questions

1. The physical keys behind key ids 0x14 etc. (only key 0x14 reaches Kart in engine state 4).
2. The range of setting 2 (level) and what the engine's spin box offers for Kart.
3. The strings for 0xfdf..0xfea (PPM text compression not followed). Real-phone menu names of
   items 1 and 2 are inferred (championship / single timed event).
4. Phases 3..9 meaning (race code): which are results, standings, cup end, and why 6 vs 7
   decide time vs score in `kart_record_save_140d5e4`.
5. Demo 2's marker position (0, 0x20) next to a keypad at (1, 0x1e) does not sit on a key; check
   against a render.
6. The tick period during demos (no `game_set_period` call; probably the engine's 100 ms from
   `engine_session_reset_1425584`).
7. state+3, +0xa, +0x14, +0x15 (race code).
