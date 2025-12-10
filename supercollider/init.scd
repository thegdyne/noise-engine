/*
Noise Engine - SuperCollider Initialization
Multi-generator system with parameter buses
*/

s.waitForBoot({
    
    "=== Noise Engine - SuperCollider ===".postln;
    "Initializing parameter buses...".postln;
    
    // Parameter buses (shared between OSC and all generators)
    ~params = Dictionary.new;
    ~params[\gravity] = Bus.control(s, 1).set(0.5);
    ~params[\density] = Bus.control(s, 1).set(0.5);
    ~params[\filter_cutoff] = Bus.control(s, 1).set(0.7);
    ~params[\amplitude] = Bus.control(s, 1).set(0.5);
    
    // Generator instances (8 slots)
    ~generators = Dictionary.new;
    
    // Simple test synth (original)
    SynthDef(\testSynth, {
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
        
        sig = RLPF.ar(
            sig, 
            filterCutoff.linexp(0.0, 1.0, 30, 18000),
            0.2
        );
        
        sig = sig * amplitude * 0.4;
        Out.ar(0, sig ! 2);
    }).add;
    
    // Load PT2399 Grainy generator
    ("generators/pt2399_grainy.scd").loadRelative;
    
    // OSC responders - receive parameters from Python
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
    
    // Generator control - start/stop generators
    OSCdef(\startGenerator, { |msg|
        var slotID = msg[1].asInteger;
        var genType = msg[2].asSymbol;
        
        // Stop existing generator in this slot if any
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
        });
        
        // Start new generator
        ~generators[slotID] = Synth(genType);
        "Started % in slot %".format(genType, slotID).postln;
    }, '/noise/start_generator');
    
    OSCdef(\stopGenerator, { |msg|
        var slotID = msg[1].asInteger;
        
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
            "Stopped generator in slot %".format(slotID).postln;
        });
    }, '/noise/stop_generator');
    
    // Wait for server sync
    s.sync;
    
    "".postln;
    "✓ Noise Engine ready!".postln;
    "Available generators:".postln;
    "  - \\testSynth (simple pulsing noise)".postln;
    "  - \\pt2399Grainy (tape delay degradation)".postln;
    "".postln;
    
    // AUTO-START: Start test synth in slot 1
    ~generators[1] = Synth(\testSynth);
    "✓ Auto-started Test Synth in slot 1".postln;
    "".postln;
    
    "Listening for OSC on port 57120".postln;
    "Waiting for Python GUI connection...".postln;
});
