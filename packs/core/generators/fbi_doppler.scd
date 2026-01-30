// core/fbi_doppler — Lightweight end-stage generator
/*
FBI Doppler Generator
Passing emergency vehicle with doppler effect

Signal flow: Siren -> Doppler shift -> Stereo pan -> Filter -> ENV VCA -> Output

Custom params:
  - P1 pass_speed: 0-1 (how fast vehicle passes)
  - P2 distance: 0-1 (closest approach distance)
  - P3 tone_split: 0-1 (siren interval)
  - P4 switch_rate: 0-1 (siren alternation)
  - P5 echo: 0-1 (environmental reflection)
*/

SynthDef(\fbiDoppler, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var passSpeed, distance, toneSplit, switchRate, echo;
    var position, doppler, freqLo, freqHi, currentFreq, switcher, distanceAmp;

    freq = In.kr(freqBus);

    passSpeed = p[0];
    distance = p[1];
    toneSplit = p[2];
    switchRate = p[3];
    echo = p[4];

    // === SOUND SOURCE ===
    position = LFSaw.kr(passSpeed.linexp(0, 1, 0.05, 1)).range(-1, 1);
    doppler = position.linlin(-1, 1, 1.1, 0.9);
    distanceAmp = (1 - position.abs) * distance.linlin(0, 1, 0.5, 1);

    freqLo = freq * doppler;
    freqHi = freq * toneSplit.linexp(0, 1, 1.1, 2.0) * doppler;

    switcher = LFPulse.kr(switchRate.linexp(0, 1, 0.5, 8));
    currentFreq = SelectX.kr(switcher, [freqLo, freqHi]);

    sig = SinOsc.ar(currentFreq) * distanceAmp * 0.5;
    sig = sig + (CombC.ar(sig, 0.3, echo.linlin(0, 1, 0.05, 0.2), echo * 2) * echo * 0.3);


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] fbiDoppler loaded".postln;
