/*
PT2399 Grainy Generator
Granular noise bursts with clock sync
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockDivBus, clockTrigBus|
    var sig, grain, env, trig, freeRate, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockDiv, clockTrig, dividedTrig, freeTrig;
    
    freeRate = In.kr(freqBus).linexp(0, 1, 0.5, 80);
    filterFreq = In.kr(cutoffBus).linexp(0, 1, 80, 16000);
    rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
    attack = In.kr(attackBus).linexp(0, 1, 0.001, 0.5);
    decay = In.kr(decayBus).linexp(0, 1, 0.01, 2);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockDiv = In.kr(clockDivBus);
    amp = In.kr(~params[\amplitude]);
    
    freeTrig = Impulse.ar(freeRate);
    clockTrig = In.ar(clockTrigBus);
    dividedTrig = PulseDivider.ar(clockTrig, clockDiv);
    
    trig = Select.ar(envEnabled, [
        freeTrig,
        dividedTrig
    ]);
    
    env = EnvGen.ar(Env.perc(attack, decay), trig);
    
    grain = WhiteNoise.ar(0.7);
    sig = grain * env;
    
    // RLPF/RHPF for resonance control
    sig = Select.ar(filterType, [
        RLPF.ar(sig, filterFreq, rq),
        RHPF.ar(sig, filterFreq, rq),
        BPF.ar(sig, filterFreq, rq)
    ]);
    
    sig = (sig * 2).tanh * 0.6;
    
    panPos = TRand.ar(-1.0, 1.0, trig);
    sig = Pan2.ar(sig, panPos);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
