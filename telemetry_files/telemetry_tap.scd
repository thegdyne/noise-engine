/*
 * Noise Engine Telemetry Tap Infrastructure
 * 
 * Handles OSC commands from Python to enable/disable telemetry on generators.
 * Works with generators that have the telemetryRate argument.
 *
 * OSC Paths:
 *   /telem/enable [slot, rate]  - Enable telemetry for slot at given rate (0 = disable)
 *   /telem/gen    [slot, ...]   - Outbound: telemetry data from generator
 *   /telem/wave   [slot, ...]   - Outbound: waveform samples from generator
 *
 * Usage:
 *   Load this file after generators are defined.
 *   Generators must include telemetryRate argument (default 0).
 *
 * Reference: DIRECT_OSC_TELEMETRY_SPEC.md
 */

(
// =============================================================================
// TELEMETRY STATE
// =============================================================================

~telemetry = ~telemetry ? ();
~telemetry.enabled = Array.fill(8, { false });
~telemetry.rates = Array.fill(8, { 0 });

// =============================================================================
// OSC HANDLER: /telem/enable
// =============================================================================

OSCdef(\telemEnable, { |msg, time, addr, recvPort|
    var slot = msg[1].asInteger;
    var rate = msg[2].asInteger;
    
    if (slot < 0 || slot > 7) {
        "[Telemetry] Invalid slot: %".format(slot).warn;
    } {
        ~telemetry.enabled[slot] = (rate > 0);
        ~telemetry.rates[slot] = rate;
        
        // Update the generator synth's telemetryRate
        if (~genNodes.notNil && ~genNodes[slot].notNil) {
            ~genNodes[slot].set(\telemetryRate, rate);
            "[Telemetry] Slot % rate set to %Hz".format(slot + 1, rate).postln;
        } {
            "[Telemetry] Warning: No generator node for slot %".format(slot + 1).warn;
        };
    };
}, '/telem/enable');

"  [Telemetry] OSC handler /telem/enable registered".postln;

// =============================================================================
// TELEMETRY-ENABLED SYNTHDEF TEMPLATE
// =============================================================================

/*
 * Generators that want telemetry support should follow this pattern:
 *
 * SynthDef(\forge_myGenerator, { |out, freqBus, customBus0, telemetryRate=0|
 *     var sig, freq, p;
 *     var stage1, stage2, stage3;  // DSP stages for telemetry taps
 *     var phase, badValue;
 *     
 *     p = In.kr(customBus0, 5);
 *     freq = In.kr(freqBus).clip(5, 20000);
 *     
 *     // Phase tracking for Python sync
 *     phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);
 *     
 *     // === DSP STAGES ===
 *     stage1 = SinOsc.ar(freq);
 *     stage2 = /* your processing */;
 *     stage3 = /* final output */;
 *     sig = stage3;
 *     
 *     // Bad value detection
 *     badValue = CheckBadValues.ar(sig, post: 0);
 *     
 *     // === TELEMETRY (only active when telemetryRate > 0) ===
 *     (telemetryRate > 0).if {
 *         SendReply.kr(Impulse.kr(telemetryRate), '/telem/gen', [
 *             \slotIndex.ir(0),
 *             freq,
 *             A2K.kr(phase),
 *             p[0], p[1], p[2], p[3], p[4],
 *             Amplitude.ar(stage1, 0.01, 0.1),
 *             Amplitude.ar(stage2, 0.01, 0.1),
 *             Amplitude.ar(stage3, 0.01, 0.1),
 *             Peak.ar(sig, Impulse.kr(telemetryRate)).lag(0.1),
 *             A2K.kr(badValue)
 *         ]);
 *     };
 *     
 *     sig = NumChannels.ar(sig, 2);
 *     ReplaceOut.ar(out, sig);
 * }).add;
 */

// =============================================================================
// WAVEFORM CAPTURE SYNTHDEF (Phase-Relative)
// =============================================================================

/*
 * This SynthDef captures exactly one cycle of audio, regardless of frequency.
 * It's instantiated on-demand when waveform telemetry is requested.
 *
 * The zero-crossing trigger ensures we always capture a complete period.
 */

SynthDef(\forge_telemetry_wave_capture, { |inBus, slotIndex=0, bufnum|
    var sig, mono, phase, captureTrig, capturePhase;
    var freq, frameSize;
    
    // Read from intermediate bus (pre-end-stage)
    sig = In.ar(inBus, 2);
    mono = Mix.ar(sig) * 0.5;
    
    // Estimate frequency from zero-crossings (for adaptive capture)
    // This is approximate but sufficient for phase-relative capture
    freq = ZeroCrossing.ar(mono).max(20).min(20000);
    
    // Frame size: exactly one cycle at current frequency
    // Clamped to buffer size
    frameSize = (SampleRate.ir / freq).clip(64, BufFrames.kr(bufnum));
    
    // Zero-crossing trigger (rising edge)
    captureTrig = (mono >= 0) & (Delay1.ar(mono) < 0);
    
    // Phase within capture frame
    capturePhase = Phasor.ar(captureTrig, 1, 0, frameSize);
    
    // Write to buffer
    BufWr.ar(mono, bufnum, capturePhase);
    
    // Send buffer contents when frame completes
    // Throttled to prevent network flooding
    SendReply.kr(
        Impulse.kr(12) * (capturePhase < 1),  // 12Hz max, only at frame start
        '/telem/wave/ready',
        [slotIndex, freq]
    );
}).add;

"  [Telemetry] forge_telemetry_wave_capture SynthDef loaded".postln;

// =============================================================================
// WAVEFORM BUFFER MANAGEMENT
// =============================================================================

~telemetry.waveBuffers = Array.fill(8, { nil });
~telemetry.waveSynths = Array.fill(8, { nil });

~telemetry.allocWaveBuffer = { |slot|
    if (~telemetry.waveBuffers[slot].isNil) {
        ~telemetry.waveBuffers[slot] = Buffer.alloc(s, 256, 1);  // 256 samples max
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

// =============================================================================
// OSC HANDLER: /telem/wave/enable
// =============================================================================

OSCdef(\telemWaveEnable, { |msg, time, addr, recvPort|
    var slot = msg[1].asInteger;
    var enable = msg[2].asInteger > 0;
    
    if (slot < 0 || slot > 7) {
        "[Telemetry] Invalid slot for wave capture: %".format(slot).warn;
    } {
        if (enable) {
            // Allocate buffer and start capture synth
            var buf = ~telemetry.allocWaveBuffer.(slot);
            var inBus = ~intermediateBuses[slot];  // Assumes this exists
            
            if (inBus.notNil) {
                ~telemetry.waveSynths[slot] = Synth(\forge_telemetry_wave_capture, [
                    \inBus, inBus,
                    \slotIndex, slot,
                    \bufnum, buf.bufnum
                ], ~fxGroup, \addAfter);  // After generators, before end-stage
                
                "[Telemetry] Wave capture started for slot %".format(slot + 1).postln;
            } {
                "[Telemetry] No intermediate bus for slot %".format(slot + 1).warn;
            };
        } {
            // Stop capture and free buffer
            ~telemetry.freeWaveBuffer.(slot);
            "[Telemetry] Wave capture stopped for slot %".format(slot + 1).postln;
        };
    };
}, '/telem/wave/enable');

"  [Telemetry] OSC handler /telem/wave/enable registered".postln;

// =============================================================================
// OSC HANDLER: /telem/wave/ready (Internal - Burst Buffer to Python)
// =============================================================================

OSCdef(\telemWaveReady, { |msg, time, addr, recvPort|
    var slot = msg[3].asInteger;
    var freq = msg[4];
    var buf = ~telemetry.waveBuffers[slot];
    
    if (buf.notNil) {
        // Read buffer and send to Python
        // Use 128 samples for consistency
        buf.getn(0, 128, { |data|
            // Send via NetAddr to Python (assumes ~pythonAddr is set)
            if (~pythonAddr.notNil) {
                ~pythonAddr.sendMsg('/telem/wave', slot, *data);
            };
        });
    };
}, '/telem/wave/ready');

"  [Telemetry] OSC handler /telem/wave/ready registered".postln;

// =============================================================================
// HELPER: Set Python Address
// =============================================================================

~telemetry.setPythonAddr = { |ip="127.0.0.1", port=57121|
    ~pythonAddr = NetAddr(ip, port);
    "[Telemetry] Python address set to %:%".format(ip, port).postln;
};

// Default: localhost
~telemetry.setPythonAddr.("127.0.0.1", 57121);

// =============================================================================
// CLEANUP
// =============================================================================

~telemetry.cleanup = {
    8.do { |i|
        ~telemetry.freeWaveBuffer.(i);
    };
    OSCdef(\telemEnable).free;
    OSCdef(\telemWaveEnable).free;
    OSCdef(\telemWaveReady).free;
    "[Telemetry] Cleaned up".postln;
};

// =============================================================================
// STATUS
// =============================================================================

"[Telemetry] Infrastructure loaded".postln;
"  - /telem/enable [slot, rate] : Enable/disable control telemetry".postln;
"  - /telem/wave/enable [slot, enable] : Enable/disable waveform capture".postln;
"  - ~telemetry.setPythonAddr.(ip, port) : Set Python OSC address".postln;
)
