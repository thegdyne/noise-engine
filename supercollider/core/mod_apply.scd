/*
==================================================================================
DEPRECATED (Phase 6 - Bus Unification)
==================================================================================

This file contains the LEGACY modulation routing engine. It is NO LONGER the
primary modulation system.

NEW SYSTEM:
- Generators read modulatable params from unified buses (~busRegistry)
- Modulation is handled by bus_unification.scd apply tick (500Hz)
- Routes are managed via /noise/bus/route/set, /noise/bus/route/remove
- Boid modulation uses /noise/boid/offsets

This file is kept for backward compatibility only. The \modRoute SynthDef and
related functions (~addModRoute, ~removeModRoute, etc.) write to ~genParams
buses which are NO LONGER read by generators for modulatable params.

To use the new system:
- Send params via /noise/bus/base [targetKey, normalizedValue]
- Set routes via /noise/bus/route/set [sourceKey, targetKey, depth, ...]
- Enable boids via /noise/boid/enable [1]

==================================================================================
LEGACY CODE BELOW - DO NOT USE FOR NEW DEVELOPMENT
==================================================================================

Mod Apply - Modulation routing engine
Applies mod bus values to generator parameters

Phase 2: Hardcoded test
Phase 3+: Dynamic routing via OSC

Modulation formula:
  output = base + (modValue * depth * range)

Where:
  - base: Original parameter value (before modulation)
  - modValue: -1 to +1 from mod bus
  - depth: -1 to +1 (negative = inverted)
  - range: Parameter-specific range (e.g. 15980 for cutoff 20-16000Hz)
*/

~setupModApply = {
    "Setting up mod apply...".postln;
    
    // Store base values for modulated params (key: "slot_param")
    ~modBaseValues = Dictionary.new;
    
    // Active modulation synths (key: "sourceBus_targetSlot_param")
    ~modRouteSynths = Dictionary.new;
    
    // Parameter ranges for modulation scaling
    // Format: [min, max] in real units
    ~paramRanges = Dictionary.new;
    ~paramRanges[\cutoff] = [20, 16000];      // Hz (exponential perception)
    ~paramRanges[\frequency] = [20, 8000];    // Hz
    ~paramRanges[\resonance] = [0.1, 1.0];    // rq (inverted: low rq = high res)
    ~paramRanges[\attack] = [0.0001, 2.0];    // seconds
    ~paramRanges[\decay] = [0.01, 10.0];      // seconds
    ~paramRanges[\custom] = [0, 1];           // normalized
    
    // SynthDef for continuous modulation
    // Reads mod bus, applies to param bus with depth scaling
    SynthDef(\modRoute, { |modBus, paramBus, baseValue=0.5, depth=0.5, 
                          minVal=0, maxVal=1, curve=0|
        var modVal, range, offset, outVal;
        
        // Read mod bus (expected -1 to +1 for BI, 0 to 1 for UNI)
        modVal = In.kr(modBus);
        
        // Calculate range
        range = maxVal - minVal;
        
        // Apply modulation: base + (mod * depth * range)
        // depth of 1.0 means full range sweep
        // depth of -1.0 means inverted full range
        offset = modVal * depth * range * 0.5;  // *0.5 because mod is +/-1
        
        // Linear vs exponential curves
        outVal = Select.kr(curve, [
            // Linear (curve=0)
            (baseValue + offset).clip(minVal, maxVal),
            // Exponential (curve=1) - for frequency/cutoff
            (baseValue * (2 ** (modVal * depth * 4))).clip(minVal, maxVal)
        ]);
        
        // Write to param bus
        ReplaceOut.kr(paramBus, outVal);
    }).add;
    
    // Helper to create a mod route
    ~addModRoute = { |sourceBus, targetSlot, targetParam, depth=0.5|
        var key = "%_%_%".format(sourceBus, targetSlot, targetParam);
        var paramBus, baseVal, range, curve;
        
        // Get param bus
        paramBus = ~genParams[targetSlot][targetParam.asSymbol];
        if(paramBus.isNil) {
            ("Mod route: unknown param " ++ targetParam ++ " for slot " ++ targetSlot).warn;
            ^nil;
        };
        
        // Store and get base value
        baseVal = paramBus.getSynchronous;
        ~modBaseValues[key] = baseVal;
        
        // Get range for this param
        range = ~paramRanges[targetParam.asSymbol] ?? [0, 1];
        
        // Exponential curve for frequency-like params
        curve = if([\cutoff, \frequency].includes(targetParam.asSymbol), 1, 0);
        
        // Free existing route if any
        ~modRouteSynths[key].free;
        
        // Create modulation synth
        ~modRouteSynths[key] = Synth(\modRoute, [
            \modBus, ~modBuses[sourceBus].index,
            \paramBus, paramBus.index,
            \baseValue, baseVal,
            \depth, depth,
            \minVal, range[0],
            \maxVal, range[1],
            \curve, curve
        ], ~modGroup, \addAfter);  // Run after mod sources
        
        ("Mod route: bus " ++ sourceBus ++ " -> slot " ++ targetSlot ++ " " ++ targetParam ++ 
         " (base=" ++ baseVal.round(0.01) ++ ", depth=" ++ depth ++ ")").postln;
        
        // Start value stream if this is the first route
        if(~modValueStreamRoutine.isNil) {
            ~startModValueStream.();
        };
    };
    
    // Helper to remove a mod route
    ~removeModRoute = { |sourceBus, targetSlot, targetParam|
        var key = "%_%_%".format(sourceBus, targetSlot, targetParam);
        var paramBus, baseVal;
        
        // Free synth
        ~modRouteSynths[key].free;
        ~modRouteSynths[key] = nil;
        
        // Restore base value
        baseVal = ~modBaseValues[key];
        if(baseVal.notNil) {
            paramBus = ~genParams[targetSlot][targetParam.asSymbol];
            if(paramBus.notNil) {
                paramBus.set(baseVal);
            };
            ~modBaseValues[key] = nil;
        };
        
        ("Mod route removed: bus " ++ sourceBus ++ " -> slot " ++ targetSlot ++ " " ++ targetParam).postln;
        
        // Stop value stream if no more routes
        if(~modRouteSynths.select({ |v| v.notNil }).size == 0) {
            ~stopModValueStream.();
        };
    };
    
    // Helper to update depth
    ~setModRouteDepth = { |sourceBus, targetSlot, targetParam, depth|
        var key = "%_%_%".format(sourceBus, targetSlot, targetParam);
        var synth = ~modRouteSynths[key];
        if(synth.notNil) {
            synth.set(\depth, depth);
        };
    };
    
    // ========================================
    // PHASE 2: HARDCODED TEST
    // ========================================
    
    ~testModulation = {
        "=== MODULATION TEST ===".postln;
        "Routing: MOD1 output A (bus 0) -> GEN1 cutoff @ 50% depth".postln;
        "Make sure GEN1 has a generator loaded (e.g. Subtractive)".postln;
        
        // Route mod bus 0 (MOD1 output A) to gen slot 1 cutoff
        ~addModRoute.(0, 1, \cutoff, 0.5);
        
        "Test active. Change LFO rate to hear sweep speed change.".postln;
        "Run ~stopTestModulation.() to stop.".postln;
    };
    
    ~stopTestModulation = {
        ~removeModRoute.(0, 1, \cutoff);
        "Test modulation stopped.".postln;
    };
    
    // Quick test with adjustable depth
    ~testModDepth = { |depth=0.5|
        ~setModRouteDepth.(0, 1, \cutoff, depth);
        ("Mod depth set to " ++ depth).postln;
    };
    
    // ========================================
    // MODULATION VALUE STREAMING (for UI)
    // ========================================
    
    // Routine to stream modulated values to Python at ~20fps
    ~modValueStreamAddr = NetAddr("127.0.0.1", 57121);  // Python OSC port
    ~modValueStreamRate = 20;  // fps
    
    ~startModValueStream = {
        if(~modValueStreamRoutine.notNil) {
            ~modValueStreamRoutine.stop;
        };
        
        ~modValueStreamRoutine = Routine({
            loop {
                var messages = List.new;
                
                // Collect all active mod routes
                ~modRouteSynths.keysValuesDo { |key, synth|
                    var parts, sourceBus, targetSlot, targetParam, paramBus, currentVal, range, normVal;
                    
                    if(synth.notNil) {
                        // Parse key: "sourceBus_targetSlot_param"
                        parts = key.asString.split($_);
                        if(parts.size >= 3) {
                            sourceBus = parts[0].asInteger;
                            targetSlot = parts[1].asInteger;
                            targetParam = parts[2].asSymbol;
                            
                            // Get current value from param bus
                            paramBus = ~genParams[targetSlot][targetParam];
                            if(paramBus.notNil) {
                                currentVal = paramBus.getSynchronous;
                                
                                // Normalize to 0-1 based on param range
                                range = ~paramRanges[targetParam] ?? [0, 1];
                                normVal = (currentVal - range[0]) / (range[1] - range[0]);
                                normVal = normVal.clip(0, 1);
                                
                                // Add to messages: [targetSlot, targetParam, normVal]
                                messages.add([targetSlot, targetParam.asString, normVal]);
                            };
                        };
                    };
                };
                
                // Send if we have any values
                if(messages.size > 0) {
                    // Flatten for OSC: slot1, param1, val1, slot2, param2, val2, ...
                    var flat = messages.collect({ |m| m }).flatten;
                    ~modValueStreamAddr.sendMsg('/noise/mod/values', *flat);
                };
                
                (1 / ~modValueStreamRate).wait;
            };
        }).play;
        
        "Mod value stream started".postln;
    };
    
    ~stopModValueStream = {
        if(~modValueStreamRoutine.notNil) {
            ~modValueStreamRoutine.stop;
            ~modValueStreamRoutine = nil;
        };
        "Mod value stream stopped".postln;
    };
    
    // Auto-start streaming when first route is added
    // (will be checked in ~addModRoute)
    
    "  [x] Mod apply ready (run ~testModulation.() to test)".postln;
};
