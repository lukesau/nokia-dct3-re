-- No Answer is scheduled for this organically ringing call.
local source = debug.getinfo(1, 'S').source:sub(2)
dofile(assert(source:match('^(.*[/])')) .. 'noki8890_sip_call_restore.lua')
