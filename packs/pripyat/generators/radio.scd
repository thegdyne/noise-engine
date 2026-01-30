// pripyat/radio — Lightweight end-stage generator
SynthDef(\forge_pripyat_radio, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tune, stat, bits, fade, voic;
    var carrier, staticSig, voiceSig, bitDepth, sampleRate, fadeMod, tuneDrift;

    freq = In.kr(freqBus);

    tune = p[0];
    stat = p[1];
    bits = p[2];
    fade = p[3];
    voic = p[4];

    // Tuning drift
    tuneDrift = LFNoise2.kr(tune.linexp(0, 1, 0.1, 2)).range(
        1 - (tune * 0.1),
        1 + (tune * 0.1)
    );

    // Fading signal strength
    fadeMod = LFNoise2.kr(fade.linexp(0, 1, 0.1, 1)).range(
        1 - (fade * 0.8),
        1
    );

    // Carrier tone - broken broadcast
    carrier = Pulse.ar(freq * tuneDrift, LFNoise2.kr(0.5).range(0.3, 0.7), 0.2);
    carrier = carrier + SinOsc.ar(freq * tuneDrift * 2, 0, 0.1);

    // Voice remnant - formant-like filtered noise
    voiceSig = BPF.ar(PinkNoise.ar(1), freq * LFNoise0.kr(3).range(1, 4), 0.2);
    voiceSig = voiceSig * LFPulse.kr(LFNoise0.kr(0.5).range(2, 8), 0, 0.6);
    voiceSig = voiceSig * voic * 0.4;

    // Mix carrier and voice
    sig = (carrier * (1 - (voic * 0.5))) + voiceSig;

    // Static interference
    staticSig = WhiteNoise.ar(1) * LFNoise2.kr(5).range(0, 1);
    staticSig = staticSig + (Dust.ar(100) * 0.3);
    staticSig = HPF.ar(staticSig, 500);
    sig = sig + (staticSig * stat * 0.3);

    // Bit crushing
    bitDepth = bits.linexp(0, 1, 16, 3);
    sampleRate = bits.linexp(0, 1, 44100, 4000);
    sig = Latch.ar(sig, Impulse.ar(sampleRate));
    sig = (sig * (2 ** bitDepth)).round / (2 ** bitDepth);

    // Apply fading
    sig = sig * fadeMod;

    // Bandpass for radio character
    sig = BPF.ar(sig, 1500, 1) * 2;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_radio loaded".postln;
