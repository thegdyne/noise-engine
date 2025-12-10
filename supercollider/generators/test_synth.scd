/*
Test Synth Generator
Pulse + noise with envelope option

Parameters:
- FRQ: oscillator frequency (50 - 2000 Hz)
- CUT: filter cutoff (80 - 16000 Hz)
- RES: filter resonance
- ATK: envelope attack time
- DEC: envelope decay time
- ENV: OFF = drone, ON = triggered
- Filter Type: LP / HP / BP
*/

SynthDef(\testSynth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus, 
                       filterTypeBus, envEnabledBus, clockDivBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp;
    var env, trig, rate, envEnabled;
    
    freq = In.kr(freqBus).linexp(0, 1, 50, 2000);
    filterFreq = In.kr(cutoffBus).linexp(0, 1, 80, 16000);
    rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
    attack = In.kr(attackBus).linexp(0, 1, 0.001, 1);
    decay = In.kr(decayBus).linexp(0, 1, 0.001, 4);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    amp = In.kr(~params[\amplitude]);
    rate = In.kr(~params[\density]).linexp(0, 1, 0.5, 60);
    
    trig = Impulse.kr(rate);
    env = Select.kr(envEnabled, [
        1.0,
        EnvGen.kr(Env.perc(attack, decay), trig)
    ]);
    
    sig = Pulse.ar(freq, 0.5, 0.3) + PinkNoise.ar(0.2);
    
    sig = Select.ar(filterType, [
        LPF.ar(sig, filterFreq),
        HPF.ar(sig, filterFreq),
        BPF.ar(sig, filterFreq, rq)
    ]);
    
    sig = sig * env * amp * 0.15;
    
    Out.ar(out, sig ! 2);
}).add;

"  ✓ testSynth loaded".postln;
