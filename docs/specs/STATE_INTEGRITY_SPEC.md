---
status: phase-1-complete
---
# State Integrity Hardening

## What

Eliminate the "whack-a-mole" pattern where every new feature silently breaks preset save/load. Replace the manual N-way field synchronization with auto-derived serialization and automated round-trip tests that catch drift at CI time.

## Invariants (Non-Negotiable)

**I1 — Schema identity:** `D == D.from_dict(D.to_dict())` field-by-field, for all hardened dataclasses (`SlotState`, `ChannelState`, `MasterState`).

**I2 — Save completeness:** The dict actually written into the preset file contains **all `SlotState` fields** (top-level + `params`) for every slot. No field is silently omitted.

**I3 — Full preset identity:** `PresetState.from_json(state.to_json())` preserves nested Slot + Channel + Master state for at least one slot exercising every high-churn feature (ARP, Euclidean, SEQ, analog stage).

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
`from_dict()` MUST ignore unknown keys to preserve backward/forward compatibility.

**Approach:** Use `dataclasses.fields()` introspection to auto-generate `to_dict()` and `from_dict()`, plus a small allow-list (`_PARAM_KEYS`) for fields that live under the nested `"params"` dict.

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
    seq_steps: list[dict] = field(default_factory=list)

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

**Goal:** Any field that doesn't survive `to_dict() → from_dict()` fails CI immediately. Enforces **I1** and **I3**.

**Policy:** Round-trip tests MUST auto-fill non-defaults for every dataclass field via introspection. Field-count guards are optional.

#### The autofill helper (mandatory)

The helper constructs a dataclass instance with **guaranteed non-default** values for every field, using `dataclasses.fields()` introspection. No manual updates needed when fields are added.

```python
from dataclasses import fields, MISSING
import dataclasses

def autofill_nondefaults(cls):
    """
    Construct an instance of dataclass `cls` with every field set to
    a deterministic non-default value. Used by round-trip tests to
    guarantee that new fields are automatically covered.
    """
    _NON_DEFAULTS = {
        float: 0.42,
        int: 7,
        bool: True,
        str: "test_value",
    }

    kwargs = {}
    for f in fields(cls):
        default = _get_default(f)
        ftype = f.type if isinstance(f.type, type) else _resolve_type(f.type)

        if ftype == bool:
            # Flip the default
            kwargs[f.name] = not default if isinstance(default, bool) else True
        elif ftype == float:
            kwargs[f.name] = default + 0.123 if isinstance(default, (int, float)) else 0.42
        elif ftype == int:
            kwargs[f.name] = default + 3 if isinstance(default, int) else 7
        elif ftype == str or f.name == "generator":
            kwargs[f.name] = f"test_{f.name}"
        elif ftype == list or "list" in str(f.type).lower():
            kwargs[f.name] = [{"test_key": f.name}]
        else:
            # Optional[str] and similar
            kwargs[f.name] = f"test_{f.name}"
    return cls(**kwargs)


def _get_default(f):
    """Extract the effective default from a dataclass field."""
    if f.default is not MISSING:
        return f.default
    if f.default_factory is not MISSING:
        return f.default_factory()
    return None


def _resolve_type(annotation) -> type:
    """Best-effort type resolution for simple annotations."""
    if annotation is None:
        return type(None)
    origin = getattr(annotation, '__origin__', None)
    if origin is not None:
        return origin  # e.g. list, dict
    if isinstance(annotation, str):
        _TYPE_MAP = {"float": float, "int": int, "bool": bool, "str": str}
        return _TYPE_MAP.get(annotation, str)
    return annotation
```

#### The schema key set helper (single definition, reused everywhere)

```python
def schema_keys(cls, param_keys=None):
    """
    Return the set of JSON keys that to_dict() must emit for dataclass `cls`.
    Used in round-trip tests AND save-time assertions — same definition,
    no divergence possible.
    """
    all_fields = {f.name for f in fields(cls)}
    if param_keys:
        return (all_fields - param_keys) | {"params"}
    return all_fields
```

#### Tests (in `tests/test_state_roundtrip.py`)

```python
"""
State round-trip tests — auto-fill based.

The autofill helper guarantees every dataclass field is set to a
non-default value. If a new field is added and to_dict/from_dict
don't handle it, the test fails automatically — no manual updates.
"""
import pytest
from dataclasses import fields
from src.presets.preset_schema import (
    SlotState, ChannelState, MasterState, PresetState, _PARAM_KEYS,
)
from tests.helpers.state_helpers import autofill_nondefaults, schema_keys


class TestSlotStateRoundTrip:
    def test_all_fields_survive(self):
        """I1: Every SlotState field round-trips through to_dict/from_dict."""
        original = autofill_nondefaults(SlotState)
        restored = SlotState.from_dict(original.to_dict())

        for f in fields(SlotState):
            orig_val = getattr(original, f.name)
            rest_val = getattr(restored, f.name)
            assert rest_val == orig_val, (
                f"SlotState.{f.name} didn't round-trip: "
                f"expected {orig_val!r}, got {rest_val!r}"
            )

    def test_to_dict_covers_all_schema_keys(self):
        """I2: to_dict() emits every schema key."""
        d = autofill_nondefaults(SlotState).to_dict()
        emitted = set(d.keys()) | set(d.get("params", {}).keys())
        expected = schema_keys(SlotState, _PARAM_KEYS)
        # Flatten: expected has "params" instead of individual param keys
        expected_flat = {f.name for f in fields(SlotState)}
        missing = expected_flat - emitted
        assert not missing, f"to_dict() missing keys: {missing}"


class TestChannelStateRoundTrip:
    def test_all_fields_survive(self):
        """I1: Every ChannelState field round-trips."""
        original = autofill_nondefaults(ChannelState)
        restored = ChannelState.from_dict(original.to_dict())
        for f in fields(ChannelState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"ChannelState.{f.name} didn't round-trip"


class TestMasterStateRoundTrip:
    def test_all_fields_survive(self):
        """I1: Every MasterState field round-trips."""
        original = autofill_nondefaults(MasterState)
        restored = MasterState.from_dict(original.to_dict())
        for f in fields(MasterState):
            assert getattr(restored, f.name) == getattr(original, f.name), \
                f"MasterState.{f.name} didn't round-trip"


class TestPresetStateRoundTrip:
    def test_full_preset_round_trips(self):
        """I3: Full PresetState with autofilled slot survives to_json/from_json."""
        state = PresetState(name="RoundTripTest", bpm=140)
        state.slots[0] = autofill_nondefaults(SlotState)
        state.mixer.channels[0] = autofill_nondefaults(ChannelState)

        restored = PresetState.from_json(state.to_json())

        for f in fields(SlotState):
            orig = getattr(state.slots[0], f.name)
            rest = getattr(restored.slots[0], f.name)
            assert rest == orig, f"PresetState.slots[0].{f.name} lost in round-trip"

        for f in fields(ChannelState):
            orig = getattr(state.mixer.channels[0], f.name)
            rest = getattr(restored.mixer.channels[0], f.name)
            assert rest == orig, f"PresetState.mixer.channels[0].{f.name} lost in round-trip"


class TestBackwardCompatibility:
    def test_old_preset_missing_new_keys(self):
        """Old preset JSON without new fields loads without error, gets defaults."""
        old_json = '{"version": 1, "name": "OldPreset", "slots": [{"generator": "FM", "params": {"frequency": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 4, "midi_channel": 1}], "mixer": {"channels": [], "master_volume": 0.8}}'
        preset = PresetState.from_json(old_json)
        slot = preset.slots[0]
        # New fields should have dataclass defaults, not crash
        assert slot.arp_enabled == False
        assert slot.euclid_enabled == False
        assert slot.analog_enabled == 0
        assert slot.seq_steps == []
```

**Why autofill is mandatory, not optional:** If a new field is added and the test doesn't set a non-default for it, the test passes silently (default → missing → default = equality). The autofill helper introspects `fields()` at runtime and guarantees every field gets a non-default value. New fields are covered automatically — no human update required.

**Field-count guards** are optional on top of autofill. They add an explicit "stop and think" moment but are not required for correctness.

---

### Phase 3: Save-path completeness (catch the preset_controller / widget gap)

**Concrete finding:** Slot schema fields can exist and round-trip correctly at the dataclass layer while still being silently dropped at save time if the UI export path doesn't include them.

Example failure mode:
- Feature fields exist in `SlotState` and are valid
- Preset save path collects state from UI using `GeneratorSlot.get_state()` and/or controller-side injection
- Some fields are not exported → `SlotState.from_dict()` receives missing keys → defaults apply → field reverts on load

This is the **second** major cause of "works live, doesn't persist" regressions.

Currently `GeneratorSlot.get_state()` does NOT include ARP, Euclidean, RST, or SEQ fields. Instead, `preset_controller._do_save_preset()` manually injects them by reaching into `arp_manager` and `motion_manager` (controller-side manual injection in `_do_save_preset()`). This is a second synchronization point that's easy to forget.

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

#### Option C: Save-time schema coverage assertion (permanent tripwire)

Add an assertion in `_do_save_preset()` that compares:
- `schema_keys(SlotState, _PARAM_KEYS)` vs keys emitted by the save-path dict (`top-level + params`)

Uses the **same `schema_keys()` helper** as the round-trip tests — single definition, no divergence possible.

If any schema fields are missing, fail loudly instead of writing a broken preset file. Saving is a *data integrity boundary* — silent data loss is worse than a crash.

```python
# In _do_save_preset(), after building slot_dict:
from tests.helpers.state_helpers import schema_keys
expected = {f.name for f in fields(SlotState)}
emitted = set(slot_dict.keys()) | set(slot_dict.get("params", {}).keys())
missing = expected - emitted
assert not missing, f"Save-path missing SlotState fields: {missing}"
```

**Required safety:** Until Option A is implemented, `_do_save_preset()` MUST assert schema coverage before writing. This is not optional — it is the tripwire that catches "works live, doesn't persist" at the moment it would create a corrupt file.

**Recommendation:** Option A for new development. It follows the principle that each component owns its own state. The preset controller becomes a thin orchestrator that just calls `get_state()` on each component and assembles the result. Option C is **required** as the safety net until Option A is complete.

---

## Acceptance Tests (must exist and pass)

| Test | Invariant | Enforces |
|------|-----------|----------|
| `test_slotstate_roundtrip_autofill()` | I1 | Every SlotState field survives to_dict→from_dict |
| `test_channelstate_roundtrip_autofill()` | I1 | Every ChannelState field survives to_dict→from_dict |
| `test_masterstate_roundtrip_autofill()` | I1 | Every MasterState field survives to_dict→from_dict |
| `test_to_dict_covers_all_schema_keys()` | I2 | to_dict() emits every schema field |
| `test_presetstate_json_roundtrip_feature_slot()` | I3 | Full preset with all high-churn features round-trips |
| `test_save_path_schema_coverage()` or save-time assertion | I2 | Save path emits all SlotState fields |
| `test_old_preset_missing_new_keys()` | compat | Old presets load without error, get defaults |

## Done When

- All acceptance tests above pass in CI.
- Preset save path exports all slot schema fields (either by consolidating into `GeneratorSlot.get_state()` or by Option C assertion).
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
**Delivers:** `SlotState`, `ChannelState`, `MasterState` all auto-serialize. Full round-trip test suite with autofill helper. Option C save-time assertion active.
**Risk:** Low. Output format unchanged. Old presets still load.
**Partial migration rule:** Phase 1 is complete only when **all three** dataclasses (Slot/Channel/Master) are migrated and tested. If only SlotState is auto-serialized but Channel/Master remain manual, you still have drift risk in mixer/master.
**Done when:** All I1/I2/I3 acceptance tests pass. Existing preset tests still pass. Save-time assertion is active in `_do_save_preset()`.

### Phase 2 — Save-path consolidation (Option A)
**Delivers:** `GeneratorSlot.get_state()` returns ALL slot fields including ARP/Euclidean/RST/SEQ. `preset_controller._do_save_preset()` contains **zero** per-feature field logic — only orchestration.
**Risk:** Medium. Requires wiring ARP/SEQ engine references into GeneratorSlot.
**Done when:** `_do_save_preset()` has no manual field injection. Controller calls `get_state()` and trusts the result. Round-trip tests still pass.

## The "Add a New Field" Checklist (after this work)

### Before (5 steps, error-prone)
1. Add field to dataclass
2. Add to `to_dict()`
3. Add to `from_dict()` with default
4. Add to `_validate_slot()` with range check
5. Add to widget `get_state()` AND preset_controller injection AND `set_state()`

### After (2 steps, test-enforced) — two-step workflow is NOT valid until Phase 2 save-path consolidation is green
1. Add field to dataclass (auto-serialized)
2. Add to `_validate_slot()` with range check (manual, domain-specific)

**Before Phase 2 is complete:** you still must ensure the save-path exports the field (widget `get_state()` or controller injection). The Option C save-time assertion will catch it if you forget — it will fail loudly on first preset save with the missing field named in the error.

**After Phase 2:** the two-step workflow is fully valid. The autofill round-trip test catches serialization drift, and the widget owns its own state so the save-path is automatically complete.

## Open Questions

- Do we want the `"params"` nesting long-term, or keep it permanently for backward compatibility and clarity?
- For Phase 2 save-path consolidation: should `GeneratorSlot` own references to ARP/SEQ/Euclid/RST state sources (preferred), or should the controller remain the assembler?
- After the high-churn three are hardened, should we extend auto-serialization + autofill to `ModSlotState`, `FXSlotsState`, and other stable dataclasses? (Recommended for consistency, but lower priority.)
