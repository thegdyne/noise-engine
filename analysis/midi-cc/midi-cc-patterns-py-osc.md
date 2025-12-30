# PATTERNS.md - Python OSC Bridge

## Patterns to Preserve

### 1. Signal Declaration Pattern
```python
class OSCBridge(QObject):
    gate_triggered = pyqtSignal(int)  # slot_id
    levels_received = pyqtSignal(float, float, float, float)
```
- Declare as class attributes
- Document parameters in comment
- Use specific types (int, float, list)

### 2. Dispatcher Mapping Pattern
```python
from src.config import OSC_PATHS

dispatcher.map(OSC_PATHS['midi_gate'], self._handle_gate)
```
- Use config constants for paths
- Handler method named `_handle_<message_type>`

### 3. Handler Implementation Pattern
```python
def _handle_gate(self, address, *args):
    """Handle gate trigger from SC - emit signal for thread safety."""
    if self._deleted:
        return
    if len(args) > 0:
        slot_id = int(args[0])
        self.gate_triggered.emit(slot_id)
```
- Check `self._deleted` first (prevents emission after shutdown)
- Validate args length before access
- Cast to expected types
- Emit signal for thread-safe Qt integration

### 4. Shutdown Guard Pattern
```python
def _handle_comp_gr(self, address, *args):
    if self._shutdown:
        return
    if self._deleted:
        return
    # ... handle message
```
- Some handlers check both `_shutdown` and `_deleted`

## Patterns to Add

### New Signal for MIDI CC
```python
midi_cc_received = pyqtSignal(int, int, int)  # channel, cc, value
```

### New Dispatcher Mapping
```python
# In _start_server():
dispatcher.map('/noise/midi/cc', self._handle_midi_cc)
```

### New Handler
```python
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

## Config Integration
OSC_PATHS should be extended in `src/config/__init__.py`:
```python
OSC_PATHS = {
    # ... existing paths ...
    'midi_cc': '/noise/midi/cc',
}
```
