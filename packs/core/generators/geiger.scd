// core/geiger — Lightweight end-stage generator
/*
Geiger Counter Generator
Radioactive click generator with Poisson distribution

Signal flow: Click generation -> Filter -> ENV VCA -> Output

Custom params:
  - P1 count_rate: 0.1-100 Hz (clicks/sec, Poisson)
  - P2 dead_time: 0-1 (tube recovery, click clustering)
  - P3 click_brightness: 0-1 (soft thud <-> sharp crack)
  - P4 click_decay: 0.01-1 (tube/speaker resonance)
  - P5 background_noise: 0-1 (tube hiss/crackle)
*/

SynthDef(\geiger, { |out, freqBus, customBus0|
    var sig, click, noise, freq;
    var p = In.kr(customBus0, 5);
    var countRate, deadTime, clickBrightness, clickDecay, backgroundNoise;
    var clickTrig, effectiveRate;

    freq = In.kr(freqBus);

    countRate = p[0];
    deadTime = p[1];
    clickBrightness = p[2];
    clickDecay = p[3];
    backgroundNoise = p[4];

    // === SOUND SOURCE ===
    effectiveRate = countRate / (1 + (deadTime * countRate * 0.1));
    clickTrig = Dust.ar(effectiveRate);

    click = EnvGen.ar(
        Env.perc(0.0001, clickDecay.linexp(0.01, 1, 0.005, 0.05)),
        clickTrig
    ) * WhiteNoise.ar;

    click = BPF.ar(click, freq.clip(20, 16000), 0.1) * 8;
    click = click + (HPF.ar(click, clickBrightness.linexp(0.001, 1, 200, 8000)) * clickBrightness * 2);

    noise = PinkNoise.ar * backgroundNoise * 0.5;
    noise = noise + (Dust.ar(countRate * 10) * 0.1 * backgroundNoise);

    sig = click + noise;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] geiger loaded".postln;
