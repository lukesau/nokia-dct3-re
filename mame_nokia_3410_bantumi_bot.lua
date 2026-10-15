-- Bantumi autopilot (NHM-2 v5.46). Plays the game with the phone's keys and
-- logs what a replay needs:
--   "BEV <event> <a> <b> c=<cycles>" every call of the handler
--     bantumi_handler_2e9bc8;
--   "BPER <ms>", "BSND <id>", "BCLOSE" the tick period, the sounds and the
--     game closing back to its menu, as the game asks the framework;
--   "BBOT <key> t=<s>" each key the autopilot presses.
-- Runs on top of the input exerciser, which presses KEYS to reach the game;
-- needs -debug -debugger none.
--
-- env: B_LEVEL       level 1..5, written to the game as New game draws the
--                    board (event 0x0c)
--      B_SEED        seed of the autopilot's own choice of pits (default 1)
--      B_HINT_EVERY  level 1: ask for a hint (*) every this many turns and
--                    sow where it puts the hand (0: never)
--      B_PASS        1: press # on the first turn, which hands the first
--                    move to the phone
--      B_PAUSE_AT    seconds of play: pause (Menu), Continue once and
--                    press 4, which starts the game's timer again
--
-- On the player's turn, with the hand still, it picks a non-empty pit,
-- walks the hand there with 4 and 6, one key at a time, and sows with 5.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local dbg = cpu.debug
local space = cpu.spaces["program"]

local level = tonumber(os.getenv("B_LEVEL") or "1")
local seed = tonumber(os.getenv("B_SEED") or "1")
local hint_every = tonumber(os.getenv("B_HINT_EVERY") or "0")
local pass = os.getenv("B_PASS") == "1"
local pause_at = tonumber(os.getenv("B_PAUSE_AT") or "")

-- The game state is at 0x1272bc (+0x19 the level); its drawing state at
-- 0x12714c (+0x20 the hand's animation).
local ST, UI = 0x1272bc, 0x12714c
dbg:bpset(0x2e9bc8, "1", 'logerror "BEV %x %x %x c=%d\\n",r0,r1,r2,totalcycles; g')
-- The level, at the handler's second instruction (MAME keeps one
-- breakpoint an address) as New game draws the board; and the beans a
-- pit starts with, from the phone's record.
dbg:bpset(0x2e9bca, "r0 == 0xc", string.format('maincpu.pb@%x = %d; logerror "BSETUP %%d %%d\\n",maincpu.pb@%x,maincpu.pb@%x; g',
	ST + 0x19, level, ST + 0x19, ST))
dbg:bpset(0x3b2546, "1", 'logerror "BPER %d\\n",r0; g')
dbg:bpset(0x3b2510, "1", 'logerror "BSND %x\\n",r0; g')
-- The title (0x3eb790): where its small pictures go, s16 x and y each.
dbg:bpset(0x3eb7d6, "1", 'logerror "BTITLE %08x %08x %08x %08x %08x %08x %08x\\n",maincpu.pd@12e1dc,maincpu.pd@12e1e0,maincpu.pd@12e1e4,maincpu.pd@12e1e8,maincpu.pd@12e1ec,maincpu.pd@12e1f0,maincpu.pd@12e1f4; g')
dbg:bpset(0x3b29de, "1", 'logerror "BCLOSE\\n"; g')

local function field(tag, mask)
	for _, f in pairs(machine.ioport.ports[tag].fields) do
		if f.mask == mask then return f end
	end
end
-- The 3410's keypad matrix, as the input exerciser has it.
local keys = {
	["4"] = field(":COL.4", 0x04), ["5"] = field(":COL.3", 0x04), ["6"] = field(":COL.2", 0x04),
	star = field(":COL.4", 0x10), hash = field(":COL.2", 0x10), menu = field(":COL.4", 0x01),
}

local function rb(a) return space:read_u8(a) end
local function turn() return space:read_u32(ST + 0x14) end
local function anim() return space:read_u32(UI + 0x20) end

local held, hold, rest = nil, 0, 0
local target, turns, hinting, pausing, passed = nil, 0, false, nil, false
local start, dumped = nil, false
local function press(name)
	keys[name]:set_value(1)
	held, hold = name, 3
	machine:logerror(string.format("BBOT %s t=%.3f\n", name, machine.time:as_double()))
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
	-- The game is under way once the player's first turn comes.
	if not start then
		if turn() ~= 3 or rb(UI + 1) ~= 0 then return end
		start = t
	end
	if not dumped then
		-- The hands' descriptors in RAM: open bottom, open top, closed top,
		-- closed bottom.
		dumped = true
		for _, a in ipairs({ UI + 0x44, UI + 0x5c, UI + 0x74, UI + 0x8c }) do
			local bytes = {}
			for i = 0, 23 do bytes[#bytes + 1] = string.format("%02x", rb(a + i)) end
			machine:logerror(string.format("BDESC %x %s\n", a, table.concat(bytes, " ")))
		end
	end
	if pause_at and t - start >= pause_at and not pausing then pausing = 0 end
	if pausing then
		-- Menu pauses into the game's menu with Continue first; Menu again
		-- picks it. The game then stands still until a key: 4.
		pausing = pausing + 1
		if pausing == 1 or pausing == 60 then press("menu") end
		if pausing == 120 then pause_at, pausing = nil, nil; press("4") end
		return
	end
	if turn() ~= 3 or anim() ~= 0 then
		if turn() ~= 6 then hinting = false end
		return
	end
	if pass and not passed then
		passed = true
		return press("hash")
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
