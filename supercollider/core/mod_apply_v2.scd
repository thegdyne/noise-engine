/*
Mod Apply v2 - Multi-Source Modulation Engine
Supports multiple mod sources targeting the same parameter.

Architecture:
- One \modApply synth per destination (slot+param combo)
- Each synth reads up to 4 mod buses and sums their contributions
- Routes stored in ~modRoutes dictionary

Summation: ADD mode (sum values, clip to range)
*/

~setupModApply = {
    "Setting up mod apply (multi-source)...".postln;
    
    // Routes per destination: "slot_param" -> List of [sourceBus, depth]
    ~modRoutes = Dictionary.new;
    
    // Active combiner synths: "slot_param" -> Synth
    ~modApplySynths = Dictionary.new;
    
    // Base values: "slot_param" -> value (captured when first route added)
    ~modBaseValues = Dictionary.new;
    
    // Parameter ranges for modulation scaling
    ~paramRanges = Dictionary.new;
    ~paramRanges[\cutoff] = [20, 16000];
    ~paramRanges[\frequency] = [20, 8000];
    ~paramRanges[\resonance] = [0.1, 1.0];
    ~paramRanges[\attack] = [0.0001, 2.0];
    ~paramRanges[\decay] = [0.01, 10.0];
    ~paramRanges[\custom] = [0, 1];
    
    // SynthDef for multi-source modulation (up to 4 sources)
    // Reads multiple mod buses, sums contributions, writes to param bus
    SynthDef(\modApply, { |paramBus, baseValue=0.5, minVal=0, maxVal=1, curve=0,
                          bus0=(-1), depth0=0, bus1=(-1), depth1=0,
                          bus2=(-1), depth2=0, bus3=(-1), depth3=0|
        var modVal0, modVal1, modVal2, modVal3;
        var sum, range, offset, outVal;
        
        // Read mod buses (use 0 if bus index is -1 = unused)
        modVal0 = Select.kr(bus0 >= 0, [0, In.kr(bus0)]);
        modVal1 = Select.kr(bus1 >= 0, [0, In.kr(bus1)]);
        modVal2 = Select.kr(bus2 >= 0, [0, In.kr(bus2)]);
        modVal3 = Select.kr(bus3 >= 0, [0, In.kr(bus3)]);
        
        // Sum all contributions (mod * depth)
        sum = (modVal0 * depth0) + (modVal1 * depth1) + 
              (modVal2 * depth2) + (modVal3 * depth3);
        
        // Calculate range
        range = maxVal - minVal;
        
        // Apply summed modulation
        offset = sum * range * 0.5;  // *0.5 because mod is ±1
        
        // Linear vs exponential curves
        outVal = Select.kr(curve, [
            // Linear (curve=0)
            (baseValue + offset).clip(minVal, maxVal),
            // Exponential (curve=1) - for frequency/cutoff
            (baseValue * (2 ** (sum * 4))).clip(minVal, maxVal)
        ]);
        
        // Write to param bus
        ReplaceOut.kr(paramBus, outVal);
    }).add;
    
    // Helper: Get destination key
    ~destKey = { |slot, param|
        "%_%".format(slot, param);
    };
    
    // Helper: Rebuild combiner synth for a destination
    ~rebuildModApply = { |slot, param|
        var destKey = ~destKey.(slot, param);
        var routes = ~modRoutes[destKey];
        var paramBus, baseVal, range, curve;
        var args;
        
        // Free existing synth
        ~modApplySynths[destKey].free;
        ~modApplySynths[destKey] = nil;
        
        // If no routes, restore base value and exit
        if(routes.isNil or: { routes.size == 0 }) {
            baseVal = ~modBaseValues[destKey];
            if(baseVal.notNil) {
                paramBus = ~genParams[slot][param.asSymbol];
                if(paramBus.notNil) { paramBus.set(baseVal) };
            };
            ("Mod apply: cleared for slot " ++ slot ++ " " ++ param).postln;
            ^nil;
        };
        
        // Get param bus
        paramBus = ~genParams[slot][param.asSymbol];
        if(paramBus.isNil) {
            ("Mod apply: unknown param " ++ param ++ " for slot " ++ slot).warn;
            ^nil;
        };
        
        // Get or capture base value
        baseVal = ~modBaseValues[destKey];
        if(baseVal.isNil) {
            baseVal = paramBus.getSynchronous;
            ~modBaseValues[destKey] = baseVal;
        };
        
        // Get range for this param
        range = ~paramRanges[param.asSymbol] ?? [0, 1];
        
        // Exponential curve for frequency-like params
        curve = if([\cutoff, \frequency].includes(param.asSymbol), 1, 0);
        
        // Build synth args
        args = [
            \paramBus, paramBus.index,
            \baseValue, baseVal,
            \minVal, range[0],
            \maxVal, range[1],
            \curve, curve
        ];
        
        // Add up to 4 routes
        routes.do { |route, i|
            if(i < 4) {
                var busKey = ("bus" ++ i).asSymbol;
                var depthKey = ("depth" ++ i).asSymbol;
                args = args ++ [busKey, ~modBuses[route[0]].index, depthKey, route[1]];
            };
        };
        
        // Create combiner synth
        ~modApplySynths[destKey] = Synth(\modApply, args, ~modGroup, \addAfter);
        
        ("Mod apply: slot " ++ slot ++ " " ++ param ++ " with " ++ routes.size ++ " sources").postln;
    };
    
    // Add a mod route
    ~addModRoute = { |sourceBus, targetSlot, targetParam, depth=0.5|
        var destKey = ~destKey.(targetSlot, targetParam);
        var routes = ~modRoutes[destKey];
        var existing;
        
        // Initialize routes list if needed
        if(routes.isNil) {
            routes = List.new;
            ~modRoutes[destKey] = routes;
        };
        
        // Check if this source already connected
        existing = routes.detect { |r| r[0] == sourceBus };
        if(existing.notNil) {
            // Update depth
            existing[1] = depth;
        } {
            // Add new route
            routes.add([sourceBus, depth]);
        };
        
        // Rebuild synth
        ~rebuildModApply.(targetSlot, targetParam.asSymbol);
        
        // Start value stream if this is the first route overall
        if(~modValueStreamRoutine.isNil) {
            ~startModValueStream.();
        };
    };
    
    // Remove a mod route
    ~removeModRoute = { |sourceBus, targetSlot, targetParam|
        var destKey = ~destKey.(targetSlot, targetParam);
        var routes = ~modRoutes[destKey];
        
        if(routes.notNil) {
            routes.removeAllSuchThat { |r| r[0] == sourceBus };
        };
        
        // Rebuild synth (will clear if no routes left)
        ~rebuildModApply.(targetSlot, targetParam.asSymbol);
        
        // Stop value stream if no more routes
        if(~modRoutes.select({ |v| v.notNil and: { v.size > 0 } }).size == 0) {
            ~stopModValueStream.();
        };
    };
    
    // Update route depth
    ~setModRouteDepth = { |sourceBus, targetSlot, targetParam, depth|
        var destKey = ~destKey.(targetSlot, targetParam);
        var routes = ~modRoutes[destKey];
        var existing;
        
        if(routes.notNil) {
            existing = routes.detect { |r| r[0] == sourceBus };
            if(existing.notNil) {
                existing[1] = depth;
                ~rebuildModApply.(targetSlot, targetParam.asSymbol);
            };
        };
    };
    
    // Get route count for a destination
    ~getRouteCount = { |targetSlot, targetParam|
        var destKey = ~destKey.(targetSlot, targetParam);
        var routes = ~modRoutes[destKey];
        if(routes.notNil) { routes.size } { 0 };
    };
    
    // ========================================
    // MODULATION VALUE STREAMING (for UI)
    // ========================================
    
    ~modValueStreamAddr = NetAddr("127.0.0.1", 57121);
    ~modValueStreamRate = 20;  // fps
    
    ~startModValueStream = {
        if(~modValueStreamRoutine.notNil) {
            ~modValueStreamRoutine.stop;
        };
        
        ~modValueStreamRoutine = Routine({
            loop {
                var messages = List.new;
                
                // Collect values for all destinations with active routes
                ~modRoutes.keysValuesDo { |destKey, routes|
                    var parts, targetSlot, targetParam, paramBus, currentVal, range, normVal;
                    
                    if(routes.notNil and: { routes.size > 0 }) {
                        parts = destKey.asString.split($_);
                        if(parts.size >= 2) {
                            targetSlot = parts[0].asInteger;
                            targetParam = parts[1].asSymbol;
                            
                            paramBus = ~genParams[targetSlot][targetParam];
                            if(paramBus.notNil) {
                                currentVal = paramBus.getSynchronous;
                                
                                range = ~paramRanges[targetParam] ?? [0, 1];
                                normVal = (currentVal - range[0]) / (range[1] - range[0]);
                                normVal = normVal.clip(0, 1);
                                
                                messages.add([targetSlot, targetParam.asString, normVal]);
                            };
                        };
                    };
                };
                
                if(messages.size > 0) {
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
    
    // ========================================
    // TEST HELPERS
    // ========================================
    
    ~testMultiMod = {
        "=== MULTI-SOURCE TEST ===".postln;
        "Routing: MOD1.A (bus 0) + MOD2.X (bus 4) → GEN1 cutoff".postln;
        ~addModRoute.(0, 1, \cutoff, 0.5);
        ~addModRoute.(4, 1, \cutoff, 0.3);
        "Both sources active. Run ~stopMultiMod.() to stop.".postln;
    };
    
    ~stopMultiMod = {
        ~removeModRoute.(0, 1, \cutoff);
        ~removeModRoute.(4, 1, \cutoff);
        "Multi-source test stopped.".postln;
    };
    
    "  ✓ Mod apply ready (multi-source, max 4 per destination)".postln;
};
