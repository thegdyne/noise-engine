/*
Mod ARSEq+ SynthDef
4-output AR envelope sequencer with SEQ/PAR modes

Each output has independent AR envelope with:
- Attack time (10ms - 5s SYNC, 100ms - 30s LOOP)
- Release time (same ranges)
- Curve shape (LOG/LIN/EXP)
- Sync mode (SYNC: follow master, LOOP: self-cycle)
- Loop rate (when LOOP mode)
- Polarity (NORM: 0->+1, INV: 0->-1)

Master controls:
- Mode: SEQ (sequential 1->2->3->4) or PAR (parallel, all at once)
- Clock mode: CLK (sync to clock) or FREE (manual rate)
- Rate: master trigger rate

Global overrides (for mod matrix P1-P4):
- globalAtk: when >= 0, overrides all atkA/B/C/D
- globalRel: when >= 0, overrides all relA/B/C/D
- globalPolarity: when >= 0, overrides all polarityA/B/C/D

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
        // Global overrides for mod matrix P1-P4
        globalAtk = -1,                    // P2: when >= 0, overrides all atk params
        globalRel = -1,                    // P3: when >= 0, overrides all rel params
        globalPolarity = -1,               // P4: when >= 0, overrides all polarity params
        // Clock infrastructure
        clockTrigBus = 0,
        clkIdx = 6,                   // Clock rate index 0-12 (default 6 = CLK)
	bpmBus = 0,
	resetBus = 0, resetIndex = 0;


    var sigA, sigB, sigC, sigD;
    var envA, envB, envC, envD;
    var gateA, gateB, gateC, gateD;
    var atkTrigA, atkTrigB, atkTrigC, atkTrigD;
    var relTrigA, relTrigB, relTrigC, relTrigD;
    var loopTrigA, loopTrigB, loopTrigC, loopTrigD;
    var masterTrig, seqStep;
    var clk, atrig, trig;
    var masterFreq;
    var freeFreq, clkFreq;
    var bpm, clkModeSel, modeSel;
    var effAtkA, effAtkB, effAtkC, effAtkD;
    var effRelA, effRelB, effRelC, effRelD;
    var effPolA, effPolB, effPolC, effPolD;
    var gAtk, gRel, gPol;
	var mapSyncTime, mapLoopTime, mapCurve, makeEnv;
    var parStep, atkTrigPar, relTrigPar, gatePar;
	var resetIn, areset, resetTrig;


	resetIn   = In.ar(resetBus + resetIndex);
	areset    = Trig1.ar(resetIn > 0.5, ControlDur.ir * 2);
	resetTrig = Trig1.kr(A2K.kr(areset), ControlDur.ir * 2);



    // Global override values (clipped)
    gAtk = globalAtk.clip(0, 1);
    gRel = globalRel.clip(0, 1);
    gPol = globalPolarity.clip(0, 1).round(1);

    // Effective attack values
    effAtkA = Select.kr(globalAtk >= 0, [atkA.clip(0, 1), gAtk]);
    effAtkB = Select.kr(globalAtk >= 0, [atkB.clip(0, 1), gAtk]);
    effAtkC = Select.kr(globalAtk >= 0, [atkC.clip(0, 1), gAtk]);
    effAtkD = Select.kr(globalAtk >= 0, [atkD.clip(0, 1), gAtk]);

    // Effective release values
    effRelA = Select.kr(globalRel >= 0, [relA.clip(0, 1), gRel]);
    effRelB = Select.kr(globalRel >= 0, [relB.clip(0, 1), gRel]);
    effRelC = Select.kr(globalRel >= 0, [relC.clip(0, 1), gRel]);
    effRelD = Select.kr(globalRel >= 0, [relD.clip(0, 1), gRel]);

    // Effective polarity values
    effPolA = Select.kr(globalPolarity >= 0, [polarityA.clip(0, 1).round(1), gPol]);
    effPolB = Select.kr(globalPolarity >= 0, [polarityB.clip(0, 1).round(1), gPol]);
    effPolC = Select.kr(globalPolarity >= 0, [polarityC.clip(0, 1).round(1), gPol]);
    effPolD = Select.kr(globalPolarity >= 0, [polarityD.clip(0, 1).round(1), gPol]);

    // Time mapping functions
    mapSyncTime = { |norm| norm.clip(0, 1).linexp(0, 1, 0.01, 5.0) };    // 10ms - 5s
    mapLoopTime = { |norm| norm.clip(0, 1).linexp(0, 1, 0.1, 30.0) };    // 100ms - 30s
    mapCurve = { |norm| (norm.clip(0, 1) * 2.0) - 1.0 };  // 0-1 -> -1 to +1

    // Envelope generator function
    makeEnv = { |gate, atkNorm, relNorm, curveNorm, isLoop|
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
    // Read all 13 pre-divided clock channels and select by index
    var allTrigs = In.ar(clockTrigBus, 13);
    // Legacy: if clkIdx < 0, derive from rate slider (0-1 -> 0-12)
    var legacyIdx = (rate * 12).round.clip(0, 12);
    var effIdx = Select.kr(clkIdx >= 0, [legacyIdx, clkIdx.round]);
    var clkIdxClamped = effIdx.clip(0, 12);
    clk = Select.ar(clkIdxClamped, allTrigs);
    atrig = Trig1.ar(clk > 0.5, ControlDur.ir * 2);
    trig = Trig1.kr(A2K.kr(atrig), ControlDur.ir * 2);

    // ---- MASTER RATE ----
    // Clock rates: [1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 8, 12, 16, 32]
    var clockMults = #[1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 8, 12, 16, 32];
    var clockMult = Select.kr(clkIdxClamped, clockMults);
    bpm = In.kr(bpmBus).max(1);
    clkFreq = bpm / 60 * clockMult;

    // FREE mode: 0.01-100Hz
    freeFreq = rate.linexp(0, 1, 0.01, 100);

    clkModeSel = clockMode.round.clip(0, 1);
    masterFreq = Select.kr(clkModeSel, [clkFreq, freeFreq]);

    // Master trigger from selected clock or free-running impulse
    masterTrig = Select.kr(clkModeSel, [
        trig,  // CLK: direct from selected clock channel
        Impulse.kr(masterFreq)
    ]);

    // ---- SEQ MODE: SEQUENTIAL TRIGGERING ----
    // CD4017-style decade counter: 2 clocks per envelope
    // Q0=attack A, Q1=release A, Q2=attack B, Q3=release B, etc.
	seqStep = Stepper.kr(masterTrig, resetTrig, 0, 7, 1, -1);

    // ---- ATTACK/RELEASE TRIGGERS ----
    // Discrete decode (matches CD4017-style stepping)
	atkTrigA = masterTrig * (seqStep < 0.5);
	relTrigA = masterTrig * (seqStep >= 0.5) * (seqStep < 1.5);

	atkTrigB = masterTrig * (seqStep >= 1.5) * (seqStep < 2.5);
	relTrigB = masterTrig * (seqStep >= 2.5) * (seqStep < 3.5);

	atkTrigC = masterTrig * (seqStep >= 3.5) * (seqStep < 4.5);
	relTrigC = masterTrig * (seqStep >= 4.5) * (seqStep < 5.5);

	atkTrigD = masterTrig * (seqStep >= 5.5) * (seqStep < 6.5);
	relTrigD = masterTrig * (seqStep >= 6.5) * (seqStep < 7.5);

    // ---- GATE FROM SET-RESET FLIP-FLOP ----
    // ARSEq behaviour = A-H-R:
    // - attack pulse SETS gate high
    // - next pulse RESETS gate low (starts release)
    modeSel = mode.round.clip(0, 1);

    // SEQ gates (independent)
	gateA = SetResetFF.kr(atkTrigA, relTrigA + resetTrig);
	gateB = SetResetFF.kr(atkTrigB, relTrigB + resetTrig);
	gateC = SetResetFF.kr(atkTrigC, relTrigC + resetTrig);
	gateD = SetResetFF.kr(atkTrigD, relTrigD + resetTrig);

    // PAR gate (shared): alternate attack/release on successive master clocks
    // step 0 = attack, step 1 = release
    parStep = Stepper.kr(masterTrig, resetTrig, 0, 1, 1, -1);
	atkTrigPar = masterTrig * (parStep < 0.5);
	relTrigPar = masterTrig * (parStep >= 0.5);
    gatePar = SetResetFF.kr(atkTrigPar, relTrigPar + resetTrig);

    // Select SEQ vs PAR gates
    gateA = Select.kr(modeSel, [gateA, gatePar]);
    gateB = Select.kr(modeSel, [gateB, gatePar]);
    gateC = Select.kr(modeSel, [gateC, gatePar]);
    gateD = Select.kr(modeSel, [gateD, gatePar]);

    // ---- LOOP MODE TRIGGERS ----
    loopTrigA = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateA.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]).max(1));
    loopTrigB = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateB.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]).max(1));
    loopTrigC = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateC.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]).max(1));
    loopTrigD = Impulse.kr(bpm / 60 * 32 / Select.kr(loopRateD.round.clip(0, 11),
        [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]).max(1));

    // ---- ENVELOPE GENERATION ----
    // SYNC: A-H-R using gate (matches hardware "sustain if attack finishes early")
    // LOOP: one-shot AR (self-trigger)

    envA = Select.kr(syncModeA.round.clip(0, 1), [
        EnvGen.kr(
            Env.asr(mapSyncTime.(effAtkA), 1.0, mapSyncTime.(effRelA), mapCurve.(curveA)),
            gateA
        ),
        makeEnv.(loopTrigA, effAtkA, effRelA, curveA, 1)
    ]);

    envB = Select.kr(syncModeB.round.clip(0, 1), [
        EnvGen.kr(
            Env.asr(mapSyncTime.(effAtkB), 1.0, mapSyncTime.(effRelB), mapCurve.(curveB)),
            gateB
        ),
        makeEnv.(loopTrigB, effAtkB, effRelB, curveB, 1)
    ]);

    envC = Select.kr(syncModeC.round.clip(0, 1), [
        EnvGen.kr(
            Env.asr(mapSyncTime.(effAtkC), 1.0, mapSyncTime.(effRelC), mapCurve.(curveC)),
            gateC
        ),
        makeEnv.(loopTrigC, effAtkC, effRelC, curveC, 1)
    ]);

    envD = Select.kr(syncModeD.round.clip(0, 1), [
        EnvGen.kr(
            Env.asr(mapSyncTime.(effAtkD), 1.0, mapSyncTime.(effRelD), mapCurve.(curveD)),
            gateD
        ),
        makeEnv.(loopTrigD, effAtkD, effRelD, curveD, 1)
    ]);

    // ---- OUTPUT SCALING ----
    // Convert 0-1 envelope to bipolar based on effective polarity
    // NORM (0): 0 to +1 -> output 0 to +1
    // INV (1): 0 to +1 -> output 0 to -1
    sigA = Select.kr(effPolA, [envA, envA.neg]);
    sigB = Select.kr(effPolB, [envB, envB.neg]);
    sigC = Select.kr(effPolC, [envC, envC.neg]);
    sigD = Select.kr(effPolD, [envD, envD.neg]);

    // ---- OUTPUT TO BUSES ----
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
    Out.kr(outD, sigD);
}).add;

"  [x] modARSeqPlus SynthDef loaded (4 AR envelopes, SEQ/PAR modes, globalAtk, globalRel, globalPolarity)".postln;
