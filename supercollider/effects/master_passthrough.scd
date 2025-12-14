/*
Master Passthrough Effect
Final output with master volume, limiter, and PRE/POST metering

Signal flow: masterBus -> PRE meter -> Limiter -> Master Vol -> POST meter -> output
                            |                                        |
                        (meterMode=0)                           (meterMode=1)
                                            ↓
                                    OSC to Python

Future: Full insert chain (Limiter → Comp → EQ) - see docs/MASTER_OUT.md
*/

~setupMasterPassthrough = {
    SynthDef(\masterPassthrough, { |inBus, outBus=0, masterVol=0.8, meterRate=24, meterMode=0,
                                    limiterCeiling=0.99, limiterBypass=0|
        var sig, sigPost;
        var preAmpL, preAmpR, prePeakL, prePeakR;
        var postAmpL, postAmpR, postPeakL, postPeakR;
        var ampL, ampR, peakL, peakR;
        var sigLimited;
        
        sig = In.ar(inBus, 2);
        
        // PRE-fader metering (shows sum from channel strips, independent of master volume)
        preAmpL = Amplitude.kr(sig[0], attackTime: 0.01, releaseTime: 0.1);
        preAmpR = Amplitude.kr(sig[1], attackTime: 0.01, releaseTime: 0.1);
        prePeakL = Amplitude.kr(sig[0], attackTime: 0.001, releaseTime: 0.3);
        prePeakR = Amplitude.kr(sig[1], attackTime: 0.001, releaseTime: 0.3);
        
        // Limiter (brickwall, pre-fader)
        sigLimited = Limiter.ar(sig, limiterCeiling, 0.01);
        sig = Select.ar(limiterBypass, [sigLimited, sig]);
        
        // Master volume
        sigPost = sig * masterVol;
        
        // POST-fader metering (shows actual output level)
        postAmpL = Amplitude.kr(sigPost[0], attackTime: 0.01, releaseTime: 0.1);
        postAmpR = Amplitude.kr(sigPost[1], attackTime: 0.01, releaseTime: 0.1);
        postPeakL = Amplitude.kr(sigPost[0], attackTime: 0.001, releaseTime: 0.3);
        postPeakR = Amplitude.kr(sigPost[1], attackTime: 0.001, releaseTime: 0.3);
        
        // Select PRE or POST based on meterMode (0=PRE, 1=POST)
        ampL = Select.kr(meterMode, [preAmpL, postAmpL]);
        ampR = Select.kr(meterMode, [preAmpR, postAmpR]);
        peakL = Select.kr(meterMode, [prePeakL, postPeakL]);
        peakR = Select.kr(meterMode, [prePeakR, postPeakR]);
        
        // Send selected levels to Python via SendReply
        SendReply.kr(
            Impulse.kr(meterRate),
            '/masterLevelsInternal',
            [ampL, ampR, peakL, peakR]
        );
        
        Out.ar(outBus, sigPost);
    }).add;
    
    "  ✓ Master passthrough SynthDef ready (PRE/POST metering, limiter)".postln;
};

~startMasterPassthrough = {
    // ~pythonAddr is set in config.scd
    
    // Track meter mode (0=PRE, 1=POST)
    ~masterMeterMode = 0;
    
    // Limiter defaults
    ~limiterCeiling = 0.99;  // -0.1dB
    ~limiterBypass = 0;      // On by default
    
    // Forward internal meter replies to Python
    OSCdef(\meterForward, { |msg|
        // msg format: ['/masterLevelsInternal', node_id, reply_id, ampL, ampR, peakL, peakR]
        ~pythonAddr.sendMsg('/noise/master/levels', msg[3], msg[4], msg[5], msg[6]);
    }, '/masterLevelsInternal');
    
    // Handle meter mode toggle from Python
    OSCdef(\masterMeterToggle, { |msg|
        var mode = msg[1].asInteger.clip(0, 1);
        ~masterMeterMode = mode;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\meterMode, mode);
        };
        ("  Meter mode: " ++ if(mode == 0, "PRE", "POST")).postln;
    }, '/noise/master/meter/toggle');
    
    // Handle limiter ceiling from Python (receives dB, converts to linear)
    OSCdef(\limiterCeiling, { |msg|
        var db = msg[1].clip(-6, 0);
        var linear = db.dbamp;  // Convert dB to linear
        ~limiterCeiling = linear;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\limiterCeiling, linear);
        };
        ("  Limiter ceiling: " ++ db ++ "dB (" ++ linear.round(0.001) ++ ")").postln;
    }, '/noise/master/limiter/ceiling');
    
    // Handle limiter bypass from Python
    OSCdef(\limiterBypass, { |msg|
        var bypass = msg[1].asInteger.clip(0, 1);
        ~limiterBypass = bypass;
        if (~masterEffects.notNil) {
            ~masterEffects.set(\limiterBypass, bypass);
        };
        ("  Limiter: " ++ if(bypass == 0, "ON", "BYPASSED")).postln;
    }, '/noise/master/limiter/bypass');
    
    // Add to fxGroup (runs AFTER generators)
    ~masterEffects = Synth(\masterPassthrough, [
        \inBus, ~masterBus,
        \outBus, 0,
        \masterVol, ~masterVolume ? 0.8,
        \meterRate, 24,
        \meterMode, ~masterMeterMode,
        \limiterCeiling, ~limiterCeiling,
        \limiterBypass, ~limiterBypass
    ], ~fxGroup);
    
    "  ✓ Master passthrough running (limiter ON, ceiling -0.1dB)".postln;
};
