/*
MIDI Handler
Handles MIDI input routing to generators

Features:
- Connect to MIDI device by port index
- Route note on/off to generators by MIDI channel
- Send gate triggers back to Python for LED flashing
- Support per-generator mute

MIDI Channel mapping:
- Each generator has a midiChannel (0=OFF, 1-16=channel)
- Note on triggers envelope gate
- Note pitch sets frequency
- Velocity can modulate amplitude

OSC messages from Python:
- /noise/midi/device [portIndex] - Connect to MIDI port (-1 = disconnect)
- /noise/gen/midiChannel [slot, channel] - Set generator's MIDI channel
- /noise/gen/mute [slot, muted] - Set generator mute state

OSC messages to Python:
- /noise/midi/gate [slot] - Gate triggered (for LED flash)
*/

~setupMIDI = {
    "Setting up MIDI...".postln;
    
    // Per-generator MIDI settings
    ~genMidiChannel = Array.fill(8, { 0 });  // 0 = OFF, 1-16 = channel
    ~genMuted = Array.fill(8, { false });
    
    // MIDI connection state
    ~midiConnected = false;
    ~midiPortIndex = -1;
    
    // Python address for sending gate notifications
    ~pythonAddr = NetAddr("127.0.0.1", 57121);
    
    // Initialize MIDI client
    MIDIClient.init;
    
    // Note On handler
    ~midiNoteOnFunc = MIDIFunc.noteOn({ |vel, note, chan, src|
        var midiChannel = chan + 1;  // Convert 0-15 to 1-16
        
        // Find generators listening on this channel
        8.do { |i|
            var slot = i + 1;
            var genChannel = ~genMidiChannel[i];
            
            if(genChannel == midiChannel && ~genMuted[i].not, {
                var freq = note.midicps;
                var amp = vel / 127.0;
                
                // Set frequency from note
                ~genParams[slot][\frequency].set(freq);
                
                // Trigger envelope if ENV is enabled
                // The envelope is triggered by writing to a trigger bus
                // For now, we'll create a trigger synth
                if(~generators[slot].notNil, {
                    // Send gate to Python for LED
                    ~pythonAddr.sendMsg('/noise/midi/gate', slot);
                    
                    // If envelope is enabled, trigger it
                    // This is handled by the clock trigger bus normally,
                    // but for MIDI we need a one-shot trigger
                    ~triggerMidiGate.(slot, amp);
                });
            });
        };
    });
    
    // Note Off handler (for future ADSR support)
    ~midiNoteOffFunc = MIDIFunc.noteOff({ |vel, note, chan, src|
        // For now, we use perc envelopes so note off isn't needed
        // Future: implement ADSR with proper gate off
    });
    
    // CC handler (for future parameter control)
    ~midiCCFunc = MIDIFunc.cc({ |val, num, chan, src|
        // Future: map CCs to generator parameters
        // Example: CC1 (mod wheel) could control filter cutoff
    });
    
    "  ✓ MIDI handlers ready".postln;
};

// Trigger MIDI gate for a generator
~triggerMidiGate = { |slot, velocity=1.0|
    // Create a one-shot trigger synth that fires immediately
    // This writes to the clock trigger bus at the generator's rate index
    // so the existing envelope system picks it up
    
    var rateIndex = ~genParams[slot][\clockRate].getSynchronous ? 6;
    
    // Simple approach: just retrigger the synth's envelope
    // by sending a control message
    if(~generators[slot].notNil, {
        // The generators read from clockTrigBus, but for MIDI we need
        // to inject a trigger. We'll use a dedicated trigger synth.
        Synth(\midiTrigger, [
            \trigBus, ~clockTrigBus,
            \rateIndex, rateIndex,
            \amp, velocity
        ], ~clockGroup);
    });
};

// One-shot trigger synth for MIDI notes
SynthDef(\midiTrigger, { |trigBus, rateIndex=6, amp=1|
    var trig = Impulse.ar(0);  // Single trigger at start
    var sig = Array.fill(13, { |i| 
        if(i == rateIndex, { trig * amp }, { DC.ar(0) })
    });
    Out.ar(trigBus, sig);
    FreeSelf.kr(Impulse.kr(0));  // Free after one control period
}).add;

// OSC handlers for MIDI
~setupMIDIOSC = {
    "Setting up MIDI OSC handlers...".postln;
    
    // Connect to MIDI device
    OSCdef(\midiDevice, { |msg|
        var portIndex = msg[1].asInteger;
        
        if(portIndex < 0, {
            // Disconnect
            MIDIIn.disconnectAll;
            ~midiConnected = false;
            ~midiPortIndex = -1;
            "MIDI disconnected".postln;
        }, {
            // Connect to specified port
            if(portIndex < MIDIClient.sources.size, {
                MIDIIn.disconnectAll;
                MIDIIn.connect(0, portIndex);
                ~midiConnected = true;
                ~midiPortIndex = portIndex;
                ("MIDI connected to: " ++ MIDIClient.sources[portIndex].device).postln;
            }, {
                ("MIDI port index out of range: " ++ portIndex).postln;
            });
        });
    }, '/noise/midi/device');
    
    // Set generator MIDI channel
    OSCdef(\genMidiChannel, { |msg|
        var slot = msg[1].asInteger;
        var channel = msg[2].asInteger;  // 0=OFF, 1-16=channel
        
        if(slot >= 1 && slot <= 8, {
            ~genMidiChannel[slot - 1] = channel;
            ("Gen " ++ slot ++ " MIDI channel: " ++ if(channel == 0, "OFF", channel)).postln;
        });
    }, '/noise/gen/midiChannel');
    
    // Set generator mute
    OSCdef(\genMute, { |msg|
        var slot = msg[1].asInteger;
        var muted = msg[2].asInteger > 0;
        
        if(slot >= 1 && slot <= 8, {
            ~genMuted[slot - 1] = muted;
            ("Gen " ++ slot ++ " mute: " ++ muted).postln;
            
            // Also mute/unmute the synth audio
            if(~generators[slot].notNil, {
                // Could set amplitude to 0, or use a gate
                // For now just track the state
            });
        });
    }, '/noise/gen/mute');
    
    "  ✓ MIDI OSC handlers ready".postln;
};
