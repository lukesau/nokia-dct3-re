-- Bantumi autopilot (NHM-5 v6.39): plays the game by pressing the phone's
-- keys and logs every event the game is handed ("GEV 2 <event>"), its
-- returns ("GRET") and sounds ("GSND"), so that a replay can hand a port
-- the same events. Runs on top of the input exerciser, which presses KEYS
-- to reach the game; needs -debug -debugger none.
--
-- env: B_LEVEL       level 1..5 (written to the game's record as it loads)
--      B_SEED        seed of the bot's own choice of pits (default 1)
--      B_HINT_EVERY  level 1: ask for a hint (*) every this many turns and
--                    sow where it puts the hand (0: never)
--      B_PAUSE_AT    seconds: pause into the menu and Continue once
--
-- On the player's turn, with the hand still, it picks a non-empty pit,
-- walks the hand there with 4 and 6, one key at a time, and sows with 5.
-- It leaves the LCD some frames to show each key's change before the next.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local dbg = cpu.debug
local space = cpu.spaces["program"]

local level = tonumber(os.getenv("B_LEVEL") or "1")
local seed = tonumber(os.getenv("B_SEED") or "1")
local hint_every = tonumber(os.getenv("B_HINT_EVERY") or "0")
local pause_at = tonumber(os.getenv("B_PAUSE_AT") or "")

-- games_ctx_load_2dbc7c: the level, from Bantumi's record (+4)
dbg:bpset(0x2dbc7c, "1", string.format("maincpu.pb@10fa3c=%d; g", level - 1))
-- games_dispatch_2dbd2a(game id, event): sounds on
dbg:bpset(0x2dbd2a, "r0==2", 'maincpu.pb@111505=1; maincpu.pb@11073a=1; ' ..
	'logerror "GEV %x %x\\n",r0,r1; g')
dbg:bpset(0x2ec8d2, "1", 'logerror "GSND %x %x\\n",r6,r5; g')

local function field(tag, mask)
	for _, f in pairs(machine.ioport.ports[tag].fields) do
		if f.mask == mask then return f end
	end
end
local keys = {
	["4"] = field(":COL.4", 0x04), ["5"] = field(":COL.3", 0x04), ["6"] = field(":COL.2", 0x04),
	star = field(":COL.4", 0x10), menu = field(":COL.3", 0x10),
}

local ST = 0x10e1f8
local function rb(a) return space:read_u8(a) end
local function turn() return space:read_u32(ST + 0x14) end
local function anim() return space:read_u32(0x10e1bc) end

local held, hold, rest = nil, 0, 0
local target, turns, hinting, pausing = nil, 0, false, nil
local in_game = false
local function press(name)
	keys[name]:set_value(1)
	held, hold = name, 3
	machine:logerror(string.format("BOT %s t=%.3f\n", name, machine.time:as_double()))
end

local function next_random()
	seed = (seed * 1103515245 + 12345) % 2147483648
	return seed // 65536
end

emu.register_frame_done(function()
	if held then
		hold = hold - 1
		if hold == 0 then keys[held]:clear_value(); held = nil; rest = 8 end
		return
	end
	if rest > 0 then rest = rest - 1; return end
	local t = machine.time:as_double()
	-- The game is under way once the player's first turn comes (the RAM
	-- is clear before the game is first played).
	if not in_game then
		if turn() ~= 3 then return end
		in_game = true
	end
	if pause_at and t >= pause_at and not pausing then pausing = 0 end
	if pausing then
		-- Menu pauses, Menu again picks Continue, then a key goes on.
		pausing = pausing + 1
		if pausing == 1 or pausing == 60 then press("menu") end
		if pausing == 120 then pause_at, pausing = nil, nil; press("4") end
		return
	end
	if turn() ~= 3 or anim() ~= 0 then
		if turn() ~= 6 then hinting = false end
		return
	end
	local cursor = rb(ST + 0xe)
	if target == nil then
		turns = turns + 1
		if hint_every > 0 and level == 1 and turns % hint_every == 0 and not hinting then
			hinting = true
			return press("star")
		end
		if hinting then
			-- The hint has put the hand where it would sow.
			hinting = false
			target = cursor
		else
			local choices = {}
			for p = 0, 5 do if rb(ST + p) ~= 0 then choices[#choices + 1] = p end end
			if #choices == 0 then return end
			target = choices[next_random() % #choices + 1]
		end
	end
	if cursor < target then return press("6") end
	if cursor > target then return press("4") end
	target = nil
	press("5")
end)
