# Fader Value Popups

**Status:** Planned  
**Created:** December 2025

## Overview

Display real-time value feedback during fader drag operations. Shows the actual mapped value (dB, Hz, %, etc.) near the fader handle while dragging.

## Current State

- **Generator params (MiniSlider):** Have popups via `set_param_config()` system
- **All other faders:** No popup feedback

Faders missing popups:
- Mixer channel volume faders
- Mixer pan sliders
- Master volume fader
- Master EQ sliders (LO, MID, HI)
- Master limiter ceiling
- Master compressor threshold/makeup
- Effect amount sliders
- LFO rate sliders

## Design Principle

**One calculation, one place.**

Each fader's value is already being calculated in its `_on_*_changed` handler before sending to SuperCollider via OSC. We don't duplicate that calculation. The handler that computes the value also provides it to the popup.

## Solution

### Widget API

Add a simple method to `DragSlider`:

```python
def show_drag_value(self, text):
    """Display a value in popup during drag. Called by handler."""
    if self.dragging and self._popup:
        handle_pos = self._get_handle_global_pos()
        self._popup.show_value(text, handle_pos)
```

The popup is created lazily on first use if it doesn't exist.

### Handler Pattern

Each `_on_*_changed` handler already calculates the real value. Add one line to display it:

```python
# In master_section.py
def _on_eq_lo_changed(self, value):
    db = (value - 120) / 10  # Already doing this calculation
    self.osc.send(OSC_PATHS['master_eq_lo'], db)
    self.eq_lo_slider.show_drag_value(f"{db:+.1f}dB")  # Add this

# In mixer_panel.py  
def on_fader_changed(self, value):
    volume = value / 1000.0  # Already doing this
    self.volume_changed.emit(self.channel_id, volume)
    db = 20 * math.log10(volume) if volume > 0 else -60
    self.fader.show_drag_value(f"{db:.1f}dB")  # Add this
```

### Value Flow

```
User drags fader
       │
       ▼
valueChanged signal fires
       │
       ▼
Handler receives raw slider value (0-1000)
       │
       ▼
Handler calculates real value ─────────────┐
(e.g. dB, Hz, %)                           │
       │                                   │
       ▼                                   ▼
Handler sends OSC              Handler calls show_drag_value()
to SuperCollider               with formatted string
                                          │
                                          ▼
                               Popup displays near handle
                                          │
                                          ▼
                               mouseReleaseEvent hides popup
```

## Format Strings by Context

| Fader | Calculation | Format |
|-------|-------------|--------|
| Volume (mixer/master) | `20 * log10(value)` | `f"{db:.1f}dB"` |
| EQ gain | `(value - 120) / 10` | `f"{db:+.1f}dB"` |
| Pan | `value / 100` | `"L50"` / `"C"` / `"R50"` |
| Limiter ceiling | `(value - 600) / 100` | `f"{db:.1f}dB"` |
| Comp threshold | `(value - 200) / 10` | `f"{db:+.1f}dB"` |
| Comp makeup | `value / 10` | `f"+{db:.1f}dB"` |
| Effect amount | `value / 10` | `f"{pct:.0f}%"` |
| LFO rate | Hz calculation | `f"{hz:.2f}Hz"` |

## Why Not Centralise Formatting?

Considered adding a central format lookup:
```python
self.fader.show_drag_value(db, 'db')  # Widget looks up format
```

Rejected because:
1. Formatting is trivial (just f-strings)
2. Handler already knows the context and units
3. Adds indirection without meaningful benefit
4. Different faders may need slightly different formats even within same "type"

## Why Not Use param_config?

The `set_param_config()` system used by MiniSlider:
1. Requires full param definition (min, max, curve, unit, invert)
2. Does its own value mapping in `get_mapped_value()`
3. Would duplicate the calculation already in handlers

The handler-driven approach reuses the existing calculation.

## Files to Modify

1. **src/gui/widgets.py**
   - Add `show_drag_value(text)` method to `DragSlider`
   - Ensure popup created lazily if needed

2. **src/gui/mixer_panel.py**
   - `ChannelStrip.on_fader_changed()` - volume popup
   - `ChannelStrip.on_pan_changed()` - pan popup

3. **src/gui/master_section.py**
   - `_on_fader_changed()` - master volume
   - `_on_eq_lo/mid/hi_changed()` - EQ gains
   - `_on_ceiling_changed()` - limiter ceiling
   - `_on_comp_threshold_changed()` - comp threshold
   - `_on_comp_makeup_changed()` - comp makeup

4. **src/gui/effects_chain.py**
   - Effect amount handler

5. **src/gui/modulation_sources.py**
   - LFO rate handler

## Testing

Manual verification:
1. Drag each fader type
2. Confirm popup appears near handle
3. Confirm value updates during drag
4. Confirm popup hides on release
5. Confirm displayed value matches what's sent to SC
