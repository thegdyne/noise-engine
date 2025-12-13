/*
Master Passthrough Effect
Final output with fidelity control, master volume, and metering

Signal flow: masterBus -> fidelity -> volume -> output
                                        |
                                    metering -> OSC
*/

~setupMasterPassthrough = {
    SynthDef(\masterPassthrough, { |inBus, outBus=0, fidelityAmount=1.0, masterVol=0.8, meterRate=24|
        var sig, ampL, ampR, peakL, peakR;
        sig = In.ar(inBus, 2);
        
        // Fidelity processing (bit crushing, sample rate, bandwidth)
        sig = sig.round(2.pow(fidelityAmount.linexp(0, 1, 4, 16)).reciprocal * 2) - 1;
        sig = Latch.ar(sig, Impulse.ar(fidelityAmount.linexp(0, 1, 4000, 44100)));
        sig = LPF.ar(sig, fidelityAmount.linexp(0, 1, 2000, 18000));
        
        // Master volume (after effects, before output)
        sig = sig * masterVol;
        
        // Metering (post-fader, pre-output)
        ampL = Amplitude.kr(sig[0], attackTime: 0.01, releaseTime: 0.1);
        ampR = Amplitude.kr(sig[1], attackTime: 0.01, releaseTime: 0.1);
        peakL = Amplitude.kr(sig[0], attackTime: 0.001, releaseTime: 0.3);
        peakR = Amplitude.kr(sig[1], attackTime: 0.001, releaseTime: 0.3);
        
        // Send levels to Python
        SendReply.kr(
            Impulse.kr(meterRate),
            '/noise/master/levels',
            [ampL, ampR, peakL, peakR]
        );
        
        Out.ar(outBus, sig);
    }).add;
    
    "  ✓ Master passthrough SynthDef ready (with metering)".postln;
};

~startMasterPassthrough = {
    // Add to fxGroup (runs AFTER generators)
    ~masterEffects = Synth(\masterPassthrough, [
        \inBus, ~masterBus,
        \outBus, 0,
        \fidelityAmount, 1.0,
        \masterVol, ~masterVolume ? 0.8,
        \meterRate, 24
    ], ~fxGroup);
    
    "  ✓ Master passthrough running".postln;
};
