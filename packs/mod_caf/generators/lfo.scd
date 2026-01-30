// mod_caf/lfo — Lightweight end-stage generator
// lfo: Slow modulation textures - wavering pulse
SynthDef(\forge_mod_caf_lfo, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rate, waveform, depth, cross, bleed;
    var lfo1, lfo2;

    rate = p[0].linexp(0, 1, 0.05, 5);  // P1: LFO rate
    waveform = p[1].linlin(0, 1, 0, 1);  // P2: Waveform blend
    depth = p[2].linlin(0, 1, 0.2, 1);  // P3: Modulation depth
    cross = p[3].linlin(0, 1, 1, 1.5);  // P4: Cross modulation
    bleed = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Audio bleed

    freq = In.kr(freqBus);

    // DSP: Two LFOs for modulation
    lfo1 = SinOsc.kr(rate);
    lfo2 = LFTri.kr(rate * cross);

    // Blend waveforms
    lfo1 = (lfo1 * (1 - waveform)) + (LFPulse.kr(rate, 0, 0.5) * 2 - 1 * waveform);

    // Audio-rate manifestation of LFO
    sig = SinOsc.ar(freq * (1 + (lfo1 * depth * 0.5))) * 0.3;
    sig = sig + (Pulse.ar(freq * (1 + (lfo2 * depth * 0.3)), 0.3 + (lfo1 * 0.2)) * 0.2);

    // LFO bleed into audio - clicking/thumping
    sig = sig + (SinOsc.ar(rate * 20) * bleed * lfo1.abs * 0.2);

    // Continuous sub
    sig = sig + (SinOsc.ar(freq * 0.5) * 0.15);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mod_caf_lfo loaded".postln;
