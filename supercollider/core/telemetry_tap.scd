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

    // Track synth nodes
    ~telemetry.waveBuffers = Array.fill(8, { nil });
    ~telemetry.waveSynths = Array.fill(8, { nil });
    ~telemetry.tapSynths = Array.fill(8, { nil });

    // --- 1. Waveform Capture Synth (Audio -> Buffer) ---
    SynthDef(\forge_telemetry_wave_capture, { |inBus, slotIndex=0, bufnum|
        // VARS MUST BE DECLARED FIRST
        var sig, mono, freq, frameSize, captureTrig, capturePhase;
        var zcCountKr, hasNewFrame;

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

        // Frame-ready detection
        zcCountKr = A2K.kr(PulseCount.ar(captureTrig));
        hasNewFrame = zcCountKr > Delay1.kr(zcCountKr);

        SendReply.kr(Impulse.kr(10) * hasNewFrame, '/noise/telem/wave/ready', [slotIndex, A2K.kr(freq)]);
    }).add;

    // --- 2. Internal Data Tap Synth (Audio -> OSC Data) ---
    // Reads audio from ~intermediateBus and control params from customBus0
    // to provide full telemetry (RMS, peak, freq, params) for any generator.
    SynthDef(\forge_internal_telem_tap, { |inBus, customBus, slotIndex=0, telemetryRate=0, calGain=1.0|
        var sig = In.ar(inBus, 2);
        var p = In.kr(customBus, 5);
        var mono = sig[0] * calGain;
        var rms = Amplitude.ar(mono, 0.01, 0.1);
        var peak = Peak.ar(mono, Impulse.kr(telemetryRate.max(0.1))).lag(0.1);
        var freq = ZeroCrossing.ar(mono).max(20).min(20000);

        SendReply.kr(Impulse.kr(telemetryRate) * (telemetryRate > 0), '/noise/telem/gen', [
            slotIndex, freq,
            0,                            // Phase (no bus available)
            p[0], p[1], p[2], p[3], p[4], // Real params from control bus
            rms, rms, rms,                // Stages 1-3
            peak, 0, peak                 // BadVal, Peak3
        ]);
    }).add;

    // Buffer helpers
    ~telemetry.allocWaveBuffer = { |slot|
        if (~telemetry.waveBuffers[slot].isNil) {
            ~telemetry.waveBuffers[slot] = Buffer.alloc(s, 256, 1);
        };
        ~telemetry.waveBuffers[slot];
    };

    ~telemetry.freeWaveBuffer = { |slot|
        if (~telemetry.waveBuffers[slot].notNil) { ~telemetry.waveBuffers[slot].free; ~telemetry.waveBuffers[slot] = nil; };
        if (~telemetry.waveSynths[slot].notNil) { ~telemetry.waveSynths[slot].free; ~telemetry.waveSynths[slot] = nil; };
    };
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
        var custom0Idx, slotKey, useUnified;

        if ((slot >= 1) && (slot <= 8)) {
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

                    ~telemetry.tapSynths[idx] = Synth(\forge_internal_telem_tap, [
                        \inBus, ~intermediateBus[idx].index,
                        \customBus, custom0Idx,
                        \slotIndex, idx, \telemetryRate, rate,
                        \calGain, calGain
                    ], ~fxGroup, \addAfter);
                    "[Telemetry] Internal Tap START slot % (customBus: %, calGain: %)".format(slot, custom0Idx, calGain).postln;
                };
            } {
                "[Telemetry] Internal Tap STOP slot %".format(slot).postln;
            };
        };
    }, '/noise/telem/tap/enable');

    // Waveform Capture
    OSCdef(\telemWaveEnable, { |msg|
        var slot = msg[1].asInteger;
        var enable = msg[2].asInteger > 0;
        var idx = slot - 1;
        var buf;

        if ((slot >= 1) && (slot <= 8)) {
            if (enable) {
                buf = ~telemetry[\allocWaveBuffer].value(idx);
                if (~telemetry.waveSynths[idx].notNil) { ~telemetry.waveSynths[idx].free; };
                if (~intermediateBus[idx].notNil) {
                    // Must pass .index (raw integer) to Synth
                    ~telemetry.waveSynths[idx] = Synth(\forge_telemetry_wave_capture, [
                        \inBus, ~intermediateBus[idx].index,
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
            ~telemetry.waveBuffers[slot].getn(0, 128, { |data| if (~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/telem/wave', slot, *data); } });
        };
    }, '/noise/telem/wave/ready');
    OSCdef(\telemHwWave, { |msg| if (~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/telem/wave', *msg[3..]); }; }, '/noise/telem/hw_wave');

    ~telemetry.cleanup = {
        8.do { |i|
            ~telemetry[\freeWaveBuffer].value(i);
            if (~telemetry.tapSynths[i].notNil) { ~telemetry.tapSynths[i].free; ~telemetry.tapSynths[i] = nil; };
        };
        [\telemEnable, \telemTapEnable, \telemGen, \telemWaveEnable, \telemWaveReady, \telemHwWave].do { |key| OSCdef(key).free; };
        "[Telemetry] Cleaned up".postln;
    };
    "[Telemetry] Tap booted".postln;
};
