---
status: approved
version: 0.4
created: 2024-12-22
updated: 2024-12-22
frozen_at: 2024-12-22
author: AI1
reviewed_by: AI2
approvals: AI1 ✓ AI2 ✓
target: post-release-1
---

# Tertiary Musical Context Layer

## What

A third analysis stage that derives **musical atmosphere descriptors** from images. Produces a 3-word context triplet (e.g., `["intimate", "organic", "breathing"]`) that biases sound selection toward a cohesive mood.

Two complementary extraction methods:
- **3a: Visual Features** — low-level image properties (edges, color, texture)
- **3b: Object Detection** — recognized objects mapped through a curated concept database

This layer answers: *"What feeling should this soundscape evoke?"*

## Why

The current Imaginarium pipeline provides:
- **Global analysis (Phase 1):** 6D SoundSpec — *what kind of sounds*
- **Spatial analysis (Phase 2):** Role assignment — *where sounds sit*

Missing: **Narrative/mood context** — *what atmosphere* we're creating.

Two images with identical SoundSpec values could demand completely different moods:
- Misty forest → intimate, organic, still
- Factory floor → vast, mechanical, churning

The context triplet provides the missing semantic layer.

## Constraints

| Constraint | Rationale |
|------------|-----------|
| ❌ No external systems | No cloud APIs, no network dependencies |
| ✅ Local ML allowed | Bundled models with fixed weights |
| ✅ Deterministic | Same image + same environment → same output |
| ✅ Debuggable | All intermediate values inspectable |
| ✅ Fallback-safe | System works if detection fails |

### Determinism Scope

Determinism is defined as **same machine + same build**:
- Same ONNX Runtime version
- Same OpenCV version  
- Same model weights (verified by SHA256)
- Same preprocessing pipeline (resize algorithm, color space)

Cross-machine determinism is **not guaranteed** due to:
- CPU instruction set differences
- Floating point implementation variance
- Library build differences

Environment fingerprint recorded in debug output for reproducibility verification.

## How

### Pipeline Position

```
Image
  ├─ Phase 1: Global Analysis (6D SoundSpec)
  ├─ Phase 2: Spatial Analysis (roles + LayerStats)
  ├─ Phase 3: Musical Context
  │     ├─ 3a: Visual Features → base distribution
  │     ├─ 3b: Object Detection → modifier distribution
  │     └─ 3c: Fusion → final triplet
  └─ Phase 4: Selection (SoundSpec + roles + context bias)
```

---

## Phase 3a: Visual Features (Base Distribution)

Extracts 9 low-level features using OpenCV, produces probability distributions over words for each axis.

### Feature Extraction

| Feature | Method | Normalization |
|---------|--------|---------------|
| color_temperature | Mean hue | `(hue - 90) / 90` → -1.0–1.0 |
| saturation | Mean saturation | `sat / 255` → 0.0–1.0 |
| texture_grain | Laplacian variance | `sigmoid(log(var + 1), k=0.5, x0=4.0)` |
| edge_density | Canny edge pixel ratio | Direct |
| contrast | Histogram std dev | `std / 64` clamped 0.0–1.0 |
| orientation_bias | Sobel V/H energy ratio | `tanh(log(ratio))` → -1.0–1.0 |
| symmetry | L/R half NCC | `(ncc + 1) / 2` → 0.0–1.0 |
| negative_space | Low-variance region % | Direct |
| focal_clarity | Center/edge sharpness ratio | `sigmoid(ratio, k=1.0, x0=1.5)` |

Calibration constants in `context_config.yaml`.

### Axis Scoring (1D Model)

v0.4 uses a 1D score per axis mapped to word distributions. Each axis has a single linear model producing `raw_score ∈ [0,1]`, then converted to word probabilities.

**Feature → Axis Weights:**

| Feature | Scale (A) | Origin (B) | Energy (C) |
|---------|-----------|------------|------------|
| color_temperature | — | +0.2 | — |
| saturation | — | — | +0.3 |
| texture_grain | — | +0.4 | +0.2 |
| edge_density | -0.4 | +0.3 | +0.4 |
| contrast | +0.2 | — | +0.3 |
| orientation_bias | — | +0.2 | +0.1 |
| symmetry | — | +0.3 | -0.2 |
| negative_space | +0.5 | — | -0.3 |
| focal_clarity | -0.2 | — | — |

**Axis Vocabulary:**

| Axis | Words (0→1) |
|------|-------------|
| Scale (A) | intimate, room, hall, vast, cosmic |
| Origin (B) | organic, natural, hybrid, mechanical, synthetic |
| Energy (C) | still, breathing, flowing, rhythmic, churning |

**Word Centers:** `[0.1, 0.3, 0.5, 0.7, 0.9]`

**Distribution Calculation:**

```python
def compute_axis_distribution(features, weights, word_centers, words):
    """Returns probability distribution over words + clarity."""
    # Compute raw axis score
    raw_score = sum(features.get(f, 0) * w for f, w in weights.items())
    raw_score = clamp(raw_score, 0.0, 1.0)
    
    # Convert to word probabilities via inverse distance + softmax
    distances = [abs(raw_score - c) for c in word_centers]
    inv_distances = [1 / (d + 0.1) for d in distances]
    probs = softmax(inv_distances, temperature=0.5)
    
    # Clarity = margin between top two
    sorted_probs = sorted(probs, reverse=True)
    clarity = sorted_probs[0] - sorted_probs[1]
    
    return {
        "distribution": dict(zip(words, probs)),
        "clarity": clarity
    }
```

**Phase 3a Output:**

```python
@dataclass
class Phase3aResult:
    scale: dict[str, float]    # word → probability
    origin: dict[str, float]
    energy: dict[str, float]
    clarity_scale: float
    clarity_origin: float
    clarity_energy: float
    confidence: float          # min(clarities)
    features: dict[str, float]
```

---

## Phase 3b: Object Detection (Modifier Distribution)

Detects objects using a local ML model, maps through a curated database to produce modifier distributions.

### Model Specification

| Aspect | Value |
|--------|-------|
| Model | MobileNet-SSD v2 |
| Runtime | ONNX Runtime (CPU, pinned version) |
| Size | ~20MB bundled weights |
| Classes | COCO 80 (subset mapped) |
| Preprocessing | Resize 300×300, INTER_LINEAR, RGB, /255 normalize |

### Detection Pipeline

```python
def detect_objects(image, model, config):
    # Fixed preprocessing for determinism
    resized = cv2.resize(image, (300, 300), interpolation=cv2.INTER_LINEAR)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    normalized = rgb.astype(np.float32) / 255.0
    
    # Inference
    detections = model.run(normalized)
    
    # Filter and sort
    objects = [
        {"class": d.class_name, "confidence": d.score, "area": d.bbox_area / image_area}
        for d in detections
        if d.score >= config.detection_threshold  # default 0.5
    ]
    
    return sorted(objects, key=lambda x: -x["confidence"])[:config.max_objects]  # default 5
```

### Concept Database

**Schema:**

```yaml
# object_concepts.yaml
dog:
  scale: room
  origin: organic
  energy: rhythmic
  weight: 1.0

tree:
  scale: vast
  origin: natural
  energy: breathing
  weight: 1.0

# ... ~30-40 curated entries
```

**Concept Aliases (synonyms):**

```yaml
# concept_aliases.yaml
vehicle: [car, truck, bus]
building: [house]
water_body: [boat]  # proxy detection
```

### Vote Weight Formula

```python
def compute_vote_weight(detection, concept):
    """
    Area-independent weighting.
    Large objects don't dominate; small salient objects count.
    """
    return detection["confidence"] * concept.weight
```

**Rationale:** Detection confidence already reflects model certainty. Concept weight is curated importance. Area caused background objects (walls, floors) to dominate.

### Modifier Distribution Calculation

```python
def compute_modifier_distributions(detected_objects, database, aliases):
    """Convert detections → probability distributions over words per axis."""
    
    axis_votes = {
        "scale": defaultdict(float),
        "origin": defaultdict(float),
        "energy": defaultdict(float)
    }
    
    for obj in detected_objects:
        obj_class = resolve_alias(obj["class"], aliases)
        if obj_class not in database:
            continue
        
        concept = database[obj_class]
        vote = obj["confidence"] * concept.weight
        
        if concept.scale:
            axis_votes["scale"][concept.scale] += vote
        if concept.origin:
            axis_votes["origin"][concept.origin] += vote
        if concept.energy:
            axis_votes["energy"][concept.energy] += vote
    
    # Normalize to distributions
    distributions = {}
    clarities = {}
    
    for axis, votes in axis_votes.items():
        if votes:
            total = sum(votes.values())
            dist = {word: v / total for word, v in votes.items()}
            # Pad missing words with 0
            for word in AXIS_WORDS[axis]:
                dist.setdefault(word, 0.0)
            distributions[axis] = dist
            
            # Clarity = top1 - top2
            sorted_probs = sorted(dist.values(), reverse=True)
            clarities[axis] = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else 1.0
        else:
            distributions[axis] = None
            clarities[axis] = 0.0
    
    return distributions, clarities
```

### Phase 3b Confidence (Concept-Level)

Confidence is based on **concept distribution clarity**, not raw detector scores:

```python
def compute_3b_confidence(clarities, distributions):
    """
    Concept-level confidence.
    High if detected objects produce clear, consistent concept signals.
    Low if objects conflict or are unmapped.
    """
    active_axes = [c for axis, c in clarities.items() if distributions.get(axis)]
    
    if not active_axes:
        return 0.0
    
    return min(active_axes)
```

**Phase 3b Output:**

```python
@dataclass
class Phase3bResult:
    enabled: bool
    detections: list[dict]
    distributions: dict[str, dict[str, float] | None]  # axis → word → prob
    clarities: dict[str, float]
    confidence: float  # min(clarities) at concept level
```

---

## Phase 3c: Fusion (Distribution Blending)

Blends base distributions (3a) with modifier distributions (3b) to produce final triplet.

### Blending Formula

```python
def fuse_distributions(base: Phase3aResult, modifier: Phase3bResult, config):
    """
    Blend 3a and 3b distributions, then select final words.
    
    w = fusion_strength × modifier_confidence × (1 - base_confidence)
    
    When base is confident: w → 0, trust base
    When base is uncertain and modifiers are confident: w → fusion_strength
    """
    
    fusion_strength = config.fusion_strength  # default 0.4
    
    # Compute blend weight
    w = fusion_strength * modifier.confidence * (1 - base.confidence)
    w = clamp(w, 0.0, fusion_strength)  # cap at fusion_strength
    
    final_triplet = []
    final_distributions = {}
    final_clarities = {}
    
    for axis in ["scale", "origin", "energy"]:
        base_dist = getattr(base, axis)  # dict word → prob
        mod_dist = modifier.distributions.get(axis)
        
        if mod_dist:
            # Blend distributions
            blended = {}
            for word in AXIS_WORDS[axis]:
                base_p = base_dist.get(word, 0.0)
                mod_p = mod_dist.get(word, 0.0)
                blended[word] = (1 - w) * base_p + w * mod_p
            
            # Renormalize (should already sum to 1, but ensure)
            total = sum(blended.values())
            blended = {k: v / total for k, v in blended.items()}
        else:
            # No modifier for this axis, use base
            blended = base_dist
        
        # Select winner
        winner = max(blended, key=blended.get)
        
        # Compute fused clarity
        sorted_probs = sorted(blended.values(), reverse=True)
        clarity = sorted_probs[0] - sorted_probs[1]
        
        final_triplet.append(winner)
        final_distributions[axis] = blended
        final_clarities[axis] = clarity
    
    # Final confidence
    final_confidence = min(final_clarities.values())
    
    return FusionResult(
        triplet=final_triplet,
        distributions=final_distributions,
        clarities=final_clarities,
        confidence=final_confidence,
        blend_weight=w
    )
```

### Fusion Behavior

| Base Confidence | Modifier Confidence | Blend Weight (w) | Behavior |
|-----------------|---------------------|------------------|----------|
| High (0.8) | High (0.8) | 0.4 × 0.8 × 0.2 = 0.064 | Base dominates |
| High (0.8) | Low (0.3) | 0.4 × 0.3 × 0.2 = 0.024 | Base dominates |
| Low (0.3) | High (0.8) | 0.4 × 0.8 × 0.7 = 0.224 | Significant blend |
| Low (0.3) | Low (0.3) | 0.4 × 0.3 × 0.7 = 0.084 | Slight blend, low confidence |

This is **smooth and continuous** — no sudden flips.

---

## Confidence & Fallback

### Combined Confidence

```python
# Probabilistic OR: enabled if either method is confident
enabled = (base.confidence >= 0.4) or (modifier.confidence >= 0.4)

# Combined confidence for downstream use
combined_confidence = fusion_result.confidence
```

### Fallback Triggers

| Condition | Action |
|-----------|--------|
| `combined_confidence < 0.4` | Use neutral triplet, `enabled=False` |
| Image < 64px either dimension | Skip all extraction, use neutral |
| Model load failure | Use 3a only (graceful degradation) |
| No objects detected AND 3a confidence < 0.4 | Use neutral triplet |

### Neutral Triplet

```python
NEUTRAL_TRIPLET = ["hall", "hybrid", "flowing"]
```

---

## Debug Output

```json
{
  "context": {
    "triplet": ["vast", "organic", "breathing"],
    "confidence": 0.68,
    "enabled": true,
    
    "environment": {
      "model_sha256": "a1b2c3...",
      "ort_version": "1.16.0",
      "opencv_version": "4.8.0",
      "config_hash": "d4e5f6..."
    },
    
    "phase_3a": {
      "distributions": {
        "scale": {"intimate": 0.08, "room": 0.15, "hall": 0.42, "vast": 0.28, "cosmic": 0.07},
        "origin": {"organic": 0.51, "natural": 0.28, "hybrid": 0.12, "mechanical": 0.06, "synthetic": 0.03},
        "energy": {"still": 0.05, "breathing": 0.45, "flowing": 0.32, "rhythmic": 0.12, "churning": 0.06}
      },
      "clarities": {"scale": 0.14, "origin": 0.23, "energy": 0.13},
      "confidence": 0.13,
      "features": {
        "color_temperature": 0.65,
        "saturation": 0.42,
        "texture_grain": 0.38,
        "edge_density": 0.22,
        "contrast": 0.55,
        "orientation_bias": -0.12,
        "symmetry": 0.31,
        "negative_space": 0.48,
        "focal_clarity": 0.61
      }
    },
    
    "phase_3b": {
      "enabled": true,
      "detections": [
        {"class": "tree", "confidence": 0.92, "area": 0.35},
        {"class": "bird", "confidence": 0.71, "area": 0.02}
      ],
      "distributions": {
        "scale": {"vast": 1.0},
        "origin": {"natural": 0.56, "organic": 0.44},
        "energy": {"breathing": 0.56, "flowing": 0.44}
      },
      "clarities": {"scale": 1.0, "origin": 0.12, "energy": 0.12},
      "confidence": 0.12
    },
    
    "fusion": {
      "blend_weight": 0.21,
      "distributions": {
        "scale": {"intimate": 0.06, "room": 0.12, "hall": 0.33, "vast": 0.43, "cosmic": 0.06},
        "origin": {"organic": 0.49, "natural": 0.34, "hybrid": 0.09, "mechanical": 0.05, "synthetic": 0.02},
        "energy": {"still": 0.04, "breathing": 0.47, "flowing": 0.34, "rhythmic": 0.10, "churning": 0.05}
      },
      "clarities": {"scale": 0.10, "origin": 0.15, "energy": 0.13},
      "shifts": ["scale: hall→vast"]
    }
  }
}
```

---

## Requirements

### Functional — Phase 3a (Visual Features)

| ID | Requirement |
|----|-------------|
| R1 | System shall extract 9 visual features from input image |
| R2 | Feature normalization shall use fixed calibration constants |
| R3 | System shall produce probability distributions over words for each axis |
| R4 | System shall compute clarity as top1 − top2 probability |
| R5 | System shall compute confidence as min(axis clarities) |
| R6 | All extraction shall use OpenCV only |

### Functional — Phase 3b (Object Detection)

| ID | Requirement |
|----|-------------|
| R7 | System shall use bundled local ONNX model |
| R8 | Model weights shall be versioned and SHA256-verified |
| R9 | Preprocessing shall use fixed resize algorithm (INTER_LINEAR) |
| R10 | Detection threshold shall be configurable (default 0.5) |
| R11 | Maximum detected objects shall be configurable (default 5) |
| R12 | Object→concept mapping shall be defined in `object_concepts.yaml` |
| R13 | Unmapped object classes shall be ignored |
| R14 | Vote weight shall be `confidence × concept_weight` (no area) |
| R15 | System shall produce modifier distributions over words per axis |
| R16 | Confidence shall be computed at concept level (min clarity of modifier distributions) |

### Functional — Fusion

| ID | Requirement |
|----|-------------|
| R17 | Fusion shall blend base and modifier distributions |
| R18 | Blend weight formula: `w = fusion_strength × mod_conf × (1 − base_conf)` |
| R19 | Fusion strength shall be configurable (default 0.4) |
| R20 | Final word shall be argmax of blended distribution |
| R21 | System shall produce exactly 3 context words (one per axis) |

### Functional — Confidence & Fallback

| ID | Requirement |
|----|-------------|
| R22 | System shall enable context if either 3a or 3b confidence ≥ 0.4 |
| R23 | System shall fall back to neutral triplet when final confidence < 0.4 |
| R24 | System shall function with 3a only if model fails to load |

### Determinism

| ID | Requirement |
|----|-------------|
| R25 | Output shall be deterministic for same image + same environment |
| R26 | Environment fingerprint shall be recorded in debug output |
| R27 | Model SHA256, ORT version, OpenCV version shall be logged |

### Integration

| ID | Requirement |
|----|-------------|
| R28 | Context extraction shall run after spatial analysis, before selection |
| R29 | Context output shall be included in pack generation debug JSON |
| R30 | CLI shall support `--show-context` flag |
| R31 | Triplet shall be stable under minor resize (±10%) |

### Bias Application

| ID | Requirement |
|----|-------------|
| R32 | Context shall bias selection via multiplicative tag weights |
| R33 | Bias multipliers shall range 0.8–1.2 |
| R34 | Synthesis method candidates shall have `tags` metadata |

---

## Edge Cases

| ID | Case | Expected Behavior |
|----|------|-------------------|
| E1 | Solid color image | Low 3a clarity, no 3b detections → likely neutral |
| E2 | Pure noise image | Low 3a clarity, no 3b detections → likely neutral |
| E3 | Image < 64px | Skip extraction → neutral |
| E4 | Grayscale image | color_temperature = 0.0, proceed normally |
| E5 | No objects detected | Use 3a only, blend weight = 0 |
| E6 | Objects detected but all unmapped | Use 3a only, blend weight = 0 |
| E7 | Model fails to load | Log warning, use 3a only |
| E8 | Single dominant object | Object concepts blend in proportionally |
| E9 | Conflicting objects (dog + machine) | Mixed modifier distribution, clarity drops |
| E10 | 10% resize | Triplet should remain stable |
| E11 | 3a confident, 3b confident, different result | Base dominates (low blend weight) |

---

## Not In Scope

- Cloud API or external service calls
- User-facing context editing UI
- Per-generator context override
- Runtime model switching
- Custom model training
- Video/animation input
- Cross-machine determinism guarantees

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Spatial analysis pipeline | ✅ Done | |
| OpenCV | ✅ Already used | Pin version |
| ONNX Runtime | ⬜ New dependency | Pin version, ~5MB |
| MobileNet-SSD weights | ⬜ New asset | ~20MB, SHA256 verified |
| object_concepts.yaml | ⬜ New file | ~30-40 entries |
| concept_aliases.yaml | ⬜ New file | ~5-10 synonym groups |
| context_config.yaml | ⬜ New file | Weights, thresholds, fusion_strength |
| Candidate tags metadata | ⬜ Needs implementation | R34 |

---

## Test Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit: Feature extraction | 9 features with known inputs |
| Unit: Distribution calculation | Softmax, clarity |
| Unit: Object detection | Mock model, known outputs |
| Unit: Concept lookup | Database queries, aliases, unmapped |
| Unit: Modifier aggregation | Vote weighting, multi-object |
| Unit: Fusion blending | Weight calculation, distribution math |
| Integration: Full pipeline | Image → triplet → bias |
| Determinism | Same image + env, multiple runs |
| Stability | 10% resize → same triplet |
| Edge cases | E1–E11 |
| Golden set | 10 reference images with expected triplets |

---

## Phases (Proposed)

| Phase | Deliverable | Verify |
|-------|-------------|--------|
| 1 | Visual feature extraction + distributions (3a) | `pytest tests/test_context_features.py` |
| 2 | ONNX model integration + detection pipeline | `pytest tests/test_context_detection.py` |
| 3 | Concept database + modifier distributions | `pytest tests/test_context_concepts.py` |
| 4 | Distribution blending + fusion | `pytest tests/test_context_fusion.py` |
| 5 | CLI integration + debug output | `imaginarium analyze --show-context test.jpg` |
| 6 | Golden image validation + stability | `pytest tests/test_context_golden.py` |

---

## Changelog

| Version | Changes |
|---------|---------|
| 0.1 | Initial draft |
| 0.2 | AI2 feedback: softmax scoring, explicit normalization, debug schema |
| 0.3 | Constraint clarified (local ML allowed), added object detection layer |
| 0.4 | AI2 feedback: distribution blending, concept-level confidence, area-independent voting, determinism scope |

---

*Spec version 0.4 — APPROVED*
