/*
MIDI Handler
Handles MIDI input routing to generators

Features:
- Connect to MIDI device by port index
- Route note on/off to generators by MIDI channel
- Send gate triggers back to Python for LED flashing
- Support per-generator mute
- MIDI retrig mode for struck/plucked generators (continuous triggers while key held)

MIDI Channel mapping:
- Each generator has a midiChannel (0=OFF, 1-16=channel)
- Note on triggers envelope gate
- Note pitch sets frequency
- Velocity can modulate amplitude

OSC messages from Python:
- /noise/midi/device [portIndex] - Connect to MIDI port (-1 = disconnect)
- /noise/gen/midiChannel [slot, channel] - Set generator's MIDI channel
- /noise/gen/mute [slot, muted] - Set generator mute state
- /noise/gen/midiRetrig [slot, enabled] - Set MIDI retrig mode for generator

OSC messages to Python:
- /noise/midi/gate [slot] - Gate triggered (for LED flash)
- /noise/midi/cc [channel, cc, value] - CC received (for Python mapping)
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
    ~genMidiRetrig = Array.fill(8, { false });  // true = continuous retrig while key held
    ~genRetrigSynths = Array.fill(8, { nil });  // Active retrig synths per slot

    // Per-generator transpose (semitones, -24 to +24)
    ~genTranspose = Array.fill(8, { 0 });

    // MIDI connection state
    ~midiConnected = false;
    ~midiPortIndex = -1;
    
    // MIDI function references (nil until connected)
    ~midiNoteOnFunc = nil;
    ~midiNoteOffFunc = nil;
    ~midiCCFunc = nil;
    
    // ~pythonAddr is set in config.scd
    
    // Defer MIDI client init to avoid blocking
    {
        try {
            MIDIClient.init;
            MIDIIn.disconnectAll;  // Disconnect again after init
            "  [x] MIDI client initialized (all inputs disconnected)".postln;
        } { |error|
            "  [ ] MIDI client init failed".postln;
        };
    }.defer(0.5);
    
    "  [x] MIDI setup complete".postln;
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
            ~handleMidiNoteOn.(vel, note, chan);
        });
        
        ~midiNoteOffFunc = MIDIFunc.noteOff({ |vel, note, chan, src|
            ~handleMidiNoteOff.(vel, note, chan);
        });
        
        ~midiCCFunc = MIDIFunc.cc({ |val, num, chan, src|
            var midiChannel = chan + 1;
            ("CC: ch=" ++ midiChannel ++ " cc=" ++ num ++ " val=" ++ val).postln;  // Debug
            if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/midi/cc', midiChannel, num, val); };
        });
        
        "  [x] MIDI handlers active".postln;
    }, {
        ~midiConnected = false;
        ~midiPortIndex = -1;
        ("MIDI disconnected (port " ++ portIndex ++ ")").postln;
    });
};

// Connect to ALL MIDI devices (for CC control - per MIDI CC spec v1)
~connectAllMIDI = {
    // Clean up any existing handlers
    if(~midiNoteOnFunc.notNil, { ~midiNoteOnFunc.free; ~midiNoteOnFunc = nil; });
    if(~midiNoteOffFunc.notNil, { ~midiNoteOffFunc.free; ~midiNoteOffFunc = nil; });
    if(~midiCCFunc.notNil, { ~midiCCFunc.free; ~midiCCFunc = nil; });

    MIDIIn.connectAll;
    ~midiConnected = true;
    ~midiPortIndex = -1;  // -1 indicates "all devices"
    "MIDI: Listening to ALL devices".postln;

    // Set up handlers
    ~midiNoteOnFunc = MIDIFunc.noteOn({ |vel, note, chan, src|
        ~handleMidiNoteOn.(vel, note, chan);
    });

    ~midiNoteOffFunc = MIDIFunc.noteOff({ |vel, note, chan, src|
        ~handleMidiNoteOff.(vel, note, chan);
    });

    ~midiCCFunc = MIDIFunc.cc({ |val, num, chan, src|
        var midiChannel = chan + 1;  // Convert 0-15 to 1-16
        if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/midi/cc', midiChannel, num, val); };
    });

    "  [x] MIDI handlers active (all devices)".postln;
};

// Handle MIDI note on
~handleMidiNoteOn = { |vel, note, chan|
    var midiChannel = chan + 1;  // Convert 0-15 to 1-16
    
    // Find generators listening on this channel
    8.do { |i|
        var slot = i + 1;
        var genChannel = ~genMidiChannel[i];
        var isMuted = ~genMuted[i];
        var needsRetrig = ~genMidiRetrig[i];
        var transpose = ~genTranspose[i];
        var freq = (note + transpose).midicps;
        var amp = vel / 127.0;
        var freqBusKey = ("gen_" ++ slot ++ "_freq").asSymbol;

        if(genChannel == midiChannel && isMuted.not, {
            // Set frequency IMMEDIATELY on the bus so the trigger fires at the correct pitch
            if(~busRegistry.notNil && ~busRegistry[freqBusKey].notNil, {
                ~busRegistry[freqBusKey].set(freq);
            });
            // Also queue for the modulation system (apply tick recalculates with mod offsets)
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(freqBusKey, freq);
            });

            // Trigger envelope if generator exists
            if(~generators[slot].notNil, {
                // Send gate to Python for LED
                if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/midi/gate', slot); };
                
                if(needsRetrig, {
                    // Continuous retrig mode - start fast triggering synth
                    ~startMidiRetrig.(slot, amp);
                }, {
                    // Normal mode - single trigger
                    ~triggerMidiGate.(slot, amp);
                });
            });
        });
    };
};

// Handle MIDI note off
~handleMidiNoteOff = { |vel, note, chan|
    var midiChannel = chan + 1;
    
    // Stop retrig synths for generators on this channel
    8.do { |i|
        var slot = i + 1;
        var genChannel = ~genMidiChannel[i];
        var needsRetrig = ~genMidiRetrig[i];
        
        if(genChannel == midiChannel && needsRetrig, {
            ~stopMidiRetrig.(slot);
        });
    };
};

// Start continuous MIDI retriggering for a slot
~startMidiRetrig = { |slot, velocity=1.0|
    // Stop any existing retrig synth for this slot
    ~stopMidiRetrig.(slot);
    
    if(~clockGroup.notNil && ~midiTrigBus.notNil, {
        // Create a synth that sends continuous triggers at ~30Hz while running
        ~genRetrigSynths[slot - 1] = Synth(\midiRetrigContinuous, [
            \trigBus, ~midiTrigBus.index + slot - 1,
            \rate, 30,  // 30Hz retrigger rate
            \amp, velocity
        ], ~clockGroup, \addToTail);
    });
};

// Stop continuous MIDI retriggering for a slot
~stopMidiRetrig = { |slot|
    var synth = ~genRetrigSynths[slot - 1];
    if(synth.notNil, {
        synth.free;
        ~genRetrigSynths[slot - 1] = nil;
    });
};

// Trigger MIDI gate for a generator (single pulse)
~triggerMidiGate = { |slot, velocity=1.0|
    if(~clockGroup.notNil && ~midiTrigBus.notNil, {
        Synth(\midiTrigger, [
            \trigBus, ~midiTrigBus.index + slot - 1,
            \amp, velocity
        ], ~clockGroup, \addToTail);
    });
};

// One-shot trigger synth for MIDI notes
// Writes a trigger pulse to a single audio bus channel
// Uses doneAction:2 to free itself after the pulse completes
// ReplaceOut prevents bus accumulation when triggers overlap
SynthDef(\midiTrigger, { |trigBus=0, amp=1, dur=0.01|
    var sig = EnvGen.ar(Env.perc(0.0005, dur, 1, -4), doneAction: 2) * amp;
    ReplaceOut.ar(trigBus, sig);
}).add;

// Continuous trigger synth for MIDI retrig mode
// Sends triggers at specified rate while running
SynthDef(\midiRetrigContinuous, { |trigBus=0, rate=30, amp=1|
    var trig = Impulse.ar(rate);
    ReplaceOut.ar(trigBus, trig * amp);
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
    
    // Set generator MIDI retrig mode
    OSCdef(\genMidiRetrig, { |msg|
        var slot = msg[1].asInteger;
        var enabled = msg[2].asInteger > 0;
        
        if(slot >= 1 && slot <= 8, {
            ~genMidiRetrig[slot - 1] = enabled;
            ("Gen " ++ slot ++ " MIDI retrig: " ++ enabled).postln;
        });
    }, '/noise/gen/midiRetrig');
    
    "  [x] MIDI OSC handlers ready".postln;
};
