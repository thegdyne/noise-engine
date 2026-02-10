# Noise Engine — Project State

**Last updated:** 2026-02-09 by agent (dual filter sync fix, modulation invariant documented)

---

## Subsystem Status

Only actively-changing subsystems are tracked here. Stable systems belong in ARCHITECTURE.md, not this table. Add rows when work begins; remove when a system stabilises.

| System | Status (Stable/Active/Built-unused/Planned/Blocked) | Key Files (repo paths) |
|--------|------------------------------------------------------|------------------------|
| Generators | Stable | `src/config/__init__.py`, `packs/core/generators/`, `supercollider/core/helpers.scd` |
| Modulation | Active | `src/boids/boid_controller.py`, `src/gui/mod_matrix_window.py`, `supercollider/core/mod_slots.scd` |
| Mixer/Master | Stable | `src/gui/mixer_panel.py`, `supercollider/core/channel_strips.scd`, `supercollider/core/master.scd` |
| Presets | Stable | `src/presets/preset_manager.py`, `src/presets/preset_schema.py`, `src/presets/migrations.py` |
| Imaginarium | Active | `imaginarium/`, `imaginarium/generate.py`, `imaginarium/select.py` |
| Morph Mapper | Active | `src/telemetry/morph_mapper.py`, `tools/analyze_morph_map.py`, `src/telemetry/stabilizer.py` |
| FX System | Active | `supercollider/core/fx_slots.scd`, `supercollider/effects/`, `src/gui/mixer_panel.py` |
| Keyboard Overlay | Stable | `src/gui/keyboard_overlay.py`, `src/gui/arp_engine.py`, `src/gui/seq_engine.py` |

## Active Concepts

Current technical approaches and design decisions that are **in effect**.
Not history — just what's true right now. One line per concept.

- **Clock Fabric:** 13 pre-divided trigger buses from master clock (BPM → Impulse.ar); all timing features derive from it, no parallel dividers — `docs/CLOCK_FABRIC.md`
- **Generator contract:** Lightweight end-stage — `|out, freqBus, customBus0..4|`, must use `~multiFilter`, `~envVCA`, `~ensure2ch` helpers
- **Morph analysis:** Three-track decomposition (Gain/DC/Shape) — `tools/analyze_morph_map.py`
- **Unified bus system:** 176 control-rate targets (gen core 0-39, gen custom 40-79, mod 80-107, channels 108-147, FX 148-167, master inserts 168-175) — `src/config/__init__.py`
- **Boid modulation:** Flocking sim at 20Hz, sparse offset array via `/noise/boid/offsets`, zone filter for cell activation — `src/boids/boid_controller.py`
- **FX architecture:** 4 hot-swappable send/return slots (Echo/Reverb/Chorus/LoFi) + 2 master inserts (Heat saturation, Dual Filter) — `supercollider/core/fx_slots.scd`
- **Imaginarium pipeline:** Image-to-pack generation — extract features, generate candidates, NRT render, safety check, score, farthest-first selection, export — `imaginarium/`
- **Preset schema:** v2 with atomic writes, FX slot state included, migrations for v1 compatibility — `src/presets/preset_schema.py`
- **Keyboard overlay:** Pure view pattern (v2.0), per-slot ARP/SEQ engines bound via controller, UI 1-indexed / OSC 0-indexed — `src/gui/keyboard_overlay.py`
- **Telemetry:** Infrastructure observer tap (non-invasive), internal + external modes, stabilizer for persistence display — `src/audio/telemetry_controller.py`
- **OSC connection:** Port 57120 forced, ping/pong handshake, heartbeat every 2s, 3 missed = CONNECTION LOST — `src/audio/osc_bridge.py`
- **OSC clock rate protocol:** Always send integer indices (-1=OFF, 0-12=clock rate), never string labels — prevents `~clockRateIndexOfLabel` silent -1 failures

### Modulation Domain Invariant

1. **Standard Modulation (Unified Bus):**
   - All 176 targets operate in **Normalized Space [0, 1]**.
   - Summation is strictly **Additive**: `eff = clip(base + (mod * scale))`.

2. **The "Sync LFO" Exception (Dual Filter Only):**
   - **Domain:** Physical Unit Space (Hz).
   - **Logic:** Multiplicative / Ratio-based.
   - **Polarity:** Unipolar Negative (Down-only).
   - **Intent:** To preserve logarithmic musical intervals during filter sweeps
     without consuming normalized headroom in the main modulation bus.
   - **Constraint:** Do not "refactor" to additive unless the entire
     filter mapping logic is moved pre-linexp.

## Known Issues

Current bugs and tech debt. Remove when fixed. Add when discovered.
**Pruning rule:** If `last_seen` is 30+ days ago and no owner is actively working it, move it to BACKLOG.md or delete it.

| Issue | Location | Priority | last_seen | Notes |
|-------|----------|----------|-----------|-------|
| Keyboard overlay slots 2-8 greyed out in MIDI mode | `src/gui/keyboard_overlay.py` | Medium | 2026-02-06 | Slot target buttons visually disabled when not slot 1 |
| `save_map()` timing cosmetic bug | `src/telemetry/morph_mapper.py:432` | Low | 2026-02-06 | Uses stale `_total_time` if called without prior `run_sweep()` |
| Mod matrix source selection dialog missing | `src/gui/mod_matrix_window.py:1340` | Low | 2026-02-06 | TODO in code — no source selection dialog implemented |

## Recent Changes

Reverse chronological. Keep the last 10 entries. Oldest entries get pruned.

- 2026-02-09: Fix dual filter sync modulation (send idx not labels, SSOT clockMults, FREE→OFF)
- 2026-02-09: Merge FILT SYNC panel into FILT, replace Phasor LFO with SinOsc.kr
- 2026-02-09: Document modulation domain invariant (additive vs multiplicative exception)
- 2026-02-06: Fix FFT spectral leakage in fingerprint extractor (whole-cycle trim)
- 2026-02-06: Added STATE.md automated project state tracking
