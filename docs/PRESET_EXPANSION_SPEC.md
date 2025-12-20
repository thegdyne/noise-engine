# Preset Expansion Spec v2.3 (FROZEN)

*Full Session State — December 2025*
*Final frozen spec after AI1 + AI2 review*

---

## Goal

Expand presets from "patch" (generators + basic mixer) to "full session" (entire working state). Users can save/restore complete sessions including modulation routing.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use `generator_id` = `"pack:stem"` | Stable across renames. Stem from filesystem, not display name |
| Add `preset_id` (UUID) | Prevents name collisions, enables future session management |
| `created` as ISO-8601 UTC | Standard timestamp format |
| `preset_id`/`created` generated at save | Not in constructor — avoids dirtying runtime state |
| `pack_id` derived, not stored | Derive from first non-empty slot's generator_id prefix |
| Store `mapping_version` | Future-proofs if UI→dB curves change |
| Store slot indices as 0-7 | Match Python internals, show 1-8 in UI only |
| `offset` range -1.0 to +1.0 | Bipolar in normalized space |
| Don't store audio device | Machine-specific, causes "device missing" errors |
| Polarity: output × connection | Document precedence to avoid confusion |
| Two validation modes | strict (tests) vs best-effort (user load) |

**Generator ID namespaces:**
- `core:*` — core audio generators (e.g. `core:saw`, `core:drone`, `core:fm`)
- `mod:*` — mod generators (e.g. `mod:lfo`, `mod:sloth`)
- `{pack_id}:*` — pack generators (e.g. `classic_synths:tb303`, `808_drums:kick_808`, `rlyeh:cthulhu`)

**Generator file locations:**
- Core generators: `supercollider/generators/*.scd` + `supercollider/generators/*.json`
- Pack generators: `packs/{pack_id}/generators/*.scd` + `packs/{pack_id}/generators/*.json`

**Generator ID resolution:**
- Loader resolves `generator_id` to generator config via registry
- Unknown IDs become empty generator (best-effort) or error (strict)
- Empty generator: `generator_id = ""` (empty string, not `"core:empty"`)

**Pack ID UI rule:**
- When derived `pack_id` is `""` (all slots empty), UI shows "Core" pack selected

---

## Current State (v1 — today's implementation)

Already captured in `PresetState`:

| Component | Fields |
|-----------|--------|
| 8 Generator Slots | type, params[10], filter_type, env_source, clock_rate, midi_channel |
| 8 Mixer Channels | volume, pan, mute, solo |
| Master | volume |

**Note:** No v1 presets exist in the wild yet. We can update schema directly to v2 without migration code.

---

## Expansion Scope

### Phase 1: Channel Strip Expansion

**Per-channel (×8):**
| Field | Widget | Range | Default | Notes |
|-------|--------|-------|---------|-------|
| eq_hi | MiniKnob | 0-200 | 100 | 100 = 0dB, maps to -20..+20dB |
| eq_mid | MiniKnob | 0-200 | 100 | |
| eq_lo | MiniKnob | 0-200 | 100 | |
| gain | Button index | 0/1/2 | 0 | 0=0dB, 1=+6dB, 2=+12dB |
| echo_send | MiniKnob | 0-200 | 0 | |
| verb_send | MiniKnob | 0-200 | 0 | |
| lo_cut | Button | bool | False | |
| hi_cut | Button | bool | False | |

**Schema addition to `ChannelState`:**
```python
@dataclass
class ChannelState:
    # Existing
    volume: float = 0.8
    pan: float = 0.5
    mute: bool = False
    solo: bool = False
    # New - Phase 1
    eq_hi: int = 100
    eq_mid: int = 100
    eq_lo: int = 100
    gain: int = 0  # Index: 0=0dB, 1=+6dB, 2=+12dB
    echo_send: int = 0
    verb_send: int = 0
    lo_cut: bool = False
    hi_cut: bool = False
```

---

### Phase 2: Global & Master

**Global:**
| Field | Widget | Range | Default |
|-------|--------|-------|---------|
| bpm | BPMDisplay | 20-300 | 120 |

**Note:** `pack_id` is derived on load from first non-empty slot's generator_id prefix, not stored.

**Master EQ:**
| Field | Widget | Range | Default |
|-------|--------|-------|---------|
| eq_hi | Slider | 0-400 | 200 | 200 = 0dB |
| eq_mid | Slider | 0-400 | 200 | |
| eq_lo | Slider | 0-400 | 200 | |
| eq_hi_kill | Button | bool | False |
| eq_mid_kill | Button | bool | False |
| eq_lo_kill | Button | bool | False |
| eq_locut | Button | bool | False |
| eq_bypass | Button | bool | False |

**Master Compressor:**
| Field | Widget | Range | Default |
|-------|--------|-------|---------|
| comp_threshold | Slider | 0-400 | 200 | 200 = 0dB |
| comp_ratio | Button index | 0-3 | 1 | [2:1, 4:1, 8:1, 20:1] |
| comp_attack | Button index | 0-2 | 1 | [0.1ms, 0.3ms, 1ms] |
| comp_release | Button index | 0-3 | 1 | [0.1s, 0.3s, 0.6s, 1.2s] |
| comp_makeup | Slider | 0-200 | 0 | Maps to 0..+20dB |
| comp_sc_hpf | Button index | 0-3 | 0 | [OFF, 80Hz, 160Hz, 300Hz] |
| comp_bypass | Button | bool | False |

**Master Limiter:**
| Field | Widget | Range | Default |
|-------|--------|-------|---------|
| limiter_ceiling | Slider | 0-60 | 60 | Maps to -6..0dB |
| limiter_bypass | Button | bool | False |

**Schema:**
```python
@dataclass
class MasterState:
    # Existing
    volume: float = 0.8
    # EQ
    eq_hi: int = 200
    eq_mid: int = 200
    eq_lo: int = 200
    eq_hi_kill: bool = False
    eq_mid_kill: bool = False
    eq_lo_kill: bool = False
    eq_locut: bool = False
    eq_bypass: bool = False
    # Compressor
    comp_threshold: int = 200
    comp_ratio: int = 1
    comp_attack: int = 1
    comp_release: int = 1
    comp_makeup: int = 0
    comp_sc_hpf: int = 0
    comp_bypass: bool = False
    # Limiter
    limiter_ceiling: int = 60
    limiter_bypass: bool = False
```

---

### Phase 3: Modulation Sources

**Per mod slot (×4):**
| Field | Widget | Range | Default |
|-------|--------|-------|---------|
| generator_id | CycleButton | string | "" | Format: "mod:lfo", "mod:sloth", or "" |
| params | Sliders | float[5] | [0.5 × 5] | Normalized 0-1 |
| output_wave | CycleButton ×4 | int[4] | [0, 0, 0, 0] | Waveform index |
| output_phase | CycleButton ×4 | int[4] | [0, 0, 0, 0] | Phase index |
| output_polarity | CycleButton ×4 | int[4] | [0, 0, 0, 0] | 0=UNI, 1=BI, 2=INV |

**Schema:**
```python
@dataclass
class ModSlotState:
    generator_id: str = ""  # Format: "mod:stem" e.g. "mod:lfo", "mod:sloth"
    params: list[float] = field(default_factory=lambda: [0.5] * 5)
    output_wave: list[int] = field(default_factory=lambda: [0] * 4)
    output_phase: list[int] = field(default_factory=lambda: [0] * 4)
    output_polarity: list[int] = field(default_factory=lambda: [0] * 4)

@dataclass
class ModSourcesState:
    slots: list[ModSlotState] = field(default_factory=lambda: [ModSlotState() for _ in range(4)])
```

---

### Phase 4: Modulation Routing

**Per connection:**
| Field | Type | Range | Description |
|-------|------|-------|-------------|
| source_bus | int | 0-15 | Which mod bus |
| target_slot | int | 0-7 | Which generator slot (0-indexed) |
| target_param | str | enum | "FRQ", "CUT", "RES", "ATK", "DEC", "P1".."P5" |
| amount | float | 0.0-1.0 | Modulation depth |
| polarity | int | 0-2 | 0=UNI, 1=BI, 2=INV |
| offset | float | -1.0 to +1.0 | Bipolar offset in normalized space |

**Offset semantics:**
- Range: -1.0 to +1.0 (bipolar, 0.0 = no offset)
- Applied in normalized parameter space; `dst_norm` is clamped to 0..1
- `src_norm` may be uni (0..1) or bi (-1..+1) depending on polarity mode
- Applied post-polarity

**Modulation formula (all in normalized space):**
```
src_norm = outputTransform(bus_value, output_polarity)
  # UNI: returns 0..1
  # BI: returns -1..+1  
  # INV: sign flip after mapping
src_norm = applyConnectionPolarity(src_norm, connection_polarity)
dst_norm = base_norm + (src_norm * amount) + offset
dst_norm = clamp(dst_norm, 0, 1)
# Then map dst_norm to actual parameter units (Hz, ms, etc)
```

**Schema:**
```python
@dataclass
class ModConnection:
    source_bus: int
    target_slot: int  # 0-7 (0-indexed)
    target_param: str
    amount: float = 0.5
    polarity: int = 0  # 0=UNI, 1=BI, 2=INV
    offset: float = 0.0  # -1.0 to +1.0

@dataclass 
class ModRoutingState:
    connections: list[ModConnection] = field(default_factory=list)
```

---

### Phase 5: FX Chain (Deferred)

*Defer until FX system stabilizes.*

---

## Updated PresetState Schema (v2)

```python
@dataclass
class PresetState:
    # Metadata (preset_id and created are filled at SAVE time, not construction)
    version: int = 2
    mapping_version: int = 1  # For future UI→value curve changes
    preset_id: str = ""  # UUID, generated in PresetManager.save()
    name: str = "Untitled"
    created: str = ""  # ISO-8601 UTC, generated in PresetManager.save()
    
    # Generators (use generator_id format "pack:stem")
    slots: list[SlotState] = field(default_factory=lambda: [SlotState() for _ in range(8)])
    
    # Mixer (expanded)
    mixer: MixerState = field(default_factory=MixerState)
    
    # Global
    bpm: int = 120
    
    # Master (new)
    master: MasterState = field(default_factory=MasterState)
    
    # Modulation (new)
    mod_sources: ModSourcesState = field(default_factory=ModSourcesState)
    mod_routing: ModRoutingState = field(default_factory=ModRoutingState)
    
    def get_pack_id(self) -> str:
        """Derive pack_id from first non-empty audio slot (ignores mod:*)."""
        for slot in self.slots:
            if slot.generator_id and ':' in slot.generator_id:
                prefix = slot.generator_id.split(':')[0]
                if prefix != 'mod':  # Skip mod generators
                    return prefix
        return ""
    
    def get_all_pack_ids(self) -> set[str]:
        """Get all unique pack prefixes from audio slots (ignores mod:*)."""
        packs = set()
        for slot in self.slots:
            if slot.generator_id and ':' in slot.generator_id:
                prefix = slot.generator_id.split(':')[0]
                if prefix != 'mod':  # Skip mod generators
                    packs.add(prefix)
        return packs
```

**PresetManager.save() generates metadata:**
```python
import uuid
from datetime import datetime, timezone

class PresetManager:
    def save(self, state: PresetState, name: str = None) -> Path:
        # Generate metadata at save time (mutates state object)
        if not state.preset_id:
            state.preset_id = str(uuid.uuid4())
        state.created = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        if name:
            state.name = name
        # ... rest of save logic
```
*Note: save() mutates the state object. Tests should account for this.*

**SlotState update:**
```python
@dataclass
class SlotState:
    generator_id: str = ""  # Format: "pack:stem" e.g. "core:saw", "rlyeh:cthulhu"
    params: list[float] = field(default_factory=lambda: [0.5] * 10)
    filter_type: int = 0
    env_source: int = 0
    clock_rate: int = 6
    midi_channel: int = 0
```

---

## Validation Strategy

**Two modes:**

1. **Strict mode** (tests, CI): Raise exception on any invalid value
2. **Best-effort mode** (user load): Warn + clamp + default

```python
class PresetValidationError(Exception):
    pass

def validate_preset(data: dict, strict: bool = False) -> tuple[bool, list[str]]:
    errors = []
    warnings = []
    
    # ... validation logic ...
    
    if strict and (errors or warnings):
        raise PresetValidationError(errors + warnings)
    
    return len(errors) == 0, errors + warnings
```

**Structural validation:**
- `slots`: must be length 8
- `SlotState.params`: must be length 10
- `mixer.channels`: must be length 8
- `mod_sources.slots`: must be length 4
- `ModSlotState.params`: must be length 5
- `output_wave/phase/polarity`: must be length 4

**Range validation:**
- All floats: reject NaN/Inf
- All ints from JSON: accept integral floats with warning (`100.0` → `100`)
- `amount`: 0.0-1.0
- `offset`: -1.0 to +1.0
- `source_bus`: 0-15
- `target_slot`: 0-7
- `target_param`: must be in ["FRQ", "CUT", "RES", "ATK", "DEC", "P1", "P2", "P3", "P4", "P5"]
- `polarity`: 0-2
- `bpm`: 20-300
- Channel EQ: 0-200
- Master EQ: 0-400
- Gain index: 0-2
- Comp ratio: 0-3, attack: 0-2, release: 0-3, sc_hpf: 0-3
- Limiter ceiling: 0-60

**Mixed pack_id handling:**
- Strict mode: If `get_all_pack_ids()` returns more than one pack, raise error
- Best-effort mode: Warn, use `get_pack_id()` (first non-empty) or `""` if ambiguous

---

## Migration Strategy

**No v1 migration needed:** First presets were created today (Dec 20). No users have saved presets yet. We update schema directly to v2.

**Future migrations:** If needed later, use `version` field:
```python
if data.get("version", 1) < 2:
    # Future migration logic here
    pass
```

**Forward/backward compatibility rules:**
- Unknown fields: ignored (forward compat)
- Missing sections: defaulted (backward compat)

---

## Apply Order on Load

To prevent UI thrash and ensure dependencies exist:

1. **BPM / global clocks** - timing must be set first
2. **Pack selection** - derive from `get_pack_id()`, set UI dropdown
3. **Generator slots** - type + params
4. **Mixer channels** - volume, pan, EQ, sends
5. **Master section** - EQ, comp, limiter
6. **Mod sources** - create the modulators
7. **Mod routing** - last, references buses + targets

**Block signals** during set_state to prevent cascade updates.

---

## Round-Trip Test Definition

**Canonical form for comparison:**
To compare presets for equality (round-trip tests), use canonical form:
- Strip: `preset_id`, `created` (auto-generated metadata)
- Keep: `name` (user-facing, should persist)
- Compare remaining JSON

```python
def to_canonical(data: dict) -> dict:
    """Strip auto-generated metadata for comparison."""
    canonical = data.copy()
    canonical.pop('preset_id', None)
    canonical.pop('created', None)
    # Keep 'name' - it's user data that should persist
    return canonical

def presets_equal(a: dict, b: dict) -> bool:
    """Compare presets ignoring auto-generated metadata."""
    return to_canonical(a) == to_canonical(b)
```

---

## Implementation Order

| Phase | Scope | Files |
|-------|-------|-------|
| 1 | Channel strip (EQ, gain, sends, cuts) | preset_schema.py, mixer_panel.py |
| 2 | BPM + Master (EQ, comp, limiter) | preset_schema.py, master_section.py, bpm_display.py |
| 3 | Mod sources (4 slots + outputs) | preset_schema.py, modulator_grid.py |
| 4 | Mod routing (connections) | preset_schema.py, mod_routing_state.py |
| 5 | FX chain | Deferred |

**Per phase:**
1. Update schema dataclasses
2. Add get_state/set_state methods to widgets
3. Update validation
4. Add tests (strict mode)
5. Test save → quit → load cycle

---

## Files to Modify

| File | Changes |
|------|---------|
| `preset_schema.py` | Add new dataclasses, mapping_version, validation modes |
| `preset_manager.py` | Generate UUID/timestamp at save time |
| `mixer_panel.py` | Expand ChannelStrip get/set_state |
| `master_section.py` | Add get/set_state for EQ, comp, limiter |
| `modulator_grid.py` | Add get/set_state for mod sources |
| `mod_routing_state.py` | Add to_dict/from_dict for serialization |
| `main_frame.py` | Update _save_preset/_apply_preset, apply order |
| `bpm_display.py` | Add get_bpm/set_bpm if not present |
| `test_presets.py` | Tests for new state, round-trip tests, strict mode |

---

## Test Requirements

**Round-trip invariant tests (strict mode):**
- Save v2 → load v2 → save v2 → canonical form identical
- All slider values restored exactly
- Mod routing survives restart

**Validation tests:**
- Out-of-range values rejected in strict mode
- Out-of-range values clamped in best-effort mode
- NaN/Inf rejected
- Integral floats accepted with warning
- Mixed pack_ids rejected in strict mode
- Wrong params length rejected (slots: 10, mod: 5)

---

## Success Criteria

- [ ] Full session save/load works
- [ ] Mod routing survives restart
- [ ] preset_id generated at save time only
- [ ] created timestamp in ISO-8601 UTC at save time only
- [ ] pack_id derived correctly from slots
- [ ] Mixed pack_ids handled per validation mode
- [ ] All tests pass (strict mode)
- [ ] Round-trip test: save → quit → load → canonical form identical
- [ ] Apply order prevents UI glitches on load
