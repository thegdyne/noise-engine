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

    // Legacy ext_mod system (handles send:*, chan:*, mod:* targets)
    ~addExtModRoute.(sourceBus, targetStr, depth, amount, offset, polarity, invert);

    // Auto-start apply task if this is first route
    if(~extModApplyTask.isNil) {
        ~startExtModApplyTask.();
    };

    // NOTE: ext_mod routes are NOT forwarded to unified bus system.
    // ext_mod has its own apply task for legacy targets.
    // Generator modulation uses /noise/bus/route/set directly.
}, '/noise/extmod/add_route');

OSCdef(\extModRemoveRoute, { |msg|
    var sourceBus = msg[1].asInteger;
    var targetStr = msg[2].asString;

    // Legacy ext_mod system
    ~removeExtModRoute.(sourceBus, targetStr);

    // Auto-stop apply task if no routes left
    if(~extTargets.size == 0) {
        ~stopExtModApplyTask.();
    };

    // NOTE: ext_mod routes are NOT forwarded to unified bus system.
}, '/noise/extmod/remove_route');

OSCdef(\extModSetUserParam, { |msg|
    var targetStr = msg[1].asString;
    var value = msg[2].asFloat;

    // Legacy ext_mod system
    ~setExtModUserParam.(targetStr, value);

    // NOTE: ext_mod base values are NOT forwarded to unified bus system.
    // Generator base values use /noise/bus/base directly.
}, '/noise/extmod/set_user_param');

OSCdef(\extModClearAll, { |msg|
    // Legacy ext_mod system only - clears ext_mod routes
    ~clearAllExtModRoutes.();

    // IMPORTANT: Do NOT forward to unified bus system!
    // ext_mod clear should only clear ext_mod routes, not generator routes.
    // Generator routes are managed separately via /noise/bus/route/clear.
}, '/noise/extmod/clear_all');

"Extended mod OSC handlers loaded".postln;
