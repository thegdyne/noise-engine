// boom: 808-style sub bass kick
SynthDef(\forge_bed_stuy_boom, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sub, punch, length, drive, click;
    var kickEnv;

    // Theme params
    sub = In.kr(customBus0).linlin(0, 1, 0.3, 1);           // P1: Sub level
    punch = In.kr(customBus1).linlin(0, 1, 0.1, 0.7);       // P2: Attack punch
    length = In.kr(customBus2).linlin(0, 1, 0.1, 0.8);      // P3: Decay length
    drive = In.kr(customBus3).linlin(0, 1, 1, 3);           // P4: Saturation drive
    click = In.kr(customBus4).linlin(0, 1, 0, 0.5);         // P5: Click transient

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // DSP: Continuous sub bass with pulse modulation
    kickEnv = LFPulse.kr(1, 0, 0.15).lag(0.005, length * 0.5);

    // Sub oscillator
    sig = SinOsc.ar(freq * 0.5) * sub;

    // Pitch envelope for punch
    sig = sig + (SinOsc.ar(freq * 0.5 * (1 + (kickEnv * punch * 2))) * punch * kickEnv * 0.5);

    // Click transient
    sig = sig + (HPF.ar(Dust.ar(2) * click, 1000) * kickEnv);

    // Saturation
    sig = (sig * drive).tanh;

    // Continuous low drone underneath
    sig = sig + (SinOsc.ar(freq * 0.25) * 0.2);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_boom loaded".postln;
