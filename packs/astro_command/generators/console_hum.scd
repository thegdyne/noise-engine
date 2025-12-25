// Console Hum - Layered mains hum with transformer saturation and CRT whine
// Role: bed (foundation layer)

SynthDef(\forge_astro_command_console_hum, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var hum, tfr, crt, flk, age;
    var mainsHum, transformer, crtWhine, flicker, ageNoise;
    var humFreq, harmonics;

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
    hum = In.kr(customBus0).linlin(0, 1, 0, 1);
    tfr = In.kr(customBus1).linlin(0, 1, 0, 1);
    crt = In.kr(customBus2).linlin(0, 1, 0, 1);
    flk = In.kr(customBus3).linlin(0, 1, 0, 1);
    age = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Mains hum at 50Hz with harmonics (scaled by freq)
    humFreq = freq.linlin(20, 8000, 40, 80);
    harmonics = Mix.ar([
        SinOsc.ar(humFreq, 0, 1),
        SinOsc.ar(humFreq * 2, 0, 0.5),
        SinOsc.ar(humFreq * 3, 0, 0.3),
        SinOsc.ar(humFreq * 4, 0, 0.2),
        SinOsc.ar(humFreq * 5, 0, 0.1)
    ]);
    mainsHum = harmonics * hum;

    // Transformer saturation - soft clip the hum
    transformer = (mainsHum * (1 + (tfr * 4))).tanh * (1 + (tfr * 0.5));

    // CRT whine - high frequency with slight wobble
    crtWhine = SinOsc.ar(
        freq.linlin(20, 8000, 12000, 16000) + LFNoise1.kr(3).range(-50, 50),
        0,
        crt * 0.15
    );

    // Fluorescent flicker - amplitude modulation
    flicker = LFNoise2.kr(
        LFNoise0.kr(0.5).range(80, 140)
    ).range(1 - (flk * 0.3), 1);

    // Age noise - adds hiss and crackle
    ageNoise = (
        PinkNoise.ar(age * 0.05) +
        Dust.ar(age.linlin(0, 1, 0, 30), age * 0.1)
    );

    // Combine all elements
    sig = (transformer * flicker) + crtWhine + ageNoise;

    // Output chain
    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_console_hum loaded".postln;
