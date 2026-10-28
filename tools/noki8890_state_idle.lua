-- Save/load the ordinarily settled idle UI.
local source = debug.getinfo(1, 'S').source:sub(2)
dofile(assert(source:match('^(.*[/])')) .. 'noki8890_state_roundtrip.lua')
