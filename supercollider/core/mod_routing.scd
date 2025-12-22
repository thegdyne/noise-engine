/*
Mod Routing OSC Handlers
Receives routing commands from Python and applies them via mod_apply_v2.scd

OSC Paths:
  /noise/mod/route/add     [source_bus, slot, param, depth, amount, offset, polarity, invert]
  /noise/mod/route/set     [source_bus, slot, param, depth, amount, offset, polarity, invert]
  /noise/mod/route/remove  [source_bus, slot, param]

Parameters:
  depth: 0.0-1.0 (range width)
  amount: 0.0-1.0 (VCA level)
  offset: -1.0-1.0 (shift mod range up/down from base)
  polarity: 0=bipolar, 1=uni+, 2=uni-
  invert: 0=normal, 1=inverted

Depends on: mod_apply_v2.scd (~addModRoute, ~removeModRoute, ~setModRoute)
*/

~setupModRouting = {
    "Setting up mod routing OSC handlers...".postln;
    
    // Add a mod route: source_bus → slot.param with full params
    OSCdef(\modRouteAdd, { |msg|
        var sourceBus = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        var depth = msg[4].asFloat;
        var amount = msg[5].asFloat;
        var offset = msg[6].asFloat;
        var polarity = msg[7].asInteger;
        var invert = msg[8].asInteger;
        
        ("OSC: Add route bus " ++ sourceBus ++ " → slot " ++ targetSlot ++ " " ++ targetParam ++
         " [d=" ++ depth ++ ", a=" ++ amount ++ ", o=" ++ offset ++ ", p=" ++ polarity ++ ", i=" ++ invert ++ "]").postln;
        ~addModRoute.(sourceBus, targetSlot, targetParam.asSymbol, depth, amount, offset, polarity, invert);
    }, '/noise/mod/route/add');
    
    // Set/update mod route params (creates if doesn't exist)
    OSCdef(\modRouteSet, { |msg|
        var sourceBus = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        var depth = msg[4].asFloat;
        var amount = msg[5].asFloat;
        var offset = msg[6].asFloat;
        var polarity = msg[7].asInteger;
        var invert = msg[8].asInteger;
        
        ~setModRoute.(sourceBus, targetSlot, targetParam.asSymbol, depth, amount, offset, polarity, invert);
    }, '/noise/mod/route/set');
    
    // Remove a mod route
    OSCdef(\modRouteRemove, { |msg|
        var sourceBus = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        
        ("OSC: Remove route bus " ++ sourceBus ++ " → slot " ++ targetSlot ++ " " ++ targetParam).postln;
        ~removeModRoute.(sourceBus, targetSlot, targetParam.asSymbol);
    }, '/noise/mod/route/remove');

     // Clear all mod routes
        OSCdef(\modRouteClearAll, { |msg|
            "OSC: Clearing all mod routes".postln;
            ~clearAllModRoutes.();
        }, '/noise/mod/route/clear_all');

    "  ✓ Mod routing OSC handlers ready".postln;
};
