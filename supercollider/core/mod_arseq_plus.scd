/*
Mod ARSEq+ SynthDef
4-output AR envelope sequencer with SEQ/PAR modes

Each output has independent AR envelope with:
- Attack time (0.1ms - 10s SYNC, 0.1ms - 120s LOOP)
- Release time (same ranges)
- Curve shape (LOG/LIN/EXP)
- Sync mode (SYNC: follow master, LOOP: self-cycle)
- Loop rate (when LOOP mode)
- Polarity (NORM: 0→+1, INV: 0→-1)

Master controls:
- Mode: SEQ (sequential 1→2→3→4) or PAR (parallel, all at once)
- Clock mode: CLK (sync to clock) or FREE (manual rate)
- Rate: master trigger rate

SEQ algorithm:
- Two pulses per envelope: pulse 1 = attack, pulse 2 = release
- env_idx = (seq_step // 2) % 4
- Cycles through envelopes in order

PAR algorithm:
- All envelopes triggered simultaneously
- Each runs independently

LOOP mode (per-envelope):
- Envelope self-retriggers at its own rate
- Overrides master clock for that envelope

Reference: docs/ARSEQ_PLUS_SPEC_v1.2.md
*/

SynthDef(\modARSeqPlus, {
    arg outA, outB, outC, outD,           // 4 output bus indices
        mode = 0,                          // 0=SEQ, 1=PAR
        clockMode = 0,                     // 0=CLK, 1=FREE
        rate = 0.5,                        // Master rate (0-1)
        // Per-envelope attack (0-1 normalized)
        atkA = 0.5, atkB = 0.5, atkC = 0.5, atkD = 0.5,
        // Per-envelope release (0-1 normalized)
        relA = 0.5, relB = 0.5, relC = 0.5, relD = 0.5,
        // Per-envelope curve (0=log, 0.5=lin, 1=exp)
        curveA = 0.5, curveB = 0.5, curveC = 0.5, curveD = 0.5,
        // Per-envelope sync mode (0=SYNC, 1=LOOP)
        syncModeA = 0, syncModeB = 0, syncModeC = 0, syncModeD = 0,
        // Per-envelope loop rate index (0-11)
        loopRateA = 6, loopRateB = 6, loopRateC = 6, loopRateD = 6,
        // Per-envelope polarity (0=NORM, 1=INV)
        polarityA = 0, polarityB = 0, polarityC = 0, polarityD = 0,
        // Clock infrastructure
        clockTrigBus = 0,
        clockIndex = 12,                   // x32 clock
        bpmBus = 0;

    var sigA, sigB, sigC, sigD;
    var envA, envB, envC, envD;
    var trigA, trigB, trigC, trigD;
    var gateA, gateB, gateC, gateD;
    var atkTrigA, atkTrigB, atkTrigC, atkTrigD;
    var relTrigA, relTrigB, relTrigC, relTrigD;
    var loopTrigA, loopTrigB, loopTrigC, loopTrigD;
    var masterTrig, seqStep, seqTrig;
    var clk, atrig, trig;
    var rateIndex, ticksPerCycle, masterFreq;
    var freeFreq, clkFreq;
    var bpm;

    // Time mapping functions
    var mapSyncTime = { |norm| norm.linexp(0, 1, 0.0001, 10.0) };
    var mapLoopTime = { |norm| norm.linexp(0, 1, 0.0001, 120.0) };
    var mapCurve = { |norm| (norm * 2.0) - 1.0 };  // 0-1 → -1 to +1

    // Envelope generator function
    var makeEnv = { |gate, atkNorm, relNorm, curveNorm, isLoop|
        var atkTime, relTime, curve, env;
        // Use loop time range if in LOOP mode, sync range otherwise
        atkTime = Select.kr(isLoop, [mapSyncTime.(atkNorm), mapLoopTime.(atkNorm)]);
        relTime = Select.kr(isLoop, [mapSyncTime.(relNorm), mapLoopTime.(relNorm)]);
        curve = mapCurve.(curveNorm);
        
        // AR envelope with variable curve
        env = EnvGen.kr(
            Env.perc(atkTime, relTime, 1.0, curve),
            gate,
            doneAction: 0
        );
        env;
    };

    // ---- CLOCK INPUT ----
    clk = In.ar(clockTrigBus + clockIndex);
    atrig = Trig1.ar(clk > 0.5, 0.001);
    trig = Trig1.kr(A2K.kr(atrig), 0.001);

    // ---- MASTER RATE ----
    // CLK mode: rate 0-1 maps to 12 divisions
    rateIndex = (rate * 11).round.clip(0, 11);
    ticksPerCycle = Select.kr(rateIndex, [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]);
    
    bpm = In.kr(bpmBus);
    clkFreq = bpm / 60 * 32 / ticksPerCycle;
    
    // FREE mode: 0.01-100Hz
    freeFreq = rate.linexp(0, 1, 0.01, 100);
    
    masterFreq = Select.kr(clockMode.round, [clkFreq, freeFreq]);
    
    // Master trigger from clock or free-running impulse
    masterTrig = Select.kr(clockMode.round, [
        PulseDivider.kr(trig, ticksPerCycle),
        Impulse.kr(masterFreq)
    ]);

// ---- SEQ MODE: SEQUENTIAL TRIGGERING ----
    // CD4017-style decade counter: 2 clocks per envelope
    // Q0=attack A, Q1=release A, Q2=attack B, Q3=release B, etc.
    seqStep = PulseCount.kr(masterTrig) % 8;  // 0-7 (2 steps × 4 envelopes)

// ---- ATTACK/RELEASE TRIGGERS ----
    // Each envelope gets separate attack and release triggers
    // Attack on even steps (0,2,4,6), Release on odd steps (1,3,5,7)
    // Use < comparisons (returns UGen, not boolean)
    atkTrigA = masterTrig * (seqStep < 0.5);                              // step 0
    relTrigA = masterTrig * (seqStep > 0.5) * (seqStep < 1.5);            // step 1
    atkTrigB = masterTrig * (seqStep > 1.5) * (seqStep < 2.5);            // step 2
    relTrigB = masterTrig * (seqStep > 2.5) * (seqStep < 3.5);            // step 3
    atkTrigC = masterTrig * (seqStep > 3.5) * (seqStep < 4.5);            // step 4
    relTrigC = masterTrig * (seqStep > 4.5) * (seqStep < 5.5);            // step 5
    atkTrigD = masterTrig * (seqStep > 5.5) * (seqStep < 6.5);            // step 6
    relTrigD = masterTrig * (seqStep > 6.5);                              // step 7

    // ---- GATE FROM SET-RESET FLIP-FLOP ----
    // Attack trigger SETS gate HIGH, Release trigger RESETS gate LOW
    // In PAR mode, use masterTrig directly (all together)
    gateA = Select.kr(mode.round, [
        SetResetFF.kr(atkTrigA, relTrigA),  // SEQ: SR flip-flop
        1  // PAR: always gated
    ]);
    gateB = Select.kr(mode.round, [
        SetResetFF.kr(atkTrigB, relTrigB),
        1
    ]);
    gateC = Select.kr(mode.round, [
        SetResetFF.kr(atkTrigC, relTrigC),
        1
    ]);
    gateD = Select.kr(mode.round, [
        SetResetFF.kr(atkTrigD, relTrigD),
        1
    ]);
    // ---- LOOP MODE TRIGGERS ----
    loopTrigA = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateA.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]));
    loopTrigB = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateB.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]));
    loopTrigC = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateC.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]));
    loopTrigD = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateD.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]));

    // ---- ENVELOPE GENERATION ----
    // SEQ mode: gate-based ASR envelope (attack on HIGH, release on LOW)
    // PAR mode: trigger-based AR envelope (all fire together)
    // LOOP mode: trigger-based AR envelope (self-triggering)

    envA = Select.kr(syncModeA.round, [
        // SYNC mode
        Select.kr(mode.round, [
            // SEQ: gate-based ASR
            EnvGen.kr(Env.asr(
                mapSyncTime.(atkA),
                1.0,
                mapSyncTime.(relA),
                mapCurve.(curveA)
            ), gateA),
            // PAR: trigger-based AR
            makeEnv.(masterTrig, atkA, relA, curveA, 0)
        ]),
        // LOOP mode: self-triggering AR
        makeEnv.(loopTrigA, atkA, relA, curveA, 1)
    ]);

    envB = Select.kr(syncModeB.round, [
        Select.kr(mode.round, [
            EnvGen.kr(Env.asr(
                mapSyncTime.(atkB), 1.0, mapSyncTime.(relB), mapCurve.(curveB)
            ), gateB),
            makeEnv.(masterTrig, atkB, relB, curveB, 0)
        ]),
        makeEnv.(loopTrigB, atkB, relB, curveB, 1)
    ]);

    envC = Select.kr(syncModeC.round, [
        Select.kr(mode.round, [
            EnvGen.kr(Env.asr(
                mapSyncTime.(atkC), 1.0, mapSyncTime.(relC), mapCurve.(curveC)
            ), gateC),
            makeEnv.(masterTrig, atkC, relC, curveC, 0)
        ]),
        makeEnv.(loopTrigC, atkC, relC, curveC, 1)
    ]);

    envD = Select.kr(syncModeD.round, [
        Select.kr(mode.round, [
            EnvGen.kr(Env.asr(
                mapSyncTime.(atkD), 1.0, mapSyncTime.(relD), mapCurve.(curveD)
            ), gateD),
            makeEnv.(masterTrig, atkD, relD, curveD, 0)
        ]),
        makeEnv.(loopTrigD, atkD, relD, curveD, 1)
    ]);
    // ---- OUTPUT SCALING ----
    // Convert 0-1 envelope to bipolar based on polarity
    // NORM (0): 0 to +1 → output 0 to +1
    // INV (1): 0 to +1 → output 0 to -1
    sigA = Select.kr(polarityA.round, [envA, envA.neg]);
    sigB = Select.kr(polarityB.round, [envB, envB.neg]);
    sigC = Select.kr(polarityC.round, [envC, envC.neg]);
    sigD = Select.kr(polarityD.round, [envD, envD.neg]);

    // ---- OUTPUT TO BUSES ----
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
    Out.kr(outD, sigD);
}).add;

"  ✓ modARSeqPlus SynthDef loaded (4 AR envelopes, SEQ/PAR modes)".postln;
