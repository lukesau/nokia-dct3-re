# Kart Racing (3510): road and track

Part of the Kart Racing map; start at `games_kart_3510.md`, which resolves the points where the slices disagreed. Names are in `ghidra/symbols/3510.csv`.

The ARM runtime divides return the **remainder in r0 and the quotient in r1** (see `games_library_3510.md`); every formula here uses that, read from the disassembly.

Image `roms/3510-nhm8-v502/flash.bin`, BE Thumb, base 0x01000000. Everything here was checked
against a capstone disassembly. Ghidra's decompiles of this slice
are wrong in several places (noted). **S** = static (read from code or data), **I** = inferred.

## Functions

### kart_road_draw_1406144 `int (s16 P)` — S
The per-tick road renderer, called from 0x0140873c with `P = cam+2` (player kart+0x10 / 2,
see State fields). Returns 1 on success, 0 on any library failure. Full algorithm in
"Road geometry". Calls, in order: `kart_seg_field` x4, `kart_backdrop_place_1406ce0(seg, H)`,
`kart_drawlist_reset_1406b08`, the behind-camera pre-pass (karts + roadside, size 3), the row
loop (with `kart_backdrop_crossing_1406e14` at a segment crossing, karts and roadside per row),
hides rows H..1, `kart_drawlist_flush_1406bb8`, then `kart_hud_build_1406828` if `cam+0 != 0`.
Ghidra decompile errors here: it reads the divide results the wrong way round, and shows
`game_rect_set_size` arguments correctly but drops the remainder/quotient distinction.

### kart_seg_field_14060c6 `int (u8 seg, int field)` — S
Reads segment `seg` of the current track (`*(*0x3cc40 + 4) + seg*4`):
- field 0: u16 length
- field 1 (slope): flags bit1 → 2, else bit0 → 1, else 0
- field 2 (curvature index): `(flags >> 2) & 7`
- field 3 (curve direction): flags bit5 → 1 else 0
- other field values → 0. (Ghidra's decompile of the bit tests is wrong; this is from the asm.)

### kart_backdrop_place_1406ce0 `int (u8 seg, int H)` — S
Places the two backdrop sprites (`*0x3ce94`, `*0x3ce98`) and the ground rect `*0x3ce9c`.
For i = 0, 1: `get_pos(obj_i)`, then
- `y = H - 19`; if `slope(seg) == 0`: `y = H - 13`.
- If `curv(seg) != 0` **and** `kart[race+2].+0x18 != 0` (player speed, I) **and** `cam+0 != 2`:
  `x += dir(seg) ? -curv : +curv` (curv = the raw index 0..7, in pixels). Then wrap with
  W = width of descriptor 0x01504c40 (120):
  - i = 0: if `x + W <= 0` → `x += W`; else if `x > 0` → `x -= W`. (Keeps x0 in (-W, 0].)
  - i = 1: if `x <= 0` → `x += W`; else if `x > W` → `x -= W`. (Keeps x1 in (0, W].)
- `set_pos(obj_i, {x, y})`.
Then `set_pos(ground_rect, {0, H + 1})`. Returns the last library result.
(Note: the wrap test reads W from 0x01504c40 even when the track uses another backdrop; all six
are 120 wide, so it doesn't matter.)

### kart_backdrop_crossing_1406e14 `int (u8 newseg, int Hnew, u8 r)` — S
Called once, at the row r where the road crosses into the next segment. `t = slope(cam seg)`,
`n = slope(newseg)`. First `set_pos(ground_rect, {0, Hnew + 1})`. Then picks a backdrop y:
- t=2, n=0, r >= 43: relative `dy = kart_horizon_2to0[r] - 17`
- t=2, n=1: absolute `y = Hnew - 19`
- t=1, n=2: absolute `Hnew - 19`
- t=1, n=0, r >= 21: `v = kart_horizon_1to0[r]`; relative dy = v-7 (r>=46), v-8 (r>=36), v-9 (r>=26), else v-10
- t=0, n=1: r < 38: relative `dy = 28 - kart_horizon_0to1[r]`; else absolute `Hnew - 19`
- t=0, n=2: r < 40: relative `dy = 28 - kart_horizon_0to2[r]`; else absolute `Hnew - 19`
- anything else: return without moving the backdrops.
Applies to both backdrop sprites: absolute → `y = value`, relative → `y = y + dy` (y as just set
by 1406ce0 this frame).

### kart_drawlist_reset_1406b08 `int ()` — S
Frees every node of the per-frame draw list at `*0x3cc3c` (deleting its scene object if
any), sets the list to empty, then sets `progress (+7) = 0` on every roadside node of the
track (count = track+1), and `kart.+0 (drawn flag) = 0` for the first `race+1 + cam+9` karts.

### kart_drawlist_add_1407588 `int (bmp*, pt* pos, u8 kind)` — S
Mallocs a 0x18-byte node `{+0 obj = 0, +4 pos, +8 bmp, +0xc kind, +0x10 next, +0x14 prev}`
and appends it at the tail of the circular list `*0x3cc3c` (head.prev = tail).

### kart_drawlist_flush_1406bb8 `int ()` — S
Walks the list **backwards** from the tail (`node = head.prev`, then `.prev` until it is back
at the head), so the **last-queued (farthest) entry is created first** and the nearest ends up
on top. For each node:
- kind 1 with `*0x3cc58 != 0` (the gate banner): if `kart_box_onscreen(banner+4, w=+8, h=+0xa)`:
  `game_rect_create(root, 0x1000, banner+4, w=+8, h=+0xa, a6=0, a7=pattern(+0), a8=0, style 0)`;
  then frees the banner and clears `*0x3cc58`.
- otherwise: if `kart_box_onscreen(node+4, bmp.w, bmp.h)`: `game_sprite_create(root, 0x1000,
  node+4, bmp, 1)` and stores the object in node+0.

### kart_box_onscreen_1406c88 `bool (pt* pos, s16 w, s16 h)` — S
`x <= 96 && y < 66 && x + w >= 0 && y + h >= 0` (note: inclusive at 96, 65 and at the
left/top edges, so a box ending exactly at x = 0 counts as visible).

### kart_row_scale_14075e2 `s16 (slope, row)` — S
`kart_row_scale_1508fa4[slope*65 + row]`.

### kart_karts_queue_1406f54 `int (seg, s16 hi, s16 lo, size, [sp] s16 hw, [sp+2] s16 xc, [sp+4] u8 row)` — S
Queues kart sprites for one row (all karts 0..race+1+cam+9-1, stride 0x44 from `*0x3cc44`).
A kart k is drawn here if `k.+0 == 0 && k.+2 == 0`, `k.+0x22 bit0 == 0`, `k.+1 != 1` and
either (`k.+8 == seg && lo <= k.+0xc>>8 <= hi`) or (`k.+0xc>>8 == 0 && hi == len[cam seg] &&
(k.+8 == seg+1 || (k.+8 == 0 && seg == nseg-1))`). Then `k.+0 = 1` (drawn this frame).
- `k.+0x16 == 99`: one sprite: bmp = k.+6==1 ? 0x01504d30 : k.+7==1 ? *0x3cc60+0x300 : 0x01504cd0,
  plus `size*0x18`. `x = xc + q(k.+0x10 * hw, 60) - (bmp.w >> 1)`, `y = row - bmp.h`.
- else two sprites, body (`B`) and driver (`D`), type = k.+0x16 (7 = custom from RAM `*0x3cc64`).
  Variant: if `k.+0x21 == 0`: k.+6==1 → B 0x015046a0, D 0x015049a0+type*0x60 (type 7: *0x3cc64+0x90);
  k.+7==1 → B *0x3cc60, D *0x3cc60+type*0x60+0x60 (type 7: *0x3cc64+0xf0); else B 0x01504640,
  D 0x01504700+type*0x60 (type 7: *0x3cc64+0x30). If `k.+0x21 != 0`: `m = (s8)k.+0x21 % 3`
  (remainder) selects the same three variants (0 → +6 variant, 1 → +7 variant, 2 → default; a
  negative remainder selects none and reuses stale pointers). Each + `size*0x18`.
  `y = row - B.h - D.h`; x: for the player (`index == race+2`) while `cam+0 != 2`:
  `x = k.+0x12 - (B.w >> 1) + 48`; otherwise `x = xc + q(k.+0x10 * hw, 60) - (B.w >> 1)`.
  Queues D at (x, y), then B at (x, y + **D.w**) (the code adds the driver's width, +0, not its
  height; I: the driver bitmaps are square so it is equivalent).
Race-logic fields used here (+0x10 lateral, +0x12 player screen x, +0xc position) belong to the
race-logic slice; listed in State fields.

### kart_roadside_queue_140726c `int (seg, s16 hi, s16 lo, size, [sp] s16 hw, [sp+2] s16 xc, [sp+4] u8 row)` — S
For each roadside node (track+1 of them, list from track+8 via +0xc):
1. skip if `node.seg > seg` or `node.progress >= node.count`.
2. base distance d0: if `seg == nseg-1 && node.seg == 0`: `d0 = len[cam seg] + node.start`;
   else if `node.seg >= seg` (i.e. ==): `d0 = node.start`; else
   `d0 = node.start - (sum of len[node.seg .. seg-1] as u16)`.
3. if `d0 + spacing*count < 0` or `node.+8 == 1`: `progress = count`, next node.
4. `x = s16(xc + q(node.lat * hw, 60))`; for i = progress .. count-1, `di = d0 + spacing*i`:
   - if `lo > di`: `progress = i+1` (passed; not drawn);
   - else if `hi < di`: stop this node (not reached yet);
   - else draw: bitmap by id: `< 99` → `0x01503f80 + id*0x60`; 99 → 0x01504d90; 100 →
     0x01504df0; 101 → 0x01504e50; 102 → 0x01504460; `>= 103` → `*(0x3d07c + ((id>>3)&0xc)) +
     (id&0x1f)*0x60` (downloaded objects); all `+ size*0x18`. Position
     `{x - (bmp.w >> 1), row - bmp.h}`. `progress = i+1`; `kart_drawlist_add(bmp, pos, 0)`.
   - id 102 is a gate post: it is skipped entirely (not drawn, progress unchanged) when the
     player kart has `+0x14 == 0 && +8 == 0` (I: lap 0, on segment 0). Otherwise each post's
     position is remembered as the left (lat < 0) or right (lat >= 0) post; the first time per
     call `(ph, ph2)` = size 0 (2,6), 1 (4,8), 2 (6,12), 3 (8,16). When both posts are known a
     banner is queued: `*0x3cc58 = malloc(0xc)` (if null) with `+8 w = ph2 + (right.x - left.x)`,
     `+0xa h = ph*2`, `+4 pos = {left.x, left.y - ph}`, `+0 = kart_gate_patterns + size*8`, and a
     list node of kind 1. No built-in track uses id 102.
5. returns 0 only if a list add failed.

### kart_hud_build_1406828 / kart_hud_delete_1406a6c / kart_time_draw_140808c — S
Rebuilt every frame (delete all, recreate). Player kart `K = kart[race+2]`.
- (0,0) panel 0x01504fd0 → `*0x3ce7c`; (13,3) digit `0x01513468 + K.+0x15*0x18` → `*0x3ce80`
  (I: race position); (22,2) if `K.+0x2c`: `K.+0x28 ? 0x01505018 : 0x01504fe8` → `*0x3ce8c`;
  (35,2) if `K.+0x30`: 0x01505000 → `*0x3ce90`; (48,2) time via 140808c: value =
  `race.+0xa < 26 && cam+0 == 1` ? (`race.+0xa % 3 == 0` → no time drawn, else `K.+0x3c`) :
  `K.+0x40`; (85,3) digit `min(K.+0x14 + 1, track+2)` → `*0x3ce84` (I: lap); (89,3) 0x01504f40
  → `*0x3cf08`; (91,3) digit `track+2` → `*0x3ce88` (laps).
- 140808c(v, pos, slot): `s = v/1000`, `m = s/60`, `ss = s%60`, `cs = (v%1000)/10`; six 10-frame
  digit sprites (small 0x01513468, or big 0x01513634 when `race.+7 == 1`): m/10, m%10, ss/10,
  ss%10, cs/10, cs%10. After digit 1 a separator (small 0x01504f40 at x+4, big 0x01504f70 at
  x+7), after digit 3 another (0x01504f58 / 0x01504f88). Advance after each digit: big 3 (after
  1,3) else 7; small 2 (after 1,3) else 4. Objects in 0x3cea4 + slot*4 + i*0x10, separators
  0x3cf04/0x3cf14 + slot*4. (HUD is outside the road picture; included because it is a callee.)

### kart_scene_build_1405534 `int ()` — S (the race-scene setup; part of the app shell)
Creates, under the root and in this order (= draw order, back to front):
1. backdrop sprites `*0x3ce94`, `*0x3ce98` at (0,0) and (W,0): bitmap = `track+3 < 0x80` ?
   `0x01504c40 + idx*0x18` : `*0x3d074 + (idx&0x7f)*0x18` (downloaded); 1 frame.
2. ground rect `*0x3ce9c`: `game_rect_create(root, 0x1000, {2W, 0}, w=96, h=20, a6=0, 0, 0, style 0)`.
3. 65 x 2 row rects `*0x3cc74[row*2 + side]`: pos {-1 (side 0) or 97 (side 1), row}, w = 0,
   h = 1, a6 = 1, a7 = a8 = 0, style 0.
Then 0x01405778 (other slice) and zeroes the HUD object pointers.
Rendering semantics (S from 0x0142a5b4 → 0x0126a2dc → fill routine 0x0126ab40): a rect covers
x..x+w-1, y..y+h-1; `a6 == 0` clears pixels, `a6 != 0` sets them (I: set = black on the LCD), so
**row rects are black and the ground rect is white**. Karts and objects are queued per frame
and created after these, so they draw on top.
- The task brief's "setup around 0x0140afde" (`kart_demo_start_140af18`) is a different scene: it
  creates **line** objects (type 6) in the same 0x3cc74 slots and a sprite of 0x01504c40 at (0,4);
  0x0140c19c then draws a fixed downhill road (slope table 2, rows 64..24, half-width 60 or 70
  with the same stripe test) with `game_line_set_points`. I: the title/menu attract picture.
  `game_rect_set_size` refuses type 6, so kart_road_draw only works on the 1405534 scene.

### Track loading (built-in) — S
`kart_track_load_builtin_140cbfc(r0 = 0)` (called from 0x0140c94c when `race.+0xf == 0`; a
non-zero +0xf loads downloaded game data instead):
- `race.+0xd == 1` (I: race): track = `kart_track_ptrs_3d090[race.+4]` (if `race.+4 >= 4`:
  `game_rand() & 3`); laps (track+2) = 3; `race.+1 = 6`.
- `race.+0xd == 2`: track = 0x015097d4; laps = 1; `race.+1 = 4`, `race.+0xe = 2`, plus a
  0x10-byte record at `*0x3cc5c` = {0, u32 20000, u32 2000, 0, 0} (race-logic slice).
- Builds `*0x3cc40` (malloc 0xc): `+0 nseg, +1 nobj, +2 laps, +3 backdrop, +4 seg array,
  +8 object list`. `kart_track_segments_load_140ca96`: calloc(nseg, 4); each ROM pair
  `{b0, b1}` → `{u16 len = b0*5, u8 flags = b1, u8 0}`. `kart_track_objects_load_140caf0`: per ROM
  5-byte record `{id, start, seg, lat, cs}` → 0x14-byte node `{+0 u16 id, +2 u8 start, +3 u8
  seg, +4 s8 lat = (lat&0x7f) negated if bit7, +5 count = cs&0x1f, +6 spacing = (cs>>5)*5,
  +7 progress 0, +8 0, +9 0xff, +0xc next, +0x10 prev}` appended to a circular list.
- `kart_track_ptrs_3d090` is RAM, initialised from the scatter-load record at 0x01536670
  (`{len 0x10, addr 0x3d090}` then 0x01509594, 0x01509600, 0x015096ac, 0x01509744).
- `kart_track_free_1406084`: frees the segment array, the object list and the track.

## Track format and the five built-in tracks

ROM record: `u8 nseg, u8 nobj, u8 backdrop, nseg x {u8 len/5, u8 flags}, nobj x 5 bytes`.
Segment flags: bits 0-1 slope (bit1 wins: 2; else bit0: 1; else 0), bits 2-4 curvature index,
bit 5 curve direction (1 = `+step` per row, I: right-hand bend... see Open questions), bits 6-7
unused (all 0). Laps come from the mode, not the record.

Slope (S: horizon row): 2 → H 23 (the common default, all straights), 0 → H 28, 1 → H 13.
I: 2 = level, 1 = uphill ahead (more road visible), 0 = crest/downhill.

| Track | ROM | segs | objs | backdrop | length (sum) | laps |
|---|---|---|---|---|---|---|
| track0 (`ptrs[0]`) | 0x01509594 | 7 | 18 | 2 | 1350 | 3 |
| track1 | 0x01509600 | 16 | 27 | 3 | 2200 | 3 |
| track2 | 0x015096ac | 17 | 23 | 0 | 1650 | 3 |
| track3 | 0x01509744 | 15 | 22 | 0 | 1900 | 3 |
| mode-2 track | 0x015097d4 | 12 | 22 | 2 | 1275 | 1 |

Backdrops 1, 4, 5 are unused by built-in tracks. Full per-segment and per-object listings are
in Appendix B. Object ids used: 0..12 (scenery, see `tools/dct4_bitmaps.py 0x01503f80 --count 52`), 100 (three across the road at lat -30/0/30, 101
(pairs at ±10): I: on-road pickups; their effect is race logic. Scenery sits at lat ±75..±90.

## Depth, scale and other tables (dumps in Appendix A)

- `kart_row_depth_150912c[row]` (8.8; integer part used): distance ahead of the camera for each
  screen row, 0 for rows 0..12, 99 at row 13 down to 1 at row 64. Entries 33..65 are reused by
  the behind-camera pre-pass. Its halfword 0x0150920e (row 56 = 0x0300) is also read by 0x0140873c
  as the camera offset: `cam+6 = (kart.+0xc - 0x300) >> 8`, i.e. the camera sits 3 units behind
  the player.
- `kart_row_scale_1508fa4[slope][i]` (8.8): road scale per row index, 256 at index 64; first
  non-zero index 29 (slope 0), 14 (slope 1), 24 (slope 2), i.e. the row just below each H.
- Horizon transition tables (`kart_horizon_<old>to<new>`): new H indexed by the crossing row.
  Checked: for every possible crossing row r (> old H) the value is in 0 < H < r, and at r = 64 it
  equals the new slope's resting horizon (28/13/23).
- `kart_curve_step_1509548[curv]` = {0, 1638, 2185, 3277, 4369, 4915, 5571, 6554} (16.16 px;
  0, 1/40, 1/30, 1/20, 1/15, 3/40, 0.085, 1/10). Built-in tracks use 0..4.
- `kart_patterns_1509568`: 8-byte fill patterns for the id-102 banner per size.

## Road geometry: the exact per-frame computation (S)

Inputs: track, `cs = cam+8` (camera segment), `pos = cam+6`, `st4 = cam+4`, `P = cam+2`.
`L(i)` = length of segment i, n = nseg. s16() = truncate to signed 16 bits, `q(a,b)` =
quotient truncated toward 0. All "s16" points below are real truncations in the code.

```
t1 = slope(cs); slope = t1; dir = dir(cs); curv = curv(cs)
idx = 0; step = 0; acc = 0; dx = 0; hw0 = 60; sw0 = 10
H = {0:28, 1:13, 2:23}[t1]
kart_backdrop_place_1406ce0(cs, H)
rem = s16(L(cs) - pos)
X = (48 - P) << 16                         # 16.16 road centre accumulator
kart_drawlist_reset_1406b08()

# pre-pass: things 0..19 units behind the camera, drawn at rows 97..65 (below the screen), size 3
for k in 0..32:
    seg = cs; a = s16(pos - (depth[33+k] >> 8)); b = s16(pos - 19)
    if a < 0: seg = (seg-1)&0xff; if seg >= n: seg = n-1; a = s16(a + L(seg)); b = s16(b + L(seg))
    v = s16(0x160 - 3k); hwk = (v*15*1024) >> 16          # 82 .. 60
    karts(seg, a, b, 3, hwk, s16(48 - 2P), 97-k); roadside(... same ...)

rowseg = cs; lo = s16(pos + 1)              # pos + (depth[64] >> 8)
for r = 64 down to 1, stopping before r == H:
    d = depth[r] >> 8
    if rowseg != cs:                        # after the crossing: interpolate the scale index
        if acc == 0: acc = idx << 8
        acc = s16(acc - step); idx = s16(acc >> 8) + ((acc >> 7) & 1)
    else: idx = r
    scale = SCALE[slope][idx]
    hi = rowseg == cs ? s16(d + pos) : s16(d + pos - L(cs))
    if d > rem and rowseg == cs:            # crossing into the next segment (happens at most once)
        old = L(cs); rowseg = (rowseg+1)&0xff; if rowseg >= n: rowseg = 0
        slope, dir, curv = fields of rowseg
        hi = s16(d + pos - old)
        v = s16(scale * hw0); hw0 = s16(v >> 8) + ((v >> 7) & 1)       # rounded
        sw0 = s16((scale * sw0) >> 8)                                  # truncated
        lo = 0
        if (t1, slope) has a table: H = horizon_<t1>to<slope>[r]       # else H unchanged
        target = s16(60 * SCALE[slope][H+1])
        for k = 63 down to 1: if hw0 * SCALE[slope][k] <= target:
                                  step = s16(q(0x4000 - k*256, r - H)); break
        rem = s16(rem + L(rowseg))
        scale = SCALE[slope][64]            # = 256
        kart_backdrop_crossing_1406e14(rowseg, H, r)
        idx = 64
    # draw row r
    qx = q(P << 16, 20)
    v = d - (s16(st4) >> 8) + 8;  stripe = ((q(v, 4) & 1) == 0 and r > 20) ? sw0 : 0
    dx += dir ? +CURV[curv] : -CURV[curv]
    X += dx; X += qx                         # 32-bit wrap
    hw = s16(s16((stripe + hw0) * scale) >> 8)
    cx = s16(X >> 16)
    xl = s16(cx - hw - P)
    if xl < 0: hide left rect
    else: show left rect at (0, r), size (min(xl, 96), 1)
    xr = s16(cx + hw - P)
    if xr > 96: hide right rect
    else: show right rect at (max(xr, 0), r), size (96 - max(xr, 0), 1)
    if d < 45:
        karts   (rowseg, hi, lo, d>=25?0: d>=15?1: d>=5?2: 3, s16((hw0*scale) >> 8), s16(cx - P), r)
        roadside(rowseg, hi, lo, d>=35?0: d>=20?1: d>=10?2: 3, same hw, same xc, r)
hide both rects of every row from the stop row (== H) down to 1        # row 0 is never touched
kart_drawlist_flush_1406bb8()
if cam+0 != 0: kart_hud_build_1406828()
```

Notes (S unless marked):
- The road is the **white gap** between a black left rect `[0, xl)` and a black right rect
  `[xr, 96)`; the road surface itself is never drawn. Background above the rects: backdrop,
  then the white ground rect at rows H+1..H+20 (it blanks the part of the backdrop that would show
  through the road; the flat-slope backdrop hangs 6 rows below H).
- The stripe term widens the road by `sw0*scale/256` on alternate 4-unit bands of distance,
  phase `st4 >> 8` (0..7, see cam+4), so the verge edge zig-zags and scrolls; rows 0..20 never
  get it. `q(v,4)` is a C truncating division (the code adds 3 for negative v).
- Curvature is a second-order accumulation from the bottom row up: `dx` grows by ±step per
  row and `X` by `dx`, so a curve bends the road quadratically. `P` both offsets the start
  (`48 - P`) and is subtracted again from each edge, while `qx = P*65536/20` per row pulls the
  centre back toward 48 with height (parallax). At the bottom the road is wider than the screen
  (hw 60 + stripe).
- The crossing can only happen once per frame (the test requires `rowseg == cs`); a second
  segment boundary further up is drawn with the first new segment's slope and curvature, and
  `hi` keeps subtracting only `L(cs)`.
- Sprites: karts and objects are drawn at the first row (from the bottom) whose `hi` reaches
  them; `lo` (pos+1, or 0 after the crossing) drops things behind. Objects and karts are only
  queued while `d < 45`; their size class comes from `d` alone.
- `rem`, `hi`, `lo` and the stack args are s16; `hw` passed to sprites omits the stripe.
- Ghidra decompile pitfalls: swapped divide results; `local_84`/`local_88` CONCAT22 halves.

## Horizon backdrop (S)

Two sprites of the track's 120x20 backdrop tile side by side (`x0` in (-120, 0], `x1` in
(0, 120]). Each frame: y = H-19 (slope 1, 2) or H-13 (slope 0), then the crossing adjustment
of 1406e14. Sideways scroll: `curv` pixels per tick (the index, not the step value), opposite
to the curve direction (dir bit set → x decreases), only while the player's +0x18 is non-zero
and `cam+0 != 2`. Initial x: 0 and 120 (scene build), y 0 until the first frame. Rendered:
the six backdrops at `0x01504c40` (`tools/dct4_bitmaps.py 0x01504c40 --count 6`) (0 clouds/hills, 1 night sky, 2 trees + tower, 3 savanna,
4 ruins/desert, 5 forest; names I).

## Roadside objects (S)

On-screen: `x = xc + q(lat * hw, 60) - (w >> 1)`, `y = row - h` (bottom at the row), where
`xc = cx - P` and `hw = (hw0 * scale) >> 8` of that row. Size class from the row's depth `d`:
`d >= 35` → 0 (4x8 class), `>= 20` → 1, `>= 10` → 2, else 3; behind the camera always 3.
Bitmaps are pre-scaled (no runtime scaling) and masked (the +0xc plane: 1 = opaque).
Repeated instances: instance i of a node sits at `start + spacing*i` in its segment.

## State fields (road)

| Struct | Offset | Size | Meaning | Written by | Read by (this slice) | S/I |
|---|---|---|---|---|---|---|
| cam `*0x3cc50` | +0 | u8 | race phase (0 countdown?, 1 racing, 2 finished; 3,6,7 later) | 0x0140873c and others | 1406ce0 (`!= 2` scroll), 1406f54 (player x mode), 1406144 (`!= 0` → HUD), 1406828 | S (meanings I) |
| cam | +2 | s16 | `P` = player kart.+0x10 / 2 (truncating) | 0x0140873c (0x01408bbe) | passed as P | S |
| cam | +4 | s16 | stripe phase 8.8: `-= kart.+0x18` each tick, `+= 0x700` when <= 0 (range 1..0x700) | 0x0140873c | 1406144 (`>>8`) | S |
| cam | +6 | s16 | camera distance into its segment = `(kart.+0xc - 0x300) >> 8`, + len if kart is in the next seg; wrapped by 0x0140873c | 0x0140873c | 1406144, 1406f54 | S |
| cam | +8 | u8 | camera segment | 0x0140873c | 1406144, 1406e14, 1406f54 | S |
| cam | +9 | u8 | extra kart count added to race+1 | ? | 1406b08, 1406f54 | S (I: player count) |
| race `*0x3cc54` | +1 | u8 | opponent/kart count (6 race, 4 mode 2) | 140cbfc | 1406b08, 1406f54 | S |
| race | +2 | u8 | player kart index | race slice | 1406ce0, 1406f54, 140726c, HUD | S |
| race | +4 | u8 | track choice 0..3 (>= 4 random) | menu | 140cbfc | S |
| race | +7 | u8 | 1 = big HUD digits | ? | 140808c | S |
| race | +0xa | u16 | tick counter (countdown/blink) | 0x0140873c | HUD | S |
| race | +0xd | u8 | mode 1 / 2 | menu | 140cbfc | S |
| kart `*0x3cc44 + i*0x44` | +0 | u8 | drawn-this-frame flag | 1406f54 (1), 1406b08 (0) | 1406f54 | S |
| kart | +1, +2, +0x22 bit0 | u8 | skip-drawing conditions | race slice | 1406f54 | S |
| kart | +6, +7, +0x21 | u8 | sprite variant selectors | race slice | 1406f54 | S |
| kart | +8 | u8 | segment | race slice | 1406f54, 140726c (player) | S |
| kart | +0xc | s32 | position in segment, 24.8 | race slice | 1406f54, 0x0140873c | S |
| kart | +0x10 | s16 | lateral, in road units (x = xc + lat*hw/60) | race slice | 1406f54, cam+2 | S |
| kart | +0x12 | s16 | player's screen x offset from 48 | race slice | 1406f54 | S |
| kart | +0x14 | u8 | lap (I) | race slice | 140726c (id 102), HUD | S |
| kart | +0x15 | u8 | position digit (I) | race slice | HUD | S |
| kart | +0x16 | u8 | sprite type (0..7, 99) | race slice | 1406f54 | S |
| kart | +0x18 | s16 | speed (I) | race slice | 1406ce0, cam+4 | S |
| kart | +0x28, +0x2c, +0x30, +0x3c, +0x40 | | HUD icons and times | race slice | HUD | S |
| track `*0x3cc40` | +0..+8 | | nseg, nobj, laps, backdrop, segs*, objs* | 140cbfc/ca96/caf0 | everything here | S |
| object node | +7 | u8 | progress (next instance) | 140726c, 1406b08 | 140726c | S |
| object node | +8 | u8 | 1 = disabled | (0 at load) | 140726c | S |
| `*0x3cc3c` | | ptr | per-frame draw list | 1407588, 1406b08 | 1406bb8 | S |
| `*0x3cc58` | | ptr | pending gate banner | 140726c | 1406bb8 | S |
| `0x3cc74` | row*8+side*4 | obj* | 65 x 2 black row rects | 1405534 | 1406144 | S |
| `0x3ce94`/`0x3ce98` | | obj* | backdrop sprites | 1405534 | 1406ce0, 1406e14 | S |
| `0x3ce9c` | | obj* | white ground rect 96x20 | 1405534 | 1406ce0, 1406e14 | S |

## Open questions

1. Colour of rect `a6`: the GDI fill (0x0126ab40) clears bits when a6 == 0 and takes another
   path when a6 != 0; that 1 = black is inferred, not traced to the LCD. If inverted the road
   would be black on white; the backdrops (black hills on white sky) suggest the inference.
2. Whether the screen is cleared to white before the scene is rendered (assumed; not checked).
3. `game_rect_set_size` with w = 0 (xl == 0) and how 0x0126ab40 handles a zero/negative width.
4. Direction semantics: dir bit 5 set makes dx grow positive (road bends right on screen) and the
   backdrop move left; which way the kart is pushed in a bend is race logic.
5. Slope semantics (which of 0/1 is up/down hill) are inferred from the horizon rows only.
6. Kart drawing details (`+6/+7/+0x21` variants, custom sprites in `*0x3cc60/*0x3cc64`,
   kart type 99) belong to race logic; I did not confirm what they mean.
7. `cam+9` and `race+1` meanings (kart counts) and the mode-2 record at `*0x3cc5c`.
8. Object ids 99-101 effects and the 102 gate (downloaded tracks only): race logic / shell.
9. 0x0140af18 / 0x0140c19c (line-object road, fixed downhill): which screen it is (attract or
   menu) is for the app-shell slice.
10. A Python model of this algorithm was written during mapping and draws a plausible road, but
    nothing here has been compared with the real code running; sprite order and the pre-pass
    are only checked by reading.

## Appendix A: tables

### kart_row_depth_150912c (u32 8.8, index = screen row; 66 words, entry 65 = 0)

| row | raw | >>8 |
|---|---|---|
| 0 | 0x0000 | 0 |
| 12 | 0x0000 | 0 |
| 13 | 0x6300 | 99 |
| 14 | 0x6100 | 97 |
| 15 | 0x5900 | 89 |
| 16 | 0x5100 | 81 |
| 17 | 0x4a00 | 74 |
| 18 | 0x4300 | 67 |
| 19 | 0x3d00 | 61 |
| 20 | 0x3700 | 55 |
| 21 | 0x3100 | 49 |
| 22 | 0x2b00 | 43 |
| 23 | 0x2600 | 38 |
| 24 | 0x2300 | 35 |
| 25 | 0x2000 | 32 |
| 26 | 0x1e00 | 30 |
| 27 | 0x1c00 | 28 |
| 28 | 0x1b00 | 27 |
| 29 | 0x1a00 | 26 |
| 30 | 0x1800 | 24 |
| 31 | 0x1600 | 22 |
| 32 | 0x1500 | 21 |
| 33 | 0x1300 | 19 |
| 34 | 0x1200 | 18 |
| 35 | 0x1000 | 16 |
| 36 | 0x0f00 | 15 |
| 37 | 0x0d00 | 13 |
| 38 | 0x0c00 | 12 |
| 39 | 0x0b00 | 11 |
| 40 | 0x0a00 | 10 |
| 41 | 0x0900 | 9 |
| 42 | 0x0880 | 8 |
| 43 | 0x0800 | 8 |
| 44 | 0x0780 | 7 |
| 45 | 0x0700 | 7 |
| 46 | 0x0680 | 6 |
| 47 | 0x0600 | 6 |
| 48 | 0x05aa | 5 |
| 49 | 0x0555 | 5 |
| 50 | 0x0500 | 5 |
| 51 | 0x04aa | 4 |
| 52 | 0x0455 | 4 |
| 53 | 0x0400 | 4 |
| 54 | 0x03ab | 3 |
| 55 | 0x0355 | 3 |
| 56 | 0x0300 | 3 |
| 57 | 0x02c0 | 2 |
| 58 | 0x0280 | 2 |
| 59 | 0x0240 | 2 |
| 60 | 0x0200 | 2 |
| 61 | 0x01c0 | 1 |
| 62 | 0x0180 | 1 |
| 63 | 0x0140 | 1 |
| 64 | 0x0100 | 1 |
| 65 | 0x0000 | 0 |

Rows 0..12 are 0.

### kart_row_scale_1508fa4 (s16 8.8, [slope][row], 3 x 65; row index past a crossing is the interpolated index)

- slope 0: rows 0..28 = 0; rows 29..64 = [97, 100, 103, 105, 108, 111, 115, 118, 121, 125, 128, 132, 135, 139, 143, 147, 151, 155, 160, 164, 169, 174, 179, 184, 189, 194, 199, 205, 211, 217, 223, 229, 236, 242, 249, 256]
- slope 1: rows 0..13 = 0; rows 14..64 = [19, 20, 21, 22, 23, 25, 26, 27, 29, 30, 32, 34, 35, 37, 39, 41, 44, 46, 48, 51, 54, 56, 59, 63, 66, 70, 73, 77, 81, 86, 90, 95, 100, 106, 111, 117, 123, 130, 137, 144, 152, 160, 169, 178, 187, 197, 208, 219, 231, 243, 256]
- slope 2: rows 0..23 = 0; rows 24..64 = [61, 63, 66, 68, 71, 73, 76, 79, 81, 84, 87, 91, 94, 97, 101, 105, 108, 112, 116, 121, 125, 130, 134, 139, 144, 150, 155, 161, 167, 173, 179, 186, 192, 199, 207, 214, 222, 230, 238, 247, 256]

### Horizon transition tables (s16 per crossing row 0..64)

- kart_horizon_2to0_1509230: rows 0..22 = 0; rows 23..64 = [23, 23, 23, 22, 22, 22, 21, 21, 21, 20, 20, 20, 19, 19, 19, 18, 18, 18, 17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 23, 24, 24, 25, 25, 26, 26, 27, 27, 28, 28]
- kart_horizon_2to1_15092b4: rows 0..22 = 0; rows 23..64 = [23, 23, 23, 23, 22, 22, 22, 22, 21, 21, 21, 21, 20, 20, 20, 20, 19, 19, 19, 18, 18, 18, 18, 17, 17, 17, 16, 16, 16, 16, 15, 15, 15, 15, 14, 14, 14, 14, 13, 13, 13, 13]
- kart_horizon_0to2_1509338: rows 0..27 = 0; rows 28..64 = [28, 28, 28, 29, 29, 29, 30, 30, 30, 31, 31, 31, 30, 30, 30, 29, 29, 29, 28, 28, 28, 27, 27, 27, 26, 26, 26, 25, 25, 25, 24, 24, 24, 23, 23, 23, 23]
- kart_horizon_0to1_15093bc: rows 0..27 = 0; rows 28..64 = [28, 28, 28, 29, 29, 29, 30, 30, 31, 31, 30, 29, 28, 28, 27, 26, 26, 25, 24, 24, 23, 22, 22, 21, 20, 20, 19, 18, 18, 17, 16, 16, 15, 14, 14, 13, 13]
- kart_horizon_1to0_1509440: rows 0..13 = 0; rows 14..64 = [13, 13, 13, 12, 12, 11, 11, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18, 19, 19, 20, 20, 20, 21, 21, 22, 22, 22, 23, 23, 24, 24, 24, 25, 25, 26, 26, 26, 27, 27, 27, 28, 28, 28]
- kart_horizon_1to2_15094c4: rows 0..13 = 0; rows 14..64 = [13, 13, 14, 14, 15, 15, 15, 15, 16, 16, 16, 16, 17, 17, 17, 17, 17, 18, 18, 18, 18, 18, 19, 19, 19, 19, 19, 19, 20, 20, 20, 20, 20, 20, 21, 21, 21, 21, 21, 22, 22, 22, 22, 22, 22, 23, 23, 23, 23, 23, 23]

### kart_curve_step_1509548 (s16, index = curvature 0..7; 16.16 px per row per row)

[0, 1638, 2185, 3277, 4369, 4915, 5571, 6554]

### kart_patterns_1509568 (8 bytes per size 0..3)

['55aa55aa55aa55aa', 'cccc3333cccc3333', '0f0f0f0ff0f0f0f0', '0f0f0f0ff0f0f0f0']

## Appendix B: the built-in tracks

### track0 @ 0x01509594: nseg=7 nobj=18 backdrop=2 total length=1350
| seg | len | flags | slope | curv idx | dir | other bits |
|---|---|---|---|---|---|---|
| 0 | 200 | 0x02 | 2 | 0 | -1 | 0x0 |
| 1 | 150 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |
| 2 | 150 | 0x0c | 0 | 3 | -1 | 0x0 |
| 3 | 100 | 0x01 | 1 | 0 | -1 | 0x0 |
| 4 | 150 | 0x32 | 2 | 4 | +1 (bit5 set) | 0x0 |
| 5 | 400 | 0x02 | 2 | 0 | -1 | 0x0 |
| 6 | 200 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |

| # | id | seg | start | lateral | count | spacing |
|---|---|---|---|---|---|---|
| 0 | 6 | 0 | 1 | 80 | 8 | 25 |
| 1 | 6 | 0 | 1 | -75 | 4 | 30 |
| 2 | 8 | 0 | 1 | -75 | 8 | 30 |
| 3 | 100 | 1 | 0 | -30 | 1 | 0 |
| 4 | 100 | 1 | 0 | 0 | 1 | 0 |
| 5 | 100 | 1 | 0 | 30 | 1 | 0 |
| 6 | 2 | 1 | 1 | -80 | 20 | 30 |
| 7 | 2 | 2 | 0 | 80 | 30 | 35 |
| 8 | 101 | 2 | 0 | -30 | 1 | 0 |
| 9 | 100 | 2 | 0 | 0 | 1 | 0 |
| 10 | 100 | 2 | 0 | 30 | 1 | 0 |
| 11 | 101 | 3 | 1 | -10 | 1 | 0 |
| 12 | 101 | 3 | 1 | 10 | 1 | 0 |
| 13 | 100 | 4 | 0 | -30 | 1 | 0 |
| 14 | 100 | 4 | 0 | 0 | 1 | 0 |
| 15 | 100 | 4 | 0 | 30 | 1 | 0 |
| 16 | 6 | 4 | 1 | 80 | 31 | 35 |
| 17 | 2 | 4 | 1 | -80 | 31 | 35 |

### track1 @ 0x01509600: nseg=16 nobj=27 backdrop=3 total length=2200
| seg | len | flags | slope | curv idx | dir | other bits |
|---|---|---|---|---|---|---|
| 0 | 200 | 0x02 | 2 | 0 | -1 | 0x0 |
| 1 | 100 | 0x2c | 0 | 3 | +1 (bit5 set) | 0x0 |
| 2 | 100 | 0x02 | 2 | 0 | -1 | 0x0 |
| 3 | 75 | 0x2d | 1 | 3 | +1 (bit5 set) | 0x0 |
| 4 | 400 | 0x02 | 2 | 0 | -1 | 0x0 |
| 5 | 75 | 0x0c | 0 | 3 | -1 | 0x0 |
| 6 | 100 | 0x02 | 2 | 0 | -1 | 0x0 |
| 7 | 100 | 0x0d | 1 | 3 | -1 | 0x0 |
| 8 | 200 | 0x02 | 2 | 0 | -1 | 0x0 |
| 9 | 100 | 0x0e | 2 | 3 | -1 | 0x0 |
| 10 | 200 | 0x00 | 0 | 0 | -1 | 0x0 |
| 11 | 100 | 0x08 | 0 | 2 | -1 | 0x0 |
| 12 | 150 | 0x02 | 2 | 0 | -1 | 0x0 |
| 13 | 100 | 0x29 | 1 | 2 | +1 (bit5 set) | 0x0 |
| 14 | 100 | 0x02 | 2 | 0 | -1 | 0x0 |
| 15 | 100 | 0x2d | 1 | 3 | +1 (bit5 set) | 0x0 |

| # | id | seg | start | lateral | count | spacing |
|---|---|---|---|---|---|---|
| 0 | 1 | 0 | 1 | 80 | 30 | 25 |
| 1 | 4 | 0 | 1 | -75 | 30 | 30 |
| 2 | 100 | 1 | 0 | -30 | 1 | 0 |
| 3 | 100 | 1 | 0 | 0 | 1 | 0 |
| 4 | 100 | 1 | 0 | 30 | 1 | 0 |
| 5 | 7 | 3 | 1 | -80 | 30 | 25 |
| 6 | 4 | 3 | 1 | 75 | 30 | 30 |
| 7 | 101 | 4 | 1 | 10 | 1 | 0 |
| 8 | 101 | 5 | 0 | -30 | 1 | 0 |
| 9 | 100 | 5 | 0 | 0 | 1 | 0 |
| 10 | 100 | 5 | 0 | 30 | 1 | 0 |
| 11 | 7 | 7 | 1 | -80 | 30 | 25 |
| 12 | 1 | 7 | 1 | 75 | 25 | 30 |
| 13 | 100 | 8 | 0 | -30 | 1 | 0 |
| 14 | 100 | 8 | 0 | 0 | 1 | 0 |
| 15 | 100 | 8 | 0 | 30 | 1 | 0 |
| 16 | 100 | 9 | 0 | 0 | 1 | 0 |
| 17 | 4 | 10 | 1 | -80 | 30 | 25 |
| 18 | 1 | 10 | 1 | 75 | 30 | 30 |
| 19 | 100 | 12 | 0 | 0 | 1 | 0 |
| 20 | 100 | 13 | 0 | -30 | 1 | 0 |
| 21 | 100 | 13 | 0 | 0 | 1 | 0 |
| 22 | 100 | 13 | 0 | 30 | 1 | 0 |
| 23 | 6 | 13 | 1 | -80 | 10 | 20 |
| 24 | 7 | 13 | 1 | 75 | 10 | 20 |
| 25 | 101 | 14 | 1 | -10 | 1 | 0 |
| 26 | 101 | 14 | 1 | 10 | 1 | 0 |

### track2 @ 0x015096ac: nseg=17 nobj=23 backdrop=0 total length=1650
| seg | len | flags | slope | curv idx | dir | other bits |
|---|---|---|---|---|---|---|
| 0 | 150 | 0x02 | 2 | 0 | -1 | 0x0 |
| 1 | 50 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |
| 2 | 50 | 0x0e | 2 | 3 | -1 | 0x0 |
| 3 | 100 | 0x2c | 0 | 3 | +1 (bit5 set) | 0x0 |
| 4 | 150 | 0x02 | 2 | 0 | -1 | 0x0 |
| 5 | 100 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |
| 6 | 200 | 0x09 | 1 | 2 | -1 | 0x0 |
| 7 | 100 | 0x2d | 1 | 3 | +1 (bit5 set) | 0x0 |
| 8 | 100 | 0x02 | 2 | 0 | -1 | 0x0 |
| 9 | 100 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |
| 10 | 100 | 0x00 | 0 | 0 | -1 | 0x0 |
| 11 | 50 | 0x0d | 1 | 3 | -1 | 0x0 |
| 12 | 50 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |
| 13 | 150 | 0x02 | 2 | 0 | -1 | 0x0 |
| 14 | 100 | 0x2c | 0 | 3 | +1 (bit5 set) | 0x0 |
| 15 | 50 | 0x0c | 0 | 3 | -1 | 0x0 |
| 16 | 50 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |

| # | id | seg | start | lateral | count | spacing |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 1 | 80 | 31 | 25 |
| 1 | 0 | 0 | 1 | -75 | 31 | 30 |
| 2 | 101 | 1 | 1 | -10 | 1 | 0 |
| 3 | 101 | 1 | 1 | 10 | 1 | 0 |
| 4 | 12 | 3 | 1 | -80 | 31 | 25 |
| 5 | 5 | 3 | 1 | 80 | 31 | 25 |
| 6 | 101 | 3 | 1 | 10 | 1 | 0 |
| 7 | 100 | 3 | 0 | 0 | 1 | 0 |
| 8 | 100 | 3 | 0 | 30 | 1 | 0 |
| 9 | 100 | 3 | 0 | -30 | 1 | 0 |
| 10 | 0 | 6 | 1 | 80 | 31 | 25 |
| 11 | 0 | 6 | 1 | -80 | 31 | 35 |
| 12 | 100 | 7 | 0 | -30 | 1 | 0 |
| 13 | 100 | 7 | 0 | 0 | 1 | 0 |
| 14 | 100 | 7 | 0 | 30 | 1 | 0 |
| 15 | 101 | 8 | 1 | -10 | 1 | 0 |
| 16 | 101 | 8 | 1 | 10 | 1 | 0 |
| 17 | 100 | 9 | 0 | 30 | 1 | 0 |
| 18 | 100 | 9 | 0 | -30 | 1 | 0 |
| 19 | 5 | 9 | 1 | 80 | 31 | 25 |
| 20 | 12 | 12 | 1 | -80 | 31 | 25 |
| 21 | 101 | 13 | 1 | -10 | 1 | 0 |
| 22 | 101 | 13 | 1 | 10 | 1 | 0 |

### track3 @ 0x01509744: nseg=15 nobj=22 backdrop=0 total length=1900
| seg | len | flags | slope | curv idx | dir | other bits |
|---|---|---|---|---|---|---|
| 0 | 150 | 0x00 | 0 | 0 | -1 | 0x0 |
| 1 | 100 | 0x32 | 2 | 4 | +1 (bit5 set) | 0x0 |
| 2 | 50 | 0x00 | 0 | 0 | -1 | 0x0 |
| 3 | 100 | 0x0e | 2 | 3 | -1 | 0x0 |
| 4 | 100 | 0x30 | 0 | 4 | +1 (bit5 set) | 0x0 |
| 5 | 200 | 0x02 | 2 | 0 | -1 | 0x0 |
| 6 | 100 | 0x31 | 1 | 4 | +1 (bit5 set) | 0x0 |
| 7 | 400 | 0x01 | 1 | 0 | -1 | 0x0 |
| 8 | 100 | 0x2e | 2 | 3 | +1 (bit5 set) | 0x0 |
| 9 | 150 | 0x02 | 2 | 0 | -1 | 0x0 |
| 10 | 75 | 0x2a | 2 | 2 | +1 (bit5 set) | 0x0 |
| 11 | 75 | 0x06 | 2 | 1 | -1 | 0x0 |
| 12 | 100 | 0x02 | 2 | 0 | -1 | 0x0 |
| 13 | 50 | 0x08 | 0 | 2 | -1 | 0x0 |
| 14 | 150 | 0x32 | 2 | 4 | +1 (bit5 set) | 0x0 |

| # | id | seg | start | lateral | count | spacing |
|---|---|---|---|---|---|---|
| 0 | 101 | 1 | 1 | -10 | 1 | 0 |
| 1 | 101 | 1 | 1 | 10 | 1 | 0 |
| 2 | 11 | 1 | 0 | -80 | 10 | 10 |
| 3 | 100 | 2 | 0 | -30 | 1 | 0 |
| 4 | 100 | 2 | 0 | 0 | 1 | 0 |
| 5 | 10 | 3 | 0 | 80 | 10 | 10 |
| 6 | 11 | 4 | 0 | -80 | 10 | 10 |
| 7 | 101 | 5 | 1 | -10 | 1 | 0 |
| 8 | 101 | 5 | 1 | 10 | 1 | 0 |
| 9 | 11 | 6 | 0 | -80 | 10 | 10 |
| 10 | 100 | 7 | 0 | 30 | 1 | 0 |
| 11 | 100 | 7 | 0 | -30 | 1 | 0 |
| 12 | 6 | 7 | 0 | -80 | 30 | 10 |
| 13 | 6 | 7 | 0 | 80 | 30 | 10 |
| 14 | 11 | 8 | 0 | -80 | 10 | 10 |
| 15 | 11 | 10 | 0 | -80 | 10 | 10 |
| 16 | 101 | 11 | 1 | -10 | 1 | 0 |
| 17 | 101 | 11 | 1 | 10 | 1 | 0 |
| 18 | 10 | 11 | 0 | 80 | 10 | 10 |
| 19 | 101 | 14 | 1 | -10 | 1 | 0 |
| 20 | 101 | 14 | 1 | 10 | 1 | 0 |
| 21 | 11 | 14 | 0 | -80 | 10 | 10 |

### special(mode2) @ 0x015097d4: nseg=12 nobj=22 backdrop=2 total length=1275
| seg | len | flags | slope | curv idx | dir | other bits |
|---|---|---|---|---|---|---|
| 0 | 100 | 0x02 | 2 | 0 | -1 | 0x0 |
| 1 | 100 | 0x2c | 0 | 3 | +1 (bit5 set) | 0x0 |
| 2 | 200 | 0x02 | 2 | 0 | -1 | 0x0 |
| 3 | 150 | 0x29 | 1 | 2 | +1 (bit5 set) | 0x0 |
| 4 | 150 | 0x02 | 2 | 0 | -1 | 0x0 |
| 5 | 75 | 0x32 | 2 | 4 | +1 (bit5 set) | 0x0 |
| 6 | 75 | 0x2c | 0 | 3 | +1 (bit5 set) | 0x0 |
| 7 | 75 | 0x02 | 2 | 0 | -1 | 0x0 |
| 8 | 100 | 0x0d | 1 | 3 | -1 | 0x0 |
| 9 | 100 | 0x0e | 2 | 3 | -1 | 0x0 |
| 10 | 100 | 0x32 | 2 | 4 | +1 (bit5 set) | 0x0 |
| 11 | 50 | 0x01 | 1 | 0 | -1 | 0x0 |

| # | id | seg | start | lateral | count | spacing |
|---|---|---|---|---|---|---|
| 0 | 3 | 0 | 1 | -90 | 20 | 30 |
| 1 | 3 | 0 | 1 | 90 | 20 | 30 |
| 2 | 100 | 1 | 0 | -30 | 1 | 0 |
| 3 | 100 | 1 | 0 | 0 | 1 | 0 |
| 4 | 100 | 1 | 0 | 30 | 1 | 0 |
| 5 | 101 | 2 | 1 | -10 | 1 | 0 |
| 6 | 101 | 2 | 1 | 10 | 1 | 0 |
| 7 | 2 | 2 | 1 | -90 | 10 | 30 |
| 8 | 5 | 2 | 1 | 90 | 30 | 30 |
| 9 | 101 | 4 | 1 | -10 | 1 | 0 |
| 10 | 101 | 4 | 1 | 10 | 1 | 0 |
| 11 | 100 | 5 | 0 | -30 | 1 | 0 |
| 12 | 100 | 5 | 0 | 0 | 1 | 0 |
| 13 | 100 | 5 | 0 | 30 | 1 | 0 |
| 14 | 3 | 7 | 1 | -90 | 30 | 30 |
| 15 | 5 | 7 | 1 | 90 | 30 | 30 |
| 16 | 100 | 9 | 0 | -30 | 1 | 0 |
| 17 | 100 | 9 | 0 | 0 | 1 | 0 |
| 18 | 100 | 9 | 0 | 30 | 1 | 0 |
| 19 | 2 | 9 | 1 | 90 | 20 | 30 |
| 20 | 101 | 10 | 1 | -10 | 1 | 0 |
| 21 | 101 | 10 | 1 | 10 | 1 | 0 |

