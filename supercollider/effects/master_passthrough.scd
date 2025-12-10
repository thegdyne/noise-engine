/*
Master Passthrough Effect
Final output with fidelity control
*/

~setupMasterPassthrough = {
    SynthDef(\masterPassthrough, { |inBus, outBus=0, fidelityAmount=1.0|
        var sig;
        sig = In.ar(inBus, 2);
        sig = sig.round(2.pow(fidelityAmount.linexp(0, 1, 4, 16)).reciprocal * 2) - 1;
        sig = Latch.ar(sig, Impulse.ar(fidelityAmount.linexp(0, 1, 4000, 44100)));
        sig = LPF.ar(sig, fidelityAmount.linexp(0, 1, 2000, 18000));
        Out.ar(outBus, sig);
    }).add;
    
    "  ✓ Master passthrough SynthDef ready".postln;
};

~startMasterPassthrough = {
    // Add to fxGroup (runs AFTER generators)
    ~masterEffects = Synth(\masterPassthrough, [
        \inBus, ~masterBus,
        \outBus, 0,
        \fidelityAmount, 1.0
    ], ~fxGroup);
    
    "  ✓ Master passthrough running".postln;
};
