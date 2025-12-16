# Mod Sources - Delivery Phases

**Parent doc:** `docs/MOD_SOURCES.md`  
**Created:** December 2025

---

## Phase 1: Config & Infrastructure

**Goal:** SSOT foundation - all constants and loaders in place.

### Tasks

1. **Add config constants** (`src/config/__init__.py`)
   - `MOD_SLOT_COUNT = 4`
   - `MOD_OUTPUTS_PER_SLOT = 3`
   - `MOD_BUS_COUNT = 12`
   - `MOD_GENERATOR_CYCLE = ["Empty", "LFO", "Sloth"]`
   - `MOD_LFO_WAVEFORMS` + index dict
   - `MOD_LFO_PHASES` + index dict
   - `MOD_SLOTH_MODES` + index dict
   - `MOD_CLOCK_RATES` + index dict
   - `MOD_POLARITY` + index dict
   - `MOD_OUTPUT_LABELS` dict

2. **Add OSC paths** (`src/config/__init__.py`)
   - `/noise/mod/generator` (args: slot, genName)
   - `/noise/mod/param` (args: slot, key, value)
   - `/noise/mod/out/wave` (args: slot, output, waveIndex)
   - `/noise/mod/out/phase` (args: slot, output, phaseIndex)
   - `/noise/mod/out/pol` (args: slot, output, polarity)
   - `/noise/mod/bus/value` (args: bus, value)

3. **Create mod generator loader**
   - `_MOD_GENERATOR_CONFIGS = {}`
   - `_load_mod_generator_configs()` 
   - `get_mod_generator_synthdef()`
   - `get_mod_generator_custom_params()`
   - `get_mod_generator_output_config()`
   - `get_mod_output_labels()`

4. **Create JSON configs**
   - `supercollider/mod_generators/lfo.json`
   - `supercollider/mod_generators/sloth.json`

### Validation
- [ ] `from src.config import MOD_GENERATOR_CYCLE` works
- [ ] `get_mod_output_labels("Sloth")` returns `["X", "Y", "Z"]`
- [ ] No hardcoded values outside config

---

## Phase 2: SuperCollider Mod Buses

**Goal:** 12 control buses allocated and accessible.

### Tasks

1. **Create mod bus definitions** (`supercollider/core/mod_buses.scd`)
   ```supercollider
   ~modBuses = Array.fill(12, { Bus.control(s, 1) });
   ~modBusIndex = { |slot, output| ((slot - 1) * 3) + output };
   ```

2. **Add OSC handlers for mod buses**
   - Receive parameter changes from Python
   - Write to appropriate control bus

3. **Update init.scd** to load mod_buses.scd

### Validation
- [ ] `~modBuses[0].index` returns valid bus number
- [ ] Can write/read from mod buses in SC

---

## Phase 3: LFO SynthDef

**Goal:** Working modLFO outputting to 3 buses.

### Tasks

1. **Create modLFO SynthDef** (`supercollider/core/mod_synths.scd`)
   - Inputs: outA, outB, outC (bus indices)
   - Inputs: rate, shape (shared params)
   - Inputs: waveA, phaseA, polarityA (per-output)
   - Inputs: waveB, phaseB, polarityB
   - Inputs: waveC, phaseC, polarityC
   - Clock sync via `~clockTrigBus`
   - 8 waveform types with shape distortion
   - Phase offset per output
   - Unipolar/bipolar per output
   - `Out.kr()` to 3 buses

2. **Add OSC handlers** for LFO parameters

### Validation
- [ ] LFO outputs visible on control buses
- [ ] Waveform selection works
- [ ] Phase offset works
- [ ] Shape distortion works
- [ ] Clock sync works

---

## Phase 4: Sloth SynthDef

**Goal:** Working modSloth chaos outputting to 3 buses.

### Tasks

1. **Create modSloth SynthDef** (`supercollider/core/mod_synths.scd`)
   - Inputs: outX, outY, outZ (bus indices)
   - Inputs: mode (0=Torpor, 1=Apathy, 2=Inertia)
   - Inputs: bias (attractor weight)
   - Inputs: polarityX, polarityY, polarityZ
   - Chaos algorithm (Lorenz or similar)
   - Time scaling per mode
   - Z = inverted Y
   - `Out.kr()` to 3 buses

2. **Add OSC handlers** for Sloth parameters

### Validation
- [ ] Sloth outputs slowly varying values
- [ ] Mode changes affect speed dramatically
- [ ] Bias affects attractor weighting
- [ ] X, Y, Z are related but different

---

## Phase 5: Basic Slot UI

**Goal:** ModSourceSlot widget displaying and controlling one mod source.

### Tasks

1. **Create ModSourceSlot widget** (`src/gui/mod_source_slot.py`)
   - Generator CycleButton (from `MOD_GENERATOR_CYCLE`)
   - 3 output rows (dynamic labels from config)
   - Per-output: waveform, phase, polarity (for LFO)
   - Per-output: polarity only (for Sloth)
   - Parameter sliders (from JSON custom_params)
   - Placeholder for scope

2. **Dynamic UI based on generator type**
   - `output_config: "waveform_phase"` → show wave/phase buttons
   - `output_config: "fixed"` → show labels only

3. **Wire signals to OSC bridge**
   - Generator change → `/noise/mod/generator` (slot, genName)
   - Param change → `/noise/mod/param` (slot, key, value)
   - Output wave → `/noise/mod/out/wave` (slot, output, index)
   - Output phase → `/noise/mod/out/phase` (slot, output, index)
   - Output polarity → `/noise/mod/out/pol` (slot, output, index)

### Validation
- [ ] Slot displays correctly for LFO
- [ ] Slot displays correctly for Sloth
- [ ] Switching generators updates UI
- [ ] OSC messages sent on control changes

---

## Phase 6: Mod Source Panel

**Goal:** 4 slots integrated into left panel.

### Tasks

1. **Create ModSourcePanel** (`src/gui/mod_source_panel.py`)
   - Vertical stack of `MOD_SLOT_COUNT` slots
   - Replace existing WIP modulation_sources.py

2. **Integrate into main_frame.py**
   - Replace placeholder modulation panel
   - Connect OSC bridge

3. **Styling**
   - Match existing theme
   - Differentiate from audio generator slots

### Validation
- [ ] 4 slots visible in left panel
- [ ] All slots independently controllable
- [ ] Panel scrolls if needed at small sizes

---

## Phase 7: Scope Display

**Goal:** Per-slot scope showing 3 output traces.

### Tasks

1. **Create ModScope widget** (`src/gui/mod_scope.py`)
   - Receives values from SC via OSC
   - Circular buffer for history
   - 3 traces, colour-coded
   - Auto-ranging time scale

2. **SC → Python value stream**
   - SC sends periodic bus values: `/noise/mod/bus/value` (args: bus, value)
   - Rate: ~30fps for scope update
   - Only send when slot is active

3. **Integrate scope into ModSourceSlot**
   - Display below parameters
   - Shows outputs for current generator

4. **Auto-ranging logic**
   - LFO: based on rate param
   - Sloth: based on mode (Torpor/Apathy/Inertia)

### Validation
- [ ] Scope shows live waveforms
- [ ] 3 traces visible and distinguishable
- [ ] Time scale adjusts appropriately
- [ ] Sloth at Inertia speed still readable

---

## Phase 8: Empty State & Polish

**Goal:** Clean empty state, visual polish, edge cases.

### Tasks

1. **Empty generator handling**
   - No audio output
   - Scope shows flat lines or disabled
   - Minimal UI (just generator selector)

2. **Visual polish**
   - Consistent spacing
   - Proper disabled states
   - Tooltips on all controls

3. **Edge cases**
   - Rapid generator switching
   - Extreme parameter values
   - Window resize behaviour

4. **Update WIP badge removal**
   - Remove "COMING SOON" from mod sources panel

### Validation
- [ ] Empty state looks intentional
- [ ] No visual glitches
- [ ] Stable under rapid interaction

---

## Delivery Status

### Phase 1: Config & Infrastructure
| Item | Status |
|------|--------|
| `MOD_SLOT_COUNT = 4` | ✅ |
| `MOD_OUTPUTS_PER_SLOT = 3` | ✅ |
| `MOD_BUS_COUNT = 12` | ✅ |
| `MOD_GENERATOR_CYCLE` | ✅ |
| `MOD_LFO_WAVEFORMS` + index | ✅ |
| `MOD_LFO_PHASES` + index | ✅ |
| `MOD_SLOTH_MODES` + index | ✅ |
| `MOD_CLOCK_RATES` + index | ✅ |
| `MOD_POLARITY` + index | ✅ |
| `MOD_OUTPUT_LABELS` dict | ✅ |
| OSC paths for mod system | ✅ |
| `_MOD_GENERATOR_CONFIGS` | ✅ |
| `_load_mod_generator_configs()` | ✅ |
| `get_mod_generator_synthdef()` | ✅ |
| `get_mod_generator_custom_params()` | ✅ |
| `get_mod_generator_output_config()` | ✅ |
| `get_mod_output_labels()` | ✅ |
| `mod_generators/lfo.json` | ✅ |
| `mod_generators/sloth.json` | ✅ |

### Phase 2: SuperCollider Mod Buses
| Item | Status |
|------|--------|
| `supercollider/core/mod_buses.scd` | ✅ |
| `~modBuses` array (12 buses) | ✅ |
| `~modBusIndex` helper function | ✅ |
| `supercollider/core/mod_slots.scd` | ✅ |
| `~modNodes` array (4 synth refs) | ✅ |
| `~freeModSlot` function | ✅ |
| `~startModSlot` function | ✅ |
| OSC handler `/noise/mod/generator` (args: slot, genName) | ✅ |
| OSC handlers for mod params | ✅ |
| Update `init.scd` to load mod_buses + mod_slots | ✅ |

### Phase 3: LFO SynthDef
| Item | Status |
|------|--------|
| `modLFO` SynthDef | ✅ |
| 3 output buses (outA, outB, outC) | ✅ |
| rate param (clock division) | ✅ |
| shape param (waveform distortion) | ✅ |
| Per-output waveform select | ✅ |
| Per-output phase offset | ✅ |
| Per-output polarity (UNI/BI) | ✅ |
| Clock sync via `~clockTrigBus` | ✅ |
| 8 waveform types | ✅ |
| Shape distortion algorithm | ✅ |
| OSC handlers for LFO | ✅ (in mod_osc.scd) |

### Phase 4: Sloth SynthDef
| Item | Status |
|------|--------|
| `modSloth` SynthDef | ✅ |
| 3 output buses (outX, outY, outZ) | ✅ |
| mode param (Torpor/Apathy/Inertia) | ✅ |
| bias param (attractor weight) | ✅ |
| Per-output polarity (UNI/BI) | ✅ |
| Chaos algorithm | ✅ (simplified Lorenz-like) |
| Time scaling per mode | ✅ |
| Z = inverted Y | ✅ |
| OSC handlers for Sloth | ✅ (in mod_osc.scd) |

### Phase 5: Basic Slot UI
| Item | Status |
|------|--------|
| `src/gui/mod_source_slot.py` | ✅ |
| Generator CycleButton | ✅ |
| 3 output rows (dynamic labels) | ✅ |
| Per-output waveform button (LFO) | ✅ |
| Per-output phase button (LFO) | ✅ |
| Per-output polarity toggle | ✅ |
| Parameter sliders from JSON | ✅ |
| Scope placeholder | ✅ |
| Dynamic UI based on output_config | ✅ |
| OSC signal wiring | ✅ |

### Phase 6: Mod Source Panel
| Item | Status |
|------|--------|
| `src/gui/mod_source_panel.py` | ✅ |
| Vertical stack of 4 slots | ✅ |
| Replace WIP modulation_sources.py | ✅ |
| Integrate into main_frame.py | ✅ |
| Connect OSC bridge | ✅ |
| Theme/styling | ✅ |

### Phase 7: Scope Display
| Item | Status |
|------|--------|
| `src/gui/mod_scope.py` | ✅ |
| Circular buffer for history | ✅ |
| 3 traces, colour-coded | ✅ |
| Auto-ranging time scale | ⬜ (future) |
| SC → Python value stream | ✅ |
| OSC `/noise/mod/bus/value` | ✅ |
| OSC `/noise/mod/scope/enable` | ✅ |
| SC only streams enabled slots | ✅ |
| ~30fps update rate | ✅ |
| UI throttle (not per-message) | ✅ |
| Integrate into ModSourceSlot | ✅ |
| Skin colours integration | ✅ |

### Phase 8: Empty State & Polish
| Item | Status |
|------|--------|
| Empty generator - free synth node | ✅ |
| Empty generator - zero buses | ✅ |
| Empty generator - minimal UI | ✅ |
| Scope disabled/flat for Empty | ✅ |
| CycleButton wrap=True default | ✅ |
| Default generators (LFO/Sloth) | ✅ |
| Default phases spread (~120°) | ✅ |
| State sync on connect | ✅ |
| Consistent spacing | ⬜ |
| Tooltips on all controls | ⬜ |
| Window resize behaviour | ⬜ |
| Remove "COMING SOON" badge | ⬜ |

---

## Phase Dependencies

```
Phase 1 ─────┬────► Phase 2 ────┬────► Phase 3 ────┐
             │                  │                  │
             │                  └────► Phase 4 ────┼────► Phase 5 ────► Phase 6 ────► Phase 7 ────► Phase 8
             │                                     │
             └─────────────────────────────────────┘
```

**Parallel work:** Phases 3 & 4 can run in parallel after Phase 2.

---

## Future Phases (Post-MVP)

### Phase 9: Additional Mod Generators
- Drift (slow smooth random)
- Envelope (clockable ADSR)
- Step sequencer

### Phase 10: Mod Routing Matrix
- Connect mod buses to generator parameters
- See `docs/MODULATION_SYSTEM.md`

### Phase 11: Modulation Visualisation
- Wavestate-style indicators on target sliders
- See `docs/MODULATION_SYSTEM.md`
