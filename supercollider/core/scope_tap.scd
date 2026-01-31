/*
 * Noise Engine Scope Tap Infrastructure
 * Version: 0.8.13
 *
 * Hardware-grade oscilloscope for monitoring generator slot outputs.
 * Taps the intermediate bus (pre-end-stage) for raw generator waveforms.
 *
 * Architecture:
 *   - SynthDef writes triggered mono signal into a buffer
 *   - SendReply reports write position at control rate
 *   - sclang Routine reads buffer at 30fps and streams to Python
 *   - Python displays only the valid region (trigger point to write head)
 */

~setupScopeTap = {
    "Setting up scope tap...".postln;

    SynthDef(\forge_core_scope_tap, { |inBus, buf, threshold=0.0|
        var sig, mono, trig, phase;

        // 1. Canonical Tap (Intermediate Bus -> Mono Sum)
        sig = In.ar(inBus, 2);
        mono = Mix.ar(sig) * 0.5;

        // 2. Rising-Edge Trigger (Audio-Rate, Zero-Jitter)
        // Fires single-sample impulse when signal crosses threshold going positive
        trig = Trig1.ar(
            (mono >= threshold) & (Delay1.ar(mono) < threshold),
            SampleDur.ir
        );

        // 3. Phase-Locked Write Position
        // Resets to 0 on every trigger, ensuring frame starts at threshold crossing
        phase = Phasor.ar(trig, 1, 0, BufFrames.kr(buf));

        // 4. Write to buffer
        BufWr.ar(mono, buf, phase);

        // 5. Report write position at control rate (for Python to know valid region)
        SendReply.kr(Impulse.kr(60), '/scope/writepos', [A2K.kr(phase)]);
    }).add;

    "  [x] Scope tap SynthDef ready (forge_core_scope_tap)".postln;
};

// === BOOT SCOPE TAP ===
// Called after end-stage infrastructure is booted (needs ~intermediateBus, groups)

~bootScopeTap = {
    "Booting scope tap...".postln;

    // Allocate scope buffer (1024 samples, mono)
    ~scopeBuf = Buffer.alloc(s, 1024, 1);

    // Create scope tap synth - runs after all generators
    // Place in ~masterGroup at tail so it runs after everything
    ~scopeTapSynth = Synth(\forge_core_scope_tap, [
        \inBus, ~intermediateBus[0].index,  // Default to slot 1
        \buf, ~scopeBuf.bufnum,
        \threshold, 0.0
    ], ~masterGroup, \addToTail);

    // Streaming state
    ~scopeStreamActive = false;
    ~scopeFrozen = false;
    ~scopeTappedSlot = 0;  // 0-indexed
    ~scopeWritePos = 0;    // Last known write position

    "  [x] Scope tap booted (buf=%, synth=%)".format(
        ~scopeBuf.bufnum, ~scopeTapSynth.nodeID
    ).postln;
};

// === SCOPE TAP OSC HANDLERS ===

~setupScopeTapOSC = {
    "Setting up scope tap OSC...".postln;

    // Capture write position from SynthDef
    OSCdef(\scopeWritePos, { |msg|
        ~scopeWritePos = msg[3].asInteger.clip(0, 1023);
    }, '/scope/writepos');

    // Set which slot to tap (0-7)
    OSCdef(\scopeSlot, { |msg|
        var slot = msg[1].asInteger.clip(0, 7);
        if(~intermediateBus.notNil && ~scopeTapSynth.notNil, {
            ~scopeTappedSlot = slot;
            ~scopeTapSynth.set(\inBus, ~intermediateBus[slot].index);
        });
    }, '/noise/scope/slot');

    // Set trigger threshold
    OSCdef(\scopeThreshold, { |msg|
        var thresh = msg[1].asFloat.clip(-1.0, 1.0);
        if(~scopeTapSynth.notNil, {
            ~scopeTapSynth.set(\threshold, thresh);
        });
    }, '/noise/scope/threshold');

    // Freeze/unfreeze
    OSCdef(\scopeFreeze, { |msg|
        var frozen = msg[1].asInteger;
        ~scopeFrozen = (frozen == 1);
    }, '/noise/scope/freeze');

    // Enable/disable streaming
    OSCdef(\scopeEnable, { |msg|
        var enabled = msg[1].asInteger;
        if(enabled == 1, {
            ~scopeStreamActive = true;
            "[Scope] Streaming enabled".postln;
        }, {
            ~scopeStreamActive = false;
            "[Scope] Streaming disabled".postln;
        });
    }, '/noise/scope/enable');

    // === DATA STREAMING ROUTINE ===
    // Reads buffer at ~30fps and sends to Python with write position
    ~scopeStreamRoutine = Routine({
        loop {
            if(~scopeStreamActive == true, {
                if(~scopeFrozen != true, {
                    var wp = ~scopeWritePos ? 0;
                    ~scopeBuf.loadToFloatArray(action: { |data|
                        if(~pythonAddr.notNil && ~scopeStreamActive, {
                            // First value is the write position, rest is buffer data
                            ~pythonAddr.sendMsg(
                                '/noise/scope/data',
                                wp,
                                *data.as(Array)
                            );
                        });
                    });
                });
            });
            (1/30).wait;  // ~30fps
        };
    }).play(AppClock);

    "  [x] Scope tap OSC handlers ready".postln;
};

"scope_tap.scd loaded".postln;
