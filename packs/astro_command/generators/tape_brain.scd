// Tape Brain - Vintage tape computer sounds with mechanical artifacts
// Role: motion (movement/texture)

SynthDef(\forge_astro_command_tape_brain, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                             portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var spd, wow, flt, drp, sat;
    var baseFreq, wowMod, flutterMod, modFreq;
    var tapeOsc, dataBlips, dropout, saturation;

    // Standard bus reads
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

    // Custom params
    spd = In.kr(customBus0).linlin(0, 1, 0, 1);
    wow = In.kr(customBus1).linlin(0, 1, 0, 1);
    flt = In.kr(customBus2).linlin(0, 1, 0, 1);
    drp = In.kr(customBus3).linlin(0, 1, 0, 1);
    sat = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Base frequency with speed variation
    baseFreq = freq * spd.linlin(0, 1, 0.5, 2);

    // Wow - slow drift (0.5-2 Hz)
    wowMod = SinOsc.kr(LFNoise1.kr(0.2).range(0.5, 2)).range(
        1 - (wow * 0.05),
        1 + (wow * 0.05)
    );

    // Flutter - fast wobble (5-15 Hz)
    flutterMod = SinOsc.kr(LFNoise1.kr(1).range(5, 15)).range(
        1 - (flt * 0.02),
        1 + (flt * 0.02)
    );

    // Combined modulated frequency
    modFreq = baseFreq * wowMod * flutterMod;

    // Main tape oscillator - stepped/quantized feeling
    tapeOsc = Mix.ar([
        Pulse.ar(modFreq, LFNoise0.kr(spd.linlin(0, 1, 2, 8)).range(0.3, 0.7), 0.5),
        Pulse.ar(modFreq * 2, 0.5, 0.25),
        SinOsc.ar(modFreq * 0.5, 0, 0.3)
    ]);

    // Data blips - random high frequency bursts
    dataBlips = Ringz.ar(
        Dust.ar(spd.linlin(0, 1, 5, 20)),
        TRand.kr(2000, 6000, Dust.kr(8)),
        0.01
    ) * 0.2;

    // Dropout - random signal loss
    dropout = 1 - (Trig.ar(Dust.ar(drp.linlin(0, 1, 0, 5)), drp.linlin(0, 1, 0.01, 0.1)) * drp);

    // Combine
    sig = (tapeOsc + dataBlips) * dropout;

    // Tape saturation
    saturation = (sig * (1 + (sat * 3))).tanh;
    sig = sig.blend(saturation, sat);

    // Tape hiss
    sig = sig + (PinkNoise.ar(0.02) * sat);

    // Output chain
    sig = ~stereoSpread.(sig, 0.3, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_tape_brain loaded".postln;
