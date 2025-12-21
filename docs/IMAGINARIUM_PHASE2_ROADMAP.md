# Imaginarium Phase 2: Analysis & Selection Improvements

## Strategic Context

Phase 1 delivered a working 8-step pipeline: Image → Pack with 8 generators.

However, the results feel "samey" despite having 10 different synthesis methods. The root cause is the **information bottleneck**:

```
Rich visual input → 2 numbers (brightness, noisiness) → 10 methods competing
```

Adding more synthesis methods has diminishing returns. The leverage is in **improving the analysis layer** so existing methods are selected more intelligently.

---

## Current State (Phase 1 Complete)

### Methods: 10
| Family | Methods |
|--------|---------|
| subtractive | bright_saw, dark_pulse, noise_filtered, supersaw |
| fm | simple_fm, feedback_fm, ratio_stack |
| physical | karplus, modal, bowed |

### SoundSpec: 2 dimensions
- `brightness` (0-1): Derived from luminance
- `noisiness` (0-1): Derived from edge density / texture

### Limitations
- No semantic understanding ("figure in hallway" = "grey rectangle")
- No mood/emotion extraction
- No color palette analysis
- No composition reading (sparse vs dense)
- All methods compete equally regardless of image character

---

## Phase 2 Roadmap

### Phase 2a: Expanded Traditional Analysis

**Goal:** Expand SoundSpec from 2 → 6-8 dimensions using pixel analysis only.

**New dimensions to extract:**

| Feature | Extraction Method | Maps To |
|---------|-------------------|---------|
| `warmth` | Color temperature (R/B ratio) | Filter character, method choice |
| `saturation` | HSV saturation mean | Harmonic richness |
| `contrast` | Luminance std dev | Dynamic range, attack character |
| `density` | Edge density + fill ratio | Generator complexity |
| `movement` | Directional gradients, flow | LFO rates, modulation depth |
| `depth` | Gradient analysis, blur detection | Reverb, space, layer separation |

**Implementation:**
- Extend `analyze.py` with new extractors
- Update `SoundSpec` dataclass
- Update scoring to use all dimensions
- All pure NumPy/PIL - no AI dependency

**Determinism:** ✅ Preserved
**Effort:** ~1 session

---

### Phase 2b: Method Biasing

**Goal:** Weight method selection based on image characteristics.

Instead of all methods competing equally, bias toward appropriate synthesis:

| Image Character | Favored Methods | Avoided Methods |
|-----------------|-----------------|-----------------|
| Dark, moody, low saturation | bowed, modal, noise_filtered | supersaw, bright_saw |
| Bright, high saturation | supersaw, bright_saw, simple_fm | noise_filtered |
| Textured, organic | karplus, noise_filtered, bowed | ratio_stack |
| Clean, geometric | simple_fm, ratio_stack, dark_pulse | noise_filtered |
| High contrast, dynamic | feedback_fm, karplus | bowed |
| Low contrast, ambient | bowed, modal, noise_filtered | feedback_fm |

**Implementation:**
- Add `method_affinity` scores based on SoundSpec dimensions
- Weight candidate generation or selection by affinity
- Could be multiplicative on fit score

**Determinism:** ✅ Preserved
**Effort:** ~0.5 session

---

### Phase 3: Optional LLM Semantic Brief (Future)

**Goal:** For users who want semantic understanding, offer LLM interpretation.

**Flow:**
```
Image → Vision LLM → "Sonic Brief" (structured) → Cached → Expanded SoundSpec → Deterministic pipeline
```

**Sonic Brief Schema (draft):**
```json
{
  "mood": ["melancholic", "tense"],
  "energy": "low",
  "texture": "smooth with grit",
  "suggested_character": ["sustained", "metallic", "dark"],
  "method_hints": ["bowed", "modal"],
  "avoid": ["bright", "aggressive"],
  "warmth": 0.3,
  "tension": 0.7,
  "movement": "slow",
  "density": "sparse"
}
```

**Implementation:**
- `--interpret` CLI flag
- Brief cached by image hash (deterministic after first run)
- Maps brief → expanded SoundSpec
- Optional Claude/GPT-4V API integration

**Determinism:** ✅ After brief generation
**Effort:** ~2 sessions
**Dependency:** API access, user opt-in

---

## Method Expansion Strategy

### Recommendation: Pause at 12 methods

Current 10 is good coverage. Add 2 more for 4/4/4 balance:

| Family | Current | Add | Total |
|--------|---------|-----|-------|
| subtractive | 4 | 0 | 4 |
| fm | 3 | 1 | 4 |
| physical | 3 | 1 | 4 |

**Candidates:**
- `fm/phase_mod` - Phase modulation (different character from FM)
- `physical/tube` - Waveguide tube/wind instrument

**Then stop.** More methods later only if specific gaps emerge from user feedback.

---

## Priority Order

1. **Complete method round-out** (2 more → 12 total) - 0.5 session
2. **Phase 2a: Expanded Analysis** - 1 session
3. **Phase 2b: Method Biasing** - 0.5 session
4. **Phase 3: LLM Brief** - 2 sessions (optional/future)

Total for meaningful improvement: ~2 sessions

---

## Success Metrics

**Before (Phase 1):**
- Packs feel samey regardless of input image
- Method selection appears random

**After (Phase 2):**
- Dark moody image → predominantly bowed, modal, noise_filtered
- Bright energetic image → supersaw, bright_saw, FM
- Textured organic image → physical methods dominate
- Packs feel intentionally matched to input

---

## Open Questions

1. Should method biasing be hard (exclude methods) or soft (weight scores)?
2. How many SoundSpec dimensions before diminishing returns?
3. Is color palette analysis worth the complexity?
4. Should Phase 3 LLM brief be Claude-only or support multiple providers?

---

## Related Docs

- `IMAGINARIUM_SPEC.md` - Technical specification
- `SESSION_SUMMARY_2025-12-21.md` - Phase 1 completion notes
- `BACKLOG.md` - Main project backlog
