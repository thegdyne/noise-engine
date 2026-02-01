/*
 * Noise Engine Telemetry Tap Infrastructure
 *
 * Handles OSC commands from Python to enable/disable telemetry on generators.
 * Works with generators that have the telemetryRate argument.
 *
 * OSC Paths (SSOT — must match src/config/__init__.py):
 *   /noise/telem/enable      [slot, rate]  - Enable telemetry (0 = disable)
 *   /noise/telem/gen         [slot, ...]   - Outbound: telemetry data
 *   /noise/telem/wave/enable [slot, enable] - Enable waveform capture
 *   /noise/telem/wave        [slot, ...]   - Outbound: waveform samples
 *
 * Variable names (must match codebase):
 *   ~generators[slotID]    - Generator synth nodes (1-based, from endstage.scd)
 *   ~intermediateBus[idx]  - Pre-end-stage buses (0-based, from endstage.scd)
 *   ~pythonAddr             - NetAddr for Python (from config.scd)
 *
 * Reference: DIRECT_OSC_TELEMETRY_SPEC.md
 */

// =============================================================================
// SETUP (called from init.scd)
// =============================================================================

~setupTelemetryTap = {

    // State
    ~telemetry = ~telemetry ? ();
    ~telemetry.enabled = Array.fill(8, { false });
    ~telemetry.rates = Array.fill(8, { 0 });

    // =========================================================================
    // WAVEFORM CAPTURE SYNTHDEF
    // =========================================================================

    SynthDef(\forge_telemetry_wave_capture, { |inBus, slotIndex=0, bufnum|
        var sig, mono, freq, frameSize, captureTrig, capturePhase;

        // Read from intermediate bus (pre-end-stage, stereo)
        sig = In.ar(inBus, 2);
        mono = Mix.ar(sig) * 0.5;

        // Estimate frequency from zero-crossings (adaptive capture)
        freq = ZeroCrossing.ar(mono).max(20).min(20000);

        // Frame size: exactly one cycle at current frequency, clamped to buffer
        frameSize = (SampleRate.ir / freq).clip(64, BufFrames.kr(bufnum));

        // Zero-crossing trigger (rising edge)
        captureTrig = (mono >= 0) & (Delay1.ar(mono) < 0);

        // Phase within capture frame
        capturePhase = Phasor.ar(captureTrig, 1, 0, frameSize);

        // Write to buffer
        BufWr.ar(mono, bufnum, capturePhase);

        // Notify when frame completes (10Hz burst cap, at frame start only)
        // A2K.kr converts audio-rate capturePhase comparison to control rate
        SendReply.kr(
            Impulse.kr(10) * A2K.kr(capturePhase < 1),
            '/noise/telem/wave/ready',
            [slotIndex, A2K.kr(freq)]
        );
    }).add;

    "  [Telemetry] forge_telemetry_wave_capture SynthDef loaded".postln;

    // =========================================================================
    // BUFFER MANAGEMENT
    // =========================================================================

    ~telemetry.waveBuffers = Array.fill(8, { nil });
    ~telemetry.waveSynths = Array.fill(8, { nil });

    ~telemetry.allocWaveBuffer = { |slot|
        if (~telemetry.waveBuffers[slot].isNil) {
            ~telemetry.waveBuffers[slot] = Buffer.alloc(s, 256, 1);
            "[Telemetry] Allocated wave buffer for slot %".format(slot + 1).postln;
        };
        ~telemetry.waveBuffers[slot];
    };

    ~telemetry.freeWaveBuffer = { |slot|
        if (~telemetry.waveBuffers[slot].notNil) {
            ~telemetry.waveBuffers[slot].free;
            ~telemetry.waveBuffers[slot] = nil;
        };
        if (~telemetry.waveSynths[slot].notNil) {
            ~telemetry.waveSynths[slot].free;
            ~telemetry.waveSynths[slot] = nil;
        };
    };

    "[Telemetry] Infrastructure loaded".postln;
};

// =============================================================================
// BOOT (called from init.scd after endstage infra exists)
// =============================================================================

~bootTelemetryTap = {

    // =========================================================================
    // OSC HANDLER: /noise/telem/enable
    // =========================================================================

    OSCdef(\telemEnable, { |msg, time, addr, recvPort|
        var slot = msg[1].asInteger;  // 1-based from Python (controller adds 1)
        var rate = msg[2].asInteger;
        var idx = slot - 1;  // 0-based for arrays

        if (slot < 1 || slot > 8) {
            "[Telemetry] Invalid slot: %".format(slot).warn;
        } {
            ~telemetry.enabled[idx] = (rate > 0);
            ~telemetry.rates[idx] = rate;

            // Update the generator synth's telemetryRate
            // ~generators uses 1-based slotID (from endstage.scd)
            if (~generators.notNil && ~generators[slot].notNil) {
                ~generators[slot].set(\telemetryRate, rate);
                "[Telemetry] Slot % rate set to %Hz".format(slot, rate).postln;
            } {
                "[Telemetry] Warning: No generator node for slot %".format(slot).warn;
            };
        };
    }, '/noise/telem/enable');

    "  [Telemetry] OSC handler /noise/telem/enable registered".postln;

    // =========================================================================
    // OSC HANDLER: /noise/telem/wave/enable
    // =========================================================================

    OSCdef(\telemWaveEnable, { |msg, time, addr, recvPort|
        var slot = msg[1].asInteger;  // 1-based
        var enable = msg[2].asInteger > 0;
        var idx = slot - 1;  // 0-based for arrays

        if (slot < 1 || slot > 8) {
            "[Telemetry] Invalid slot for wave capture: %".format(slot).warn;
        } {
            if (enable) {
                var buf = ~telemetry[\allocWaveBuffer].value(idx);
                // ~intermediateBus uses 0-based index (from endstage.scd)
                var inBus = ~intermediateBus[idx];

                if (inBus.notNil) {
                    ~telemetry.waveSynths[idx] = Synth(\forge_telemetry_wave_capture, [
                        \inBus, inBus,
                        \slotIndex, idx,
                        \bufnum, buf.bufnum
                    ], ~fxGroup, \addAfter);

                    "[Telemetry] Wave capture started for slot %".format(slot).postln;
                } {
                    "[Telemetry] No intermediate bus for slot %".format(slot).warn;
                };
            } {
                ~telemetry[\freeWaveBuffer].value(idx);
                "[Telemetry] Wave capture stopped for slot %".format(slot).postln;
            };
        };
    }, '/noise/telem/wave/enable');

    "  [Telemetry] OSC handler /noise/telem/wave/enable registered".postln;

    // =========================================================================
    // OSC HANDLER: /noise/telem/gen (relay SendReply data to Python)
    // =========================================================================

    OSCdef(\telemGen, { |msg, time, addr, recvPort|
        // SendReply format: [cmdName, nodeID, replyID, ...data]
        // Forward data values (msg[3..]) to Python via ~pythonAddr
        if (~pythonAddr.notNil) {
            ~pythonAddr.sendMsg('/noise/telem/gen', *msg[3..]);
        };
    }, '/noise/telem/gen');

    "  [Telemetry] OSC handler /noise/telem/gen relay registered".postln;

    // =========================================================================
    // OSC HANDLER: /noise/telem/wave/ready (internal — burst buffer to Python)
    // =========================================================================

    OSCdef(\telemWaveReady, { |msg, time, addr, recvPort|
        var slot = msg[3].asInteger;  // slot from SendReply args
        var freq = msg[4];
        var buf = ~telemetry.waveBuffers[slot];

        if (buf.notNil) {
            // Read 128 samples from buffer and send to Python
            buf.getn(0, 128, { |data|
                if (~pythonAddr.notNil) {
                    ~pythonAddr.sendMsg('/noise/telem/wave', slot, *data);
                };
            });
        };
    }, '/noise/telem/wave/ready');

    "  [Telemetry] OSC handler /noise/telem/wave/ready registered".postln;

    // =========================================================================
    // OSC HANDLER: /noise/telem/hw_wave (relay embedded waveform SendReply)
    // =========================================================================
    // hw_assessment_tap embeds a phase-wrapped 128-sample capture via SendReply.
    // Relay the data to Python in the same format as the buffer-based path.
    // SendReply format: [cmdName, nodeID, replyID, slotIndex, ...128 samples]

    OSCdef(\telemHwWave, { |msg, time, addr, recvPort|
        if (~pythonAddr.notNil) {
            // msg[3] = slotIndex, msg[4..] = 128 waveform samples
            ~pythonAddr.sendMsg('/noise/telem/wave', *msg[3..]);
        };
    }, '/noise/telem/hw_wave');

    "  [Telemetry] OSC handler /noise/telem/hw_wave relay registered".postln;

    // =========================================================================
    // CLEANUP
    // =========================================================================

    ~telemetry.cleanup = {
        8.do { |i|
            ~telemetry[\freeWaveBuffer].value(i);
        };
        OSCdef(\telemEnable).free;
        OSCdef(\telemGen).free;
        OSCdef(\telemWaveEnable).free;
        OSCdef(\telemWaveReady).free;
        OSCdef(\telemHwWave).free;
        "[Telemetry] Cleaned up".postln;
    };

    "[Telemetry] Tap booted (OSC handlers registered)".postln;
};
