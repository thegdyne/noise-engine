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
    
    // Clear any existing named MIDI responders from previous runs
    MIDIdef.freeAll;
    
    // Disconnect any existing MIDI connections
    try { MIDIIn.disconnectAll } { };
    
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
            MIDIIn.disconnectAll;  // Disconnect again after init
            "  ✓ MIDI client initialized (all inputs disconnected)".postln;
        } { |error|
            "  ✗ MIDI client init failed".postln;
        };
    }.defer(0.5);
    
    "  ✓ MIDI setup complete".postln;
};

// Connect MIDI and set up handlers
~connectMIDI = { |portIndex|
    // Clean up any existing handlers
    if(~midiNoteOnFunc.notNil, { ~midiNoteOnFunc.free; ~midiNoteOnFunc = nil; });
    if(~midiNoteOffFunc.notNil, { ~midiNoteOffFunc.free; ~midiNoteOffFunc = nil; });
    if(~midiCCFunc.notNil, { ~midiCCFunc.free; ~midiCCFunc = nil; });
    
    MIDIIn.disconnectAll;
    
    if(portIndex >= 0 && portIndex < MIDIClient.sources.size, {
        var src = MIDIClient.sources[portIndex];
        ("Connecting to MIDI port " ++ portIndex ++ ": " ++ src.device).postln;
        
        MIDIIn.connect(0, portIndex);
        ~midiConnected = true;
        ~midiPortIndex = portIndex;
        ("MIDI connected to: " ++ src.device).postln;
        
        // Now set up handlers
        ~midiNoteOnFunc = MIDIFunc.noteOn({ |vel, note, chan, src|
            ("MIDIFunc.noteOn triggered!").postln;
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
        ("MIDI disconnected (port " ++ portIndex ++ ")").postln;
    });
};

// Handle MIDI note on
~handleMidiNoteOn = { |vel, note, chan|
    var midiChannel = chan + 1;  // Convert 0-15 to 1-16
    
    ("MIDI Note: " ++ note ++ " vel: " ++ vel ++ " chan: " ++ midiChannel).postln;
    
    // Find generators listening on this channel
    8.do { |i|
        var slot = i + 1;
        var genChannel = ~genMidiChannel[i];
        var isMuted = ~genMuted[i];
        
        if(genChannel == midiChannel && isMuted.not, {
            var freq = note.midicps;
            var amp = vel / 127.0;
            
            ("  -> Routing to Gen " ++ slot ++ " freq: " ++ freq).postln;
            
            // Set frequency from note
            if(~genParams[slot].notNil && ~genParams[slot][\frequency].notNil, {
                ~genParams[slot][\frequency].set(freq);
            });
            
            // Trigger envelope if generator exists
            if(~generators[slot].notNil, {
                ("  -> Triggering gate for Gen " ++ slot).postln;
                // Send gate to Python for LED
                ~pythonAddr.sendMsg('/noise/midi/gate', slot);
                
                // Trigger the envelope
                ~triggerMidiGate.(slot, amp);
            }, {
                ("  -> Gen " ++ slot ++ " not running").postln;
            });
        });
    };
};

// Trigger MIDI gate for a generator
~triggerMidiGate = { |slot, velocity=1.0|
    if(~clockGroup.notNil && ~midiTrigBus.notNil, {
        ("  -> Creating MIDI trigger for slot " ++ slot).postln;
        Synth(\midiTrigger, [
            \trigBus, ~midiTrigBus.index,
            \slotIndex, slot - 1,  // 0-indexed
            \amp, velocity
        ], ~clockGroup, \addToTail);
    });
};

// One-shot trigger synth for MIDI notes
// Writes a trigger pulse to a specific slot channel in the MIDI trigger bus
SynthDef(\midiTrigger, { |trigBus=0, slotIndex=0, amp=1|
    var trig = Trig1.ar(DC.ar(1), 0.001);  // 1ms trigger pulse
    var sig = Array.fill(8, { |i| if(i == slotIndex, { trig * amp }, { DC.ar(0) }) });
    Out.ar(trigBus, sig);
    FreeSelf.kr(TDelay.kr(Impulse.kr(0), 0.01));
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
