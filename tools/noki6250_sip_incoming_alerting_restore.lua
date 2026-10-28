-- Withhold physical Answer while restoring an organically ringing handset.
local source = debug.getinfo(1, 'S').source:sub(2)
dofile(assert(source:match('^(.*[/])')) .. 'noki6250_sip_call_restore.lua')
