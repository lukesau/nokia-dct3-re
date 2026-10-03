-- Pairs II autopilot (NHM-5 v6.39): plays the game by pressing the phone's
-- keys, reading the board from RAM, and logs what the probe logs (every
-- event "GEV", every return "GRET", sounds "GSND") so that a replay can
-- hand a port the same events. Runs on top of the input exerciser, which
-- presses KEYS to reach the game; needs -debug -debugger none.
--
-- env: P2_LEVEL      level 1..7 for both modes (written to their records)
--      P2_MISS_EVERY open a wrong card every this many pairs (0: never)
--      P2_STOP_BOARD  Time trial: stop playing on this board, so that the
--                     time runs out
--      P2_PAUSE_AT    seconds: pause into the menu and Continue once
--
-- It steers with all four cursor keys, taking the shortest way to the
-- card it wants, and opens cards with 5. It presses a key only once the
-- LCD has shown the last tick's change, which takes the phone 0 to 170 ms,
-- and at least 130 ms before the next tick, so that each picture is on the
-- LCD whole before the next change and every picture can be compared; at
-- level 7's 100 ms there is no such time, so play it at 1 to 6. The
-- exerciser counts the LCD's changes in nokia_dct3_lcd_dumps. It logs
-- each tick it sees as TICK with the time. Bytes of padding after the
-- game's state (0x1096f0..0x1096f2) carry "a game is under way", the last
-- return code and a count of ticks from the debugger to this script.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local dbg = cpu.debug
local space = cpu.spaces["program"]

local level = tonumber(os.getenv("P2_LEVEL") or "1")
local miss_every = tonumber(os.getenv("P2_MISS_EVERY") or "0")
local stop_board = tonumber(os.getenv("P2_STOP_BOARD") or "99")
local pause_at = tonumber(os.getenv("P2_PAUSE_AT") or "")

local FLAG, LAST = 0x1096f0, 0x1096f1
local rec = string.format('maincpu.pb@10fa68=%x; maincpu.pb@10fa94=%x; ', level - 1, level - 1)
-- games_dispatch_2dbd2a(game id, event): sounds on, the level, the flag
dbg:bpset(0x2dbd2a, "1", 'maincpu.pb@111505=1; maincpu.pb@11073a=1; ' .. rec ..
	'maincpu.pb@1096f0=maincpu.pb@1096f0|(((r0==3)||(r0==4))&&(r1==0x2b)); ' ..
	'maincpu.pb@1096f2=maincpu.pb@1096f2+(((r0==3)||(r0==4))&&(r1==1)); ' ..
	'logerror "GEV %x %x lvl=%x opt=%x\\n",r0,r1,maincpu.pb@11122e,maincpu.pb@11122f; g')
-- the return from pairs2_handler_2da004 into the dispatcher
dbg:bpset(0x2dbd8a, "1", 'maincpu.pb@1096f1=r0; maincpu.pb@1096f0=maincpu.pb@1096f0&(r0!=0x18); ' ..
	'logerror "GRET %x phase=%x time=%x board=%x score=%x\\n",r0,maincpu.pb@10919d,maincpu.pw@109190,maincpu.pb@10919b,maincpu.pd@111228; g')
dbg:bpset(0x2ec8d2, "1", 'logerror "GSND %x %x\\n",r6,r5; g')

local function field(tag, mask)
	for _, f in pairs(machine.ioport.ports[tag].fields) do
		if f.mask == mask then return f end
	end
end
local keys = {
	["2"] = field(":COL.3", 0x02), ["4"] = field(":COL.4", 0x04), ["5"] = field(":COL.3", 0x04),
	["6"] = field(":COL.2", 0x04), ["8"] = field(":COL.3", 0x08), menu = field(":COL.3", 0x10),
}

local ST = 0x109190
local function rb(a) return space:read_u8(a) end
local function card(i, off) return rb(ST + 0x24 + 20 * i + off) end

local held, hold, rest = nil, 0, 0
local ticks_seen, since_tick = 0, 0
-- The LCD's changes before the last tick, and at the end of the last frame:
-- a tick can be drawn in the frame it comes in.
local dumps_at_tick, dumps_last_frame = 0, 0
local pairs_done, pausing = 0, nil
-- After Continue the phone waits for a key; outside play the game ignores
-- it, so one is pressed there just to go on.
local nudge = false
local function press(name)
	keys[name]:set_value(1)
	held, hold = name, 3
	machine:logerror(string.format("BOT %s t=%.3f\n", name, machine.time:as_double()))
end

-- Steps from `from` to `to` with a key, or a large number.
local function steps(from, to, n, key)
	local at, k = from, 0
	local order, place = {}, 0
	if key == "2" or key == "8" then
		for i = 0, n - 1 do order[i] = rb(ST + 0x524 + i) end
		while order[place] ~= from do place = place + 1 end
	end
	while k < 200 do
		repeat
			if key == "6" then at = (at + 1) % n
			elseif key == "4" then at = (at + n - 1) % n
			elseif key == "8" then place = (place + 1) % n; at = order[place]
			else place = (place + n - 1) % n; at = order[place] end
		until card(at, 2) == 0
		k = k + 1
		if at == to then return k end
	end
	return 1000
end

emu.register_frame_done(function()
	local ticks = rb(0x1096f2)
	if ticks ~= ticks_seen then
		ticks_seen, since_tick = ticks, 0
		dumps_at_tick = dumps_last_frame
		machine:logerror(string.format("TICK t=%.4f\n", machine.time:as_double()))
	else
		since_tick = since_tick + 1
	end
	dumps_last_frame = nokia_dct3_lcd_dumps or 0
	if held then
		hold = hold - 1
		if hold == 0 then keys[held]:clear_value(); held = nil; rest = 3 end
		return
	end
	if rest > 0 then rest = rest - 1; return end
	if rb(FLAG) ~= 1 then return end
	local t = machine.time:as_double()
	if pause_at and t >= pause_at and not pausing then pausing = 0 end
	if pausing then
		-- Menu pauses, Menu again picks Continue, then any key goes on:
		-- the game's next key, as if a tick had just been shown.
		pausing = pausing + 1
		if pausing == 1 or pausing == 60 then press("menu") end
		if pausing == 120 then pause_at, pausing, since_tick, dumps_at_tick, nudge = nil, nil, 0, -1, true end
		return
	end
	if rb(ST + 0xd) ~= 4 then
		if nudge then nudge = false; press("6") end
		return
	end
	nudge = false
	-- The tick period in ms, from the context; 0 after Continue, when the
	-- tick starts again at the next key. A key's change is on the LCD 30 to
	-- 100 ms after it is pressed.
	local period_frames = space:read_u16(0x111224) * 60 // 1000
	if (nokia_dct3_lcd_dumps or 0) == dumps_at_tick then return end
	if period_frames > 0 and since_tick > period_frames - 8 then return end
	if rb(ST + 0x11) == 0 and rb(ST + 0xb) >= stop_board then return end
	local n, cur, open = rb(ST + 2), rb(ST + 6), rb(ST + 0xa)
	if open == 2 then return press("6") end
	if open == 0 then return press("5") end
	if open ~= 1 then return end
	local first = rb(ST + 7)
	local target
	if miss_every > 0 and (pairs_done + 1) % miss_every == 0 then
		target = cur
		pairs_done = pairs_done + 1
	else
		for i = 0, n - 1 do
			if i ~= first and card(i, 2) == 0 and card(i, 0) == card(first, 0) then target = i end
		end
	end
	if target == nil or target == cur then
		if target ~= nil and card(cur, 0) == card(first, 0) then pairs_done = pairs_done + 1 end
		return press("5")
	end
	local best, best_key = 1000, "6"
	for _, key in ipairs({ "6", "4", "8", "2" }) do
		local s = steps(cur, target, n, key)
		if s < best then best, best_key = s, key end
	end
	press(best_key)
end)
