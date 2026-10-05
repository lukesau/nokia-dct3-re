-- 3410 games probe (NHM-2 v5.46). Logs every call of the five handlers in
-- the table at 0x4c57ec as "H3410 <name> ev=<r0> a=<r1> b=<r2> c=<cycles>",
-- with the boot broadcast 0x3bf990 as "H3410 broadcast".
-- Requires: -debug -debugger none -log
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local dbg = cpu.debug
assert(dbg, "mame_nokia_3410_games_probe.lua needs -debug")

local handlers = {
	{0x24f8ec, "snake2"},
	{0x25c974, "si"},
	{0x2d6d1c, "bumper"},
	{0x2e9bc8, "bantumi"},
	{0x32ae6e, "link5"},
	{0x3bf990, "broadcast"},
}
for _, h in ipairs(handlers) do
	dbg:bpset(h[1], "1", string.format(
		'logerror "H3410 %s ev=%%x a=%%x b=%%x c=%%d\\n",r0,r1,r2,totalcycles; g', h[2]))
end
