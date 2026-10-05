-- Snake II runtime probe (NHM-2 v5.46). Logs the handler's events with CPU
-- cycle counts ("SEV <event> <a> <b> c=<cycles>"), the calls that set the
-- tick period ("SPER <ms>") and two framework calls the tick makes on a
-- meal and a death ("SCALL <addr> <r0>"), and, per frame, changes of the
-- game state ("S3 t=..."). An optional autopilot steers to the food by
-- writing the pending direction (state+0x528) between ticks, logging each
-- write as "S3KEY d" (0 left, 1 up, 2 right, 3 down).
-- env: S3_AUTO=1, S3_AUTO_FROM (s), S3_DIE_AFTER (foods),
--      S3_IGNORE_CREATURE=1, S3_SAVE_ONCE=1 (as the 3310 probe's)
-- Requires: -debug -debugger none -log
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local dbg = cpu.debug
local space = cpu.spaces["program"]

-- The ANSI C generator's state is at 0x12ebac.
dbg:bpset(0x24f8ec, "1", 'logerror "SEV %x %x %x c=%d seed=%x\\n",r0,r1,r2,totalcycles,maincpu.pd@12ebac; g')
dbg:bpset(0x3b2546, "1", 'logerror "SPER %d c=%d\\n",r0,totalcycles; g')
dbg:bpset(0x3b2510, "1", 'logerror "SCALL 3b2510 %x c=%d\\n",r0,totalcycles; g')
dbg:bpset(0x3b25d4, "1", 'logerror "SCALL 3b25d4 %x c=%d\\n",r0,totalcycles; g')

local GLOBALS = 0x12e238
local function rb(a) return space:read_u8(a) end
local function s8(v) if v > 127 then return v - 256 end return v end
local function state() return space:read_u32(GLOBALS + 0x10) end

local auto = os.getenv("S3_AUTO") == "1"
local auto_from = tonumber(os.getenv("S3_AUTO_FROM") or "0") or 0
local die_after = tonumber(os.getenv("S3_DIE_AFTER") or "")
local ignore_creature = os.getenv("S3_IGNORE_CREATURE") == "1"
local save_once = os.getenv("S3_SAVE_ONCE") == "1"
local saved = false
local foods = 0
local lastfood = nil
local last = ""
local dx = {[0] = -1, 0, 1, 0}
local dy = {[0] = 0, -1, 0, 1}

emu.register_frame_done(function()
	local t = machine.time:as_double()
	local S = state()
	if S == 0 or S < 0x100000 or S >= 0x180000 then return end
	if rb(GLOBALS + 3) ~= 6 then return end
	local w, h = rb(S + 0xc), rb(S + 0xd)
	if w == 0 or h == 0 then return end
	local occ_at = space:read_u32(S + 8)
	local function occ(x, y)
		if occ_at == 0 then return true end
		return ((rb(occ_at + (y >> 3) * w + x) >> (y & 7)) & 1) == 1
	end
	local hx, hy = s8(rb(S + 0x4e4)), s8(rb(S + 0x4e5))
	local fx, fy = s8(rb(S + 0x4f4)), s8(rb(S + 0x4f5))
	local bx, by = s8(rb(S + 0x4f8)), s8(rb(S + 0x4f9))
	local cur = rb(S + 0x4ee)
	local line = string.format(
		"h=%d,%d d=%d f=%d,%d b=%d,%d cnt=%d out=%d crash=%d blink=%d score=%d tail=%d head=%d per=%d lvl=%d mode=%d maze=%d",
		hx, hy, cur, fx, fy, bx, by, rb(S + 0x525), rb(S + 0x527), rb(S + 0x521), rb(S + 0x52a),
		space:read_u32(S), space:read_u16(S + 0x4e8), space:read_u16(S + 0x4ea), space:read_u16(S + 0x516),
		rb(S + 0x51c), rb(S + 0x51b), (space:read_u32(S + 0x10) - 0x497458) // 12)
	if line ~= last then
		machine:logerror(string.format("S3 t=%.6f %s\n", t, line))
		last = line
	end
	if not auto or t < auto_from or hx < 0 then return end
	if lastfood and (fx ~= lastfood[1] or fy ~= lastfood[2]) then foods = foods + 1 end
	lastfood = {fx, fy}

	local function bfs(tx, ty)
		local seen, q = {}, {}
		for d = 0, 3 do
			if d ~= (cur + 2) % 4 then
				local nx, ny = (hx + dx[d]) % w, (hy + dy[d]) % h
				if not occ(nx, ny) and not seen[ny * w + nx] then
					seen[ny * w + nx] = true
					q[#q + 1] = {nx, ny, d}
				end
			end
		end
		local i = 1
		while i <= #q do
			local x, y, d0 = q[i][1], q[i][2], q[i][3]
			if x == tx and y == ty then return d0 end
			for d = 0, 3 do
				local nx, ny = (x + dx[d]) % w, (y + dy[d]) % h
				if not occ(nx, ny) and not seen[ny * w + nx] then
					seen[ny * w + nx] = true
					q[#q + 1] = {nx, ny, d0}
				end
			end
			i = i + 1
		end
		return nil
	end
	local function free_turn(want_occupied)
		local pick
		for d = 0, 3 do
			if d ~= (cur + 2) % 4 then
				local nx, ny = (hx + dx[d]) % w, (hy + dy[d]) % h
				if occ(nx, ny) == want_occupied then pick = d end
			end
		end
		return pick
	end

	local want
	local crash = rb(S + 0x521)
	if crash == 1 and save_once and not saved then
		want = free_turn(false)
		if want ~= nil then
			saved = true
			foods = 0
			space:write_u8(S + 0x528, want)
			machine:logerror(string.format("S3KEY %d\n", want))
		end
		return
	end
	if crash ~= 0 then return end
	if die_after and foods >= die_after then
		want = free_turn(true)
		if want == nil then want = (cur + 1) % 4 end
	else
		if rb(S + 0x527) == 1 and bx >= 0 and not ignore_creature then want = bfs(bx, by) end
		if want == nil and fx >= 0 then want = bfs(fx, fy) end
		if want == nil then want = free_turn(false) end
	end
	if want ~= nil and rb(S + 0x528) ~= want then
		space:write_u8(S + 0x528, want)
		machine:logerror(string.format("S3KEY %d\n", want))
	end
end)
