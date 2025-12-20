# IMAGINARIUM — Spec Sheet v0.3.0

> **Release Info**
> | | |
> |---|---|
> | Spec Version | v10 |
> | Scripts Version | v8 |
> | Last Updated | 2025-12-20 |
> | Status | **Shippable** (Phase 0 ready, Phase 1 buildable) |

A deterministic **sound-palette generator** for Noise Engine: given an input stimulus (image / text / audio / video), Imaginarium generates many synthesis candidates across a method catalogue, rejects unsafe output, scores candidates for fit to the inferred "SoundSpec", then selects a small **diverse** subset (e.g. 8) and exports them as Noise Engine pack generators.

---

## 1) Goals

| ID | Goal | Description |
|----|------|-------------|
| G1 | On-brief | Outputs match the inferred SoundSpec (Phase 1: brightness + noisiness only) |
| G2 | Diverse | Outputs are meaningfully different (explicit distance/constraints, not randomness) |
| G3 | Reproducible | Same input + same `run_seed` → identical outputs; different `run_seed` → different outputs |
| G4 | Compatible | Generated SynthDefs + JSON satisfy the Noise Engine Generator Contract |

---

## 2) Non-goals (v0.3.x)

* No ML training
* No "perfect semantic mapping" from image/text to sound
* No global "best" embedding model requirement in Phase 1

---

## 3) Inputs

| Input | Phase 1 | Phase 2+ |
|-------|---------|----------|
| Image | Primary | ✓ |
| Text | — | ✓ |
| Audio clip | — | ✓ |
| Video | — | Still-frame + motion |

Phase 1: **Image → brightness/noisiness** only; all other spec dimensions are null.

---

## 4) Core data model

### 4.1 SoundSpec (Phase 1)

```json
{
  "version": "0.3.0",
  "fields_used": ["brightness", "noisiness"],
  "brightness": 0.65,
  "noisiness": 0.30,
  "weights": { "brightness": 1.0, "noisiness": 1.0 }
}
```

### 4.2 CandidateFeatures (Phase 1)

All normalized to 0–1:

| Feature | Source | Mapping |
|---------|--------|---------|
| centroid | spectral centroid | log [100, 12000] Hz |
| flatness | spectral flatness | linear [0, 1] |
| onset_density | onset rate | linear [0, 20] onsets/sec |
| crest | peak/RMS ratio | linear [0, 24] dB |
| width | stereo correlation | linear [0, 1] |
| harmonicity | harmonic ratio | linear [0, 1] |

### 4.3 CandidateSignature

```python
def compute_signature(features: CandidateFeatures, family: str) -> np.ndarray:
    continuous = [
        features.centroid, features.flatness, features.onset_density,
        features.crest, features.harmonicity, features.width
    ]
    family_onehot = [0.1 if f == family else 0.0 for f in FAMILIES]
    return np.array(continuous + family_onehot, dtype=np.float32)
```

**FAMILIES versioning:** Phase 1 uses `FAMILIES = ['subtractive', 'fm', 'physical']` (3 families → signature length 9). Later phases must keep ordering stable (append-only) or version the signature to maintain archive compatibility.

---

## 5) Method catalogue

### 5.1 Phase 1 families

| Family | Methods | Strengths |
|--------|---------|-----------|
| subtractive | bright_saw, dark_pulse, multi_osc | High brightness control |
| fm | simple_fm, complex_fm | Mid-bright, variable noise |
| physical | karplus, modal, waveguide | Natural decay, low noise |

### 5.2 Method definition

```json
{
  "method_id": "subtractive/bright_saw",
  "family": "subtractive",
  "template_path": "templates/subtractive_bright_saw.scd.j2",
  "param_axes": ["cutoff", "drive", "detune", "pulsewidth", "spread"],
  "macro_controls": ["TONE", "EDGE", "MOTION", "SPACE", "SHAPE"]
}
```

### 5.3 Method priors

Normalized to sum=1.0:

```python
METHOD_PRIORS = {"subtractive": 0.35, "fm": 0.35, "physical": 0.30}
```

---

## 6) Noise Engine generator contract

### 6.1 Required JSON schema

```json
{
  "name": "Display Name",
  "synthdef": "imaginarium_packname_method_variant",
  "custom_params": [],
  "output_trim_db": -6.0,
  "midi_retrig": false,
  "pitch_target": null
}
```

### 6.2 Required SynthDef arglist

```supercollider
SynthDef(\imaginarium_pack_method_variant, {
    |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
     filterTypeBus, envEnabledBus, envSourceBus=0,
     clockRateBus, clockTrigBus,
     midiTrigBus=0, slotIndex=0,
     customBus0, customBus1, customBus2, customBus3, customBus4,
     seed=0|   // REQUIRED for Imaginarium

    RandSeed.ir(1, seed);  // MUST be first, before any random UGens
    // ... synthesis ...
}).add;
```

### 6.3 Helper functions

Available after Noise Engine bootstrap:

* `~ensure2ch.(sig)` — Force stereo
* `~multiFilter.(sig, filterType, filterFreq, rq)` — LP/HP/BP
* `~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex)`
* `~stereoSpread.(sig, rate, width)`

### 6.4 envEnabledBus

Vestigial: generators must accept it but may ignore it. Envelope control via `envSourceBus` (0=OFF, 1=CLK, 2=MIDI).

### 6.5 Namespacing

All generated SynthDef symbols: `\imaginarium_<pack>_<method>_<variant>`

---

## 7) Determinism + seeds

### 7.1 Stable hashing

**Do NOT use Python `hash()`** — it's salted per-process.

```python
import hashlib

def stable_u32(*parts) -> int:
    s = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(s).digest()[:4], "big")
```

### 7.2 Seed hierarchy

```python
@dataclass
class GenerationContext:
    run_seed: int

    @property
    def sobol_seed(self) -> int:
        return stable_u32("sobol", self.run_seed)

    def candidate_seed(self, candidate_id: str) -> int:
        return stable_u32("cand", self.run_seed, candidate_id)
```

### 7.3 Candidate identity

Seeds derived from **identity**, not position:

```
candidate_id = "{method_id}:{macro}:{param_index}:{template_version}"
```

### 7.4 SynthDef requirement

All Imaginarium SynthDefs must include:

```supercollider
RandSeed.ir(1, \seed.kr(0));
```

This must appear **before** any random UGens.

---

## 8) Pipeline

```
Input → SpecExtractor → CandidateGenerator → PreviewRender(NRT)
      → SafetyGates → Analyzer → SpecFitScoring
      → DiversitySelection → FinalRender → Export
```

---

## 9) Safety gates

### 9.1 Configuration

```python
@dataclass
class SafetyGateConfig:
    sample_rate: int = 48000
    frame_length: int = 2048
    hop_length: int = 1024
    min_rms_db: float = -40.0
    active_threshold_db: float = -45.0
    min_active_frames_pct: float = 0.30
    max_sample_value: float = 0.999
    max_dc_offset: float = 0.01
    max_level_growth_db: float = 6.0
```

### 9.2 Gate logic

| Gate | Condition | Fail reason |
|------|-----------|-------------|
| Audibility | RMS < -40 dB | "silence" |
| Active frames | < 30% above -45 dB | "sparse" |
| Clipping | any sample ≥ 0.999 | "clipping" |
| DC offset | abs(mean) > 0.01 | "dc_offset" |
| Runaway | level growth > +6 dB | "runaway" |

---

## 10) Feature normalization

All normalizations explicit and versioned:

```python
NORMALIZATION_V1 = {
    "centroid": {"range": [100, 12000], "curve": "log"},
    "flatness": {"range": [0, 1]},
    "onset_density": {"range": [0, 20]},
    "crest": {"range": [0, 24]},
    "width": {"range": [0, 1]},
    "harmonicity": {"range": [0, 1]},
}
```

---

## 11) Scoring (Phase 1)

```python
def compute_fit(spec: SoundSpec, features: CandidateFeatures) -> float:
    brightness_fit = 1.0 - abs(spec.brightness - features.centroid)
    noisiness_fit = 1.0 - abs(spec.noisiness - features.flatness)
    return (
        spec.weights["brightness"] * brightness_fit +
        spec.weights["noisiness"] * noisiness_fit
    ) / sum(spec.weights.values())
```

Minimum fit threshold: `0.6`

---

## 12) Diversity selection

### 12.1 Distance metric

```python
def distance(a: Candidate, b: Candidate) -> float:
    feat_dist = np.linalg.norm(a.signature - b.signature)
    tag_dist = 1.0 - jaccard(a.tags, b.tags)
    return 0.8 * feat_dist + 0.2 * tag_dist
```

**Tag distance:** Compute Jaccard on the set of `f"{k}={v}"` pairs (e.g., `{"family=subtractive", "topology=serial"}`). Phase 1 weights: `W_FEAT=0.8`, `W_TAG=0.2`.

### 12.2 Farthest-first algorithm (unconstrained core)

```python
def farthest_first_select_unconstrained(pool: List[Candidate], n: int) -> List[Candidate]:
    """Core algorithm without constraints - for illustration only."""
    selected = [max(pool, key=lambda c: c.fit)]
    while len(selected) < n:
        best = max(
            [c for c in pool if c not in selected],
            key=lambda c: min(distance(c, s) for s in selected)
        )
        selected.append(best)
    return selected
```

**Production selection** uses `select_with_constraints(pool, constraints)` which wraps farthest-first with:
- `min_family_count` / `max_per_family` enforcement
- `min_pair_distance` threshold checks
- Archive distance blocking
- Relaxation ladder on constraint failure

### 12.3 Phase 1 constraints

```python
PHASE1_CONSTRAINTS = {
    "min_family_count": 3,
    "max_per_family": 3,
    "min_pair_distance": 0.15,
    "min_archive_distance": 0.20,
}
```

### 12.4 Relaxation ladder

```python
# Ladder starts at baseline and progressively relaxes
RELAXATION_LADDER = [
    {"min_pair_distance": 0.15},   # level 0: baseline (same as PHASE1_CONSTRAINTS)
    {"min_pair_distance": 0.12},   # level 1: relax distance
    {"min_pair_distance": 0.10},   # level 2: relax further
    {"max_per_family": "+1"},      # level 3: allow one more per family
    {"min_family_count": "-1"},    # level 4: reduce family requirement
    {"n_select": 6},               # level 5: reduce output count
    {"n_select": 4},               # level 6: reduce further
]

# relaxation_level=0 is baseline; levels 1-6 are actual relaxations
MAX_LADDER_STEPS = len(RELAXATION_LADDER)  # 7 total steps (0-6)
```

### 12.5 Deadlock report

```python
@dataclass
class SelectionDeadlock:
    pool_size: int
    family_counts: Dict[str, int]
    constraint_failures: List[str]
    nearest_neighbor_distances: List[float]
    relaxation_level: int
    fallback_used: bool
```

### 12.6 Ultimate fallback

1. Select best-fit with `max_per_family` enforced
2. Emit deadlock report (do not silently succeed)
3. Log warning in generation_report.json

---

## 13) Archive

Per-selected output:

```python
@dataclass
class ArchiveEntry:
    candidate_id: str
    signature: np.ndarray
    tags: Dict[str, str]
    run_seed: int
    input_fingerprint: str
    timestamp: datetime
```

Rules:
* Reject if `min_distance(candidate, archive) < min_archive_distance`
* Archive consulted **during** selection
* Persists across runs (JSON file)

---

## 14) Calibration (Phase 1.5)

1. Generate 500–2000 preview candidates
2. Compute pairwise distances
3. Separate within-family vs across-family
4. Set thresholds:
   * `min_pair_distance = P25(across-family)`
   * `min_archive_distance = P50(across-family)`

Output: `calibration_report.json`

---

## 15) Candidate Pool Policy

### 15.1 "Usable" definition

A candidate is **usable** if all of:

```python
usable = (
    safety_pass and          # Passed all safety gates (§9)
    fit >= MIN_FIT and       # Meets spec fit threshold (§11)
    not archive_blocked      # Not too similar to archive (§13)
)
```

### 15.2 Acceptance rate

Calibration measures:

```python
p_safe   = count(safety_pass) / count(total)
p_fit    = count(fit_pass) / count(safety_pass)      # P(fit | safe)
p_unique = count(not_archive_blocked) / count(fit_pass)  # P(unique | fit ∧ safe)

p_usable = p_safe * p_fit * p_unique
```

**Note:** `p_fit` is conditional on safety-pass; `p_unique` is conditional on fit-pass; thus `p_usable` is the chain product P(safe) × P(fit|safe) × P(unique|fit∧safe).

### 15.3 Pool size derivation

**Do not hardcode candidate count.** Derive from acceptance rate:

```python
def required_pool_size(n_select: int, p_usable: float) -> int:
    """Conservative heuristic for pool size. Calibration should tune margin."""
    base = ceil(n_select / max(p_usable, 0.05))
    margin = 2.0 if p_usable < 0.1 else 1.5
    return min(ceil(base * margin), MAX_CANDIDATES)
```

**Policy note:** We clamp `p_usable` to 0.05 minimum to prevent unbounded pool sizes when the system is misconfigured. If calibration reports `p_usable < 0.05`, treat it as a pipeline problem (fix safety gates, fit thresholds, or method templates) rather than increasing candidate count indefinitely.

**Phase 2 upgrade:** Replace heuristic margins with binomial-based N selection: choose N such that `P(X ≥ n_select) ≥ 0.99` where `X ~ Binomial(N, p_usable)`.

### 15.4 Per-family allocation (floor)

Because families have different acceptance rates, allocate a **floor** per family to prevent starvation:

```python
def allocate_per_family(n_select: int, families: List[str], p_family: Dict[str, float]) -> Dict[str, int]:
    """Floor allocation per family based on acceptance rates."""
    target_per_family = ceil(n_select / len(families))
    return {
        f: ceil(target_per_family / max(p_family.get(f, 0.1), 0.05) * 1.5)
        for f in families
    }
```

**Note:** Per-family allocation is a floor to prevent family starvation; excess budget can be assigned by method priors or observed `p_family`. The goal is ensuring at least 1–2 viable candidates from each family early, not strict equality.

### 15.5 Adaptive batching (recommended)

Instead of generating all candidates upfront:

```python
BATCH_SIZE = 32
MAX_BATCHES = 15  # Hard ceiling: 480 candidates max

def generate_until_selectable():
    candidates = []
    for batch_num in range(MAX_BATCHES):
        candidates.extend(generate_batch(BATCH_SIZE))
        usable = [c for c in candidates if c.usable]
        
        if can_select(usable, n_select=8, constraints=CONSTRAINTS):
            return select(usable)
    
    # Hit ceiling - use relaxation ladder
    return select_with_fallback(usable)
```

**Precedence:** In Phase 1, adaptive batching is the execution strategy; `required_pool_size()` (§15.3) is the calibration recommendation used to tune `MAX_BATCHES` based on observed `p_usable`.

### 15.6 Calibration report additions

`calibration_report.json` must include:

```json
{
  "acceptance_rates": {
    "p_safe": 0.85,
    "p_fit": 0.40,
    "p_unique": 0.70,
    "p_usable": 0.24
  },
  "per_family": {
    "subtractive": {"p_usable": 0.30, "recommended_n": 45},
    "fm": {"p_usable": 0.20, "recommended_n": 60},
    "physical": {"p_usable": 0.15, "recommended_n": 80}
  },
  "recommended_pool_size": 185
}
```

---

## 16) Outputs

### 16.1 Pack structure

```
packs/<pack_name>/
├── manifest.json
├── generators/
│   ├── <gen_id>.json
│   └── <gen_id>.scd
└── reports/
    ├── generation_report.json
    └── selection_report.json
```

### 16.2 generation_report.json

```json
{
  "version": "0.3.0",
  "input_fingerprint": "sha256:...",
  "run_seed": 12345,
  "sobol_seed": 67890,
  "candidates": [
    {"id": "...", "seed": 111, "method_id": "...", "status": "selected"}
  ]
}
```

### 16.3 selection_report.json

```json
{
  "selected": ["id1", "id2"],
  "pairwise_distances": {"min": 0.25, "mean": 0.42},
  "family_counts": {"subtractive": 3, "fm": 3, "physical": 2},
  "relaxations_applied": [],
  "deadlock": null
}
```

---

## 17) Phase plan

### Phase 0 — Trust gate

**Goal:** Prove environment + determinism + contract checks work.

**Scripts:**

| Script | Purpose |
|--------|---------|
| `imaginarium_verify_contract_v8.scd` | SC contract verification with bootstrap + timeout |
| `imaginarium_determinism_test_v8.scd` | NRT render for hash comparison |
| `imaginarium_verify_contract_v8.py` | Python wrapper + arglist parser |
| `imaginarium_determinism_test_v8.py` | Two-part determinism proof |

**Requirements:**

1. SC script bootstraps Noise Engine context by executing either `supercollider/init.scd` or the minimal set of core files required to ensure helpers and `~params` exist (at minimum `core/buses.scd` and `core/helpers.scd`). If using minimal core, load `core/buses.scd` before `core/helpers.scd`.
2. SC script emits `IMAGINARIUM_VERIFY_OK/FAIL`
3. SC script enforces 15s boot timeout
4. Determinism test proves:
   * Same seed → identical PCM hash
   * Different seed → different PCM hash
5. Python arglist parser uses regex (not substring)
6. Missing `seed` arg is ERROR for Imaginarium packs

### Phase 1 — MVP

* Input: image
* Spec: brightness + noisiness only
* Families: 3
* Preview: 3s NRT
* Selection: farthest-first + Phase 1 constraints

### Phase 2+

* Enum proxies (tonality, register, motion)
* Richer signature features
* BD coverage / MAP-Elites

---

## 18) Success criteria

| Criterion | Test |
|-----------|------|
| Phase 0 passes | Scripts exit 0 in clean repo |
| Same seed → identical | Same input + run_seed → identical pack |
| Different seed → different | Different run_seed → different selected set |
| Safety | All selected pass safety gates |
| Contract | All SynthDefs load in Noise Engine |
| Diversity | Selected set meets min_pair_distance |

---

## 19) Installation

```bash
# Copy scripts to Noise Engine
cp imaginarium_verify_contract_v8.py   noise-engine/scripts/
cp imaginarium_verify_contract_v8.scd  noise-engine/scripts/
cp imaginarium_determinism_test_v8.scd noise-engine/scripts/
cp IMAGINARIUM_SPEC_v10.md             noise-engine/docs/

# Run verification (single command runs all Phase 0 checks)
cd noise-engine
python scripts/imaginarium_verify_contract_v8.py
```

---

## Appendix: Version history

| Version | Changes |
|---------|---------|
| 0.1.0 | Initial draft |
| 0.2.0 | Safety gates, selection algorithm |
| 0.3.0 | Determinism contract, Phase 1 constraints, safety thresholds |
| Scripts v6 | Fixed s.boot, versioned script fallback, single-command Phase 0 |
| Spec v7 | Added §15 Candidate Pool Policy |
| Spec v8 | Fixed relaxation ladder order, section numbering, clarified constrained selection |
| Spec v9 | Renamed MAX_LADDER_STEPS, batching precedence, conditional probability note, FAMILIES versioning |
| Spec v10 | Bootstrap flexibility + ordering, floor allocation, Jaccard k=v pairs, p_usable clamp policy, release header |
| Scripts v7 | Fixed SC var declaration order (must be at block start) |
| Scripts v8 | Fixed remaining var declarations in SynthDef and Routine blocks |
