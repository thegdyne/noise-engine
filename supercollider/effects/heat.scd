/*
Heat - Saturation Module
Analog-style saturation with 4 circuit presets

Signal flow:
  Input -> HPF (DC) -> PreGain -> Waveshaper -> LPF (HF loss) -> PostGain -> Mix -> Output

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
    
    SynthDef(\heat, { |inBus, outBus, circuit=0, drive=0, mix=1, bypass=1,
                        driveBus=(-1), mixBus=(-1)|
        var sig, dry, wet;
        var curve, asymmetry, hfLoss, preGain, postGain;
        var shaped, filtered;
        var driveEff, mixEff;

        // Bus unification: read from bus if valid index, otherwise use direct arg
        driveEff = Select.kr(driveBus >= 0, [drive, In.kr(driveBus)]);
        mixEff = Select.kr(mixBus >= 0, [mix, In.kr(mixBus)]);

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
        hfLoss = VarLag.kr(hfLoss, 0.05, warp: \exp);
        preGain = VarLag.kr(preGain, 0.05);
        postGain = VarLag.kr(postGain, 0.05);
        driveEff = Lag.kr(driveEff, 0.02);
        mixEff = Lag.kr(mixEff, 0.02);
        
        // Read input
        sig = In.ar(inBus, 2);
        dry = sig;
        
        // DC blocking HPF
        sig = HPF.ar(sig, 20);
        
        // Drive stage (drive 0-1 maps to 1x-4x additional gain)
        sig = sig * preGain * (1 + (driveEff * 3));
        
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
        sig = (dry * (1 - mixEff)) + (wet * mixEff);
        
        // Bypass (click-free)
        sig = XFade2.ar(sig, dry, (Lag.kr(bypass, 0.02) * 2) - 1);  // Crossfade bypass
        
        ReplaceOut.ar(outBus, sig);
    }).add;
    
    "  [x] Heat SynthDef ready".postln;
};

~startHeat = {
    // Get bus indices from bus unification (if available)
    var driveBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_heat_drive) ? -1 }, { -1 });
    var mixBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_heat_mix) ? -1 }, { -1 });

    ~heatSynth = Synth(\heat, [
        \inBus, ~masterBus,
        \outBus, ~masterBus,
        \circuit, ~heatCircuit,
        \drive, ~heatDrive,
        \mix, ~heatMix,
        \bypass, ~heatBypass,
        \driveBus, driveBusIdx,
        \mixBus, mixBusIdx
    ], ~masterGroup, \addToHead);  // Head of master = first in chain

    "  [x] Heat running (bypassed, buses: drive=%, mix=%)".format(driveBusIdx, mixBusIdx).postln;
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
        // Dual-write: both legacy .set() and bus unification
        if(~heatSynth.notNil) {
            ~heatSynth.set(\drive, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_heat_drive, val);
        };
    }, '/noise/master/heat/drive');

    OSCdef(\heatMix, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~heatMix = val;
        // Dual-write: both legacy .set() and bus unification
        if(~heatSynth.notNil) {
            ~heatSynth.set(\mix, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_heat_mix, val);
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
    
    "  [x] Heat OSC handlers ready".postln;
};
