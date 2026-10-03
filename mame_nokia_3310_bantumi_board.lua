-- Bantumi scratch: when NOKIA_BANTUMI_BOARD holds 28 hex digits, replaces the
-- 14 pits on the first intro tick (before the board is drawn), then loads
-- bantumi_auto.lua. Breakpoints at one address: only the first matching one
-- (in creation order) runs, so this one is created first.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
local b = os.getenv("NOKIA_BANTUMI_BOARD")
local function setup()
	local dbg = manager.machine.devices[":maincpu"].debug
	if b and #b == 28 then
		local act = ""
		for i = 0, 13 do act = act .. string.format("maincpu.pb@%x=%d; ", 0x10e1f8 + i, tonumber(b:sub(2*i+1, 2*i+2), 16)) end
		dbg:bpset(0x2dbd2a, "r0==2 && r1==1 && maincpu.pd@10e20c==0 && maincpu.pb@10e17a==0", act .. 'logerror "BBOARD %d\\n",frame; g')
	end
	dbg:bpset(0x2dc03e, "maincpu.pb@11fd57==2 && r0!=1 && r0!=0x21", 'logerror "BRET %d ret=%x ctx10=%x ctxc=%x\\n",frame,r0,maincpu.pd@111228,maincpu.pw@111224; g')
end
setup()
dofile(script_dir .. "/mame_nokia_3310_bantumi_probe.lua")
