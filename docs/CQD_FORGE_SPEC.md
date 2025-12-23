# CQD_FORGE_SPEC.md — v1.0 (FROZEN)

*Pack Creation for Noise Engine Launch*

---

## Status

|         |                   |
| ------- | ----------------- |
| Version | v1.0              |
| Status  | **FROZEN**        |
| Date    | 2025-12-23        |
| Author  | Gareth + Claude   |
| AI1     | Approved          |
| AI2     | Approved          |

---

## 1. Goal

Create a library of diverse, expressive packs for Noise Engine's initial release.

**Input:** Batch of images from Gareth (10 minimum, 20 stretch)
**Output:** One pack per image, ready to ship

---

## 2. Pack Requirements

Each pack contains 8 generators that:

| Requirement | Detail |
|-------------|--------|
| Thematic coherence | All 8 fit the image's mood |
| Diversity | Varied families, roles, spectral range |
| Expressive P1-P5 | Evocative labels, themed tooltips |
| Playable | Sound good, inspire music-making |
| Validated | Pass contract + safety checks |

---

## 3. Per-Image Process

### 3.1 Read the Image

Claude looks at the image and notes:
- Mood / emotional tone
- Visual texture → sonic texture
- Color palette → tonal quality
- Movement / energy level
- Theme / narrative

### 3.2 Design 8 Generators

**Output: Design sheet (table format)**

| Slot | Name | Method | Family | Role | P1 | P2 | P3 | P4 | P5 |
|------|------|--------|--------|------|----|----|----|----|-----|

**Balance targets:**
- Roles: Must include **bed** and **accent** at minimum; prefer all 4 roles when image supports it
- Families: No more than 3 from same family; at least 2 families represented
- Spectral: Mix of dark and bright

**Method selection:**
- Use existing methods from catalog
- New methods only if 3+ images in batch have a clearly repeating unmet need
- New methods require explicit justification before creation

### 3.3 Generate Files

Claude creates generator files. Each generator SynthDef is a **parameterized instance** of an existing method template — the DSP topology comes from the method, Claude designs the P1-P5 configuration and defaults.

Output:
- Generator JSON files
- Generator SynthDef files
- Pack manifest

### 3.4 Validate

**Contract checks:**
- Bus arguments match spec
- Helper functions used (`~ensure2ch`, `~multiFilter`, `~envVCA`)
- Post-chain order correct
- Custom buses read correctly

**Safety gates:**

| Gate | Condition | Window |
|------|-----------|--------|
| Silence | RMS > -60 dBFS | 3 seconds |
| Clipping | Peak < -0.3 dBFS | Full render |
| DC offset | abs(mean) < 0.01 | Full render |
| Runaway | Peak growth < +6 dB | 10 seconds |

**Safety gate measurement methods (normative):**

- **RMS**: Compute RMS on interleaved stereo samples over stated window. Use the louder channel (max of L/R RMS).
- **Peak**: Sample peak of either channel across full render (max abs sample value).
- **DC offset**: abs(mean) per channel; fail if either channel exceeds threshold.
- **Runaway**: Compare peak in first 1s vs peak in last 1s of a 10s render. Use `peak_first = max(peak_first, 1e-6)` to avoid division by zero. Fail if `20 * log10(peak_last / peak_first) >= +6 dB`.

**Determinism check:**

Deterministic render contract for hash comparison:
- Sample rate: 48000 Hz
- Duration: 3 seconds
- Seed: Fixed value injected via `seed` argument
- Input: No MIDI trigger; envelope source = OFF (drone mode)
- Gate behavior: Render with `gate=1` constant for full duration (no retriggers), and any per-note pitch inputs fixed to a constant default (e.g., `freq=220` if required by the method contract)
- Normalization: None
- Hash method: SHA-256 of raw float32 interleaved stereo frames

Same seed → identical hash.

### 3.5 Output Pack

```
packs/{pack_id}/
├── manifest.json
└── generators/
    ├── {generator_id}.json
    ├── {generator_id}.scd
    └── ...
```

---

## 4. Naming and ID Rules

### 4.1 Pack IDs

| Field | Format | Example |
|-------|--------|---------|
| `pack_id` | Slug: lowercase, underscores | `abyssal_depths` |
| `name` | Display: title case, spaces allowed | `Abyssal Depths` |

**Slug rules:**
- Lowercase a-z, digits 0-9, underscores only
- No spaces, hyphens, or special characters
- **Max 24 characters** (to keep SynthDef names reasonable)

### 4.2 Generator IDs

Same slug rules as pack IDs.

| Field | Format | Example |
|-------|--------|---------|
| `generator_id` | Slug | `pressure_wave` |
| `name` | Display | `Pressure Wave` |
| `synthdef` | SC symbol | `forge_{pack_id}_{generator_id}` |

**Max 24 characters** for generator_id.

**SynthDef name length note:** Combined `forge_{pack_id}_{generator_id}` should stay under 56 characters total. SuperCollider handles longer names but tooling may truncate.

---

## 5. Output Schemas

### 5.1 Pack Manifest

```json
{
  "pack_id": "abyssal_depths",
  "name": "Abyssal Depths",
  "description": "Dark underwater ambience, crushing pressure, bioluminescent hints",
  "author": "CQD_Forge",
  "version": "1.0.0",
  "created": "2025-12-23T12:00:00Z",
  "generators": [
    "pressure_wave",
    "biolume_ping",
    "abyssal_drift",
    "ancient_signal",
    "crush_depth",
    "murk_shimmer",
    "stone_whisper",
    "ruin_echo"
  ]
}
```

**Required fields:**
- `pack_id` (slug, max 24 chars)
- `name` (display)
- `description` (non-empty)
- `author` (string)
- `version` (semver)
- `generators` (array of generator_ids, length 8)

**Optional fields:**
- `created` (ISO-8601 UTC)

**Generator file resolution (normative):**
- `generator_json_path = "generators/{generator_id}.json"`
- `generator_scd_path = "generators/{generator_id}.scd"`
- Manifest stores **IDs only**, not filenames or paths.

### 5.2 Generator JSON

```json
{
  "generator_id": "pressure_wave",
  "name": "Pressure Wave",
  "synthdef": "forge_abyssal_depths_pressure_wave",
  "custom_params": [
    {"key": "void", "label": "VOD", "tooltip": "Void depth — how deep into the abyss", "default": 0.8, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "pressure", "label": "PRS", "tooltip": "Crushing intensity", "default": 0.7, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "drift", "label": "DFT", "tooltip": "Pitch instability", "default": 0.3, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "churn", "label": "CHN", "tooltip": "Subsurface turbulence", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "breath", "label": "BRH", "tooltip": "Organic movement", "default": 0.4, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""}
  ],
  "output_trim_db": -6.0,
  "midi_retrig": false,
  "pitch_target": null
}
```

**Required fields:**
- `generator_id` (slug, matches filename)
- `name` (display)
- `synthdef` (SC symbol name)
- `custom_params` (array of 5)
- `output_trim_db`
- `midi_retrig`
- `pitch_target`

### 5.3 Generator SynthDef

Standard Noise Engine contract — see GENERATOR_SPEC.md.

SynthDef name format: `forge_{pack_id}_{generator_id}`

---

## 6. Families

**Normative family enum for launch:**

| Family | Code | Description |
|--------|------|-------------|
| Subtractive | `sub` | Oscillator + filter (saw, pulse, noise) |
| FM | `fm` | Frequency modulation synthesis |
| Physical | `phys` | Physical modeling (karplus, modal, bowed) |
| Spectral | `spec` | Additive, FFT-based synthesis |
| Texture | `tex` | Noise-based, granular, sample-like |

Each method maps to exactly one family. Family is recorded in design sheets for diversity tracking.

---

## 7. P1-P5 Rules

**Labels:**
- Format: `[A-Z0-9]{3}` (exactly 3 characters)
- **Unique within generator** (not pack-wide)
- Encouraged: evocative, thematic

**Tooltips:**
- **Required non-empty**
- Should explain the sonic effect in context

**Units:**
- May be empty for unitless params

**Forbidden labels** (collision with core UI params):
```
CUT, RES, ATK, DEC, FRQ
```

**Generic labels allowed if tooltip is themed:**
```
MIX — allowed if tooltip explains blend (e.g., "Biolume vs Abyss blend")
DRV — allowed if tooltip indicates character (e.g., "Rust saturation")
WID — allowed if tooltip is specific (e.g., "Stereo void spread")
```

---

## 8. Batch Session Format

### 8.1 Planning Phase

Claude reviews all images and produces per-image design sheets:

```
## Pack: Abyssal Depths
Image: [description of what Claude sees]
Mood: Dark, underwater, ominous
Theme: Ancient ruins, crushing depth, bioluminescence

| Slot | Name | Method | Family | Role | P1 | P2 | P3 | P4 | P5 |
|------|------|--------|--------|------|----|----|----|----|-----|
| 1 | Pressure Wave | dark_pulse | sub | bed | VOD | PRS | DFT | CHN | BRH |
| 2 | Biolume Ping | karplus | phys | accent | GLW | DIM | RNG | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
```

Gareth reviews and approves designs before generation.

### 8.2 Generation Phase

For each approved pack, Claude provides:
- Full generator JSON files
- Full SynthDef files
- Pack manifest
- Copy commands for file placement

### 8.3 Validation Report

```
Pack: abyssal_depths
Generators: 8/8 created
Contract: PASS (8/8)
Safety: PASS (8/8)
Diversity:
  - Families: sub(2), fm(3), phys(2), tex(1) ✓
  - Roles: accent(2), fg(1), motion(2), bed(3) ✓
```

### 8.4 File Output

Copy commands + git commit for each pack.

---

## 9. Method Catalog Strategy

**For launch batch:**
- Prefer existing methods (currently 14)
- Recombine and retune before creating new
- New methods only with explicit justification

**New method criteria:**
- 3+ images in batch require capability not covered
- Creates reusable value (not one-off)
- Justification documented before creation

**If new method needed:**
- Add to backlog or create in dedicated phase
- Must pass full contract validation
- Must follow IMAGINARIUM_CUSTOM_PARAMS_SPEC

---

## 10. Deliverables for Launch

| Target | Count |
|--------|-------|
| Images processed | 10 minimum, 20 stretch |
| Packs created | 1 per image |
| Generators per pack | 8 |
| Total generators | 80-160 |

---

## 11. Session Phases

### Phase 1: Setup
- [x] Finalize spec
- [ ] Review method catalog readiness
- [ ] Confirm validation approach

### Phase 2: Batch Run
- [ ] Gareth provides image batch
- [ ] Claude creates design sheets for all
- [ ] Gareth reviews/approves designs
- [ ] Claude generates all files
- [ ] Validation reports

### Phase 3: Polish (if needed)
- [ ] Fix any validation failures
- [ ] Adjust based on listening tests
- [ ] Final commit

---

## 12. Success Criteria

- [ ] 10+ packs created from image batch
- [ ] All packs pass contract validation
- [ ] All packs pass safety gates
- [ ] P1-P5 labels are evocative, tooltips are themed
- [ ] Packs are diverse across the batch (not all same vibe)
- [ ] Ready to ship with Noise Engine v1
- [ ] Gareth enjoys making music with them

---

**v1.0 — FROZEN**
