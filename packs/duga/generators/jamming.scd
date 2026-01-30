// duga/jamming — Lightweight end-stage generator
SynthDef(\forge_duga_jamming, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var bits, srate, dens, tone, chop;
    var noiseSig, toneSig, bitDepth, sampleRate, chopSig;

    freq = In.kr(freqBus);

    bits = p[0];
    srate = p[1];
    dens = p[2];
    tone = p[3];
    chop = p[4];

    // Noise component - broadband interference
    noiseSig = WhiteNoise.ar(1) * (0.3 + (dens * 0.7));
    noiseSig = BPF.ar(noiseSig, freq * LFNoise0.kr(5).range(0.5, 2), 0.5);

    // Tonal component - jamming carriers
    toneSig = Pulse.ar(freq * LFNoise0.kr(2).range(0.9, 1.1), 0.5);
    toneSig = toneSig + Pulse.ar(freq * 1.5, 0.3) * 0.5;
    toneSig = toneSig * 0.4;

    // Mix tone and noise
    sig = (noiseSig * (1 - tone)) + (toneSig * tone);

    // Bitcrushing
    bitDepth = bits.linexp(0, 1, 16, 3);
    sampleRate = srate.linexp(0, 1, 44100, 2000);
    sig = Latch.ar(sig, Impulse.ar(sampleRate));
    sig = (sig * (2 ** bitDepth)).round / (2 ** bitDepth);

    // Signal chopping - less aggressive, always some signal
    chopSig = LFPulse.kr(chop.linexp(0, 1, 1, 20), 0, LFNoise0.kr(1).range(0.3, 0.7));
    sig = sig * (0.4 + (chopSig.lag(0.01) * 0.6));

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_jamming loaded".postln;
