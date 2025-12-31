# MIDI CC Control - Phase 1 Implementation

## Overview

Phase 1 establishes the core data flow: CC from MIDI device → SC → Python → mapped controls.

## Contracts Created

| Contract | Purpose | Status |
|----------|---------|--------|
| `midi-cc-sc-forwarding.yaml` | SC receives CC, forwards via OSC | draft |
| `midi-cc-py-receiver.yaml` | Python receives OSC, emits Qt signal | draft |
| `midi-cc-mapping-manager.yaml` | Stores CC→control mappings | draft |

## Implementation Order

### Step 1: SC CC Forwarding

**File**: `supercollider/core/midi_handler.scd`

**Changes**:
1. Replace `~connectMIDI` to use `MIDIIn.connectAll` (listen to all devices)
2. Fill in `~midiCCFunc` stub to forward CCs to Python

**Code to add/modify**:
```supercollider
// In ~connectMIDI or new ~connectAllMIDI:
MIDIIn.connectAll;

// Fill in existing stub:
~midiCCFunc = MIDIFunc.cc({ |val, num, chan, src|
    var midiChannel = chan + 1;  // Convert 0-15 to 1-16
    ~pythonAddr.sendMsg('/noise/midi/cc', midiChannel, num, val);
});
```

### Step 2: Python OSC Receiver

**File**: `src/audio/osc_bridge.py`

**Changes**:
1. Add `midi_cc_received` signal
2. Add dispatcher mapping
3. Add handler method

**Code to add**:
```python
# Signal (class attribute):
midi_cc_received = pyqtSignal(int, int, int)  # channel, cc, value

# In _start_server():
dispatcher.map('/noise/midi/cc', self._handle_midi_cc)

# Handler method:
def _handle_midi_cc(self, address, *args):
    """Handle MIDI CC from SC."""
    if self._deleted:
        return
    if len(args) >= 3:
        channel = int(args[0])  # 1-16
        cc = int(args[1])       # 0-127
        value = int(args[2])    # 0-127
        self.midi_cc_received.emit(channel, cc, value)
```

### Step 3: Mapping Manager

**New file**: `src/midi/cc_mapping_manager.py`

**Creates**: New component to store mappings and track pickup state.

```python
from PyQt5.QtCore import QObject

class MidiCCMappingManager(QObject):
    """Manages MIDI CC to UI control mappings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Mapping: (channel, cc) -> list of controls
        self._mappings = {}
        # Pickup state: (channel, cc) -> {control: caught}
        self._caught = {}
    
    def add_mapping(self, channel, cc, control):
        """Add mapping from (channel, cc) to control."""
        key = (channel, cc)
        if key not in self._mappings:
            self._mappings[key] = []
        if control not in self._mappings[key]:
            self._mappings[key].append(control)
        # Initialize caught state
        if key not in self._caught:
            self._caught[key] = {}
        self._caught[key][control] = False
    
    def get_controls(self, channel, cc):
        """Get list of controls mapped to (channel, cc)."""
        return self._mappings.get((channel, cc), [])
    
    def remove_mapping(self, control):
        """Remove all mappings for a control."""
        for key in list(self._mappings.keys()):
            if control in self._mappings[key]:
                self._mappings[key].remove(control)
                if key in self._caught and control in self._caught[key]:
                    del self._caught[key][control]
            if not self._mappings[key]:
                del self._mappings[key]
    
    def clear_all(self):
        """Clear all mappings."""
        self._mappings.clear()
        self._caught.clear()
    
    def is_caught(self, channel, cc, control):
        """Check if pickup is caught for this mapping."""
        return self._caught.get((channel, cc), {}).get(control, False)
    
    def set_caught(self, channel, cc, control, caught):
        """Set caught state for this mapping."""
        key = (channel, cc)
        if key in self._caught:
            self._caught[key][control] = caught
    
    def reset_all_pickup(self):
        """Reset all caught states (e.g., on preset load)."""
        for key in self._caught:
            for control in self._caught[key]:
                self._caught[key][control] = False
```

## Testing Workflow

After implementation:

```bash
cd ~/repos/noise-engine

# G0.3: Verify paths resolve
cdd paths contracts/midi-cc-sc-forwarding.yaml
cdd paths contracts/midi-cc-py-receiver.yaml  
cdd paths contracts/midi-cc-mapping-manager.yaml

# G1: Lint contracts
cdd lint contracts/midi-cc-sc-forwarding.yaml
cdd lint contracts/midi-cc-py-receiver.yaml
cdd lint contracts/midi-cc-mapping-manager.yaml

# G2: Run tests
cdd test contracts/midi-cc-sc-forwarding.yaml
cdd test contracts/midi-cc-py-receiver.yaml
cdd test contracts/midi-cc-mapping-manager.yaml
```

## Next Phases

- **Phase 2**: MIDI Learn (armed state, first-CC capture)
- **Phase 3**: Pickup Mode (soft takeover with ghost indicator)
- **Phase 4**: Flood Control (~60Hz coalescing)
- **Phase 5**: UI Chrome (status indicator, context menus)
- **Phase 6**: Persistence (presets, session restore)
