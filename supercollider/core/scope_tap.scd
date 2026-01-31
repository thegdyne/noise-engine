/*
 * Noise Engine Scope Tap Infrastructure
 * Version: 0.8.15
 *
 * Hardware-grade oscilloscope for monitoring generator slot outputs.
 * Taps the intermediate bus (pre-end-stage) for raw generator waveforms.
 *
 * Architecture (RecordBuf + Frozen-Gate):
 *   - Single buffer, RecordBuf writes once per trigger (loop:0), then stops
 *   - Sweep timer tracks elapsed time since trigger
 *   - SendReply reports "writing" vs "frozen" state at 60Hz
 *   - sclang only reads buffer when frozen (guaranteed tear-free)
 *   - 2x holdoff ensures generous frozen window for reliable reads
 */

~setupScopeTap = {
    "Setting up scope tap...".postln;

    SynthDef(\forge_core_scope_tap, { |inBus, buf, threshold=0.0|
        var sig, mono, trig, elapsed, writing;

        // 1. Canonical Tap (Intermediate Bus -> Mono Sum)
        sig = In.ar(inBus, 2);
        mono = Mix.ar(sig) * 0.5;

        // 2. Rising-Edge Trigger with Holdoff
        // Holdoff = 2x buffer duration: write phase + frozen phase.
        // During frozen phase, RecordBuf has stopped and buffer is safe to read.
        trig = Trig1.ar(
            (mono >= threshold) & (Delay1.ar(mono) < threshold),
            BufDur.kr(buf) * 2
        );

        // 3. RecordBuf writes once per trigger, stops at buffer end (loop:0)
        // On trigger: resets to position 0 and starts recording
        // After BufFrames samples: stops writing, buffer is frozen
        RecordBuf.ar(mono, buf,
            offset: 0,
            recLevel: 1,
            preLevel: 0,
            run: 1,
            loop: 0,
            trigger: trig
        );

        // 4. Track buffer state via elapsed time since trigger
        // Sweep resets to 0 on trigger, counts up in seconds
        elapsed = Sweep.ar(trig);
        writing = (elapsed < BufDur.kr(buf));  // 1 = writing, 0 = frozen

        // 5. Report state: writing flag (0=frozen/safe, 1=writing)
        SendReply.kr(Impulse.kr(60), '/scope/state', [
            A2K.kr(writing)
        ]);
    }).add;

    "  [x] Scope tap SynthDef ready (forge_core_scope_tap, frozen-gate)".postln;
};

// === BOOT SCOPE TAP ===
// Called after end-stage infrastructure is booted (needs ~intermediateBus, groups)

~bootScopeTap = {
    "Booting scope tap...".postln;

    // Allocate scope buffer (1024 samples, mono)
    ~scopeBuf = Buffer.alloc(s, 1024, 1);

    // Create scope tap synth - runs after all generators
    ~scopeTapSynth = Synth(\forge_core_scope_tap, [
        \inBus, ~intermediateBus[0].index,  // Default to slot 1
        \buf, ~scopeBuf.bufnum,
        \threshold, 0.0
    ], ~masterGroup, \addToTail);

    // Streaming state
    ~scopeStreamActive = false;
    ~scopeFrozen = false;
    ~scopeTappedSlot = 0;  // 0-indexed
    ~scopeWriting = 1;     // Start as "writing" until first sweep completes

    "  [x] Scope tap booted (buf=%, synth=%)".format(
        ~scopeBuf.bufnum, ~scopeTapSynth.nodeID
    ).postln;
};

// === SCOPE TAP OSC HANDLERS ===

~setupScopeTapOSC = {
    "Setting up scope tap OSC...".postln;

    // Receive buffer state from SynthDef (0=frozen, 1=writing)
    OSCdef(\scopeState, { |msg|
        ~scopeWriting = msg[3].asInteger;
    }, '/scope/state');

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

    // === DEBUG CAPTURE ===
    // Captures raw intermediate bus audio + scope buffer simultaneously to CSV
    OSCdef(\scopeDebug, { |msg|
        var slot = ~scopeTappedSlot ? 0;
        var inBus = ~intermediateBus[slot];
        var rawBuf = Buffer.alloc(s, 2048, 1);

        "[Scope Debug] Capturing slot % ...".format(slot + 1).postln;

        SynthDef(\scope_debug_capture, { |bus, buf|
            var sig = Mix.ar(In.ar(bus, 2)) * 0.5;
            RecordBuf.ar(sig, buf, loop: 0, doneAction: 2);
        }).add;

        s.sync;

        Synth(\scope_debug_capture, [
            \bus, inBus.index,
            \buf, rawBuf.bufnum
        ], ~masterGroup, \addToTail);

        0.1.wait;

        rawBuf.loadToFloatArray(action: { |rawData|
            ~scopeBuf.loadToFloatArray(action: { |scopeData|
                var path = Platform.userHomeDir +/+ "Downloads" +/+ "scope_debug.csv";
                var file = File(path, "w");

                file.write("sample,raw_audio,scope_buffer\n");

                2048.do { |i|
                    var raw = rawData[i];
                    var scope = if(i < 1024, { scopeData[i] }, { "" });
                    file.write("%,%,%\n".format(i, raw, scope));
                };

                file.close;
                rawBuf.free;

                "[Scope Debug] Saved to %".format(path).postln;

                if(~pythonAddr.notNil, {
                    ~pythonAddr.sendMsg('/noise/scope/debug/done', path);
                });
            });
        });
    }, '/noise/scope/debug');

    // === DATA STREAMING ROUTINE ===
    // Polls at 60Hz. Only reads buffer when state is "frozen" (writing=0).
    // RecordBuf with loop:0 stops after filling the buffer, so during the
    // frozen phase the buffer is guaranteed complete and unchanging.
    ~scopeStreamRoutine = Routine({
        loop {
            if(~scopeStreamActive == true, {
                if(~scopeFrozen != true, {
                    if(~scopeWriting == 0, {
                        // Buffer is frozen — safe to read
                        ~scopeBuf.loadToFloatArray(action: { |data|
                            if(~pythonAddr.notNil && ~scopeStreamActive, {
                                ~pythonAddr.sendMsg(
                                    '/noise/scope/data',
                                    *data.as(Array)
                                );
                            });
                        });
                    });
                });
            });
            (1/60).wait;  // 60Hz polling for responsive frozen-state detection
        };
    }).play(AppClock);

    "  [x] Scope tap OSC handlers ready".postln;
};

"scope_tap.scd loaded".postln;
