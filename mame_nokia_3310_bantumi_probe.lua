-- Bantumi auto-player (NHM-5 v6.39): sets the level from NOKIA_BANTUMI_LEVEL
-- (0-based record value) when the record is loaded, logs as bantumi_log.lua,
-- and when NOKIA_BANTUMI_AUTO=1 turns a tick during the player's turn into a
-- key-5 event on the lowest non-empty pit.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local dbg = manager.machine.devices[":maincpu"].debug
local lvl = os.getenv("NOKIA_BANTUMI_LEVEL")
if lvl then dbg:bpset(0x2dbc7c, "1", string.format("maincpu.pb@10fa3c=%d; g", tonumber(lvl))) end
if os.getenv("NOKIA_BANTUMI_AUTO") == "1" then
	local base = "r0==2 && r1==1 && maincpu.pd@10e20c==3 && maincpu.pd@10e1bc==0"
	for p = 0, 5 do
		local c = base
		for q = 0, p - 1 do c = c .. string.format(" && maincpu.pb@%x==0", 0x10e1f8 + q) end
		c = c .. string.format(" && maincpu.pb@%x!=0", 0x10e1f8 + p)
		dbg:bpset(0x2dbd2a, c, string.format('maincpu.pb@10e206=%d; r1=0xe; logerror "BAUTO %%d pit=%d\\n",frame; g', p, p))
	end
end
dbg:bpset(0x2dbd2a, "r0==2", 'maincpu.pb@111505=1; maincpu.pb@11073a=1; logerror "BEV %d ev=%x turn=%x anim=%x sub=%x\\n",frame,r1,maincpu.pd@10e20c,maincpu.pd@10e1bc,maincpu.pd@10e218; g')
dbg:bpset(0x2b1764, "1", 'logerror "BPIT %d pit=%x n=%x\\n",frame,r0,r1; g')
dbg:bpset(0x2b1ad0, "1", 'logerror "BPICK %d pit=%x turn=%x\\n",frame,r0,maincpu.pd@10e20c; g')
dbg:bpset(0x2b1898, "1", 'logerror "BTURNEND %d arg=%x turn=%x pits=%08x %08x %08x %04x\\n",frame,r0,maincpu.pd@10e20c,maincpu.pd@10e1f8,maincpu.pd@10e1fc,maincpu.pd@10e200,maincpu.pw@10e204; g')
dbg:bpset(0x2dd3bc, "1", 'logerror "BAIINIT %d level=%x turn=%x pits=%08x %08x %08x %04x\\n",frame,maincpu.pb@10e211,maincpu.pd@10e20c,maincpu.pd@10e1f8,maincpu.pd@10e1fc,maincpu.pd@10e200,maincpu.pw@10e204; g')
dbg:bpset(0x2dd5ac, "1", 'logerror "BAISTEP %d depth=%x\\n",frame,maincpu.pb@10f405; g')
dbg:bpset(0x2dd648, "1", 'logerror "BAIDONE %d chosen=%x\\n",frame,maincpu.pb@10f404; g')
dbg:bpset(0x2dd28e, "1", 'logerror "BAICHILD %d pit=%x\\n",frame,r1; g')
dbg:bpset(0x2ec8d2, "1", 'logerror "BSND %d %x %x\\n",frame,r6,r5; g')
dbg:bpset(0x2dbfc6, "1", 'logerror "BGOVER %d ret=%x score=%x\\n",frame,r0,maincpu.pd@111228; g')
