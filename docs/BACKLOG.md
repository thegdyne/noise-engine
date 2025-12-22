# Noise Engine Backlog

*Updated: December 21, 2025*

---

## Now
- [ ] Expand Presets — add channel EQ, BPM, master settings to preset schema

## Next (spec approved, ready to plan)
- [ ] Cross-Platform Testing — Windows & Linux compatibility
- [ ] Integration Tests — tests that boot SuperCollider

---

## Imaginarium

**Module:** `imaginarium/`

### Phase 1: Core Pipeline ✅ COMPLETE
- [x] Image → SoundSpec extraction (brightness, noisiness)
- [x] Sobol quasi-random candidate generation (32 candidates)
- [x] NRT SuperCollider rendering
- [x] Safety gates (silence, clipping, DC offset)
- [x] librosa feature extraction
- [x] Fit scoring against target SoundSpec
- [x] Farthest-first diversity selection
- [x] Pack export (Noise Engine-compliant)

### Phase 2a: Enhanced Analysis ✅ COMPLETE
- [x] 6-dimensional SoundSpec (brightness, noisiness, warmth, saturation, contrast, density)
- [x] Method affinity biasing (image characteristics → method multipliers)
- [x] 14 synthesis methods across 4 families:
  - Subtractive: bright_saw, dark_pulse, noise_filtered, supersaw
  - FM: simple_fm, feedback_fm, ratio_stack, ring_mod, hard_sync
  - Physical: karplus, modal, bowed, formant
  - Spectral: additive

### Phase 2b: Spatial Analysis ✅ COMPLETE
- [x] 4×4 tile feature extraction (edges, texture, orientation)
- [x] Role assignment (accent/foreground/motion/bed)
- [x] Quality gating with fallback to global selection
- [x] Role-based candidate selection (audio features + tags)
- [x] Soft family diversity penalty (prevents single-family dominance)
- [x] CLI: `spatial-preview` command and `--spatial` flag
- [x] 72 tests passing

### Phase 2 Backlog
- [ ] Make `--spatial` the default (currently opt-in)
- [ ] A/B listening tests: spatial vs global selection
- [ ] Quantile-based floors (replace fixed thresholds)
- [ ] Per-role SoundSpec generation (targeted candidate pools)
- [ ] Layer mix defaults (gain/pan/EQ hints per role)

### Phase 3: Extended Input (future)
- [ ] Text → SoundSpec (NLP keywords to parameters)
- [ ] Audio → SoundSpec (analyze reference audio)

### Ideas
- Foreground detection for soft-edge/painterly images
- Adaptive pool sizing based on safety pass rate
- Archive/novelty filtering (skip similar to previous packs)

---

## Cross-Platform Testing

**Goal:** Ensure Noise Engine runs on Windows and Linux, not just macOS.

**Tasks:**
- [ ] Recruit Windows tester (Discord?)
- [ ] Recruit Linux tester (Discord?)
- [ ] Document platform-specific setup (SC paths, Python env)
- [ ] Test PyQt5 rendering on Windows
- [ ] Test PyQt5 rendering on Linux (X11/Wayland)
- [ ] Verify OSC communication works cross-platform
- [ ] Check file paths (presets dir, pack loading)
- [ ] Create Windows install guide
- [ ] Create Linux install guide

**Known Risks:**
- SuperCollider paths differ per OS
- Audio device APIs vary (CoreAudio vs WASAPI vs ALSA/Jack)
- Font rendering may differ
- Keyboard shortcuts (Cmd vs Ctrl)

---

## Needs Spec (Large/Medium)
- [ ] MIDI Learn
- [ ] Mod Matrix Expansion
- [ ] SC State Sync on Restart

---

## Mopup (Small — just do it)
- [ ] UI font audit — improve visibility across all labels
- [ ] Empty mod state polish

---

## Ideas (not committed)
- Keyboard Mode (CMD+K)
- Filter improvements (ladder, MS-20, etc)
- Eurorack send/return
- Generator waveform display
- Performance profiling
- Per-generator transpose
- Multitimbral mode

---

## Done (recent)
- ✅ **Imaginarium Phase 2b** — Spatial analysis, role-based selection (Dec 21)
- ✅ **Imaginarium Phase 2a** — 6D analysis, 14 methods, method affinity (Dec 21)
- ✅ **Imaginarium Phase 1** — Image → 8 diverse generators pipeline
- ✅ Preset System — Save/Load with Ctrl+S/O (Dec 20)
- ✅ Generator Envelope Compliance — All 16 pack generators fixed (Dec 20)
- ✅ Doc Reorganization — archive/, ideas/, demos/ (Dec 20)
- ✅ Pack System — Phase 1-3 complete
- ✅ FX System v1 — Inline FX strip with HEAT, ECHO, REVERB, FILTER
- ✅ TURBO presets (INI/T1/T2) for all FX modules
- ✅ Channel strips (volume, pan, mute, solo, EQ)
- ✅ Master section (fader, meters, EQ, compressor, limiter)
- ✅ Mod Matrix — 16×40 routing grid
- ✅ Mod Sources — LFO + Sloth
- ✅ 53 generators total
- ✅ CI/CD pipeline (280 tests)

---

## Web-Based Manual
- [ ] Create documentation website for Noise Engine
- Consider: GitHub Pages, MkDocs, or simple HTML
- Sections: Getting started, Generators, Packs, Modulation, MIDI, API reference
- Include screenshots, audio examples
- Auto-generate generator list from pack manifests

## FX System v1.1
- [ ] P1: State sync on reconnect - create _sync_master_state() method
- [ ] P2: fx_window.py uses hardcoded OSC paths - refactor to use OSC_PATHS
- [ ] P2: master_passthrough LR4 comment doesn't match implementation

## FX System Future
- [ ] Per-channel echo/verb send knobs in mixer strip
- [ ] Reverb pre-delay parameter
- [ ] FX audio tuning (adjust default values, ranges, response curves)


## Preset Pack Integration (SPEC IMPLEMENTED, CODE MISSING)

**Spec:** PACK_SYSTEM_SPEC.md §7.1-7.4  
**Status:** Spec approved, implementation incomplete  
**Priority:** High — blocks Imaginarium preset workflow

### Problem
Presets with a `"pack"` field don't auto-switch to that pack on load. User must manually select pack first, then load preset. This breaks the Imaginarium workflow where generated packs include a ready-to-load preset.

### Current State
- `PresetState` (preset_schema.py) has no `pack` field
- `_apply_preset` (main_frame.py) doesn't read/handle pack field
- Imaginarium exports presets with `"pack": "pack-name"` but it's ignored

### Required Changes

**1. preset_schema.py — Add pack field to PresetState**
```python
@dataclass
class PresetState:
    version: int = PRESET_VERSION
    mapping_version: int = MAPPING_VERSION
    name: str = ""
    pack: Optional[str] = None  # ADD: None = Core, string = pack_id
    slots: List[SlotState] = ...
```

Update `to_dict()`:
```python
def to_dict(self) -> Dict:
    return {
        "version": self.version,
        "pack": self.pack,  # ADD
        ...
    }
```

Update `from_dict()`:
```python
@classmethod
def from_dict(cls, data: Dict) -> "PresetState":
    return cls(
        pack=data.get("pack"),  # ADD
        ...
    )
```

**2. main_frame.py — Handle pack switching in _apply_preset**
```python
def _apply_preset(self, state: PresetState):
    """Apply preset state to all components."""
    from src.config import PACKS, set_current_pack
    
    # Handle pack switching FIRST (before loading slots)
    pack_id = state.pack
    if pack_id:
        if pack_id in PACKS:
            # Switch pack (this resets all slots to Empty)
            self.pack_selector.set_pack(pack_id)  # or direct call
        else:
            logger.warning(f"Pack '{pack_id}' not found, using Core")
            pack_id = None
    else:
        # Preset is for Core generators
        self.pack_selector.set_pack(None)
    
    # NOW apply slot states (after pack is loaded)
    for i, slot_state in enumerate(state.slots):
        ...
```

**3. main_frame.py — Include pack in _save_preset**
```python
def _save_preset(self):
    from src.config import get_current_pack
    
    state = PresetState(
        name=name,
        pack=get_current_pack(),  # ADD
        ...
    )
```

**4. Validation (preset_schema.py)**
Update `validate_preset()` to handle pack field:
```python
# Pack field is optional, but if present must be string or None
pack = data.get("pack")
if pack is not None and not isinstance(pack, str):
    errors.append("pack must be string or null")
```

### Test Cases
- [ ] Load preset with `pack: "pizza-spatial"` → pack switches, generators load
- [ ] Load preset with `pack: null` → stays on Core
- [ ] Load preset with missing pack field → stays on current pack (backward compat)
- [ ] Load preset with `pack: "nonexistent"` → warning, falls back to Core
- [ ] Save preset while on pack → `pack` field included in JSON
- [ ] Save preset while on Core → `pack: null` in JSON

### Files to Modify
| File | Changes |
|------|---------|
| `src/presets/preset_schema.py` | Add `pack` field to PresetState, update to_dict/from_dict |
| `src/gui/main_frame.py` | Pack switching in `_apply_preset`, include pack in `_save_preset` |
| `src/gui/pack_selector.py` | May need `set_pack(pack_id)` method if not exists |


## CLI Enhancement
- [ ] Show spatial role grid in generate output when --spatial used (like spatial-preview does)


---

## Imaginarium Preset Defaults Reference

**Location:** `imaginarium/export.py` (around line 145-165)

When Imaginarium generates a pack, it also creates a preset file with these default param values:

| Param | Value | Meaning |
|-------|-------|---------|
| frequency | 0.5 | Mid-range |
| cutoff | 1.0 | Filter fully open |
| resonance | 0.0 | No resonance |
| attack | 0.0 | Snappiest attack |
| decay | 0.76 | ~2 seconds |
| custom_0-4 | 0.5 | Mid-range defaults |

**To change defaults:** Edit the `preset = {...}` block in `export.py` after the manifest write.

**Decay curve reference:**
- 0.73 → ~1.0s
- 0.76 → ~2.0s  
- 0.80 → ~2.5s
- 0.85 → ~4.0s
- 0.90 → ~5.5s

