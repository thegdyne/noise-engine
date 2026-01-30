// leviathan/whale_song — Lightweight end-stage generator
// ============================================================================
// LEVIATHAN: Whale Song
// Role: Foreground - the creature's voice, ancient calls
//
// CAL (Call)     - Vocalization type, morphs between call patterns
// RSN (Resonance)- Body cavity size, scales formants
// ECO (Echo)     - Underwater propagation, distance
// LIF (Lift)     - Emergence, muffled deep to clear surface
// SOL (Soul)     - Emotional weight, vibrato and drift
// ============================================================================

SynthDef(\forge_leviathan_whale_song, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var call, resonance, echo, lift, soul;
    var vocalSource, formant1, formant2, formant3;
    var vibrato, pitchDrift, callMod;
    var echoSig, depthFilter;

    // Read standard params
    freq = In.kr(freqBus);

    // === THEMED PARAMS ===
    call = p[0].linlin(0, 1, 0.0, 1.0);
    resonance = p[1].linexp(0, 1, 0.5, 2.0);
    echo = p[2].linlin(0, 1, 0.0, 1.0);
    lift = p[3].linlin(0, 1, 0.0, 1.0);
    soul = p[4].linlin(0, 1, 0.0, 1.0);

    // === SOUL (vibrato and drift) ===
    vibrato = SinOsc.kr(4 + LFNoise1.kr(0.5).range(-1, 1)).range(1 - (soul * 0.03), 1 + (soul * 0.03));
    pitchDrift = LFNoise2.kr(0.2).range(1 - (soul * 0.02), 1 + (soul * 0.02));
    freq = freq * vibrato * pitchDrift;

    // === CALL MORPHING ===
    // Different call types blend based on call parameter
    // Low moan (0) -> Mid call (0.5) -> High whistle (1)
    callMod = call;

    // === VOCAL SOURCE ===
    // Pulse-like glottal source with varying width
    vocalSource = Pulse.ar(freq, 0.3 + (call * 0.2)) * 0.5;
    vocalSource = vocalSource + (SinOsc.ar(freq) * 0.3);
    // Add sub for low moans
    vocalSource = vocalSource + (SinOsc.ar(freq * 0.5) * (1 - call) * 0.4);

    // === FORMANT FILTERS (whale vocal tract) ===
    // Formants shift based on call type and resonance
    formant1 = Resonz.ar(vocalSource,
        (200 + (call * 600)) * resonance,  // 200-800 Hz base
        0.1) * 2;

    formant2 = Resonz.ar(vocalSource,
        (500 + (call * 1500)) * resonance,  // 500-2000 Hz
        0.15) * 1.5;

    formant3 = Resonz.ar(vocalSource,
        (1000 + (call * 3000)) * resonance,  // 1000-4000 Hz (whistle range)
        0.2) * call;  // Only present in higher calls

    sig = formant1 + formant2 + formant3;

    // === DEPTH FILTER (lift controls clarity) ===
    // Deep = muffled, surface = clear
    depthFilter = 300 + (lift * 8000);
    sig = LPF.ar(sig, depthFilter);
    sig = sig + (HPF.ar(sig, 500) * lift * 0.3);  // Add presence when surfaced

    // === UNDERWATER ECHO ===
    echoSig = DelayC.ar(sig, 0.5, LFNoise2.kr(0.1).range(0.1, 0.3));
    echoSig = LPF.ar(echoSig, 1000);  // Distance filtering
    echoSig = echoSig + DelayC.ar(sig, 0.8, LFNoise2.kr(0.08).range(0.3, 0.5)) * 0.5;
    sig = sig + (echoSig * echo * 0.4);

    // Gentle saturation
    sig = (sig * 1.5).tanh * 0.6;

    // === OUTPUT CHAIN ===
    sig = ~stereoSpread.(sig, 0.1, 0.25);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_leviathan_whale_song loaded".postln;
