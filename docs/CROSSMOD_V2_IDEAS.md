# Crossmod v2 Ideas

Features deferred from v1 implementation, captured for future development.

**v1 shipped:** 2025-12-30  
**Status:** Backlog

---

## Follower Controls Panel

**What:** When clicking a row label (GEN 1, GEN 2, etc.), show a side panel with full follower configuration.

**Controls:**
- EN checkbox (currently in row header)
- ATK slider (attack time, log scale, 1ms-500ms)
- REL slider (release time, log scale, 10ms-2000ms)

**OSC:**
```
/noise/crossmod/attack/<src> <seconds>
/noise/crossmod/release/<src> <seconds>
```

**Why deferred:** Defaults (10ms attack, 100ms release) work for most use cases. Row header EN checkbox covers the must-have (CPU savings when disabled).

**When to add:** If users request finer control over follower response, or for specific musical effects (very fast attack for transient following, very slow release for ambient swells).

---

## Depth & Polarity in Popup

**What:** Expose `depth` and `polarity` parameters in the connection popup.

**Current v1:** Hardcoded `depth=1.0`, `polarity=0` (unipolar)

**v2 popup would have:**
- Amount (0-100%)
- Offset (-100% to +100%)
- Depth (0-100%) — scales the modulation range
- Polarity toggle (unipolar 0..1 / bipolar -1..+1)
- Invert checkbox

**Why deferred:** Amount+Offset+Invert covers 90% of use cases. Depth and polarity add complexity without proportional benefit for v1.

**When to add:** Power user requests, or if bipolar crossmod (centered modulation) proves musically useful.

---

## Visual Feedback / Activity Meters

**What:** Show activity on active crossmod routes.

**Options:**
1. **Cell glow** — Active cells pulse/glow based on follower level
2. **Row meters** — Small VU meter next to each GEN label showing follower output
3. **Connection lines** — Animated lines between source and target (like some modular synth UIs)

**Why deferred:** Functional crossmod works without visual feedback. Adds rendering overhead and UI complexity.

**When to add:** If users find it hard to understand what's modulating what, or for educational/demo purposes.

---

## Theme Integration

**What:** Row colours, cell states, and popup styling from app theme system.

**Current v1:** Hardcoded palette (dark grey inactive, coloured active, etc.)

**Why deferred:** Works fine with hardcoded colours. Theme system may not exist yet.

**When to add:** When implementing app-wide theming, or if users request dark/light mode.

---

## Per-Connection ATK/REL Override

**What:** Allow different attack/release times per connection, not just per source.

**Example:** Gen 3 → Gen 5 cutoff could have fast attack, while Gen 3 → Gen 7 frequency has slow attack.

**Current model:** One follower per source, all routes from that source share ATK/REL.

**Why deferred:** Significantly more complex. Requires either multiple followers per source or post-follower envelope shaping. Unclear if musically necessary.

**When to add:** If specific use cases emerge where per-route envelope shaping is essential.

---

## Preset System

**What:** Save/recall crossmod routing configurations.

**Would include:**
- All route states (source, target, param, amount, offset, invert)
- Follower enable states
- Optionally ATK/REL if exposed

**Why deferred:** v1 focuses on core routing. Presets are session management, separate concern.

**When to add:** When implementing broader session/preset management for noise-engine.

---

## Crossmod Sidechain Input

**What:** External audio input as crossmod source (source ID 24?).

**Use case:** Modulate generators based on external audio (DJ mixing, live performance with other instruments).

**Why deferred:** Requires audio input infrastructure, latency considerations, level normalisation.

**When to add:** When external audio input is added to noise-engine generally.

---

## Notes

- v1 implementation: `crossmod_matrix_window.py`, `crossmod_routing_state.py`, etc.
- Design spec: `CROSSMOD_GUI_DESIGN.md`
- Backend: envelope followers in SuperCollider tapping `~genBus[0-7]`
