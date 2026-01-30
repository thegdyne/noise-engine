// pripyat/music — Lightweight end-stage generator
SynthDef(\forge_pripyat_music, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var brok, pipe, whee, rust, memo;
    var pipes, wheezeSig, memoSig, detuneAmt;

    freq = In.kr(freqBus);

    brok = p[0];
    pipe = p[1];
    whee = p[2];
    rust = p[3];
    memo = p[4];

    // Detune amount based on broken-ness
    detuneAmt = brok.linlin(0, 1, 0.001, 0.05);

    // Organ pipes - additive synthesis with detuning (no var inside block)
    pipes = Mix.fill(8, { |i|
        SinOsc.ar(
            freq * (i + 1) * LFNoise2.kr(0.1 + (i * 0.02)).range(1 - detuneAmt, 1 + detuneAmt),
            0,
            (1 / (i + 1))
            * (LFNoise2.kr(0.05 + (i * 0.01)).range(0, 1) < pipe).asInteger
            * ((1 - rust).pow(i * 0.3))
            * LFNoise2.kr(0.3 + (i * 0.1)).range(0.8, 1)
        );
    });

    pipes = pipes * 0.4;

    // Air wheeze - breathy leaking pipes
    wheezeSig = BPF.ar(PinkNoise.ar(1), freq * LFNoise2.kr(0.5).range(0.5, 2), 0.3);
    wheezeSig = wheezeSig * LFNoise2.kr(2).range(0, 1);
    wheezeSig = wheezeSig * whee * 0.5;

    // Melody fragments - occasional pitch shifts suggesting melody
    memoSig = SinOsc.ar(freq * Select.kr(LFNoise0.kr(memo.linexp(0, 1, 0.1, 1)).range(0, 5).round, [1, 1.25, 1.5, 1.33, 2]));
    memoSig = memoSig * LFPulse.kr(memo.linexp(0, 1, 0.1, 0.5), 0, 0.3).lag(0.1);
    memoSig = memoSig * memo * 0.3;

    // Mix
    sig = pipes + wheezeSig + memoSig;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_music loaded".postln;
