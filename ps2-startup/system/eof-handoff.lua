-- Signals ps2-system-boot when the final frame is on screen (keep-open holds it),
-- so SDDM's greeter can start on top of the identical image.
local flag = mp.get_opt("ps2handoff-flag")
mp.observe_property("eof-reached", "bool", function(_, reached)
    if reached and flag then
        local f = io.open(flag, "w")
        if f then f:close() end
    end
end)
