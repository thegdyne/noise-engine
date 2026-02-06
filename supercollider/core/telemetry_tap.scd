/*
 * Noise Engine Telemetry Tap Infrastructure
 * Handles OSC commands to enable telemetry on generators.
 * Capture types:
 * INTERNAL: forge_internal_telem_tap (Infrastructure Observer)
 * EXTERNAL: hw_profile_tap (Self-Contained Embedded SendReply)
 */

~setupTelemetryTap = {
    ~telemetry = ~telemetry ? ();
    ~telemetry.enabled = Array.fill(8, { false });
    ~telemetry.rates = Array.fill(8, { 0 });
    ~telemetry.sourceIds = Array.fill(8, { 0 });  // 0=pre-analog, 1=post-analog, 2=post-endstage
    ~telemetry.calGains = Array.fill(8, { 1.0 });

    // Track synth nodes
    ~telemetry.waveBuffers = Array.fill(8, { nil });
    ~telemetry.waveSynths = Array.fill(8, { nil });
    ~telemetry.tapSynths = Array.fill(8, { nil });

    // --- 1. Waveform Capture Synth (Audio -> Buffer) ---
    // Captures 1024 consecutive mono samples starting from a zero-crossing.
    // RecordBuf with run: gating writes sequentially while gate is high,
    // no samples leak when idle. loop:0 stops after one full pass.
    // run: is (captureGate + Delay1(captureGate)).clip(0,1) — ensures
    // run=1 on the trigger sample AND all subsequent samples, while
    // dropping to 0 when idle (no write leak).
    //
    // Trigger chain is audio-rate end-to-end so the capture start is
    // sample-accurate (no block-quantization jitter). Previous kr-domain
    // chain (T2K→Trig1.kr→T2A) introduced up to blockSize-1 samples of
    // start-time jitter, causing progressive persistence thickening.
    SynthDef(\forge_telemetry_wave_capture, { |inBus, slotIndex=0, bufnum|
        var sig, mono, edge, start;
        var captureGate, gateKr;
        var gateFall, frames, dur, freqKr, div, sendTrig;

        // Read from intermediate bus (stereo), mix to mono
        sig = In.ar(inBus, 2);
        mono = Mix.ar(sig) * 0.5;

        frames = BufFrames.kr(bufnum);
        dur = BufDur.kr(bufnum);

        // Rising zero-cross edge at audio rate
        edge = (mono >= 0) & (Delay1.ar(mono) < 0);

        // Canonical one-shot start pulse:
        // 1. Provisional gate masks subsequent edges while capturing
        // 2. start = first edge only (Delay1 still reads 0 on the opening sample)
        // 3. Recompute canonical gate from start so trigger is hard one-shot
        captureGate = Trig1.ar(edge, dur);
        start = edge * (Delay1.ar(captureGate) < 0.5);
        captureGate = Trig1.ar(start, dur);
        gateKr = A2K.kr(captureGate);

        // --- RecordBuf with run: gating ---
        // run = captureGate OR Delay1(captureGate): guarantees run=1
        // on the trigger sample (captureGate just rose) AND on all
        // subsequent samples (Delay1 sustains). Both go 0 when idle.
        RecordBuf.ar(
            mono,
            bufnum,
            offset: 0,                      // explicit start position
            recLevel: 1,
            preLevel: 0,                    // overwrite, don't mix
            run: (captureGate + Delay1.ar(captureGate)).clip(0, 1),
            loop: 0,                        // single pass, then stop
            trigger: start,                 // discrete impulse resets write position
            doneAction: 0                   // keep synth alive
        );

        // --- SendReply on capture completion (gate fall) ---
        // kr is fine here — only affects notification latency, not capture accuracy.
        gateFall = (Delay1.kr(gateKr) > 0.5) & (gateKr < 0.5);

        // Rate limit to ~10Hz independent of freq and SR
        freqKr = A2K.kr(ZeroCrossing.ar(mono).max(20).min(20000));
        div = (SampleRate.ir / (frames * 10)).round(1).max(1);
        sendTrig = PulseDivider.kr(gateFall, div);

        SendReply.kr(sendTrig, '/noise/telem/wave/ready', [slotIndex, freqKr]);
    }).add;

    // --- 2. Internal Data Tap Synth (Audio -> OSC Data) ---
    // Reads audio from the selected tap point and control params from customBus0.
    // sourceId: 0=pre-analog, 1=post-analog, 2=post-endstage
    SynthDef(\forge_internal_telem_tap, { |inBus, customBus, slotIndex=0, telemetryRate=0, calGain=1.0, sourceId=0|
        var sig = In.ar(inBus, 2);
        var p = In.kr(customBus, 5);

        // Stereo average (not left-only)
        var mono = Mix.ar(sig) * 0.5 * calGain;

        var rms = Amplitude.ar(mono, 0.01, 0.1);
        var freq = ZeroCrossing.ar(mono).max(20).min(20000);

        // Clamp telemetry rate to prevent OSC spam
        var rate = telemetryRate.clip(0, 120);

        // Peak meter window: always valid even at low rate
        var peak = Peak.ar(mono, Impulse.kr(rate.max(0.1))).lag(0.1);

        // Normalized 0-1 phase for overlay alignment
        var trig = (mono >= 0) & (Delay1.ar(mono) < 0);
        var phase = Phasor.ar(trig, freq / SampleRate.ir, 0, 1);

        SendReply.kr(Impulse.kr(rate) * (rate > 0), '/noise/telem/gen', [
            slotIndex, freq,
            A2K.kr(phase),
            p[0], p[1], p[2], p[3], p[4],
            rms, rms, rms,
            peak, 0, peak,
            sourceId
        ]);
    }).add;

    // Buffer helpers
    ~telemetry.allocWaveBuffer = { |slot|
        if (~telemetry.waveBuffers[slot].notNil) { ~telemetry.waveBuffers[slot].free; };
        ~telemetry.waveBuffers[slot] = Buffer.alloc(s, 1024, 1);
        ~telemetry.waveBuffers[slot];
    };

    ~telemetry.freeWaveBuffer = { |slot|
        if (~telemetry.waveBuffers[slot].notNil) { ~telemetry.waveBuffers[slot].free; ~telemetry.waveBuffers[slot] = nil; };
        if (~telemetry.waveSynths[slot].notNil) { ~telemetry.waveSynths[slot].free; ~telemetry.waveSynths[slot] = nil; };
    };

    // Resolve audio bus for a given source ID
    // 0=pre-analog (intermediateBus), 1=post-analog (enhancedBus), 2=post-endstage (genBus)
    ~telemetry.busForSource = { |idx, sourceId|
        case
            { sourceId == 0 } { ~intermediateBus[idx].index }
            { sourceId == 1 } { ~enhancedBus[idx].index }
            { sourceId == 2 } { ~genBus[idx].index }
            { ~intermediateBus[idx].index };  // default
    };

    // --- 3. Hardware Send SynthDef (Audio -> Physical Outputs) ---
    // Routes intermediate bus audio to configurable MOTU physical outputs.
    // Parallel consumer of the same tap point as telemetry.
    SynthDef(\forge_hardware_send, { |inBus, outPair=1, gainDB=0|
        var sig, baseChan;
        sig = In.ar(inBus, 2);
        baseChan = 2 + ((outPair - 1) * 2);
        sig = sig * gainDB.dbamp.lag(0.05);
        sig = Limiter.ar(sig, 0.95, 0.01);
        Out.ar(baseChan, sig);
    }).add;

    "[Telemetry] Infrastructure loaded".postln;
};

~bootTelemetryTap = {
    // Enable/Disable Global (Params)
    OSCdef(\telemEnable, { |msg|
        var slot = msg[1].asInteger;
        var rate = msg[2].asInteger;
        if ((slot >= 1) && (slot <= 8)) {
            ~telemetry.enabled[slot-1] = (rate > 0);
            ~telemetry.rates[slot-1] = rate;
            if (~generators[slot].notNil) { ~generators[slot].set(\telemetryRate, rate); };
        };
    }, '/noise/telem/enable');

    // Spawn/Free Internal Data Tap
    OSCdef(\telemTapEnable, { |msg|
        var slot = msg[1].asInteger;
        var rate = msg[2].asInteger;
        var calGain = if(msg.size > 3, { msg[3].asFloat }, { 1.0 });
        var idx = slot - 1;
        var custom0Idx, slotKey, useUnified, sourceId, tapBus;

        if ((slot >= 1) && (slot <= 8)) {
            // Track state so \telemSource can respawn with correct rate/gain
            ~telemetry.rates[idx] = rate;
            ~telemetry.enabled[idx] = (rate > 0);
            ~telemetry.calGains[idx] = calGain;

            // Always free existing first to prevent dupes/leaks
            if (~telemetry.tapSynths[idx].notNil) {
                ~telemetry.tapSynths[idx].free;
                ~telemetry.tapSynths[idx] = nil;
            };

            if (rate > 0) {
                if (~intermediateBus[idx].notNil && ~generators[slot].notNil) {
                    // Look up customBus0 (same pattern as endstage.scd)
                    slotKey = slot.asString;
                    useUnified = ~genUnifiedSlots.includes(slot);
                    if (useUnified) {
                        custom0Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom0").asSymbol].index;
                    } {
                        custom0Idx = ~genParams[slot][\custom][0].index;
                    };

                    // Resolve tap bus from current source selection
                    sourceId = ~telemetry.sourceIds[idx];
                    tapBus = ~telemetry[\busForSource].value(idx, sourceId);

                    ~telemetry.tapSynths[idx] = Synth(\forge_internal_telem_tap, [
                        \inBus, tapBus,
                        \customBus, custom0Idx,
                        \slotIndex, idx, \telemetryRate, rate,
                        \calGain, calGain,
                        \sourceId, sourceId
                    ], ~fxGroup, \addAfter);
                    "[Telemetry] Internal Tap START slot % source % (bus: %, calGain: %)".format(slot, sourceId, tapBus, calGain).postln;
                };
            } {
                "[Telemetry] Internal Tap STOP slot %".format(slot).postln;
            };
        };
    }, '/noise/telem/tap/enable');

    // Telemetry Source Selection (0=pre-analog, 1=post-analog, 2=post-endstage)
    // Restarts the tap synth with the new bus if already running.
    OSCdef(\telemSource, { |msg|
        var slot = msg[1].asInteger;
        var sourceId = msg[2].asInteger.clip(0, 2);
        var idx = slot - 1;
        var sourceNames = ["Pre-Analog", "Post-Analog", "Post-Endstage"];

        if ((slot >= 1) && (slot <= 8)) {
            ~telemetry.sourceIds[idx] = sourceId;
            "[Telemetry] Source select slot %: % (%)".format(slot, sourceId, sourceNames[sourceId]).postln;

            // If tap is running, restart it with the new bus
            if (~telemetry.tapSynths[idx].notNil) {
                var rate = ~telemetry.rates[idx];
                // Re-trigger the tap enable logic (rate > 0 restarts, rate 0 stops)
                if (rate > 0) {
                    // Free and re-spawn via the existing OSCdef handler
                    ~telemetry.tapSynths[idx].free;
                    ~telemetry.tapSynths[idx] = nil;
                    // Inline respawn (mirrors the telemTapEnable logic)
                    if (~intermediateBus[idx].notNil && ~generators[slot].notNil) {
                        var slotKey = slot.asString;
                        var useUnified = ~genUnifiedSlots.includes(slot);
                        var custom0Idx, tapBus;
                        if (useUnified) {
                            custom0Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom0").asSymbol].index;
                        } {
                            custom0Idx = ~genParams[slot][\custom][0].index;
                        };
                        tapBus = ~telemetry[\busForSource].value(idx, sourceId);
                        ~telemetry.tapSynths[idx] = Synth(\forge_internal_telem_tap, [
                            \inBus, tapBus,
                            \customBus, custom0Idx,
                            \slotIndex, idx, \telemetryRate, rate,
                            \calGain, ~telemetry.calGains[idx],
                            \sourceId, sourceId
                        ], ~fxGroup, \addAfter);
                    };
                };
            };

            // If wave capture is running, restart it with the new bus
            if (~telemetry.waveSynths[idx].notNil) {
                var waveBus = ~telemetry[\busForSource].value(idx, sourceId);
                ~telemetry.waveSynths[idx].free;
                if (~telemetry.waveBuffers[idx].notNil) {
                    ~telemetry.waveSynths[idx] = Synth(\forge_telemetry_wave_capture, [
                        \inBus, waveBus,
                        \slotIndex, idx, \bufnum, ~telemetry.waveBuffers[idx].bufnum
                    ], ~fxGroup, \addAfter);
                };
                "[Telemetry] Wave capture restarted slot % (bus: %)".format(slot, waveBus).postln;
            };
        };
    }, '/noise/telem/source');

    // Waveform Capture
    OSCdef(\telemWaveEnable, { |msg|
        var slot = msg[1].asInteger;
        var enable = msg[2].asInteger > 0;
        var idx = slot - 1;
        var buf;

        if ((slot >= 1) && (slot <= 8)) {
            if (enable) {
                var waveBus = ~telemetry[\busForSource].value(idx, ~telemetry.sourceIds[idx]);
                buf = ~telemetry[\allocWaveBuffer].value(idx);
                if (~telemetry.waveSynths[idx].notNil) { ~telemetry.waveSynths[idx].free; };
                if (~intermediateBus[idx].notNil) {
                    // Use source-selected bus (matches data tap)
                    ~telemetry.waveSynths[idx] = Synth(\forge_telemetry_wave_capture, [
                        \inBus, waveBus,
                        \slotIndex, idx, \bufnum, buf.bufnum
                    ], ~fxGroup, \addAfter);
                };
            } {
                ~telemetry[\freeWaveBuffer].value(idx);
            };
        };
    }, '/noise/telem/wave/enable');

    // Relay Handlers
    OSCdef(\telemGen, { |msg| if (~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/telem/gen', *msg[3..]); }; }, '/noise/telem/gen');
    OSCdef(\telemWaveReady, { |msg|
        var slot=msg[3].asInteger;
        if (~telemetry.waveBuffers[slot].notNil) {
            ~telemetry.waveBuffers[slot].getn(0, 1024, { |data| if (~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/telem/wave', slot, *data); } });
        };
    }, '/noise/telem/wave/ready');
    OSCdef(\telemHwWave, { |msg| if (~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/telem/wave', *msg[3..]); }; }, '/noise/telem/hw_wave');

    ~telemetry.cleanup = {
        8.do { |i|
            ~telemetry[\freeWaveBuffer].value(i);
            if (~telemetry.tapSynths[i].notNil) { ~telemetry.tapSynths[i].free; ~telemetry.tapSynths[i] = nil; };
            // Clean up hardware send synths
            if (~hardwareSendSynths.notNil && ~hardwareSendSynths[i].notNil) {
                ~hardwareSendSynths[i].free; ~hardwareSendSynths[i] = nil;
            };
        };
        [\telemEnable, \telemTapEnable, \telemSource, \telemGen, \telemWaveEnable, \telemWaveReady, \telemHwWave, \hwSendEnable, \hwSendDisable].do { |key| OSCdef(key).free; };
        "[Telemetry] Cleaned up".postln;
    };
    "[Telemetry] Tap booted".postln;
};

~bootHardwareSend = {
    // Initialize synth tracking array (8 slots, nil = no active send)
    ~hardwareSendSynths = Array.fill(8, { nil });

    // Enable hardware send: spawn forge_hardware_send synth for slot
    OSCdef(\hwSendEnable, { |msg|
        var slot = msg[1].asInteger;
        var outPair = msg[2].asInteger;
        var gainDB = msg[3].asFloat;
        var idx = slot;  // 0-based from Python

        if ((idx >= 0) && (idx < 8) && (outPair >= 1)) {
            // Free existing synth for this slot to prevent dupes
            if (~hardwareSendSynths[idx].notNil) {
                ~hardwareSendSynths[idx].free;
                ~hardwareSendSynths[idx] = nil;
            };

            if (~intermediateBus[idx].notNil) {
                ~hardwareSendSynths[idx] = Synth(\forge_hardware_send, [
                    \inBus, ~intermediateBus[idx].index,
                    \outPair, outPair,
                    \gainDB, gainDB
                ], ~fxGroup, \addAfter);
                "[HW Send] Enabled slot % -> outPair % (gain: % dB)".format(idx, outPair, gainDB).postln;
            } {
                "[HW Send] No intermediate bus for slot %".format(idx).postln;
            };
        };
    }, '/noise/telem/hw_send/enable');

    // Disable hardware send: free synth for slot
    OSCdef(\hwSendDisable, { |msg|
        var slot = msg[1].asInteger;
        var idx = slot;  // 0-based from Python

        if ((idx >= 0) && (idx < 8)) {
            if (~hardwareSendSynths[idx].notNil) {
                ~hardwareSendSynths[idx].free;
                ~hardwareSendSynths[idx] = nil;
                "[HW Send] Disabled slot %".format(idx).postln;
            };
        };
    }, '/noise/telem/hw_send/disable');

    "[HW Send] Hardware send booted".postln;
};
