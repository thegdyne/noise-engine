/*
Noise Engine - SuperCollider Initialization
Master bus with always-on passthrough/effects
*/

s.waitForBoot({
    
    "=== Noise Engine - SuperCollider ===".postln;
    "Initializing parameter buses...".postln;
    
    ~params = Dictionary.new;
    ~params[\gravity] = Bus.control(s, 1).set(0.5);
    ~params[\density] = Bus.control(s, 1).set(0.5);
    ~params[\filter_cutoff] = Bus.control(s, 1).set(0.7);
    ~params[\amplitude] = Bus.control(s, 1).set(0.5);
    
    ~masterBus = Bus.audio(s, 2);
    
    ~generators = Dictionary.new;
    ~masterEffects = nil;
    
    SynthDef(\testSynth, {
        arg out;
        var sig, env, freq, rate, pitch;
        
        var gravity = In.kr(~params[\gravity]);
        var density = In.kr(~params[\density]);
        var filterCutoff = In.kr(~params[\filter_cutoff]);
        var amplitude = In.kr(~params[\amplitude]);
        
        pitch = gravity.linexp(0.0, 1.0, 20, 5000);
        rate = density.linexp(0.0, 1.0, 0.1, 100);
        
        env = LFPulse.ar(rate, 0, 0.3);
        sig = PinkNoise.ar(0.5) * env;
        sig = sig + (SinOsc.ar(pitch) * 0.3 * env);
        
        sig = RLPF.ar(sig, filterCutoff.linexp(0.0, 1.0, 30, 18000), 0.2);
        sig = sig * amplitude * 0.4;
        
        Out.ar(out, sig ! 2);
    }).add;
    
    ("generators/pt2399_grainy.scd").loadRelative;
    
    SynthDef(\masterPassthrough, {
        arg inBus, outBus=0, fidelityAmount=1.0;
        var sig, crushed, sampleRate, bandwidth;
        
        sig = In.ar(inBus, 2);
        
        crushed = fidelityAmount.linexp(0.0, 1.0, 4, 16);
        sig = sig.round(2.pow(crushed).reciprocal * 2) - 1;
        
        sampleRate = fidelityAmount.linexp(0.0, 1.0, 4000, 44100);
        sig = Latch.ar(sig, Impulse.ar(sampleRate));
        
        bandwidth = fidelityAmount.linexp(0.0, 1.0, 2000, 18000);
        sig = LPF.ar(sig, bandwidth);
        
        Out.ar(outBus, sig);
    }).add;
    
    OSCdef(\gravity, { |msg|
        ~params[\gravity].set(msg[1]);
    }, '/noise/gravity');
    
    OSCdef(\density, { |msg|
        ~params[\density].set(msg[1]);
    }, '/noise/density');
    
    OSCdef(\filterCutoff, { |msg|
        ~params[\filter_cutoff].set(msg[1]);
    }, '/noise/filter_cutoff');
    
    OSCdef(\amplitude, { |msg|
        ~params[\amplitude].set(msg[1]);
    }, '/noise/amplitude');
    
    OSCdef(\fidelityAmount, { |msg|
        var amount = msg[1];
        if(~masterEffects.notNil, {
            ~masterEffects.set(\fidelityAmount, amount);
        });
    }, '/noise/fidelity_amount');
    
    OSCdef(\startGenerator, { |msg|
        var slotID = msg[1].asInteger;
        var genType = msg[2].asSymbol;
        
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
        });
        
        ~generators[slotID] = Synth(genType, [\out, ~masterBus], addAction: \addToHead);
        "Started % in slot % -> master bus".format(genType, slotID).postln;
    }, '/noise/start_generator');
    
    OSCdef(\stopGenerator, { |msg|
        var slotID = msg[1].asInteger;
        
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
            "Stopped generator in slot %".format(slotID).postln;
        });
    }, '/noise/stop_generator');
    
    s.sync;
    
    ~masterEffects = Synth(\masterPassthrough, [
        \inBus, ~masterBus,
        \outBus, 0,
        \fidelityAmount, 1.0
    ], addAction: \addToTail);
    
    "".postln;
    "✓ Noise Engine ready!".postln;
    "✓ Master passthrough active".postln;
    "Available generators:".postln;
    "  - \\testSynth (simple pulsing noise)".postln;
    "  - \\pt2399Grainy (tape delay degradation)".postln;
    "Available effects:".postln;
    "  - Fidelity (bit crushing, sample rate reduction)".postln;
    "".postln;
    "Listening for OSC on port 57120".postln;
    "Waiting for Python GUI connection...".postln;
});
