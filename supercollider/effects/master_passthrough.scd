/*
Master Passthrough Effect
Final output with fidelity control, master volume, and metering

Signal flow: masterBus -> metering (PRE-fader) -> fidelity -> volume -> output
                            |
                        OSC to Python (shows channel strip sum)
*/

~setupMasterPassthrough = {
    SynthDef(\masterPassthrough, { |inBus, outBus=0, fidelityAmount=1.0, masterVol=0.8, meterRate=24|
        var sig, ampL, ampR, peakL, peakR;
        sig = In.ar(inBus, 2);
        
        // Metering PRE-fader (shows sum from channel strips, independent of master volume)
        ampL = Amplitude.kr(sig[0], attackTime: 0.01, releaseTime: 0.1);
        ampR = Amplitude.kr(sig[1], attackTime: 0.01, releaseTime: 0.1);
        peakL = Amplitude.kr(sig[0], attackTime: 0.001, releaseTime: 0.3);
        peakR = Amplitude.kr(sig[1], attackTime: 0.001, releaseTime: 0.3);
        
        // Send levels to Python via SendReply (will be forwarded by OSC responder)
        SendReply.kr(
            Impulse.kr(meterRate),
            '/masterLevelsInternal',
            [ampL, ampR, peakL, peakR]
        );
        
        // Fidelity processing (bit crushing, sample rate, bandwidth)
        sig = sig.round(2.pow(fidelityAmount.linexp(0, 1, 4, 16)).reciprocal * 2) - 1;
        sig = Latch.ar(sig, Impulse.ar(fidelityAmount.linexp(0, 1, 4000, 44100)));
        sig = LPF.ar(sig, fidelityAmount.linexp(0, 1, 2000, 18000));
        
        // Master volume (after metering and effects, controls output level only)
        sig = sig * masterVol;
        
        Out.ar(outBus, sig);
    }).add;
    
    "  ✓ Master passthrough SynthDef ready (PRE-fader metering)".postln;
};

~startMasterPassthrough = {
    // Python address for sending meter data
    ~pythonAddr = NetAddr("127.0.0.1", 57121);
    
    // Forward internal meter replies to Python
    OSCdef(\meterForward, { |msg|
        // msg format: ['/masterLevelsInternal', node_id, reply_id, ampL, ampR, peakL, peakR]
        ~pythonAddr.sendMsg('/noise/master/levels', msg[3], msg[4], msg[5], msg[6]);
    }, '/masterLevelsInternal');
    
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
