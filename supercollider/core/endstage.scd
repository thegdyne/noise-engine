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

    "  [x] End-stage SynthDefs ready (ne_gen_silence, ne_endstage_standard)".postln;
};

// === BOOT END-STAGE INFRASTRUCTURE ===
// Called after buses and groups are allocated.
// Creates per-slot intermediate buses, groups, silence generators, and end-stage synths.

~bootEndstageInfra = {
    "Booting end-stage infrastructure (8 slots)...".postln;

    // Allocate intermediate buses (stereo audio, one per slot)
    ~intermediateBus = Array.fill(8, { Bus.audio(s, 2) });

    // Per-slot group structure:
    //   slotGroup[n]
    //     ├── genSubGroup[n]     (generators execute first)
    //     └── endstageSubGroup[n] (end-stage reads result)
    ~slotGroup = Array.fill(8, { nil });
    ~genSubGroup = Array.fill(8, { nil });
    ~endstageSubGroup = Array.fill(8, { nil });
    ~endstageNodes = Array.fill(8, { nil });
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
        ~slotGroup[idx] = Group(~genGroup, \addToTail);
        ~genSubGroup[idx] = Group(~slotGroup[idx], \addToHead);
        ~endstageSubGroup[idx] = Group(~slotGroup[idx], \addToTail);

        // Boot silence generator (always-writer invariant)
        ~silenceNodes[idx] = Synth(\ne_gen_silence, [
            \outBus, ~intermediateBus[idx].index
        ], ~genSubGroup[idx], \addToTail);

        // Boot end-stage synth (persistent infrastructure)
        ~endstageNodes[idx] = Synth(\ne_endstage_standard, [
            \inBus, ~intermediateBus[idx].index,
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

        "  Slot %: intermediate=%, genSub=%, endSub=%, endstage=%, silence=%".format(
            slotID,
            ~intermediateBus[idx].index,
            ~genSubGroup[idx].nodeID,
            ~endstageSubGroup[idx].nodeID,
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
            \slotIndex, slotID  // For telemetry routing (ignored by generators without this arg)
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
