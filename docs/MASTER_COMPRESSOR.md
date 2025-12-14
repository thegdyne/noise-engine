# Master Compressor - SSL G-Series Style Bus Compressor

**Status:** ✅ Complete (Phase 5)  
**Created:** 2025-12-14

---

## Overview

The master compressor is modeled after the SSL G-Series bus compressor, the industry standard for "glue" compression on the mix bus. It features stepped controls, dominant stereo detection, and a sidechain high-pass filter.

---

## Signal Flow

```
AUDIO PATH:
  EQ Out → VCA (gain reduction) → Limiter → Output
                ↑
           GR Control
                ↑
SIDECHAIN PATH:
  EQ Out → [SC HPF] → Peak Detector → Gain Computer → Attack/Release → GR
              ↓
         (dominant L/R)
```

**Key Points:**
- Sidechain HPF is on detection signal only, NOT in audio path
- Dominant stereo: max(L, R) controls both channels
- GR applied as VCA-style gain reduction

---

## Architecture Decisions

### Why Custom Detector (Not Compander.ar)

SC's `Compander.ar` doesn't provide SSL-style behavior:
- No dominant stereo detection
- No separate sidechain path
- No true peak detection with custom time constants

Custom implementation allows:
- Proper SSL-style detection
- Sidechain HPF on detection only
- Dominant channel selection
- Auto-release behavior

### Why Dominant Stereo Detection

SSL bus compressors use "dominant" detection where the louder channel controls both:

```supercollider
detector = max(detectorL, detectorR);
```

This prevents:
- Stereo image shift during compression
- Pumping on one channel affecting the other differently
- Unbalanced gain reduction

### Why Stepped Controls

SSL compressors have fixed detented positions, not continuous controls:
- Ratio: 2:1, 4:1, 10:1 (not 1:1 to 20:1)
- Attack: 0.1, 0.3, 1, 3, 10, 30 ms
- Release: 0.1, 0.3, 0.6, 1.2s + Auto

Benefits:
- Faster recall of settings
- Classic SSL workflow
- Reduces decision paralysis

### Why Sidechain HPF (Not "Thrust")

The SC HPF prevents low frequencies from triggering compression:
- Lets bass through without pumping
- Common on SSL 500-series G-Comp
- True bypass at index 0 (not fake 20Hz)

Note: "Thrust" is a weighted sidechain curve (API-2500 style), not just an HPF. We implemented simple HPF; Thrust modes could be added later.

---

## Specifications

### Parameters

| Parameter | Range | Default | Options |
|-----------|-------|---------|---------|
| Threshold | -20 to +20 dB | -10 dB | Continuous |
| Ratio | Fixed | 4:1 | 2:1, 4:1, 10:1 |
| Attack | Fixed | 10ms | 0.1, 0.3, 1, 3, 10, 30 ms |
| Release | Fixed | Auto | 0.1, 0.3, 0.6, 1.2s, Auto |
| Makeup | 0 to +20 dB | 0 dB | Continuous |
| SC HPF | Fixed | Off | Off, 30, 60, 90, 120, 185 Hz |
| Bypass | On/Off | On | - |

### Threshold

- Range: -20dB to +20dB
- Default: -10dB (sensible bus compression starting point)
- At 0dB threshold with typical -6dB peaks, no compression occurs
- Lower threshold = more compression

### Ratio

| Index | Ratio | Use Case |
|-------|-------|----------|
| 0 | 2:1 | Gentle glue |
| 1 | 4:1 | Classic bus compression |
| 2 | 10:1 | Heavy limiting |

### Attack Times

| Index | Time | Character |
|-------|------|-----------|
| 0 | 0.1ms | Fastest - catches all transients |
| 1 | 0.3ms | Fast - slight transient through |
| 2 | 1ms | Medium-fast |
| 3 | 3ms | Medium - punchy |
| 4 | 10ms | Slow - preserves punch |
| 5 | 30ms | Slowest - maximum punch |

### Release Times

| Index | Time | Character |
|-------|------|-----------|
| 0 | 0.1s | Fast - pumping possible |
| 1 | 0.3s | Medium-fast |
| 2 | 0.6s | Medium |
| 3 | 1.2s | Slow - smooth |
| 4 | Auto | Dual-time adaptive |

### Auto Release

Auto release uses dual-time behavior:
- Fast release (0.1s) for transients / light GR
- Slow release (1.2s) when GR exceeds 3dB

```supercollider
autoRelease = Select.kr(gainReductionDb > 3, [
    0.1,    // Light compression: fast release
    1.2     // Heavy compression: slow release
]);
```

### Sidechain HPF

| Index | Frequency | Use |
|-------|-----------|-----|
| 0 | Off (bypass) | Full frequency detection |
| 1 | 30Hz | Subtle - removes sub |
| 2 | 60Hz | Light - reduces bass pumping |
| 3 | 90Hz | Medium |
| 4 | 120Hz | Strong - bass mostly ignored |
| 5 | 185Hz | Aggressive - only mids/highs trigger |

---

## Detection & Gain Computation

### Peak Detection

```supercollider
// Fast peak detection (0.1ms attack)
detectorL = Amplitude.kr(scSig[0], attackTime: 0.0001, releaseTime: 0.05);
detectorR = Amplitude.kr(scSig[1], attackTime: 0.0001, releaseTime: 0.05);
detector = max(detectorL, detectorR);  // Dominant
```

### Gain Computer

```supercollider
// Excess above threshold in dB
excessDb = (detector / thresholdLin.max(0.0001)).ampdb.max(0);

// Apply ratio: GR = excess * (1 - 1/ratio)
gainReductionDb = excessDb * (1 - (1 / ratio));

// Smooth with attack/release
grSmoothed = Lag2UD.kr(gainReductionDb, attack, releaseTime);

// Convert to linear gain
gainReductionLin = grSmoothed.neg.dbamp;
```

---

## OSC Paths

| Path | Value | Description |
|------|-------|-------------|
| `/noise/master/comp/threshold` | -20 to +20 | Threshold (dB) |
| `/noise/master/comp/ratio` | 0-2 | Ratio index |
| `/noise/master/comp/attack` | 0-5 | Attack index |
| `/noise/master/comp/release` | 0-4 | Release index (4=Auto) |
| `/noise/master/comp/makeup` | 0 to +20 | Makeup gain (dB) |
| `/noise/master/comp/sc_hpf` | 0-5 | SC HPF index (0=Off) |
| `/noise/master/comp/bypass` | 0/1 | Bypass |
| `/noise/master/comp/gr` | 0-20 | GR meter (dB, SC→Python) |

---

## UI Layout

```
┌──────────────────────────────────────────────────────┐
│ COMP  [ON]                              GR ████░░░░ │
│                                                      │
│ THR    RAT     ATK      REL      MKP     SC         │
│  █    [2:1]   [0.1]    [0.1]      █    [Off]       │
│  █    [4:1]   [0.3]    [0.3]      █    [ 30]       │
│  █    [10:1]  [ 1 ]    [0.6]      █    [ 60]       │
│  █            [ 3 ]    [1.2]      █    [ 90]       │
│  █            [10 ]    [Auto]     █    [120]       │
│  █            [30 ]               █    [185]       │
└──────────────────────────────────────────────────────┘
```

---

## GR Meter

- Range: 0 to 20dB gain reduction
- Update rate: 24fps (matches level meters)
- Display: Vertical bar, orange/amber color
- Sent from SC via SendReply → Python via OSC

```supercollider
SendReply.kr(
    Impulse.kr(meterRate),
    '/masterCompGR',
    [grDb]
);
```

---

## Implementation

### SuperCollider (master_passthrough.scd)

Key sections:
- Parameter arrays for stepped controls
- Sidechain HPF with true bypass
- Peak detector with dominant selection
- dB-domain gain computer
- Auto-release logic
- GR metering via SendReply

### Python (master_section.py)

- `comp_threshold` - DragSlider
- `comp_ratio_btns` - Button array (3)
- `comp_attack_btns` - Button array (6)
- `comp_release_btns` - Button array (5)
- `comp_makeup` - DragSlider
- `comp_sc_btns` - Button array (6)
- `comp_bypass_btn` - Toggle
- `comp_gr_meter` - QProgressBar

---

## Files

- `supercollider/effects/master_passthrough.scd` - DSP implementation
- `src/gui/master_section.py` - UI controls
- `src/audio/osc_bridge.py` - GR meter signal
- `src/config/__init__.py` - OSC path definitions

---

## Future Enhancements

### Thrust Modes (Not Implemented)

Full "Thrust" is a weighted sidechain curve, not just HPF:
- ThrustM: Mid-focused weighting
- ThrustL: Low-cut plus mid emphasis

Could be added as `SC_MODE = Off | HPF | ThrustM | ThrustL`

### Mix/Blend Control

Parallel compression via wet/dry mix:
- 100% wet = full compression
- 50% = parallel compression
- Common on modern bus compressors

### Soft Knee

SSL-style ratio affects perceived knee behavior. Could add:
- Ratio-dependent soft knee
- Or threshold offset based on ratio

---

## Design Rationale

### Why SSL G-Style?

1. **Industry standard** - Most engineers know it
2. **Musical on bus** - Designed for mix glue
3. **Predictable** - Stepped controls = repeatable results
4. **Dominant stereo** - Maintains stereo image

### Why -10dB Default Threshold?

At 0dB threshold, typical -6dB peaks won't trigger compression. -10dB ensures:
- Compression actually happens out of the box
- GR meter shows activity
- User can hear the effect immediately

### Why Auto-Release Default?

Auto-release is the most forgiving:
- Adapts to material
- Less pumping than fixed fast release
- Less sluggish than fixed slow release
- Good starting point for any material
