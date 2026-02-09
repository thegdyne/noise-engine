/*
Step Engine — SC-side clock-locked sequencer/arpeggiator

Reads clockTrigBus (via SendReply/OSCdef), writes freq + trigger to midiTrigBus.
Runs in sclang (not a SynthDef) for bus.set + Synth.new access.

Modes per slot:
- 0=OFF: no action
- 1=ARP: steps through expanded note list, fires trigger on each step
- 2=SEQ: steps through step list (NOTE/REST/TIE), fires trigger for NOTE steps

OSC inputs from Python:
- /noise/gen/stepMode [slot_1indexed, mode]       — handled in osc_handlers.scd
- /noise/arp/set_notes [slot_0indexed, note1, ...] — set ARP expanded note list
- /noise/step/set_rate [slot_0indexed, fabricIdx]  — set clock fabric index
- /noise/seq/set_bulk [slot_0indexed, length, type1, note1, vel1, ...] — set SEQ steps
- /noise/seq/set_play_mode [slot_0indexed, playMode] — set SEQ play mode

OSC output to Python:
- /noise/step/event [slot_0indexed, position]      — step event for UI playhead

Dependencies: buses.scd (~genStepMode, ~midiTrigBus, ~busRegistry),
             midi_handler.scd (~triggerMidiGate), bus_unification.scd (~queueBaseUpdate)
*/

~setupStepEngine = {
    "Setting up Step Engine...".postln;

    // Per-slot step engine state
    ~stepEngine = Array.fill(8, {
        Dictionary.newFrom([
            \mode, 0,            // 0=OFF, 1=ARP, 2=SEQ
            \notes, [],          // ARP: expanded note list (MIDI notes)
            \steps, [],          // SEQ: array of [type, note, vel] triplets
            \position, 0,        // Current step index
            \fabricIdx, 6,       // Clock fabric index to listen on (default CLK)
            \length, 16,         // SEQ active length
            \lastNote, nil,      // Last sounded MIDI note (for REST cleanup)
            \ppFwd, true,        // Ping-pong direction (SEQ PINGPONG mode)
            \playMode, 0,        // SEQ play mode: 0=FWD, 1=REV, 2=PP, 3=RAND
        ])
    });

    // === ADVANCE LOGIC ===

    ~stepEngineAdvance = { |slotIdx|
        var eng = ~stepEngine[slotIdx];
        var slot = slotIdx + 1;  // 1-indexed for bus/trigger access
        var mode = eng[\mode];

        if(mode == 1, {
            // === ARP MODE ===
            var notes = eng[\notes];
            var n = notes.size;
            if(n > 0, {
                var pos = eng[\position] % n;
                var note = notes[pos];
                var freq = note.midicps;
                var freqBusKey = ("gen_" ++ slot ++ "_freq").asSymbol;

                // Set frequency immediately on bus
                if(~busRegistry.notNil && ~busRegistry[freqBusKey].notNil, {
                    ~busRegistry[freqBusKey].set(freq);
                });
                // Queue for modulation system
                if(~queueBaseUpdate.notNil, {
                    ~queueBaseUpdate.(freqBusKey, freq);
                });

                // Fire trigger on midiTrigBus
                ~triggerMidiGate.(slot, 1.0);

                // Send step event to Python for playhead
                if(~pythonAddr.notNil, {
                    ~pythonAddr.sendMsg('/noise/step/event', slotIdx, pos);
                });

                // Advance position (wraps via modulo on next call)
                eng[\position] = pos + 1;
            });
        });

        if(mode == 2, {
            // === SEQ MODE ===
            var steps = eng[\steps];
            var length = eng[\length].min(steps.size);
            if(length > 0, {
                var pos = eng[\position];
                var stepData = steps[pos];
                var stepType = stepData[0];  // 0=NOTE, 1=REST, 2=TIE
                var note = stepData[1];
                var vel = stepData[2];

                case
                { stepType == 0 } {
                    // NOTE: set freq + fire trigger
                    var freq = note.midicps;
                    var freqBusKey = ("gen_" ++ slot ++ "_freq").asSymbol;
                    var amp = vel / 127.0;

                    if(~busRegistry.notNil && ~busRegistry[freqBusKey].notNil, {
                        ~busRegistry[freqBusKey].set(freq);
                    });
                    if(~queueBaseUpdate.notNil, {
                        ~queueBaseUpdate.(freqBusKey, freq);
                    });

                    ~triggerMidiGate.(slot, amp);
                    eng[\lastNote] = note;
                }
                { stepType == 1 } {
                    // REST: silence (envelope decays naturally)
                    eng[\lastNote] = nil;
                }
                { stepType == 2 } {
                    // TIE: sustain current note, no new trigger
                };

                // Send step event to Python for playhead
                if(~pythonAddr.notNil, {
                    ~pythonAddr.sendMsg('/noise/step/event', slotIdx, pos);
                });

                // Advance position based on play mode
                eng[\position] = ~stepEngineNextPos.(eng, length);
            });
        });
    };

    // Compute next position based on SEQ play mode
    ~stepEngineNextPos = { |eng, length|
        var pos = eng[\position];
        var playMode = eng[\playMode];
        var next;

        case
        { playMode == 0 } {
            // FORWARD
            next = (pos + 1) % length;
        }
        { playMode == 1 } {
            // REVERSE
            next = (pos - 1 + length) % length;
        }
        { playMode == 2 } {
            // PINGPONG
            if(length <= 1, {
                next = 0;
            }, {
                if(eng[\ppFwd], {
                    next = pos + 1;
                    if(next >= (length - 1), {
                        next = length - 1;
                        eng[\ppFwd] = false;
                    });
                }, {
                    next = pos - 1;
                    if(next <= 0, {
                        next = 0;
                        eng[\ppFwd] = true;
                    });
                });
            });
        }
        { playMode == 3 } {
            // RANDOM
            next = length.rand;
        };

        next;
    };

    // === OSC HANDLERS ===

    // Clock tick handler — advance matching step engines
    // Listens on same /clock/tick path as clockTickForward (different OSCdef key)
    OSCdef(\stepEngineTick, { |msg|
        var fabricIdx = msg[3].asInteger;
        8.do { |i|
            if(~genStepMode[i] && (~stepEngine[i][\mode] > 0), {
                if(~stepEngine[i][\fabricIdx] == fabricIdx, {
                    ~stepEngineAdvance.(i);
                });
            });
        };
    }, '/clock/tick');

    // ARP: set expanded note list
    OSCdef(\arpSetNotes, { |msg|
        var slot0 = msg[1].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            var notes = msg[2..].collect(_.asInteger);
            ~stepEngine[slot0][\notes] = notes;
        });
    }, '/noise/arp/set_notes');

    // ARP/SEQ: set clock rate (fabric index)
    OSCdef(\stepSetRate, { |msg|
        var slot0 = msg[1].asInteger;
        var fabricIdx = msg[2].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            ~stepEngine[slot0][\fabricIdx] = fabricIdx;
            ~stepEngine[slot0][\position] = 0;
        });
    }, '/noise/step/set_rate');

    // SEQ: set bulk step data
    // Format: [slot_0indexed, length, type1, note1, vel1, type2, note2, vel2, ...]
    OSCdef(\seqSetBulk, { |msg|
        var slot0 = msg[1].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            var length = msg[2].asInteger;
            var data = msg[3..];
            var steps = [];
            (data.size / 3).asInteger.do { |i|
                steps = steps.add([
                    data[i*3].asInteger,      // type: 0=NOTE, 1=REST, 2=TIE
                    data[i*3+1].asInteger,    // note
                    data[i*3+2].asInteger     // velocity
                ]);
            };
            ~stepEngine[slot0][\steps] = steps;
            ~stepEngine[slot0][\length] = length;
        });
    }, '/noise/seq/set_bulk');

    // SEQ: set play mode
    OSCdef(\seqSetPlayMode, { |msg|
        var slot0 = msg[1].asInteger;
        var playMode = msg[2].asInteger;
        if(slot0 >= 0 && (slot0 < 8), {
            ~stepEngine[slot0][\playMode] = playMode;
            ~stepEngine[slot0][\ppFwd] = true;
        });
    }, '/noise/seq/set_play_mode');

    "  [x] Step Engine ready (8 slots)".postln;
};
