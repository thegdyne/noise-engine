/*
Test Synth Generator
Pulse + noise with clock sync

Parameters:
- FRQ: oscillator frequency (50 - 2000 Hz)
- CUT: filter cutoff (80 - 16000 Hz)
- RES: filter resonance
- ATK: envelope attack time
- DEC: envelope decay time
- ENV: OFF = drone, ON = clock sync
- CLK: clock division (1, 2, 4, 8, 16)
*/

SynthDef(\testSynth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus, 
                       filterTypeBus, envEnabledBus, clockDivBus, clockTrigBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp;
    var env, trig, envEnabled, clockDiv, clockTrig, dividedTrig;
    var divCount;
    
    // Read params
    freq = In.kr(freqBus).linexp(0, 1, 50, 2000);
    filterFreq = In.kr(cutoffBus).linexp(0, 1, 80, 16000);
    rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
    attack = In.kr(attackBus).linexp(0, 1, 0.001, 1);
    decay = In.kr(decayBus).linexp(0, 1, 0.001, 4);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockDiv = In.kr(clockDivBus);
    amp = In.kr(~params[\amplitude]);
    
    // Master clock trigger
    clockTrig = In.ar(clockTrigBus);
    
    // Divide clock
    divCount = PulseCount.ar(clockTrig);
    dividedTrig = Trig1.ar((divCount % clockDiv) < 0.5, 0.001) * clockTrig;
    
    // Convert to kr
    trig = Trig1.kr(A2K.kr(dividedTrig), 0.001);
    
    // ENV OFF = always on, ENV ON = triggered
    env = Select.kr(envEnabled, [
        1.0,
        EnvGen.kr(Env.perc(attack, decay), trig)
    ]);
    
    // Sound source
    sig = Pulse.ar(freq, 0.5, 0.3) + PinkNoise.ar(0.2);
    
    // Filter
    sig = Select.ar(filterType, [
        LPF.ar(sig, filterFreq),
        HPF.ar(sig, filterFreq),
        BPF.ar(sig, filterFreq, rq)
    ]);
    
    sig = sig * env * amp * 0.15;
    
    Out.ar(out, sig ! 2);
}).add;

"  ✓ testSynth loaded (with clock sync)".postln;
