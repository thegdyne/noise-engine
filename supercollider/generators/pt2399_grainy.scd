/*
PT2399 Grainy Generator
Granular noise bursts with filter and saturation

Parameters:
- FRQ: grain rate (0.5 - 80 Hz)
- CUT: filter cutoff (80 - 16000 Hz)
- RES: filter resonance
- ATK: grain attack time
- DEC: grain decay time
- Filter Type: LP / HP / BP
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockDivBus|
    var sig, grain, env, trig, rate, filterFreq, rq, filterType, attack, decay, amp;
    var panPos;
    
    // FRQ controls grain rate
    rate = In.kr(freqBus).linexp(0, 1, 0.5, 80);
    filterFreq = In.kr(cutoffBus).linexp(0, 1, 80, 16000);
    rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
    attack = In.kr(attackBus).linexp(0, 1, 0.001, 0.5);
    decay = In.kr(decayBus).linexp(0, 1, 0.01, 2);
    filterType = In.kr(filterTypeBus);
    amp = In.kr(~params[\amplitude]);
    
    // Trigger from FRQ
    trig = Impulse.kr(rate);
    env = EnvGen.kr(Env.perc(attack, decay), trig);
    
    // Clean noise source
    grain = WhiteNoise.ar(0.7);
    
    sig = grain * env;
    
    // Filter before distortion
    sig = Select.ar(filterType, [
        LPF.ar(sig, filterFreq),
        HPF.ar(sig, filterFreq),
        BPF.ar(sig, filterFreq, rq)
    ]);
    
    // Light saturation
    sig = (sig * 2).tanh * 0.6;
    
    // Random pan per grain
    panPos = TRand.kr(-1.0, 1.0, trig);
    sig = Pan2.ar(sig, panPos);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
