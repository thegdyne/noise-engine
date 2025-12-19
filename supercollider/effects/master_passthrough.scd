/*
Master Passthrough Effect
Final output with EQ, Compressor, Limiter, master volume, and PRE/POST metering

Signal flow:
  masterBus -> PRE meter -> EQ -> LO CUT -> Compressor -> Limiter -> Master Vol -> POST meter -> output

Compressor sidechain:
  Post-EQ signal -> Peak Detector (dominant L/R) -> [SC HPF] -> Time Constants -> GR -> VCA
*/

~setupMasterPassthrough = {
    SynthDef(\masterPassthrough, { |inBus, outBus=0, masterVol=0.8, meterRate=24, meterMode=0,
                                    // Limiter
                                    limiterCeiling=0.99, limiterBypass=0,
                                    // EQ
                                    eqLoGain=0, eqMidGain=0, eqHiGain=0, 
                                    eqLoKill=0, eqMidKill=0, eqHiKill=0,
                                    eqLoCut=0, eqBypass=0,
                                    // Compressor - sensible defaults for bus compression
                                    compThreshold=(-10), compRatioIdx=1, compAttackIdx=4, compReleaseIdx=4,
                                    compMakeup=0, compScHpfIdx=0, compBypass=0|
        
        // Variable declarations (must be at top)
        var sig, sigPost;
        var preAmpL, preAmpR, prePeakL, prePeakR;
        var postAmpL, postAmpR, postPeakL, postPeakR;
        var ampL, ampR, peakL, peakR;
        var sigEQ, sigLimited, sigComp;
        var sigLo, sigMid, sigHi, sigRest;
        var loGainLin, midGainLin, hiGainLin;
        // Compressor variables
        var ratios, attacks, releases, scHpfFreqs;
        var ratio, attack, release, scHpfFreq;
        var scSig, detectorL, detectorR, detector;
        var thresholdLin, excessDb, gainReductionDb, grSmoothed;
        var gainReductionLin, grDb;
        var autoRelease, releaseTime;
        var makeupLin;
        
        sig = In.ar(inBus, 2);
        
        // PRE-fader metering (shows sum from channel strips, before any processing)
        preAmpL = Amplitude.kr(sig[0], attackTime: 0.01, releaseTime: 0.1);
        preAmpR = Amplitude.kr(sig[1], attackTime: 0.01, releaseTime: 0.1);
        prePeakL = Amplitude.kr(sig[0], attackTime: 0.001, releaseTime: 0.3);
        prePeakR = Amplitude.kr(sig[1], attackTime: 0.001, releaseTime: 0.3);
        
        // === DJ-Style 3-Band Isolator EQ ===
        // Clean LR4-style split: split at 250Hz first, then split "rest" at 2500Hz
        
        // First split: LO + REST
        sigLo = LPF.ar(LPF.ar(sig, 250), 250);
        sigRest = HPF.ar(HPF.ar(sig, 250), 250);
        
        // Second split: MID + HI from REST
        sigMid = LPF.ar(LPF.ar(sigRest, 2500), 2500);
        sigHi = HPF.ar(HPF.ar(sigRest, 2500), 2500);
        
        // Gain mapping: true kill at min, unity at center, +12dB at max
        // Select.kr(condition, [whenFalse, whenTrue])
        // When gain <= 0: condition TRUE (1) -> use cut/kill mapping
        // When gain > 0: condition FALSE (0) -> use boost mapping
        loGainLin = Select.kr(eqLoGain <= 0, [
            eqLoGain.linlin(0, 12, 0, 12).dbamp,       // gain > 0: boost range (0 to +12dB)
            eqLoGain.linlin(-12, 0, -80, 0).dbamp      // gain <= 0: cut/kill range (-80dB to 0dB)
        ]).lag(0.02);
        
        midGainLin = Select.kr(eqMidGain <= 0, [
            eqMidGain.linlin(0, 12, 0, 12).dbamp,
            eqMidGain.linlin(-12, 0, -80, 0).dbamp
        ]).lag(0.02);
        
        hiGainLin = Select.kr(eqHiGain <= 0, [
            eqHiGain.linlin(0, 12, 0, 12).dbamp,
            eqHiGain.linlin(-12, 0, -80, 0).dbamp
        ]).lag(0.02);
        
        // Apply kill buttons
        loGainLin = Select.kr(eqLoKill, [loGainLin, DC.kr(0)]);
        midGainLin = Select.kr(eqMidKill, [midGainLin, DC.kr(0)]);
        hiGainLin = Select.kr(eqHiKill, [hiGainLin, DC.kr(0)]);
        
        // Apply gains and sum
        sigEQ = (sigLo * loGainLin) + (sigMid * midGainLin) + (sigHi * hiGainLin);
        
        // LO CUT - HPF @ 75Hz (rumble filter, post-EQ)
        sigEQ = Select.ar(eqLoCut, [sigEQ, HPF.ar(sigEQ, 75)]);
        
        // EQ bypass
        sig = Select.ar(eqBypass, [sigEQ, sig]);
        
        // === SSL G-Style Bus Compressor ===
        
        // Fixed parameter arrays (SSL-style stepped controls)
        ratios = #[2, 4, 10];                                    // 2:1, 4:1, 10:1
        attacks = #[0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03];   // 0.1, 0.3, 1, 3, 10, 30 ms
        releases = #[0.1, 0.3, 0.6, 1.2, 0.3];                   // 0.1, 0.3, 0.6, 1.2s, [4]=Auto placeholder
        scHpfFreqs = #[30, 60, 90, 120, 185];                    // HPF options (idx 0 = bypass via Select)
        
        // Select current values from indices
        ratio = Select.kr(compRatioIdx.clip(0, 2), ratios);
        attack = Select.kr(compAttackIdx.clip(0, 5), attacks);
        release = Select.kr(compReleaseIdx.clip(0, 3), releases);  // Only 0-3 for fixed, 4=Auto handled below
        scHpfFreq = Select.kr((compScHpfIdx - 1).clip(0, 4), scHpfFreqs);  // idx 1-5 map to freqs
        
        // Sidechain signal - true bypass when idx=0, HPF when idx>0
        scSig = Select.ar(compScHpfIdx > 0, [
            sig,                           // idx 0: bypass (use raw signal)
            HPF.ar(sig, scHpfFreq)          // idx 1-5: apply HPF
        ]);
        
        // Peak detector - fixed fast attack for accurate peak detection
        // Attack is only applied in GR smoothing stage, not here
        // Dominant stereo: max of L/R controls both channels
        detectorL = Amplitude.kr(scSig[0], attackTime: 0.0001, releaseTime: 0.05);
        detectorR = Amplitude.kr(scSig[1], attackTime: 0.0001, releaseTime: 0.05);
        detector = max(detectorL, detectorR);
        
        // Convert to dB domain for gain computation
        thresholdLin = compThreshold.dbamp;
        
        // Calculate excess above threshold in dB
        excessDb = (detector / thresholdLin.max(0.0001)).ampdb.max(0);
        
        // Apply ratio to get gain reduction in dB
        // GR = excess * (1 - 1/ratio)
        gainReductionDb = excessDb * (1 - (1 / ratio));
        
        // Auto-release: dual-time behavior
        // Fast release (0.1s) for transients, slower (1.2s) when GR persists
        autoRelease = Select.kr(gainReductionDb > 3, [
            0.1,    // Light compression: fast release
            1.2     // Heavy compression: slow release
        ]);
        releaseTime = Select.kr(compReleaseIdx >= 4, [release, autoRelease]);
        
        // Smooth the gain reduction with attack/release
        grSmoothed = Lag2UD.kr(gainReductionDb, attack, releaseTime);
        
        // Convert back to linear gain
        gainReductionLin = grSmoothed.neg.dbamp;
        
        // Apply makeup gain
        makeupLin = compMakeup.dbamp;
        
        // Apply compression
        sigComp = sig * gainReductionLin * makeupLin;
        
        // GR for metering (positive value = amount of reduction)
        grDb = grSmoothed.clip(0, 20);
        
        // Send GR to Python
        SendReply.kr(
            Impulse.kr(meterRate),
            '/masterCompGR',
            [grDb]
        );
        
        // Compressor bypass
        sig = Select.ar(compBypass, [sigComp, sig]);
        
        // Limiter (brickwall, post-compressor)
        sigLimited = Limiter.ar(sig, limiterCeiling, 0.01);
        sig = Select.ar(limiterBypass, [sigLimited, sig]);
        
        // Master volume
        sigPost = sig * masterVol;
        
        // POST-fader metering
        postAmpL = Amplitude.kr(sigPost[0], attackTime: 0.01, releaseTime: 0.1);
        postAmpR = Amplitude.kr(sigPost[1], attackTime: 0.01, releaseTime: 0.1);
        postPeakL = Amplitude.kr(sigPost[0], attackTime: 0.001, releaseTime: 0.3);
        postPeakR = Amplitude.kr(sigPost[1], attackTime: 0.001, releaseTime: 0.3);
        
        // Select PRE or POST based on meterMode
        ampL = Select.kr(meterMode, [preAmpL, postAmpL]);
        ampR = Select.kr(meterMode, [preAmpR, postAmpR]);
        peakL = Select.kr(meterMode, [prePeakL, postPeakL]);
        peakR = Select.kr(meterMode, [prePeakR, postPeakR]);
        
        // Send levels to Python
        SendReply.kr(
            Impulse.kr(meterRate),
            '/masterLevelsInternal',
            [ampL, ampR, peakL, peakR]
        );
        
        Out.ar(outBus, sigPost);
    }).add;
    
    "  ✓ Master passthrough SynthDef ready (EQ, compressor, limiter)".postln;
};

~startMasterPassthrough = {
    // Track meter mode (0=PRE, 1=POST)
    ~masterMeterMode = 0;
    
    // Limiter defaults
    ~limiterCeiling = 0.99;  // -0.1dB
    ~limiterBypass = 0;
    
    // EQ defaults
    ~eqLoGain = 0;
    ~eqMidGain = 0;
    ~eqHiGain = 0;
    ~eqLoKill = 0;
    ~eqMidKill = 0;
    ~eqHiKill = 0;
    ~eqLoCut = 0;
    ~eqBypass = 0;
    
    // Compressor defaults - sensible bus compression starting point
    ~compThreshold = -10;    // -10dB threshold
    ~compRatioIdx = 1;       // 4:1
    ~compAttackIdx = 4;      // 10ms
    ~compReleaseIdx = 4;     // Auto
    ~compMakeup = 0;         // 0dB
    ~compScHpfIdx = 0;       // Off (true bypass)
    ~compBypass = 0;         // On
    
    // Forward internal meter replies to Python
    OSCdef(\meterForward, { |msg|
        ~pythonAddr.sendMsg('/noise/master/levels', msg[3], msg[4], msg[5], msg[6]);
    }, '/masterLevelsInternal');
    
    // Forward compressor GR to Python
    OSCdef(\compGRForward, { |msg|
        ~pythonAddr.sendMsg('/noise/master/comp/gr', msg[3]);
    }, '/masterCompGR');
    
    // Handle meter mode toggle
    OSCdef(\masterMeterToggle, { |msg|
        var mode = msg[1].asInteger.clip(0, 1);
        ~masterMeterMode = mode;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\meterMode, mode);
        };
        ("  Meter mode: " ++ if(mode == 0, "PRE", "POST")).postln;
    }, '/noise/master/meter/toggle');
    
    // Limiter handlers
    OSCdef(\limiterCeiling, { |msg|
        var db = msg[1].clip(-6, 0);
        var linear = db.dbamp;
        ~limiterCeiling = linear;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\limiterCeiling, linear);
        };
    }, '/noise/master/limiter/ceiling');
    
    OSCdef(\limiterBypass, { |msg|
        var bypass = msg[1].asInteger.clip(0, 1);
        ~limiterBypass = bypass;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\limiterBypass, bypass);
        };
        ("  Limiter: " ++ if(bypass == 0, "ON", "BYPASSED")).postln;
    }, '/noise/master/limiter/bypass');
    
    // === EQ OSC Handlers ===
    
    OSCdef(\eqLoGain, { |msg|
        var db = msg[1].clip(-12, 12);
        ~eqLoGain = db;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqLoGain, db);
        };
    }, '/noise/master/eq/lo');
    
    OSCdef(\eqMidGain, { |msg|
        var db = msg[1].clip(-12, 12);
        ~eqMidGain = db;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqMidGain, db);
        };
    }, '/noise/master/eq/mid');
    
    OSCdef(\eqHiGain, { |msg|
        var db = msg[1].clip(-12, 12);
        ~eqHiGain = db;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqHiGain, db);
        };
    }, '/noise/master/eq/hi');
    
    OSCdef(\eqLoKill, { |msg|
        var kill = msg[1].asInteger.clip(0, 1);
        ~eqLoKill = kill;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqLoKill, kill);
        };
    }, '/noise/master/eq/lo/kill');
    
    OSCdef(\eqMidKill, { |msg|
        var kill = msg[1].asInteger.clip(0, 1);
        ~eqMidKill = kill;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqMidKill, kill);
        };
    }, '/noise/master/eq/mid/kill');
    
    OSCdef(\eqHiKill, { |msg|
        var kill = msg[1].asInteger.clip(0, 1);
        ~eqHiKill = kill;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqHiKill, kill);
        };
    }, '/noise/master/eq/hi/kill');
    
    OSCdef(\eqLoCut, { |msg|
        var enabled = msg[1].asInteger.clip(0, 1);
        ~eqLoCut = enabled;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqLoCut, enabled);
        };
    }, '/noise/master/eq/locut');
    
    OSCdef(\eqBypass, { |msg|
        var bypass = msg[1].asInteger.clip(0, 1);
        ~eqBypass = bypass;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\eqBypass, bypass);
        };
        ("  EQ: " ++ if(bypass == 0, "ON", "BYPASSED")).postln;
    }, '/noise/master/eq/bypass');
    
    // === Compressor OSC Handlers ===
    
    OSCdef(\compThreshold, { |msg|
        var db = msg[1].clip(-20, 20);
        ~compThreshold = db;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\compThreshold, db);
        };
    }, '/noise/master/comp/threshold');
    
    OSCdef(\compRatio, { |msg|
        var idx = msg[1].asInteger.clip(0, 2);
        ~compRatioIdx = idx;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\compRatioIdx, idx);
        };
        ("  Comp ratio: " ++ #["2:1", "4:1", "10:1"][idx]).postln;
    }, '/noise/master/comp/ratio');
    
    OSCdef(\compAttack, { |msg|
        var idx = msg[1].asInteger.clip(0, 5);
        ~compAttackIdx = idx;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\compAttackIdx, idx);
        };
        ("  Comp attack: " ++ #["0.1", "0.3", "1", "3", "10", "30"][idx] ++ "ms").postln;
    }, '/noise/master/comp/attack');
    
    OSCdef(\compRelease, { |msg|
        var idx = msg[1].asInteger.clip(0, 4);
        ~compReleaseIdx = idx;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\compReleaseIdx, idx);
        };
        ("  Comp release: " ++ #["0.1s", "0.3s", "0.6s", "1.2s", "Auto"][idx]).postln;
    }, '/noise/master/comp/release');
    
    OSCdef(\compMakeup, { |msg|
        var db = msg[1].clip(0, 20);
        ~compMakeup = db;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\compMakeup, db);
        };
    }, '/noise/master/comp/makeup');
    
    OSCdef(\compScHpf, { |msg|
        var idx = msg[1].asInteger.clip(0, 5);
        ~compScHpfIdx = idx;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\compScHpfIdx, idx);
        };
        ("  Comp SC HPF: " ++ #["Off", "30Hz", "60Hz", "90Hz", "120Hz", "185Hz"][idx]).postln;
    }, '/noise/master/comp/sc_hpf');
    
    OSCdef(\compBypass, { |msg|
        var bypass = msg[1].asInteger.clip(0, 1);
        ~compBypass = bypass;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\compBypass, bypass);
        };
        ("  Compressor: " ++ if(bypass == 0, "ON", "BYPASSED")).postln;
    }, '/noise/master/comp/bypass');
    
    // Create the synth
    ~masterEffects = Synth(\masterPassthrough, [
        \inBus, ~masterBus,
        \outBus, 0,
        \masterVol, ~masterVolume ? 0.8,
        \meterRate, 24,
        \meterMode, ~masterMeterMode,
        // Limiter
        \limiterCeiling, ~limiterCeiling,
        \limiterBypass, ~limiterBypass,
        // EQ
        \eqLoGain, ~eqLoGain,
        \eqMidGain, ~eqMidGain,
        \eqHiGain, ~eqHiGain,
        \eqLoKill, ~eqLoKill,
        \eqMidKill, ~eqMidKill,
        \eqHiKill, ~eqHiKill,
        \eqLoCut, ~eqLoCut,
        \eqBypass, ~eqBypass,
        // Compressor
        \compThreshold, ~compThreshold,
        \compRatioIdx, ~compRatioIdx,
        \compAttackIdx, ~compAttackIdx,
        \compReleaseIdx, ~compReleaseIdx,
        \compMakeup, ~compMakeup,
        \compScHpfIdx, ~compScHpfIdx,
        \compBypass, ~compBypass
    ], ~masterGroup);
    
    "  ✓ Master passthrough running (EQ ON, compressor ON, limiter ON)".postln;
};
