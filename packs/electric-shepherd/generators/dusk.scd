// electric-shepherd/dusk — Lightweight end-stage generator
/*
DUSK Generator
Twilight atmosphere - the dying of the light

Features:
  - Fading light drone
  - Cricket-like high tones
  - Cooling air movement
  - Melancholy undertone
  - Last light glimmer

Custom params:
  - P1 fade: Descending warmth drone
  - P2 cricket: High rhythmic chirps
  - P3 cool: Evening air texture
  - P4 sorrow: Sad harmonic content
  - P5 last: Bright transient glimmers

The hour between dog and wolf.
*/

SynthDef(\dusk, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var fade, cricket, cool, sorrow, last;
    var trig, twilightMod;
    var fadeSig, cricketSig, coolSig, sorrowSig, lastSig;
    var fadeOsc, fadeLFO;
    var cricketTrig, cricketOsc;
    var coolNoise, coolMod;
    var sorrowOsc, sorrowMod;
    var lastTrig, lastOsc;

    freq = In.kr(freqBus);

    // Custom params with smoothing
    fade = p[0];
    fade = Lag.kr(fade, 0.1);
    cricket = p[1];
    cool = p[2];
    cool = Lag.kr(cool, 0.1);
    sorrow = p[3];
    sorrow = Lag.kr(sorrow, 0.1);
    last = p[4];

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Overall twilight modulation - very slow fade
    twilightMod = LFTri.kr(0.02).range(0.7, 1);

    // === FADE (light drone) ===
    // Warm drone that slowly descends
    fadeLFO = LFNoise2.kr(0.1).range(0.98, 1.02);
    fadeOsc = SinOsc.ar(freq * fadeLFO);
    fadeOsc = fadeOsc + (SinOsc.ar(freq * 2 * fadeLFO) * 0.3);  // Warmth
    fadeOsc = fadeOsc + (SinOsc.ar(freq * 0.5 * fadeLFO) * 0.4);  // Foundation
    // Slow downward drift
    fadeOsc = fadeOsc * (1 - (LFSaw.kr(0.01).range(0, 0.2)));
    fadeSig = fadeOsc * fade * 0.4 * twilightMod;

    // === CRICKET (evening chirps) ===
    // High pitched rhythmic sounds
    cricketTrig = Impulse.ar(8 + (cricket * 12) + LFNoise1.kr(0.5).range(-2, 2));
    cricketOsc = SinOsc.ar(freq * 16 * TRand.ar(0.9, 1.1, cricketTrig));
    cricketOsc = cricketOsc * EnvGen.ar(Env.perc(0.001, 0.02), cricketTrig);
    // Multiple "crickets" at slightly different rates
    cricketOsc = cricketOsc + (
        SinOsc.ar(freq * 14) *
        EnvGen.ar(Env.perc(0.001, 0.015),
                  Impulse.ar(7 + (cricket * 10) + LFNoise1.kr(0.3).range(-2, 2))) * 0.6
    );
    cricketSig = HPF.ar(cricketOsc, 2000) * cricket * 0.3;

    // === COOL (evening air) ===
    // Gentle filtered noise suggesting cooling breeze
    coolNoise = PinkNoise.ar;
    coolMod = LFNoise2.kr(0.3).range(0.7, 1.3);
    coolSig = LPF.ar(coolNoise, 400 * coolMod);
    coolSig = coolSig + (BPF.ar(coolNoise, 800 * coolMod, 0.4) * 0.3);
    // Slow swell
    coolSig = coolSig * LFNoise2.kr(0.15).range(0.5, 1);
    coolSig = coolSig * cool * 0.3 * twilightMod;

    // === SORROW (melancholy) ===
    // Minor key undertone
    sorrowMod = LFNoise2.kr(0.2).range(0.99, 1.01);
    // Minor third and tritone for sadness
    sorrowOsc = SinOsc.ar(freq * 1.2 * sorrowMod) * 0.4;  // Minor third
    sorrowOsc = sorrowOsc + (SinOsc.ar(freq * 1.5 * sorrowMod) * 0.3);  // Fifth
    sorrowOsc = sorrowOsc + (SinOsc.ar(freq * 0.75 * sorrowMod) * 0.35);  // Below
    // Slow vibrato
    sorrowOsc = sorrowOsc * (1 + (SinOsc.kr(4).range(-0.02, 0.02)));
    sorrowSig = sorrowOsc * sorrow * 0.35 * twilightMod;

    // === LAST (final glimmers) ===
    // Bright transient moments
    lastTrig = trig + Dust.ar(last * 3);
    lastOsc = SinOsc.ar(freq * 4);
    lastOsc = lastOsc + (SinOsc.ar(freq * 6) * 0.5);
    lastOsc = lastOsc * EnvGen.ar(Env.perc(0.01, 0.3, 1, -4), lastTrig);
    // Add shimmer
    lastOsc = lastOsc + (
        SinOsc.ar(freq * 8 * LFNoise2.kr(5).range(0.98, 1.02)) *
        EnvGen.ar(Env.perc(0.05, 0.5), lastTrig) * 0.3
    );
    lastSig = lastOsc * last * 0.4;

    // === MIX ===
    sig = fadeSig + cricketSig + coolSig + sorrowSig + lastSig;

    // Soft limiting
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.1, 0.25);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] dusk loaded".postln;
