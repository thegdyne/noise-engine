/*
Mod Routing OSC Handlers
Receives routing commands from Python and applies them via mod_apply.scd

OSC Paths:
  /noise/mod/route/add     [source_bus, slot, param, depth]
  /noise/mod/route/remove  [source_bus, slot, param]
  /noise/mod/route/depth   [source_bus, slot, param, depth]
  /noise/mod/route/enable  [source_bus, slot, param, enabled]

Depends on: mod_apply.scd (~addModRoute, ~removeModRoute, ~setModRouteDepth)
*/

~setupModRouting = {
    "Setting up mod routing OSC handlers...".postln;
    
    // Add a mod route: source_bus → slot.param @ depth
    OSCdef(\modRouteAdd, { |msg|
        var sourceBus = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        var depth = msg[4].asFloat;
        
        ("OSC: Add route bus " ++ sourceBus ++ " → slot " ++ targetSlot ++ " " ++ targetParam ++ " @ " ++ depth).postln;
        ~addModRoute.(sourceBus, targetSlot, targetParam.asSymbol, depth);
    }, '/noise/mod/route/add');
    
    // Remove a mod route
    OSCdef(\modRouteRemove, { |msg|
        var sourceBus = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        
        ("OSC: Remove route bus " ++ sourceBus ++ " → slot " ++ targetSlot ++ " " ++ targetParam).postln;
        ~removeModRoute.(sourceBus, targetSlot, targetParam.asSymbol);
    }, '/noise/mod/route/remove');
    
    // Update route depth
    OSCdef(\modRouteDepth, { |msg|
        var sourceBus = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        var depth = msg[4].asFloat;
        
        ~setModRouteDepth.(sourceBus, targetSlot, targetParam.asSymbol, depth);
    }, '/noise/mod/route/depth');
    
    // Enable/disable route (removes synth but keeps base value stored)
    OSCdef(\modRouteEnable, { |msg|
        var sourceBus = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        var enabled = msg[4].asInteger == 1;
        
        if(enabled) {
            // Re-add with stored depth (default 0.5 if not found)
            var key = "%_%_%".format(sourceBus, targetSlot, targetParam);
            var depth = ~modRouteDepths[key] ?? 0.5;
            ~addModRoute.(sourceBus, targetSlot, targetParam.asSymbol, depth);
        } {
            // Store depth before removing
            var key = "%_%_%".format(sourceBus, targetSlot, targetParam);
            var synth = ~modRouteSynths[key];
            if(synth.notNil) {
                // We can't easily read depth back, so just remove
                ~removeModRoute.(sourceBus, targetSlot, targetParam.asSymbol);
            };
        };
    }, '/noise/mod/route/enable');
    
    // Storage for depths when disabled (to restore on re-enable)
    ~modRouteDepths = Dictionary.new;
    
    "  ✓ Mod routing OSC handlers ready".postln;
};
