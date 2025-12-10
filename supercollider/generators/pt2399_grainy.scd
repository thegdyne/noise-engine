/*
PT2399 Grainy Generator
Granular noise bursts with clock sync

Parameters:
- FRQ: grain rate when ENV off (free-running)
- CUT: filter cutoff (80 - 16000 Hz)
- RES: filter resonance
- ATK: grain attack time
- DEC: grain decay time
- ENV: OFF = free-running, ON = clock sync
- CLK: clock division (1, 2, 4, 8, 16)
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockDivBus, clockTrigBus|
    var sig, grain, env, trig, freeRate, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockDiv, clockTrig, dividedTrig;
    var divCount;
    
    // Read params
    freeRate = In.kr(freqBus).linexp(0, 1, 0.5, 80);
    filterFreq = In.kr(cutoffBus).linexp(0, 1, 80, 16000);
    rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
    attack = In.kr(attackBus).linexp(0, 1, 0.001, 0.5);
    decay = In.kr(decayBus).linexp(0, 1, 0.01, 2);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockDiv = In.kr(clockDivBus);
    amp = In.kr(~params[\amplitude]);
    
    // Master clock trigger
    clockTrig = In.ar(clockTrigBus);
    
    // Divide clock: count triggers and fire every N
    divCount = PulseCount.ar(clockTrig);
    dividedTrig = Trig1.ar((divCount % clockDiv) < 0.5, 0.001) * clockTrig;
    
    // Select trigger source
    trig = Select.ar(envEnabled, [
        Impulse.ar(freeRate),  // ENV OFF: free-running
        dividedTrig             // ENV ON: clock-synced
    ]);
    
    // Convert to kr for envelope
    trig = Trig1.kr(A2K.kr(trig), 0.001);
    
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

"  ✓ pt2399Grainy loaded (with clock sync)".postln;
