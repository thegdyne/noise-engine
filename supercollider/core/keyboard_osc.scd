/*
Keyboard Overlay OSC Handlers
Handles note-on/off from Python keyboard overlay

OSC messages from Python:
- /noise/slot/{slot}/midi/note_on [note, velocity] - Trigger note
- /noise/slot/{slot}/midi/note_off [note] - Release note  
- /noise/slot/{slot}/midi/all_notes_off - Release all notes (panic)

Where slot is 0-7 (0-indexed)

These bypass the MIDI channel filtering and directly trigger slots.
Useful for the QWERTY keyboard overlay and programmatic note triggering.
*/

~setupKeyboardOSC = {
    "Setting up Keyboard Overlay OSC handlers...".postln;
    
    // Track active notes per slot for note-off matching
    ~keyboardActiveNotes = Array.fill(8, { Dictionary.new });
    
    // Note on - direct slot triggering
    8.do { |i|
        var path = "/noise/slot/" ++ i ++ "/midi/note_on";
        
        OSCdef(("keyboardNoteOn" ++ i).asSymbol, { |msg|
            var slot = i + 1;  // Convert 0-indexed to 1-indexed
            var note = msg[1].asInteger;
            var velocity = msg[2].asInteger;
            var transpose = ~genTranspose[i];
            var freq = (note + transpose).midicps;
            var amp = velocity / 127.0;
            var isMuted = ~genMuted[i];
            var needsRetrig = ~genMidiRetrig[i];
            var freqBusKey = ("gen_" ++ slot ++ "_freq").asSymbol;

            if(isMuted.not, {
                // Track this note
                ~keyboardActiveNotes[i][note] = true;

                // Set frequency IMMEDIATELY on the bus so the trigger fires at the correct pitch.
                // queueBaseUpdate alone has up to 5ms latency (200Hz apply tick),
                // which causes the envelope to start at the old note's frequency.
                if(~busRegistry.notNil && ~busRegistry[freqBusKey].notNil, {
                    ~busRegistry[freqBusKey].set(freq);
                });
                // Also queue for the modulation system (apply tick recalculates with mod offsets)
                if(~queueBaseUpdate.notNil, {
                    ~queueBaseUpdate.(freqBusKey, freq);
                });

                // Trigger envelope if generator exists
                if(~generators[slot].notNil, {
                    if(needsRetrig, {
                        // Continuous retrig mode
                        ~startMidiRetrig.(slot, amp);
                    }, {
                        // Normal mode - single trigger
                        ~triggerMidiGate.(slot, amp);
                    });

                    // Send gate to Python for LED (after audio trigger)
                    if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/midi/gate', slot); };
                });
            });
        }, path);
    };
    
    // Note off - stop retriggering
    8.do { |i|
        var path = "/noise/slot/" ++ i ++ "/midi/note_off";
        
        OSCdef(("keyboardNoteOff" ++ i).asSymbol, { |msg|
            var slot = i + 1;
            var note = msg[1].asInteger;
            var needsRetrig = ~genMidiRetrig[i];
            
            // Remove from active notes
            ~keyboardActiveNotes[i].removeAt(note);
            
            // Stop retrig if no more notes held for this slot
            if(needsRetrig && ~keyboardActiveNotes[i].isEmpty, {
                ~stopMidiRetrig.(slot);
            });
        }, path);
    };
    
    // All notes off (panic) - clear all active notes and stop retrigs
    8.do { |i|
        var path = "/noise/slot/" ++ i ++ "/midi/all_notes_off";
        
        OSCdef(("keyboardAllOff" ++ i).asSymbol, { |msg|
            var slot = i + 1;
            
            // Clear all tracked notes
            ~keyboardActiveNotes[i].clear;
            
            // Stop any retrig synth
            ~stopMidiRetrig.(slot);
        }, path);
    };
    
    "  [x] Keyboard Overlay OSC handlers ready".postln;
};

// Call setup (safe to call multiple times - OSCdef replaces existing)
~setupKeyboardOSC.();
