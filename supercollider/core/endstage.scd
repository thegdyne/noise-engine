/*
End-Stage Processing
Shared output chain for all generators (filter, envelope, routing)

See docs/END_STAGE_ARCHITECTURE_SPEC.md for full architecture details.

Signal flow per slot:
  [Generator] → intermediateBus[slot] → [End-Stage] → genBus[slot] → [Channel Strip]

The end-stage is persistent infrastructure — booted once at startup, never freed.
Generators are swapped in/out of the intermediate bus; the end-stage reads from it.

Invariants:
  - Intermediate bus is always 2ch stereo
  - Generator writes via ReplaceOut (never Out — prevents volume doubling)
  - Silence generator keeps bus zeroed when no generator loaded
  - Group ordering: generatorGroup (head) → endstageGroup (tail)
*/

~setupEndstage = {
    "Setting up end-stage processing...".postln;

    // === SILENCE GENERATOR ===
    // Always-writer invariant: every slot must have a node writing to the
    // intermediate bus. When no generator is loaded, this writes silence.
    // Prevents stale audio from hanging on the bus.
    SynthDef(\ne_gen_silence, { |outBus|
        ReplaceOut.ar(outBus, Silent.ar(2));
    }).add;

    // === STANDARD END-STAGE ===
    // Shared output processing chain: filter → envelope/VCA → limiter
    // One instance per slot, persistent (never freed during normal operation).
    //
    // Bus arguments are RAW INTEGER indices (Pillar 3).
    // clockTrigBus and midiTrigBus are ABSOLUTE pre-calculated indices (Pillar 1).
    // slotIndex is for debug/display only — never used for address calculation.
    SynthDef(\ne_endstage_standard, { |inBus, outBus,
        cutoffBus, resBus, attackBus, decayBus,
        filterTypeBus, envSourceBus, clockRateIndexBus,
        clockTrigBus, midiTrigBus, slotIndex=0, ampBus, mute=0|

        var sig, filterFreq, rq, attack, decay, filterType, envSource, clockRateIndex, amp;

        // Input from generator (intermediate register — always 2ch)
        sig = In.ar(inBus, 2);

        // Bus reads with SAFETY CLAMPS to prevent runaway values
        filterFreq = In.kr(cutoffBus).clip(20, 20000);
        rq = In.kr(resBus).clip(0.05, 1.0);
        attack = In.kr(attackBus).clip(0.0001, 10);
        decay = In.kr(decayBus).clip(0.01, 30);
        filterType = In.kr(filterTypeBus);
        envSource = In.kr(envSourceBus);
        clockRateIndex = In.kr(clockRateIndexBus).clip(0, 12);
        amp = In.kr(ampBus).clip(0, 2);

        // Processing chain (SSOT — defined once, all generators benefit)
        sig = LeakDC.ar(sig);
        sig = ~multiFilter.(sig, filterType, filterFreq, rq);
        sig = ~envVCA.(sig, envSource, clockRateIndex, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);

        // Mute with click-free fade (10ms lag)
        sig = sig * (1 - Lag.kr(mute.clip(0, 1), 0.01));

        // Safety limiter
        sig = Limiter.ar(sig, 0.95);

        // Ensure stereo output for channel strip
        sig = ~ensure2ch.(sig);

        Out.ar(outBus, sig);
    }).add;

    // === ANALOG OUTPUT STAGE ===
    // Per-slot analog coloring: sits between generator and end-stage.
    // Signal flow: intermediateBus → [Analog Stage] → enhancedBus → [End-Stage]
    // Types: 0=CLEAN, 1=TAPE, 2=TUBE, 3=XFOLD
    SynthDef(\ne_analog_stage, { |inBus, outBus,
        enableBus, typeBus, driveBus, mixBus|

        var sig, clean, shaped, enable, t, drive, mix;
        var drift, driveMult, drivenSig, env, slewHz;
        var sag, bias, dynamicThresh, tape, asym, tube, xfold, compensation;

        // Read input (stereo from intermediate bus)
        sig = In.ar(inBus, 2);
        clean = sig;

        // Control reads with lag for click-free switching
        enable = In.kr(enableBus).lag(0.02);
        t = In.kr(typeBus).round.clip(0, 3);
        drive = In.kr(driveBus).clip(0, 1);
        mix = In.kr(mixBus).clip(0, 1);

        // --- 1. Circuit Infrastructure: Thermal Drift & Slew ---
        // Micro-Drift: ±2% meander ensures the saturation point is never frozen
        drift = Lag.kr(LFNoise1.kr(0.05).range(0.98, 1.02), 2.0);
        driveMult = drive.linexp(0, 1, 1, 10) * drift;
        drivenSig = sig * driveMult;

        // Level-Dependent Slew: waveform edges soften as volume drops
        env = Amplitude.ar(drivenSig, 0.001, 0.15).clip(0.01, 1.0);
        slewHz = env.linexp(0.01, 1.0, 3000, 12000);
        drivenSig = LPF.ar(drivenSig, slewHz);

        // --- 2. Mode Upgrades: Sag & Recovery ---
        // TAPE: Hysteresis + Sag (1.2s memory of loud events)
        sag = LagUD.kr(env, 0.05, 1.2);
        bias = sag.linlin(0.01, 1.0, 0.0, 0.03);
        dynamicThresh = env.linexp(0.01, 1.0, 0.5, 1.5).clip(0.3, 2.0);
        tape = ((drivenSig + bias) * (0.8 / dynamicThresh)).tanh * dynamicThresh;
        tape = LPF.ar(tape, 12000) * 0.85;

        // TUBE: Dynamic Asymmetry (bias shift with level)
        asym = env.linlin(0.01, 1.0, 0.1, 0.35);
        tube = ((drivenSig + (drivenSig * drivenSig * asym)) * 1.2).tanh * 0.85;

        // XFOLD: tighter fold window for maximum mangling
        xfold = Fold.ar(drivenSig, -0.2, 0.2) * 0.8;

        // --- 3. Final Mix & Safety ---
        shaped = Select.ar(t, [sig, tape, tube, xfold]);
        compensation = (1 / driveMult.sqrt).clip(0.2, 1.0);
        shaped = shaped * compensation;

        // Wet/dry mix, then enable bypass
        sig = XFade2.ar(clean, shaped, (mix * 2) - 1);
        sig = XFade2.ar(clean, sig, (enable * 2) - 1);

        // Safety: remove DC and soft-limit
        sig = LeakDC.ar(sig).softclip;

        ReplaceOut.ar(outBus, sig);
    }).add;

    "  [x] End-stage SynthDefs ready (ne_gen_silence, ne_endstage_standard, ne_analog_stage)".postln;
};

// === BOOT END-STAGE INFRASTRUCTURE ===
// Called after buses and groups are allocated.
// Creates per-slot intermediate buses, groups, silence generators, and end-stage synths.

~bootEndstageInfra = {
    "Booting end-stage infrastructure (8 slots)...".postln;

    // Allocate intermediate buses (stereo audio, one per slot)
    ~intermediateBus = Array.fill(8, { Bus.audio(s, 2) });

    // Allocate enhanced buses (post-analog stage, stereo, one per slot)
    ~enhancedBus = Array.fill(8, { Bus.audio(s, 2) });

    // Per-slot group structure:
    //   slotGroup[n]
    //     ├── genSubGroup[n]       (generators execute first)
    //     ├── analogSubGroup[n]    (analog stage reads intermediate, writes enhanced)
    //     └── endstageSubGroup[n]  (end-stage reads enhanced)
    ~slotGroup = Array.fill(8, { nil });
    ~genSubGroup = Array.fill(8, { nil });
    ~analogSubGroup = Array.fill(8, { nil });
    ~endstageSubGroup = Array.fill(8, { nil });
    ~endstageNodes = Array.fill(8, { nil });
    ~analogNodes = Array.fill(8, { nil });
    ~silenceNodes = Array.fill(8, { nil });

    8.do { |idx|
        var slotID = idx + 1;
        var slotKey = slotID.asString;

        // Determine bus indices for this slot
        var freqBusIdx, cutoffBusIdx, resBusIdx, attackBusIdx, decayBusIdx;
        var useUnified = ~genUnifiedSlots.includes(slotID);

        if(useUnified, {
            freqBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_freq").asSymbol].index;
            cutoffBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_cutoff").asSymbol].index;
            resBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_res").asSymbol].index;
            attackBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_attack").asSymbol].index;
            decayBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_decay").asSymbol].index;
        }, {
            // Fallback to legacy buses
            freqBusIdx = ~genParams[slotID][\frequency].index;
            cutoffBusIdx = ~genParams[slotID][\cutoff].index;
            resBusIdx = ~genParams[slotID][\resonance].index;
            attackBusIdx = ~genParams[slotID][\attack].index;
            decayBusIdx = ~genParams[slotID][\decay].index;
        });

        // Create per-slot group hierarchy within ~genGroup
        // genGroup already exists and runs before stripGroup
        // Order: genSubGroup → analogSubGroup → endstageSubGroup
        ~slotGroup[idx] = Group(~genGroup, \addToTail);
        ~genSubGroup[idx] = Group(~slotGroup[idx], \addToHead);
        ~analogSubGroup[idx] = Group(~slotGroup[idx], \addToTail);
        ~endstageSubGroup[idx] = Group(~slotGroup[idx], \addToTail);

        // Boot silence generator (always-writer invariant)
        ~silenceNodes[idx] = Synth(\ne_gen_silence, [
            \outBus, ~intermediateBus[idx].index
        ], ~genSubGroup[idx], \addToTail);

        // Boot analog stage synth (reads intermediate, writes enhanced)
        ~analogNodes[idx] = Synth(\ne_analog_stage, [
            \inBus, ~intermediateBus[idx].index,
            \outBus, ~enhancedBus[idx].index,
            \enableBus, ~genParams[slotID][\analogEnable].index,
            \typeBus, ~genParams[slotID][\analogType].index,
            \driveBus, ~genParams[slotID][\analogDrive].index,
            \mixBus, ~genParams[slotID][\analogMix].index
        ], ~analogSubGroup[idx], \addToTail);

        // Boot end-stage synth (reads enhanced bus — post-analog)
        ~endstageNodes[idx] = Synth(\ne_endstage_standard, [
            \inBus, ~enhancedBus[idx].index,
            \outBus, ~genBus[idx].index,
            \cutoffBus, cutoffBusIdx,
            \resBus, resBusIdx,
            \attackBus, attackBusIdx,
            \decayBus, decayBusIdx,
            \filterTypeBus, ~genParams[slotID][\filterType].index,
            \envSourceBus, ~genParams[slotID][\envSource].index,
            \clockRateIndexBus, ~genParams[slotID][\clockRate].index,
            \clockTrigBus, ~clockTrigBus.index,  // Shared base — envVCA handles slot selection
            \midiTrigBus, if(~midiTrigBus.notNil, { ~midiTrigBus.index }, { 0 }),
            \slotIndex, idx,  // 0-indexed, debug only
            \ampBus, ~params[\amplitude].index,
            \mute, 0
        ], ~endstageSubGroup[idx], \addToTail);

        "  Slot %: intermediate=%, enhanced=%, genSub=%, analogSub=%, endSub=%, analog=%, endstage=%, silence=%".format(
            slotID,
            ~intermediateBus[idx].index,
            ~enhancedBus[idx].index,
            ~genSubGroup[idx].nodeID,
            ~analogSubGroup[idx].nodeID,
            ~endstageSubGroup[idx].nodeID,
            ~analogNodes[idx].nodeID,
            ~endstageNodes[idx].nodeID,
            ~silenceNodes[idx].nodeID
        ).postln;
    };

    "  [x] End-stage infrastructure ready (8 slots)".postln;
};

// === START/STOP GENERATOR (NEW ARCHITECTURE) ===
// These replace the functions in helpers.scd for end-stage-aware generators.
// Generators only write DSP to the intermediate bus — no filter/envelope.
// The end-stage reads from intermediate and applies the shared output chain.

~startGeneratorEndstage = { |slotID, genType|
    var idx = slotID - 1;
    var slotKey = slotID.asString;
    var useUnified = ~genUnifiedSlots.includes(slotID);
    var freqBusIdx, custom0Idx;

    // Determine bus indices
    if(useUnified, {
        freqBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_freq").asSymbol].index;
        custom0Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom0").asSymbol].index;
    }, {
        freqBusIdx = ~genParams[slotID][\frequency].index;
        custom0Idx = ~genParams[slotID][\custom][0].index;
    });

    if(~genSubGroup[idx].notNil, {
        var newGen;

        // Start channel strip (must exist before generator writes)
        ~startChannelStrip.(slotID);

        // Create new generator in genSubGroup (addToTail)
        // The generator writes to intermediate bus via ReplaceOut
        newGen = Synth(genType, [
            \out, ~intermediateBus[idx].index,
            \freqBus, freqBusIdx,
            \customBus0, custom0Idx,
            \slotIndex, idx  // 0-based for telemetry routing (ignored by generators without this arg)
        ], ~genSubGroup[idx], \addToTail);

        // Free the old generator/silence (ReplaceOut means no glitch during overlap)
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
        });
        if(~silenceNodes[idx].notNil, {
            ~silenceNodes[idx].free;
            ~silenceNodes[idx] = nil;
        });

        ~generators[slotID] = newGen;

        // Start cross-mod follower
        if(~startCrossModFollower.notNil, {
            ~startCrossModFollower.(slotID);
        });

        "Started (endstage) % in slot %".format(genType, slotID).postln;
    }, {
        "ERROR: genSubGroup[%] is nil!".format(idx).postln;
    });
};

~stopGeneratorEndstage = { |slotID|
    var idx = slotID - 1;

    if(~generators[slotID].notNil, {
        ~generators[slotID].free;
        ~generators[slotID] = nil;
    });

    // Restore silence generator (always-writer invariant)
    if(~genSubGroup[idx].notNil, {
        ~silenceNodes[idx] = Synth(\ne_gen_silence, [
            \outBus, ~intermediateBus[idx].index
        ], ~genSubGroup[idx], \addToTail);
    });

    // Stop cross-mod follower
    if(~stopCrossModFollower.notNil, {
        ~stopCrossModFollower.(slotID);
    });

    // Stop channel strip
    ~stopChannelStrip.(slotID);

    "Stopped generator in slot % (endstage silence restored)".format(slotID).postln;
};

"endstage.scd loaded".postln;
