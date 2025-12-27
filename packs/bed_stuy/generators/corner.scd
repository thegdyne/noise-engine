// corner: Street corner ambience
SynthDef(\forge_bed_stuy_corner, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var traffic, voices, sirens, subway, night;

    // Theme params
    traffic = In.kr(customBus0).linlin(0, 1, 0.2, 0.7);     // P1: Traffic drone
    voices = In.kr(customBus1).linlin(0, 1, 0, 0.4);        // P2: Distant voices
    sirens = In.kr(customBus2).linlin(0, 1, 0, 0.3);        // P3: Siren wail
    subway = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);      // P4: Subway rumble
    night = In.kr(customBus4).linlin(0, 1, 500, 3000);      // P5: Night filter

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

    // DSP: Traffic - continuous filtered noise
    sig = LPF.ar(BrownNoise.ar(traffic), 300) * 0.6;

    // Distant voices - filtered bursts
    sig = sig + (BPF.ar(PinkNoise.ar(voices), freq * 4 * LFNoise0.kr(0.5).range(0.8, 1.2), 0.2) * LFNoise1.kr(0.3).range(0.3, 1));

    // Siren wail - distant
    sig = sig + (SinOsc.ar(800 * LFTri.kr(0.3).range(0.9, 1.5)) * sirens * LFNoise1.kr(0.1).range(0, 1) * 0.1);

    // Subway rumble
    sig = sig + (LPF.ar(PinkNoise.ar(subway), 80) * LFNoise1.kr(0.05).range(0.3, 1));

    // Night filter
    sig = LPF.ar(sig, night);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_corner loaded".postln;
