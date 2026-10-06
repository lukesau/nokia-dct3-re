-- Space Impact autopilot (NHM-2 v5.46). Plays the game with the phone's keys
-- and logs what a replay needs:
--   "SIEV <event> <a> <b> c=<cycles> seed=<rand state>" every call of the
--     handler si_handler_25c974;
--   "SIPER <ms>", "SISND <id>", "SIVIB <on>" the tick period, sounds and
--     vibrator the game asks the framework for;
--   "SIBOT <key> down|up t=<s>" each key the autopilot presses and lets go.
-- Runs on top of the input exerciser, which presses KEYS to reach the game;
-- needs -debug -debugger none -log.
--
-- env: SI_FIRE_EVERY  frames between shots (default 20; 0 never fires)
--      SI_SPECIAL_AT  seconds of play, comma-separated: fire the special
--      SI_PAUSE_AT    seconds of play: pause (Menu) and Continue once
--      SI_CONTINUE    1: on the continue screen, press 1 to go on
--      SI_IDLE        1: never move, only fire
--
-- The autopilot steers the ship toward the row of the nearest enemy ahead
-- of it by holding 8 (up) or 0 (down) and fires with 1; the keys are held
-- for whole frames and let go between presses, so each press reaches the
-- game as a key event and as the held state it polls.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local dbg = cpu.debug
local space = cpu.spaces["program"]

-- The ANSI C generator's state is at 0x12ebac.
dbg:bpset(0x25c974, "1", 'logerror "SIEV %x %x %x c=%d seed=%x\\n",r0,r1,r2,totalcycles,maincpu.pd@12ebac; g')
dbg:bpset(0x3b2546, "1", 'logerror "SIPER %d c=%d\\n",r0,totalcycles; g')
dbg:bpset(0x3b2510, "1", 'logerror "SISND %x c=%d\\n",r0,totalcycles; g')
dbg:bpset(0x3b25d4, "1", 'logerror "SIVIB %x c=%d\\n",r0,totalcycles; g')

local function field(tag, mask)
	for _, f in pairs(machine.ioport.ports[tag].fields) do
		if f.mask == mask then return f end
	end
end
-- The 3410's keypad matrix, as the input exerciser has it.
local keys = {
	["1"] = field(":COL.2", 0x02), ["3"] = field(":COL.1", 0x10), ["4"] = field(":COL.4", 0x04),
	["6"] = field(":COL.2", 0x04), ["8"] = field(":COL.3", 0x08), ["0"] = field(":COL.2", 0x01),
	menu = field(":COL.4", 0x01),
}

local STATE = 0x11d848
local function rb(a) return space:read_u8(a) end
local function s16(v) if v >= 0x8000 then return v - 0x10000 end return v end
-- A picture's position (type 4 objects keep it at +0x14).
local function pos(pic)
	if pic == 0 then return nil end
	return s16(space:read_u16(pic + 0x14)), s16(space:read_u16(pic + 0x16))
end

local fire_every = tonumber(os.getenv("SI_FIRE_EVERY") or "20")
local specials = {}
for s in (os.getenv("SI_SPECIAL_AT") or ""):gmatch("[^,]+") do specials[#specials + 1] = tonumber(s) end
local pause_at = tonumber(os.getenv("SI_PAUSE_AT") or "")
local go_on = os.getenv("SI_CONTINUE") == "1"
local idle = os.getenv("SI_IDLE") == "1"

local held = {}
local function down(k)
	if held[k] then return end
	keys[k]:set_value(1)
	held[k] = true
	machine:logerror(string.format("SIBOT %s down t=%.3f\n", k, machine.time:as_double()))
end
local function up(k)
	if not held[k] then return end
	keys[k]:clear_value()
	held[k] = nil
	machine:logerror(string.format("SIBOT %s up t=%.3f\n", k, machine.time:as_double()))
end
-- A tap: down for `n` frames, then up.
local taps = {}
local function tap(k, n)
	if held[k] or taps[k] then return end
	down(k)
	taps[k] = n
end

local start, frame, pausing = nil, 0, nil

emu.register_frame_done(function()
	for k, n in pairs(taps) do
		if n <= 1 then up(k); taps[k] = nil else taps[k] = n - 1 end
	end
	local phase = rb(STATE + 0x558)
	if phase ~= 10 and phase ~= 0x14 and phase ~= 0x1e then
		start = nil
		return
	end
	local t = machine.time:as_double()
	if not start then start = t end
	local played = t - start
	frame = frame + 1

	if pausing then
		-- Menu pauses into the game's menu with Continue first; Menu again
		-- picks it.
		pausing = pausing + 1
		if pausing == 2 or pausing == 60 then tap("menu", 3) end
		if pausing == 120 then pausing = nil end
		return
	end
	if pause_at and played >= pause_at then
		pause_at = nil
		up("8"); up("0"); up("1")
		pausing = 0
		return
	end
	if phase == 0x14 then
		up("8"); up("0")
		if go_on and frame % 30 == 0 then tap("1", 3) end
		return
	end
	if phase ~= 10 then
		up("8"); up("0")
		return
	end

	if #specials > 0 and played >= specials[1] then
		table.remove(specials, 1)
		tap("4", 3)
	end
	if fire_every > 0 and frame % fire_every == 0 then tap("1", 3) end
	if idle then return end

	-- The nearest enemy to the right of the ship.
	local sx, sy = pos(space:read_u32(STATE + 0x56c))
	if not sx then return end
	local best, by = nil, nil
	for n = 0, 59 do
		local rec = STATE + 0x90 + n * 20
		local ty = rb(rec + 2)
		if ty ~= 0x7f and ty >= 20 and rb(rec + 0xf) ~= 0x0a then
			local x, y = pos(space:read_u32(rec + 8))
			if x and x > sx and (not best or x < best) then best, by = x, y end
		end
	end
	if not by then up("8"); up("0"); return end
	if by < sy - 1 then up("0"); down("8")
	elseif by > sy + 1 then up("8"); down("0")
	else up("8"); up("0") end
end)
