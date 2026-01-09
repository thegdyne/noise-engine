/*
Mod Apply v2 - Multi-Source Modulation Engine
Supports multiple mod sources targeting the same parameter.

Architecture:
- One \modApply synth per destination (slot+param combo) - ALWAYS RUNNING
- Each synth reads center from ~genUserParams bus (live tracking)
- Each synth has 4 FIXED route slots, updated via .set() ONLY
- 0 routes = passthrough (all buses = -1, deltas = 0)
- NEVER rebuild synths - create once, update via .set()

Per-slot args: busK, depthK, amountK, offsetK, polarityK, invertK
Polarity: 0=bipolar, 1=uni+, 2=uni-
Invert: 0=normal, 1=inverted (flips signal before polarity)
Offset: -1 to +1, shifts mod range up/down from base value

Mapped-space modulation:
- Linear params: delta = polarityFn(s, r) + offset
- Exp params: out = base * (2 ** (polarityFn(s, r) + offset) * octRange))
*/

~setupModApply = {
    "Setting up mod apply (multi-source, .set() only)...".postln;
    
    // Active synths: "slot_param" -> Synth (created once, never freed)
    ~modApplySynths = Dictionary.new;
    
    // Route tracking: "slot_param" -> Array[4] of source buses (nil = empty slot)
    ~modRoutes = Dictionary.new;
    
    // Parameter config: [minVal, maxVal, curve, octRange]
    // curve: 0=linear, 1=exponential (for modulation behavior)
    // octRange: octaves of sweep for exp mod (e.g. 4 = +/-4 octaves at 100% depth)
    // MUST MATCH Python GENERATOR_PARAMS - Python is SSOT
    ~paramConfig = Dictionary.new;
    ~paramConfig[\cutoff] = [20, 16000, 1, 4];      // exp mod, 4 octaves
    ~paramConfig[\frequency] = [20, 8000, 1, 4];    // exp mod, 4 octaves
    ~paramConfig[\resonance] = [0.1, 1.0, 0, 0];    // linear mod
    ~paramConfig[\attack] = [0.0001, 2.0, 0, 0];    // linear mod
    ~paramConfig[\decay] = [0.01, 10.0, 0, 0];      // linear mod
    // Custom params (P1-P5) - linear 0-1
    ~paramConfig[\p1] = [0, 1, 0, 0];
    ~paramConfig[\p2] = [0, 1, 0, 0];
    ~paramConfig[\p3] = [0, 1, 0, 0];
    ~paramConfig[\p4] = [0, 1, 0, 0];
    ~paramConfig[\p5] = [0, 1, 0, 0];
    
    // Modulatable params (list of params that get passthrough synths)
    ~modulatableParams = [\cutoff, \frequency, \resonance, \attack, \decay, \p1, \p2, \p3, \p4, \p5];
    
    // Helper: check if param is a custom param (p1-p5)
    ~isCustomParam = { |param|
        var s = param.asString;
        (s.size == 2) and: { s[0] == $p } and: { s[1].isDecDigit }
    };
    
    // Helper: get custom param index (p1 -> 0, p2 -> 1, etc.)
    ~customParamIndex = { |param|
        param.asString[1].asString.asInteger - 1
    };
    
    // Helper: get param output bus (handles both standard and custom params)
    ~getParamBus = { |slot, param|
        if(~isCustomParam.(param)) {
            var idx = ~customParamIndex.(param);
            ~genParams[slot][\custom][idx]
        } {
            ~genParams[slot][param.asSymbol]
        }
    };
    
    // Helper: get user param bus (for relative modulation center point)
    ~getUserParamBus = { |slot, param|
        if(~isCustomParam.(param)) {
            var idx = ~customParamIndex.(param);
            ~genUserParams[slot][\custom][idx]
        } {
            ~genUserParams[slot][param.asSymbol]
        }
    };
    
    // SynthDef with 4 fixed route slots
    // Each slot: bus, depth, amount, offset, polarity, invert
    SynthDef(\modApply, { |userBus, outBus, minVal=0, maxVal=1, curve=0, octRange=4,
                          bus0=(-1), depth0=0, amount0=1, offset0=0, polarity0=0, invert0=0,
                          bus1=(-1), depth1=0, amount1=1, offset1=0, polarity1=0, invert1=0,
                          bus2=(-1), depth2=0, amount2=1, offset2=0, polarity2=0, invert2=0,
                          bus3=(-1), depth3=0, amount3=1, offset3=0, polarity3=0, invert3=0|
        var base, range, totalDelta, out;
        var s0, s1, s2, s3;
        var r0, r1, r2, r3;
        var d0, d1, d2, d3;
        
        // Read center value from user params bus (live tracking)
        base = In.kr(userBus);
        range = maxVal - minVal;
        
        // === SLOT 0 ===
        s0 = Select.kr(bus0 >= 0, [0, In.kr(bus0)]);
        s0 = s0 * Select.kr(invert0, [1, -1]);  // Apply invert
        r0 = depth0 * amount0;
        d0 = Select.kr(polarity0, [
            s0 * r0,                           // 0: bipolar
            ((s0 + 1) * 0.5) * r0,             // 1: uni+
            ((s0 + 1) * 0.5).neg * r0          // 2: uni-
        ]) + offset0;  // Add offset after modulation
        
        // === SLOT 1 ===
        s1 = Select.kr(bus1 >= 0, [0, In.kr(bus1)]);
        s1 = s1 * Select.kr(invert1, [1, -1]);
        r1 = depth1 * amount1;
        d1 = Select.kr(polarity1, [
            s1 * r1,
            ((s1 + 1) * 0.5) * r1,
            ((s1 + 1) * 0.5).neg * r1
        ]) + offset1;
        
        // === SLOT 2 ===
        s2 = Select.kr(bus2 >= 0, [0, In.kr(bus2)]);
        s2 = s2 * Select.kr(invert2, [1, -1]);
        r2 = depth2 * amount2;
        d2 = Select.kr(polarity2, [
            s2 * r2,
            ((s2 + 1) * 0.5) * r2,
            ((s2 + 1) * 0.5).neg * r2
        ]) + offset2;
        
        // === SLOT 3 ===
        s3 = Select.kr(bus3 >= 0, [0, In.kr(bus3)]);
        s3 = s3 * Select.kr(invert3, [1, -1]);
        r3 = depth3 * amount3;
        d3 = Select.kr(polarity3, [
            s3 * r3,
            ((s3 + 1) * 0.5) * r3,
            ((s3 + 1) * 0.5).neg * r3
        ]) + offset3;
        
        // Sum all deltas
        totalDelta = d0 + d1 + d2 + d3;
        
        // Apply modulation based on curve type
        out = Select.kr(curve, [
            // Linear (curve=0): base + delta * range
            (base + (totalDelta * range)).clip(minVal, maxVal),
            // Exponential (curve=1): base * 2^(delta * octRange)
            (base * (2 ** (totalDelta * octRange))).clip(minVal, maxVal)
        ]);
        
        // Write to output bus
        ReplaceOut.kr(outBus, out);
    }).add;
    
    // Helper: Get destination key
    ~destKey = { |slot, param|
        "%_%".format(slot, param);
    };
    
    // Create a modApply synth for a destination (called ONCE per slot+param)
    ~createModApply = { |slot, param|
        var destKey = ~destKey.(slot, param);
        var userBus, outBus, config;
        var synth;
        
        userBus = ~getUserParamBus.(slot, param);
        outBus = ~getParamBus.(slot, param);
        config = ~paramConfig[param.asSymbol] ?? [0, 1, 0, 4];
        
        if(userBus.isNil or: { outBus.isNil }) {
            ("Mod apply: unknown param " ++ param ++ " for slot " ++ slot).warn;
            ^nil;
        };
        
        synth = Synth(\modApply, [
            \userBus, userBus.index,
            \outBus, outBus.index,
            \minVal, config[0],
            \maxVal, config[1],
            \curve, config[2],
            \octRange, config[3],
            // All slots disabled by default (bus = -1)
            \bus0, -1, \depth0, 0, \amount0, 1, \polarity0, 0, \invert0, 0,
            \bus1, -1, \depth1, 0, \amount1, 1, \polarity1, 0, \invert1, 0,
            \bus2, -1, \depth2, 0, \amount2, 1, \polarity2, 0, \invert2, 0,
            \bus3, -1, \depth3, 0, \amount3, 1, \polarity3, 0, \invert3, 0
        ], ~modGroup, \addAfter);
        
        ~modApplySynths[destKey] = synth;
        ~modRoutes[destKey] = Array.fill(4, { nil });  // Track which source in each slot
        
        synth;
    };
    
    // Initialize passthrough synths for all slots x params
    ~initPassthroughs = {
        "Creating passthrough synths (40 total, .set() only updates)...".postln;
        8.do { |i|
            var slot = i + 1;
            ~modulatableParams.do { |param|
                ~createModApply.(slot, param);
            };
        };
        "  [x] 40 modApply synths created (never rebuilt)".postln;
    };
    
    // Find slot index for a source bus, or first free slot
    ~findSlot = { |destKey, sourceBus|
        var routes = ~modRoutes[destKey];
        var existingIdx, freeIdx;
        
        if(routes.isNil) { ^nil };
        
        existingIdx = routes.indexOf(sourceBus);
        if(existingIdx.notNil) {
            existingIdx;  // Already connected
        } {
            freeIdx = routes.indexOf(nil);  // First free slot
            freeIdx;  // May be nil if full
        };
    };
    
    // Add a route (find free slot, use .set())
    // sourceBus: 0-15 (mod buses) OR 16-23 (crossmod buses)
    ~addModRoute = { |sourceBus, targetSlot, targetParam, depth=0.5, amount=1.0, offset=0.0, polarity=0, invert=0|
        var destKey = ~destKey.(targetSlot, targetParam.asSymbol);
        var synth = ~modApplySynths[destKey];
        var routes = ~modRoutes[destKey];
        var slotIdx, sourceBusObj;
        
        if(synth.isNil) {
            ("Mod apply: no synth for " ++ destKey).warn;
            ^nil;
        };
        
        slotIdx = ~findSlot.(destKey, sourceBus);
        
        if(slotIdx.isNil) {
            ("Mod apply: no free slots for " ++ destKey ++ " (max 4)").warn;
            ^nil;
        };
        
        // Use unified bus resolver (handles both mod buses 0-15 and crossmod 16-23)
        sourceBusObj = ~getModSourceBus.(sourceBus);
        if(sourceBusObj.isNil) {
            ("Mod apply: invalid source bus " ++ sourceBus).warn;
            ^nil;
        };
        
        // Update tracking
        routes[slotIdx] = sourceBus;
        
        // Set synth args for this slot via .set() - NO REBUILD
        synth.set(
            ("bus" ++ slotIdx).asSymbol, sourceBusObj.index,
            ("depth" ++ slotIdx).asSymbol, depth,
            ("amount" ++ slotIdx).asSymbol, amount,
            ("offset" ++ slotIdx).asSymbol, offset,
            ("polarity" ++ slotIdx).asSymbol, polarity,
            ("invert" ++ slotIdx).asSymbol, invert
        );
        
        ("Mod route: bus " ++ sourceBus ++ " -> slot " ++ targetSlot ++ " " ++ targetParam ++ 
         " [idx=" ++ slotIdx ++ ", d=" ++ depth ++ ", a=" ++ amount ++ ", o=" ++ offset ++
         ", p=" ++ polarity ++ ", i=" ++ invert ++ "]").postln;
        
        // Start value stream if first route
        if(~modValueStreamRoutine.isNil) {
            ~startModValueStream.();
        };
        
        slotIdx;
    };
    
    // Remove a route (set bus to -1 via .set())
    ~removeModRoute = { |sourceBus, targetSlot, targetParam|
        var destKey = ~destKey.(targetSlot, targetParam.asSymbol);
        var synth = ~modApplySynths[destKey];
        var routes = ~modRoutes[destKey];
        var slotIdx;
        
        if(synth.isNil or: { routes.isNil }) { ^nil };
        
        slotIdx = routes.indexOf(sourceBus);
        if(slotIdx.isNil) { ^nil };  // Not connected
        
        // Clear slot - just set bus to -1, NO REBUILD
        routes[slotIdx] = nil;
        synth.set(("bus" ++ slotIdx).asSymbol, -1);
        
        ("Mod route removed: bus " ++ sourceBus ++ " from slot " ++ targetSlot ++ " " ++ targetParam).postln;
        
        // Stop value stream if no routes remain
        if(~modRoutes.select({ |r| r.notNil and: { r.any({ |x| x.notNil }) } }).size == 0) {
            ~stopModValueStream.();
        };
    };
    
    // Update route parameters via .set() (depth, amount, offset, polarity, invert)
    // Creates route if it doesn't exist
    ~setModRoute = { |sourceBus, targetSlot, targetParam, depth, amount, offset, polarity, invert|
        var destKey = ~destKey.(targetSlot, targetParam.asSymbol);
        var synth = ~modApplySynths[destKey];
        var routes = ~modRoutes[destKey];
        var slotIdx;
        
        if(synth.isNil) { ^nil };
        
        slotIdx = routes.indexOf(sourceBus);
        if(slotIdx.isNil) {
            // Create if missing
            slotIdx = ~addModRoute.(sourceBus, targetSlot, targetParam, depth, amount, offset, polarity, invert);
            ^slotIdx;
        };
        
        // Update existing connection via .set() - NO REBUILD
        synth.set(
            ("depth" ++ slotIdx).asSymbol, depth,
            ("amount" ++ slotIdx).asSymbol, amount,
            ("offset" ++ slotIdx).asSymbol, offset,
            ("polarity" ++ slotIdx).asSymbol, polarity,
            ("invert" ++ slotIdx).asSymbol, invert
        );
    };
    
    // Get route count for a destination
    ~getRouteCount = { |targetSlot, targetParam|
        var destKey = ~destKey.(targetSlot, targetParam);
        var routes = ~modRoutes[destKey];
        if(routes.notNil) { routes.count({ |x| x.notNil }) } { 0 };
    };
    
    // ========================================
    // MODULATION VALUE STREAMING (for UI)
    // ========================================
    
    ~modValueStreamAddr = NetAddr("127.0.0.1", 57121);
    ~modValueStreamRate = 30;  // fps (bumped from 20)
    
    ~startModValueStream = {
        if(~modValueStreamRoutine.notNil) {
            ~modValueStreamRoutine.stop;
        };
        
        ~modValueStreamRoutine = Routine({
            loop {
                var messages = List.new;
                
                // Collect values for all destinations with active routes
                ~modRoutes.keysValuesDo { |destKey, routes|
                    var parts, targetSlot, targetParam, paramBus, currentVal;
                    
                    if(routes.notNil and: { routes.any({ |x| x.notNil }) }) {
                        parts = destKey.asString.split($_);
                        if(parts.size >= 2) {
                            targetSlot = parts[0].asInteger;
                            targetParam = parts[1].asSymbol;
                            
                            paramBus = ~getParamBus.(targetSlot, targetParam);
                            
                            if(paramBus.notNil) {
                                currentVal = try { paramBus.getSynchronous } { 0 };
                                
                                // Send raw mapped value - Python will unmap to 0-1
                                // This keeps Python as SSOT for mapping/unmapping logic
                                messages.add([targetSlot, targetParam.asString, currentVal]);
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
    
    ~testRelativeMod = {
        "=== RELATIVE MOD TEST ===".postln;
        "1. Set CUT slider to different positions".postln;
        "2. Modulation should center around slider position".postln;
        ~addModRoute.(0, 1, \cutoff, 0.5, 1.0, 0.0, 0, 0);  // bipolar, no offset, no invert
        "Route: MOD1.A -> GEN1 cutoff (bipolar, depth=0.5)".postln;
        "Run ~stopRelativeMod.() to stop.".postln;
    };
    
    ~stopRelativeMod = {
        ~removeModRoute.(0, 1, \cutoff);
        "Relative mod test stopped.".postln;
    };
    
    ~testPolarities = {
        "=== POLARITY TEST ===".postln;
        "Testing bipolar...".postln;
        ~addModRoute.(0, 1, \cutoff, 0.5, 1.0, 0.0, 0, 0);
        "Run ~setModRoute.(0, 1, \\cutoff, 0.5, 1.0, 0.0, 1, 0) for uni+".postln;
        "Run ~setModRoute.(0, 1, \\cutoff, 0.5, 1.0, 0.0, 2, 0) for uni-".postln;
        "Run ~stopRelativeMod.() to stop.".postln;
    };
    
    ~testOffset = {
        "=== OFFSET TEST ===".postln;
        "Testing offset +0.5...".postln;
        ~addModRoute.(0, 1, \cutoff, 0.3, 1.0, 0.5, 0, 0);  // offset shifts mod up
        "Modulation should be centered +50% from slider position".postln;
        "Run ~setModRoute.(0, 1, \\cutoff, 0.3, 1.0, -0.5, 0, 0) for offset down".postln;
        "Run ~stopRelativeMod.() to stop.".postln;
    };
    
    "  [x] Mod apply ready (40 synths, .set() only, 4 slots per target)".postln;
};
