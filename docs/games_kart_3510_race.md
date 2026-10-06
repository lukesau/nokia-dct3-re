# Kart Racing (3510): the race slice

Part of the Kart Racing map; start at `games_kart_3510.md`, which resolves the points where the slices disagreed. Names are in `ghidra/symbols/3510.csv`.

The ARM runtime divides return the **remainder in r0 and the quotient in r1** (see `games_library_3510.md`); every formula here uses that, read from the disassembly.

Image `roms/3510-nhm8-v502/flash.bin`, big-endian Thumb, base 0x01000000. Slice: the per-message
function `kart_tick_140873c` and everything under it except the road renderer
`kart_road_draw_1406144` subtree. Every claim is marked **S** (static: read from the code or data,
checked against the disassembly where it matters) or **I** (inferred).

## Units and conventions (all S)

- Tick: one call of `kart_tick_140873c(0, …)` per engine timer message. The only
  `game_set_period` calls in the Kart range are 0x0140d282 (50 ms, in 0x0140d234), 0x0140d7be
  (300 ms) and 0x0140d826 (1500 ms). The race runs at **50 ms** (I: 0x0140d234 is the
  game-start routine; the 300/1500 ms ones are the splash). Race times add `game_get_period()`
  each tick, so they are in ms (S).
- Track: a ring of segments. Segment `s` is 4 bytes at `track->segs + 4*s`:
  `u16 length` (track units), `u8 flags`. `kart_seg_prop` 0x014060c6 (road agent's slice) decodes
  flags: prop 1 = hill class (bit 1 set → 2, else bit 0 set → 1, else 0), prop 2 = curve level
  `(flags >> 2) & 7` (0 = straight), prop 3 = curve direction `(flags >> 5) & 1`.
- Position along the track: entity `+8` u8 segment, `+0xc` s32 position inside the segment in
  **24.8 fixed point** (units × 256). Speed `+0x18` is s16 in 1/256 unit per tick, added to
  `+0xc` every tick.
- Lateral position `+0x10` s16: 0 = centre, **negative = left**, clamped to ±80 by most writers.
  Key 0x13 makes it go negative, 0xf positive (S).
- Collision boxes use "screen-ish" x = `x − width/2 + 60` and "distance to the end of the
  current segment" y = `len − (pos >> 8) − 2` (S).

## Functions

| Addr | Name | Signature | What it does | S/I |
|---|---|---|---|---|
| 0x0140873c | kart_tick_140873c | `int (msg, key, p3)` | Called by the handler 0x014047f0 for every message unless state +5/+6/+7 reroutes it. msg 0 = timer tick, msg 1 = key press (key id in `key`). Dispatches on game state `*0x3cc54+0` (0 kart select, 1/2 race, 3..8 result screens, 9 unlock). See "The tick" and "Start and finish" | S (I: msg 1 = key down, from the engine's event 1 → `(s & 0xf8) | 6`) |
| 0x01405428 | kart_race_init_1405428 | `int (u8 kart)` | malloc 12 B race struct `*0x3cc50` {+0 phase 0, +2/+4/+6 = 0, +8 = 0, +9 = 6, +10 = 0}; `*0x3cc40 = *0x3cc3c = 0`; state+0xa = 0; state = 1 if mode(+0xd) == 1, 2 if mode == 2; track load 0x0140c94c(state+0xf) (shell); 0x01405534 (shell, HUD objects); if `*0x3cc68 == 0` calloc(n,1) with `order[i] = n − i`; if `*0x3cc6c == 0` calloc(n,2) zeroed (points); `kart_racers_init(n, kart)`; 0x01405ad6 (shell) | S |
| 0x01408dce | kart_racers_init_1408dce | `int (u8 n, u8 kart)` | state+2 (player index) = 0. calloc `*0x3cc44` = (n + race+9) × 0x44. If `*0x3cc70 == 0`: kart types `types[0] = kart`, `types[1..n−1]` drawn with game_rand (see Random numbers). Racers i < n: bytes 0..3 = 0, +2 = 1 if `*0x3cc4c` exists and bit i of `(*0x3cc4c)[1]` (tie-break exclusion); pos +0x15 = order[i]; grid slot g = n − order[i]: +8 = `grid[g].seg`, +0xc = `grid[g].dist << 8`, +0x10 = `grid[g].x`; +0x16 = types[i]; stats +0x1c/+0x1e/+0x1f/+0x20 = `kart_stat(type, 0..3)`; +0x28 = 0, +0x2c = +0x30 = 0, +0x34 = 0xff, +0x21..+0x24 = 0, times = 0. Extra slots n..n+5 (missiles): +2 = 1 (inactive), stats 0x600/0x4b/0x19/3, +0x16 = 99, rest zero | S |
| 0x01409076 | kart_kart_stat_1409076 | `s16 (type, k)` | level L = `kart_type_levels[type*4 + k]` (type < 7) or `custom[k]` (`0x3d0b0`, type ≥ 7); returns s16 at `0x015098ea + 2*(L + 6k)`, i.e. level L (1..6) of stat k | S |
| 0x01409204 | kart_race_step_1409204 | `int ()` | One physics step for all entities: rubber band, AI/input decisions and collisions (loop 1), then movement, laps and ranking (loop 2), then the engine sound. See "The race step" | S |
| 0x01408dc0 | kart_next_seg_1408dc0 | `u8 (ent*, track*)` | `(ent.seg + 1) % nsegs` (compare form) | S |
| 0x014090a4 | kart_rubber_band_14090a4 | `void (i)` | Opponent stat boost, see Opponents | S |
| 0x0140990a | kart_player_input_140990a | `(i, s16 maxEff)` | Reads keys 0x14/0x15/0x13/0xf, sets the decision flags, see Input | S |
| 0x0140998a | kart_player_lateral_140998a | `void (i)` | Player sideways movement with a momentum counter +0x12, see Player physics | S |
| 0x01409a40 | kart_rank_update_1409a40 | `void (i)` | Swaps race positions when entity i has overtaken someone, see Laps/position | S |
| 0x01409efc | kart_centrifugal_1409efc | `void (i)` | Adds the curve push to +0x1a (player only), see Player physics | S |
| 0x0140a31c | kart_missile_home_140a31c | `void (i)` | Missile steering: nearest racer ahead, steer toward its x | S |
| 0x0140a468 | kart_collide_140a468 | `int (i)` | Kart-vs-kart (with lookahead for AI), then kart-vs-track-objects; picks up items; AI avoidance | S |
| 0x01409f64 | kart_box_overlap_1409f64 | `bool (ax, ay, aw, ah, {bx,by}, {bw,bh})` | inclusive AABB: `by+bh ≥ ay && by ≤ ay+ah && bx+bw ≥ ax && bx ≤ ax+aw`. The two pairs are passed on the stack, x in the first (high-address-first, BE) halfword | S |
| 0x01409fb0 | kart_hit_kart_1409fb0 | `int (i, ax_i, ay_i, j, {ax_j, ay_j})` | Contact between entity i and j, see Collisions | S |
| 0x0140a1f0 | kart_hit_object_140a1f0 | `int (i, ax, ay, type, {bx, by})` | Contact with a roadside object or a mine, see Collisions | S |
| 0x0140a2c8 | kart_ai_avoid_140a2c8 | `void (i, my_ax, other_ax, k)` | AI dodge of a kart predicted k ticks ahead, see Opponents | S |
| 0x0140a412 | kart_ai_seek_pickup_140a412 | `void (i, my_ax, box_ax)` | AI (never the player) steers toward a pickup box | S |
| 0x0140aa9c | kart_ai_weapon_140aa9c | `int (i)` | AI decides to fire its weapon | S |
| 0x0140abf6 | kart_fire_weapon_140abf6 | `int (i)` | Fire the held weapon: kind 0 spawns a homing missile entity, kind 1 drops a mine object; tone 0xfb3 | S |
| 0x0140ad78 | kart_ai_turbo_140ad78 | `int (i)` | AI decides to use its turbo | S |
| 0x0140aea6 | kart_use_turbo_140aea6 | `int (i)` | Turbo: speed = 2 × max, 5 ticks; tone 0xfb1 for the player | S |
| 0x01409aba | kart_finish_times_1409aba | `void ()` | At race end: estimated times for unfinished racers, then final positions from times | S |
| 0x01409bea | kart_cup_points_1409bea | `void ()` | Championship points after a race, grid order for the next race, standings; after race 4: tie-break setup or final multiplier | S |
| 0x01409dd0 | kart_challenge_points_1409dd0 | `void ()` | Challenge points: place points + time bonus, then order and standings | S |
| 0x0140d5e4 | kart_record_save_140d5e4 | `int (u32 value)` | Read-modify-write of the 0x18-byte mode-data record (best points / best time) | S |
| 0x0140d554 | kart_record_init_140d554 | `void (u32** rec)` | Initialises that record; stores one `game_rand()` at +8 | S |
| 0x01407620 | kart_select_draw_1407620 | `int ()` | State 0 kart-select screen: 2×2 portraits, blinking cursor, four stat bars; in sub-mode 2 the full-screen start picture | S |
| 0x014079b8 | kart_select_clear_14079b8 | `void ()` | Deletes the select/result grid objects (0x3cf24[4], 0x3cf98[4], 0x3cfa8[4][5], 0x3cea0) | S |
| 0x01407a60 | kart_start_lights_draw_1407a60 | `int ()` | Rebuilds the start-lights panel and 0..4 lamps from the tick counter | S |
| 0x01407b24 | kart_start_lights_clear_1407b24 | `int ()` | Deletes the panel 0x3cf34 and lamps 0x3cf38[4] | S |
| 0x01407b84 | kart_results_table_draw_1407b84 | `int ()` | States 3/4/6/7: 2×2 table of the racers in position order (page `(*0x3cc4c)[0]`), each with portrait, rank badge and digit, and a time (3/6) or points (4/7) | S |
| 0x01407e08 | kart_result_final_draw_1407e08 | `int ()` | States 5/8: the player's portrait, trophy if position < 4, rank badge, points (mode 1) or time (mode 2), two 96-wide rectangles | S |
| 0x0140808c | kart_time_draw_140808c | `int (u32 ms, pt* pos, slot)` | Draws a time as 6 digits `M M sep S S sep c c` (ms → s = ms/1000, m = s/60, ss = s − 60m, cs = (ms − 1000s)/10; digits m/10, m%10, ss/10, ss%10, cs/10, cs%10) into slot 0..3. Big 6×8 digits (0x01513634) when state+7 == 1, else 3×5 (0x01513468). Shared: the race HUD calls it from 0x014069a8 (road agent's subtree), and the records screen from 0x0140d450/478 | S |
| 0x01408394 | kart_points_draw_1408394 | `int (u16 v, pt* pos, slot)` | 3 digits v/100, (v%100)/10, v%10, no zero suppression | S |
| 0x0140830c / 0x014084b0 / 0x014084f4 | kart_time_clear / kart_points_clear / kart_rank_badges_clear | `void ()` | delete the time digits (0x3cf04, 0x3cf14, 0x3cea4[6][4]), points digits (0x3cf68[3][4]), rank badges (0x3cf48[4], 0x3cf58[4]) | S |
| 0x0140853c | kart_unlock_draw_140853c | `int (u8 kart)` | State 9: the kart-select grid page holding the newly unlocked kart, with its stat bars | S |

## The tick (kart_tick_140873c), msg 0

Game state `st = *0x3cc54`, race `rc = *0x3cc50`, counter `st+0xa` (u16). After any branch
that returns 1, `game_redraw()` (S).

**State 0, kart select** (S): `st+0xa += 1`; `kart_select_draw`. Sub-mode `sel = *0x3cc48`
byte 0: if sel == 1 and counter > 19 → sel = 2, counter = 0. If sel == 2 and counter > 19 →
delete the picture `*0x3ce94`, `kart_select_clear`, free `*0x3cc48`,
`kart_race_init(st+3)`. So after choosing: 20 ticks of highlight, 20 ticks of the start
picture (`*0x3d078` if set, else 0x01505048, 96×65, centred), then the race.

**States 1 and 2, racing** (S), in this order:
1. `L = len(seg[rc+8])` (camera segment, before it moves).
2. First race tick: if `st+0x15 == 0` → `game_sound_loop(0xfb8)` (GameBG Car Racing),
   `st+0x15 = 1`.
3. Camera segment wrap: if `rc+6 ≥ L` → `rc+6 −= L`, `rc+8 += 1` (0 at nsegs). Else if
   `rc+6 < 0` → `rc+8 −= 1` (nsegs − 1 below 0), `rc+6 += L` (L of the old segment).
4. If race phase `rc+0 != 0` → `kart_race_step()` (no physics during the countdown).
5. Phase 2 (finished): if `st+0xa < 60` → `st+0xa += 1`; else end of race (see Start and
   finish). Phases 0/1: if phase 1 and `st+0xa < 26` → `st+0xa += 1` (lap banner timer, I);
   `rc+6 = (player.pos − 0x300) >> 8` (`kart_camera_lag_150920e` = 0x0300: the camera is 3 units
   behind the player); if `rc+8 != player.seg` → `rc+6 += L`; `rc+2 = player.x / 2`;
   `rc+4 −= player.speed`, and if `rc+4 ≤ 0` → `rc+4 += 0x700` (I: road stripe phase).
6. `kart_road_draw(rc+2)`.
7. Phase 0 (countdown): if `st+0xa ≥ 26` → `st+0xa = 30`, phase = 1,
   `kart_start_lights_clear`. Else if `st+0xa == 0` → `game_sound(0xfb2)`; `st+0xa += 1`;
   `kart_start_lights_draw`.

**States 3, 4, 6, 7** → `kart_results_table_draw`. **5, 8** → `kart_result_final_draw`.
**State 9** (unlock): `st+0xa += 1`; at 20: clear bit `st+0x14` of `st+0xc`, write it as the
1-byte app data (`game_appdata_write(1, …)`), return; at 40: `game_savegame_clear`,
`game_exit`, 0x01404a56; otherwise `kart_unlock_draw(st+0x14)` (S).

## The tick, msg 1 (key press)

- State 0 with `sel == 0` (S): cursor `c = sel[2]` 0..3 on a 2×2 grid, page `p = sel[1]` 0..3.
  0xd: `c < 2 ? p −= 1 : c −= 2`, p wraps 255 → 3. 0x11: `c < 2 ? c += 2 : p += 1`, p wraps 4 → 0.
  0xf: if c is 0 or 2 → c += 1. 0x13: if c is 1 or 3 → c −= 1. 0x14: kart
  `k = (c + 2p) % 8`; refused if bit k of `st+0xc` (locked) or (k == 7 and `st+8 == 0`); else
  `st+3 = k`, `st+0xa = st+0xb = 0`, sel = 1, `game_set_key_layout(2)`. The grid shows kart
  `(i + 2p) % 8` at cell i. So 0xd = up, 0x11 = down, 0xf = right, 0x13 = left, 0x14 = select.
- States 1/2, only in phase 1 (S): 0x16 → `kart_fire_weapon(player)`; 0x17 →
  `kart_use_turbo(player)`.
- States 3..8 (S): 0xd → `(*0x3cc4c)[0] −= 1` if > 0; 0x11 → `= 1` if 0 (two result pages).
  Any other key: state 3 → `kart_cup_points`, `kart_time_clear`, state 4. State 4 after the
  4th race (`st+4 > 3`) with no tie-break (`(*0x3cc4c)[1] == 0`) → `kart_points_clear`,
  `kart_record_save(points[player])`, state 5. State 6 → `kart_time_clear`,
  `kart_record_save(player.+0x40)`, state 8. State 7 → `kart_points_clear`,
  `kart_record_save(points[player])`, state 8. State 5 → savegame_clear, game_exit, 0x01404a56.
  State 8 → delete the trophy and rectangles, `st+0xa = 0`, then state 9 if `st+0x14 != 0`,
  else savegame_clear + exit. State 4 otherwise (next cup race) → clear the screen, free
  `*0x3cc44`, `kart_race_init(st+3)`, free `*0x3cc4c`, phase 0, state 1.

## The race step (kart_race_step_1409204)

`E = n + rc+9` entities (n racers, then 6 missile slots). `P = st+2` (player index, always 0).
All S.

0. `dt = game_get_period()`. For i in 0..n−1: `kart_rubber_band(i)`.

**Loop 1, i = 0..E−1 (decisions):**
1. Clear flags +4 (accel), +5 (brake), +6 (right), +7 (left) and `+0x1a = 0`.
2. Missile lifetime: if `+0x24 > 0`: `+0x24 −= 1`; if it reaches 0 → `+2 = 1` (inactive), next i.
3. Skip if `+2 == 1`. `+0x22 −= 1` if > 0 (invulnerable); `+0x23 −= 1` if > 0 (turbo).
4. Spin: if `+0x21 > 0`: `−= 1`; if still > 0 → next i; if it hit 0 → `+1 = 1` and fall into 5.
5. Recentre (`+1 == 1`): if x < 0: x += 4, clamp to 0 if > 0; if x > 0: x −= 4, clamp to 0
   if < 0; next i. If x == 0: `+1 = 0`, `+0x22 = 30`, continue to 6 this tick.
6. Segment data: `nx = next seg`, `hill = prop1(seg)`, `dir = prop3(seg)`,
   `len = len(seg)`, `lv = prop2(seg)`, `dirN = prop3(nx)`, `lvN = prop2(nx)`;
   `maxEff = (s16)(kart_hill_maxspeed[hill] + max)`; `accEff = (s16)(kart_hill_drag[hill] + accel)`.
7. Decide: player and phase != 2 → `kart_player_input(i, maxEff)`. Missile (type 99) →
   `kart_missile_home(i)`, accel flag = 1, and if `lv != 0` → dir 1 sets +6, dir 0 sets +7. Otherwise (AI, and the player after finishing) → the AI rules in
   Opponents, then `kart_ai_turbo` if holding a turbo (+0x30), then `kart_ai_weapon` if
   holding a weapon (+0x2c).
8. Over-speed decay: if `speed > maxEff` and `+0x23 ≤ 0` and not a missile: `speed += drag[hill]`
   (negative), clamp ≥ 0.
9. `kart_collide(i)`.
10. Player only: `kart_centrifugal(i)`.
11. Not the player and neither +6 nor +7: drift back to the centre band:
    `x < −20 − steer` → `+0x1a = steer`, +6; `x > 20 + steer` → `+0x1a = −steer`, +7.

**Loop 2, i = 0..E−1 (movement):**
1. Skip if `+2 == 1`.
2. If `laps(+0x14) < track laps`: `+0x38 += dt`, `+0x40 += dt`.
3. If spinning (`+0x21 != 0`) or recentring (`+1 == 1`): no movement, go to 7.
4. Lateral: player and phase != 2 → `kart_player_lateral(i)`. Others: if `+0x1a < 0` and
   x > −80 → x −= steer; if `+0x1a > 0` and x < 80 → x += steer (no exact clamp: x can reach
   79 + steer).
5. Speed: brake flag → if player or `speed ≥ 102`: `speed −= brake`; then `speed = max(speed, 0)`.
   Else accel flag → `speed += accEff`, `speed = min(speed, maxEff)`. Else coast →
   `h = maxEff / 2`; if `speed > h`: `speed += drag[hill]`, `speed = max(speed, h)`.
6. `pos += speed`. If `pos >> 8 ≥ len`: `pos −= len << 8`, `seg += 1`; if `seg ≥ nsegs`:
   `laps += 1`, `seg = 0`, `+0x3c = +0x38`, `+0x38 = 0`; for the player also `st+0xa = 0`
   and, if `laps ≥ track laps`, race phase = 2. At most one segment per tick.
7. If spinning/recentring, or i < n after a move: `kart_rank_update(i)` (the spin path calls it
   for any i, see Open questions).

**Engine sound** (after both loops, player record): if not braking, `speed != 0`, `+0x23 == 0`
and `+0x21 == 0` → if `0x3d0b4[2] == 0`: `game_sound(0xfb0)`, flag = 1. Otherwise, if the
flag is set: `game_sound_stop(0xfb0)`, flag = 0.

## Input (S unless noted)

| Key id | Race meaning | Code |
|---|---|---|
| 0x14 held | accelerate: accel flag if `speed ≤ maxEff` | 0x0140991a |
| 0x15 held | brake, only when 0x14 is not held and `speed > 0` | 0x01409924 |
| 0x13 held (0xf not) | steer left: `+0x1a = −steer`, +7 | 0x0140994c |
| 0xf held (0x13 not) | steer right: `+0x1a = +steer`, +6 | 0x0140996e |
| 0x16 press | fire weapon (msg 1) | 0x01408902 |
| 0x17 press | use turbo (msg 1) | 0x01408922 |

"Held" is bit 1 of `game_key_state` (`lsrs #2` carry). Both steering keys together → neither.

Physical keys (I): the keypad-help table `0x01512ee8` (17 bytes per cover×layout,
`engine_key_screen_pos_142bd4c`; 0x80 marks a key that is shown) has an identity layout 4
(`80..8b` = ids 0..11 at positions 0..11), so position p is digit p, then `*`, `#`. Layout 0
(the default) reads `0:0x16 1:0xc 2:0xd 3:0xe 4:0x13 5:0x14 6:0xf 7:0x12 8:0x11 9:0x10 *:0x17
#:0x15`, a clockwise joystick ring on 1..9 with 5 = 0x14 (fire/select). Kart's race layout 2
marks `1:0x16 2:0x17 4:0x13 5:0xf 6:0x14 9:0x15` (left 4, right 5, gas 6, brake 9, weapon 1,
turbo 2). This only proves what the help picture shows; the firmware's key → id translation is
before `engine_app_send` and was not traced. The kart-select keys are the layout-0 ring
(2 up, 8 down, 4 left, 6 right, 5 select) if the ids are the same.

## Player physics (S)

- Stats per kart from `kart_type_levels_150991c` (u8 levels 1..6, order max speed, accel,
  brake, steer) through `kart_stat_levels`:

  | Level | 1 | 2 | 3 | 4 | 5 | 6 | (7 = boost of 6) |
  |---|---|---|---|---|---|---|---|
  | max speed `+0x1c` | 0x300 | 0x340 | 0x380 | 0x3c0 | 0x400 | 0x440 | 0x28 (!) |
  | accel `+0x1e` | 40 | 49 | 58 | 67 | 76 | 85 | 25 |
  | brake `+0x1f` | 25 | 38 | 50 | 62 | 75 | 85 | 7 |
  | steer `+0x20` | 7 | 8 | 9 | 10 | 12 | 14 | (next byte) |

  Kart types 0..6 (speed, accel, brake, steer): 0 `3 4 1 4`, 1 `3 3 4 4`, 2 `4 2 3 2`,
  3 `5 2 3 1`, 4 `2 5 4 4`, 5 `4 3 1 5`, 6 `4 5 2 2`. Type 7 = custom, levels at RAM 0x3d0b0.
  Column 7 is what the rubber band reads for a level-6 stat (it runs into the next row): no
  built-in kart has a level 6, so only a custom kart can hit it (I).
- Hill class (`kart_hill_maxspeed_15098c0` / `kart_hill_drag_15098b8`, index prop 1):
  0 → max −200, drag −38; 1 → max +100, drag −16; 2 → max +0, drag −24. I: 0 uphill, 1
  downhill, 2 flat (the road agent's horizon rows 0x1c / 0xd / 0x17 for the same index).
- Effective accel per tick = `accel + drag` (e.g. 40 − 24 = 16 on flat). Max speed 0x380 on
  flat = 3.5 units/tick = 70 units/s at 50 ms.
- Coasting (no gas, no brake) only decays to `maxEff/2`, never below.
- Braking: `speed −= brake`, floor 0. Brake key requires speed > 0 (player).
- Turbo (`kart_use_turbo`, needs a held turbo box, not spinning/boosting/recentring):
  `speed = max << 1` (raw stat, not maxEff), `+0x23 = 5`. While `+0x23 > 0` the over-speed
  decay of loop 1 is off, but coasting drag still applies every tick (accel is not set because
  speed > maxEff). After 5 ticks both apply until `speed ≤ maxEff`.
- No off-road slowdown: nothing in the slice reads x for speed. Leaving the road is only limited
  by the ±80 clamp (S, absence).
- Lateral (player, `kart_player_lateral`), momentum m = `+0x12`, s = steer:
  - `+0x1a > 0`: if m ≥ 6: if x < 80 → x = min(x + s, 80); else m += 2.
  - `+0x1a < 0`: if m ≤ −6: if x > −80 → x = max(x − s, −80); else m −= 2.
  - `+0x1a == 0` and m != 0: m > 0 → m −= 2, and if x < 80 → x += s (no clamp); m < 0 →
    m += 2, and if x > −80 → x −= s (no clamp).
  So a turn starts after 3 ticks (0→2→4→6), keeps sliding 3 ticks after release, and reversing
  from full lock takes 6 ticks. Only the sign of `+0x1a` matters, the step is always `steer`.
- Centrifugal (`kart_centrifugal`, player, after collisions): with `lv = prop2(seg) != 0`:
  `q = (u32)(speed*speed*256) / (kart_corner_speed[lv] * 0x600)` (unsigned),
  `f = ((q * kart_centrifugal_mult[lv]) & 0xffffff) >> 8`, then `f −= 1` if f != 0 (u16);
  `+0x1a += f` if dir == 0, `−= f` if dir == 1. If f > steer the player cannot hold the line
  against the curve. Tables: corner speed s16[8] = 1250, 900, 850, 800, 750, 700, 650, 600;
  multiplier u8[8] = 0, 4, 7, 11, 18, 23, 26, 28.
- Spin (`+0x21 = 10`, speed 0): 10 ticks frozen, then recentre to x = 0 at 4 per tick, then 30
  ticks invulnerable (`+0x22`). While invulnerable, hits neither spin nor push the kart.

## Opponents and AI (S unless noted)

- Count: n racers (championship: 6, set in 0x0140c94c; challenge: from its data). The player is
  index 0; opponents 1..n−1. Plus 6 missile slots (type 99) after them.
- Kart types: distinct random types for 1..n−1 on the first race of a series (see Random).
- Grid `kart_grid_15098c8` (6 entries {u8 0, u8 seg, s16 dist, s16 x}): seg 0 for all,
  dist 5, 7, 10, 12, 15, 17, x +25, −25 alternating. Slot g = n − order[i]; the first race
  has order[i] = n − i, so the player starts last at slot 0 (dist 5, x 25). Later cup races use
  the previous race's finishing order (`*0x3cc68`): the winner starts at the front.
- Decisions each tick (loop 1, step 7), using `lv`, `lvN`, `dirN`, `maxEff`, `accEff`, `len`,
  `rem = len − (pos >> 8)`, `C[l] = kart_corner_speed[l]`:
  - Brake for the next curve: if `lvN != 0`: `t = (speed − (maxEff − C[lvN]) / 2) / brake`;
    if `0 < t ≤ rem` and `steer < lv` → brake. If `lvN == 0` and `lv != 0`: if
    `speed > (maxEff − C[lv]) / 2` and `steer < lv` → brake. (The steer test uses the *current*
    level `lv`, so on a straight before a curve the AI never brakes.)
  - Accelerate if not braking, `speed < maxEff` and `speed + accEff < C[lv]`.
  - Line: in a curve (`lv != 0`): dir 1 → +6 set, aim x = +45 (`x < 45 − s` → `+0x1a = +s`,
    `x > 45 + s` → `−s`); dir 0 → +7 set, aim −45. On a straight before a curve: dirN 0 aims
    +25, dirN 1 aims −25, moving only when `t = |x − target| / s ≥ rem` and t > 0 (sets +6/+7).
    Then the centre-band rule of step 11 (|x| ≤ 20 + s).
  - `kart_collide` lookahead (k = 1..5 ticks for AI, only k = 0 for the player): a predicted
    overlap with a kart calls `kart_ai_avoid(i, my_ax, other_ax, k)`: if `other_ax ≤ 24` or
    (`other_ax < 72` and `other_ax < my_ax`) → steer right (+6, `+0x1a = +s`), and brake if
    `my_ax + k*s ≤ other_ax + 48`; else steer left, and brake if `my_ax − k*s ≥ other_ax − 24`.
    Object lookahead count is the difficulty `st+0xe` (1, 2 or 3; 0 for other values); for
    roadside objects only k = 0 is used, for pickup boxes all k: the AI steers toward boxes
    (`kart_ai_seek_pickup`: box right of it → +s unless +7, left → −s unless +6).
- Rubber band (`kart_rubber_band`, every tick for each opponent): if not boosted, ranked behind
  the player (`pos_rank > player rank`), and the player is more than 100 units ahead (counted
  within the lap: same segment → difference of `pos >> 8`; else the player's `pos >> 8` plus
  the lengths of the segments from player.seg − 1 back to the kart's segment inclusive, minus
  the kart's `pos >> 8`; laps are ignored) → `+3 = 1` and all four stats go up one level
  (`0x015098ec + 2L`, `0x015098f9 + 2L`, `0x01509905 + 2L`, `0x01509911 + 2L`). When a boosted
  kart's rank becomes better than the player's → `+3 = 0` and normal stats.
- Weapons (AI, `kart_ai_weapon`, only when holding one): difficulty 1 → hold 40 ticks
  (`+0x26`) then drop it without firing. Kind 0 (missile): fire when a racer is ahead in the
  same segment or anywhere in the next one and `|Δx| < 12`; difficulty 3 only targets the
  player. Kind 1 (mine): fire when a racer is behind in the same segment or anywhere in the
  previous one with `|Δx| < 12`; difficulty 3 only if that racer's points ≥ its own.
- Turbo (AI, `kart_ai_turbo`): difficulty 1 → hold 40 ticks and drop. Otherwise use it when
  `rem > 60` and `lv < 2`, or `len(nx) + rem > 60` and `lv < 2` and `lvN < 2`. The "is
  something in front" checks require an object or kart whose segment equals both the own and
  the next segment, so they never trigger unless the track has one segment (I: bug).
- Missiles (`kart_fire_weapon` kind 0): first slot ≥ n with `+2 == 1`; none free → nothing
  happens and the weapon is kept. Spawn: seg, `pos + 0x600` (wrapped once), same x, max 0x600,
  accel 0x4b, brake 0x19, steer 3, speed 0x600, type 99, owner `+0x34`, lifetime `+0x24 = 60`.
  Each tick they home (`kart_missile_home`: nearest racer with `d ≥ 0`, same segment
  `d = (pos_j − pos_i) >> 8`, next segment `d = len + ((pos_j − pos_i) >> 8)`, first index wins
  ties; the owner is a valid target) and steer ±3 toward its x. They always accelerate; they
  ignore track objects.
- Mines (kind 1): only if `rc+10 ≤ 5` (at most 6 on track; otherwise the weapon is consumed
  silently). New object {type 99, dist = (pos >> 8) − 6 (into the previous segment if negative,
  plus its length), seg, x = low byte of x (s8), count 1, spacing 0, owner}, appended to the
  object ring, `track+1 += 1`, `rc+10 += 1`.

## Collisions (kart_collide_140a468, S)

Boxes: kart `ax = x − w/2 + 60 (± k*steer while +6/+7, k < 3 for the other kart)`,
`ay = len − ((pos + k*speed) >> 8) − 2`, w = 24 (12 for missiles), h = 4.

1. **Karts.** For every other entity j that is active, not recentring, and in this or the next
   segment (missiles i skip this entirely): for k = 0.. (player: 0 only; AI: 0..5): stop when j
   is more than 4 behind; on overlap at k = 0 → `kart_hit_kart` and **return** (no object test
   this tick); at k > 0 → `kart_ai_avoid` and next j.
2. **Objects** (the track's object ring, `track+1` nodes from `track+8`): node {u16 type, u8 dist,
   u8 seg, s8 x, u8 count, u8 spacing, …, u8 held +8, s8 owner +9, next +0xc, prev +0x10}.
   Width 8 for 99 (mine), 12 for 100 (weapon box) and 101 (turbo box), 20 otherwise
   (roadside obstacles). Skipped: held boxes, objects not in this or the next segment, everything
   for missiles. Each of `count` copies at `dist + c*spacing`. For k = 0..look−1:
   - overlap at k = 0: type 100 → release any held weapon box, `+0x28 = game_rand() & 1`, hold
     this one (`+0x2c`, node +8 = 1), return. Type 101 → release, hold in `+0x30`, return.
     Otherwise `kart_hit_object`; if the node is a mine: unlink and free it, `track+1 −= 1`,
     `rc+10 −= 1`, and if the owner is not i, state is 2 and `(*0x3cc5c)[0] == 0`:
     `points[owner] += 1`; return.
   - overlap at k > 0: boxes → seek; obstacles/mines → `kart_ai_avoid`.
   - no overlap and a box → seek.
   Held boxes come back when their item is used or dropped (node +8 = 0).
3. `kart_hit_kart(i, …, j)`: `dv = |speed_i − speed_j|`. If `dv ≥ max_i >> 1` or either is a
   missile: missile j → i spins (if not invulnerable: `+0x21 = 10`, speed 0, x = 60 if x > 0
   else −60) and `points[owner] += 1` when owner != i and state == 2; j deactivated. Missile i
   → the mirror case (also requires `(*0x3cc5c)[0] == 0`; unreachable, see Open questions).
   Two karts → the faster one spins (if not invulnerable). Else a bump: the one ahead
   (smaller ay) gets `pos += 0x200`, the other `pos −= 0x200` (each only if not invulnerable);
   lateral push 24 if `−4 ≤ ax_i − ax_j ≤ 4` else 12: j moves away from i and i away from j,
   clamped to ±80.
4. `kart_hit_object(i, ax, ay, type, {bx, by})`: head-on = `−24 ≤ ax − bx ≤ 20` and
   `|ay − by| ≤ 4`. If (speed < max/3 or not head-on) and not a mine → bump (unless
   invulnerable): `pos += 0x400`, push 24 if `|(ax+12) − (bx+10)| ≤ 4` else 12 away from the
   object centre, clamp ±80. Otherwise (fast head-on, or any mine) → spin (unless
   invulnerable): `+0x21 = 10`, speed 0, and for a mine x = ±60. A missile that hits an object
   is deactivated (not reachable, missiles skip objects).

## Laps, position, timing (S)

- Laps: `+0x14`; a lap ends when the segment index wraps to 0 (step 6 of loop 2). Track laps
  at `track+2`. Lap time `+0x38`, previous lap `+0x3c`, total `+0x40` (ms, `+= period` while
  laps < total). No checkpoint logic: progress is the segment index plus position.
- Position `+0x15` (1 = first): starts from `order[]`; `kart_rank_update(i)` (racers, each
  tick): for every racer j with a worse rank, not i, and laps_j < total, swap ranks if
  `laps_i > laps_j`, or equal laps and (`seg_i > seg_j`, or equal seg and `pos_i > pos_j`).
  Exact test (disassembly of 0x01409a40): for j with `rank_i < rank_j` (i listed ahead), j != i, laps_j < total:
  swap if `laps_i < laps_j`, or equal laps and (`seg_i < seg_j`, or equal seg and `pos_i < pos_j`),
  i.e. j is really further. Only pairwise swaps, never a full sort.
- Race end (phase 2 + 60 ticks): `kart_finish_times`: for racer i: inactive → time 5999990
  (`0x5b8d76`); laps < total → `time += ((rem) << 8) / (((max*85)/100) >> 8)` (unsigned), with
  `rem = acc + len(seg) − (pos >> 8) + Σ len(segments after seg)`, where acc, if laps < total − 1,
  is `(acc + Σ all segment lengths) * (total − laps − 1)`. **acc is not reset between racers**
  (one variable for the whole loop, S), so later unfinished racers inherit earlier racers'
  distance. Then rank: for each i, for each j != i: if `t_i == t_j` and `t_i != 5999990` →
  `t_j += 10`; if `t_i > t_j` → rank_i += 1 (ranks start at 1).
- Points (`kart_cup_points`, state 3 → 4): for races 1..4 (`st+4 < 4`): active racers get
  `{10, 6, 4, 3, 2, 1}[pos − 1]`; `order[i]` = finishing position (ties numbered in index
  order); then `+0x15` = 1 + number of racers with more points (standings); `st+4 += 1`.
  After the 4th: if the player and another racer are both 1st, it sets up a tie-break race:
  `order[]` numbers the tied racers 1, 2, …, all others get their bit in `(*0x3cc4c)[1]`
  (inactive next race). Else every points total is multiplied by
  `{10, 6, 4, 3, 2, 1}[min((pos − difficulty + 2) & 0xff, 5)]`.
- Challenge (`kart_challenge_points`, state 2 end, only if `(*0x3cc5c)[0] == 0`): place
  points as above plus 1 per time threshold met: `thr = target+4`; up to 5 times: stop if
  `time > thr`, else `points += 1`, `thr −= target+8`. Then order and standings as above.
  Unlock: if bit `target+0xc` of the locked mask is set and (kind 0: `points[player] ≥ s16
  target+2`; kind 1: `points[player] ≤ u32 target+4`) → `st+0x14 = target+0xc` (state 9
  later clears that lock bit). Missile and mine hits add to `points[owner]` in challenge races.

## Start and finish (S)

- Countdown (phase 0): counter before increment 0 → `game_sound(0xfb2)`. Lamps drawn after
  the increment: count = 0 (counter 0), 1 (1..6), 2 (7..13), 3 (14..19), 4 (≥ 20). So 1 lamp
  for 6 ticks, 2 for 7, 3 for 6, 4 for 7 (counter 20..26), then GO when the pre-increment
  counter is 26 (27th tick, 1.35 s at 50 ms). Panel 72×16 (0x01504fa0) at (48 − 36, 0) =
  (12, 0); lamps 8×8 (0x01504fb8) at (20 + 15k, 5). Rebuilt every tick. No physics runs
  during the countdown, but the camera and road do.
- After GO: `st+0xa = 30` (so the lap-banner timer does not run until the first lap).
- Finish: the race ends when the **player** completes the last lap (phase 2). For 60 more ticks
  the race keeps running with the player driven by the AI rules. Then: `kart_finish_times`;
  challenge points/unlock (state 2); 0x01405f60, 0x01406084 (if track), 0x01406a6c (shell/road
  teardown, I); state 1 → 3, state 2 → 6 (time challenge, `(*0x3cc5c)[0] != 0`) or 7 (points
  challenge); `*0x3cc4c` = malloc(2) = {0, 0}.

## Sounds and vibration (S)

| Tone | When | Site |
|---|---|---|
| 0xfb8 loop | first race tick (GameBG Car Racing) | 0x01408ada |
| 0xfb2 | countdown start (counter 0) | 0x01408cfe |
| 0xfb0 start / stop | engine: starts when the player is moving without brake/turbo/spin, stops otherwise (flag 0x3d0b4[2]) | 0x014093ae / 0x014093c8 |
| 0xfb1 | player uses a turbo | 0x0140aee8 |
| 0xfb3 | any racer fires a weapon (player or AI, missile or mine) | 0x0140ad60 |

No `game_vibrator` call anywhere in 0x014047f0..0x0140da28 (BL scan). No tones on hits,
pickups, laps or the finish.

## Random numbers (S)

All game_rand calls in the Kart range (BL scan): 0x01408e3e, 0x0140a7cc, 0x0140c98a, 0x0140cc12,
0x0140d534, 0x0140d568. In this slice:

1. **0x01408e3e, `kart_racers_init`**, only when `*0x3cc70 == 0` (first race of a series):
   for i = 1..n−1: repeat `r = game_rand() % 7` (unsigned remainder) until r differs from
   `types[0..i−1]`; `types[i] = r`. types[0] is the player's kart (7 = custom never collides).
   Variable number of calls. Order in a race start: the track loader 0x0140c94c (shell) may call
   rand first (0x0140c98a: `rand & 3` picks the course of race 5, the tie-break, I) and
   0x0140cc12 (shell), then this.
2. **0x0140a7cc, `kart_collide`**, when any racer (player included) touches a weapon box
   (type 100) at k = 0: `+0x28 = game_rand() & 1` (0 = homing missile, 1 = mine). In entity
   order within loop 1 of the race step; at most one per entity per tick.
3. **0x0140d568, `kart_record_init`**, only when the mode-data record is new: stored as a u32
   at +8. Not used by the race.

The rest of the race is deterministic.

## State fields (race)

`st = *0x3cc54` (0x18 B, calloc in 0x0140491e), `rc = *0x3cc50` (12 B), `E[i] = *0x3cc44 +
0x44*i`, `trk = *0x3cc40` (12 B, built by the shell's track loader).

| Base | Off | Size | Meaning | Writers / readers |
|---|---|---|---|---|
| st | +0 | u8 | game state: 0 select, 1 cup race, 2 challenge race, 3 cup result, 4 cup standings, 5 cup final, 6 time-challenge result, 7 points-challenge result, 8 challenge final, 9 unlock | tick, race_init / everything |
| st | +1 | u8 | n racers | 0x0140c94c (shell) / all |
| st | +2 | u8 | player index (0) | racers_init / all |
| st | +3 | u8 | chosen kart 0..7 | tick (select) / race_init |
| st | +4 | u8 | cup races done (0..4) | cup_points / tick, shell |
| st | +5,+6,+7 | u8 | handler reroute flags (shell); +7 == 1 also selects the big digits | shell / handler, time/points draw |
| st | +8 | u8 | custom kart (7) exists | shell / select |
| st | +0xa | u16 | tick counter (select, countdown, lap banner, finish delay, unlock); +0xb cleared on select | tick, race_step |
| st | +0xc | u8 | locked karts mask (app data, default 0x78 = karts 3..6) | 0x0140491e, tick (state 9) / select, unlock |
| st | +0xd | u8 | mode: 1 cup, 2 challenge (setting 3) | 0x0140491e / race_init, results |
| st | +0xe | u8 | difficulty 1..3 (I) (setting 2; challenge data overrides) | shell / AI, cup multiplier |
| st | +0xf, +0x10 | u8, u32 | setting 4/5 present, value | shell / race_init, record_save |
| st | +0x14 | u8 | kart to unlock (0 none) | tick (race end) / tick (states 8, 9) |
| st | +0x15 | u8 | BG tune started | tick |
| rc | +0 | u8 | phase: 0 countdown, 1 racing, 2 player finished | race_init, tick, race_step |
| rc | +2 | s16 | player.x / 2 (passed to the road renderer) | tick |
| rc | +4 | s16 | −= speed, wraps +0x700 (I: stripe phase for the road) | tick / road (I) |
| rc | +6, +8 | s16, u8 | camera position (units) and segment, 3 units behind the player | tick / road |
| rc | +9 | u8 | missile slots (6) | race_init |
| rc | +10 | u8 | mines on track | fire_weapon, collide |
| E | +1 | u8 | 1 = recentring after a spin | race_step |
| E | +2 | u8 | 1 = inactive (excluded racer, spent missile) | racers_init, race_step, hit_kart |
| E | +3 | u8 | rubber-band boost on | rubber_band |
| E | +4..+7 | u8 | per-tick flags: accel, brake, right, left | race_step, input, AI |
| E | +8 | u8 | segment | race_step / all |
| E | +0xc | s32 | position in segment, 24.8 | race_step, hits |
| E | +0x10 | s16 | lateral x (−80..80, − = left) | lateral, AI, hits |
| E | +0x12 | s16 | player steering momentum | player_lateral |
| E | +0x14 | u8 | laps done | race_step |
| E | +0x15 | u8 | rank (1 = first) / standing | racers_init, rank_update, points |
| E | +0x16 | u8 | kart type 0..7, 99 = missile | racers_init, fire_weapon |
| E | +0x18 | s16 | speed (1/256 unit per tick) | race_step, hits, turbo |
| E | +0x1a | s16 | steer intent (sign used) | input, AI, centrifugal |
| E | +0x1c, +0x1e, +0x1f, +0x20 | u16, u8×3 | max speed, accel, brake, steer | racers_init, rubber_band |
| E | +0x21 / +0x22 / +0x23 / +0x24 | s8 | spin (10) / invulnerable (30) / turbo (5) / missile life (60) | hits, race_step, turbo, fire |
| E | +0x26 | s16 | AI item hold counter (difficulty 1) | ai_weapon, ai_turbo |
| E | +0x28 | u8 | weapon kind | collide (rand) |
| E | +0x2c / +0x30 | ptr | held weapon box / turbo box node | collide, fire, turbo |
| E | +0x34 | s8 | missile owner (0xff) | fire_weapon |
| E | +0x38 / +0x3c / +0x40 | u32 | lap ms / last lap ms / total ms (5999990 = DNF) | race_step, finish_times |
| trk | +0, +1, +2 | u8 | segments, objects, laps | loader, collide, fire |
| trk | +4, +8 | ptr | segment array, object ring head | loader / all |
| *0x3cc48 | +0..+2 | u8 | select sub-mode, page, cursor | tick |
| *0x3cc4c | +0, +1 | u8 | result page; tie-break exclusion mask | tick, cup_points / results, racers_init |
| *0x3cc5c | +0, +2, +4, +8, +0xc | u8, s16, u32, u32, u8 | challenge: kind (0 points, 1 time), points target, time target, time step, kart unlocked | shell / tick, points, hits |
| *0x3cc68 | [n] | u8 | start order for the next race | race_init, points / racers_init |
| *0x3cc6c | [n] | u16 | points | race_init, points, hits / results, AI |
| *0x3cc70 | [n] | u8 | kart type per racer (kept for the series) | racers_init |
| *0x3cc64 | | ptr | custom kart portrait frames | shell / select, results |
| 0x3d0b0 | [4] | u8 | custom kart stat levels | shell / kart_stat, rubber_band |
| 0x3d0b4 | +2 | u8 | engine tone 0xfb0 playing | race_step |
| *0x3d078 | | ptr | custom start picture (else 0x01505048) | shell / select |

Scene-object handles touched: 0x3cf24[4] portraits, 0x3cf98[4] stat icons, 0x3cfa8[4][5] stat
blocks, 0x3cea0 cursor, 0x3cf34 lights panel, 0x3cf38[4] lamps, 0x3cf48[4] rank badges,
0x3cf58[4] rank digits, 0x3cf04[4]/0x3cf14[4] time separators, 0x3cea4[6][4] time digits,
0x3cf68[3][4] points digits, 0x3cff8 trophy, 0x3ce94[2] start picture / final-screen rects.
Slot 0 of the time/points arrays is also used by the race HUD (road agent, 0x014069a8).

## Open questions

1. Physical keys: the ids come from the engine already translated; the layout table only drives
   the keypad-help picture. The 1..9 ring for layout 0 and Kart's layout 2 (4 left, 5 right,
   6 gas, 9 brake, 1 weapon, 2 turbo) are inferred from 0x01512ee8, not from the key path.
2. `kart_rank_update` is called for any spinning/recentring entity, missiles included (loop 2,
   0x01409580 skips the `i < n` test). A missile has rank 0 and could swap ranks with a racer
   if it ever spun; no code path found that spins a missile, so probably harmless.
3. `kart_hit_kart`'s "i is a missile" branch (with the `(*0x3cc5c)[0] == 0` test) is
   unreachable: `kart_collide` never runs the kart test for a missile. The live branch scores
   missile hits in every challenge, the mine path only in points challenges.
4. AI turbo "obstacle ahead" check needs seg == own seg == next seg (never true on a real track).
   Bug or intentional? Faithful port: keep.
5. `kart_finish_times` accumulator not reset per racer: confirm on hardware/emulator whether the
   displayed estimated times of unfinished racers grow with index.
6. Rubber band on a level-6 stat reads into the next table row (speed 6 → 0x28 = 40). Only a
   custom kart can have level 6 (I); what the custom-kart editor allows is in the shell.
7. Meaning of hill classes (0 uphill, 1 downhill, 2 flat) and `rc+4` (stripe phase) need the
   road agent's confirmation.
8. Difficulty `st+0xe` values outside 1..3 (0 would disable all AI object handling).
9. Segment-advance allows only one segment per tick; a segment shorter than the top speed per
   tick (turbo 0x880/256 ≈ 8.5 units) would desync position. Check track data minimum length.

