/*
Dual Filter - Sherman-inspired
Dual resonant filters with tube overdrive, INSERT-only

Signal flow:
  masterBus → HPF(dc) → Drive → Filter1 ─┬─ Serial ─→ Filter2 → Mix → Output
                                         └─ Parallel → Mix → Output

Features:
  - Tube-style drive stage
  - Two resonant multimode filters (LP/BP/HP)
  - Harmonics sync (Filter2 = Filter1 / ratio)
  - Serial or parallel routing
  - Safety limiter for resonance
*/

~setupDualFilter = {
    "Setting up Dual Filter...".postln;
    
    // State defaults
    ~fbDrive = 0.0;
    ~fbFreq1 = 0.5;       // 0-1 maps to 20Hz-20kHz exp
    ~fbReso1 = 0.0;
    ~fbMode1 = 1;         // 0=LP, 1=BP, 2=HP
    ~fbFreq2 = 0.35;
    ~fbReso2 = 0.0;
    ~fbMode2 = 1;
    ~fbHarmonics = 0;     // 0=Free, 1-7 = sync ratios
    ~fbRouting = 0;       // 0=Serial, 1=Parallel
    ~fbMix = 1.0;
    ~fbBypass = 1;        // 1=bypassed
    
    SynthDef(\dualFilter, { |inBus, outBus, 
                             drive=0, freq1=0.5, reso1=0, mode1=1,
                             freq2=0.35, reso2=0, mode2=1,
                             harmonics=0, routing=0, mix=1, bypass=1|
        var sig, dry, wet;
        var f1hz, f2hz, rq1, rq2;
        var filt1, filt2, filtSerial, filtParallel;
        var harmonicRatios, syncedFreq2;
        
        // Harmonic ratios: Free/1/2/3/4/5/8/16
        harmonicRatios = #[1, 1, 2, 3, 4, 5, 8, 16];
        
        // Map freq 0-1 to 20Hz-20kHz exponential
        freq1 = VarLag.kr(freq1, 0.02);
        freq2 = VarLag.kr(freq2, 0.02);
        f1hz = freq1.linexp(0, 1, 20, 20000);
        
        // Apply harmonics sync if not Free (harmonics > 0)
        syncedFreq2 = f1hz / Select.kr(harmonics, harmonicRatios);
        f2hz = Select.kr(harmonics > 0, [
            freq2.linexp(0, 1, 20, 20000),  // Free: independent
            syncedFreq2                       // Synced
        ]);
        
        // Map reso 0-1 to rq (1 = no reso, 0.01 = max reso)
        reso1 = Lag.kr(reso1, 0.02);
        reso2 = Lag.kr(reso2, 0.02);
        rq1 = (1 - reso1).linexp(0, 1, 0.05, 1);
        rq2 = (1 - reso2).linexp(0, 1, 0.05, 1);
        
        // Smooth other params
        drive = Lag.kr(drive, 0.02);
        mix = Lag.kr(mix, 0.02);
        
        // Read input
        sig = In.ar(inBus, 2);
        dry = sig;
        
        // DC blocking HPF
        sig = HPF.ar(sig, 20);
        
        // Drive stage (tube-style soft saturation)
        sig = sig * (1 + (drive * 4));
        sig = (sig * 1.2).tanh * 0.85;
        
        // Filter 1 (multimode)
        filt1 = Select.ar(mode1, [
            RLPF.ar(sig, f1hz, rq1),   // LP
            BPF.ar(sig, f1hz, rq1),    // BP
            RHPF.ar(sig, f1hz, rq1)    // HP
        ]);
        
        // Filter 2 - Serial path (Filter1 → Filter2)
        filtSerial = Select.ar(mode2, [
            RLPF.ar(filt1, f2hz, rq2),
            BPF.ar(filt1, f2hz, rq2),
            RHPF.ar(filt1, f2hz, rq2)
        ]);
        
        // Filter 2 - Parallel path (input → Filter2, then mix with Filter1)
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
        sig = (dry * (1 - mix)) + (wet * mix);
        
        // Bypass (click-free)
        sig = Select.ar(Lag.kr(bypass, 0.02), [sig, dry]);
        
        ReplaceOut.ar(outBus, sig);
    }).add;
    
    "  ✓ Dual Filter SynthDef ready".postln;
};

~startDualFilter = {
    // Runs in masterGroup, after Heat
    ~fbSynth = Synth(\dualFilter, [
        \inBus, ~masterBus,
        \outBus, ~masterBus,
        \drive, ~fbDrive,
        \freq1, ~fbFreq1,
        \reso1, ~fbReso1,
        \mode1, ~fbMode1,
        \freq2, ~fbFreq2,
        \reso2, ~fbReso2,
        \mode2, ~fbMode2,
        \harmonics, ~fbHarmonics,
        \routing, ~fbRouting,
        \mix, ~fbMix,
        \bypass, ~fbBypass
    ], ~masterGroup, \addAfter);  // After Heat in master chain
    
    "  ✓ Dual Filter running (bypassed)".postln;
};

~setupDualFilterOSC = {
    OSCdef(\fbDrive, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbDrive = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\drive, val) };
    }, '/noise/master/fb/drive');
    
    OSCdef(\fbFreq1, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbFreq1 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\freq1, val) };
    }, '/noise/master/fb/freq1');
    
    OSCdef(\fbReso1, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbReso1 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\reso1, val) };
    }, '/noise/master/fb/reso1');
    
    OSCdef(\fbMode1, { |msg|
        var val = msg[1].asInteger.clip(0, 2);
        ~fbMode1 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\mode1, val) };
        ("  Filter 1 mode: " ++ #["LP", "BP", "HP"][val]).postln;
    }, '/noise/master/fb/mode1');
    
    OSCdef(\fbFreq2, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbFreq2 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\freq2, val) };
    }, '/noise/master/fb/freq2');
    
    OSCdef(\fbReso2, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~fbReso2 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\reso2, val) };
    }, '/noise/master/fb/reso2');
    
    OSCdef(\fbMode2, { |msg|
        var val = msg[1].asInteger.clip(0, 2);
        ~fbMode2 = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\mode2, val) };
        ("  Filter 2 mode: " ++ #["LP", "BP", "HP"][val]).postln;
    }, '/noise/master/fb/mode2');
    
    OSCdef(\fbHarmonics, { |msg|
        var val = msg[1].asInteger.clip(0, 7);
        ~fbHarmonics = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\harmonics, val) };
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
    }, '/noise/master/fb/mix');
    
    OSCdef(\fbBypass, { |msg|
        var val = msg[1].asInteger.clip(0, 1);
        ~fbBypass = val;
        if(~fbSynth.notNil) { ~fbSynth.set(\bypass, val) };
        ("  Dual Filter: " ++ if(val == 0, "ON", "BYPASSED")).postln;
    }, '/noise/master/fb/bypass');
    
    "  ✓ Dual Filter OSC handlers ready".postln;
};
