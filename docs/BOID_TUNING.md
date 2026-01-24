# Boid Modulation Tuning Guide

This guide explains how to tune boid modulation scales for artistic control.

## Overview

Boid modulation adds organic, flocking-based variation to parameters. The **depth** knob in the UI controls overall intensity, while **scales** in SuperCollider control how much each parameter responds.

```
effective = base + (boid_offset × scale)
```

- `base` = your UI setting
- `boid_offset` = contribution from boids (-1 to +1, scaled by depth)
- `scale` = per-parameter sensitivity

## GEN Zone (Generator Parameters)

Located in `supercollider/core/osc_handlers.scd`

These scales are in **native units** (Hz, seconds, etc.) and apply to all 8 generator slots.

| Key | Default | Description |
|-----|---------|-------------|
| `\frequency` | 500 | Oscillator pitch: ±500 Hz (~1 octave) |
| `\cutoff` | 8000 | Filter cutoff: ±8000 Hz (half range) |
| `\resonance` | 0.5 | Filter resonance: ±50% |
| `\attack` | 1.0 | Envelope attack: ±1 second |
| `\decay` | 5.0 | Envelope decay: ±5 seconds |
| `\custom` | 0.5 | Custom params: ±50% |

### Examples

```supercollider
// Disable frequency modulation entirely
~genBoidScales[\frequency] = 0;

// Subtle pitch wobble
~genBoidScales[\frequency] = 100;

// Full filter sweep
~genBoidScales[\cutoff] = 16000;

// Gentle resonance (avoid screech)
~genBoidScales[\resonance] = 0.3;
```

## Unified Buses (Mod/Channel/FX)

Located in `supercollider/core/bus_unification.scd`

These scales are **percentages** (0.0-1.0) of the parameter's range.

### Mod Slot Parameters (4 slots × 7 params)

| Key Pattern | Default | Description |
|-------------|---------|-------------|
| `\mod_N_p0` | 0.4 | Rate: ±40% |
| `\mod_N_p1` | 0.5 | Shape/AtkA: ±50% |
| `\mod_N_p2` | 0.5 | Pattern/AtkB: ±50% |
| `\mod_N_p3` | 0.5 | Rotate/AtkC: ±50% |
| `\mod_N_p4` | 0.5 | WaveA/AtkD: ±50% |
| `\mod_N_p5` | 0.5 | WaveB/RelA: ±50% |
| `\mod_N_p6` | 0.5 | WaveC/RelB: ±50% |

Where N = 1, 2, 3, or 4

### Channel Parameters (8 channels × 3 params)

| Key Pattern | Default | Description |
|-------------|---------|-------------|
| `\chan_N_echo` | 0.4 | Echo send: ±40% |
| `\chan_N_verb` | 0.4 | Reverb send: ±40% |
| `\chan_N_pan` | 0.6 | Pan: ±60% of -1 to +1 |

Where N = 1-8

### FX: Heat

| Key | Default | Description |
|-----|---------|-------------|
| `\fx_heat_drive` | 0.5 | ±50% |
| `\fx_heat_mix` | 0.4 | ±40% |

### FX: Echo

| Key | Default | Description |
|-----|---------|-------------|
| `\fx_echo_time` | 0.3 | ±30% (low - time jumps are jarring) |
| `\fx_echo_feedback` | 0.5 | ±50% |
| `\fx_echo_tone` | 0.6 | ±60% |
| `\fx_echo_wow` | 0.5 | ±50% |
| `\fx_echo_spring` | 0.4 | ±40% |
| `\fx_echo_verbSend` | 0.4 | ±40% |

### FX: Reverb

| Key | Default | Description |
|-----|---------|-------------|
| `\fx_verb_size` | 0.4 | ±40% |
| `\fx_verb_decay` | 0.5 | ±50% |
| `\fx_verb_tone` | 0.6 | ±60% |

### FX: Dual Filter

| Key | Default | Description |
|-----|---------|-------------|
| `\fx_fb_drive` | 0.5 | ±50% |
| `\fx_fb_freq1` | 0.6 | ±60% (musical) |
| `\fx_fb_freq2` | 0.6 | ±60% (musical) |
| `\fx_fb_reso1` | 0.4 | ±40% (can screech) |
| `\fx_fb_reso2` | 0.4 | ±40% (can screech) |
| `\fx_fb_syncAmt` | 0.5 | ±50% |
| `\fx_fb_harmonics` | 0.5 | ±50% |
| `\fx_fb_mix` | 0.4 | ±40% |

### Examples

```supercollider
// Disable echo time modulation (prevents jarring jumps)
~boidScales[\fx_echo_time] = 0;

// Full send swing on channel 1
~boidScales[\chan_1_echo] = 1.0;

// Gentle pan movement
~boidScales[\chan_1_pan] = 0.3;

// Disable all reverb modulation
~boidScales[\fx_verb_size] = 0;
~boidScales[\fx_verb_decay] = 0;
~boidScales[\fx_verb_tone] = 0;
```

## Interaction with Mod Matrix

Boid modulation **adds** to existing mod matrix modulation:

```
effective = base + mod_matrix_contribution + boid_contribution
```

Both are clamped to the parameter's valid range. If you're using heavy mod matrix routing, consider reducing boid scales to leave headroom.

## Live Tuning Workflow

1. Start with boids enabled, depth at 50%
2. Listen to which parameters feel too dramatic
3. Reduce those scales in SC:
   ```supercollider
   ~genBoidScales[\cutoff] = 4000;  // halve filter sweep
   ```
4. Increase depth to 100% and verify it doesn't clip constantly
5. Save your preferred scales (they persist until SC restart)

## Saving Custom Scales

Scales reset when SC restarts. To persist custom scales, add them to `supercollider/core/init.scd` after the standard initialization:

```supercollider
// Custom boid scales (add at end of init.scd)
~genBoidScales[\frequency] = 250;
~boidScales[\fx_echo_time] = 0;
```

## Disable Boid Modulation Per Zone

Use the UI zone toggles (GEN, MOD, CHN, FX) to disable entire zones, or set individual scales to 0 for fine-grained control.
