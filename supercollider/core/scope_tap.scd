/*
 * Noise Engine Scope Tap Infrastructure
 * Version: 0.8.16
 *
 * Hardware-grade oscilloscope for monitoring generator slot outputs.
 * Taps the intermediate bus (pre-end-stage) for raw generator waveforms.
 *
 * Architecture (Server-Managed Ping-Pong with AR/KR Alignment):
 *   - Two buffers: SynthDef writes to one, sclang reads the other
 *   - Trigger quantized to control-rate so ToggleFF and Phasor reset
 *     happen on the SAME clock boundary (eliminates ~64 sample bleed)
 *   - Gated writing: Trig1.ar stops writer after exactly one buffer fill
 *   - Toggle-driven push: only streams data when toggle changes
 *   - Read-in-flight gating prevents async race conditions
 *   - LeakDC + HPF conditioning for trigger detection only (raw signal to buffer)
 */

~setupScopeTap = {
    "Setting up scope tap...".postln;

    SynthDef(\forge_core_scope_tap, { |inBus, buf0, buf1, threshold=0.0|
        var sig, mono, trigSig, edge, kEdge, kTrig, aTrig, toggle, phase, activeBuf, aWriteGate;

        // 1. Tap: raw mono for display, conditioned copy for trigger only
        sig = In.ar(inBus, 2);
        mono = Mix.ar(sig) * 0.5;                      // Raw signal → buffer
        trigSig = HPF.ar(LeakDC.ar(mono), 5);           // Conditioned → trigger detection only

        // 2. Rising-edge detect (audio-rate) with hysteresis
        edge = (trigSig >= threshold) & (Delay1.ar(trigSig) < (threshold - 0.001));

        // 3. Reliable ar->kr trigger capture (lossless)
        kEdge = T2K.kr(edge);

        // 4. Retrigger inhibit (Holdoff)
        kTrig = Trig1.kr(kEdge, BufDur.kr(buf0));

        // 5. Single-sample audio reset impulse
        aTrig = T2A.ar(kTrig);

        // 6. Double-buffer toggle (block-aligned)
        toggle = ToggleFF.kr(kTrig);

        // 7. One-shot write gate (one full sweep)
        aWriteGate = Trig1.ar(aTrig, BufDur.kr(buf0));

        // 8. Phase counter — fills buffer from index 0
        phase = Phasor.ar(aTrig, aWriteGate, 0, BufFrames.kr(buf0) - 1);

        // 9. Gated write to active buffer
        activeBuf = Select.kr(toggle, [buf0, buf1]);
        BufWr.ar(mono * aWriteGate, activeBuf, phase);

        // 10. Status feedback: toggle-driven push
        SendReply.kr(kTrig, '/scope/status', [toggle, 0]);
    }).add;

    // Debug capture SynthDef (defined once at setup, not per-capture)
    SynthDef(\scope_debug_capture, { |bus, buf|
        var sig = Mix.ar(In.ar(bus, 2)) * 0.5;
        RecordBuf.ar(sig, buf, loop: 0, doneAction: 2);
    }).add;

    "  [x] Scope tap SynthDef ready (forge_core_scope_tap, ping-pong v0.8.16)".postln;
};

// === BOOT SCOPE TAP ===
// Called after end-stage infrastructure is booted (needs ~intermediateBus, groups)

~bootScopeTap = {
    "Booting scope tap...".postln;

    // Allocate two scope buffers (1024 samples each, mono)
    ~scopeBuf0 = Buffer.alloc(s, 1024, 1);
    ~scopeBuf1 = Buffer.alloc(s, 1024, 1);

    // Create scope tap synth - runs after all generators
    ~scopeTapSynth = Synth(\forge_core_scope_tap, [
        \inBus, ~intermediateBus[0].index,  // Default to slot 1
        \buf0, ~scopeBuf0.bufnum,
        \buf1, ~scopeBuf1.bufnum,
        \threshold, 0.0
    ], ~masterGroup, \addToTail);

    // Streaming state
    ~scopeStreamActive = false;
    ~scopeFrozen = false;
    ~scopeTappedSlot = 0;       // 0-indexed
    ~scopeToggle = 0;           // Which buffer is being written (0 or 1)
    ~scopeLastReadToggle = -1;  // Track last read toggle to detect changes
    ~scopeReadInFlight = false; // Prevents overlapping async reads
    ~scopePhase = 0;            // Last known write position

    "  [x] Scope tap booted (buf0=%, buf1=%, synth=%)".format(
        ~scopeBuf0.bufnum, ~scopeBuf1.bufnum, ~scopeTapSynth.nodeID
    ).postln;
};

// === SCOPE TAP OSC HANDLERS ===

~setupScopeTapOSC = {
    "Setting up scope tap OSC...".postln;

    // Receive status from SynthDef: toggle + phase
    OSCdef(\scopeStatus, { |msg|
        var newToggle = msg[3].asInteger.clip(0, 1);
        var phase = msg[4].asInteger.clip(0, 1023);
        ~scopePhase = phase;

        // Toggle-driven push: only read when toggle changes
        // (means a new sweep just started → previous buffer is complete)
        if(newToggle != ~scopeToggle, {
            ~scopeToggle = newToggle;

            if(~scopeStreamActive == true && ~scopeFrozen != true, {
                if(~scopeReadInFlight.not, {
                    // Read the INACTIVE buffer (opposite of current toggle)
                    var readBuf = if(newToggle == 1, { ~scopeBuf0 }, { ~scopeBuf1 });
                    ~scopeReadInFlight = true;
                    ~scopeLastReadToggle = newToggle;
                    readBuf.loadToFloatArray(action: { |data|
                        ~scopeReadInFlight = false;
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
    }, '/scope/status');

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
            ~scopeLastReadToggle = -1;  // Reset so first toggle change triggers read
            "[Scope] Streaming enabled".postln;
        }, {
            ~scopeStreamActive = false;
            "[Scope] Streaming disabled".postln;
        });
    }, '/noise/scope/enable');

    // === DEBUG CAPTURE ===
    // Captures raw intermediate bus audio + inactive scope buffer to CSV
    // Wrapped in fork for Routine context (s.sync / wait require it)
    OSCdef(\scopeDebug, { |msg|
        fork {
            var slot = ~scopeTappedSlot ? 0;
            var inBus = ~intermediateBus[slot];
            var rawBuf = Buffer.alloc(s, 2048, 1);
            var readBuf = if(~scopeToggle == 1, { ~scopeBuf0 }, { ~scopeBuf1 });

            "[Scope Debug] Capturing slot % ...".format(slot + 1).postln;

            s.sync;

            Synth(\scope_debug_capture, [
                \bus, inBus.index,
                \buf, rawBuf.bufnum
            ], ~masterGroup, \addToTail);

            0.1.wait;

            rawBuf.loadToFloatArray(action: { |rawData|
                readBuf.loadToFloatArray(action: { |scopeData|
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
        };
    }, '/noise/scope/debug');

    "  [x] Scope tap OSC handlers ready".postln;
};

// === CLEANUP ===
~shutdownScopeTap = {
    "[Scope] Shutting down...".postln;
    if(~scopeTapSynth.notNil, { ~scopeTapSynth.free; ~scopeTapSynth = nil });
    if(~scopeBuf0.notNil, { ~scopeBuf0.free; ~scopeBuf0 = nil });
    if(~scopeBuf1.notNil, { ~scopeBuf1.free; ~scopeBuf1 = nil });
    OSCdef(\scopeStatus).free;
    OSCdef(\scopeSlot).free;
    OSCdef(\scopeThreshold).free;
    OSCdef(\scopeFreeze).free;
    OSCdef(\scopeEnable).free;
    OSCdef(\scopeDebug).free;
    ~scopeStreamActive = false;
    "[Scope] Shutdown complete".postln;
};

"scope_tap.scd loaded".postln;
