# Noise Engine Signal Architecture

All signal layers from UI slider to audio output.

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONTROL LAYERS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. USER PARAMETER BUSES     ~genUserParams[slot][param]                    │
│     What the slider is set to (center point for modulation)                 │
│                                                                             │
│  2. MOD SOURCE BUSES         ~modBuses[0-15]  (LFO, Sloth, Env outputs)     │
│                              ~crossModBus[0-7] (envelope followers)         │
│                                                                             │
│  3. MOD APPLY SYNTHS         One per destination, mixes user + mod sources  │
│                                                                             │
│  4. FINAL PARAMETER BUSES    ~genParams[slot][param]                        │
│     What the generator actually reads                                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              AUDIO LAYERS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  5. GENERATOR AUDIO          ~genBus[0-7]  (8 stereo buses)                 │
│                                                                             │
│  6. CHANNEL STRIPS           Vol, Pan, EQ, Mute, Solo                       │
│                                                                             │
│  7. FX SEND BUSES            ~echoSendBus, ~verbSendBus                     │
│                                                                             │
│  8. FX RETURN BUSES          ~echoReturnBus, ~verbReturnBus                 │
│                                                                             │
│  9. DRY SUM BUS              ~drySumBus (all strips summed)                 │
│                                                                             │
│  10. MASTER BUS              ~masterBus (dry + FX returns)                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. User Parameter Buses

**What:** Where slider values land before modulation.

**Location:** `~genUserParams[slot][param]`

**Buses per slot:**
| Bus | Type | Range | Description |
|-----|------|-------|-------------|
| `\frequency` | kr | 20-8000 Hz | Base pitch |
| `\cutoff` | kr | 20-16000 Hz | Filter cutoff |
| `\resonance` | kr | 0.1-1.0 | Filter Q (RQ) |
| `\attack` | kr | 0.0001-2.0 s | Envelope attack |
| `\decay` | kr | 0.01-10.0 s | Envelope decay |
| `\custom[0-4]` | kr | varies | P1-P5 custom params |

**Signal path:**
```
PyQt Slider → OSC message → SC OSC handler → ~genUserParams[slot][param].set(value)
```

---

## 2. Mod Source Buses

**What:** Control signals from modulation sources.

### Standard Mod Buses (0-15)

**Location:** `~modBuses[0-15]`

**Layout:** 4 mod slots × 4 outputs = 16 buses
```
Slot 1: buses 0-3   (A/X, B/Y, C/Z, D/R)
Slot 2: buses 4-7
Slot 3: buses 8-11
Slot 4: buses 12-15
```

**Sources:**
| Type | Outputs | Range |
|------|---------|-------|
| LFO | A,B,C,D (quad) | -1 to +1 |
| Sloth | X,Y,Z,R | -1 to +1 |
| Envelope | single | 0 to +1 |

### Crossmod Buses (16-23)

**Location:** `~crossModBus[0-7]`

**What:** Envelope follower output from each generator's audio.

| Source ID | Generator | Range |
|-----------|-----------|-------|
| 16 | Gen 1 | 0 to +1 |
| 17 | Gen 2 | 0 to +1 |
| 18 | Gen 3 | 0 to +1 |
| 19 | Gen 4 | 0 to +1 |
| 20 | Gen 5 | 0 to +1 |
| 21 | Gen 6 | 0 to +1 |
| 22 | Gen 7 | 0 to +1 |
| 23 | Gen 8 | 0 to +1 |

**Note:** Unipolar (silence=0, loud=1), different from LFO/Sloth which are bipolar.

---

## 3. Mod Apply Synths

**What:** Mixes user value + up to 4 mod sources, writes to final param bus.

**Location:** `~modApplySynths["slot_param"]`

**One synth per modulatable destination:**
- cutoff, frequency, resonance, attack, decay, p1-p5
- × 8 slots = up to 80 synths

**Per-route parameters:**
| Param | Range | Description |
|-------|-------|-------------|
| `depth` | 0-1 | Modulation range |
| `amount` | 0-1 | VCA level (how much gets through) |
| `offset` | -1 to +1 | Shifts mod center up/down |
| `polarity` | 0/1/2 | 0=bipolar, 1=uni+, 2=uni- |
| `invert` | 0/1 | Flip signal before polarity |

**Signal path:**
```
~genUserParams[slot][param] ──┐
                              │
~modBuses[source] × depth ────┼──► Mod Apply Synth ──► ~genParams[slot][param]
~modBuses[source] × depth ────┤       (mixes up to
~crossModBus[n] × depth ──────┤        4 sources)
~crossModBus[n] × depth ──────┘
```

---

## 4. Final Parameter Buses

**What:** The actual values generators read.

**Location:** `~genParams[slot][param]`

**Same structure as user params, but after modulation applied.**

When no modulation active: passthrough (user value copied directly).

---

## 5. Generator Audio Buses

**What:** Audio output from each generator synth.

**Location:** `~genBus[0-7]` (8 stereo buses)

**Signal path inside generator:**
```
Oscillator/DSP → ~multiFilter → ~envVCA → Out.ar(~genBus[slot])
```

**Tap point for crossmod:** Envelope followers read from `~genBus[slot]` (post-trim).

---

## 6. Channel Strips

**What:** Per-generator mixing (happens after generator audio).

**Location:** `~channelStrips[0-7]` (synths)

**Signal flow:**
```
~genBus[slot] ──► genTrim ──► EQ (3-band) ──► Mute ──► Solo ──► Gain ──► Pan ──► Vol ──► output
                                                                                          │
                                                                                          ├──► ~drySumBus
                                                                                          ├──► ~echoSendBus (× send level)
                                                                                          └──► ~verbSendBus (× send level)
```

**Controls per strip:**
| Control | Range | Description |
|---------|-------|-------------|
| `genTrim` | dB | Per-generator loudness normalization |
| `eqLo` | 0-2 | Low band (< 250 Hz) |
| `eqMid` | 0-2 | Mid band (250-2500 Hz) |
| `eqHi` | 0-2 | High band (> 2500 Hz) |
| `mute` | 0/1 | Silence this channel |
| `solo` | 0/1 | Solo-in-place |
| `gain` | 0-4 | Pre-fader gain (0/+6/+12 dB) |
| `pan` | -1 to +1 | L/R balance |
| `vol` | 0-1 | Fader level |
| `echoSend` | 0-1 | Send to echo FX |
| `verbSend` | 0-1 | Send to reverb FX |

---

## 7. FX Send Buses

**What:** Sum of all channel strip sends to each effect.

**Location:**
- `~echoSendBus` (stereo)
- `~verbSendBus` (stereo)

**Signal path:**
```
Channel Strip 1 ──┐
Channel Strip 2 ──┼──► ~echoSendBus ──► Echo FX Synth
Channel Strip 3 ──┤
...               ┘
```

---

## 8. FX Return Buses

**What:** 100% wet output from FX processors.

**Location:**
- `~echoReturnBus` (stereo)
- `~verbReturnBus` (stereo)

**Signal path:**
```
~echoSendBus ──► Echo Synth ──► ~echoReturnBus
~verbSendBus ──► Reverb Synth ──► ~verbReturnBus
```

---

## 9. Dry Sum Bus

**What:** Sum of all channel strip direct outputs (no FX).

**Location:** `~drySumBus` (stereo)

---

## 10. Master Bus

**What:** Final mix (dry + FX returns) before master processing.

**Location:** `~masterBus` (stereo)

**Signal path (FX Mixer):**
```
~drySumBus ─────────────────────┐
~echoReturnBus × echoReturn ────┼──► ~masterBus ──► Master Effects ──► Hardware Out
~verbReturnBus × verbReturn ────┘
```

---

## Complete Signal Flow Diagram

```
                           CONTROL DOMAIN
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  PyQt Slider ──► OSC ──► ~genUserParams[slot][param] ──┐                     │
│                                                        │                     │
│  LFO Synth ──────────► ~modBuses[0-15] ────────────────┼──► Mod Apply Synth  │
│  Sloth Synth ─────────► ~modBuses[0-15] ───────────────┤    (up to 4 sources │
│  Env Synth ───────────► ~modBuses[0-15] ───────────────┤     per dest)       │
│                                                        │         │           │
│  Gen Audio ──► Envelope Follower ──► ~crossModBus[0-7] ┘         │           │
│                                                                  ▼           │
│                                              ~genParams[slot][param]         │
│                                                                  │           │
└──────────────────────────────────────────────────────────────────┼───────────┘
                                                                   │
                           AUDIO DOMAIN                            │
┌──────────────────────────────────────────────────────────────────┼───────────┐
│                                                                  │           │
│  Generator Synth ◄───────────────────────────────────────────────┘           │
│       │                                                                      │
│       ▼                                                                      │
│  ~genBus[slot] ◄──────────────────────┐ (crossmod taps here)                 │
│       │                               │                                      │
│       ▼                               │                                      │
│  Channel Strip ───────────────────────┼──► ~echoSendBus ──► Echo ──► ~echoReturnBus
│       │                               │                                      │
│       │                               └──► ~verbSendBus ──► Verb ──► ~verbReturnBus
│       ▼                                                                      │
│  ~drySumBus ──────────────────────────┐                                      │
│                                       │                                      │
│  ~echoReturnBus × return level ───────┼──► FX Mixer ──► ~masterBus           │
│  ~verbReturnBus × return level ───────┘                      │               │
│                                                              ▼               │
│                                                      Master Effects          │
│                                                              │               │
│                                                              ▼               │
│                                                       Hardware Out           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Synth Group Order

Execution order matters. Groups run in this sequence:

```
~clockGroup    Clock trigger generation
     ↓
~genGroup      Generator synths + envelope followers
     ↓
~stripGroup    Channel strips
     ↓
~fxGroup       FX processors (echo, reverb)
     ↓
~mixerGroup    FX mixer (dry + returns)
     ↓
~masterGroup   Master effects, limiter, output
```

---

## Bus Counts Summary

| Domain | Bus Type | Count | Description |
|--------|----------|-------|-------------|
| Control | `~genUserParams` | 8 × 10 | User slider values |
| Control | `~genParams` | 8 × 10 | Final modulated values |
| Control | `~modBuses` | 16 | LFO/Sloth/Env outputs |
| Control | `~crossModBus` | 8 | Envelope follower outputs |
| Audio | `~genBus` | 8 × 2ch | Generator outputs |
| Audio | `~echoSendBus` | 2ch | Echo FX input |
| Audio | `~verbSendBus` | 2ch | Reverb FX input |
| Audio | `~echoReturnBus` | 2ch | Echo FX output |
| Audio | `~verbReturnBus` | 2ch | Reverb FX output |
| Audio | `~drySumBus` | 2ch | Dry sum |
| Audio | `~masterBus` | 2ch | Final mix |
| Audio | `~clockTrigBus` | 13ch | Clock triggers (audio rate) |
| Audio | `~midiTrigBus` | 8ch | MIDI triggers (audio rate) |
