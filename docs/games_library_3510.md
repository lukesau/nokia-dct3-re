# The 3510's shared game library

The library all five built-in games call (0x0142c616..0x0142edd4) and the
downloadable-games engine layer under it. Names are in `ghidra/symbols/3510.csv`;
the games themselves are in `games_survey_3510.md`.

Image `roms/3510-nhm8-v502/flash.bin`, big-endian Thumb, base 0x01000000. Each row is marked
**S** (static: read directly from code or data) or **I** (inferred). "Callers" counts BL sites in
the five games (Kart 0x01404000.., SI 0x0140e000.., Bumper 0x01416700.., Link5 0x0141ce00..,
D2M 0x01422a00..~0x014247dc).

## Where the library begins and ends

- S: the game library is 0x0142c616..0x0142edd3 (and `0x0142c58c`, see Bitmaps). From
  0x0142edd4 to 0x01430000 the code is WAP session code: its assertion strings are
  `wsp_ses.c` (0x0142f14c, 0x0142f638, 0x0142fa30), and its only callers are in
  0x0143xxxx (WSP), so no game calls it. It is listed in the CSV as `wsp_ses_unknown_*`.
- S: below the library is the downloadable-games engine (`engine_*_isa.c`). It starts near
  0x014247dc: 0x01422a00..0x014247dc is called only from D2M (D2M's code reaches that far), and
  0x014247dc and above are called only from the engine.
- S: the games call nothing outside the library except the ARM runtime divides
  (0x012fb028 signed, 0x012fb0d8 unsigned, 160 sites), memcpy 0x0148af8e (207 sites),
  `engine_tone_stop_all_1428d48` (D2M, once) and `game_bitmap_draw_line_142c58c` (Bumper, once).
- S: the library functions with no BL caller and no stored pointer (dead in this firmware) are
  c616, d442, d67e, d6c2, d98a, da82, dc08, dc8a, df4e, e2b4, e328, e894, e914, e9ea, ea14,
  ec98, eca0, ed5a, ed8e.

## Conventions used by the library

- S: a point is 4 bytes `{s16 x, s16 y}` passed **by pointer** and always copied with memcpy,
  because it may be unaligned. Sizes are packed the same way, `{w, h}`.
- S: the screen is 96 x 65 (`0x0142a814` returns 0x60 and `0x0142a818` returns 0x41).
- S: a bitmap descriptor is 0x18 bytes: `+0 s16 w, +2 s16 h, +4 u32 depth (1 or 2; c6a2 picks
  the 1-bpp or 2-bpp path from it), +8 data, +0xc second plane/mask (nullable), +0x10, +0x14`.
  The last three words go to the GDI blitter unchanged. I: +0xc is a mask or transparency plane.
  Frame arrays are contiguous 0x18-byte descriptors (the renderer indexes `frames + frame*0x18`).
- S: text ids from 4000 (0xfa0) up are ROM (PPM) texts (`engine_rom_text_142b4f0`); ids below
  4000 index strings that the game added at run time (`game_app_add_string_142d814`). 4000 is
  also the "failed" return value.
- S: almost every function returns 1 on success and 0 on failure.

## Memory

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142dd46 | game_malloc | `void* (u32 n)` | → engine_malloc 0x0142ba80 → 0x012ef746(n, "engine_services_isa.c", 0xf6) | S | heap allocator |
| 0x0142dd4e | game_calloc | `void* (n, size)` | 0x012ef746(n*size) then memset 0 | S | heap |
| 0x0142dd56 | game_realloc | `void* (p, new, old)` | allocates `new`, copies min(new, old), frees p (takes the **old size** as its 3rd argument) | S | heap |
| 0x0142dd5e | game_free | `void (p)` | 0x012efa34(p, file, line) | S | heap |
| 0x0142dd66 | game_memcpy | `(dst, src, n)` | → 0x0148af8e | S | memcpy |
| 0x0142dd6e | game_memset | `(dst, v, n)` | → 0x0148b424 | S | memset |

## App and menu registration (run once per game when the Games menu is built)

The engine keeps an app table: `*0x3d704` is an array of 0x40-byte app records, `*(u16*)0x3d708`
is the count, `0x3d741` is the current app index, `0x3d740` the current mode (1..3) and `0x3d742`
the current item. `engine_app_new_1425b8e` appends a zeroed record. The calls below write into
the **last** record and only when `engine_get_state_142817e() == 2` (S). Each game calls
d174, d1d0, d260, d3cc and d538 once each, in that order, at registration (S, e.g. Bumper
0x0141a0ec..0x0141a16c, Kart 0x0140d8a0..0x0140d952). d814 + d706 run later, from the code
that handles stored game data (Bumper 0x0141ae26/0x0141ae38, after ebe4).

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142d174 | game_app_define | `(id, name_text, unused, u16 save_size, u8 flag)` | app+0 = id (0x30 Bumper, 0x3b D2M, 0x3d Link5, 0x43 SI, 0x4b Kart), +8 = name text (Bumper 0xfd6, Kart 0xfdf), +0x38 = size of the save-game record (Bumper 250, Kart 1050; de30 checks against it), +0x3c = flag | S (meaning of +8 as the name: I) | return 1, record id |
| 0x0142d1d0 | game_app_set_records | `(u16 ids[], u16 sizes[], n)` | copies n `{id, size}` pairs to app+0x20, count to +0x3a. The engine (0x014252ea) reserves one record of each size: Kart {1:3300, 2:2000, 3:1000}, Bumper {1:2800} | S (I: per-game extra data records) | return 1 |
| 0x0142d260 | game_menu_add_item | `(text, item_id, u32 p3)` | appends a 0x20-byte item {+0 id, +4 text, +0x1c p3} to app+0xc, count byte app+0x3d; refuses duplicate ids | S (I: a Games-menu entry) | return 1 |
| 0x0142d3cc | game_menu_item_set_mode1 | `(item_id, desc*)` | item+8 = desc; desc = {+0 ?, +4 entries, +8 count, +0xc u16 max data size}, read by de6c and the engine for mode 1 | S | return 1 |
| 0x0142d442 | game_menu_item_set_mode2 | `(item_id, desc*)` | item+0xc = desc (mode 2); not called | S | — |
| 0x0142d538 | game_menu_add_option | `(item_id, text, p3, opt_id, opts*, n)` | adds a 0x24-byte sub-item {opt_id, text, p3, static option table `opts` of n entries} to the item | S (I: a setting such as a level list) | return 1 |
| 0x0142d706 | game_menu_option_append | `(app_id, item_id, opt_id, {a,b}*)` | appends an 8-byte entry to the sub-item's run-time option list, then rebuilds menus (`engine_menus_rebuild_1426996`) | S | return 1 |
| 0x0142d814 | game_app_add_string | `u16 (app_id, wchar_t* s)` | copies a UCS-2 string into app+0x14 and returns its text index (app+0x34 counts, base +0x30), 4000 on failure | S | return a small index |
| 0x0142da82 / dc08 | game_menu_option_remove / game_app_remove_string | | the inverses of d706 / d814; not called | S | — |
| 0x0142d67e / d6c2 / d98a / dc8a | game_app_set_text_table / set_blob_table / add_blob / remove_blob | | static string table (+0x10) and 16-byte blob table (+0x18/+0x1c); not called | S | — |
| 0x0142dcf6 | game_app_set_appdata_size | `(u32 n)` | app+0x2c = n, the size limit of e260 (Kart only, n = 1) | S | return 1 |

## Scene objects (drawing)

All drawing is retained-mode. The game builds a tree of objects under a root, and the engine
redraws the whole tree (`engine_render_scene_1428808`, depth first, children in list order, so
later siblings are drawn on top) whenever the redraw flag is set (`game_redraw_142dfc8`). There
are no immediate-mode draw calls. Objects come from fixed pools (`engine_obj_pools_init_14254d2`:
blocks of 10 sprites x 0x1c bytes, 10 shapes x 0x2c bytes, 3 groups x 0x24 bytes, chained
when a block is full).

Common header (S): `+0 u16 type, +2 u16 flags, +4 parent, +8 next sibling, +0xc previous
sibling`. Containers (root, type 2, type 3) also have `+0x10 child count, +0x14 first child,
+0x18 last child`. Type 2 is a group or clip window, 4 a sprite, 6 a line and 7 a rectangle. No
library function creates type 3, 5 or 8 (5 is only the shape pool's default before the type is
overwritten). The root is the RAM struct at **0x0003d6e4** (`+0 count, +4 first child, +8 last
child, +0xc u16 width, +0xe u16 height`).

Flags (S, `engine_gdi_mode_142a89e`): `flags & 0xf000` of 0x1000 → GDI mode 1, 0x2000 → mode 2,
anything else → not drawn. Bit 2 → mode 4, bit 0 → `| 0x10`. Games use 0 (hidden), 0x1000
(normal), 0x1004 and 0x2000. I: mode 1 draws black, 2 white, 4 XOR, and 0x10 is transparent.

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142edcc | game_root | `obj* ()` | returns 0x0003d6e4 | S | return the root address (231 calls) |
| 0x0142edc4 | game_screen_width | `int ()` | 96 | S | return 96 |
| 0x0142edbc | game_screen_height | `int ()` | 65 | S | return 65 |
| 0x0142eaa4 | game_sprite_create | `obj* (parent, u16 flags, pt* pos, bmp* frames, u16 nframes [stack])` | type 4: +0x10 frames, +0x14 pos, +0x18 nframes, +0x1a frame = 0; appended as the parent's last child. Returns 0 if parent is not a container | S | yes: object model (194 calls) |
| 0x0142eb1c | game_sprite_get_frame | `(spr, u16* out)` | out = +0x1a | S | yes |
| 0x0142eb42 | game_sprite_set_frame | `(spr, n)` | +0x1a = n if n < nframes | S | yes |
| 0x0142eb66 | game_sprite_step_frame | `(spr, dir)` | dir == 1: next, wrapping to 0; otherwise previous, wrapping | S | yes |
| 0x0142ebaa | game_sprite_set_frames | `(spr, bmp* frames, n)` | replaces the frame array, frame = 0 | S | yes |
| 0x0142ecd4 | game_group_create | `obj* (parent, flags, pt* pos, u16 w, u16 h [stack])` | type 2 container, pos +0x1c, size +0x20/+0x22. The renderer clips children to it | S | yes |
| 0x0142ed5a / ed8e | game_group_get_size / set_size | `(g, s16* w, s16* h)` / `(g, w, h)` | +0x20/+0x22; not called | S | — |
| 0x0142e798 | game_line_create | `obj* (parent, flags, pt* p1, pt* p2, a5, a6, a7, s16 style)` | type 6: p1 +0x18, p2 +0x1c, a5 → +0x10, a6 → +0x28, a7 → +0x14, style (clamped to 255) → +0x24. Drawn by `engine_gdi_line_142a438` → 0x0126a69c | S (I: the meaning of +0x10/+0x14/+0x28/+0x24, perhaps pattern and width) | yes |
| 0x0142e84c / e8be | game_line_get_points / set_points | `(l, pt* p1, pt* p2)` | +0x18/+0x1c | S | yes |
| 0x0142e894 / e914 | game_line_get_style / set_style | | +0x24, ≤ 255; not called | S | — |
| 0x0142e948 | game_rect_create | `obj* (parent, flags, pt* pos, u16 w, u16 h, a6, a7, a8, s16 style)` | type 7: pos +0x18, w/h +0x1c/+0x1e, style +0x24. The renderer uses 0x0126a2dc when style == 0, else 0x0126a254 | S (I: outline vs fill or rounded) | yes |
| 0x0142ea14 / ea76 | game_rect_get_size / set_size | `(r, s16* w, s16* h)` / `(r, w, h)` | +0x1c/+0x1e (ea76: Kart, 2 calls) | S | yes |
| 0x0142e9ea | game_rect_get_style | | +0x24; not called | S | — |
| 0x0142e4e4 | game_obj_delete | `int (obj)` | recursively deletes the children of a container, unlinks from the parent, returns the object to its pool | S | yes (151 calls) |
| 0x0142e54c / e572 | game_obj_get_flags / set_flags | `(obj, u16* out)` / `(obj, u16 f)` | +2 (show/hide/draw mode); refuses the root | S | yes (e572: 71) |
| 0x0142e590 | game_obj_get_pos | `(obj, pt* out)` | position at +0x1c (type 2), +0x38 (3), +0x14 (4), +0x18 (5..8) | S | yes (96, mostly SI) |
| 0x0142e5e6 | game_obj_set_pos | `(obj, pt* pos)` | the same offsets | S | yes (56) |
| 0x0142e638 | game_obj_move | `(obj, s16 dx, s16 dy)` | adds to the position | S | yes (40) |
| 0x0142e6aa | game_obj_reorder | `(obj, new_parent, after)` | moves obj after sibling `after` (0 = first, which is drawn first, so at the back); reparents when new_parent differs | S | z-order |
| 0x0142e764 | game_obj_last_child | `obj* (container)` | +0x18; used as `reorder(o, 0, last_child(root))` to bring o to the front | S | yes |
| 0x0142dfc8 | game_redraw | `()` | sets bit 1 (0x02 in byte 0x3d713) of the request word 0x3d710. After the handler returns, the engine runs 0x01428ac0 (msg to the display task), renders the tree, then 0x01428ac8 (msg 0x4000, flush) | S | **render the scene now** (33 calls) |

## Off-screen bitmaps

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142c6a2 | game_bitmap_blit_scaled | `int (bmp* dst, bmp* src, a3, pt* dpos, {w,h} dsize, pt* spos, {w,h} ssize, a8, pt* a9, u32 xform)` | draws src into dst's pixel buffer through the GDI blitter (`engine_gdi_blit_142a26c` → 0x01267df8). When ssize ≠ dsize or xform ≠ 0 it first makes a temporary copy: 1 bpp via ca7e, 2 bpp via cd48 (xform bit 1 transposes or rotates, bit 0 mirrors, then nearest-neighbour scaling). A source offset goes through d072 | S (I: the exact argument roles) | yes if games draw generated bitmaps (Kart 4, SI 1, Bumper 13) |
| 0x0142ca7e / cd48 | game_bitmap_scale_1bpp / _2bpp | `(src, dst, w, h, {sw,sh}, xform)` | the helpers above | S | none (internal) |
| 0x0142d072 | game_bitmap_extract | `(dst, bmp*, pt* off, w, h)` | copies a sub-rectangle at a bit offset | S | none (internal) |
| 0x0142c616 | game_bitmap_draw_rect | `(bmp*, ?, pt* pos, pt* size, a5, style, a7, a8, flags)` | `engine_gdi_rect_142a5b4` into a bitmap; not called | S | — |
| 0x0142c58c | game_bitmap_draw_line | `(bmp*, ?, pt* p1, pt* p2, a5, a6, a7, flags)` | `engine_gdi_line_142a438` into a bitmap (below the library start; Bumper 0x0141b6aa) | S | yes (1 call) |

## Timing and frame control

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142dd36 | game_set_period | `(u32 ms)` | `*0x3d70c = ms`, sets bit 2 of 0x3d710. The engine then calls `engine_set_period_1428aa0` → `engine_timer_start_142b98c` (timer messages 0x91 stop, 0x95 start(ms), 0x93 via 0x012c79ca). Values passed: 50, 66, 200, 210, 230, 300, 400, 700, 800, 1500, 2000, 3000 | S (I: the unit is ms, and each expiry becomes a tick message to the game, as on the 3410) | **tick timer** (27 calls) |
| 0x0142dd30 | game_get_period | `u32 ()` | returns `*0x3d70c` | S | return the last period set |
| 0x0142dfbc | game_exit | `()` | sets bit 0 of 0x3d710. The engine then runs `engine_app_exit_1428488`: vibrator off, stop all tones, state 1, rebuild menus, free the scene. The engine also calls it itself after message 3 | S (I: this is "leave the game") | **end of run** (31 calls) |

## Keys

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142dd76 | game_key_state | `u8 (key)` | returns `0x3d714[key]` for key < 26, else 0. The engine writes the array (0x01427f9e/0x01428084): event 1 → `(s & 0xf8) \| 6`, event 2 → `\| 5`; every tick clears bit 2 of all 26 entries. Games test bit 1 (`lsrs #2` carry) | S (I: bit 1 = held, bit 0 = up, bit 2 = changed this tick). Key ids used: 0xd, 0xf, 0x11, 0x13, 0x14, 0x15 (the mapping to physical keys is not established) | **key input** (17: Kart 12, SI 1, Bumper 4) |
| 0x0142e4ac | game_set_key_layout | `int (n ≤ 4)` | clears the 26 key states (`engine_keys_clear_14255d0`), then `engine_set_cover_layout_142bd28(cover, n)` with cover = feature byte 3 == 1 (0x3d4f0 = cover, 0x3d4f1 = layout). The layout only feeds `engine_key_screen_pos_142bd4c` (key → on-screen position for the keypad help) | S | clear the key states; return 1 (14 calls) |
| 0x0142e2b4 | game_keypad_help_show | `(x, y, show)` | (once) a sprite of the cover-specific phone picture (table 0x01513084 + cover*0x18) at (x, y). With show: draws a marker (0x015130c0 + cover*0x18) on every key set in mask 0x3d738 (e38c). Otherwise hides it. Not called | S | — |
| 0x0142e328 | game_keypad_help_mark | `(key, on)` | sets or clears key bit `key` in 0x3d738, rebuilds the help; not called | S | — |
| 0x0142e38c | game_keypad_help_build | `()` | the helper behind e2b4/e328 | S | — |

## Sound and vibrator

Tone ids are 4000..4024 (`engine_tone_play_id_142bfd4` maps id → PPM tone through the u16 table
at 0x0150ff48 + 2*id). Each call first checks a feature byte (`engine_feature_on_1428b7c`,
array 0x3d78c: [0] sound, [2] vibrator; filled from engine settings by 0x01428b56).

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142df26 | game_sound | `bool (tone_id)` | plays once: 0x0142bffc(ppm_tone, 0x10, 0, 0) → 0x0127257c + 0x012c399a(0x1f, …). Ids seen: 0xfa2..0xfb3 (effects) | S | record (sound) (33 calls) |
| 0x0142df3a | game_sound_loop | `bool (tone_id)` | the same with repeat (0xff instead of 1). Each game calls it once with its own background tune: Bumper 0xfb4, D2M 0xfb5, Link5 0xfb6, SI 0xfb7, Kart 0xfb8, matching the PPM's GameBG order | S | record |
| 0x0142df60 | game_sound_stop | `(tone_id)` | 0x0142c07a → 0x01272632 (Kart, 0xfb0) | S | record |
| 0x0142df68 | game_sound_play_data | `bool (obj*)` | if obj+2 == 5: plays the buffer at obj+4, length +10 (0x012c804c, 0x01272678); D2M only | S (I: D2M's composed tune) | record |
| 0x0142df4e | game_sound_available | `bool ()` | always 1; not called | S | — |
| 0x0142df7a | game_vibrator | `(u8 on)` | if feature [2]: 0x0142ba26 → message {0, 0xc, on} 0x1c via 0x012c399a. SI and Bumper pass 0/1 | S | record (vibra) |
| 0x01428d48 | engine_tone_stop_all | `()` | stops any tone (D2M calls it directly) | S | record |

## Random numbers

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142de20 | game_srand | `()` | seed `*0x3d6dc` = 0x012fae6e() (a firmware time or tick value) | S (I: time) | seed deterministically |
| 0x0142de28 | game_rand | `u16 ()` | `s = s*0x343fd + 0x269ec3; return (s & 0x7fffffff) >> 16` (the MSVC LCG) | S | emulate exactly (43 calls) |
| 0x0142e22a | game_ipow | `int (base, exp)` | base^exp recursively (exp < 0 → 0); used for decimal digits | S | none (pure) |

## Saved data and settings

Everything persistent goes through engine records: `engine_rec_find_142788e(key)` finds a
`{u16 file_id, u16 length}` slot from a key `{kind, app, …}`. `engine_rec_read_1427cb6` and
`engine_rec_write_1427cda` move whole records to and from PMM group 0xbf (file ids < 0x20)
through 0x012d53a4 (read) and 0x012d50d6 (write). Kinds (S): 1 save game (app, slot),
2 settings (app), 3 item settings (app, item, mode), 4 global (0x1a-byte user string), 5 game
data (app, key), 6 mode data (app, mode, item), 7 app data (app). "Settings" records hold
`{u32 key, u32 value}` pairs.

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142de30 | game_savegame_write | `bool (u32 size, void* data)` | if 0 < size ≤ app+0x38: writes the kind-1 record of the current app | S (I: "continue game" state) | **persistent store** (5 calls, once per game) |
| 0x0142de5e | game_savegame_clear | `()` | sets the kind-1 record's length to 0 | S | store (13) |
| 0x0142ddac | game_app_setting_get | `bool (app_id, key, u32* out)` | only when the app's kind-1 record (slot 1) is non-empty: looks up `key` in the kind-2 pairs | S | store (7) |
| 0x0142dd84 | game_setting_get | `bool (key, u32* out)` | looks up `key` in the current app's kind-2 record, or the kind-3 record (app, mode, item) when bit 7 of 0x3d784 is clear | S | store (16) |
| 0x0142ddd8 | game_setting_set | `bool (app_id, key, value, item_id, u8 mode)` | read-modify-write of one pair (kind 2 or 3, as above) | S | store (4) |
| 0x0142de6c | game_modedata_write | `bool (u32 size, void* data)` | kind-6 record for (app, mode, item); size ≤ the u16 at +0xc of the item's mode descriptor (d3cc/d442) | S (I: a per-mode table such as top scores or times) | store (7) |
| 0x0142def2 | game_modedata_read | `bool (int nonzero, void** out)` | mallocs a buffer of the record's length and reads it into *out (the caller frees it) | S | store (11) |
| 0x0142e260 | game_appdata_write | `bool (u32 size, void* data)` | kind 7, size ≤ app+0x2c (Kart) | S | store (2) |
| 0x0142e28c | game_appdata_read | `bool (int nonzero, void** out)` | kind 7 into a malloc'd buffer | S | store (1) |
| 0x0142ebe4 | game_gamedata_store | `int (app_id, u8 key, u32 size, void* data)` | only in engine state 3: if the (app, key) kind-5 slot is empty, purges that key's menu options and strings (0x01425d68/ea4/faa), then writes the record and sets engine state 1. Each game calls it once, with fields of a message parameter struct | S (I: stores game data received by the download engine, `application/x-NokiaGameData`, e.g. a new level, which Bumper then lists with d814 + d706) | store; only on the download path |
| 0x0142ec7e | game_gamedata_read | `bool (key, sub, void** out)` | kind 5 of the current app into a malloc'd buffer (0 if `out` is null) | S | store (6) |
| 0x0142ec98 / eca0 | game_unknown | | → 0x01427b7c, and app lookup → 0x01424eca; not called | S | — |

## Score display and score sending

| Addr | Name | Signature | What it does | S/I | Stub needs |
|---|---|---|---|---|---|
| 0x0142dfec | game_score_box | `(u8 ndigits, int top, u32 value, bool no_leading_zeros)` | builds a framed number from lib objects under the root: lines (e798), corner sprites (0x01513598/0x01513604/0x0151361c) and digit sprites (10 descriptors at 0x01513634 + d*0x18, 8 px apart, from 10^i). top = 1 places it at y = 1, otherwise at the bottom (y = H - 0x13) plus e1d8. Then requests a redraw | S (I: the 3410's game_score_box counterpart) | none if the object API is emulated (7: SI 3, Bumper 2, D2M 2) |
| 0x0142e1d8 | game_score_box_icon | `obj* ()` | if product-profile flag 8 is set and the global 0x1a-byte user string is non-empty: a sprite of bitmap 0x01513568 at (6, H-6) | S (I: a "score can be sent" or Club Nokia badge) | none, given the PP flag stub |
| 0x0142df82 | game_score_send | `int (a1..a5, ...)` (varargs) | if PP flag 8 (`engine_pp_flag_142bc08(1)` → 0x0129e3b4(8)) is set: formats a UCS-2 string from the user string and the arguments (0x01427298/0x0142766c, fixed parts at 0x01427660/64/68) and queues it for `engine_scoresend_isa.c` (`0x0142c326`: state 6). Returns 1 when the flag is off | S (I: Club Nokia score code) | return 1 (3: SI, Bumper, D2M) |

## Engine to game interface (for the harness)

- S: the engine calls the current app as `apps[*0x3d741]->+4 (msg, a, b)` from
  `engine_app_send_1428124`. Its event code (0x01427ee6..0x01428122) sends messages
  0, 1, 2, 3, 0xc, 0xd, 0x10, 0x14 and 0x17, with key events setting `0x3d714` first.
  I: 0 is the timer tick (after it all key "changed" bits are cleared and a redraw is
  requested). The game handlers switch on 3, 7, 9, 10, 0xb, 0xd, 0xe, 0x11 and 0x12, so app+4 is
  probably a wrapper rather than the handler table entry itself; not established.
- S: after each message the engine reads 0x3d710: bit 0 → exit, bit 1 → redraw, bit 2 → new
  timer period. A harness can do the same: run the handler, then act on the requests.
- S: `engine_session_reset_1425584` is the state a game starts from: root count, first and
  last child = 0, `*0x3d6f0` = 96 and `*0x3d6f2` = 65 (root +0xc/+0xe), key array cleared,
  `game_set_period(100)`, keypad-help variables 0x3d734/0x3d6e0/0x3d738 = 0, 0x3d710 = 0.
  `engine_scene_reset_14255e0` deletes the whole tree under the root, then does the same.

## Firmware services the library and engine depend on (the real stub boundary)

| Group | Address | Use |
|---|---|---|
| Heap | 0x012ef746 `alloc(n, file, line)`, 0x012efa34 `free(p, file, line)` | every malloc/free |
| C runtime | 0x0148af8e memcpy, 0x0148b424 memset, 0x012fb028 / 0x012fb0d8 signed/unsigned divide (remainder in r1) | games and library |
| Strings | 0x010b9f54 wcslen, 0x010b9f9a, 0x010ba17c, 0x010b9f88, 0x012b2340 (`ui_text.c` area) | d814, score send |
| Time | 0x012fae6e | rand seed |
| Product profile | 0x0129e3b4(id, 0, &out) (`i_pp_if.c`) | flags 7/8/9: score badge and sending |
| OS messages and timers | 0x012c79ca (send/timer: 0x91/0x95/0x93 period, 0x8e, 0x90/0x94, 0x4000 flush), 0x012c399a (send to a server: 0x1f audio, 0x1c vibra), 0x012c2f38 (message alloc), 0x012c79f2, 0x012c7a62 | timer, redraw, tones, vibra |
| GDI (`pgdi_canvas…`) | 0x01267df8 blit, 0x0126b364 (canvas for screen), 0x0126a69c line, 0x0126a2dc / 0x0126a254 rectangles, 0x01268ce8 (copy, unused) | the renderer and the off-screen bitmap calls |
| Tones (`srvtone_toneobject_nrt.c`) | 0x0127257c play, 0x01272632 stop, 0x01272678 play data, 0x01272712, 0x012c804c | sound |
| PMM (`pmm_api.c`) | 0x012d53a4 read(0xbf, id, 0, len, buf), 0x012d50d6 write(0xbf, id, buf, len, 0) | all saved data |
| Assert | 0x012fb454 | key layout checks |

Two ways to draw the line (I):
1. Stub the about 60 library entry points the games actually call (the tables above with call
   counts), keeping a Python model of the scene tree, the key array, the period, tones and
   records.
2. Run the library and engine natively: initialise the pools (0x014254d2), the root at 0x3d6e4
   and the app record, and stub only the firmware services listed above. Rendering then needs
   only the four GDI calls. This keeps every object and score-box detail exact, at the cost of
   setting up the engine's RAM state.
