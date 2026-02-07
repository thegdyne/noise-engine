/*
Mod Slots
Manages mod source synth lifecycle (create/free per slot)

Each slot can have one active synth writing to 4 mod buses (quadrature).
Switching generators frees old synth and creates new one.
Empty generator = no synth, buses zeroed.

P1-P4 standardized params for mod matrix cross-modulation:
  | Param | LFO          | ARSeq+         | SauceOfGrav    | Sloth |
  |-------|--------------|----------------|----------------|-------|
  | P1    | rate         | rate           | rate           | -     |
  | P2    | globalWave   | globalAtk      | globalTension  | -     |
  | P3    | pattern      | globalRel      | calm           | -     |
  | P4    | globalPolarity| globalPolarity| globalPolarity | -     |
*/

~setupModSlots = {
    "Setting up mod slots...".postln;
    
    // Per-slot synth node tracking (nil = empty/no synth)
    ~modNodes = Array.fill(4, { nil });
    
    // Per-slot generator name tracking
    ~modGenNames = Array.fill(4, { "Empty" });
    
    // Per-slot parameter state (for recreation after param changes)
    ~modParams = Array.fill(4, { Dictionary.new });
    
    // Per-output state: waveform, polarity (4 outputs per slot)
    // Phases now controlled by pattern+rotate, not per-output
    ~modOutputState = Array.fill(4, {
        [
            Dictionary.newFrom([\wave, 0, \polarity, 0]),  // A/X
            Dictionary.newFrom([\wave, 0, \polarity, 0]),  // B/Y
            Dictionary.newFrom([\wave, 0, \polarity, 0]),  // C/Z
            Dictionary.newFrom([\wave, 0, \polarity, 0])   // D/R
        ]
    });

    // Per-slot clock index buses (live-updatable via .asMap)
    // Default to -1 (derive from rate knob - legacy behaviour)
    // Set to 0-12 to override with explicit clock rate
    ~modClkIdxBus = 4.collect { Bus.control(s, 1).set(-1) };

    // P1-P4 mapping per generator type
    // Returns [actualParamSymbol, isDiscrete, min, max] or nil if not supported
    ~mapP1P4Param = { |genName, pKey|
        var mapping;
        
        case
        { genName == "LFO" } {
            mapping = switch(pKey.asSymbol,
                \p1, { [\rate, false, 0, 1] },
                \p2, { [\globalWave, true, -1, 7] },      // -1=off, 0-7=waveform
                \p3, { [\pattern, true, 0, 5] },          // 0-5 patterns
                \p4, { [\globalPolarity, true, -1, 1] },  // -1=off, 0-1=polarity
                { nil }
            );
        }
        { genName == "ARSEq+" } {
            mapping = switch(pKey.asSymbol,
                \p1, { [\rate, false, 0, 1] },
                \p2, { [\globalAtk, false, -1, 1] },      // -1=off, 0-1=attack
                \p3, { [\globalRel, false, -1, 1] },      // -1=off, 0-1=release
                \p4, { [\globalPolarity, true, -1, 1] },  // -1=off, 0-1=polarity
                { nil }
            );
        }
        { genName == "SauceOfGrav" } {
            mapping = switch(pKey.asSymbol,
                \p1, { [\rate, false, 0, 1] },
                \p2, { [\globalTension, false, -1, 1] },  // -1=off, 0-1=tension
                \p3, { [\calm, false, 0, 1] },
                \p4, { [\globalPolarity, true, -1, 1] },  // -1=off, 0-1=polarity
                { nil }
            );
        }
        { /* Sloth or Empty - no P1-P4 support */ 
            mapping = nil;
        };
        
        mapping;
    };
    
    // Free mod slot synth and zero buses
    ~freeModSlot = { |slot|
        var idx = slot - 1;
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].free;
            ~modNodes[idx] = nil;
        };
        // Zero the buses (not hold)
        ~zeroModBuses.(slot);
    };
    
    // Start mod slot with specified generator
    ~startModSlot = { |slot, genName|
        var idx = slot - 1;
        var base = idx * 4;  // 4 outputs per slot
        var busA = ~modBuses[base + 0].index;
        var busB = ~modBuses[base + 1].index;
        var busC = ~modBuses[base + 2].index;
        var busD = ~modBuses[base + 3].index;
        var params = ~modParams[idx];
        var outState = ~modOutputState[idx];
        
        // Free existing
        ~freeModSlot.(slot);
        
        // Store generator name
        ~modGenNames[idx] = genName;
        
        // Create new synth based on generator type
        case
        { genName == "LFO" } {
            ~modNodes[idx] = Synth(\modLFO, [
                \outA, busA,
                \outB, busB,
                \outC, busC,
                \outD, busD,
                \mode, params[\mode] ? 0,
                \rate, params[\rate] ? 0.5,
                \shape, params[\shape] ? 0.5,
                \pattern, params[\pattern] ? 0,  // QUAD default
                \rotate, params[\rotate] ? 0,
                \waveA, outState[0][\wave] ? 0,
                \waveB, outState[1][\wave] ? 0,
                \waveC, outState[2][\wave] ? 0,
                \waveD, outState[3][\wave] ? 0,
                \polarityA, outState[0][\polarity] ? 0,
                \polarityB, outState[1][\polarity] ? 0,
                \polarityC, outState[2][\polarity] ? 0,
                \polarityD, outState[3][\polarity] ? 0,
                \globalWave, params[\globalWave] ? -1,
                \globalPolarity, params[\globalPolarity] ? -1,
                \clockTrigBus, ~clockTrigBus.index,
                \clkIdx, ~modClkIdxBus[slot - 1].asMap,  // Per-slot, bus-mapped
                \bpmBus, ~clockBus.index
            ], ~modGroup);
            ("  Mod slot " ++ slot ++ " -> LFO").postln;
        }
        { genName == "Sloth" } {
            ~modNodes[idx] = Synth(\modSloth, [
                \outX, busA,
                \outY, busB,
                \outZ, busC,
                \outR, busD,
                \mode, params[\mode] ? 0,
                \bias, params[\bias] ? 0.5,
                \polarityX, outState[0][\polarity] ? 0,
                \polarityY, outState[1][\polarity] ? 0,
                \polarityZ, outState[2][\polarity] ? 0,
                \polarityR, outState[3][\polarity] ? 0  // R defaults NORM
            ], ~modGroup);
("  Mod slot " ++ slot ++ " -> Sloth").postln;
        }
        { genName == "ARSEq+" } {
            ~modNodes[idx] = Synth(\modARSeqPlus, [
                \outA, busA,
                \outB, busB,
                \outC, busC,
                \outD, busD,
                \mode, params[\mode] ? 0,
                \clockMode, params[\clockMode] ? 0,
                \rate, params[\rate] ? 0.5,
                \atkA, params[\atkA] ? 0.5,
                \atkB, params[\atkB] ? 0.5,
                \atkC, params[\atkC] ? 0.5,
                \atkD, params[\atkD] ? 0.5,
                \relA, params[\relA] ? 0.5,
                \relB, params[\relB] ? 0.5,
                \relC, params[\relC] ? 0.5,
                \relD, params[\relD] ? 0.5,
                \curveA, params[\curveA] ? 0.5,
                \curveB, params[\curveB] ? 0.5,
                \curveC, params[\curveC] ? 0.5,
                \curveD, params[\curveD] ? 0.5,
                \syncModeA, params[\syncModeA] ? 0,
                \syncModeB, params[\syncModeB] ? 0,
                \syncModeC, params[\syncModeC] ? 0,
                \syncModeD, params[\syncModeD] ? 0,
                \loopRateA, params[\loopRateA] ? 6,
                \loopRateB, params[\loopRateB] ? 6,
                \loopRateC, params[\loopRateC] ? 6,
                \loopRateD, params[\loopRateD] ? 6,
                \polarityA, outState[0][\polarity] ? 0,
                \polarityB, outState[1][\polarity] ? 0,
                \polarityC, outState[2][\polarity] ? 0,
                \polarityD, outState[3][\polarity] ? 0,
                \globalAtk, params[\globalAtk] ? -1,
                \globalRel, params[\globalRel] ? -1,
                \globalPolarity, params[\globalPolarity] ? -1,
                \clockTrigBus, ~clockTrigBus.index,
                \clkIdx, ~modClkIdxBus[slot - 1].asMap,  // Per-slot, bus-mapped
                \bpmBus, ~clockBus.index
            ], ~modGroup);
("  Mod slot " ++ slot ++ " -> ARSEq+").postln;
        }
        { genName == "SauceOfGrav" } {
            ~modNodes[idx] = Synth(\ne_mod_sauce_of_grav, [
                \out1, busA,
                \out2, busB,
                \out3, busC,
                \out4, busD,
                \clockMode, params[\clockMode] ? 0,
                \rate, params[\rate] ? 0.5,
                \depth, params[\depth] ? 0.5,
                \gravity, params[\gravity] ? 0.5,
                \resonance, params[\resonance] ? 0.5,
                \excursion, params[\excursion] ? 0.5,
                \calm, params[\calm] ? 0.5,
                \tension1, params[\tension1] ? 0.5,
                \tension2, params[\tension2] ? 0.5,
                \tension3, params[\tension3] ? 0.5,
                \tension4, params[\tension4] ? 0.5,
                \mass1, params[\mass1] ? 0.5,
                \mass2, params[\mass2] ? 0.5,
                \mass3, params[\mass3] ? 0.5,
                \mass4, params[\mass4] ? 0.5,
                \polarity1, outState[0][\polarity] ? 0,
                \polarity2, outState[1][\polarity] ? 0,
                \polarity3, outState[2][\polarity] ? 0,
                \polarity4, outState[3][\polarity] ? 0,
                \globalTension, params[\globalTension] ? -1,
                \globalPolarity, params[\globalPolarity] ? -1,
                \clockTrigBus, ~clockTrigBus.index,
                \clockIndex, ~modClockSourceIndex,
                \bpmBus, ~clockBus.index
            ], ~modGroup);
            ("  Mod slot " ++ slot ++ " -> SauceOfGrav").postln;
        }
        { /* Empty - node stays nil, buses already zeroed */
            ("  Mod slot " ++ slot ++ " -> Empty").postln;
        };
    };
    
    // Update parameter on existing synth
    // Handles P1-P4 mapping to underlying params
    ~setModParam = { |slot, key, value|
        var idx = slot - 1;
        var genName = ~modGenNames[idx];
        var actualKey = key.asSymbol;
        var mapping;
        
        // Check if this is a P1-P4 param that needs mapping
        if(#[\p1, \p2, \p3, \p4].includes(actualKey)) {
            mapping = ~mapP1P4Param.(genName, actualKey);
            if(mapping.notNil) {
                actualKey = mapping[0];  // Get actual param symbol
                // Clamp value to valid range
                value = value.clip(mapping[2], mapping[3]);
                if(mapping[1]) { value = value.round };  // Round if discrete
            } {
                // No mapping for this mod type - ignore
                ^nil;
            };
        };
        
//         ("  Mod " ++ slot ++ " param: " ++ actualKey ++ " = " ++ value).postln;
        ~modParams[idx][actualKey] = value;
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(actualKey, value);
        };
    };
    
    // Update output waveform (LFO only)
    ~setModOutputWave = { |slot, output, waveIndex|
        var idx = slot - 1;
        var paramName;
        if(~modGenNames[idx] != "LFO") { ^nil };
        paramName = [\waveA, \waveB, \waveC, \waveD][output];
        ~modOutputState[idx][output][\wave] = waveIndex;
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(paramName, waveIndex);
        };
    };
    
    // Update output polarity
    ~setModOutputPolarity = { |slot, output, polarity|
        var idx = slot - 1;
        var genName = ~modGenNames[idx];
        var paramName;
        
        ~modOutputState[idx][output][\polarity] = polarity;
        
    // Parameter name depends on generator type
        case
        { (genName == "LFO") || (genName == "ARSEq+") } {
            paramName = [\polarityA, \polarityB, \polarityC, \polarityD][output];
        }
        { genName == "SauceOfGrav" } {
            paramName = [\polarity1, \polarity2, \polarity3, \polarity4][output];
        }
        { /* Sloth */
            paramName = [\polarityX, \polarityY, \polarityZ, \polarityR][output];
        };
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(paramName, polarity);
        };
    };
    
    // Create mod group (runs before generators)
    ~modGroup = Group.after(~clockGroup);  // After clock for proper sync
    
    "  [x] Mod slots ready (4 slots x 4 outputs, P1-P4 cross-mod support)".postln;
};
