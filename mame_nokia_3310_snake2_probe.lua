-- Snake II runtime probe (NHM-5 v6.39). Logs handler events with CPU cycle
-- counts (SNK/SRET), sounds (GSND), vibration calls (GVIB), and, per frame,
-- changes of head cell / score / food / creature (S2 t=...). Optional
-- autopilot steers to the food (and creature) by writing the pending
-- direction (state+0x2a3) between ticks, logging each write as "S2KEY d".
-- env: S2_LEVEL (1..9), S2_MAZE (0..5), S2_TOP (top score to plant),
--      S2_AUTO=1, S2_AUTO_FROM (s), S2_DIE_AFTER (foods), S2_BONUS16=1,
--      S2_IGNORE_CREATURE=1 (leave creatures to run out),
--      S2_SAVE_ONCE=1 (the first time the snake is blocked, turn it free in
--      its one short tick instead of letting it die)
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local dbg = cpu.debug
local space = cpu.spaces["program"]
local lvl = tonumber(os.getenv("S2_LEVEL") or "")
local maze = tonumber(os.getenv("S2_MAZE") or "")
local top = tonumber(os.getenv("S2_TOP") or "")
local pre = 'maincpu.pb@111505=1; maincpu.pb@11073a=1; maincpu.pb@111506=1; maincpu.pb@11fcbd=1; '
local rec = ''
if lvl then rec = rec .. string.format('maincpu.pb@10f9e4=%x; ', lvl - 1) end
if maze then rec = rec .. string.format('maincpu.pb@10fa08=%x; ', maze) end
if top then rec = rec .. string.format('maincpu.pw@10f9e2=%x; ', top) end
dbg:bpset(0x2dbd2a, "1", pre .. rec .. 'logerror "GEV %x %x c=%d\\n",r0,r1,totalcycles; g')
dbg:bpset(0x275aa4, "1", 'logerror "SNK ev=%x c=%d per=%d one=%d score=%d lvl=%x maze=%x\\n",r0,totalcycles,maincpu.pw@(r1+0xc),maincpu.pw@(r1+0xe),maincpu.pd@(r1+0x10),maincpu.pb@(r1+0x16),maincpu.pb@(r1+0x17); g')
dbg:bpset(0x276642, "1", 'logerror "SRET %x snd=%x c=%d\\n",r7,maincpu.pw@11122c,totalcycles; g')
dbg:bpset(0x2ec8d2, "1", 'logerror "GSND %x %x\\n",r6,r5; g')
dbg:bpset(0x2dd70e, "1", 'logerror "GVIB\\n"; g')
if os.getenv("S2_BONUS16") == "1" then
	dbg:bpset(0x275da0, "maincpu.pb@10cc5b==0 && maincpu.pb@10cc5d==0", "maincpu.pb@10cc5b=0x10; g")
end

local ST = 0x10c9bc
local function s8(v) if v > 127 then return v - 256 end return v end
local function rb(a) return space:read_u8(a) end
local last = ""
local auto = os.getenv("S2_AUTO") == "1"
local auto_from = tonumber(os.getenv("S2_AUTO_FROM") or "17") or 17
local die_after = tonumber(os.getenv("S2_DIE_AFTER") or "")
local foods = 0
local ignore_creature = os.getenv("S2_IGNORE_CREATURE") == "1"
local save_once = os.getenv("S2_SAVE_ONCE") == "1"
local saved = false
local lastfood = nil
local dx = {[0] = -1, 0, 1, 0}
local dy = {[0] = 0, -1, 0, 1}

local function occ(x, y)
	local p = space:read_u32(ST + 0x274)
	if p == 0 then return true end
	local b = rb(p + (y >> 3) * 20 + x)
	return ((b >> (y & 7)) & 1) == 1
end

local function bfs(hx, hy, cur, tx, ty)
	-- returns first direction of a shortest free path to (tx, ty), or nil
	local seen = {}
	local q = {}
	for d = 0, 3 do
		if d ~= (cur + 2) % 4 then
			local nx, ny = (hx + dx[d]) % 20, (hy + dy[d]) % 9
			if not occ(nx, ny) and not seen[ny * 20 + nx] then
				seen[ny * 20 + nx] = true
				q[#q + 1] = {nx, ny, d}
			end
		end
	end
	local i = 1
	while i <= #q do
		local x, y, d0 = q[i][1], q[i][2], q[i][3]
		if x == tx and y == ty then return d0 end
		for d = 0, 3 do
			local nx, ny = (x + dx[d]) % 20, (y + dy[d]) % 9
			if not occ(nx, ny) and not seen[ny * 20 + nx] then
				seen[ny * 20 + nx] = true
				q[#q + 1] = {nx, ny, d0}
			end
		end
		i = i + 1
	end
	return nil
end

emu.register_frame_done(function()
	local t = machine.time:as_double()
	if t < 15 then return end
	local hx, hy = s8(rb(ST + 8)), s8(rb(ST + 9))
	local fx, fy = s8(rb(ST + 0x27c)), s8(rb(ST + 0x27d))
	local bx, by = s8(rb(ST + 0x284)), s8(rb(ST + 0x285))
	local score = space:read_u32(0x111228)
	local cnt = rb(ST + 0x29f)
	local cur = rb(ST + 0x10)
	local s = string.format("h=%d,%d d=%d f=%d,%d b=%d,%d cnt=%d act=%d big=%d crash=%d score=%d tail=%d head=%d per=%d",
		hx, hy, cur, fx, fy, bx, by, cnt, rb(ST + 0x2a1), rb(ST + 0x2ab), rb(ST + 0x2a2), score,
		space:read_u16(ST), space:read_u16(ST + 2), space:read_u16(0x111224))
	if s ~= last then
		machine:logerror(string.format("S2 t=%.6f %s\n", t, s))
		last = s
	end
	if not auto or t < auto_from then return end
	if lastfood and (fx ~= lastfood[1] or fy ~= lastfood[2]) then foods = foods + 1 end
	lastfood = {fx, fy}
	if hx < 0 then return end
	local want
	if rb(ST + 0x2a2) == 1 and save_once and not saved then
		for d = 0, 3 do
			if d ~= (cur + 2) % 4 then
				local nx, ny = (hx + dx[d]) % 20, (hy + dy[d]) % 9
				if not occ(nx, ny) then want = d end
			end
		end
		if want ~= nil then
			saved = true
			foods = 0
			space:write_u8(ST + 0x2a3, want)
			machine:logerror(string.format("S2KEY %d\n", want))
		end
		return
	end
	if rb(ST + 0x2a2) ~= 0 then return end
	if die_after and foods >= die_after then
		-- turn into the body if possible
		for d = 0, 3 do
			if d ~= (cur + 2) % 4 then
				local nx, ny = (hx + dx[d]) % 20, (hy + dy[d]) % 9
				if occ(nx, ny) then want = d end
			end
		end
		if want == nil then want = (cur + 1) % 4 end
	else
		if rb(ST + 0x2a1) == 1 and bx >= 0 and not ignore_creature then want = bfs(hx, hy, cur, bx, by) end
		if want == nil and fx >= 0 then want = bfs(hx, hy, cur, fx, fy) end
		if want == nil then
			for d = 0, 3 do
				if d ~= (cur + 2) % 4 then
					local nx, ny = (hx + dx[d]) % 20, (hy + dy[d]) % 9
					if not occ(nx, ny) then want = d end
				end
			end
		end
	end
	if want ~= nil and rb(ST + 0x2a3) ~= want then
		space:write_u8(ST + 0x2a3, want)
		-- What a key would have done: a replay hands the game the key
		-- for this direction here (never the way back, which a key
		-- could not do either).
		machine:logerror(string.format("S2KEY %d\n", want))
	end
end)
