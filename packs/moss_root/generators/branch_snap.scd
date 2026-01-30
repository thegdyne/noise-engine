// moss_root/branch_snap — Lightweight end-stage generator
SynthDef(\forge_moss_root_branch_snap, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crack, wood, echo, size, dry, localTrig;
    var noise, crackEnv, woodBody, bodyFreq, delayedSig;

    freq = In.kr(freqBus);

    localTrig = Impulse.ar(4);  // Self-trigger for percussive envelopes
    crack = p[0];
    wood = p[1];
    echo = p[2];
    size = p[3];
    dry = p[4];

    // Base frequency scaled by size (bigger branch = lower)
    bodyFreq = freq * size.linexp(0, 1, 2, 0.5);

    // Crack: bright noise burst with fast envelope
    crackEnv = EnvGen.ar(Env.perc(0.001, dry.linexp(0, 1, 0.08, 0.02)), localTrig);
    noise = HPF.ar(WhiteNoise.ar, crack.linexp(0, 1, 2000, 8000)) * crackEnv * crack;

    // Wood body resonance: multiple modes
    woodBody = Mix([
        Ringz.ar(noise * 0.5, bodyFreq, dry.linexp(0, 1, 0.3, 0.08)) * 0.4,
        Ringz.ar(noise * 0.3, bodyFreq * 1.6, dry.linexp(0, 1, 0.25, 0.05)) * 0.3,
        Ringz.ar(noise * 0.2, bodyFreq * 2.4, dry.linexp(0, 1, 0.2, 0.04)) * 0.2
    ]) * wood;

    // Pitch bend for snap character
    sig = (noise * 0.6) + woodBody;

    // Add subtle pitched click
    sig = sig + (SinOsc.ar(bodyFreq * EnvGen.ar(Env.perc(0.001, 0.02), localTrig)) * EnvGen.ar(Env.perc(0.001, 0.03), localTrig) * 0.3);

    // Forest echo: short delay with feedback
    delayedSig = CombL.ar(sig, 0.3, size.linlin(0, 1, 0.08, 0.2), echo.linlin(0, 1, 0.1, 1.5));
    sig = sig + (delayedSig * echo * 0.5);

    // Stereo spread based on echo
    sig = Pan2.ar(Mix(sig), SinOsc.kr(0.1) * echo.linlin(0, 1, 0.2, 0.6));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_branch_snap loaded".postln;
