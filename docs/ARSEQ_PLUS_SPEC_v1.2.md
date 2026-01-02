# ARSEq+ Modulator Specification

---
status: approved
version: 1.2
date: 2025-01-01
inspired_by: NLC ARSEq, Make Noise Maths
---

## What

ARSEq+ is a 4-output envelope sequencer/function generator modulator for Noise Engine. It combines the sequenced envelope concept from Nonlinear Circuits' ARSEq with the cycling function generator behavior of Make Noise Maths.

**Core identity:** 4 Attack-Release envelopes that can be clocked sequentially, triggered in parallel, or run as independent self-cycling function generators.

## Why

Current modulators:
- **LFO** — Continuous cyclic modulation (periodic)
- **Sloth** — Chaotic slow modulation (organic)

Missing: **Event-driven modulation** — envelopes that respond to clock triggers, creating rhythmic or sequenced modulation shapes.

ARSEq+ fills this gap with:
- Clock-synced envelope sequences for rhythmic texture
- Parallel envelope triggering for punchy synchronized hits
- Independent cycling mode for Maths-style function generation
- Variable curve shapes (log/lin/exp) for character control

---

## Naming Convention

| Context | Value |
|---------|-------|
| Display name | `ARSEq+` |
| Internal ID | `arseq_plus` |
| Theme key | `accent_mod_arseq_plus` |
| Config key | `"ARSEq+"` (display) / `"arseq_plus"` (internal) |
| OSC path prefix | `/noise/mod/arseq_plus/` |

---

## Feature Summary

| Feature | Description |
|---------|-------------|
| 4 envelope outputs | Independent AR envelopes with shared or individual clocking |
| SEQ/PAR modes | Sequential rotation or parallel triggering |
| SYNC/LOOP per envelope | Follow master clock or self-cycle independently |
| Variable curve | Bipolar LOG ↔ LIN ↔ EXP per envelope |
| Legato retrigger | Smooth retriggering from current level |
| Visual feedback | 4-trace scope + fill/drain indicator per envelope |

---

## Master Controls

| Control | Type | Values | Description |
|---------|------|--------|-------------|
| MODE | Toggle | SEQ / PAR | Clock distribution to SYNC'd envelopes |
| CLK/FREE | Toggle | CLK / FREE | Master clock source |
| RATE | Slider | See below | Clock division or Hz |

**RATE values:**

| Mode | Range | Source |
|------|-------|--------|
| CLK | /64, /32, /16, /8, /4, /2, 1, x2, x4, x8, x16, x32 | `MOD_CLOCK_RATES` |
| FREE | 0.01Hz – 100Hz (exponential) | `MOD_LFO_FREQ_MIN/MAX` |

**RATE parameter mapping:**
- Stored as normalized float 0.0–1.0
- CLK mode: `idx = round(rate_norm * (len(MOD_CLOCK_RATES) - 1))`
- FREE mode: `hz = exp_map(rate_norm, 0.01, 100)`

---

## Per-Envelope Controls (×4)

| Control | Type | Range | Description |
|---------|------|-------|-------------|
| ATK | Slider | 0.1ms–10s (SYNC) / 0.1ms–2min (LOOP) | Attack time |
| REL | Slider | 0.1ms–10s (SYNC) / 0.1ms–2min (LOOP) | Release time |
| CURVE | Knob | Bipolar | LOG (left) ↔ LIN (center) ↔ EXP (right) |
| SYN/LOP | Toggle | SYN / LOP | Follow master clock or self-cycle |
| RATE | Selector | `MOD_CLOCK_RATES` | Only visible/active when LOP mode |
| N/I | Toggle | N / I | NORM (0→+1→0) or INV (0→-1→0) |

**UI label convention:** `SYN`/`LOP` and `N`/`I` for compact display. Spec prose uses SYNC/LOOP and NORM/INV for clarity.

---

## Output Range

Outputs are normalized floats:
- **NORM (N):** 0.0 to +1.0
- **INV (I):** 0.0 to -1.0

---

## Curve Mapping

Single CURVE control affects both attack and release phases identically.

**Storage:** Normalized 0.0–1.0 where 0.5 = linear center.

**Conversion to bipolar:**
```
curve_bipolar = (curve_norm * 2.0) - 1.0
# Result: -1.0 = LOG, 0.0 = LIN, +1.0 = EXP
```

**Curve shapes:**
```
LOG (-1):   ████░░░░░░  Fast start, slow end — snappy, percussive
LIN (0):    ██████████  Steady ramp — linear
EXP (+1):   ░░░░░░████  Slow start, fast end — soft, swelling
```

---

## Mode Behavior

### SEQ Mode (Sequential)

Master clock advances through SYNC'd envelopes in rotation using a two-pulse-per-envelope pattern:

**Algorithm:**
```python
sync_ids = [i for i in range(4) if envelopes[i].sync_mode == SYNC]
seq_step = 0  # Reset on init

def on_master_clock():
    if not sync_ids:
        return
    env_idx = sync_ids[(seq_step // 2) % len(sync_ids)]
    phase = seq_step % 2  # 0 = attack, 1 = release
    
    if phase == 0:
        trigger_attack(env_idx)
    else:
        trigger_release(env_idx)
    
    seq_step += 1
```

**Timing behavior (Option A):**
- Odd pulse: Begin attack toward peak (+1)
- Even pulse: Begin release from *current level* toward 0
- If attack completes before even pulse: Hold at peak until even pulse
- If attack incomplete by even pulse: Release begins from current level (truncated shape, no forced peak)

**Note:** 8 clocks = full cycle through 4 SYNC'd envelopes. LOOP envelopes are skipped in sequence.

### PAR Mode (Parallel)

Master clock triggers ALL SYNC'd envelopes simultaneously on each pulse pair:
- Odd pulse: All SYNC'd envelopes begin attack
- Even pulse: All SYNC'd envelopes begin release

LOOP envelopes are unaffected and continue independently.

### LOOP Mode (Per-Envelope)

Envelope self-cycles: completes attack → release → retriggers automatically.

**Clock reference:** LOOP uses the global clock/BPM (same source as `MOD_CLOCK_RATES`) for its retrigger interval, but does not participate in master trigger distribution (SEQ/PAR logic).

**Timing behavior (Rule 1 — absolute times):**
- ATK/REL sliders set actual durations (0.1ms – 2 minutes)
- LOOP_RATE sets the retrigger interval (when the next cycle can start)
- If ATK + REL < retrigger interval: envelope completes, idles until next tick
- If ATK + REL > retrigger interval: envelope completes fully, then waits for the *next* division tick (skips one)

**Example:** LOOP_RATE = /2 at 120 BPM (1000ms interval), ATK = 200ms, REL = 300ms:
```
[ATK 200ms][REL 300ms][idle 500ms][ATK 200ms][REL 300ms]...
```

This matches Maths behavior — sliders always mean real time, not proportions.

---

## Retrigger Behavior

**Legato retrigger (default):**
- On retrigger during envelope: Begin attack from current level toward peak
- No snap-to-zero (avoids clicks)
- Musically smooth, matches Maths behavior

**Same-phase retrigger:**
- If already attacking and retrigger arrives: Restart attack timing from current level (re-time the rise, don't jump)

---

## Visual Feedback

### Fill/Drain Indicator (per envelope)
- Single horizontal bar per envelope
- **Fills** left→right during attack phase (rate matches ATK time + curve)
- **Drains** right→left during release phase (rate matches REL time + curve)
- Empty when envelope idle

### 4-Trace Scope
- Shows all 4 envelope outputs in real-time
- Uses consistent 4-color scheme (same as other modulators)
- Downsampled for performance (N points per frame)
- Updates at display refresh rate

---

## Output Configuration

| Property | Value |
|----------|-------|
| Output labels | 1, 2, 3, 4 |
| Output count | 4 |
| Accent color | Cyan (`COLORS['accent_mod_arseq_plus']`) |

**Note:** All modulators (LFO, Sloth, ARSEq+) will use 1, 2, 3, 4 output labels. See backlog for unification task.

---

## Mod Matrix Display

Grouped by slot with type headers:

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│      LFO        │     Sloth       │    ARSEq+       │      LFO        │
│     Slot 1      │     Slot 2      │     Slot 3      │     Slot 4      │
├────┬────┬────┬────┼────┬────┬────┬────┼────┬────┬────┬────┼────┬────┬────┬────┤
│  1 │  2 │  3 │  4 │  1 │  2 │  3 │  4 │  1 │  2 │  3 │  4 │  1 │  2 │  3 │  4 │
```

Color indicates modulator type. Position provides slot context.

---

## UI Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ [3]  ARSEq+                          [SEQ|PAR]  [CLK]  ──RATE──  /4  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1  [▓▓▓░░░]  ╽ATK╽  ╽REL╽  (CRV)  [SYN]       [N]                  │
│                                                                      │
│  2  [▓░░░░░]  ╽ATK╽  ╽REL╽  (CRV)  [LOP]  /8   [N]                  │
│                                                                      │
│  3  [░░░░░░]  ╽ATK╽  ╽REL╽  (CRV)  [SYN]       [I]                  │
│                                                                      │
│  4  [▓▓▓▓░░]  ╽ATK╽  ╽REL╽  (CRV)  [LOP]  x2   [N]                  │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                        4-TRACE SCOPE                           │  │
│  │  ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

Legend:
  [▓▓░░░░]  Fill indicator (shows envelope phase + curve)
  ╽ATK╽     Attack time slider (vertical)
  ╽REL╽     Release time slider (vertical)
  (CRV)     Curve knob (bipolar: LOG ↔ LIN ↔ EXP)
  [SYN]     SYNC mode (follows master clock)
  [LOP]     LOOP mode (self-cycling) — shows own rate selector
  /8, x2    Per-envelope clock division (LOP mode only)
  [N]/[I]   Polarity: NORM / INV
```

---

## Parameter Key Naming

OSC addresses and preset keys use consistent naming:

**Master parameters:**
- `mode` — 0=SEQ, 1=PAR
- `clock_mode` — 0=CLK, 1=FREE
- `rate` — normalized 0.0–1.0

**Per-envelope parameters (n = 1–4):**
- `env{n}_attack` — normalized 0.0–1.0
- `env{n}_release` — normalized 0.0–1.0
- `env{n}_curve` — normalized 0.0–1.0 (0.5 = linear)
- `env{n}_sync_mode` — 0=SYNC, 1=LOOP
- `env{n}_loop_rate` — index into MOD_CLOCK_RATES
- `env{n}_polarity` — 0=NORM, 1=INV

**OSC path examples:**
- `/noise/mod/arseq_plus/3/mode` (slot 3, master mode)
- `/noise/mod/arseq_plus/3/env2_attack` (slot 3, envelope 2 attack)

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| All envelopes LOOP | Master MODE/RATE ignored, all run independently |
| Mixed SYNC/LOOP in SEQ | SEQ only cycles through SYNC'd envelopes; LOOP ignored |
| Mixed SYNC/LOOP in PAR | PAR triggers all SYNC'd simultaneously; LOOP runs independently |
| Single SYNC'd envelope in SEQ | Triggers on every pulse pair (attack, release, repeat) |
| Attack longer than half-period | Release begins from current level (truncated, no peak hold) |
| Attack completes early | Holds at peak until release pulse |
| Retrigger mid-attack | Restart attack timing from current level (legato) |
| Retrigger mid-release | Begin new attack from current level |
| LOOP with A+R < interval | Envelope idles after release until next retrigger tick |
| LOOP with A+R > interval | Envelope completes, waits for *next* division tick (skips one) |
| LOOP with very long A+R | Cycles slowly (up to 4 min per cycle) |
| Global clock stopped | LOOP envelopes continue cycling at last known BPM |

---

## Preset State Schema

```python
@dataclass
class ARSeqEnvelopeState:
    """State for a single ARSEq+ envelope."""
    attack: float = 0.5         # Normalized 0–1
    release: float = 0.5        # Normalized 0–1
    curve: float = 0.5          # 0=LOG, 0.5=LIN, 1=EXP (bipolar via *2-1)
    sync_mode: int = 0          # 0=SYNC, 1=LOOP
    loop_rate: int = 6          # Index into MOD_CLOCK_RATES (6 = "1" = 1:1)
    polarity: int = 0           # 0=NORM, 1=INV

@dataclass
class ARSeqPlusState:
    """Full ARSEq+ modulator state."""
    mode: int = 0               # 0=SEQ, 1=PAR
    clock_mode: int = 0         # 0=CLK, 1=FREE
    rate: float = 0.5           # Normalized 0–1
    envelopes: list = field(default_factory=lambda: [
        ARSeqEnvelopeState() for _ in range(4)
    ])
    
    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "clock_mode": self.clock_mode,
            "rate": self.rate,
            "envelopes": [
                {
                    "attack": e.attack,
                    "release": e.release,
                    "curve": e.curve,
                    "sync_mode": e.sync_mode,
                    "loop_rate": e.loop_rate,
                    "polarity": e.polarity,
                }
                for e in self.envelopes
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ARSeqPlusState":
        envelopes = [
            ARSeqEnvelopeState(**e) 
            for e in data.get("envelopes", [{} for _ in range(4)])
        ]
        return cls(
            mode=data.get("mode", 0),
            clock_mode=data.get("clock_mode", 0),
            rate=data.get("rate", 0.5),
            envelopes=envelopes,
        )
```

---

## Theme Additions

```python
# In theme.py COLORS dict:
'accent_mod_arseq_plus': '#00CCCC',  # Cyan
```

---

## Config Additions

```python
# In src/config/__init__.py

# ARSEq+ time ranges (in seconds)
ARSEQ_SYNC_TIME_MIN = 0.0001   # 0.1ms
ARSEQ_SYNC_TIME_MAX = 10.0     # 10s
ARSEQ_LOOP_TIME_MIN = 0.0001   # 0.1ms  
ARSEQ_LOOP_TIME_MAX = 120.0    # 2 minutes

# Modulator generator config
_MOD_GENERATOR_CONFIGS["ARSEq+"] = {
    "internal_id": "arseq_plus",
    "params": [
        {"key": "mode", "label": "MODE", "steps": 2, "default": 0.0},      # SEQ/PAR
        {"key": "clock_mode", "label": "CLK", "steps": 2, "default": 0.0}, # CLK/FREE
        {"key": "rate", "label": "RATE", "default": 0.5},
    ],
    "output_config": "arseq_plus",  # Custom config for envelope rows
    "output_labels": ["1", "2", "3", "4"],
}
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
- Add theme color (`accent_mod_arseq_plus`)
- Add config constants and generator config
- Create ARSeqPlusState dataclass
- Add to modulator type cycle

### Phase 2: UI Components
- Envelope row widget (indicator + sliders + knob + toggles)
- Fill/drain indicator with curve-aware animation
- 4-trace scope renderer

### Phase 3: SuperCollider SynthDef
- ARSEq+ synth with 4 envelope generators
- Clock input handling (SEQ/PAR distribution)
- Per-envelope LOOP self-triggering
- Curve shape implementation (log/lin/exp)
- Legato retrigger logic
- 4 output buses

### Phase 4: Integration
- OSC parameter mapping
- Preset save/load
- Mod matrix routing

---

## Backlog Items (Deferred)

| Item | Description | Priority |
|------|-------------|----------|
| Reset input | Reset sequence to envelope 1 (per-mod or global) | Low |
| FREE mode for LOOP | Per-envelope Hz rate when in LOOP | Low |
| Unify output labels | Change LFO/Sloth from A,B,C,D / X,Y,Z,R to 1,2,3,4 | Medium |
| Unify scope colors | Consistent 4-color trace scheme across all modulators | Medium |
| Matrix headers | Add grouped type+slot headers to mod matrix | Medium |

---

## Open Questions

None — spec complete pending implementation.

---

## Approval

- [x] Gareth
- [x] AI1 review
- [x] AI2 review
- [x] Implementation ready

---

*Inspired by Nonlinear Circuits ARSEq (Andrew Fitch) and Make Noise Maths*
