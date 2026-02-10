/*
Step Engine v2 — Persistent SynthDef per slot (clock-locked, zero-jitter)

Each slot has a persistent \stepEngineSlot synth that:
- Reads clockTrigBus directly via In.ar (no OSC round-trip)
- Steps through buffer-based note/step data via BufRd.kr
- Writes freq + trigger directly to buses (ReplaceOut)
- Sends position via SendReply for UI playhead

Buffer layout per slot: 16 frames x 4 channels
  ch0=type (0=NOTE, 1=REST, 2=TIE), ch1=note, ch2=velocity, ch3=gate

Modes per slot:
- 0=OFF: no action (synth idles, no bus writes)
- 1=ARP: steps through expanded note list
- 2=SEQ: steps through step list with type/note/vel/gate

OSC inputs from Python (handled here):
- /noise/arp/set_notes [slot_0indexed, note1, ...] — set ARP note list via buffer
- /noise/arp/set_bulk [slot_0indexed, stepCount, type1,note1,vel1,gate1, ...] — Euclidean ARP buffer
- /noise/step/set_rate [slot_0indexed, fabricIdx]  — set clock fabric index
- /noise/step/reset [slot_0indexed] — reset SC PulseCount (RST)
- /noise/seq/set_bulk [slot_0indexed, length, type1, note1, vel1, gate1, ...] — set SEQ steps
- /noise/seq/set_play_mode [slot_0indexed, playMode] — set SEQ play mode

OSC output to Python:
- /noise/step/event [slot_0indexed, position] — step event for UI playhead
  (replyID = bufnum for slot identification)

Dependencies: buses.scd (~clockTrigBus, ~midiTrigBus, ~busRegistry, ~genGroup, ~stepBuf),
             midi_handler.scd (~stopMidiRetrig, ~triggerMidiGate)
*/

// === SYNTHDEF (loaded at file parse time, before server boot completes) ===

SynthDef(\stepEngineSlot, {
    |clockTrigBus, freqBus, midiTrigBusChan,
     bufnum, mode=0, fabricIdx=6, stepCount=0,
     playMode=0|

    var allTrigs, tick, edge;
    var resetPulse, count;
    var posFwd, posRev, posPP, posRand, pos;
    var step, type, note, vel, gateFrac;
    var active, isNote;
    var freq, freqHeld, freqIn, freqOut;
    var trigPulse, trigIn, trigOut;
    var safeStepCount;

    // Read all 13 clock fabric trigger channels
    allTrigs = In.ar(clockTrigBus, 13);
    // Select the fabric channel for this slot's rate
    tick = Select.ar(fabricIdx, allTrigs);
    // Convert audio trigger to control-rate edge (one trigger per control block)
    edge = T2K.kr(tick);

    // Position counter with reset support (\resetTrig is a TrigControl — must use NamedControl syntax)
    resetPulse = Trig1.kr(\resetTrig.tr(0), ControlDur.ir);
    count = PulseCount.kr(edge, resetPulse);

    // Compute position for each play mode
    safeStepCount = max(stepCount, 1);
    posFwd  = count % safeStepCount;
    posRev  = (safeStepCount - 1) - (count % safeStepCount);
    posPP   = Fold.kr(count, 0, max(stepCount - 1, 0));
    posRand = TIRand.kr(0, max(stepCount - 1, 0), edge);
    // Select active play mode: 0=FWD, 1=REV, 2=PP, 3=RAND
    pos = Select.kr(playMode, [posFwd, posRev, posPP, posRand]);

    // Read step data from buffer (4 channels: type, note, vel, gate)
    step = BufRd.kr(4, bufnum, pos, loop: 1, interpolation: 1);
    // gateFrac: captured but not yet applied — reserved for v2.1 gate/envelope control
    type = step[0]; note = step[1]; vel = step[2]; gateFrac = step[3];

    // Active = mode > 0 AND we have steps
    active = (mode > 0.5) * (stepCount > 0.5);
    // isNote = type is NOTE (0) AND we're active
    isNote = (type < 0.5) * active;

    // Sample-and-hold frequency: only updates on NOTE steps
    freq = note.midicps;
    freqHeld = Latch.kr(freq, edge * isNote);
    // P0.1: pass through current bus value when inactive — avoids clobbering MIDI/knob freq
    freqIn = In.kr(freqBus);
    freqOut = Select.kr(active, [freqIn, freqHeld]);
    ReplaceOut.kr(freqBus, freqOut);

    // Generate trigger pulse: 2-sample audio pulse on NOTE steps
    trigPulse = Trig1.ar(K2A.ar(edge * isNote), SampleDur.ir * 2);
    // Pass through current bus when inactive — avoids clobbering MIDI/keyboard triggers
    trigIn = In.ar(midiTrigBusChan, 1);
    trigOut = Select.ar(K2A.ar(active), [trigIn, trigPulse]);
    ReplaceOut.ar(midiTrigBusChan, trigOut);

    // Send position to Python for UI playhead (replyID = bufnum for identification)
    SendReply.kr(edge * active, '/noise/step/event', [pos], bufnum);
}).add;


// === SETUP (called post-boot, after ~startClock creates groups) ===

~setupStepEngine = {
    "Setting up Step Engine v2 (persistent SynthDef)...".postln;

    // Allocate per-slot buffers: 16 frames x 4 channels (type, note, vel, gate)
    ~stepBuf = Array.fill(8, { Buffer.alloc(s, 16, 4) });

    // Wait for buffers to be ready on server before spawning synths that read them
    s.sync;

    // Spawn persistent synths — one per slot, BEFORE generators in node order
    ~stepSynths = Array.fill(8, { |i|
        var slot1 = i + 1;
        var freqBusKey = ("gen_" ++ slot1 ++ "_freq").asSymbol;
        Synth(\stepEngineSlot, [
            \clockTrigBus, ~clockTrigBus.index,
            \freqBus, ~busRegistry[freqBusKey].index,
            \midiTrigBusChan, ~midiTrigBus.index + i,
            \bufnum, ~stepBuf[i].bufnum,
            \mode, 0,
            \fabricIdx, 6,
            \stepCount, 0,
            \playMode, 0,
        ], target: ~genGroup, addAction: \addBefore);
    });

    // === OSC HANDLERS (step engine data transfer) ===

    // ARP: set expanded note list via buffer
    // Empty payload = clear (stepCount -> 0)
    OSCdef(\arpSetNotes, { |msg|
        var slot0 = msg[1].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            var notes = msg[2..].collect(_.asInteger);
            var buf = ~stepBuf[slot0];
            if(notes.size > 0, {
                // Pack notes into buffer: type=0 (NOTE), note=N, vel=127, gate=1.0
                var data = [];
                notes.do { |n|
                    data = data ++ [0, n, 127, 1.0];  // type=NOTE, note, vel, gate
                };
                buf.setn(0, data);
                ~stepSynths[slot0].set(\stepCount, notes.size, \resetTrig, 1);
            }, {
                // Empty notes: clear buffer and zero stepCount
                buf.zero;
                ~stepSynths[slot0].set(\stepCount, 0, \resetTrig, 1);
            });
        });
    }, '/noise/arp/set_notes');

    // ARP: set Euclidean-encoded bulk buffer (NOTE + REST frames)
    // Format: [slot_0indexed, stepCount, type1, note1, vel1, gate1, ...]
    OSCdef(\arpSetBulk, { |msg|
        var slot0 = msg[1].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            var stepCount = msg[2].asInteger;
            var raw = msg[3..];
            var buf = ~stepBuf[slot0];
            var data = [];
            var numSteps = (raw.size / 4).asInteger.min(16);

            numSteps.do { |i|
                data = data ++ [
                    raw[i*4].asInteger,      // type: 0=NOTE, 1=REST
                    raw[i*4+1].asInteger,    // note
                    raw[i*4+2].asInteger,    // velocity
                    raw[i*4+3].asFloat       // gate fraction
                ];
            };

            // Pad remaining frames as REST
            (16 - numSteps).do {
                data = data ++ [1, 60, 0, 0.0];
            };

            buf.setn(0, data);
            ~stepSynths[slot0].set(\stepCount, stepCount.min(16), \resetTrig, 1);
        });
    }, '/noise/arp/set_bulk');

    // ARP/SEQ: set clock rate (fabric index)
    OSCdef(\stepSetRate, { |msg|
        var slot0 = msg[1].asInteger;
        var fabricIdx = msg[2].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            ~stepSynths[slot0].set(\fabricIdx, fabricIdx, \resetTrig, 1);
        });
    }, '/noise/step/set_rate');

    // RST: reset PulseCount for a slot (phase reset without buffer change)
    OSCdef(\stepReset, { |msg|
        var slot0 = msg[1].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            ~stepSynths[slot0].set(\resetTrig, 1);
        });
    }, '/noise/step/reset');

    // SEQ: set bulk step data (4-channel format)
    // Format: [slot_0indexed, length, type1, note1, vel1, gate1, type2, ...]
    OSCdef(\seqSetBulk, { |msg|
        var slot0 = msg[1].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            var length = msg[2].asInteger;
            var raw = msg[3..];
            var buf = ~stepBuf[slot0];
            var data = [];
            var numSteps = (raw.size / 4).asInteger.min(16);

            // Pack received steps
            numSteps.do { |i|
                data = data ++ [
                    raw[i*4].asInteger,      // type: 0=NOTE, 1=REST, 2=TIE
                    raw[i*4+1].asInteger,    // note
                    raw[i*4+2].asInteger,    // velocity
                    raw[i*4+3].asFloat       // gate fraction
                ];
            };

            // Pad remaining steps as REST (type=1)
            (16 - numSteps).do {
                data = data ++ [1, 60, 0, 0.0];
            };

            buf.setn(0, data);
            // playMode is set separately by seqSetPlayMode (called before bulk in handover)
            ~stepSynths[slot0].set(\stepCount, length.min(16), \resetTrig, 1);
        });
    }, '/noise/seq/set_bulk');

    // SEQ: set play mode
    OSCdef(\seqSetPlayMode, { |msg|
        var slot0 = msg[1].asInteger;
        var playMode = msg[2].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            ~stepSynths[slot0].set(\playMode, playMode);
        });
    }, '/noise/seq/set_play_mode');

    "  [x] Step Engine v2 ready (8 persistent synths, buffer-based)".postln;
};
