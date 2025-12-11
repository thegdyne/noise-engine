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
    
    // MIDI function references (nil until connected)
    ~midiNoteOnFunc = nil;
    ~midiNoteOffFunc = nil;
    ~midiCCFunc = nil;
    
    // Python address for sending gate notifications
    ~pythonAddr = NetAddr("127.0.0.1", 57121);
    
    // Defer MIDI client init to avoid blocking
    {
        try {
            MIDIClient.init;
            "  ✓ MIDI client initialized".postln;
        } { |error|
            "  ✗ MIDI client init failed (no MIDI devices?)".postln;
        };
    }.defer(0.5);
    
    "  ✓ MIDI setup complete (client init deferred)".postln;
};

// Connect MIDI and set up handlers
~connectMIDI = { |portIndex|
    // Clean up any existing handlers
    if(~midiNoteOnFunc.notNil, { ~midiNoteOnFunc.free; ~midiNoteOnFunc = nil; });
    if(~midiNoteOffFunc.notNil, { ~midiNoteOffFunc.free; ~midiNoteOffFunc = nil; });
    if(~midiCCFunc.notNil, { ~midiCCFunc.free; ~midiCCFunc = nil; });
    
    MIDIIn.disconnectAll;
    
    if(portIndex >= 0 && portIndex < MIDIClient.sources.size, {
        MIDIIn.connect(0, portIndex);
        ~midiConnected = true;
        ~midiPortIndex = portIndex;
        ("MIDI connected to: " ++ MIDIClient.sources[portIndex].device).postln;
        
        // Now set up handlers
        ~midiNoteOnFunc = MIDIFunc.noteOn({ |vel, note, chan, src|
            ~handleMidiNoteOn.(vel, note, chan);
        });
        
        ~midiNoteOffFunc = MIDIFunc.noteOff({ |vel, note, chan, src|
            // Future: handle note off for ADSR
        });
        
        ~midiCCFunc = MIDIFunc.cc({ |val, num, chan, src|
            // Future: map CCs to parameters
        });
        
        "  ✓ MIDI handlers active".postln;
    }, {
        ~midiConnected = false;
        ~midiPortIndex = -1;
        "MIDI disconnected".postln;
    });
};

// Handle MIDI note on
~handleMidiNoteOn = { |vel, note, chan|
    var midiChannel = chan + 1;  // Convert 0-15 to 1-16
    
    // Find generators listening on this channel
    8.do { |i|
        var slot = i + 1;
        var genChannel = ~genMidiChannel[i];
        var isMuted = ~genMuted[i];
        
        if(genChannel == midiChannel && isMuted.not, {
            var freq = note.midicps;
            var amp = vel / 127.0;
            
            // Set frequency from note
            if(~genParams[slot].notNil && ~genParams[slot][\frequency].notNil, {
                ~genParams[slot][\frequency].set(freq);
            });
            
            // Trigger envelope if generator exists
            if(~generators[slot].notNil, {
                // Send gate to Python for LED
                ~pythonAddr.sendMsg('/noise/midi/gate', slot);
                
                // Trigger the envelope
                ~triggerMidiGate.(slot, amp);
            });
        });
    };
};

// Trigger MIDI gate for a generator
~triggerMidiGate = { |slot, velocity=1.0|
    // Create a one-shot trigger synth that fires immediately
    var rateIndex = 6;  // CLK rate
    
    if(~clockGroup.notNil && ~clockTrigBus.notNil, {
        Synth(\midiTrigger, [
            \trigBus, ~clockTrigBus.index,
            \rateIndex, rateIndex,
            \amp, velocity
        ], ~clockGroup);
    });
};

// One-shot trigger synth for MIDI notes
SynthDef(\midiTrigger, { |trigBus=0, rateIndex=6, amp=1|
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
        ~connectMIDI.(portIndex);
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
        });
    }, '/noise/gen/mute');
    
    "  ✓ MIDI OSC handlers ready".postln;
};
