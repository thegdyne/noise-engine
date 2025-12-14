# Master Limiter - Brickwall Output Protection

**Status:** ✅ Complete (Phase 4)  
**Created:** 2025-12-14

---

## Overview

The master limiter is a brickwall limiter positioned at the end of the signal chain before output. Its primary purpose is **protection** - preventing digital overs and speaker damage - rather than creative gain maximization.

---

## Signal Flow

```
EQ → Compressor → LIMITER → Master Volume → Output
                     ↓
              Ceiling Control
```

**Position:** After compressor, before master volume. This ensures:
- Compressor output can't clip
- Master volume adjustment doesn't bypass protection
- Final output never exceeds ceiling

---

## Specifications

### Parameters

| Parameter | Range | Default | Unit |
|-----------|-------|---------|------|
| Ceiling | -6 to 0 | -0.1 | dB |
| Lookahead | Fixed | 10 | ms |
| Bypass | On/Off | On | - |

### Ceiling

- **Range:** -6dB to 0dB
- **Default:** -0.1dB (leaves headroom for intersample peaks)
- **Purpose:** Maximum output level
- **UI:** Slider with dB ValuePopup

Why -0.1dB default:
- Prevents intersample clipping on D/A conversion
- Industry standard for digital masters
- Leaves tiny headroom without audible level loss

### Lookahead

- **Fixed at 10ms**
- Allows limiter to anticipate peaks
- Smoother limiting than zero-lookahead
- 10ms is SC Limiter.ar default

### Bypass

- When bypassed, signal passes through unlimited
- **Warning:** Bypassing removes protection - use with caution
- Visual feedback: ON (green) vs BYP (orange/warning)

---

## Implementation

### SuperCollider

```supercollider
// Brickwall limiter with lookahead
sigLimited = Limiter.ar(sig, limiterCeiling, 0.01);
sig = Select.ar(limiterBypass, [sigLimited, sig]);
```

Using SC's built-in `Limiter.ar`:
- True brickwall behavior
- Lookahead-based (not clipping)
- Efficient and battle-tested

### Python

- `ceiling_fader` - DragSlider (0-600 → -6dB to 0dB)
- `limiter_bypass_btn` - Toggle button
- `ceiling_label` - dB display

---

## OSC Paths

| Path | Value | Description |
|------|-------|-------------|
| `/noise/master/limiter/ceiling` | -6 to 0 | Ceiling (dB) |
| `/noise/master/limiter/bypass` | 0/1 | Bypass state |

---

## UI Layout

```
┌─────────┐
│   LIM   │
│  [ON]   │  ← Bypass toggle
│    █    │
│    █    │  ← Ceiling slider
│    █    │
│  -0.1   │  ← dB display
└─────────┘
```

---

## Files

- `supercollider/effects/master_passthrough.scd` - Limiter DSP
- `src/gui/master_section.py` - UI controls
- `src/config/__init__.py` - OSC paths

---

## Design Rationale

### Why Brickwall (Not Soft Clipper)?

- **Predictable:** Output never exceeds ceiling
- **Transparent:** Minimal coloration at low GR
- **Safe:** Guaranteed protection for downstream equipment

Soft clipping adds harmonics and doesn't guarantee peak level.

### Why After Compressor?

Compressor can add gain (makeup), potentially causing peaks. Limiter catches these:
```
Comp output: -3dB peak + 6dB makeup = +3dB peak
Limiter catches: +3dB → -0.1dB
```

### Why Before Master Volume?

If limiter were after master volume:
- Turning up master could bypass the protection intent
- Limiter would constantly engage as volume increases

Current position means:
- Limiter sets absolute ceiling
- Master volume scales within safe range

### Why No GR Meter?

The limiter should rarely engage with proper gain staging:
1. Generators have individual volume
2. Mixer has channel faders
3. Compressor has makeup gain
4. Master fader scales output

If limiter is constantly working, gain staging is wrong. A GR meter could be added but may encourage "riding the limiter" which isn't the intent.

---

## Usage Notes

### When to Adjust Ceiling

- **Recording:** Keep at -0.1dB for maximum headroom
- **Live performance:** May lower to -1dB or -2dB for extra safety
- **Intentional clipping:** Set to -6dB and drive harder (not recommended)

### When to Bypass

- **Never during normal use** - protection should always be active
- **Testing/debugging** - to hear pre-limited signal
- **Trust your gain staging** - if you've set levels correctly, limiter is transparent

### Gain Staging for Minimal Limiting

1. Set generator volumes so peaks hit -12dB to -6dB
2. Use mixer faders for balance, not level
3. Keep compressor makeup modest
4. Master fader at 80% (-2dB) default
5. Limiter should see peaks at -3dB to 0dB, rarely engaging
