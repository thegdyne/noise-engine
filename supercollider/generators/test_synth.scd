/*
Test Synth Generator
Pulse + noise with clock sync
*/

SynthDef(\testSynth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus, 
                       filterTypeBus, envEnabledBus, clockDivBus, clockTrigBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp;
    var env, envEnabled, clockDiv, clockTrig, dividedTrig;
    
    freq = In.kr(freqBus).linexp(0, 1, 50, 2000);
    filterFreq = In.kr(cutoffBus).linexp(0, 1, 80, 16000);
    rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
    attack = In.kr(attackBus).linexp(0, 1, 0.001, 1);
    decay = In.kr(decayBus).linexp(0, 1, 0.001, 4);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockDiv = In.kr(clockDivBus);
    amp = In.kr(~params[\amplitude]);
    
    clockTrig = In.ar(clockTrigBus);
    dividedTrig = PulseDivider.ar(clockTrig, clockDiv);
    
    env = Select.kr(envEnabled, [
        1.0,
        EnvGen.ar(Env.perc(attack, decay), dividedTrig)
    ]);
    
    sig = Pulse.ar(freq, 0.5, 0.3) + PinkNoise.ar(0.2);
    
    // RLPF/RHPF for resonance control
    sig = Select.ar(filterType, [
        RLPF.ar(sig, filterFreq, rq),
        RHPF.ar(sig, filterFreq, rq),
        BPF.ar(sig, filterFreq, rq)
    ]);
    
    sig = sig * env * amp * 0.15;
    
    Out.ar(out, sig ! 2);
}).add;

"  ✓ testSynth loaded".postln;
