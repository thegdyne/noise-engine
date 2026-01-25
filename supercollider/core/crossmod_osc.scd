/*
Cross-Mod OSC Handlers
Control interface for cross-modulation routing and parameters

OSC Paths:
  /noise/crossmod/attack   [slot, seconds]   - Set envelope follower attack time
  /noise/crossmod/release  [slot, seconds]   - Set envelope follower release time
  /noise/crossmod/enabled  [slot, 0|1]       - Enable/disable cross-mod output for slot
  /noise/crossmod/route    [src, tgt, param, depth, amount, offset, polarity, invert]
  /noise/crossmod/unroute  [src, tgt, param] - Remove a cross-mod route
  /noise/crossmod/clear    []                - Clear all cross-mod routes

Route Semantics:
  /route is IDEMPOTENT - overwrites existing (src,tgt,param) route if present.
  No need to unroute before changing parameters.

Enabled Behavior:
  When disabled (enabled=0): follower synth is FREED (CPU efficient).
  Bus outputs 0 (silence). Routes remain configured but receive 0.
  Re-enabling recreates follower if generator is running.

Parameters:
  src, tgt: slot numbers 1-8
  param: frequency, cutoff, resonance, attack, decay, p1-p5
  depth: 0.0-1.0 (range width)
  amount: 0.0-1.0 (VCA level)
  offset: -1.0-1.0 (shifts mod range up/down from base)
  polarity: 0=bipolar, 1=uni+, 2=uni-
  invert: 0=normal, 1=inverted

Signal Range Note:
  Crossmod sources output UNIPOLAR 0..1 (silence=0, loud=1).
  This differs from LFO/Sloth sources which are bipolar -1..+1.

  The unified bus system polarity logic assumes bipolar sources,
  so crossmod produces half-range results:
    - bipolar: 0..r (positive only, use invert=1 for negative)
    - uni+: 0.5r..r (upper half)
    - uni-: -r..-0.5r (lower half)

  Simplest recipes:
    - Positive mod: bipolar, invert=0 -> silence=0, loud=+r
    - Negative mod (duck): bipolar, invert=1 -> silence=0, loud=-r

Routes use the unified bus system (bus_unification.scd) via ~queueRouteOp.
*/

~setupCrossModOSC = {
    "Setting up cross-mod OSC handlers...".postln;

    // Track active cross-mod routes (for clear operation)
    ~crossModRoutes = Dictionary.new;  // "sourceSlot_targetSlot_param" -> [sourceKey, targetKey]

    // Helper: build source key for crossmod (slot 1-8 -> "crossModBus_0" to "crossModBus_7")
    ~crossModSourceKey = { |slot|
        ("crossModBus_%").format(slot - 1).asSymbol;
    };

    // Helper: build target key for unified bus system
    // Maps param names to unified format
    ~crossModTargetKey = { |targetSlot, targetParam|
        var paramKey = switch(targetParam.asSymbol,
            \frequency, { \freq },
            \cutoff, { \cutoff },
            \resonance, { \res },
            \attack, { \attack },
            \decay, { \decay },
            \p1, { \custom0 },
            \p2, { \custom1 },
            \p3, { \custom2 },
            \p4, { \custom3 },
            \p5, { \custom4 },
            { targetParam.asSymbol }  // fallback
        );
        ("gen_%_%").format(targetSlot, paramKey).asSymbol;
    };
    
    // Set attack time (1ms - 2s)
    OSCdef(\crossModAttack, { |msg|
        var slot = msg[1].asInteger;
        var attack = msg[2].asFloat.clip(0.001, 2.0);
        ~setCrossModAttack.(slot, attack);
    }, '/noise/crossmod/attack');
    
    // Set release time (10ms - 5s)
    OSCdef(\crossModRelease, { |msg|
        var slot = msg[1].asInteger;
        var release = msg[2].asFloat.clip(0.01, 5.0);
        ~setCrossModRelease.(slot, release);
    }, '/noise/crossmod/release');
    
    // Enable/disable cross-mod output for a slot
    OSCdef(\crossModEnabled, { |msg|
        var slot = msg[1].asInteger;
        var enabled = msg[2].asInteger > 0;
        ~setCrossModEnabled.(slot, enabled);
    }, '/noise/crossmod/enabled');
    
    // Route cross-mod: source_slot -> target_slot.param
    // Uses unified bus system via ~queueRouteOp
    OSCdef(\crossModRoute, { |msg|
        var sourceSlot = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        var depth = msg[4].asFloat;
        var amount = msg[5].asFloat;
        var offset = msg[6].asFloat;
        var polarity = msg[7].asInteger;
        var invert = msg[8].asInteger;
        var sourceKey, targetKey, routeKey;

        // Validate slots
        if(sourceSlot < 1 || sourceSlot > 8 || targetSlot < 1 || targetSlot > 8) {
            "ERROR: Invalid slot in cross-mod route (%, %)".format(sourceSlot, targetSlot).postln;
            ^nil;
        };

        // Build unified bus system keys
        sourceKey = ~crossModSourceKey.(sourceSlot);
        targetKey = ~crossModTargetKey.(targetSlot, targetParam);

        ("Cross-mod route: GEN" ++ sourceSlot ++ " (" ++ sourceKey ++ ") -> " ++ targetKey ++
         " [d=" ++ depth ++ ", a=" ++ amount ++ ", o=" ++ offset ++ ", p=" ++ polarity ++ ", i=" ++ invert ++ "]").postln;

        // Queue route via unified bus system
        if(~queueRouteOp.notNil) {
            ~queueRouteOp.(\set, sourceKey, targetKey, depth, amount, offset, polarity, invert);

            // Track for clear operation
            routeKey = "%_%_%".format(sourceSlot, targetSlot, targetParam);
            ~crossModRoutes[routeKey] = [sourceKey, targetKey];
        } {
            "ERROR: ~queueRouteOp not available (bus_unification not loaded?)".postln;
        };
    }, '/noise/crossmod/route');
    
    // Unroute cross-mod
    OSCdef(\crossModUnroute, { |msg|
        var sourceSlot = msg[1].asInteger;
        var targetSlot = msg[2].asInteger;
        var targetParam = msg[3].asString;
        var sourceKey, targetKey, routeKey;

        if(sourceSlot < 1 || sourceSlot > 8 || targetSlot < 1 || targetSlot > 8) {
            "ERROR: Invalid slot in cross-mod unroute".postln;
            ^nil;
        };

        sourceKey = ~crossModSourceKey.(sourceSlot);
        targetKey = ~crossModTargetKey.(targetSlot, targetParam);

        ("Cross-mod unroute: " ++ sourceKey ++ " from " ++ targetKey).postln;

        // Remove via unified bus system
        if(~queueRouteOp.notNil) {
            ~queueRouteOp.(\remove, sourceKey, targetKey, 0, 0, 0, 0, 0);
        };

        // Update tracking
        routeKey = "%_%_%".format(sourceSlot, targetSlot, targetParam);
        ~crossModRoutes.removeAt(routeKey);
    }, '/noise/crossmod/unroute');
    
    // Clear all cross-mod routes
    OSCdef(\crossModClear, { |msg|
        "Clearing all cross-mod routes...".postln;
        if(~queueRouteOp.notNil) {
            ~crossModRoutes.keysValuesDo { |key, routeInfo|
                // routeInfo is [sourceKey, targetKey]
                if(routeInfo.isArray && routeInfo.size >= 2) {
                    ~queueRouteOp.(\remove, routeInfo[0], routeInfo[1], 0, 0, 0, 0, 0);
                };
            };
        };
        ~crossModRoutes.clear;
        "All cross-mod routes cleared".postln;
    }, '/noise/crossmod/clear');
    
    // Debug: dump cross-mod state
    OSCdef(\crossModDebug, { |msg|
        ~debugCrossModFollowers.();
        ~debugCrossModRoutes.();
    }, '/noise/crossmod/debug');
    
    "  [x] Cross-mod OSC handlers ready".postln;
};

// Debug helper
~debugCrossModRoutes = {
    "=== Cross-Mod Routes ===".postln;
    if(~crossModRoutes.size == 0) {
        "  (none active)".postln;
    } {
        ~crossModRoutes.keysValuesDo { |key, routeInfo|
            var parts = key.asString.split($_);
            if(parts.size >= 3) {
                var sourceSlot = parts[0].asInteger;
                var targetSlot = parts[1].asInteger;
                var targetParam = parts[2];
                if(routeInfo.isArray && routeInfo.size >= 2) {
                    "  GEN% -> slot % % (% -> %)".format(sourceSlot, targetSlot, targetParam, routeInfo[0], routeInfo[1]).postln;
                };
            };
        };
    };
};
