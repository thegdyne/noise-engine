/*
Dual Filter - Sherman-inspired
Dual resonant filters with tube overdrive, INSERT-only

Signal flow:
  masterBus -> HPF(dc) -> Drive -> Filter1 ??? Serial ?-> Filter2 -> Mix -> Output
                                         ?? Parallel -> Mix -> Output

Features:
  - Tube-style drive stage
  - Two resonant multimode filters (LP/BP/HP)
  - Tempo-synced LFO modulation of cutoff (per-filter sync rates)
  - Harmonics sync (Filter2 = Filter1 / ratio)
  - Serial or parallel routing
  - Safety limiter for resonance
*/

~setupDualFilter = {
    "Setting up Dual Filter...".postln;
    
    // State defaults (match GUI INI state)
    ~fbDrive = 0.0;
    ~fbFreq1 = 0.6;       // 60% = 120/200
    ~fbReso1 = 0.3;       // 30% = 60/200
    ~fbMode1 = 0;         // 0=LP
    ~fbFreq2 = 0.6;
    ~fbReso2 = 0.3;
    ~fbMode2 = 0;
    ~fbSync1Rate = 0;     // LFO rate multiplier (0 = free/off)
    ~fbSync2Rate = 0;
    ~fbSyncAmt = 0.0;     // Sync modulation depth 0-1
    ~fbHarmonics = 0;     // 0=Free, 1-7 = sync ratios
    ~fbRouting = 0;       // 0=Serial, 1=Parallel
    ~fbMix = 0.5;         // 50%
    ~fbBypass = 1;        // 1=bypassed
    
    // Rate string to multiplier lookup
    ~fbRateToMult = { |rateStr|
        case
        { rateStr == "" }     { 0 }
        { rateStr == "/32" }  { 1/32 }
        { rateStr == "/16" }  { 1/16 }
        { rateStr == "/12" }  { 1/12 }
        { rateStr == "/8" }   { 1/8 }
        { rateStr == "/4" }   { 1/4 }
        { rateStr == "/2" }   { 1/2 }
        { rateStr == "CLK" }  { 1 }
        { rateStr == "x2" }   { 2 }
        { rateStr == "x4" }   { 4 }
        { rateStr == "x8" }   { 8 }
        { rateStr == "x12" }  { 12 }
        { rateStr == "x16" }  { 16 }
        { rateStr == "x32" }  { 32 }
        { 0 };  // Default: no sync
    };

    // Convert rate string to clock bus index (-1 = off, 0-12 = clock rate)
    ~fbRateToIndex = { |rateStr|
        case
        { rateStr == "" }     { -1 }  // Off
        { rateStr == "/32" }  { 0 }
        { rateStr == "/16" }  { 1 }
        { rateStr == "/12" }  { 2 }
        { rateStr == "/8" }   { 3 }
        { rateStr == "/4" }   { 4 }
        { rateStr == "/2" }   { 5 }
        { rateStr == "CLK" }  { 6 }
        { rateStr == "x2" }   { 7 }
        { rateStr == "x4" }   { 8 }
        { rateStr == "x8" }   { 9 }
        { rateStr == "x12" }  { 10 }
        { rateStr == "x16" }  { 11 }
        { rateStr == "x32" }  { 12 }
        { -1 };  // Default: off
    };

    SynthDef(\dualFilter, { |inBus, outBus, bpmBus, clockTrigBus,
                             drive=0, freq1=0.6, reso1=0.3, mode1=0,
                             freq2=0.6, reso2=0.3, mode2=0,
                             sync1Rate=0, sync2Rate=0, sync1Idx=(-1), sync2Idx=(-1), syncAmt=0,
                             harmonics=0, routing=0, mix=0.5, bypass=1,
                             driveBus=(-1), freq1Bus=(-1), freq2Bus=(-1),
                             reso1Bus=(-1), reso2Bus=(-1), syncAmtBus=(-1),
                             harmonicsBus=(-1), mixBus=(-1)|
        var sig, dry, wet;
        var f1hz, f2hz, f1base, f2base, rq1, rq2;
        var filt1, filt2, filtSerial, filtParallel;
        var harmonicRatios, syncedFreq2;
        var lfo1, lfo2, tempoHz;
        var driveEff, freq1Eff, freq2Eff, reso1Eff, reso2Eff, syncAmtEff, harmonicsEff, mixEff;
        var allTrigs, sync1On, sync1IdxClamped, sync1Trig, sync1TrigK, phase1;
        var sync2On, sync2IdxClamped, sync2Trig, sync2TrigK, phase2;

        // Bus unification: read from bus if valid index, otherwise use direct arg
        driveEff = Select.kr(driveBus >= 0, [drive, In.kr(driveBus)]);
        freq1Eff = Select.kr(freq1Bus >= 0, [freq1, In.kr(freq1Bus)]);
        freq2Eff = Select.kr(freq2Bus >= 0, [freq2, In.kr(freq2Bus)]);
        reso1Eff = Select.kr(reso1Bus >= 0, [reso1, In.kr(reso1Bus)]);
        reso2Eff = Select.kr(reso2Bus >= 0, [reso2, In.kr(reso2Bus)]);
        syncAmtEff = Select.kr(syncAmtBus >= 0, [syncAmt, In.kr(syncAmtBus)]);
        harmonicsEff = Select.kr(harmonicsBus >= 0, [harmonics, In.kr(harmonicsBus)]);
        mixEff = Select.kr(mixBus >= 0, [mix, In.kr(mixBus)]);
        
        // Harmonic ratios: Free/1/2/3/4/5/8/16
        harmonicRatios = #[1, 1, 2, 3, 4, 5, 8, 16];
        
        // Get tempo in Hz from BPM bus (BPM / 60 = beats per second)
        tempoHz = In.kr(bpmBus) / 60;

        // Phase-locked triangle LFOs using clock trigger reset
        // sync1Idx/sync2Idx: -1 = off, 0-12 = clock rate index
        allTrigs = In.ar(clockTrigBus, 13);

        // LFO 1: phase-locked to clock
        sync1On = (sync1Idx >= 0);
        sync1IdxClamped = sync1Idx.clip(0, 12);
        sync1Trig = Select.ar(sync1IdxClamped, allTrigs) * sync1On;  // Gate when off
        sync1TrigK = A2K.kr(Trig1.ar(sync1Trig, ControlDur.ir * 2));
        phase1 = Phasor.kr(sync1TrigK, sync1Rate * tempoHz * ControlDur.ir, 0, 1, 0);
        lfo1 = Select.kr(sync1On, [
            DC.kr(1),
            (1 - (phase1 * 2 - 1).abs).linlin(0, 1, 0.01, 1)  // Triangle: 0.01-1 (never 0)
        ]);

        // LFO 2: phase-locked to clock
        sync2On = (sync2Idx >= 0);
        sync2IdxClamped = sync2Idx.clip(0, 12);
        sync2Trig = Select.ar(sync2IdxClamped, allTrigs) * sync2On;  // Gate when off
        sync2TrigK = A2K.kr(Trig1.ar(sync2Trig, ControlDur.ir * 2));
        phase2 = Phasor.kr(sync2TrigK, sync2Rate * tempoHz * ControlDur.ir, 0, 1, 0);
        lfo2 = Select.kr(sync2On, [
            DC.kr(1),
            (1 - (phase2 * 2 - 1).abs).linlin(0, 1, 0.01, 1)  // Triangle: 0.01-1 (never 0)
        ]);
        
        // Smooth params
        freq1Eff = VarLag.kr(freq1Eff, 0.02, warp: \exp);
        freq2Eff = VarLag.kr(freq2Eff, 0.02, warp: \exp);
        syncAmtEff = Lag.kr(syncAmtEff, 0.05);

        // Base frequencies (exponential mapping)
        f1base = freq1Eff.linexp(0, 1, 20, 20000);
        f2base = freq2Eff.linexp(0, 1, 20, 20000);

        // Apply sync modulation: sweeps from (1-amt)*freq up to freq
        // amt=0 -> no sweep, amt=1 -> full sweep from near-zero to freq
        f1hz = f1base * ((1 - syncAmtEff) + (syncAmtEff * lfo1));
        f2hz = f2base * ((1 - syncAmtEff) + (syncAmtEff * lfo2));

        // Apply harmonics sync if not Free (harmonics > 0)
        syncedFreq2 = f1hz / Select.kr(harmonicsEff.round, harmonicRatios);
        f2hz = Select.kr(harmonicsEff > 0, [
            f2hz,        // Free: use independent freq (with sync mod)
            syncedFreq2  // Synced to filter1
        ]);

        // Map reso 0-1 to rq (1 = no reso, 0.05 = max reso)
        reso1Eff = Lag.kr(reso1Eff, 0.02);
        reso2Eff = Lag.kr(reso2Eff, 0.02);
        rq1 = (1 - reso1Eff).linexp(0, 1, 0.05, 1);
        rq2 = (1 - reso2Eff).linexp(0, 1, 0.05, 1);

        // Smooth other params
        driveEff = Lag.kr(driveEff, 0.02);
        mixEff = Lag.kr(mixEff, 0.02);
        
        // Read input
        sig = In.ar(inBus, 2);
        dry = sig;
        
        // DC blocking HPF
        sig = HPF.ar(sig, 20);

        // Drive stage (tube-style soft saturation)
        sig = sig * (1 + (driveEff * 4));
        sig = (sig * 1.2).tanh * 0.85;
        
        // Filter 1 (multimode)
        filt1 = Select.ar(mode1, [
            RLPF.ar(sig, f1hz, rq1),   // LP
            BPF.ar(sig, f1hz, rq1),    // BP
            RHPF.ar(sig, f1hz, rq1)    // HP
        ]);
        
        // Filter 2 - Serial path (Filter1 -> Filter2)
        filtSerial = Select.ar(mode2, [
            RLPF.ar(filt1, f2hz, rq2),
            BPF.ar(filt1, f2hz, rq2),
            RHPF.ar(filt1, f2hz, rq2)
        ]);
        
        // Filter 2 - Parallel path (input -> Filter2, then mix with Filter1)
        filt2 = Select.ar(mode2, [
            RLPF.ar(sig, f2hz, rq2),
            BPF.ar(sig, f2hz, rq2),
            RHPF.ar(sig, f2hz, rq2)
        ]);
        filtParallel = (filt1 + filt2) * 0.5;
        
        // Select routing
        wet = Select.ar(routing, [filtSerial, filtParallel]);
        
        // Safety limiter (catch resonance spikes)
        wet = Limiter.ar(wet, 0.95, 0.01);
        
        // Wet/dry mix
        sig = (dry * (1 - mixEff)) + (wet * mixEff);
        
        // Bypass (click-free)
        sig = XFade2.ar(sig, dry, (Lag.kr(bypass, 0.02) * 2) - 1);
        
        ReplaceOut.ar(outBus, sig);
    }).add;
    
    "  [x] Dual Filter SynthDef ready".postln;
};

~startDualFilter = {
    var target, action;
    // Get bus indices from bus unification (if available)
    var driveBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_drive) ? -1 }, { -1 });
    var freq1BusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_freq1) ? -1 }, { -1 });
    var freq2BusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_freq2) ? -1 }, { -1 });
    var reso1BusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_reso1) ? -1 }, { -1 });
    var reso2BusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_reso2) ? -1 }, { -1 });
    var syncAmtBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_syncAmt) ? -1 }, { -1 });
    var harmonicsBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_harmonics) ? -1 }, { -1 });
    var mixBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_fb_mix) ? -1 }, { -1 });

    // If Heat exists, insert directly after it; otherwise head of master
    target = if(~heatSynth.notNil, { ~heatSynth }, { ~masterGroup });
    action = if(~heatSynth.notNil, { \addAfter }, { \addToHead });

    ~fbSynth = Synth(\dualFilter, [
        \inBus, ~masterBus,
        \outBus, ~masterBus,
        \bpmBus, ~clockBus.index,
        \clockTrigBus, ~clockTrigBus.index,
        \drive, ~fbDrive,
        \freq1, ~fbFreq1,
        \reso1, ~fbReso1,
        \mode1, ~fbMode1,
        \freq2, ~fbFreq2,
        \reso2, ~fbReso2,
        \mode2, ~fbMode2,
        \sync1Rate, ~fbSync1Rate,
        \sync2Rate, ~fbSync2Rate,
        \syncAmt, ~fbSyncAmt,
        \harmonics, ~fbHarmonics,
        \routing, ~fbRouting,
        \mix, ~fbMix,
        \bypass, ~fbBypass,
        \driveBus, driveBusIdx,
        \freq1Bus, freq1BusIdx,
        \freq2Bus, freq2BusIdx,
        \reso1Bus, reso1BusIdx,
        \reso2Bus, reso2BusIdx,
        \syncAmtBus, syncAmtBusIdx,
        \harmonicsBus, harmonicsBusIdx,
        \mixBus, mixBusIdx
    ], target, action);

    "  [x] Dual Filter running (bypassed)".postln;
};

~setupDualFilterOSC = {
    OSCdef(\fbDrive, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbDrive = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\drive, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_drive, val) };
    }, '/noise/master/fb/drive');

    OSCdef(\fbFreq1, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbFreq1 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\freq1, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_freq1, val) };
    }, '/noise/master/fb/freq1');

    OSCdef(\fbReso1, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbReso1 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\reso1, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_reso1, val) };
    }, '/noise/master/fb/reso1');
    
    OSCdef(\fbMode1, { |msg|
        var val = msg[1].asInteger.clip(0, 2);
        ~fbMode1 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\mode1, val) };
        ("  Filter 1 mode: " ++ #["LP", "BP", "HP"][val]).postln;
    }, '/noise/master/fb/mode1');
    
    OSCdef(\fbSync1, { |msg|
        var rateStr = msg[1].asString;
        var mult = ~fbRateToMult.(rateStr);
        var idx = ~fbRateToIndex.(rateStr);
        ~fbSync1Rate = mult;
        if(~fbSynth.notNil) {
            ~fbSynth.set(\sync1Rate, mult);
            ~fbSynth.set(\sync1Idx, idx);
        };
        ("  Filter 1 sync: " ++ if(mult == 0, "FREE", rateStr)).postln;
    }, '/noise/master/fb/sync1');
    
    OSCdef(\fbFreq2, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbFreq2 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\freq2, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_freq2, val) };
    }, '/noise/master/fb/freq2');

    OSCdef(\fbReso2, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbReso2 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\reso2, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_reso2, val) };
    }, '/noise/master/fb/reso2');
    
    OSCdef(\fbMode2, { |msg|
        var val = msg[1].asInteger.clip(0, 2);
        ~fbMode2 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\mode2, val) };
        ("  Filter 2 mode: " ++ #["LP", "BP", "HP"][val]).postln;
    }, '/noise/master/fb/mode2');
    
    OSCdef(\fbSync2, { |msg|
        var rateStr = msg[1].asString;
        var mult = ~fbRateToMult.(rateStr);
        var idx = ~fbRateToIndex.(rateStr);
        ~fbSync2Rate = mult;
        if(~fbSynth.notNil) {
            ~fbSynth.set(\sync2Rate, mult);
            ~fbSynth.set(\sync2Idx, idx);
        };
        ("  Filter 2 sync: " ++ if(mult == 0, "FREE", rateStr)).postln;
    }, '/noise/master/fb/sync2');
    
    OSCdef(\fbSyncAmt, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbSyncAmt = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\syncAmt, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_syncAmt, val) };
    }, '/noise/master/fb/syncAmt');

    OSCdef(\fbHarmonics, { |msg|
        var val = msg[1].asInteger.clip(0, 7);
        ~fbHarmonics = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\harmonics, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_harmonics, val) };
        ("  Harmonics: " ++ #["Free", "1", "2", "3", "4", "5", "8", "16"][val]).postln;
    }, '/noise/master/fb/harmonics');
    
    OSCdef(\fbRouting, { |msg|
        var val = msg[1].asInteger.clip(0, 1);
        ~fbRouting = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\routing, val) };
        ("  Routing: " ++ #["Serial", "Parallel"][val]).postln;
    }, '/noise/master/fb/routing');
    
    OSCdef(\fbMix, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbMix = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\mix, val) };
        if(~queueBaseUpdate.notNil) { ~queueBaseUpdate.(\fx_fb_mix, val) };
    }, '/noise/master/fb/mix');
    
    OSCdef(\fbBypass, { |msg|
        var val = msg[1].asInteger.clip(0, 1);
        ~fbBypass = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\bypass, val) };
        ("  Dual Filter: " ++ if(val == 0, "ON", "BYPASSED")).postln;
    }, '/noise/master/fb/bypass');
    
    "  [x] Dual Filter OSC handlers ready".postln;
};
