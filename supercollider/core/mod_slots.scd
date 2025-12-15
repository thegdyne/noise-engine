/*
Mod Slots
Manages mod source synth lifecycle (create/free per slot)

Each slot can have one active synth writing to 3 mod buses.
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
    
    // Per-output state: waveform, phase, polarity
    // Default phases: A=0° (0), B=120° (2.67→3), C=240° (5.33→5)
    // Using indices: 0, 3, 5 gives roughly 120° spacing
    ~modOutputState = Array.fill(4, {
        [
            Dictionary.newFrom([\wave, 0, \phase, 0, \polarity, 1]),  // A: 0°
            Dictionary.newFrom([\wave, 0, \phase, 3, \polarity, 1]),  // B: 135° (close to 120°)
            Dictionary.newFrom([\wave, 0, \phase, 5, \polarity, 1])   // C: 225° (close to 240°)
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
        var base = idx * 3;
        var busA = ~modBuses[base + 0].index;
        var busB = ~modBuses[base + 1].index;
        var busC = ~modBuses[base + 2].index;
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
                \rate, params[\rate] ? 0.5,
                \shape, params[\shape] ? 0.5,
                \waveA, outState[0][\wave] ? 0,
                \waveB, outState[1][\wave] ? 0,
                \waveC, outState[2][\wave] ? 0,
                \phaseA, outState[0][\phase] ? 0,
                \phaseB, outState[1][\phase] ? 0,
                \phaseC, outState[2][\phase] ? 0,
                \polarityA, outState[0][\polarity] ? 1,
                \polarityB, outState[1][\polarity] ? 1,
                \polarityC, outState[2][\polarity] ? 1,
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
                \mode, params[\mode] ? 0,
                \bias, params[\bias] ? 0.5,
                \polarityX, outState[0][\polarity] ? 1,
                \polarityY, outState[1][\polarity] ? 1,
                \polarityZ, outState[2][\polarity] ? 1
            ], ~modGroup);
            ("  Mod slot " ++ slot ++ " → Sloth").postln;
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
        paramName = [\waveA, \waveB, \waveC][output];
        ~modOutputState[idx][output][\wave] = waveIndex;
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(paramName, waveIndex);
        };
    };
    
    // Update output phase (LFO only)
    ~setModOutputPhase = { |slot, output, phaseIndex|
        var idx = slot - 1;
        var paramName;
        if(~modGenNames[idx] != "LFO") { ^nil };
        paramName = [\phaseA, \phaseB, \phaseC][output];
        ~modOutputState[idx][output][\phase] = phaseIndex;
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(paramName, phaseIndex);
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
            paramName = [\polarityA, \polarityB, \polarityC][output];
        } {
            paramName = [\polarityX, \polarityY, \polarityZ][output];
        };
        
        if(~modNodes[idx].notNil) {
            ~modNodes[idx].set(paramName, polarity);
        };
    };
    
    // Create mod group (runs before generators)
    ~modGroup = Group.new(s, \addToHead);
    
    "  ✓ Mod slots ready (4 slots)".postln;
};
