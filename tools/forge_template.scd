// tools/forge_template.scd
// Template SynthDef for CQD_Forge generators
// Copy this as a starting point for hand-authored generators

SynthDef(\forge_PACKID_GENERATORID, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       seed=12345|

    // === VARIABLE DECLARATIONS (must be at top of block) ===
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var p1, p2, p3, p4, p5;  // Custom parameters

    // === DETERMINISM SEED (must be first executable line) ===
    RandSeed.ir(1, seed);

    // === READ STANDARD PARAMS ===
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // === READ CUSTOM PARAMS (P1-P5) ===
    // Each reads 0-1 from bus, map to actual range with linlin/linexp
    //
    // Example for linear param (0.1 to 0.9):
    //   /// IMAG_CUSTOMBUS:0
    //   p1 = In.kr(customBus0).linlin(0, 1, 0.1, 0.9);
    //
    // Example for exponential param (20 to 2000 Hz):
    //   /// IMAG_CUSTOMBUS:1
    //   p2 = In.kr(customBus1).linexp(0, 1, 20, 2000);

    /// IMAG_CUSTOMBUS:0
    p1 = In.kr(customBus0).linlin(0, 1, 0.0, 1.0);
    /// IMAG_CUSTOMBUS:1
    p2 = In.kr(customBus1).linlin(0, 1, 0.0, 1.0);
    /// IMAG_CUSTOMBUS:2
    p3 = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    /// IMAG_CUSTOMBUS:3
    p4 = In.kr(customBus3).linlin(0, 1, 0.0, 1.0);
    /// IMAG_CUSTOMBUS:4
    p5 = In.kr(customBus4).linlin(0, 1, 0.0, 1.0);


    // =========================================================================
    // === YOUR SYNTHESIS CODE HERE ===
    // =========================================================================

    // Example: simple saw with P1 controlling brightness
    sig = Saw.ar(freq);
    sig = sig * p1.linlin(0, 1, 0.3, 1.0);  // P1 = brightness


    // =========================================================================
    // === OUTPUT CHAIN (REQUIRED - in this exact order) ===
    // =========================================================================

    // 1. Filter (LP/HP/BP based on filterType)
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);

    // 2. Envelope VCA (handles OFF/CLK/MIDI triggering)
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);

    // 3. Ensure stereo output
    sig = ~ensure2ch.(sig);

    // 4. Output
    Out.ar(out, sig);

}).add;

"  * forge_PACKID_GENERATORID loaded".postln;


// ============================================================================
// NOTES
// ============================================================================
//
// NAMING:
//   SynthDef name format: \forge_{pack_id}_{generator_id}
//   Example: \forge_abyssal_depths_pressure_wave
//
// CUSTOM PARAMS (P1-P5):
//   - Always read from customBus0-4
//   - Always 0-1 normalized input
//   - Map to actual range with linlin (linear) or linexp (exponential)
//   - Include /// IMAG_CUSTOMBUS:N marker for validation
//
// HELPERS:
//   ~stereoSpread.(sig, rate, width)  - Optional: mono to stereo with movement
//   ~multiFilter.(sig, type, freq, rq) - REQUIRED: LP/HP/BP filter
//   ~envVCA.(...)                      - REQUIRED: envelope + VCA
//   ~ensure2ch.(sig)                   - REQUIRED: force stereo output
//
// POST-CHAIN ORDER:
//   Must be: ~multiFilter → ~envVCA → ~ensure2ch → Out.ar
//   Do NOT reorder these!
//
// TRIGGERS (for custom envelopes like TB-303 filter):
//   Triggers are AUDIO RATE! Use In.ar(), not In.kr()
//   
//   envTrig = Select.ar(envSource, [
//       DC.ar(0),                                             // OFF
//       Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),  // CLK
//       Select.ar(slotIndex, In.ar(midiTrigBus, 8))           // MIDI
//   ]);
//
// ============================================================================
