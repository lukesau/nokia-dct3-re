-- Logs the 3310 games' vibrator use, in MAME's error.log: "GVIB <time>
-- <flags>" whenever game_vibrate_2dd70e is entered, with the bytes it
-- checks (Shakes setting 0x111506, 0x11fcbd, 0x111a79, 0x11fe97), and
-- "VIB <time> <state>" whenever the driver's vibration output changes.
-- Runs on top of the input exerciser; needs -debug -debugger none.
-- NHM-5 v6.39 only.
--
-- Games, Settings, Shakes (0x111506) is off on a fresh NVRAM; it is
-- switched on here, in RAM.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local dbg = manager.machine.devices[":maincpu"].debug
dbg:bpset(0x2dbd2a, "1", "maincpu.pb@111506=1; maincpu.pb@11fcbd=1; g")
dbg:bpset(0x2dd70e, "1", 'logerror "GVIB %x %x %x %x %x\\n",maincpu.pb@111506,maincpu.pb@11fcbd,maincpu.pb@111a79,maincpu.pb@11fe97,r0; g')
local last = nil
emu.register_frame_done(function()
	local v = manager.machine.output:get_value("vibration")
	if v ~= last then
		manager.machine:logerror(string.format("VIB %s %d\n", tostring(manager.machine.time), v))
		last = v
	end
end)
