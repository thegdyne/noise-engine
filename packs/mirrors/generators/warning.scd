// mirrors/warning — Lightweight end-stage generator
SynthDef(\forge_mirrors_warning, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var alertLvl, pulse, siren, urgency, staticAmt;
    var carrier, amMod, sirenMod, tones, radioStatic;

    alertLvl = p[0];
    pulse = p[1];
    siren = p[2];
    urgency = p[3];
    staticAmt = p[4];

    freq = In.kr(freqBus);

    // Siren sweep modulation
    sirenMod = SinOsc.kr(siren.linexp(0, 1, 0.2, 2)).range(0.9, 1.1);
    freq = freq * sirenMod;

    // AM modulation - warning pulse
    amMod = SinOsc.kr(pulse.linexp(0, 1, 1, 8)).range(1 - (alertLvl * 0.6), 1);

    // Main carrier tone
    carrier = SinOsc.ar(freq, 0, 0.3) * amMod;

    // Additional warning tones - chorus spread
    tones = carrier;
    tones = tones + (SinOsc.ar(freq * 1.003, 0.2, 0.2) * amMod * alertLvl);
    tones = tones + (SinOsc.ar(freq * 0.997, 0.4, 0.2) * amMod * alertLvl);

    // Urgency harmonics
    tones = tones + SinOsc.ar(freq * 2, 0, 0.15 * urgency) * amMod;
    tones = tones + SinOsc.ar(freq * 3, 0, 0.1 * urgency) * amMod;
    tones = tones + SinOsc.ar(freq * 0.5, 0, 0.2 * (1 - urgency));

    // Sub pulse
    tones = tones + (SinOsc.ar(freq * 0.25, 0, 0.15) * LFPulse.kr(pulse.linexp(0, 1, 0.5, 4), 0, 0.5).lag(0.05));

    sig = tones;

    // Radio static
    radioStatic = BPF.ar(WhiteNoise.ar(0.3), 2000 + (freq * 2), 0.5) * 2;
    radioStatic = radioStatic * LFNoise0.kr(10 + (staticAmt * 20)).range(0, 1);
    sig = sig + (radioStatic * staticAmt);

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.06), 400);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_warning loaded".postln;
