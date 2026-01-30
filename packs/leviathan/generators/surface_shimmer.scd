// leviathan/surface_shimmer — Lightweight end-stage generator
// ============================================================================
// LEVIATHAN: Surface Shimmer
// Role: Foreground - light dancing on the surface, hope and air
//
// SUN (Sun)      - Sunlight intensity, high harmonic brightness
// RIP (Ripple)   - Surface wave movement, modulation rate
// AIR (Air)      - Above-water clarity, presence
// RAY (Ray)      - Light ray penetration, filtered beams
// SPA (Sparkle)  - Dancing light points, granular brightness
// ============================================================================

SynthDef(\forge_leviathan_surface_shimmer, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var sun, ripple, air, ray, sparkle;
    var shimmerOsc, rippleMod, airPresence;
    var rayBeams, sparkleGrains;
    var stereoMod;

    // Read standard params
    freq = In.kr(freqBus);

    // === THEMED PARAMS ===
    sun = p[0].linlin(0, 1, 0.0, 1.0);
    ripple = p[1].linexp(0, 1, 0.5, 8.0);
    air = p[2].linlin(0, 1, 0.0, 1.0);
    ray = p[3].linlin(0, 1, 0.0, 1.0);
    sparkle = p[4].linexp(0, 1, 1, 50);

    // === RIPPLE MODULATION ===
    rippleMod = SinOsc.kr(ripple).range(0.95, 1.05);
    rippleMod = rippleMod * SinOsc.kr(ripple * 1.3).range(0.98, 1.02);

    // === SHIMMER OSCILLATORS (bright, clean) ===
    shimmerOsc = SinOsc.ar(freq * 2 * rippleMod) * 0.4;
    shimmerOsc = shimmerOsc + (SinOsc.ar(freq * 3 * rippleMod) * 0.3);
    shimmerOsc = shimmerOsc + (SinOsc.ar(freq * 4 * rippleMod) * sun * 0.3);
    shimmerOsc = shimmerOsc + (SinOsc.ar(freq * 5 * rippleMod) * sun * 0.2);
    shimmerOsc = shimmerOsc + (SinOsc.ar(freq * 6 * rippleMod) * sun * 0.15);

    // Fundamental for body
    shimmerOsc = shimmerOsc + (SinOsc.ar(freq * rippleMod) * 0.3);

    // === AIR PRESENCE (high frequency content) ===
    airPresence = WhiteNoise.ar * air * 0.1;
    airPresence = HPF.ar(airPresence, 5000);
    airPresence = airPresence + (SinOsc.ar(freq * 8) * air * 0.1);

    // === RAY BEAMS (filtered sweeping light) ===
    rayBeams = Saw.ar(freq * 2 * rippleMod) * ray * 0.2;
    rayBeams = rayBeams + (Pulse.ar(freq * 3 * rippleMod, 0.3) * ray * 0.15);
    // Sweeping filter like light through water
    rayBeams = RLPF.ar(rayBeams,
        SinOsc.kr(ripple * 0.5).range(freq * 2, freq * 8),
        0.3);
    rayBeams = rayBeams * SinOsc.kr(ripple * 0.7).range(0.3, 1);

    // === SPARKLE GRAINS ===
    sparkleGrains = Dust.ar(sparkle) * 0.4;
    sparkleGrains = Ringz.ar(sparkleGrains, freq * 4 * LFNoise0.kr(10).range(0.8, 1.5), 0.05);
    sparkleGrains = sparkleGrains + Ringz.ar(Dust.ar(sparkle * 0.7), freq * 6 * LFNoise0.kr(8).range(0.9, 1.2), 0.04) * 0.6;
    sparkleGrains = sparkleGrains + Ringz.ar(Dust.ar(sparkle * 0.5), freq * 8, 0.03) * 0.4;
    sparkleGrains = HPF.ar(sparkleGrains, 2000);

    // === MIX ===
    sig = shimmerOsc + airPresence + rayBeams + sparkleGrains;

    // Gentle high shelf boost for brightness
    sig = sig + (HPF.ar(sig, 3000) * sun * 0.3);

    // Stereo movement like light on waves
    stereoMod = SinOsc.kr(ripple * 0.3).range(-0.4, 0.4);
    sig = Balance2.ar(sig, sig, stereoMod);

    // Soft clip
    sig = (sig * 1.5).tanh * 0.6;

    // === OUTPUT CHAIN ===

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_leviathan_surface_shimmer loaded".postln;
