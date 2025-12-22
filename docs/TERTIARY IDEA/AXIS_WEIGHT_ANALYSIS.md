# Axis Weight Table Analysis

**Purpose:** Validate that the feature→axis weight mappings produce sensible score ranges and don't have degenerate behavior.

---

## Current Weight Table

| Feature | Range | Scale (A) | Origin (B) | Energy (C) |
|---------|-------|-----------|------------|------------|
| color_temperature | -1.0–1.0 | — | +0.2 | — |
| saturation | 0.0–1.0 | — | — | +0.3 |
| texture_grain | 0.0–1.0 | — | +0.4 | +0.2 |
| edge_density | 0.0–1.0 | -0.4 | +0.3 | +0.4 |
| contrast | 0.0–1.0 | +0.2 | — | +0.3 |
| orientation_bias | -1.0–1.0 | — | +0.2 | +0.1 |
| symmetry | 0.0–1.0 | — | +0.3 | -0.2 |
| negative_space | 0.0–1.0 | +0.5 | — | -0.3 |
| focal_clarity | 0.0–1.0 | -0.2 | — | — |

---

## Axis A (Scale): intimate ↔ cosmic

**Contributing features:**
- edge_density: -0.4 (dense edges → intimate)
- contrast: +0.2 (high contrast → vast)
- negative_space: +0.5 (more space → vast)
- focal_clarity: -0.2 (focused → intimate)

**Score range analysis:**

```
Minimum (intimate scenario):
  edge_density=1.0 × -0.4 = -0.4
  contrast=0.0 × +0.2 = 0.0
  negative_space=0.0 × +0.5 = 0.0
  focal_clarity=1.0 × -0.2 = -0.2
  RAW TOTAL = -0.6 → clamped to 0.0 ✓

Maximum (cosmic scenario):
  edge_density=0.0 × -0.4 = 0.0
  contrast=1.0 × +0.2 = 0.2
  negative_space=1.0 × +0.5 = 0.5
  focal_clarity=0.0 × -0.2 = 0.0
  RAW TOTAL = 0.7 → valid ✓

Neutral (mid-range features):
  edge_density=0.5 × -0.4 = -0.2
  contrast=0.5 × +0.2 = 0.1
  negative_space=0.5 × +0.5 = 0.25
  focal_clarity=0.5 × -0.2 = -0.1
  RAW TOTAL = 0.05 → biased toward intimate ⚠️
```

**Issue found:** Neutral features produce score ~0.05, which maps to "intimate" (center 0.1). This means the axis has an **intimate bias** — images with average features will tend toward intimate.

**Recommendation:** Add a +0.4 baseline offset to center neutral at 0.45 (→ "hall").

```python
# Corrected
scale_score = baseline + sum(features[f] * w for f, w in weights.items())
scale_baseline = 0.4  # centers neutral at ~0.45
```

---

## Axis B (Origin): organic ↔ synthetic

**Contributing features:**
- color_temperature: +0.2 (warm → organic, but range is -1 to 1)
- texture_grain: +0.4 (grainy → organic)
- edge_density: +0.3 (dense edges → mechanical)
- orientation_bias: +0.2 (strong V/H → mechanical)
- symmetry: +0.3 (symmetric → mechanical)

**Score range analysis:**

```
Minimum (organic scenario):
  color_temperature=1.0 × +0.2 = 0.2 (warm)
  texture_grain=1.0 × +0.4 = 0.4
  edge_density=0.0 × +0.3 = 0.0
  orientation_bias=-1.0 × +0.2 = -0.2
  symmetry=0.0 × +0.3 = 0.0
  RAW TOTAL = 0.4 → maps to "natural" (0.3) ⚠️

Maximum (synthetic scenario):
  color_temperature=-1.0 × +0.2 = -0.2 (cool)
  texture_grain=0.0 × +0.4 = 0.0
  edge_density=1.0 × +0.3 = 0.3
  orientation_bias=1.0 × +0.2 = 0.2
  symmetry=1.0 × +0.3 = 0.3
  RAW TOTAL = 0.6 → maps to "mechanical" (0.7) ✓

Neutral:
  all features at midpoint
  RAW TOTAL ≈ 0.35 → maps to "natural/hybrid" boundary ✓
```

**Issue found:** Even extreme organic inputs only reach 0.4, never hitting "organic" (0.1). The organic end is unreachable.

**Recommendation:** 
1. Flip sign on color_temperature contribution: warm should REDUCE the score (toward organic end)
2. Add negative baseline to shift range down

```python
# Corrected weights for Origin
color_temperature: -0.15  # warm (positive) → lower score → organic
texture_grain: -0.3       # grainy → organic (lower)
edge_density: +0.3        # edges → mechanical (higher)
orientation_bias: +0.2    # structured → mechanical
symmetry: +0.25           # symmetric → mechanical

origin_baseline = 0.5     # start at hybrid
```

---

## Axis C (Energy): still ↔ churning

**Contributing features:**
- saturation: +0.3 (saturated → energetic)
- texture_grain: +0.2 (grainy → churning)
- edge_density: +0.4 (dense → energetic)
- contrast: +0.3 (high contrast → energetic)
- orientation_bias: +0.1 (structured → rhythmic)
- symmetry: -0.2 (symmetric → still)
- negative_space: -0.3 (space → still)

**Score range analysis:**

```
Minimum (still scenario):
  saturation=0.0 × +0.3 = 0.0
  texture_grain=0.0 × +0.2 = 0.0
  edge_density=0.0 × +0.4 = 0.0
  contrast=0.0 × +0.3 = 0.0
  orientation_bias=0.0 × +0.1 = 0.0
  symmetry=1.0 × -0.2 = -0.2
  negative_space=1.0 × -0.3 = -0.3
  RAW TOTAL = -0.5 → clamped to 0.0 ✓

Maximum (churning scenario):
  saturation=1.0 × +0.3 = 0.3
  texture_grain=1.0 × +0.2 = 0.2
  edge_density=1.0 × +0.4 = 0.4
  contrast=1.0 × +0.3 = 0.3
  orientation_bias=1.0 × +0.1 = 0.1
  symmetry=0.0 × -0.2 = 0.0
  negative_space=0.0 × -0.3 = 0.0
  RAW TOTAL = 1.3 → clamped to 1.0 ✓

Neutral:
  all features at midpoint (0.5 or 0.0 for bias features)
  saturation=0.5 × +0.3 = 0.15
  texture_grain=0.5 × +0.2 = 0.1
  edge_density=0.5 × +0.4 = 0.2
  contrast=0.5 × +0.3 = 0.15
  orientation_bias=0.0 × +0.1 = 0.0
  symmetry=0.5 × -0.2 = -0.1
  negative_space=0.5 × -0.3 = -0.15
  RAW TOTAL = 0.35 → maps to "breathing/flowing" boundary ✓
```

**Analysis:** Energy axis looks well-balanced. Full range is achievable, neutral lands in the middle.

---

## Summary of Issues

| Axis | Issue | Severity | Fix |
|------|-------|----------|-----|
| Scale (A) | Neutral bias toward intimate | Medium | Add +0.4 baseline |
| Origin (B) | "Organic" end unreachable | High | Flip color_temp sign, add baseline, adjust weights |
| Energy (C) | None | — | Keep as-is |

---

## Corrected Weight Table

```yaml
# context_config.yaml

axis_weights:
  scale:
    baseline: 0.4
    edge_density: -0.35
    contrast: +0.2
    negative_space: +0.45
    focal_clarity: -0.2

  origin:
    baseline: 0.5
    color_temperature: -0.15  # warm → organic (lower score)
    texture_grain: -0.25      # grainy → organic
    edge_density: +0.25       # edges → mechanical
    orientation_bias: +0.15
    symmetry: +0.2

  energy:
    baseline: 0.0
    saturation: +0.3
    texture_grain: +0.2
    edge_density: +0.35
    contrast: +0.25
    orientation_bias: +0.1
    symmetry: -0.2
    negative_space: -0.25
```

---

## Validation Test Cases

These should be added to `test_context_features.py`:

```python
def test_scale_neutral_produces_hall():
    """Neutral features should produce 'hall' (middle of scale)."""
    features = {f: 0.5 for f in FEATURES}
    features["orientation_bias"] = 0.0  # centered
    result = compute_axis("scale", features)
    assert result["word"] == "hall"

def test_origin_warm_grainy_produces_organic():
    """Warm, grainy, low-edge image should produce 'organic'."""
    features = {
        "color_temperature": 0.8,  # warm
        "texture_grain": 0.9,      # grainy
        "edge_density": 0.1,       # few edges
        "orientation_bias": 0.0,   # no strong direction
        "symmetry": 0.2            # asymmetric
    }
    result = compute_axis("origin", features)
    assert result["word"] in ["organic", "natural"]

def test_energy_empty_produces_still():
    """Empty, desaturated, symmetric image should produce 'still'."""
    features = {
        "saturation": 0.1,
        "texture_grain": 0.1,
        "edge_density": 0.1,
        "contrast": 0.2,
        "orientation_bias": 0.0,
        "symmetry": 0.9,
        "negative_space": 0.8
    }
    result = compute_axis("energy", features)
    assert result["word"] == "still"
```

---

*Analysis complete. Corrected weights ready for implementation.*
