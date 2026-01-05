// ============================================================================
// EXTENDED MODULATION OSC HANDLERS
// ============================================================================
//
// Purpose: OSC interface for Python UI to control extended modulation
// Paths: /noise/extmod/add_route, remove_route, set_user_param, clear_all
//
// Part of: Mod Matrix Expansion (MOD_MATRIX_EXPANSION_SPEC_v1.6.1)
// ============================================================================

OSCdef(\extModAddRoute, { |msg|
    var sourceBus = msg[1].asInteger;
    var targetStr = msg[2].asString;
    var depth = msg[3].asFloat;
    var amount = msg[4].asFloat;
    var offset = msg[5].asFloat;
    var polarity = msg[6].asInteger;
    var invert = msg[7].asInteger;
    
    ~addExtModRoute.(sourceBus, targetStr, depth, amount, offset, polarity, invert);
    
    // Auto-start apply task if this is first route
    if(~extModApplyTask.isNil) {
        ~startExtModApplyTask.();
    };
}, '/noise/extmod/add_route');

OSCdef(\extModRemoveRoute, { |msg|
    var sourceBus = msg[1].asInteger;
    var targetStr = msg[2].asString;
    
    ~removeExtModRoute.(sourceBus, targetStr);
    
    // Auto-stop apply task if no routes left
    if(~extTargets.size == 0) {
        ~stopExtModApplyTask.();
    };
}, '/noise/extmod/remove_route');

OSCdef(\extModSetUserParam, { |msg|
    var targetStr = msg[1].asString;
    var value = msg[2].asFloat;
    
    ~setExtModUserParam.(targetStr, value);
}, '/noise/extmod/set_user_param');

OSCdef(\extModClearAll, { |msg|
    ~clearAllExtModRoutes.();
}, '/noise/extmod/clear_all');

"Extended mod OSC handlers loaded".postln;
