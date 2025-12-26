# CQD_Forge — Phased Delivery Plan

*Based on CQD_FORGE_SPEC.md v1.0 (FROZEN)*

---

## Overview

| | |
|---|---|
| Target | 10-20 packs (80-160 generators) |
| Sessions | 5-6 sessions |
| Spec | CQD_FORGE_SPEC.md v1.0 |
| New Methods | 5 (filling texture gap + expanding palette) |

---

## Phase 0: Method Expansion (Session 1 — Evening)

**Goal:** Fill the texture family gap and expand the synthesis palette before Forge begins.

### Current State

| Family | Code | Methods | Count |
|--------|------|---------|-------|
| Subtractive | `sub` | bright_saw, dark_pulse, noise_filtered, supersaw | 4 |
| FM | `fm` | simple_fm, feedback_fm, ratio_stack | 3 |
| Physical | `phys` | karplus, modal, bowed | 3 |
| Spectral | `spec` | additive | 1 |
| Texture | `tex` | — | **0** ❌ |

### New Methods to Add

| # | Method | Family | Tag | Character | Use Case |
|---|--------|--------|-----|-----------|----------|
| 1 | `granular_cloud` | tex | GRAIN | Diffuse, atmospheric, shimmering | Pads, beds, ambient washes |
| 2 | `dust_resonator` | tex | STOCH | Organic impulses, rain, crackle | Texture layers, organic motion |
| 3 | `wavefold` | sub | NL | West Coast, complex harmonics, metallic | Aggressive leads, evolving timbres |
| 4 | `formant` | phys | MODEL | Breathy, vocal, choir-like | Organic pads, human-ish sounds |
| 5 | `ring_mod` | fm | RM | Metallic, atonal, sci-fi, bells | Accents, sci-fi textures, inharmonic |

### After Expansion

| Family | Code | Methods | Count |
|--------|------|---------|-------|
| Subtractive | `sub` | bright_saw, dark_pulse, noise_filtered, supersaw, **wavefold** | 5 |
| FM | `fm` | simple_fm, feedback_fm, ratio_stack, **ring_mod** | 4 |
| Physical | `phys` | karplus, modal, bowed, **formant** | 4 |
| Spectral | `spec` | additive | 1 |
| Texture | `tex` | **granular_cloud, dust_resonator** | 2 |
| **Total** | | | **16** |

### Per-Method Deliverables

Each new method requires:

| File | Description |
|------|-------------|
| `imaginarium/methods/{family}/{method}.py` | Method class with axes, macros, SC generation |
| P1-P5 axis definitions | With label, tooltip, unit per IMAGINARIUM_CUSTOM_PARAMS_SPEC |
| Validation pass | `python -m imaginarium.validate_methods` exits 0 |

### Method Design Notes

#### 1. `granular_cloud` (tex)
- **Source:** Buffer or internal noise
- **P1-P5:** Density, grain size, pitch scatter, position jitter, shimmer
- **Character:** Clouds that can be sparse or dense, static or evolving

#### 2. `dust_resonator` (tex)
- **Source:** Dust impulses → resonant filter bank
- **P1-P5:** Density, decay, brightness, spread, pitch
- **Character:** Rain on glass, crackling fire, organic textures

#### 3. `wavefold` (sub)
- **Source:** Sine/tri → wavefolder → filter
- **P1-P5:** Fold amount, symmetry, drive, harmonics, thickness
- **Character:** Buchla-ish, rich harmonics from simple source

#### 4. `formant` (phys)
- **Source:** Impulse/noise → parallel formant filters
- **P1-P5:** Vowel, breathiness, pitch tracking, formant shift, chorus
- **Character:** Vocal pads, choir swells, breathy textures

#### 5. `ring_mod` (fm)
- **Source:** Two oscillators → ring modulation
- **P1-P5:** Mod ratio, mod depth, carrier shape, detune, balance
- **Character:** Bells, metallic hits, sci-fi textures

### Session Plan

| Time | Task |
|------|------|
| 0:00 | Review IMAGINARIUM_CUSTOM_PARAMS_SPEC requirements |
| 0:15 | Implement `granular_cloud` |
| 0:45 | Implement `dust_resonator` |
| 1:15 | Implement `wavefold` |
| 1:45 | Implement `formant` |
| 2:15 | Implement `ring_mod` |
| 2:45 | Run validation, fix any issues |
| 3:00 | Quick sound check in Noise Engine |

### Verification

```bash
# 1. Method validator (must pass for generation to work)
python -m imaginarium.validate_methods | cpb
# Expect: 16 methods, all PASS

# 2. Unit tests
pytest tests/test_imaginarium_custom_params.py -v | cpb
# Expect: All pass, test_all_methods_pass confirms count = 16

# 3. Quick sound check (manual)
# Load Noise Engine, run generate on test image, confirm new methods appear
```

### Exit Criteria

- [ ] 5 new method files created
- [ ] `python -m imaginarium.validate_methods` → 16/16 PASS
- [ ] `pytest tests/test_imaginarium_custom_params.py` → all pass
- [ ] Each method produces sound (quick manual test)
- [ ] Texture family no longer empty
- [ ] `SYNTHESIS_TECHNIQUES.md` updated with new methods in "Implemented" section

---

## Phase 1: Tooling & Validation Setup (Session 2, Part A)

**Goal:** Ensure we can validate packs before generating at scale.

### Deliverables

| Item | Description |
|------|-------------|
| `tools/forge_validate.py` | Contract + safety gate checker for Forge packs |
| `tools/forge_template.scd` | SynthDef template with correct arg signature |
| Validation test | Run against one existing pack to confirm tooling works |

### Validation Script Requirements

From spec §3.4:

```python
# Contract checks
- Bus arguments match spec (freqBus, cutoffBus, etc.)
- Helper functions used (~ensure2ch, ~multiFilter, ~envVCA)
- Post-chain order correct
- Custom buses read correctly

# Safety gates
- Silence: RMS > -60 dBFS over 3s
- Clipping: Peak < -0.3 dBFS
- DC offset: abs(mean) < 0.01
- Runaway: Peak growth < +6 dB over 10s

# Determinism
- Same seed → identical SHA-256 hash (3s @ 48kHz)
```

### Verification

```bash
python tools/forge_validate.py packs/rlyeh/ | cpb
# Should output: PASS for existing pack
```

### Exit Criteria

- [ ] Validation script exists and runs
- [ ] One existing pack passes all checks
- [ ] Template SynthDef compiles in SC

---

## Phase 2: First Batch — Design Sheets (Session 2, Part B)

**Goal:** Process first 5 images, create design sheets only.

### Input

Gareth provides 5 images for first batch.

### Process Per Image

1. **Claude analyzes image:**
   - Mood / emotional tone
   - Visual texture → sonic texture
   - Color palette → tonal quality
   - Movement / energy level
   - Theme / narrative

2. **Claude produces design sheet:**

```markdown
## Pack: {pack_id}
Image: [description]
Mood: [one line]
Theme: [one line]

| Slot | Name | Method | Family | Role | P1 | P2 | P3 | P4 | P5 |
|------|------|--------|--------|------|----|----|----|----|-----|
| 1 | ... | ... | sub | bed | ... | ... | ... | ... | ... |
| 2 | ... | ... | phys | accent | ... | ... | ... | ... | ... |
...
```

3. **Gareth reviews and approves** (or requests changes)

### Balance Targets (from spec §3.2)

| Constraint | Requirement |
|------------|-------------|
| Roles | Must have bed + accent; prefer all 4 roles |
| Families | Max 3 from same family; min 2 families |
| Spectral | Mix of dark and bright |

### Deliverables

| Item | Count |
|------|-------|
| Design sheets | 5 (one per image) |
| Approval status | Per sheet |

### Exit Criteria

- [ ] 5 design sheets created
- [ ] All sheets meet balance targets
- [ ] Gareth has approved designs (or provided feedback)

---

## Phase 3: First Batch — Generation (Session 3, Part A)

**Goal:** Generate files for approved designs from Phase 2.

### Per Pack Output

```
packs/{pack_id}/
├── manifest.json
└── generators/
    ├── {generator_id}.json
    ├── {generator_id}.scd
    └── ... (8 generators)
```

### Generation Checklist (per generator)

- [ ] JSON has all required fields (generator_id, name, synthdef, custom_params[5], output_trim_db, midi_retrig, pitch_target)
- [ ] SynthDef name = `forge_{pack_id}_{generator_id}`
- [ ] Custom params have evocative labels + themed tooltips
- [ ] Defaults reproduce intended sound

### Validation Run

```bash
for pack in packs/forge_*; do
    python tools/forge_validate.py "$pack"
done | cpb
```

### Deliverables

| Item | Count |
|------|-------|
| Complete packs | 5 |
| Validation reports | 5 (all PASS) |

### Exit Criteria

- [ ] All 5 packs pass validation
- [ ] Files committed to repo
- [ ] Ready for listening test

---

## Phase 4: First Batch — Listening Test (Session 3, Part B)

**Goal:** Verify packs sound good and inspire music-making.

### Test Protocol

Per pack:
1. Load pack in Noise Engine
2. Play each generator individually
3. Test P1-P5 sliders — do they affect sound meaningfully?
4. Layer 3-4 generators — does it feel cohesive?
5. Rate: ✓ Ship / ⚠ Needs tweaks / ✗ Redesign

### Feedback Capture

```markdown
## Pack: {pack_id}
Overall: ✓ / ⚠ / ✗

| Generator | Sound | P1-P5 | Notes |
|-----------|-------|-------|-------|
| gen_1 | ✓ | ✓ | |
| gen_2 | ⚠ | ✓ | Too quiet |
...
```

### Exit Criteria

- [ ] All 5 packs tested
- [ ] Issues documented
- [ ] Ship/tweak/redesign decision per pack

---

## Phase 5: Second Batch (Session 4)

**Goal:** Process remaining 5-15 images.

### Workflow

Same as Phases 2-4, but batched more aggressively:

| Step | Approach |
|------|----------|
| Design | All remaining images → design sheets |
| Approval | Batch review (faster) |
| Generation | Parallel generation |
| Validation | Automated batch run |
| Listening | Sample-based (not exhaustive) |

### Stretch Target

| Batch | Images | Packs |
|-------|--------|-------|
| First | 5 | 5 |
| Second | 5-10 | 5-10 |
| Stretch | 5 | 5 |
| **Total** | **10-20** | **10-20** |

---

## Phase 6: Polish & Ship (Session 5)

**Goal:** Final fixes, documentation, ship.

### Tasks

| Task | Effort |
|------|--------|
| Fix any validation failures from Phase 5 | Variable |
| Address listening test feedback | 1-2 hr |
| Update pack catalog/documentation | 30 min |
| Final git cleanup and tag | 15 min |

### Exit Criteria

- [ ] All packs pass validation
- [ ] All packs pass listening test
- [ ] Documentation updated
- [ ] Tagged for release

---

## Session Allocation Summary

| Session | Duration | Phases | Output |
|---------|----------|--------|--------|
| 1 (Evening) | 3 hr | 0 | 5 new methods (texture family + palette expansion) |
| 2 | 2-3 hr | 1 + 2 | Tooling ready, 5 design sheets approved |
| 3 | 3-4 hr | 3 + 4 | 5 packs generated + tested |
| 4 | 3-4 hr | 5 | 5-15 more packs |
| 5 | 2 hr | 6 | Polish + ship |

**Total: 5 sessions → 10-20 packs (with 16 methods available)**

---

## Dependencies

| Dependency | Status | Needed By |
|------------|--------|-----------|
| Images from Gareth | ❓ | Phase 2 |
| 5 new methods | 🔨 Build | Phase 0 (tonight) |
| Forge validation tooling | 🔨 Build | Phase 1 |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| New method implementation issues | Phase 0 is isolated; won't block Forge if delayed |
| Validation failures at scale | Fix tooling in Phase 1, not Phase 5 |
| Listening tests reveal design issues | Allow 20% rework budget in Phase 6 |
| Image batch smaller than expected | 10 packs is minimum viable, 20 is stretch |

---

## Quick Reference: Key Spec Sections

| Topic | Spec Section |
|-------|--------------|
| Per-image process | §3 |
| Naming rules | §4 |
| Pack manifest schema | §5.1 |
| Generator JSON schema | §5.2 |
| Family enum | §6 |
| P1-P5 rules | §7 |
| Safety gates | §3.4 |
| Determinism contract | §3.4 |

---

## Tonight's Session: Phase 0

**Focus:** Add 5 new synthesis methods

| Method | Family | Time Est |
|--------|--------|----------|
| `granular_cloud` | tex | 30 min |
| `dust_resonator` | tex | 30 min |
| `wavefold` | sub | 30 min |
| `formant` | phys | 30 min |
| `ring_mod` | fm | 30 min |
| Validation + testing | — | 30 min |

**Total: ~3 hours**

*Ready to start?*
