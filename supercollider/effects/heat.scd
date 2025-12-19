/*
Heat - Saturation Module
Analog-style saturation with 4 circuit presets

Signal flow:
  Input → HPF (DC) → PreGain → Waveshaper → LPF (HF loss) → PostGain → Mix → Output

Circuits (same topology, different coefficients):
  0: CLEAN  - Subtle mixer warmth
  1: TAPE   - Woolly, rolled-off  
  2: TUBE   - Glowing sheen (even harmonics)
  3: CRUNCH - Gritty aggressive
*/

~setupHeat = {
    "Setting up Heat...".postln;
    
    // State defaults
    ~heatCircuit = 0;      // CLEAN
    ~heatDrive = 0.0;      // 0-1
    ~heatMix = 1.0;        // 0-1 wet/dry
    ~heatBypass = 1;       // 1 = bypassed
    
    SynthDef(\heat, { |inBus, outBus, circuit=0, drive=0, mix=1, bypass=1|
        var sig, dry, wet;
        var curve, asymmetry, hfLoss, preGain, postGain;
        var shaped, filtered;
        
        // Circuit coefficients [curve, asymmetry, hfLoss, preGain, postGain]
        // curve: 0=soft, 1=hard
        // asymmetry: 0=symmetric, 1=full asymmetric (even harmonics)
        // hfLoss: cutoff freq (20000 = none)
        var circuits = #[
            // CLEAN: subtle, symmetric, no HF loss
            [0.3, 0.0, 20000, 1.5, 0.9],
            // TAPE: soft, medium asymmetry, rolled off
            [0.4, 0.3, 8000, 2.0, 0.85],
            // TUBE: softer curve, high asymmetry (even harmonics), slight HF loss
            [0.25, 0.6, 12000, 2.5, 0.8],
            // CRUNCH: hard clip, medium asymmetry, slight HF loss
            [0.7, 0.35, 10000, 3.0, 0.7]
        ];
        
        // Select circuit coefficients with smoothing
        curve = Select.kr(circuit, circuits.flop[0]);
        asymmetry = Select.kr(circuit, circuits.flop[1]);
        hfLoss = Select.kr(circuit, circuits.flop[2]);
        preGain = Select.kr(circuit, circuits.flop[3]);
        postGain = Select.kr(circuit, circuits.flop[4]);
        
        // Smooth all params for click-free changes
        curve = VarLag.kr(curve, 0.05);
        asymmetry = VarLag.kr(asymmetry, 0.05);
        hfLoss = VarLag.kr(hfLoss, 0.05);
        preGain = VarLag.kr(preGain, 0.05);
        postGain = VarLag.kr(postGain, 0.05);
        drive = Lag.kr(drive, 0.02);
        mix = Lag.kr(mix, 0.02);
        
        // Read input
        sig = In.ar(inBus, 2);
        dry = sig;
        
        // DC blocking HPF
        sig = HPF.ar(sig, 20);
        
        // Drive stage (drive 0-1 maps to 1x-4x additional gain)
        sig = sig * preGain * (1 + (drive * 3));
        
        // Waveshaping with variable curve and asymmetry
        // Attempt: Combine tanh with asymmetry
        // asymmetry adds even harmonics by biasing the signal
        shaped = sig + (asymmetry * sig.abs * 0.3);
        
        // Variable curve: blend between soft (tanh) and hard (clip)
        shaped = (shaped.tanh * (1 - curve)) + (shaped.clip(-1, 1) * curve);
        
        // Apply post-gain compensation
        sig = shaped * postGain;
        
        // HF loss filter
        sig = LPF.ar(sig, hfLoss);
        
        // Wet/dry mix
        wet = sig;
        sig = (dry * (1 - mix)) + (wet * mix);
        
        // Bypass (click-free)
        sig = Select.ar(Lag.kr(bypass, 0.02), [sig, dry]);
        
        ReplaceOut.ar(outBus, sig);
    }).add;
    
    "  ✓ Heat SynthDef ready".postln;
};

~startHeat = {
    ~heatSynth = Synth(\heat, [
        \inBus, ~masterBus,
        \outBus, ~masterBus,
        \circuit, ~heatCircuit,
        \drive, ~heatDrive,
        \mix, ~heatMix,
        \bypass, ~heatBypass
    ], ~masterGroup, \addToHead);  // Head of master = first in chain
    
    "  ✓ Heat running (bypassed)".postln;
};

~setupHeatOSC = {
    OSCdef(\heatCircuit, { |msg|
        var idx = msg[1].asInteger.clip(0, 3);
        ~heatCircuit = idx;
        if(~heatSynth.notNil) {
            ~heatSynth.set(\circuit, idx);
        };
        ("  Heat circuit: " ++ #["CLEAN", "TAPE", "TUBE", "CRUNCH"][idx]).postln;
    }, '/noise/master/heat/circuit');
    
    OSCdef(\heatDrive, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~heatDrive = val;
        if(~heatSynth.notNil) {
            ~heatSynth.set(\drive, val);
        };
    }, '/noise/master/heat/drive');
    
    OSCdef(\heatMix, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~heatMix = val;
        if(~heatSynth.notNil) {
            ~heatSynth.set(\mix, val);
        };
    }, '/noise/master/heat/mix');
    
    OSCdef(\heatBypass, { |msg|
        var val = msg[1].asInteger.clip(0, 1);
        ~heatBypass = val;
        if(~heatSynth.notNil) {
            ~heatSynth.set(\bypass, val);
        };
        ("  Heat: " ++ if(val == 0, "ON", "BYPASSED")).postln;
    }, '/noise/master/heat/bypass');
    
    "  ✓ Heat OSC handlers ready".postln;
};
