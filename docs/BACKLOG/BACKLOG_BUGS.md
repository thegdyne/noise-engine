
## OSC Shutdown Race Condition
**Priority:** Low — cosmetic, only on exit

When closing Noise Engine, OSC server thread continues receiving messages after Qt objects deleted.

**Error:** `RuntimeError: wrapped C/C++ object of type OSCBridge has been deleted`

**Fix:** Stop OSC server before destroying Qt objects, or add guard:
```python
def _handle_mod_bus_value(self, addr, *args):
    if self._shutdown:
        return
```

**File:** `src/audio/osc_bridge.py`
