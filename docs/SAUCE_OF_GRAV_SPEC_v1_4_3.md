# SauceOfGrav Modulator Specification

---
status: validated
version: 1.4.3
date: 2026-01-01
inspired_by: Buchla 266 Source of Uncertainty, NLC Sauce of Unce, Make Noise Wogglebug
validated: 2-minute Python simulation confirms wide motion, hub drift, phase space coverage
---

## What

SauceOfGrav is a 4-output coupled random voltage generator for Noise Engine. It combines gravitational physics metaphors with elastic tension dynamics to create interconnected, evolving modulation that feels mysterious but coherent.

**Core identity:** 4 outputs connected via a ring topology + central hub with inertia. Outputs use Van der Pol-style amplitude regulation for self-sustaining wide motion. RESO + hub feed inject energy continuously. The hub accumulates directional bias over time, then periodically refreshes (forgets).

**v1.4.3 goal:** Achieve **wide, divergent, self-sustaining motion** via Van der Pol negative damping + micro-asymmetries + CALM macro control for user-adjustable energy level without killing motion.

## Why

Current modulators:
- **LFO** — Periodic, predictable cyclic modulation
- **Sloth** — Chaotic, organic slow movement
- **ARSEq+** — Event-driven envelopes, rhythmic/sequenced

Missing: **Interconnected uncertainty** — multiple outputs that influence each other, creating emergent relationships and collective tendencies.

SauceOfGrav fills this gap with:
- Ring topology coupling (neighbour-to-neighbour) for phase offsets + travelling ripples
- Hub coupling for collective drift
- RESO energy floor for sustained motion (limit-cycle behaviour)
- Hub with inertia (2nd order dynamics)
- Rail bumpers (midrange linear, boundaries absorb momentum)

---

## Naming Convention

| Context | Value |
|---------|-------|
| Display name | `SauceOfGrav` |
| Internal ID | `sauce_of_grav` |
| Theme key | `accent_mod_sauce_of_grav` |
| Config key | `"SauceOfGrav"` (display) / `"sauce_of_grav"` (internal) |
| OSC path prefix | `/noise/mod/sauce_of_grav/` |
| Accent color | Magenta `#FF00FF` |

**Lineage:** Buchla 266 → NLC Sauce of Unce → SauceOfGrav

---

## Feature Summary

| Feature | Description |
|---------|-------------|
| 4 coupled outputs | Connected via ring topology + hub coupling |
| Van der Pol damping | Negative damping near center (energy injection), positive near rails (dissipation) — creates wide self-sustaining motion |
| Hub with inertia | Hub has momentum + continuous feed from output "work" + overshoot impulses |
| Ring coupling | Neighbour springs create phase offsets + travelling ripples; slightly non-reciprocal for divergence |
| Micro-asymmetries | Per-node calibration trims + non-reciprocal ring + hub-modulated VDP threshold → butterfly-effect sensitivity |
| Resonance sustain | RESO energy floor + kickstart when system is starved |
| Rail bumpers | Midrange is linear; rails only absorb momentum near 0/1 |
| Periodic refresh | Optional discrete hub "forget" events layered on continuous damping |
| Manual reset | Clear hub bias + hub velocity immediately |

---

## Hub Controls

| Control | Type | Range | Description |
|---------|------|-------|-------------|
| CLK/FREE | Toggle | CLK / FREE | RATE timing mode (refresh events) |
| RATE | Knob | See below | How often refresh events occur |
| DEPTH | Knob | 0% – 100% | Forgetting intensity (continuous hub damping + refresh strength) |
| GRAVITY | Knob | 0% – 100% | Restoring field stiffness + hub influence on target |
| RESONANCE | Knob | 0% – 100% | Sustain/drive strength (energy floor) |
| EXCURSION | Knob | 0% – 100% | Range/expressiveness — how far hub_target can move from center |
| CALM | Bipolar knob | -100%..+100% | Macro feel: anticlockwise calms (more damping, less kick), clockwise wilds (less damping, more VDP); cannot kill motion |
| RESET | Button | Trigger | Immediate hub clear (mod matrix routable) |

### RATE Values

| Mode | Range | Notes |
|------|-------|-------|
| CLK | OFF, /64, /32, /16, /8, /4, /2, 1, x2, x4, x8, x16, x32 | Tempo-synced refresh events |
| FREE | OFF, 0.001Hz – 100Hz | Free-running refresh event rate |

**OFF behaviour:**
- No discrete refresh events
- Hub still experiences **continuous damping** set by DEPTH

### RATE Parameter Mapping

Stored as normalized float 0.0–1.0 with deadband for OFF:

```
rate_norm in [0.0 .. SAUCE_RATE_DEADBAND] → OFF (no refresh events)
rate_norm in (SAUCE_RATE_DEADBAND .. 1.0] → active range

For active range, remap to [0..1]:
  rate_active = (rate_norm - SAUCE_RATE_DEADBAND) / (1 - SAUCE_RATE_DEADBAND)

CLK mode: idx = round(rate_active × (len(MOD_CLOCK_RATES) - 1))
FREE mode: hz = exp_map(rate_active, SAUCE_FREE_RATE_MIN, SAUCE_FREE_RATE_MAX)
```

`MOD_CLOCK_RATES` contains only active rates (no OFF). OFF is provided exclusively by the deadband.

**`MOD_CLOCK_RATES` order (exact):**
```
['/64', '/32', '/16', '/8', '/4', '/2', '1', 'x2', 'x4', 'x8', 'x16', 'x32']
```
UI display order must match array order to ensure RATE knob behaviour is consistent.

### DEPTH Behaviour (dual role)

DEPTH controls **both**:

1. **Continuous hub damping** (always active):
   ```
   HUB_DAMP = DEPTH_DAMP_MIN + (depth_norm × (DEPTH_DAMP_MAX - DEPTH_DAMP_MIN))
   ```

2. **Discrete refresh fade** (when RATE is active):
   ```
   fade_factor = 0.95 - (depth_norm × 0.95)
   ```
   Applied to `hub_bias` and `hub_vel` on each refresh event.

---

## Per-Output Controls (×4)

| Control | Type | Range | Description |
|---------|------|-------|-------------|
| TENSION | Knob | 0% – 100% | Coupling tightness: loose (independent) → taut (strong hub+ring coupling) |
| MASS | Knob | 0% – 100% | Inertia: light (snappy) → heavy (slow, momentum-dominated) |
| POLARITY | Toggle | N / I | NORM (0→+1) or INV (0→-1) |

**UI label convention:** `TENS` and `MASS` for compact display. `N`/`I` for polarity.

---

## Output Range

Outputs are normalized floats (unipolar with inversion):
- **NORM (N):** 0.0 to +1.0
- **INV (I):** 0.0 to -1.0

**Polarity application (explicit transform):**
```
out_i_engine ∈ [0..1]           # internal physics state
out_i_final = out_i_engine      # NORM: pass through
out_i_final = -out_i_engine     # INV: negate (NOT 1 - out_i)
```

Matches LFO, Sloth, and ARSEq+ convention.

---

## Initial State

On load/init:
- `out_i = 0.5` for i = 1..4 (center position)
- `v_i = 0.0` for i = 1..4 (zero velocity)
- `hub_bias = 0.0` (neutral)
- `hub_vel = 0.0` (no hub momentum)

System immediately receives continuous noise, so movement begins.

---

## Physics Behaviour

### State Variables

Per output `i ∈ {1, 2, 3, 4}`:
- `out_i` — position (0..1)
- `v_i` — velocity (continuous)
- `prev_side` — previous sign of `(out_i - hub_target)` for crossing detection
- `overshoot_active` — boolean, true while tracking an overshoot event
- `overshoot_target_i` — latched hub_target value at crossing
- `overshoot_peak` — max signed excursion during active overshoot

Hub:
- `hub_bias` — directional bias (soft-limited)
- `hub_vel` — hub momentum

Kickstart (global):
- `kick_toggle` — alternates ±1 each kick (init: +1)
- `kick_index` — cycles 0..2 through kick patterns (init: 0)
- `kick_cooldown` — seconds until next kick allowed (init: 0)

**Note:** `hub_bias` and `hub_vel` are abstract state variables scaled for musical behaviour (not physical units).

### The Hub + Ring Model

```
        [1]
       /   \
      /     \
    [4]──[HUB]──[2]
      \     /
       \   /
        [3]

- Ring coupling: 1↔2, 2↔3, 3↔4, 4↔1 (neighbour springs)
- Hub coupling: each output ↔ hub (via TENSION)
- Ring creates phase offsets; hub creates collective drift
```

### Core Mappings

**Gravity influence (hub target scaling):**
```
gravity_influence = (1 - gravity_norm)
```

**Excursion gain (range/expressiveness):**
```
excursion_gain = EXCURSION_MIN + (excursion_norm × (EXCURSION_MAX - EXCURSION_MIN))
```

**Gravity influence on hub target (with excursion):**
```
hub_target_raw = 0.5 + (hub_bias × gravity_influence × excursion_gain)
hub_target = clamp(hub_target_raw, 0, 1)
```
- GRAVITY = 0%: hub_target follows hub_bias fully (scaled by excursion_gain, clamped)
- GRAVITY = 100%: hub_target fixed at 0.5 (hub influence removed)
- EXCURSION = 0%: reduced travel (hub_bias effect scaled down)
- EXCURSION = 100%: expanded travel (hub_bias effect scaled up)

**Note:** `hub_target` (clamped) is used consistently for both coupling forces AND overshoot detection. The raw value may exceed 0..1 but is never used directly.

**Gravity restoring stiffness (separate from influence):**
```
k_grav = GRAV_STIFF_BASE + (GRAV_STIFF_GAIN × gravity_norm)
```
GRAVITY tightens the restoring field without necessarily killing motion (RESO sustain prevents collapse).

**MASS → inertia (with calibration trim, v1.4.1):**
```
mass_eff_i = clamp(mass_norm_i + MASS_TRIM[i], 0, 1)
m_i = MASS_BASE + (MASS_GAIN × mass_eff_i)
```

**TENSION → coupling strengths (with calibration trim, v1.4.1):**
```
tension_eff_i = clamp(tension_norm_i + TENSION_TRIM[i], 0, 1)
k_hub_i  = HUB_COUPLE_BASE  + (HUB_COUPLE_GAIN  × (tension_eff_i ^ HUB_TENSION_EXP))
k_ring_i = RING_COUPLE_BASE + (RING_COUPLE_GAIN × (tension_eff_i ^ RING_TENSION_EXP))
```

**Calibration trims (static micro-asymmetries):**
```
TENSION_TRIM = [+0.012, -0.008, +0.015, -0.018]  # per-node, ±2% max
MASS_TRIM    = [-0.010, +0.014, -0.006, +0.011]  # per-node, ±2% max
```

**Intent:** Tiny per-node mismatches prevent phase-locking and create long-term divergence naturally. These are fixed constants, not user-facing parameters.

### CALM Macro Mapping (v1.4.3)

**CALM** is a bipolar macro that scales the system's energy level without being able to kill motion.

**Storage:** `calm_norm ∈ [0..1]` (0.5 = neutral, matches other params)

**Conversion to bipolar (physics use):**
```
calm_bi = 2 × calm_norm - 1    # → [-1..+1]
```

**Physics parameter:** `calm_bi ∈ [-1..+1]`
- `-1.0` = **Calm** (more damping, less VDP injection, reduced kick)
- `0.0` = **Normal** (v1.4.2 behaviour)
- `+1.0` = **Wild** (less damping, more VDP injection)

**Damping multiplier (piecewise linear):**
```
if calm_bi < 0:
    calm_damp_mul = lerp(1.0, CALM_DAMP_CALM, -calm_bi)
else:
    calm_damp_mul = lerp(1.0, CALM_DAMP_WILD, calm_bi)
```

**VDP injection multiplier:**
```
if calm_bi < 0:
    calm_vdp_mul = lerp(1.0, CALM_VDP_CALM, -calm_bi)
else:
    calm_vdp_mul = lerp(1.0, CALM_VDP_WILD, calm_bi)
```

**Kick scaling (calm side only):**
```
if calm_bi < 0:
    calm_kick_mul = lerp(1.0, CALM_KICK_CALM, -calm_bi)
else:
    calm_kick_mul = 1.0
```

**Damping coefficient (base, with CALM scaling):**
```
damping_base_i = (SAUCE_DAMPING_BASE + (SAUCE_DAMPING_TENSION × (1 - tension_eff_i))) × calm_damp_mul
```

### Van der Pol Amplitude Regulation (v1.4.0, enhanced v1.4.3)

**Core mechanism:** Negative damping when amplitude is low (inject energy), positive damping when amplitude is high (dissipate energy). This creates self-sustaining oscillation at a characteristic amplitude.

**Amplitude from center:**
```
amp_i = abs(out_i - 0.5)
```

**Hub-modulated VDP threshold (v1.4.1):**
```
hub_bias_norm = hub_bias / HUB_LIMIT
vdp_threshold_i = VDP_THRESHOLD × (1 + VDP_HUB_MOD × hub_bias_norm)
vdp_threshold_i = max(vdp_threshold_i, VDP_THRESHOLD_FLOOR)  # safety floor
```

**Safety:** The floor prevents pathological division or runaway if hub bias ever pushes threshold too low.

**Intent:** The VDP "preferred orbit size" breathes ±5% as the hub drifts, creating slowly evolving motion without changing the core engine.

**Van der Pol factor (with CALM scaling):**
```
vdp_factor_i = (VDP_INJECT × calm_vdp_mul) × (1 - (amp_i / vdp_threshold_i)^2)
```

- When `amp_i < vdp_threshold_i`: `vdp_factor_i > 0` → negative damping (energy injection)
- When `amp_i > vdp_threshold_i`: `vdp_factor_i < 0` → positive damping (energy dissipation)
- At `amp_i = vdp_threshold_i`: `vdp_factor_i = 0` → neutral (limit cycle amplitude)

**Effective damping:**
```
damping_effective_i = damping_base_i - vdp_factor_i
```

**Intent:** The system naturally seeks amplitude ≈ `vdp_threshold_i`. This replaces reliance on sparse events (overshoot, RESO alignment) for energy — the amplitude regulation is continuous and automatic.

### Neighbour Indices

Ring topology with wrap-around:
- `prev(1) = 4, prev(2) = 1, prev(3) = 2, prev(4) = 3`
- `next(1) = 2, next(2) = 3, next(3) = 4, next(4) = 1`

### Forces

**1) Gravity restoring (toward center):**
```
F_grav_i = k_grav × (0.5 - out_i)
```

**2) Hub coupling (toward hub target):**
```
F_hub_i = k_hub_i × (hub_target - out_i)
```

(hub_target is already clamped in the mapping step)

**3) Ring coupling (neighbour springs, non-reciprocal v1.4.1):**

Ring coupling has a slight directional bias to prevent phase-locking:
```
k_ring_fwd_i = k_ring_i × (1 + RING_SKEW)
k_ring_bwd_i = k_ring_i × (1 - RING_SKEW)

F_ring_i = k_ring_fwd_i × (out_next(i) - out_i) + k_ring_bwd_i × (out_prev(i) - out_i)
```

**Intent:** Non-reciprocal coupling (1.5% skew) is a classic route to rich dynamics. The asymmetry creates slow phase drift between outputs without affecting amplitude.

**4) Damping with Van der Pol (applied as velocity decay):**

Damping is applied multiplicatively to velocity each step (see loop step 7), using the effective damping that includes Van der Pol regulation:
```
v_i *= exp(-damping_effective_i × dt)
```

**Note:** When `damping_effective_i < 0` (near center), this becomes velocity amplification rather than decay — the core mechanism for energy injection.

**5) Noise injection (velocity):**
```
dv_noise ~ Normal(0, SAUCE_NOISE_RATE) × sqrt(dt)
v_i += dv_noise
```
Produces Brownian-like drift after integration.

### Boundary Behaviour (Rail Bumpers)

Midrange is linear. Rails only absorb momentum near extremes.

After position integration:

1. Hard clamp for safety:
   ```
   out_i = clamp(out_i, 0, 1)
   ```

2. Velocity absorption near rails:
   ```
   d = min(out_i, 1 - out_i)
   u = clamp((SAUCE_RAIL_ZONE - d) / SAUCE_RAIL_ZONE, 0, 1)
   v_i *= (1 - SAUCE_RAIL_ABSORB × u^2)
   ```

**Intent:** Big excursions remain big; rails only shape behaviour at extremes.

### Overshoot Definition

**Overshoot occurs when an output crosses its hub_target with velocity.**

**Per-output tracking state:**
Each output maintains overshoot tracking state:
- `prev_side` — previous sign of `(out_i - hub_target)` (+1, -1, or 0)
- `overshoot_active` — boolean, true while tracking an overshoot event
- `overshoot_target_i` — latched hub_target value at crossing
- `overshoot_peak` — max signed excursion beyond overshoot_target_i

**Detection and completion:**
- Crossing detected when `(out_i - hub_target)` changes sign (using clamped hub_target)
- Crossing only counts if `abs(v_i) >= SAUCE_VELOCITY_EPSILON` at the crossing step (prevents spurious events from numeric jitter)
- **On crossing, freeze the target:** `overshoot_target_i = hub_target` at the instant of crossing; set `overshoot_active = true`
- While active, track peak: let `e = out_i - overshoot_target_i`; if `abs(e) > abs(overshoot_peak)` then `overshoot_peak = e` (signed)
- **Completion:** An overshoot event completes when velocity sign flips relative to excursion direction
- On completion: emit `overshoot_i = clamp(overshoot_peak, -OVERSHOOT_MAX, +OVERSHOOT_MAX)` as impulse, then clear tracking state (`overshoot_active = false`, `overshoot_peak = 0`)

**Impulse semantics:** `overshoot_i` is an impulse — it is 0 on all steps except the step an overshoot event completes, where it equals the signed peak excursion for that event. This prevents overshoot from continuously pushing the hub.

**Note:** Since hub_target is clamped to 0..1, overshoot detection always uses a valid target within the output range. Freezing the target at crossing time ensures overshoot measurement is well-defined even as hub_target drifts.

### Resonance Sustain (RESO Energy Floor)

Resonance enforces a minimum motion energy (limit-cycle behaviour).

**Alignment factor (unchanged from v1.1.x):**

1. Calculate velocity for each output
2. Classify:
   - `abs(v_i) < SAUCE_VELOCITY_EPSILON` → stationary (excluded)
   - `v_i > SAUCE_VELOCITY_EPSILON` → moving up (+1)
   - `v_i < -SAUCE_VELOCITY_EPSILON` → moving down (-1)
3. Count outputs moving in dominant direction
4. Alignment factor:
   - 4 aligned → 1.0
   - 3 aligned → 0.5
   - 2 or fewer → 0.0

**Kinetic energy:**
```
E = Σ_i (0.5 × m_i × v_i^2)
```

**Energy floor:**
```
E_floor = RESO_FLOOR_MIN + (resonance_norm × (RESO_FLOOR_MAX - RESO_FLOOR_MIN))
```

**Drive direction:**
```
drive_dir = sign(Σ v_i over moving outputs)
if drive_dir == 0: drive_dir = +1
```

**Drive force injection:**

If `alignment_factor > 0` AND `E < E_floor`:
```
ΔE = E_floor - E
ΔE = clamp(ΔE, 0, RESO_DELTAE_MAX)
F_reso_i = drive_dir × alignment_factor × resonance_norm × RESO_DRIVE_GAIN × ΔE
```

**State-dependent rail attenuation (prevents pushing into rails):**
```
rail_attn_i = 1 - abs(2 × out_i - 1)     # 1 at center (out=0.5), 0 at rails (out=0 or 1)
rail_attn_i = rail_attn_i ^ RESO_RAIL_EXP
F_reso_i *= rail_attn_i
```

**Notes:**
- `ΔE` is used as a scalar drive magnitude; units are intentionally abstract (pseudo-physics for musical behaviour).
- `ΔE` is clamped to prevent excessive drive spikes when energy collapses hard.
- Apply `F_reso_i` only to outputs classified as moving in `drive_dir`; stationary or opposed outputs receive `F_reso_i = 0`.
- Rail attenuation reduces RESO drive near boundaries, preventing "flat-top/flat-bottom" modulation.

This is added to total force before acceleration.

**Note:** RESO contributes as a force term (mass affects response via division by `m_i` in the acceleration calculation).

**Intent:** RESO sustains motion — aligned movement becomes self-reinforcing instead of dying out. Rail attenuation ensures drive is strongest at center, weakest near rails.

### RESO Kickstart (Symmetry-Break, v1.4.0)

When the system is starved (no moving outputs or no alignment), the normal RESO path can't inject energy. Kickstart provides a symmetry-breaking impulse.

**Kickstart conditions (all must be true):**
- `resonance_norm > 0`
- `E < E_floor`
- AND (`moving_count == 0` OR `alignment_factor == 0`)
- AND `kick_cooldown == 0`

**Kickstart force:**
```
kick_mag = clamp(RESO_KICK_GAIN × (E_floor - E), 0, RESO_KICK_MAXF)

pattern cycles: [+1, -1, +1, -1], [+1, +1, -1, -1], [+1, -1, -1, +1]
F_kick_i = kick_toggle × pattern[kick_index][i] × kick_mag

kick_toggle *= -1
kick_index = (kick_index + 1) mod 3
kick_cooldown = RESO_KICK_COOLDOWN_S
```

**State variables for kickstart:**
- `kick_toggle` — alternates ±1 each kick (starts +1)
- `kick_index` — cycles through 3 patterns (starts 0)
- `kick_cooldown` — seconds until next kick allowed (decrements by dt each step)

**Notes:**
- Kick is added to F_total (not rail-attenuated; typically fires when near center anyway)
- Kick provides diversity via cycling patterns, preventing repetitive nudges
- Cooldown prevents kick spam when system is sluggish

### Hub Accumulation with Momentum (2nd Order Hub)

The hub is a dynamic system with inertia, fed by both overshoot impulses and continuous "work" from outputs.

**Hub impulse source (overshoot events):**
```
hub_impulse = OVERSHOOT_TO_HUB_GAIN × Σ overshoot_i
```
Where `overshoot_i` is the signed peak excursion impulse emitted on the step an overshoot completes (0 otherwise).

**Continuous hub feed (work term, v1.4.0):**

The hub also receives continuous energy from outputs "doing work" against the target:
```
e_i = out_i - hub_target          # signed offset from target
work_sum = Σ (e_i × v_i)          # positive when moving away, negative when returning
hub_feed = clamp(HUB_FEED_GAIN × work_sum, -HUB_FEED_MAX, +HUB_FEED_MAX)
```

**Intent:** This ensures hub_bias evolves continuously, not just from sparse overshoot events. When outputs move away from hub_target, they push the hub; when returning, they pull it back.

**Hub dynamics per step:**
```
hub_vel  += (hub_impulse + hub_feed) × dt
hub_vel  *= exp(-HUB_DAMP × dt)
hub_bias += hub_vel × dt
hub_bias  = HUB_LIMIT × tanh(hub_bias / HUB_LIMIT)
```

**DEPTH → HUB_DAMP mapping:**
```
HUB_DAMP = DEPTH_DAMP_MIN + (depth_norm × (DEPTH_DAMP_MAX - DEPTH_DAMP_MIN))
```

### Discrete Refresh Events (RATE/DEPTH)

Refresh events are optional, layered on top of continuous damping.

- If RATE is OFF: no refresh events (hub only experiences continuous damping)
- If RATE is active: refresh event occurs each period

**On refresh event:**
```
fade_factor = 0.95 - (depth_norm × 0.95)
hub_bias *= fade_factor
hub_vel  *= fade_factor
```

**Intent:** Continuous damping defines physical "friction"; refresh events are deliberate "memory clears" timed by RATE.

---

## Physics Simulation Loop (Explicit Ordering)

Runs at control rate with fixed `dt`.

```
1. Read params (gravity_norm, depth_norm, resonance_norm, excursion_norm, calm_norm,
   per-output tension_norm_i, mass_norm_i)
   
   Convert CALM to bipolar: calm_bi = 2 × calm_norm - 1

2. Compute CALM multipliers (v1.4.3):
   if calm_bi < 0:
       calm_damp_mul = lerp(1.0, CALM_DAMP_CALM, -calm_bi)
       calm_vdp_mul  = lerp(1.0, CALM_VDP_CALM, -calm_bi)
       calm_kick_mul = lerp(1.0, CALM_KICK_CALM, -calm_bi)
   else:
       calm_damp_mul = lerp(1.0, CALM_DAMP_WILD, calm_bi)
       calm_vdp_mul  = lerp(1.0, CALM_VDP_WILD, calm_bi)
       calm_kick_mul = 1.0

3. Compute mappings (with calibration trims):
   - gravity_influence = (1 - gravity_norm)
   - excursion_gain = EXCURSION_MIN + (excursion_norm × (EXCURSION_MAX - EXCURSION_MIN))
   - hub_target_raw = 0.5 + (hub_bias × gravity_influence × excursion_gain)
   - hub_target = clamp(hub_target_raw, 0, 1)
   - k_grav = GRAV_STIFF_BASE + (GRAV_STIFF_GAIN × gravity_norm)
   - mass_eff_i = clamp(mass_norm_i + MASS_TRIM[i], 0, 1)
   - m_i = MASS_BASE + (MASS_GAIN × mass_eff_i)
   - tension_eff_i = clamp(tension_norm_i + TENSION_TRIM[i], 0, 1)
   - k_hub_i = HUB_COUPLE_BASE + (HUB_COUPLE_GAIN × (tension_eff_i ^ HUB_TENSION_EXP))
   - k_ring_i = RING_COUPLE_BASE + (RING_COUPLE_GAIN × (tension_eff_i ^ RING_TENSION_EXP))
   - k_ring_fwd_i = k_ring_i × (1 + RING_SKEW)
   - k_ring_bwd_i = k_ring_i × (1 - RING_SKEW)
   - damping_base_i = (SAUCE_DAMPING_BASE + (SAUCE_DAMPING_TENSION × (1 - tension_eff_i))) × calm_damp_mul
   - HUB_DAMP = DEPTH_DAMP_MIN + (depth_norm × (DEPTH_DAMP_MAX - DEPTH_DAMP_MIN))

4. Compute Van der Pol effective damping (hub-modulated threshold, CALM-scaled):
   hub_bias_norm = hub_bias / HUB_LIMIT
   vdp_threshold_i = VDP_THRESHOLD × (1 + VDP_HUB_MOD × hub_bias_norm)
   vdp_threshold_i = max(vdp_threshold_i, VDP_THRESHOLD_FLOOR)
   amp_i = abs(out_i - 0.5)
   vdp_factor_i = (VDP_INJECT × calm_vdp_mul) × (1 - (amp_i / vdp_threshold_i)^2)
   damping_effective_i = damping_base_i - vdp_factor_i

5. Inject velocity noise:
   v_i += Normal(0, SAUCE_NOISE_RATE) × sqrt(dt)

6. Compute forces per output (non-reciprocal ring):
   F_grav_i = k_grav × (0.5 - out_i)
   F_hub_i = k_hub_i × (hub_target - out_i)
   F_ring_i = k_ring_fwd_i × (out_next(i) - out_i) + k_ring_bwd_i × (out_prev(i) - out_i)

7. Compute resonance (standard path):
   - Calculate alignment_factor, moving_count
   - Calculate E = Σ(0.5 × m_i × v_i^2)
   - E_floor = RESO_FLOOR_MIN + (resonance_norm × (RESO_FLOOR_MAX - RESO_FLOOR_MIN))
   - If alignment_factor > 0 AND E < E_floor:
       drive_dir = sign(Σ v_i over moving)
       ΔE = clamp(E_floor - E, 0, RESO_DELTAE_MAX)
       For each output i:
         If moving in drive_dir:
           F_reso_i = drive_dir × alignment_factor × resonance_norm × RESO_DRIVE_GAIN × ΔE
           rail_attn_i = (1 - abs(2 × out_i - 1)) ^ RESO_RAIL_EXP
           F_reso_i *= rail_attn_i
         Else: F_reso_i = 0
   - Else: F_reso_i = 0 for all i

8. Compute kickstart (if RESO path inactive, CALM-scaled):
   - Decrement kick_cooldown by dt (clamp to 0)
   - If resonance_norm > 0 AND E < E_floor AND (moving_count == 0 OR alignment_factor == 0) AND kick_cooldown == 0:
       kick_mag = clamp(RESO_KICK_GAIN × (E_floor - E), 0, RESO_KICK_MAXF) × calm_kick_mul
       pattern = KICK_PATTERNS[kick_index]
       F_kick_i = kick_toggle × pattern[i] × kick_mag
       kick_toggle *= -1
       kick_index = (kick_index + 1) mod 3
       kick_cooldown = RESO_KICK_COOLDOWN_S
   - Else: F_kick_i = 0 for all i

8. Apply acceleration:
   a_i = (F_grav_i + F_hub_i + F_ring_i + F_reso_i + F_kick_i) / m_i
   v_i += a_i × dt

9. Apply damping (Van der Pol effective):
   v_i *= exp(-damping_effective_i × dt)

10. Integrate position:
    out_i += v_i × dt

11. Apply rail bumpers:
    out_i = clamp(out_i, 0, 1)
    d = min(out_i, 1 - out_i)
    u = clamp((SAUCE_RAIL_ZONE - d) / SAUCE_RAIL_ZONE, 0, 1)
    v_i *= (1 - SAUCE_RAIL_ABSORB × u^2)

12. Overshoot detection (per-output tracking state):
    - Compute side = sign(out_i - hub_target)
    - Check for hub_target crossing: (side != 0) AND (prev_side != 0) AND (side != prev_side)
    - Crossing only counts if abs(v_i) >= SAUCE_VELOCITY_EPSILON
    - On valid crossing: overshoot_target_i = hub_target, overshoot_active = true
    - While active: e = out_i - overshoot_target_i; if abs(e) > abs(overshoot_peak): overshoot_peak = e
    - On velocity sign flip (completion): overshoot_i = clamp(overshoot_peak, -OVERSHOOT_MAX, +OVERSHOOT_MAX)
    - Clear tracking: overshoot_active = false, overshoot_peak = 0
    - overshoot_i is impulse: 0 on all other steps
    - Update prev_side: if side != 0 then prev_side = side (else leave unchanged)

13. Hub update (impulse + continuous feed):
    hub_impulse = OVERSHOOT_TO_HUB_GAIN × Σ overshoot_i
    e_i = out_i - hub_target
    work_sum = Σ (e_i × v_i)
    hub_feed = clamp(HUB_FEED_GAIN × work_sum, -HUB_FEED_MAX, +HUB_FEED_MAX)
    hub_vel += (hub_impulse + hub_feed) × dt
    hub_vel *= exp(-HUB_DAMP × dt)
    hub_bias += hub_vel × dt
    hub_bias = HUB_LIMIT × tanh(hub_bias / HUB_LIMIT)

14. Refresh event check:
    If RATE active AND period elapsed:
      fade_factor = 0.95 - (depth_norm × 0.95)
      hub_bias *= fade_factor
      hub_vel *= fade_factor

15. RESET handling:
    If RESET triggered:
      hub_bias = 0
      hub_vel = 0
      kick_cooldown = 0
      (output positions and velocities unchanged)
```

---

## Reset Behaviour

### Manual RESET (button or mod matrix trigger)

| What | On Reset |
|------|----------|
| Hub bias | Set to 0 |
| Hub velocity | Set to 0 |
| Output positions | **Unchanged** — continue from current value |
| Output velocities | **Unchanged** — no clicks |

Smooth transition — hub forgets tendencies, but outputs don't jump.

### RESET Button

- Located in hub section
- Red/warning colored (distinct from magenta accent)
- Clearly labeled `RESET`

### RESET via Mod Matrix

**Trigger semantics: Rising edge crossing 0.5**

- RESET fires when source value transitions from below 0.5 to above 0.5
- Single trigger per crossing (not continuous)
- Works with any modulator (LFO, ARSEq+, Sloth, another SauceOfGrav)

**Edge detection timing:** Edge detection is performed on the raw control-rate value (pre-display smoothing/decimation). One trigger per crossing regardless of UI refresh rate.

---

## Visual Feedback

### Hub Visualization
- Circular display showing center point + 4 orbiting dots
- Dots represent output positions relative to center
- Optional: ripple rings when resonance active

### Activity Indicator (per output)
- Horizontal bar showing current value
- Center line at 0.5 (neutral)
- Bar position shows drift from center

### 4-Trace Scope
- Shows all 4 output values over time
- Uses consistent 4-color scheme (same as other modulators)
- Downsampled for performance
- Updates at display refresh rate

---

## Mod Matrix Display

Grouped by slot with type headers (same as other modulators):

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│      LFO        │     Sloth       │   SauceOfGrav   │    ARSEq+       │
│     Slot 1      │     Slot 2      │     Slot 3      │     Slot 4      │
├────┬────┬────┬────┼────┬────┬────┬────┼────┬────┬────┬────┼────┬────┬────┬────┤
│  1 │  2 │  3 │  4 │  1 │  2 │  3 │  4 │  1 │  2 │  3 │  4 │  1 │  2 │  3 │  4 │
```

**Additional mod matrix destinations:**
- RESET (per SauceOfGrav instance) — rising edge trigger

---

## UI Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [2]  SauceOfGrav                                           [CLK|FREE]        │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐                                                                 │
│  │  HUB    │                                                                 │
│  │ ●     ● │   (RATE)  (DEPTH)  (GRAV)  (RESO)  (EXCUR)   [RESET]           │
│  │    ◉    │    /4      75%      50%     60%     50%      (red)              │
│  │ ●     ● │                                                                 │
│  └─────────┘                                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1  [▓▓▓▓░░░░░░]  (TENS)  (MASS)  [N]                                       │
│                                                                              │
│  2  [░░░░░▓▓▓▓░]  (TENS)  (MASS)  [N]                                       │
│                                                                              │
│  3  [▓▓░░░░░░░░]  (TENS)  (MASS)  [I]                                       │
│                                                                              │
│  4  [░░░░░░▓▓▓▓]  (TENS)  (MASS)  [N]                                       │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        4-TRACE SCOPE                                   │  │
│  │  ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│            Buchla 266 → NLC Sauce of Unce → SauceOfGrav                     │
└──────────────────────────────────────────────────────────────────────────────┘

Legend:
  (RATE)    Refresh event rate (divisions or Hz, with OFF deadband)
  (DEPTH)   Hub damping + refresh fade intensity
  (GRAV)    Restoring field stiffness + hub influence
  (RESO)    Sustain/drive strength (energy floor)
  (EXCUR)   Range/expressiveness — how far hub_target moves from center
  [RESET]   Manual reset button (red/warning color)
  [▓░░░░]   Activity indicator (shows output position, center line at 0.5)
  (TENS)    Tension knob — hub + ring coupling strength (exponents differ)
  (MASS)    Mass knob — inertia
  [N]/[I]   Polarity toggle: NORM / INV
```

---

## Parameter Key Naming

**Hub parameters (OSC + preset):**
- `clock_mode` — 0=CLK, 1=FREE
- `rate` — normalized 0.0–1.0 (0–0.05 = OFF)
- `depth` — normalized 0.0–1.0
- `gravity` — normalized 0.0–1.0
- `resonance` — normalized 0.0–1.0
- `excursion` — normalized 0.0–1.0
- `calm` — normalized 0.0–1.0 (0.5 = neutral); convert to bipolar: `calm_bi = 2 × calm_norm - 1`
- `reset` — trigger (rising edge, OSC only)

**Per-output parameters:**

*OSC keys (flat, n = 1–4):*
- `out{n}_tension` — normalized 0.0–1.0
- `out{n}_mass` — normalized 0.0–1.0
- `out{n}_polarity` — 0=NORM, 1=INV

*Preset keys (structured list):*
- `outputs[i].tension` — normalized 0.0–1.0
- `outputs[i].mass` — normalized 0.0–1.0
- `outputs[i].polarity` — 0=NORM, 1=INV

**OSC path examples:**
- `/noise/mod/sauce_of_grav/2/rate` (slot 2, refresh rate)
- `/noise/mod/sauce_of_grav/2/excursion` (slot 2, range/expressiveness)
- `/noise/mod/sauce_of_grav/2/out3_tension` (slot 2, output 3 tension)
- `/noise/mod/sauce_of_grav/2/reset` (slot 2, reset trigger)

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| RATE in [0..0.05] | OFF — no refresh events; hub only has continuous damping |
| RATE > 0.05 | Active refresh events at mapped rate |
| High RESONANCE + RATE OFF | Sustained motion; hub accumulates until soft limit |
| All outputs same TENSION | Ring + hub coupling equal; simultaneous response |
| All outputs stationary | Noise injection + VDP negative damping ensure eventual movement; VDP sustains amplitude, RESO adds collective drive |
| Conflicting overshoots | Energies SUM — net direction wins but all contribute |
| RESET during motion | Hub clears; outputs continue from current positions/velocities |
| GRAVITY = 100% | Strong restoring field to 0.5; RESO can still sustain motion |
| GRAVITY = 0% | No center restoring force; motion governed by hub/ring coupling + RESO/noise |
| RESONANCE = 0% | Disables resonance drive/floor/kick; VDP still sustains motion, but less collectively 'pushed' — feels more locally orbiting |
| RESONANCE = 100% | High energy floor; sustained motion even with high damping |
| Output near rail | Velocity absorbed by rail bumpers; RESO drive attenuated; position clamped |
| State goes NaN/Inf | Reset affected subsystem only: output → `out_i=0.5, v_i=0`; hub → `hub_bias=0, hub_vel=0`. Never cross-reset. |

---

## Implementation Safety (v1.4.3)

**Per-sample safety clamps:**
- Keep existing rails + bumpers
- Non-finite state handling (explicit isolation rules):
  - If `out_i` or `v_i` non-finite → reset that output only: `out_i = 0.5, v_i = 0`
  - If `hub_bias` or `hub_vel` non-finite → reset hub only: `hub_bias = 0, hub_vel = 0`
  - Never reset unrelated outputs when hub fails
  - Never reset hub when only one output fails

**VDP threshold floor:**
- Already in spec: `vdp_threshold_i = max(vdp_threshold_i, VDP_THRESHOLD_FLOOR)`
- Prevents pathological division when hub bias is extreme

**Integration stability (dt constraint):**
- Recommend internal sim rate with `dt ≤ 1/400 s` (2.5ms) or substep until this is achieved
- `exp(-damping_effective_i × dt)` must be computed at the simulation dt, not once per UI frame
- VDP negative damping can explode if dt is too large; this is the #1 real-world failure mode

---

## Transient Behaviour (Expected)

**On reset / patch load:** A brief chaotic transient is normal. The system self-organises into sustained motion within a few seconds as the VDP amplitude regulation establishes limit-cycle behaviour.

This "wild then settles" quality is intentional — it provides an initial event/burst followed by a long evolving bed of modulation.

---

## Preset State Schema

**Note:** Python snippets below are illustrative; implementation may differ while preserving behaviour.

```python
@dataclass
class SauceOfGravOutputState:
    """State for a single SauceOfGrav output."""
    tension: float = 0.5       # Normalized 0–1
    mass: float = 0.5          # Normalized 0–1
    polarity: int = 0          # 0=NORM, 1=INV

@dataclass
class SauceOfGravState:
    """Full SauceOfGrav modulator state."""
    clock_mode: int = 0        # 0=CLK, 1=FREE
    rate: float = 0.5          # Normalized 0–1 (0–0.05 = OFF)
    depth: float = 0.5         # Normalized 0–1
    gravity: float = 0.5       # Normalized 0–1
    resonance: float = 0.5     # Normalized 0–1
    excursion: float = 0.5     # Normalized 0–1 (range/expressiveness)
    calm: float = 0.5          # Normalized 0–1 (0.5 = neutral); physics uses calm_bi = 2×calm - 1
    outputs: list = field(default_factory=lambda: [
        SauceOfGravOutputState() for _ in range(4)
    ])
    
    def to_dict(self) -> dict:
        return {
            "clock_mode": self.clock_mode,
            "rate": self.rate,
            "depth": self.depth,
            "gravity": self.gravity,
            "resonance": self.resonance,
            "excursion": self.excursion,
            "calm": self.calm,
            "outputs": [
                {
                    "tension": o.tension,
                    "mass": o.mass,
                    "polarity": o.polarity,
                }
                for o in self.outputs
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SauceOfGravState":
        raw_outputs = data.get("outputs", [])
        # Always pad to exactly 4 outputs
        outputs = []
        for i in range(4):
            if i < len(raw_outputs):
                outputs.append(SauceOfGravOutputState(**raw_outputs[i]))
            else:
                outputs.append(SauceOfGravOutputState())
        return cls(
            clock_mode=data.get("clock_mode", 0),
            rate=data.get("rate", 0.5),
            depth=data.get("depth", 0.5),
            gravity=data.get("gravity", 0.5),
            resonance=data.get("resonance", 0.5),
            excursion=data.get("excursion", 0.5),
            calm=data.get("calm", 0.5),
            outputs=outputs,
        )
```

---

## Theme Additions

```python
# In theme.py COLORS dict:
'accent_mod_sauce_of_grav': '#FF00FF',  # Magenta
'reset_button': '#CC3333',               # Red/warning for RESET
```

---

## Config Additions

```python
# In src/config/__init__.py

# === SauceOfGrav v1.4.3 Config Constants ===

# Rate ranges
SAUCE_FREE_RATE_MIN = 0.001    # Hz (≈16 min period)
SAUCE_FREE_RATE_MAX = 100.0    # Hz
SAUCE_RATE_DEADBAND = 0.05     # 0–0.05 = OFF

# Noise / thresholds
SAUCE_NOISE_RATE = 0.012       # RMS velocity noise per second
SAUCE_VELOCITY_EPSILON = 0.001 # Below this = stationary for resonance

# Mass mapping
MASS_BASE = 0.25
MASS_GAIN = 2.1

# Coupling (hub + ring) with separate tension exponents
HUB_COUPLE_BASE = 0.0
HUB_COUPLE_GAIN = 6.0
HUB_TENSION_EXP = 0.70         # Hub comes in earlier, softer
RING_COUPLE_BASE = 0.0
RING_COUPLE_GAIN = 3.5
RING_TENSION_EXP = 1.30        # Ring ramps harder at high tension

# Non-reciprocal ring coupling (v1.4.1)
RING_SKEW = 0.015              # 1.5% directional bias for phase drift

# Gravity stiffness
GRAV_STIFF_BASE = 0.0
GRAV_STIFF_GAIN = 6.0

# Excursion (range/expressiveness)
EXCURSION_MIN = 0.60           # Minimum hub_target scaling
EXCURSION_MAX = 1.60           # Maximum hub_target scaling

# CALM macro (v1.4.3) — bipolar energy scaling
CALM_DAMP_CALM = 1.30          # at CALM=-1 (more damping)
CALM_DAMP_WILD = 0.75          # at CALM=+1 (less damping)
CALM_VDP_CALM = 0.90           # at CALM=-1 (still self-sustaining)
CALM_VDP_WILD = 1.15           # at CALM=+1 (more animated)
CALM_KICK_CALM = 0.60          # at CALM=-1 (reduce kick spam in calm mode)

# Van der Pol amplitude regulation (v1.4.0)
VDP_INJECT = 0.8               # Injection strength (negative damping when amp < threshold)
VDP_THRESHOLD = 0.35           # Target amplitude from center (0.35 → outputs span ~0.15..0.85)
VDP_HUB_MOD = 0.05             # ±5% threshold modulation by hub bias (v1.4.1)
VDP_THRESHOLD_FLOOR = 0.05     # Safety floor to prevent division issues

# Per-node calibration trims (v1.4.1) — static micro-asymmetries for butterfly divergence
TENSION_TRIM = [+0.012, -0.008, +0.015, -0.018]  # per-node, ±2% max
MASS_TRIM    = [-0.010, +0.014, -0.006, +0.011]  # per-node, ±2% max

# Damping (base, before Van der Pol adjustment)
SAUCE_DAMPING_BASE = 0.10      # Reduced from 0.15 to allow VDP to dominate
SAUCE_DAMPING_TENSION = 0.40   # Reduced from 0.55

# Rails (bumpers)
SAUCE_RAIL_ZONE = 0.08         # 8% of range
SAUCE_RAIL_ABSORB = 0.35       # Absorption strength

# Resonance sustain (energy floor)
RESO_FLOOR_MIN = 0.0002
RESO_FLOOR_MAX = 0.0040
RESO_DRIVE_GAIN = 6.0
RESO_DELTAE_MAX = 0.01         # Cap on ΔE to prevent drive spikes
RESO_RAIL_EXP = 1.4            # Exponent for rail attenuation of RESO drive

# RESO kickstart (v1.4.0)
RESO_KICK_GAIN = 2.8           # Kick magnitude scaling
RESO_KICK_MAXF = 0.30          # Max kick force
RESO_KICK_COOLDOWN_S = 0.20    # Seconds between kicks
KICK_PATTERNS = [
    [+1, -1, +1, -1],
    [+1, +1, -1, -1],
    [+1, -1, -1, +1],
]

# Hub dynamics
OVERSHOOT_TO_HUB_GAIN = 0.6
OVERSHOOT_MAX = 0.25           # Cap on individual overshoot contribution (per-event impulse)
HUB_LIMIT = 2.0
DEPTH_DAMP_MIN = 0.005          # Tuned for visible hub drift
DEPTH_DAMP_MAX = 2.50

# Continuous hub feed (v1.4.0)
HUB_FEED_GAIN = 8.0            # Tuned for visible hub drift
HUB_FEED_MAX = 0.35            # Cap on hub feed per step

# Modulator generator config
_MOD_GENERATOR_CONFIGS["SauceOfGrav"] = {
    "internal_id": "sauce_of_grav",
    "params": [
        {"key": "clock_mode", "label": "CLK", "steps": 2, "default": 0.0},
        {"key": "rate", "label": "RATE", "default": 0.5},
        {"key": "depth", "label": "DEPTH", "default": 0.5},
        {"key": "gravity", "label": "GRAV", "default": 0.5},
        {"key": "resonance", "label": "RESO", "default": 0.5},
        {"key": "excursion", "label": "EXCUR", "default": 0.5},
        {"key": "calm", "label": "CALM", "default": 0.5, "bipolar": True},  # stored 0–1, UI shows -100%..+100%
    ],
    "output_config": "sauce_of_grav",
    "output_labels": ["1", "2", "3", "4"],
    "has_reset": True,
}
```

---

## "Can I Feel It?" Test (v1.4.3 Updated)

| Control | Distinct Effect |
|---------|-----------------|
| RATE | Timing of refresh events (optional memory clears). OFF = no refresh pulses, hub only has continuous damping. |
| DEPTH | Hub friction/forgetting: higher = hub loses momentum/bias faster; refresh pulses (if enabled) are stronger. |
| GRAVITY | Restoring field tightness + hub influence: low = free drift, hub controls target; high = tight oscillation around center. |
| RESONANCE | **Sustained motion strength**: raises energy floor; aligned motion + kickstart ensure system never starves. Rail attenuation prevents pushing into boundaries. |
| EXCURSION | **Range/expressiveness**: low = conservative travel, high = wide confident swings. Scales hub_target offset. |
| CALM | **Energy macro**: anticlockwise = calmer (tighter orbit, fewer rail visits, still alive); clockwise = wilder (larger excursions, faster evolution). Cannot kill motion. |
| TENSION | Coupling strength (hub + ring respond differently via exponents): low = independent, high = strongly linked with phase-offset ripples. Hub comes in earlier/softer, ring ramps harder. |
| MASS | Inertia: low = agile/snappy, high = slow arcs with stronger momentum memory. |

**v1.4.0 internal mechanisms (not user-facing controls):**
- **Van der Pol damping**: automatically injects energy when amplitude is low, dissipates when high → self-sustaining wide motion
- **Hub feed**: continuous work term (HUB_FEED_GAIN=8.0) keeps hub_bias evolving with visible bipolar drift
- **Kickstart**: symmetry-breaking impulse when RESO path can't fire

**v1.4.3 micro-asymmetries (butterfly-effect sensitivity):**
- **Calibration trims**: per-node ±2% offsets on TENSION/MASS → prevents perfect phase-lock
- **Non-reciprocal ring**: 1.5% directional skew on ring coupling → slow phase drift
- **Hub-modulated VDP threshold**: ±5% amplitude target variation with hub bias → evolving orbit size

---

## Implementation Phases

### Phase 1: Core Infrastructure
- Add theme colors (`accent_mod_sauce_of_grav`, `reset_button`)
- Add all config constants (v1.4.3 table)
- Create SauceOfGravState dataclass
- Add to modulator type cycle

### Phase 2: UI Components
- Hub section with visualization + 6 knobs + RESET button (red)
- Output rows (activity indicator + TENSION + MASS + polarity)
- 4-trace scope renderer
- RESET button styling

### Phase 3: SuperCollider SynthDef
- State: 4 output positions + velocities, hub_bias + hub_vel, kickstart state
- Ring topology neighbour indices
- Van der Pol effective damping (amplitude-dependent)
- Forces: F_grav, F_hub, F_ring, F_reso, F_kick
- RESO energy floor with alignment factor + kickstart path
- Hub 2nd order dynamics with overshoot impulses + continuous work feed
- Rail bumpers (velocity absorption near 0/1)
- Overshoot detection with frozen target + impulse semantics
- Continuous hub damping (DEPTH → HUB_DAMP)
- Optional discrete refresh events (RATE timing)
- RESET trigger handling
- 4 output buses

### Phase 4: Integration
- OSC parameter mapping
- RESET as mod matrix destination
- Preset save/load (with 4-output padding)
- Mod matrix routing for outputs

---

## Backlog Items (Deferred)

| Item | Description | Priority |
|------|-------------|----------|
| Unify output labels | Change LFO/Sloth to 1,2,3,4 (with ARSEq+/SauceOfGrav) | Medium |
| Unify scope colors | Consistent 4-color scheme across all modulators | Medium |
| Matrix headers | Add grouped type+slot headers to mod matrix | Medium |
| Gate output | Trigger output when threshold crossed | Low |
| Per-output range | Individual min/max travel limits | Low |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-15 | Initial spec |
| 1.1 | 2025-12-18 | Added all blocker resolutions from AI review |
| 1.1.1 | 2025-12-20 | Fixed GRAVITY mapping, clarified MOD_CLOCK_RATES, noise distribution, resonance wording, overshoot measurement |
| 1.1.2 | 2025-12-22 | Added explicit gravity pull force formula, SPRING_CONSTANT config, updated simulation loop |
| 1.2.0 | 2026-01-01 | **Divergent dynamics**: ring topology + hub momentum (2nd order) + RESO energy floor (limit-cycle) + rail bumpers + explicit mass/damping mappings. RATE/DEPTH refresh events now optional layer on continuous hub damping. |
| 1.2.1 | 2026-01-01 | Added gravity_influence definition in Core Mappings, clarified overshoot impulse semantics with explicit per-output tracking state (prev_side, overshoot_active, overshoot_target_i, overshoot_peak), added abstract units note for hub state, confirmed RESO as force term, clarified RESET edge detection on raw control-rate value, changed status to ready_for_review. |
| 1.3.0 | 2026-01-01 | **Musical tuning**: EXCURSION control (range/expressiveness); RESO rail attenuation (prevents pushing into rails); hub/ring tension exponents (preserves divergence at high TENSION); reduced OVERSHOOT_MAX (0.5→0.25) for smoother hub dynamics. **Clarifications**: overshoot peak signed update rule; velocity threshold for crossing detection; OSC vs preset key naming separation. |
| 1.4.0 | 2026-01-01 | **Wide motion architecture**: Van der Pol amplitude regulation (negative damping near center, positive near rails); continuous hub feed (work term); RESO kickstart (symmetry-break when system starved). Reduced base damping to allow VDP to dominate. Added kickstart state variables. |
| 1.4.1 | 2026-01-01 | **Butterfly-effect sensitivity**: per-node calibration trims (±2% TENSION/MASS); non-reciprocal ring coupling (1.5% RING_SKEW); hub-modulated VDP threshold (±5% VDP_HUB_MOD). **Hardening**: VDP_THRESHOLD_FLOOR safety, NaN/Inf per-node reset, damping uses tension_eff (post-trim). Documented transient behaviour as expected. |
| 1.4.2 | 2026-01-01 | **Implementation-ready release**. Clarifications: explicit polarity transform (`-out_i` not `1-out_i`); isolated NaN/Inf reset rules (output vs hub); prev_side update rule (side=0 unchanged); crossing requires `side != 0` (prevents spurious overshoots); MOD_CLOCK_RATES exact order; dt stability constraint (≤2.5ms). |
| 1.4.3 | 2026-01-01 | **CALM macro control**: bipolar knob (-100%..+100%) scales system energy level. Anticlockwise = calmer (more damping, less VDP, reduced kick), clockwise = wilder (less damping, more VDP). Cannot kill motion — even at full calm, VDP injection remains >0. Added CALM_DAMP_*, CALM_VDP_*, CALM_KICK_* constants. **Hub tuning**: HUB_FEED_GAIN 2.2→8.0, DEPTH_DAMP_MIN 0.05→0.005 for visible bipolar hub drift. Validated via 2-minute simulation: outputs decorrelated (~0.56), full 0–1 range coverage, hub drifting ±0.2 with organic crossover through zero. Phase space orbits confirm non-repetitive butterfly-effect motion. |

---

## Open Questions

None — spec complete pending review.

---

## Simulation Tool

Reference Python simulation available at `tools/sauce_of_grav_v1_4_3_sim.py`:
- Implements full physics model
- Generates MP4 with output traces, hub trace, and dual phase space plots
- Validates wide motion, hub drift, and phase space coverage

---

## Approval

- [ ] Gareth
- [x] Simulation validated (2-minute run, phase space coverage confirmed)
- [ ] Implementation ready

---

*Lineage: Buchla 266 Source of Uncertainty → NLC Sauce of Unce → SauceOfGrav*
