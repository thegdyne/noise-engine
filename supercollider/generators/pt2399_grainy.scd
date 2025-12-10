/*
PT2399 Grainy Generator
Tape delay degradation with granular processing
Inspired by PT2399 IC characteristics: bit crushing, flutter, distortion
*/

SynthDef(\pt2399Grainy, {
    arg out=0;
    
    var sig, grain, env, trig, rate, pitch, crush, flutter;
    var gravity, density, filterCutoff, amplitude;
    var buf, pos, panPos;
    
    // Read parameters from control buses
    gravity = In.kr(~params[\gravity]);
    density = In.kr(~params[\density]);
    filterCutoff = In.kr(~params[\filter_cutoff]);
    amplitude = In.kr(~params[\amplitude]);
    
    // Grain trigger rate (0.5 - 120 Hz)
    rate = density.linexp(0.0, 1.0, 0.5, 120);
    trig = Impulse.kr(rate);
    
    // Grain pitch/playback rate (0.25 - 4.0)
    pitch = gravity.linexp(0.0, 1.0, 0.25, 4.0);
    
    // PT2399-style tape flutter (warble)
    flutter = LFNoise1.kr(3).range(0.95, 1.05);
    pitch = pitch * flutter;
    
    // Grain envelope (10ms - 200ms)
    env = EnvGen.kr(
        Env.perc(0.001, gravity.linexp(0.0, 1.0, 0.01, 0.2)),
        trig
    );
    
    // Noise source for grains
    grain = PinkNoise.ar(0.5);
    
    // PT2399-style bit crushing (16-bit down to 4-bit)
    crush = (1.0 - gravity).linexp(0.0, 1.0, 4, 16);
    grain = grain.round(2.pow(crush).reciprocal * 2) - 1;
    
    // Apply grain envelope
    sig = grain * env;
    
    // Sample rate reduction (tape degradation)
    sig = Latch.ar(sig, Impulse.ar(filterCutoff.linexp(0.0, 1.0, 2000, 44100)));
    
    // Resonant filter (tape head resonance)
    sig = RLPF.ar(
        sig,
        filterCutoff.linexp(0.0, 1.0, 200, 8000),
        0.3
    );
    
    // Tape saturation (soft clipping)
    sig = (sig * 2).tanh * 0.5;
    
    // Stereo spread with random panning per grain
    panPos = TRand.kr(-1.0, 1.0, trig);
    sig = Pan2.ar(sig, panPos);
    
    // Output with amplitude control
    sig = sig * amplitude * 0.4;
    
    Out.ar(out, sig);
}).add;

"✓ PT2399 Grainy generator loaded".postln;
