/*
Mod Slots
Manages mod source synth lifecycle (create/free per slot)

Each slot can have one active synth writing to 4 mod buses (quadrature).
Switching generators frees old synth and creates new one.
Empty generator = no synth, buses zeroed.
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
                \clockTrigBus, ~clockTrigBus.index,
                \clockIndex, ~modClockSourceIndex,  // From config.scd
                \bpmBus, ~clockBus.index
            ], ~modGroup);
            ("  Mod slot " ++ slot ++ " → LFO").postln;
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
("  Mod slot " ++ slot ++ " → Sloth").postln;
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
                \clockTrigBus, ~clockTrigBus.index,
                \clockIndex, ~modClockSourceIndex,
                \bpmBus, ~clockBus.index
            ], ~modGroup);
            ("  Mod slot " ++ slot ++ " → ARSEq+").postln;
        }
        { /* Empty - node stays nil, buses already zeroed */
            ("  Mod slot " ++ slot ++ " → Empty").postln;
        };
    };
    
    // Update parameter on existing synth
    ~setModParam = { |slot, key, value|
        var idx = slot - 1;
        ~modParams[idx][key.asSymbol] = value;
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(key.asSymbol, value);
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
        if(genName == "LFO") {
            paramName = [\polarityA, \polarityB, \polarityC, \polarityD][output];
        } {
            paramName = [\polarityX, \polarityY, \polarityZ, \polarityR][output];
        };
        
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(paramName, polarity);
        };
    };
    
    // Create mod group (runs before generators)
    ~modGroup = Group.after(~clockGroup);  // After clock for proper sync
    
    "  ✓ Mod slots ready (4 slots × 4 outputs)".postln;
};
