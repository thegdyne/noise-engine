// duga/control — Lightweight end-stage generator
SynthDef(\forge_duga_control, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var hum, flkr, pwid, dead, dustAmt;
    var humSig, flickerMod, pulseSig, deadSig, dustSig;

    freq = In.kr(freqBus);

    hum = p[0];
    flkr = p[1];
    pwid = p[2];
    dead = p[3];
    dustAmt = p[4];

    // Main pulse oscillator - dark hollow character
    pulseSig = Pulse.ar(freq, pwid.linlin(0, 1, 0.2, 0.8));
    pulseSig = pulseSig + Pulse.ar(freq * 0.5, 0.5) * 0.5;
    pulseSig = LPF.ar(pulseSig, freq * 3);

    // Electrical hum - 50Hz harmonics
    humSig = SinOsc.ar(50) + (SinOsc.ar(100) * 0.5) + (SinOsc.ar(150) * 0.25);
    humSig = humSig * hum * 0.15;

    // Fluorescent flicker modulation
    flickerMod = LFNoise2.kr(flkr.linexp(0, 1, 2, 15)).range(0.7, 1);
    flickerMod = flickerMod * LFPulse.kr(flkr.linexp(0, 1, 0.5, 8), 0, 0.9).range(0.8, 1);

    // Dead equipment - low rumble
    deadSig = LPF.ar(BrownNoise.ar(1), 100);
    deadSig = deadSig * dead * 0.2;

    // Dust particles
    dustSig = Dust.ar(dustAmt.linexp(0, 1, 0.5, 5)) * 0.1;
    dustSig = Ringz.ar(dustSig, freq * 4, 0.02);

    // Mix
    sig = (pulseSig * 0.3 * flickerMod) + humSig + deadSig + dustSig;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_control loaded".postln;
