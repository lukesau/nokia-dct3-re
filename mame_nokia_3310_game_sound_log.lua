-- Logs the sounds the 3310's games play, in MAME's error.log: "GEV <game>
-- <event>" for every event a game is handed, "GSND <class> <id>" for every
-- sound asked of the tone task, next to the buzzer lines -verbose gives.
-- Runs on top of the input exerciser; needs -debug -debugger none.
-- NHM-5 v6.39 only.
--
-- The phone comes up with the games' sounds off twice over: Games,
-- Settings, Sounds (0x111505), and the profile's Warning and game tones,
-- which the tone task keeps as the switch of its tone class 0 (0x11073a).
-- Both are switched on here, in RAM.
--
-- NOKIA_3310_GAME_SOUND_AS=1a,1f plays those ids in place of the first
-- sounds a game asks for, to hear sounds a scripted run does not reach.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local dbg = manager.machine.devices[":maincpu"].debug
-- games_dispatch_2dbd2a(game id, event)
dbg:bpset(0x2dbd2a, "1", 'maincpu.pb@111505=1; maincpu.pb@11073a=1; logerror "GEV %x %x\\n",r0,r1; g')
-- sound_play_2ec8ca(0, class, id); games pass class 0xf1
local swap, n = "", 0
for id in (os.getenv("NOKIA_3310_GAME_SOUND_AS") or ""):gmatch("%x+") do
	swap = swap .. string.format("(temp0==%d)*0x%s+", n, id)
	n = n + 1
end
if n > 0 then
	dbg:bpset(0x2ec8ca, "r1==0xf1", string.format("r2=%s(temp0>=%d)*r2; temp0=temp0+1; g", swap, n))
end
dbg:bpset(0x2ec8d2, "1", 'logerror "GSND %x %x\\n",r6,r5; g')
