// core/fbi_siren — Lightweight end-stage generator
/*
FBI Siren Generator
Classic two-tone emergency siren

Signal flow: Dual oscillators -> Alternation -> Filter -> ENV VCA -> Output

Custom params:
  - P1 tone_split: 0-1 (interval between tones)
  - P2 switch_rate: 0-1 (alternation speed)
  - P3 waveform: 0-1 (sine <-> square)
  - P4 portamento: 0-1 (glide between tones)
  - P5 warble: 0-1 (vibrato depth)
*/

SynthDef(\fbiSiren, { |out, freqBus, customBus0|
    var sig, freq, portaTime;
    var p = In.kr(customBus0, 5);
    var toneSplit, switchRate, waveform, warble;
    var freqLo, freqHi, currentFreq, switcher, vibrato;

    freq = In.kr(freqBus);
    portaTime = In.kr(portamentoBus);
    freq = Lag.kr(freq, portaTime.linexp(0, 1, 0.001, 0.5));

    toneSplit = p[0];
    switchRate = p[1];
    waveform = p[2];
    portamento = p[3];
    warble = p[4];

    // === SOUND SOURCE ===
    freqLo = freq;
    freqHi = freq * toneSplit.linexp(0, 1, 1.1, 2.0);

    switcher = LFPulse.kr(switchRate.linexp(0, 1, 0.5, 8));
    currentFreq = SelectX.kr(switcher, [freqLo, freqHi]);
    currentFreq = currentFreq.lag(portamento.linexp(0, 1, 0.001, 0.3));

    vibrato = SinOsc.kr(5 + (switchRate * 3)) * warble * currentFreq * 0.02;
    currentFreq = currentFreq + vibrato;

    sig = SelectX.ar(waveform, [
        SinOsc.ar(currentFreq),
        Pulse.ar(currentFreq, 0.5)
    ]) * 0.5;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] fbiSiren loaded".postln;
