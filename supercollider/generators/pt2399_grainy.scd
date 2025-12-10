/*
PT2399 Grainy Generator
Now supports routing to master bus
*/

SynthDef(\pt2399Grainy, {
    arg out=0;
    
    var sig, grain, env, trig, rate, pitch, crush, flutter;
    var gravity, density, filterCutoff, amplitude;
    var panPos;
    
    gravity = In.kr(~params[\gravity]);
    density = In.kr(~params[\density]);
    filterCutoff = In.kr(~params[\filter_cutoff]);
    amplitude = In.kr(~params[\amplitude]);
    
    rate = density.linexp(0.0, 1.0, 0.5, 120);
    trig = Impulse.kr(rate);
    
    pitch = gravity.linexp(0.0, 1.0, 0.25, 4.0);
    flutter = LFNoise1.kr(3).range(0.95, 1.05);
    pitch = pitch * flutter;
    
    env = EnvGen.kr(
        Env.perc(0.001, gravity.linexp(0.0, 1.0, 0.01, 0.2)),
        trig
    );
    
    grain = PinkNoise.ar(0.5);
    
    crush = (1.0 - gravity).linexp(0.0, 1.0, 4, 16);
    grain = grain.round(2.pow(crush).reciprocal * 2) - 1;
    
    sig = grain * env;
    
    sig = Latch.ar(sig, Impulse.ar(filterCutoff.linexp(0.0, 1.0, 2000, 44100)));
    
    sig = RLPF.ar(sig, filterCutoff.linexp(0.0, 1.0, 200, 8000), 0.3);
    
    sig = (sig * 2).tanh * 0.5;
    
    panPos = TRand.kr(-1.0, 1.0, trig);
    sig = Pan2.ar(sig, panPos);
    
    sig = sig * amplitude * 0.4;
    
    Out.ar(out, sig);
}).add;

"✓ PT2399 Grainy generator loaded".postln;
