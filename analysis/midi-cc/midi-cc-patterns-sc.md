# PATTERNS.md - SC MIDI Handler

## Patterns to Preserve

### 1. MIDIFunc Handler Pattern
```supercollider
~midiNoteOnFunc = MIDIFunc.noteOn({ |vel, note, chan, src|
    ~handleMidiNoteOn.(vel, note, chan);
});
```
- Store function reference in global var for cleanup
- Delegate to separate handler function

### 2. Channel Conversion (CRITICAL)
```supercollider
var midiChannel = chan + 1;  // Convert 0-15 to 1-16
```
- SC receives 0-15 from wire
- Convert to 1-16 before any public use (OSC, logging)
- Single conversion point at SC boundary

### 3. OSC Send to Python
```supercollider
~pythonAddr.sendMsg('/noise/midi/gate', slot);
```
- Use `~pythonAddr` (set in config.scd)
- Path format: `/noise/midi/<message_type>`

### 4. Cleanup Pattern
```supercollider
if(~midiCCFunc.notNil, { ~midiCCFunc.free; ~midiCCFunc = nil; });
```
- Check notNil before free
- Set to nil after free

## Patterns to Change

### Device Handling (per spec)
**Current**: Port-specific connection
```supercollider
MIDIIn.connect(0, portIndex);
```

**New**: Listen to all devices
```supercollider
MIDIIn.connectAll;
```

### CC Handler (currently stub)
**Current**:
```supercollider
~midiCCFunc = MIDIFunc.cc({ |val, num, chan, src|
    // Future: map CCs to parameters
});
```

**New**:
```supercollider
~midiCCFunc = MIDIFunc.cc({ |val, num, chan, src|
    var midiChannel = chan + 1;  // Convert 0-15 to 1-16
    ~pythonAddr.sendMsg('/noise/midi/cc', midiChannel, num, val);
});
```

## Key Variables
- `~pythonAddr` - NetAddr for Python OSC
- `~midiCCFunc` - CC handler reference
- `~midiConnected` - Connection state
