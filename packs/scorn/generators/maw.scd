// maw: Organic mouth - breath, gurgle
SynthDef(\forge_scorn_maw, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var breath, gurgle, throat, teeth, saliva;
    var breathMod;

    // Theme params
    breath = In.kr(customBus0).linlin(0, 1, 0.1, 0.3);      // P1: Breath rate
    gurgle = In.kr(customBus1).linlin(0, 1, 3, 20);         // P2: Gurgle sounds
    throat = In.kr(customBus2).linlin(0, 1, 0.3, 0.9);      // P3: Throat resonance
    teeth = In.kr(customBus3).linlin(0, 1, 0, 0.4);         // P4: Teeth click
    saliva = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);      // P5: Wet saliva

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

    // DSP: Breathing - slow modulated noise
    breathMod = SinOsc.kr(breath).range(0.3, 1);
    sig = BPF.ar(PinkNoise.ar(throat * 0.5), freq * 2, 0.4) * breathMod;

    // Throat resonance - formant-like
    sig = sig + (Formant.ar(freq * 0.5, freq * 2, freq * 4) * throat * 0.25);

    // Gurgle - wet bubbling
    sig = sig + (Ringz.ar(Dust.ar(gurgle) * 0.15, freq * [1.5, 2, 2.5], 0.06) * saliva * 0.5);

    // Teeth clicks
    sig = sig + (HPF.ar(Dust.ar(teeth * 8) * 0.2, 2000) * teeth);

    // Saliva wetness
    sig = sig + (LPF.ar(Crackle.ar(1.8) * saliva * 0.2, 1500));

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_maw loaded".postln;
