---
status: draft
---
# State Integrity Hardening

## What

Eliminate the "whack-a-mole" pattern where every new feature silently breaks preset save/load. Replace the manual N-way field synchronization with auto-derived serialization and automated round-trip tests that catch drift at CI time.

## Why

~40% of all commits are fixes/reverts. The dominant regression pattern:

1. A new feature adds a state field (e.g. `analog_enabled`, `euclid_k`, `rst_rate`)
2. The feature works live (widget/engine path is correct)
3. The field is missing from one or more state sync points
4. Preset save/load silently drops the field → it reverts to default later
5. A separate debugging session is needed to find and patch the gap

This happens for **structural** reasons:

### Root Cause 1 — State is defined in N places that must be kept in sync

Every slot-level field effectively exists in 4–5 locations that must all agree:

| Location | Purpose | File |
|----------|---------|------|
| Dataclass field | Definition + default | `src/presets/preset_schema.py` |
| `to_dict()` | Serialize to JSON | `src/presets/preset_schema.py` |
| `from_dict()` | Deserialize from JSON | `src/presets/preset_schema.py` |
| `_validate_slot()` | Domain validation | `src/presets/preset_schema.py` |
| Save-path collection | Collect UI state | `src/gui/controllers/preset_controller.py` and/or `GeneratorSlot.get_state()` |

When a feature lands, missing *any one* of these produces a "works live, doesn't persist" bug.

### Root Cause 2 — Silent failures mask regressions

* `from_dict()` commonly fills missing values with defaults (so missing fields don't error)
* GUI widgets can update visuals without guaranteeing "state export" is updated
* SuperCollider coercion (e.g. `nil → 0`) can hide missing/incorrect values
* There is currently no test asserting "save then load is identical" for all fields

### Root Cause 3 — No automated sync check

There is no CI test that enforces:

* Every dataclass field is actually serialized/deserialized (round-trip)
* The save-path export covers every schema field (widget/controller completeness)

So regressions are only found manually during later use.

## How

Three changes, ordered by impact. Each is independently useful.

---

### Phase 1: Auto-derived serialization (kill the boilerplate)

**Goal:** Adding a new field = adding ONE line (the dataclass field). No more manual `to_dict`/`from_dict` sync.

**Key contract:** Dataclass defaults are the **single source of truth**.
`from_dict()` MUST start from `cls()` (defaults) and overlay provided keys. It MUST NOT maintain a separate "shadow default table", because that recreates drift.

**Approach:** Use `dataclasses.fields()` introspection to auto-generate `to_dict()` and `from_dict()`, with a small metadata annotation for fields that nest under `"params"`.

```python
from dataclasses import dataclass, field, fields
from typing import Optional, ClassVar, Set

# Keys that live under the nested "params" dict in JSON (backward compatible)
_PARAM_KEYS: Set[str] = {
    "frequency", "cutoff", "resonance", "attack", "decay",
    "custom_0", "custom_1", "custom_2", "custom_3", "custom_4",
}

@dataclass
class SlotState:
    # SSOT: defaults live here and only here
    generator: Optional[str] = None
    frequency: float = 0.5
    cutoff: float = 1.0
    # ...
    analog_enabled: int = 0
    analog_type: int = 0
    seq_steps: list = field(default_factory=list)

    # Optional: keep it as a class-level contract if you prefer
    PARAM_KEYS: ClassVar[Set[str]] = _PARAM_KEYS

    def to_dict(self) -> dict:
        """Serialize to preset JSON schema (backward compatible)."""
        d: dict = {"generator": self.generator, "params": {}}
        for f in fields(self):
            name = f.name
            if name == "generator":
                continue
            val = getattr(self, name)
            if name in self.PARAM_KEYS:
                d["params"][name] = val
            elif name == "seq_steps":
                d[name] = list(val)  # defensive copy
            elif isinstance(val, list):
                d[name] = list(val)  # defensive copy for any list field
            else:
                d[name] = val
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SlotState":
        """Deserialize using dataclass defaults as SSOT."""
        obj = cls()  # ← single source of defaults

        if "generator" in data:
            obj.generator = data.get("generator")

        params = data.get("params", {}) or {}
        for k in cls.PARAM_KEYS:
            if k in params:
                setattr(obj, k, params[k])

        for f in fields(obj):
            name = f.name
            if name == "generator" or name in cls.PARAM_KEYS:
                continue
            if name in data:
                if name == "seq_steps":
                    setattr(obj, name, list(data.get(name, [])))
                else:
                    setattr(obj, name, data.get(name))
        return obj
```

**Apply to:** `SlotState`, `ChannelState`, `MasterState` — the three classes where fields are added most frequently.

**NOT applying to:** Nested composite classes (`FXState`, `ModSourcesState`, etc.) which have stable schemas and complex `from_dict` logic (backward compat migrations). Leave those hand-written.

**Backward compatibility:** Output JSON format is identical. Old presets load fine (missing fields get dataclass defaults). No version bump needed.

**Validation:** `_validate_slot()` stays hand-written. Validation rules (ranges, types) can't be auto-derived from the dataclass — they require explicit domain knowledge. But with auto-serialization, the validator is the ONLY place that needs manual updates beyond the field definition itself: 5 sync points → 2 **(dataclass + validator)**, with the save-path completeness enforced by tests in Phase 3 / Phase 2.

---

### Phase 2: Round-trip tests (catch drift automatically)

**Goal:** Any field that doesn't survive `to_dict() → from_dict()` fails CI immediately.

**Tests to add (in `tests/test_state_roundtrip.py`):**

```python
"""
State round-trip tests.

These tests use NON-DEFAULT values for every field. If a field is added
to the dataclass but missing from to_dict/from_dict, the test fails
because the default will appear instead of the non-default test value.
"""

class TestSlotStateRoundTrip:
    def test_all_fields_survive(self):
        """Every SlotState field round-trips through to_dict/from_dict."""
        original = SlotState(
            generator="TestGen",
            frequency=0.123, cutoff=0.456, resonance=0.789,
            attack=0.111, decay=0.222,
            custom_0=0.333, custom_1=0.444, custom_2=0.555,
            custom_3=0.666, custom_4=0.777,
            filter_type=3, env_source=2, clock_rate=7,
            midi_channel=5, transpose=3, portamento=0.42,
            arp_enabled=True, arp_rate=5, arp_pattern=2,
            arp_octaves=3, arp_hold=True,
            euclid_enabled=True, euclid_n=12, euclid_k=7, euclid_rot=3,
            rst_rate=6,
            seq_enabled=True, seq_rate=4, seq_length=8, seq_play_mode=2,
            seq_steps=[{"step_type": 0, "note": 60, "velocity": 100}],
            analog_enabled=1, analog_type=2,
        )
        restored = SlotState.from_dict(original.to_dict())

        for f in fields(SlotState):
            orig_val = getattr(original, f.name)
            rest_val = getattr(restored, f.name)
            assert rest_val == orig_val, (
                f"SlotState.{f.name} didn't round-trip: "
                f"expected {orig_val!r}, got {rest_val!r}"
            )

    def test_field_count_matches_expectation(self):
        """Guard: adding a field without updating this test is caught."""
        EXPECTED_FIELDS = 30  # Update when adding fields
        actual = len(fields(SlotState))
        assert actual == EXPECTED_FIELDS, (
            f"SlotState has {actual} fields but test expects {EXPECTED_FIELDS}. "
            f"Update the test values AND this count."
        )

class TestChannelStateRoundTrip:
    def test_all_fields_survive(self):
        """Every ChannelState field round-trips."""
        original = ChannelState(
            volume=0.3, pan=0.7, mute=True, solo=True,
            eq_hi=150, eq_mid=80, eq_lo=120,
            gain=2,
            fx1_send=42, fx2_send=84, fx3_send=126, fx4_send=168,
            lo_cut=True, hi_cut=True,
        )
        restored = ChannelState.from_dict(original.to_dict())
        for f in fields(ChannelState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"ChannelState.{f.name} didn't round-trip"

class TestMasterStateRoundTrip:
    def test_all_fields_survive(self):
        """Every MasterState field round-trips."""
        original = MasterState(
            volume=0.6, meter_mode=1,
            heat_bypass=0, heat_circuit=2, heat_drive=150, heat_mix=100,
            filter_bypass=0, filter_f1=80, filter_r1=50,
            filter_f1_mode=1, filter_f2=120, filter_r2=30,
            filter_f2_mode=2, filter_routing=1, filter_mix=150,
            sync_f1=3, sync_f2=5, sync_amt=80,
            eq_hi=100, eq_mid=140, eq_lo=80,
            eq_hi_kill=1, eq_mid_kill=0, eq_lo_kill=1,
            eq_locut=1, eq_bypass=1,
            comp_threshold=200, comp_makeup=100, comp_ratio=2,
            comp_attack=3, comp_release=2, comp_sc=4, comp_bypass=1,
            limiter_ceiling=400, limiter_bypass=1,
        )
        restored = MasterState.from_dict(original.to_dict())
        for f in fields(MasterState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"MasterState.{f.name} didn't round-trip"

class TestPresetStateRoundTrip:
    def test_full_preset_round_trips(self):
        """Full PresetState with non-default values survives to_json/from_json."""
        state = PresetState(name="RoundTripTest", bpm=140)
        state.slots[0] = SlotState(
            generator="TestGen", frequency=0.9, arp_enabled=True,
            euclid_enabled=True, euclid_k=5, analog_type=3,
        )
        state.mixer.channels[0] = ChannelState(volume=0.3, mute=True)

        restored = PresetState.from_json(state.to_json())

        # Verify nested slot fields
        for f in fields(SlotState):
            orig = getattr(state.slots[0], f.name)
            rest = getattr(restored.slots[0], f.name)
            assert rest == orig, f"PresetState.slots[0].{f.name} lost in round-trip"
```

**Why non-default values matter:** If a field is missing from `to_dict()`, the default value still appears in `from_dict()` — so a test using defaults would pass even with a broken serializer. Non-default values make the test sensitive to actual round-trip fidelity.

**Optional guard (nice-to-have):** A field-count assertion can force deliberate test updates, but it's not strictly required if the test already sets non-default values for all fields and iterates via `fields(SlotState)`. The introspection loop is the real safety net — if a new field is added to the dataclass but not to the test constructor, the round-trip test will still catch it as long as the default differs from what `from_dict` would produce for a missing key (which it always does when the test uses non-defaults).

---

### Phase 3: Save-path completeness (catch the preset_controller / widget gap)

**Concrete finding:** Slot schema fields can exist and round-trip correctly at the dataclass layer while still being silently dropped at save time if the UI export path doesn't include them.

Example failure mode:
- Feature fields exist in `SlotState` and are valid
- Preset save path collects state from UI using `GeneratorSlot.get_state()` and/or controller-side injection
- Some fields are not exported → `SlotState.from_dict()` receives missing keys → defaults apply → field reverts on load

This is the **second** major cause of "works live, doesn't persist" regressions.

Currently `GeneratorSlot.get_state()` does NOT include ARP, Euclidean, RST, or SEQ fields. Instead, `preset_controller._do_save_preset()` manually injects them by reaching into `arp_manager` and `motion_manager` (lines 96-133). This is a second synchronization point that's easy to forget.

**Three options (choose one):**

#### Option A: Move state collection INTO the widgets (preferred)

Each widget/manager owns its own state completely. The preset controller just calls `get_state()` and trusts the result.

```python
# In GeneratorSlot.get_state():
def get_state(self) -> dict:
    state = {
        "generator": self.generator_type,
        "params": { ... },
        "filter_type": ...,
        # ... existing fields ...
        "analog_enabled": ...,
        "analog_type": ...,
    }
    # ARP/SEQ state injected by the slot's own references
    if self._arp_engine:
        arp = self._arp_engine.get_settings()
        state["arp_enabled"] = arp.enabled
        state["arp_rate"] = arp.rate_index
        # ... etc
    return state
```

This requires GeneratorSlot to hold a reference to its ARP/SEQ engine, which may need a small wiring change at init time. But it eliminates the scattered state collection in preset_controller.

#### Option B: Registry-based save-path test

Keep the current scattered collection but add a test that verifies completeness:

```python
def test_save_path_covers_all_slot_fields():
    """Every SlotState field is populated in _do_save_preset's output."""
    # This test creates a mock environment and calls the save path,
    # then verifies every SlotState field has a non-default value.
    # Requires mocking arp_manager, motion_manager, and generator_slots.
    ...
```

This is harder to write (needs extensive mocking) but doesn't require architectural changes.

#### Option C: Save-time schema coverage assertion (dev tripwire)

Add a dev-only assertion in `_do_save_preset()` that compares:
- `fields(SlotState)` vs keys emitted by the save-path dict (`top-level + params`)
If any schema fields are missing, fail loudly during development instead of producing a broken preset file.

This doesn't replace tests, but it turns silent data loss into an immediate, local failure.

**Recommendation:** Option A for new development. It follows the principle that each component owns its own state. The preset controller becomes a thin orchestrator that just calls `get_state()` on each component and assembles the result. Option C can be added as a quick safety net in the interim.

---

## Done When

- CI has round-trip tests that fail if any dataclass field is not serialized/deserialized.
- Preset save path exports all slot schema fields (either by consolidating into `GeneratorSlot.get_state()` or by an audited controller path).
- A regression like "ARP/Euclid/RST works live but is missing from presets" is caught before merge.

## Scope

**In scope:**
- Auto-derive `to_dict`/`from_dict` for `SlotState`, `ChannelState`, `MasterState`
- Round-trip tests for all state dataclasses (with non-default values)
- Document the "add a new field" checklist (2 steps instead of 5)

**Out of scope:**
- Refactoring the SuperCollider side (nil-coercion, global variable issues)
- GUI widget `set_state()` signal emission fixes (separate, per-widget work)
- Changing the preset JSON format (fully backward compatible)
- Auto-generating `_validate_slot()` (validation rules need domain knowledge)

## Phases

### Phase 1 — Auto-serialization + round-trip tests
**Delivers:** `SlotState`, `ChannelState`, `MasterState` auto-serialize. Full round-trip test suite.
**Risk:** Low. Output format unchanged. Old presets still load.
**Done when:** `pytest tests/test_state_roundtrip.py` passes, existing preset tests still pass.

### Phase 2 — Save-path consolidation (Option A)
**Delivers:** `GeneratorSlot.get_state()` returns ALL slot fields including ARP/Euclidean/RST/SEQ. `preset_controller._do_save_preset()` simplified to just call `get_state()`.
**Risk:** Medium. Requires wiring ARP/SEQ engine references into GeneratorSlot.
**Done when:** `_do_save_preset()` has no manual field injection. Round-trip test still passes.

## The "Add a New Field" Checklist (after this work)

### Before (5 steps, error-prone)
1. Add field to dataclass
2. Add to `to_dict()`
3. Add to `from_dict()` with default
4. Add to `_validate_slot()` with range check
5. Add to widget `get_state()` AND preset_controller injection AND `set_state()`

### After (2 steps, test-enforced)
1. Add field to dataclass (auto-serialized, round-trip test catches it)
2. Add to `_validate_slot()` with range check (manual, domain-specific)

Step 1 failure mode: if you add a field to the dataclass but don't serialize it, the round-trip test fails because the non-default test value won't survive. You cannot ship a broken field.

## Open Questions

- Do we want the `"params"` nesting long-term, or keep it permanently for backward compatibility and clarity?
- For Phase 2 save-path consolidation: should `GeneratorSlot` own references to ARP/SEQ/Euclid/RST state sources (preferred), or should the controller remain the assembler?
- Do we add the save-time schema coverage assertion in dev builds only, or always-on (fails fast in production too)?
- Should the same SSOT + round-trip approach be applied to *all* schema dataclasses (recommended), or only the high-churn ones first (`SlotState`, `ChannelState`, `MasterState`)?
