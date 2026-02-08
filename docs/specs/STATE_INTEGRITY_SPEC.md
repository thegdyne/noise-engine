---
status: draft
---
# State Integrity Hardening

## What

Eliminate the "whack-a-mole" pattern where every new feature silently breaks preset save/load. Replace the manual N-way field synchronization with auto-derived serialization and automated round-trip tests that catch drift at CI time.

## Why

40% of all commits (86 of 215) are fixes or reverts. The dominant pattern:

1. New feature adds a field (e.g. `analog_enabled`, `euclid_k`, `rst_rate`)
2. Field works live because the widget/engine handles it
3. Field is missing from one or more of: `to_dict()`, `from_dict()`, `_validate_slot()`, `get_state()`, `set_state()`
4. User saves a preset → loads it later → new setting silently reverts to default
5. Separate debugging session to find and fix the gap

This happens because every field must be manually added to **5 separate locations** that have no automated consistency check:

| Location | Purpose | File |
|----------|---------|------|
| Dataclass field | Definition + default | `preset_schema.py` |
| `to_dict()` | Serialize to JSON | `preset_schema.py` |
| `from_dict()` | Deserialize from JSON | `preset_schema.py` |
| `_validate_slot()` | Validation | `preset_schema.py` |
| `_do_save_preset()` | Collect from UI | `preset_controller.py` |

Adding a field to one but not all five is the single most repeated bug.

## How

Three changes, ordered by impact. Each is independently useful.

---

### Phase 1: Auto-derived serialization (kill the boilerplate)

**Goal:** Adding a new field = adding ONE line (the dataclass field). No more manual `to_dict`/`from_dict` sync.

**Approach:** Use `dataclasses.fields()` introspection to auto-generate `to_dict()` and `from_dict()`, with a small metadata annotation for fields that nest under `"params"`.

```python
from dataclasses import dataclass, field, fields

# Marker for fields that serialize under the "params" sub-dict
_PARAM_KEYS = frozenset([
    "frequency", "cutoff", "resonance", "attack", "decay",
    "custom_0", "custom_1", "custom_2", "custom_3", "custom_4",
])

@dataclass
class SlotState:
    generator: Optional[str] = None
    frequency: float = 0.5
    cutoff: float = 1.0
    # ... all fields defined ONCE ...
    analog_enabled: int = 0
    analog_type: int = 0

    def to_dict(self) -> dict:
        result = {}
        params = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if f.name in _PARAM_KEYS:
                params[f.name] = val
            elif isinstance(val, list):
                result[f.name] = list(val)  # defensive copy
            else:
                result[f.name] = val
        result["params"] = params
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SlotState":
        params = data.get("params", {})
        kwargs = {}
        for f in fields(cls):
            if f.name in _PARAM_KEYS:
                kwargs[f.name] = params.get(f.name, f.default)
            elif f.name == "seq_steps":
                kwargs[f.name] = list(data.get(f.name, []))
            else:
                default = f.default if f.default is not dataclasses.MISSING else f.default_factory()
                kwargs[f.name] = data.get(f.name, default)
        return cls(**kwargs)
```

**Apply to:** `SlotState`, `ChannelState`, `MasterState` — the three classes where fields are added most frequently.

**NOT applying to:** Nested composite classes (`FXState`, `ModSourcesState`, etc.) which have stable schemas and complex `from_dict` logic (backward compat migrations). Leave those hand-written.

**Backward compatibility:** Output JSON format is identical. Old presets load fine (missing fields get dataclass defaults). No version bump needed.

**Validation:** `_validate_slot()` stays hand-written. Validation rules (ranges, types) can't be auto-derived from the dataclass — they require explicit domain knowledge. But with auto-serialization, the validator is the ONLY place that needs manual updates beyond the field definition itself: 5 sync points → 2.

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

**The field count guard:** Forces the developer to update the test when adding fields. The test failure message tells them exactly what to do.

---

### Phase 3: Save-path audit test (catch the preset_controller gap)

**Problem found:** `GeneratorSlot.get_state()` does NOT include ARP, Euclidean, RST, or SEQ fields. Instead, `preset_controller._do_save_preset()` manually injects them by reaching into `arp_manager` and `motion_manager` (lines 96-133). This is a second synchronization point that's easy to forget.

**Two options (choose one):**

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

**Recommendation:** Option A for new development. It follows the principle that each component owns its own state. The preset controller becomes a thin orchestrator that just calls `get_state()` on each component and assembles the result.

---

## Scope

**In scope:**
- Auto-derive `to_dict`/`from_dict` for `SlotState`, `ChannelState`, `MasterState`
- Round-trip tests for all state dataclasses
- Field-count guard tests
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

Step 1 failure mode: if you forget, the field count guard test fails immediately with a message telling you to update the test. If you update the count but not the test values, the round-trip test fails. You cannot ship a broken field.

## Open Questions

- Should auto-serialization extend to `ModSlotState` and FX dataclasses, or keep those hand-written given their stability?
- For Phase 2 (Option A), should GeneratorSlot receive its ARP engine at construction time, or via a late-binding setter?
- Should we add a CI step that runs `test_state_roundtrip.py` specifically on any PR that touches `preset_schema.py`?
