// robotjox/reactor — Lightweight end-stage generator
SynthDef(\forge_robotjox_reactor, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var outputLvl, spin, surge, coolant, redline;
    var saws, detuneAmt, surgeMod, coolantNoise, sub;

    outputLvl = p[0];
    spin = p[1];
    surge = p[2];
    coolant = p[3];
    redline = p[4];

    freq = In.kr(freqBus);

    // Surge modulation
    surgeMod = LFNoise2.kr(0.5 + (surge * 2)).range(0.9, 1.1);
    surgeMod = surgeMod * SinOsc.kr(surge.linexp(0, 1, 0.1, 1)).range(0.95, 1.05);

    // Detune amount based on spin
    detuneAmt = spin * 0.02;

    // Supersaw stack - 7 detuned saws
    saws = Saw.ar(freq * surgeMod, 0.15);
    saws = saws + Saw.ar(freq * (1 + detuneAmt) * surgeMod, 0.12 * outputLvl);
    saws = saws + Saw.ar(freq * (1 - detuneAmt) * surgeMod, 0.12 * outputLvl);
    saws = saws + Saw.ar(freq * (1 + (detuneAmt * 2)) * surgeMod, 0.1 * outputLvl);
    saws = saws + Saw.ar(freq * (1 - (detuneAmt * 2)) * surgeMod, 0.1 * outputLvl);
    saws = saws + Saw.ar(freq * (1 + (detuneAmt * 3)) * surgeMod, 0.08 * outputLvl);
    saws = saws + Saw.ar(freq * (1 - (detuneAmt * 3)) * surgeMod, 0.08 * outputLvl);

    // Sub bass foundation
    sub = SinOsc.ar(freq * 0.5, 0, 0.25);
    sub = sub + Pulse.ar(freq * 0.25, 0.5, 0.15);

    sig = saws + sub;

    // Redline distortion
    sig = sig * (1 + (redline * 2));
    sig = sig.tanh;
    sig = sig * (1 / (1 + redline));

    // Coolant flow noise
    coolantNoise = BPF.ar(PinkNoise.ar(0.3), freq * 3, 0.4) * 2;
    coolantNoise = coolantNoise + LPF.ar(BrownNoise.ar(0.2), 300);
    coolantNoise = coolantNoise * LFNoise2.kr(1 + (coolant * 3)).range(0.5, 1.0);
    sig = sig + (coolantNoise * coolant);

    // Continuous bed
    sig = sig + BrownNoise.ar(0.05);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_reactor loaded".postln;
