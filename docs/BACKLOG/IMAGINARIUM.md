# Imaginarium Backlog

## Phase 3: Detail Layer (NEXT)
Second layer system adding texture/movement to generated packs.

**10 Techniques:**
- sub, dust, drift, shimmer, beat
- growl, ghost, swarm, breath, ping

**Allocation:** SoundSpec (6D) → technique weights  
**Budget:** Total detail capped to prevent mud  
**Role bias:** Accent → +ping, Bed → +sub, etc.

**Spec:** `DETAIL_LAYER_SPEC.md` (to create)

## Phase 2 Remaining
- [x] A/B listening tests: spatial vs global selection
- [ ] Quantile-based floors (replace fixed thresholds)
- [ ] Per-role SoundSpec generation (targeted candidate pools)
- [ ] Layer mix defaults (gain/pan/EQ hints per role)

## Phase 4: Extended Input (future)
- [ ] Text → SoundSpec (NLP keywords to parameters)
- [ ] Audio → SoundSpec (analyze reference audio)

## Extraction Calibration
Improve SoundSpec extraction accuracy using synthetic ground truth.

Source: `imaginarium/tools/gen_test_image.py` generates images with known brightness/noisiness.

Approach:
- Generate calibration grid (e.g., 10×10 brightness×noisiness)
- Run extract.py on each generated image
- Compare extracted values vs input parameters
- Compute correction coefficients
- Apply calibration in extract.py

## Image Generator Color Improvements
Purple/magenta bias from alpha blending + saturated backgrounds.

**Backlog A: Calibration Suite**
- Add `hue: float | None` parameter (0-1, forces hue coverage)
- Add saturation/value tier controls
- Add saturation coupling rule (one vivid, one calm)
- Add QA gate (reject if hue histogram too concentrated)
- Add `--suite calibration` mode

**Backlog B: Showcase Suite**
- Neutral backgrounds default
- Visual diversity without strict bin balancing

**Backlog C: Harmony Separability**
- Make `colour_*` presets compositionally distinct
- Complementary: 50/50 split, Triadic: 3 wedges, etc.

**Backlog D: Corpus Health Metric**
- Hue histogram summary
- Saturation mean/std
- % images with dominant hue bin > threshold

## CLI Enhancement
- [x] Show spatial role grid in generate output (--spatial is now default)

## Ideas
- Foreground detection for soft-edge/painterly images
- Adaptive pool sizing based on safety pass rate
- Archive/novelty filtering (skip similar to previous packs)

---

## Reference: Preset Defaults

Location: `imaginarium/export.py` (~line 145-165)

| Param | Value | Meaning |
|-------|-------|---------|
| frequency | 0.5 | Mid-range |
| cutoff | 1.0 | Filter fully open |
| resonance | 0.0 | No resonance |
| attack | 0.0 | Snappiest attack |
| decay | 0.76 | ~2 seconds |
| custom_0-4 | 0.5 | Mid-range defaults |

**Decay curve:** 0.73→~1.0s, 0.76→~2.0s, 0.80→~2.5s, 0.85→~4.0s, 0.90→~5.5s
