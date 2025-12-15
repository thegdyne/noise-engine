# Discord Update - December 15, 2025

## 🎛️ MODULATION SOURCES LIVE!

The mod panel is now functional! 4 mod source slots with real-time oscilloscope display.

### What's Working

**LFO (based on Ginkosynthese TTLFO v2)**
- Clock-synced from /64 (16 bars) to x32 (audio rate)
- 8 waveforms: Saw, Ramp, Square, Triangle, Sine, Rectified±, S&H
- 3 independent outputs (A, B, C) with per-output waveform, phase & polarity
- Shape control (waveform distortion / PWM)
- Default phases spread at ~120° for immediate stereo movement

**Sloth (inspired by NLC Triple Sloth)**
- 3 speed modes: Torpor (~20s), Apathy (~75s), Inertia (~33min)
- Chaos-style slowly varying CV
- Bias control affects attractor weighting
- X, Y, Z outputs (Z = inverted Y, per NLC design)

**Scope Display**
- Real-time 3-trace oscilloscope per slot
- ~30fps update rate
- Colour-coded traces from new skin system

### Skin System (Phase 1)

Started implementing a proper skin/theme system:
- High-contrast default theme
- Module accent colours: Green (generators), Cyan (LFO), Orange (Sloth), Purple (effects)
- Foundation for future skin switching

### Layout

Mod sources now in a 2×2 grid that aligns with the generator rows:
```
[LFO]   [Sloth]  ← Row 1
[LFO]   [Sloth]  ← Row 2
```

### Coming Next

- LFO FREE mode (non-clocked)
- Mod routing matrix (connect to generator params)
- Phase 8 polish (tooltips, edge cases)
- More skins

### Try It

```bash
git pull
# Restart SuperCollider (re-run init.scd)
# Restart Python GUI
# Click Connect - mod sources should auto-start with LFO/Sloth
```

The mod buses are outputting CV but not routed to anything yet - that's the routing matrix work. For now you can see the waveforms in the scopes!
