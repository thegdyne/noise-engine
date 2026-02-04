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
    ~telemetry.calGains = Array.fill(8, { 1.0 });  // Persist across source changes

    // Track synth nodes
    ~telemetry.waveBuffers = Array.fill(8, { nil });
    ~telemetry.waveSynths = Array.fill(8, { nil });
    ~telemetry.tapSynths = Array.fill(8, { nil });

    // --- 1. Waveform Capture Synth (Audio -> Buffer) ---
    // Variable-speed phasor stretches exactly one cycle across the entire buffer,
    // eliminating stale tail samples that caused waveform corruption.
    SynthDef(\forge_telemetry_wave_capture, { |inBus, slotIndex=0, bufnum|
        var sig, mono, freq, trig, frames, step, phase, phaseKr, wrapped;

        sig = In.ar(inBus, 2);
        mono = Mix.ar(sig) * 0.5;

        freq = ZeroCrossing.ar(mono).max(20).min(20000);

        // Rising zero-crossing to re-sync phase (one cycle capture)
        trig = (mono >= 0) & (Delay1.ar(mono) < 0);

        frames = BufFrames.kr(bufnum);     // 1024
        step   = (freq * frames) / SampleRate.ir; // advances 0..frames in one cycle
        phase  = Phasor.ar(trig, step, 0, frames);

        BufWr.ar(mono, bufnum, phase);

        // Detect wrap at control rate (SendReply requires kr trigger)
        phaseKr = A2K.kr(phase);
        wrapped = phaseKr < Delay1.kr(phaseKr);

        // Notify no faster than 10Hz
        SendReply.kr(Impulse.kr(10) * wrapped, '/noise/telem/wave/ready', [slotIndex, A2K.kr(freq)]);
    }).add;

    // --- 2. Internal Data Tap Synth (Audio -> OSC Data) ---
    // Reads audio from the selected tap point and control params from customBus0.
    // sourceId: 0=pre-analog, 1=post-analog, 2=post-endstage
    SynthDef(\forge_internal_telem_tap, { |inBus, customBus, slotIndex=0, telemetryRate=0, calGain=1.0, sourceId=0|
        var sig = In.ar(inBus, 2);
        var p = In.kr(customBus, 5);
        var mono = Mix.ar(sig) * 0.5 * calGain;
        var rms = Amplitude.ar(mono, 0.01, 0.1);
        var peak = Peak.ar(mono, Impulse.kr(telemetryRate.max(0.1))).lag(0.1);
        var freq = ZeroCrossing.ar(mono).max(20).min(20000);
        var trig = (mono >= 0) & (Delay1.ar(mono) < 0);
        var phase = Phasor.ar(trig, freq / SampleRate.ir, 0, 1); // 0..1

        SendReply.kr(Impulse.kr(telemetryRate) * (telemetryRate > 0), '/noise/telem/gen', [
            slotIndex, freq,
            A2K.kr(phase),                // Normalized 0-1 phase for overlay alignment
            p[0], p[1], p[2], p[3], p[4], // Real params from control bus
            rms, rms, rms,                // Stages 1-3
            peak, 0, peak,               // BadVal, Peak3
            sourceId                      // Tap source identification
        ]);
    }).add;

    // Buffer helpers
    ~telemetry.allocWaveBuffer = { |slot|
        // Always free and reallocate to ensure correct buffer size
        if (~telemetry.waveBuffers[slot].notNil) {
            ~telemetry.waveBuffers[slot].free;
        };
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
            // Track state so \telemSource can respawn with correct rate/calGain
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
        };
        [\telemEnable, \telemTapEnable, \telemSource, \telemGen, \telemWaveEnable, \telemWaveReady, \telemHwWave].do { |key| OSCdef(key).free; };
        "[Telemetry] Cleaned up".postln;
    };
    "[Telemetry] Tap booted".postln;
};
