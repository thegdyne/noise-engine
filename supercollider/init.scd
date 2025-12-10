/*
Noise Engine - SuperCollider Initialization
Simple test synth that responds to OSC parameters from Python
*/

s.waitForBoot({
    
    "=== Noise Engine - SuperCollider ===".postln;
    "Waiting for OSC messages on port 57120...".postln;
    
    // Parameter buses (shared between OSC and synth)
    ~params = Dictionary.new;
    ~params[\gravity] = Bus.control(s, 1).set(0.5);
    ~params[\density] = Bus.control(s, 1).set(0.5);
    ~params[\filter_cutoff] = Bus.control(s, 1).set(0.7);
    ~params[\amplitude] = Bus.control(s, 1).set(0.5);
    
    // Simple test synth - filtered noise with modulation
    SynthDef(\noiseTest, {
        var sig, env, freq, rate, pitch;
        
        // Read parameters from buses
        var gravity = In.kr(~params[\gravity]);
        var density = In.kr(~params[\density]);
        var filterCutoff = In.kr(~params[\filter_cutoff]);
        var amplitude = In.kr(~params[\amplitude]);
        
        // Map gravity to pitch modulation (50 - 2000 Hz) - MORE RANGE!
        pitch = gravity.linexp(0.0, 1.0, 50, 2000);
        
        // Map density to pulse rate (0.5 - 30 Hz) - MORE RANGE!
        rate = density.linexp(0.0, 1.0, 0.5, 30);
        
        // Generate pulsing noise with pitch modulation
        env = LFPulse.ar(rate, 0, 0.3);
        
        // Use gravity to modulate the noise itself
        sig = PinkNoise.ar(0.5) * env;
        sig = sig + (SinOsc.ar(pitch) * 0.3 * env); // Add pitched component
        
        // Filter with cutoff control (100 - 12000 Hz) - WIDER RANGE!
        sig = RLPF.ar(
            sig, 
            filterCutoff.linexp(0.0, 1.0, 100, 12000),
            0.2
        );
        
        // Apply amplitude
        sig = sig * amplitude * 0.4;
        
        // Stereo output
        Out.ar(0, sig ! 2);
    }).add;
    
    // OSC responders - receive parameters from Python
    OSCdef(\gravity, { |msg|
        ~params[\gravity].set(msg[1]);
        "Gravity: %".format(msg[1]).postln;
    }, '/noise/gravity');
    
    OSCdef(\density, { |msg|
        ~params[\density].set(msg[1]);
        "Density: %".format(msg[1]).postln;
    }, '/noise/density');
    
    OSCdef(\filterCutoff, { |msg|
        ~params[\filter_cutoff].set(msg[1]);
        "Filter Cutoff: %".format(msg[1]).postln;
    }, '/noise/filter_cutoff');
    
    OSCdef(\amplitude, { |msg|
        ~params[\amplitude].set(msg[1]);
        "Amplitude: %".format(msg[1]).postln;
    }, '/noise/amplitude');
    
    // Start the synth after a brief delay
    s.sync;
    "Starting synth...".postln;
    ~synth = Synth(\noiseTest);
    "✓ Noise Engine ready!".postln;
    "Move sliders in Python GUI to control sound.".postln;
});
