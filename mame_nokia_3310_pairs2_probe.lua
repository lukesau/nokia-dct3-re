-- Logs Pairs II events, returns and state in error.log. Needs -debug -debugger none.
local script_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "."
dofile(script_dir .. "/mame_nokia_dct3_input_exerciser.lua")
local dbg = manager.machine.devices[":maincpu"].debug
-- games_dispatch_2dbd2a(game id, event): also switch the games' sounds on
dbg:bpset(0x2dbd2a, "1", 'maincpu.pb@111505=1; maincpu.pb@10fa94=0; maincpu.pb@11073a=1; logerror "GEV %x %x lvl=%x opt=%x\\n",r0,r1,maincpu.pb@11122e,maincpu.pb@11122f; g')
-- return from pairs2_handler_2da004 into the dispatcher
dbg:bpset(0x2dbd8a, "1", 'logerror "GRET %x phase=%x time=%x cnt=%x sel=%x cur=%x first=%x lvl=%x mode=%x run=%x bar=%x per=%x score=%x ncards=%x cards=%x,%x,%x,%x,%x,%x,%x,%x\\n",r0,maincpu.pb@10919d,maincpu.pw@109190,maincpu.pb@109193,maincpu.pb@10919a,maincpu.pb@109196,maincpu.pb@109197,maincpu.pb@10919b,maincpu.pb@1091a1,maincpu.pb@1091a2,maincpu.pb@109195,maincpu.pw@111224,maincpu.pd@111228,maincpu.pb@109192,maincpu.pb@1091b4,maincpu.pb@1091c8,maincpu.pb@1091dc,maincpu.pb@1091f0,maincpu.pb@109204,maincpu.pb@109218,maincpu.pb@10922c,maincpu.pb@109240; g')
dbg:bpset(0x2ec8d2, "1", 'logerror "GSND %x %x\\n",r6,r5; g')
