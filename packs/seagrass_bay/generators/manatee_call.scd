// seagrass_bay/manatee_call — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_manatee_call, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var chirp, squeak, warm, bend, echo;
    var modFreq, modIndex, carrier, bendMod, chirpMod, echoSig;

    // Standard bus reads
    freq = In.kr(freqBus);

    chirp = p[0];  // Vocalization rate
    squeak = p[1];  // High harmonics
    warm = p[2];  // Body/fullness
    bend = p[3];  // Pitch inflection
    echo = p[4];  // Underwater resonance

    // Pitch bend - characteristic manatee pitch warble
    bendMod = SinOsc.kr(chirp.linexp(0, 1, 2, 8)) * bend * 0.08;
    freq = freq * (1 + bendMod);

    // Chirp modulation - vibrato-like
    chirpMod = SinOsc.kr(chirp.linexp(0, 1, 4, 15)) * chirp * 0.02;
    freq = freq * (1 + chirpMod);

    // FM synthesis for squeaky character
    modFreq = freq * squeak.linlin(0, 1, 1.5, 4);
    modIndex = squeak.linlin(0, 1, 0.5, 3);

    carrier = SinOsc.ar(freq + (SinOsc.ar(modFreq) * modFreq * modIndex));

    // Warmth - add fundamental and sub
    sig = carrier * (1 - (warm * 0.3));
    sig = sig + (SinOsc.ar(freq) * warm * 0.5);
    sig = sig + (SinOsc.ar(freq * 0.5) * warm * 0.2);

    // Echo - comb filter for underwater quality
    echoSig = CombL.ar(sig, 0.2, echo.linlin(0, 1, 0.02, 0.1), echo * 2);
    sig = sig + (echoSig * echo * 0.4);

    // Gentle stereo
    sig = ~stereoSpread.(sig, 0.3, 0.25);

    // Standard output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_manatee_call loaded".postln;
