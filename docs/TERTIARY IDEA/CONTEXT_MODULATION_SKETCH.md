# Context-Driven Modulation Biasing

**Status:** Design sketch (future enhancement)  
**Prerequisite:** Tertiary Musical Context Layer (v0.4) implemented  
**Target:** Post-release-1, after core context→generator selection is validated

---

## Overview

The v0.4 spec covers how context triplets bias **generator selection** via tag multipliers. This document sketches how context could additionally influence **modulation parameters** — making the entire pack feel cohesive not just in sound choice but in movement and behavior.

---

## Current Scope (v0.4)

Context influences:
- ✅ Which generators are selected (via tag biases)
- ❌ How those generators are modulated (not yet)

---

## Proposed Extension

Context triplet axes map to modulation characteristics:

| Axis | Word | Modulation Influence |
|------|------|---------------------|
| **Energy** | still | Disable or minimize LFO, static parameters |
| | breathing | Slow LFO (0.1–0.3 Hz), gentle depth |
| | flowing | Medium LFO (0.3–0.8 Hz), moderate depth |
| | rhythmic | Clock-synced LFO, quantized, medium-fast |
| | churning | Fast LFO (2–8 Hz), high depth, multiple sources |
| **Scale** | intimate | Narrow mod ranges, subtle movement |
| | room–hall | Default mod ranges |
| | vast–cosmic | Wide mod ranges, dramatic sweeps |
| **Origin** | organic | Irregular/humanized timing, slight drift |
| | mechanical | Precise timing, quantized, locked |
| | synthetic | Extreme ranges, non-natural shapes |

---

## Implementation Sketch

### ModulationProfile dataclass

```python
@dataclass
class ModulationProfile:
    """Modulation parameters influenced by context."""
    
    # LFO characteristics
    lfo_rate_range: tuple[float, float]  # Hz min/max
    lfo_depth_range: tuple[float, float] # 0.0–1.0 min/max
    lfo_sync_preference: str             # "free", "tempo", "clock"
    
    # Humanization
    timing_drift: float                  # 0.0–1.0, random timing variation
    parameter_wander: float              # 0.0–1.0, slow random walk on params
    
    # Range scaling
    mod_range_multiplier: float          # scales all mod depths
    
    # Shape preferences
    preferred_waveforms: list[str]       # ["sine", "triangle", "square", etc.]
```

### Context → ModulationProfile Mapping

```python
ENERGY_PROFILES = {
    "still": ModulationProfile(
        lfo_rate_range=(0.0, 0.05),
        lfo_depth_range=(0.0, 0.1),
        lfo_sync_preference="free",
        timing_drift=0.0,
        parameter_wander=0.02,  # tiny drift for life
        mod_range_multiplier=0.3,
        preferred_waveforms=["sine"]
    ),
    "breathing": ModulationProfile(
        lfo_rate_range=(0.05, 0.3),
        lfo_depth_range=(0.1, 0.4),
        lfo_sync_preference="free",
        timing_drift=0.1,
        parameter_wander=0.1,
        mod_range_multiplier=0.6,
        preferred_waveforms=["sine", "triangle"]
    ),
    "flowing": ModulationProfile(
        lfo_rate_range=(0.2, 0.8),
        lfo_depth_range=(0.2, 0.5),
        lfo_sync_preference="free",
        timing_drift=0.15,
        parameter_wander=0.15,
        mod_range_multiplier=0.8,
        preferred_waveforms=["sine", "triangle", "smooth_random"]
    ),
    "rhythmic": ModulationProfile(
        lfo_rate_range=(0.5, 4.0),
        lfo_depth_range=(0.3, 0.7),
        lfo_sync_preference="clock",
        timing_drift=0.0,
        parameter_wander=0.0,
        mod_range_multiplier=1.0,
        preferred_waveforms=["square", "triangle", "saw"]
    ),
    "churning": ModulationProfile(
        lfo_rate_range=(1.0, 10.0),
        lfo_depth_range=(0.4, 0.9),
        lfo_sync_preference="free",
        timing_drift=0.3,
        parameter_wander=0.25,
        mod_range_multiplier=1.3,
        preferred_waveforms=["noise", "sample_hold", "triangle"]
    )
}

SCALE_MODIFIERS = {
    "intimate": {"mod_range_multiplier": 0.5},
    "room": {"mod_range_multiplier": 0.7},
    "hall": {"mod_range_multiplier": 1.0},
    "vast": {"mod_range_multiplier": 1.3},
    "cosmic": {"mod_range_multiplier": 1.6}
}

ORIGIN_MODIFIERS = {
    "organic": {"timing_drift": 0.2, "parameter_wander": 0.15},
    "natural": {"timing_drift": 0.1, "parameter_wander": 0.1},
    "hybrid": {},  # no modification
    "mechanical": {"timing_drift": 0.0, "parameter_wander": 0.0, "lfo_sync_preference": "clock"},
    "synthetic": {"mod_range_multiplier": 1.4, "preferred_waveforms": ["square", "saw", "sample_hold"]}
}
```

### Profile Composition

```python
def compute_modulation_profile(context_triplet: list[str]) -> ModulationProfile:
    """Compose final modulation profile from context triplet."""
    
    scale_word, origin_word, energy_word = context_triplet
    
    # Start with energy-based profile (most influential)
    profile = copy(ENERGY_PROFILES[energy_word])
    
    # Apply scale modifier
    scale_mod = SCALE_MODIFIERS.get(scale_word, {})
    for key, value in scale_mod.items():
        if key == "mod_range_multiplier":
            profile.mod_range_multiplier *= value
        else:
            setattr(profile, key, value)
    
    # Apply origin modifier
    origin_mod = ORIGIN_MODIFIERS.get(origin_word, {})
    for key, value in origin_mod.items():
        if key == "mod_range_multiplier":
            profile.mod_range_multiplier *= value
        elif key == "preferred_waveforms":
            # Intersect or blend waveform preferences
            profile.preferred_waveforms = blend_waveforms(
                profile.preferred_waveforms, value
            )
        else:
            setattr(profile, key, value)
    
    return profile
```

---

## Integration Points

### 1. Pack Generation

When generating a pack, compute `ModulationProfile` and store in pack metadata:

```json
{
  "pack_name": "Misty Forest",
  "context": {
    "triplet": ["vast", "organic", "breathing"],
    "modulation_profile": {
      "lfo_rate_range": [0.05, 0.3],
      "lfo_depth_range": [0.1, 0.4],
      "timing_drift": 0.2,
      "mod_range_multiplier": 1.04
    }
  }
}
```

### 2. Mod Source Initialization

When a pack loads, apply profile to mod sources:

```python
def initialize_mod_sources(profile: ModulationProfile):
    for mod_slot in mod_sources:
        # Set rate within profile range
        mod_slot.rate = random.uniform(*profile.lfo_rate_range)
        
        # Set depth within profile range
        mod_slot.depth = random.uniform(*profile.lfo_depth_range)
        
        # Choose waveform from preferences
        mod_slot.waveform = random.choice(profile.preferred_waveforms)
        
        # Apply sync preference
        if profile.lfo_sync_preference == "clock":
            mod_slot.sync_to_clock()
```

### 3. Mod Matrix Routing

Profile influences which parameters get modulated and how much:

```python
def suggest_mod_routing(profile: ModulationProfile, generator_params: list[str]):
    """Suggest mod matrix routing based on profile."""
    
    suggestions = []
    
    if profile.mod_range_multiplier > 1.0:
        # Wide, dramatic — modulate cutoff and pan
        suggestions.append(("lfo1", "cutoff", profile.lfo_depth_range[1]))
        suggestions.append(("lfo2", "pan", 0.3))
    
    if profile.timing_drift > 0:
        # Organic — modulate pitch slightly
        suggestions.append(("lfo3", "pitch", 0.02 * profile.timing_drift))
    
    if "churning" in str(profile):
        # Chaotic — multi-target modulation
        suggestions.append(("lfo1", "cutoff", 0.6))
        suggestions.append(("lfo2", "resonance", 0.4))
        suggestions.append(("lfo3", "amp", 0.3))
    
    return suggestions
```

---

## Example Scenarios

### Scenario 1: Misty Forest

```
Context: ["vast", "organic", "breathing"]

Energy (breathing):
  - LFO rate: 0.05–0.3 Hz (slow)
  - LFO depth: 10–40%
  - Free-running (not clock synced)
  - Preferred shapes: sine, triangle

Scale (vast):
  - Range multiplier: 1.3× (wider sweeps)

Origin (organic):
  - Timing drift: 0.2 (humanized)
  - Parameter wander: 0.15

Result:
  - Slow, drifting filter sweeps
  - Gentle pitch wobble
  - Nothing locked or quantized
  - Wide, dramatic range
```

### Scenario 2: Factory Floor

```
Context: ["hall", "mechanical", "rhythmic"]

Energy (rhythmic):
  - LFO rate: 0.5–4.0 Hz (medium-fast)
  - LFO depth: 30–70%
  - Clock-synced
  - Preferred shapes: square, triangle, saw

Scale (hall):
  - Range multiplier: 1.0× (default)

Origin (mechanical):
  - Timing drift: 0.0 (precise)
  - Parameter wander: 0.0 (static between beats)
  - Force clock sync

Result:
  - Locked, rhythmic gating
  - Hard-edged modulation shapes
  - No drift or wander
  - Industrial pulse feel
```

### Scenario 3: Deep Space

```
Context: ["cosmic", "synthetic", "flowing"]

Energy (flowing):
  - LFO rate: 0.2–0.8 Hz
  - LFO depth: 20–50%
  - Free-running
  - Preferred shapes: sine, triangle, smooth_random

Scale (cosmic):
  - Range multiplier: 1.6× (very wide)

Origin (synthetic):
  - Range multiplier: 1.4× (stacked: 1.6 × 1.4 = 2.24×!)
  - Preferred shapes: square, saw, sample_hold

Result:
  - Huge, sweeping modulation ranges
  - Mix of smooth and stepped shapes
  - Otherworldly, non-natural movement
  - Extreme parameter excursions
```

---

## Open Questions

1. **Where does this live?** Pack metadata only, or does it affect real-time Noise Engine state?

2. **User override?** Can user adjust mod sources after pack load, or are they locked to profile?

3. **Determinism:** Modulation profile is deterministic, but random.uniform calls in initialization are not. Need seed-based selection.

4. **Interaction with existing mod system:** Current Noise Engine has mod sources with user-controllable rate/depth. How do pack profiles interact?

---

## Dependencies

- Tertiary Musical Context Layer (v0.4) implemented
- Pack metadata schema extended
- Mod source initialization hook in pack loader

---

## Not In Scope (This Sketch)

- Real-time context re-analysis
- User-facing profile editor
- Per-generator modulation profiles
- Adaptive profiles that change over time

---

*Sketch version 1.0 — Future enhancement, not blocking v0.4 implementation*
