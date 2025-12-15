# Channel EQ Specification

**Status:** Planned  
**Created:** December 2025

---

## Overview

Add a simple 3-band EQ to each channel strip. Goal is quick tone shaping, not surgical precision - think DJ mixer or Mackie 1202 style.

---

## Design Goals

1. **Compact** - Must fit in existing channel strip without bloating UI
2. **Quick** - Immediately useful, not menu-diving
3. **Musical** - Fixed frequencies, wide Q, full kill capability
4. **Consistent** - Same EQ type as master section (DJ isolator style)

---

## UI Options

### Option A: Mini Knobs (Recommended)
Three tiny knobs stacked vertically above the fader:

```
┌───────┐
│  FM   │  ← Generator name
├───────┤
│  H●   │  ← HI knob (tiny, ~20px)
│  M●   │  ← MID knob  
│  L●   │  ← LO knob
├───────┤
│   █   │
│   █   │  ← Fader
│   █   │
│  ═●═  │  ← Pan
│ [M][S]│  ← Mute/Solo
│  [0]  │  ← Gain
└───────┘
```

- Knobs: 18-20px diameter
- Range: -∞ to +6dB (full cut to slight boost)
- Double-click: reset to 0dB
- No labels (tooltip shows "HI", "MID", "LO")

### Option B: Single EQ Button → Popup
One "EQ" button that opens a small popup with three sliders:

```
┌───────┐
│  FM   │
│ [EQ]  │  ← Click to open popup
├───────┤    ┌─────────────┐
│   █   │    │ LO  MID  HI │
│   █   │    │  █   █   █  │
│   █   │    │ [×] Close   │
│  ═●═  │    └─────────────┘
│ [M][S]│
└───────┘
```

- Saves vertical space
- Extra click to access
- Popup could get annoying

### Option C: Expandable Section
Click channel label to expand/collapse EQ section:

```
Collapsed:           Expanded:
┌───────┐            ┌───────┐
│ ▶ FM  │            │ ▼ FM  │
├───────┤            │  H ●  │
│   █   │            │  M ●  │
                     │  L ●  │
                     ├───────┤
                     │   █   │
```

- Clean when not needed
- Requires extra click
- Variable height channels look messy

**Recommendation: Option A** - Always visible, no clicks, consistent with "everything visible" philosophy.

---

## Frequencies

Match master EQ crossover points for consistency:

| Band | Center/Crossover | Q | Character |
|------|------------------|---|-----------|
| LO   | < 250 Hz | Wide | Sub/bass body |
| MID  | 250 Hz - 2.5 kHz | Wide | Presence/body |
| HI   | > 2.5 kHz | Wide | Air/brightness |

---

## Range

| Value | dB | Behaviour |
|-------|-----|-----------|
| 0% | -∞ | Full kill (band muted) |
| 50% | 0dB | Unity (flat) |
| 100% | +6dB | Boost |

This matches DJ mixer convention: center = flat, fully down = kill.

---

## Signal Flow

```
Generator → [Trim] → [EQ] → [Gain Stage] → [Pan] → [Volume] → Master Bus
                ↑
            NEW: Insert EQ here
```

EQ before gain stage so boosts don't clip the channel, and so the fader controls post-EQ level.

---

## SuperCollider Implementation

Update `\channelStrip` SynthDef:

```supercollider
SynthDef(\channelStrip, { |inBus, outBus, vol=0.8, mute=0, solo=0, gain=1.0, pan=0, 
                          genTrim=0, soloActiveBus, slotID=1,
                          eqLo=1, eqMid=1, eqHi=1|  // NEW: EQ params (linear amp)
    var sig, soloActive, soloGate, ampL, ampR;
    var lo, mid, hi;
    
    sig = In.ar(inBus, 2);
    
    // Generator trim
    sig = sig * genTrim.dbamp;
    
    // === NEW: 3-Band EQ (DJ Isolator style) ===
    // Split into bands using LPF/HPF pairs
    lo = LPF.ar(LPF.ar(sig, 250), 250);  // LR4 @ 250Hz
    hi = HPF.ar(HPF.ar(sig, 2500), 2500);  // LR4 @ 2.5kHz
    mid = sig - lo - hi;  // Remainder = mid band
    
    // Apply gains (0 = kill, 1 = unity, 2 = +6dB)
    lo = lo * eqLo;
    mid = mid * eqMid;
    hi = hi * eqHi;
    
    // Recombine
    sig = lo + mid + hi;
    // === End EQ ===
    
    // Mute
    sig = sig * (1 - mute);
    
    // Solo logic
    soloActive = In.kr(soloActiveBus);
    soloGate = Select.kr(soloActive, [1, solo]);
    sig = sig * soloGate;
    
    // Gain stage
    sig = sig * gain;
    
    // Pan
    sig = Balance2.ar(sig[0], sig[1], pan);
    
    // Volume
    sig = sig * vol;
    
    // Metering
    ampL = Amplitude.kr(sig[0], 0.01, 0.1);
    ampR = Amplitude.kr(sig[1], 0.01, 0.1);
    SendReply.kr(Impulse.kr(24), '/noise/gen/levels', [slotID, ampL, ampR]);
    
    Out.ar(outBus, sig);
}).add;
```

---

## OSC Messages

```
/noise/strip/X/eq/lo   <float 0-2>   // 0=kill, 1=unity, 2=+6dB
/noise/strip/X/eq/mid  <float 0-2>
/noise/strip/X/eq/hi   <float 0-2>
```

Python sends linear amplitude (0-2), not dB.

---

## Python Implementation

### mixer_panel.py - ChannelStrip class

Add three `MiniKnob` widgets (new widget type or reuse DragSlider with knob styling):

```python
# In ChannelStrip.setup_ui()

# EQ section (above fader)
eq_layout = QVBoxLayout()
eq_layout.setSpacing(1)

self.eq_hi = MiniKnob()  # New widget or styled DragSlider
self.eq_hi.setRange(0, 200)  # 0=-∞, 100=0dB, 200=+6dB
self.eq_hi.setValue(100)  # Unity default
self.eq_hi.setFixedSize(20, 20)
self.eq_hi.setToolTip("HI EQ (double-click to reset)")
self.eq_hi.setDoubleClickValue(100)
self.eq_hi.valueChanged.connect(self.on_eq_hi_changed)
eq_layout.addWidget(self.eq_hi, alignment=Qt.AlignCenter)

# ... same for eq_mid, eq_lo ...

layout.addLayout(eq_layout)
```

### Signals

```python
eq_changed = pyqtSignal(int, str, float)  # channel_id, band ('lo'/'mid'/'hi'), value (0-2)

def on_eq_hi_changed(self, value):
    # Convert 0-200 to 0-2 linear
    linear = value / 100.0
    self.eq_changed.emit(self.channel_id, 'hi', linear)
```

---

## State Tracking

Add to `channel_strips.scd`:

```supercollider
~stripEqLoState = Array.fill(8, { 1.0 });
~stripEqMidState = Array.fill(8, { 1.0 });
~stripEqHiState = Array.fill(8, { 1.0 });
```

Preserve EQ state when restarting channel strips (same pattern as mute/solo/gain).

---

## Config

Add to `src/config/__init__.py`:

```python
OSC_PATHS = {
    # ... existing ...
    'strip_eq_lo': '/noise/strip/{}/eq/lo',
    'strip_eq_mid': '/noise/strip/{}/eq/mid',
    'strip_eq_hi': '/noise/strip/{}/eq/hi',
}
```

---

## UI Sizing

Current channel strip width: ~50px

With mini knobs:
- Knob diameter: 18px
- Knob + margin: ~22px
- Still fits in 50px width ✓

Vertical space needed:
- 3 knobs × 20px = 60px
- May need to reduce fader minimum height slightly
- Or accept slightly taller channel strips

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/gui/mixer_panel.py` | Add EQ knobs to ChannelStrip |
| `src/gui/widgets.py` | Add MiniKnob widget (or style DragSlider) |
| `src/gui/theme.py` | Add knob styling |
| `src/config/__init__.py` | Add OSC paths |
| `supercollider/core/channel_strips.scd` | Add EQ to SynthDef |
| `supercollider/core/osc_handlers.scd` | Add EQ OSC handlers |

---

## Testing

1. Each band kills completely at 0
2. Unity (center) is truly flat
3. +6dB boost doesn't clip before fader
4. Double-click resets to unity
5. EQ state preserved when generator changes
6. All 8 channels independent

---

## Future Enhancements

- Per-channel HPF (rumble filter)
- EQ bypass per channel
- Copy EQ settings between channels
- EQ presets (vocal cut, bass boost, etc.)
