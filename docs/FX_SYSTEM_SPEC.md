# FX System Spec v1.0

**Status:** APPROVED  
**Date:** 2025-12-19  
**Author:** Gareth + Claude (with AI1/AI2 consultation)

---

## Overview

Master FX chain for Noise Engine combining analog-inspired character effects with flexible routing. Extends existing master section (EQ, Compressor, Limiter) with saturation, delay, reverb, and dual-filter processing.

---

## Architecture Summary

**Master Inserts (inline):** EQ → Filterbank → Heat → Compressor → Limiter  
**Send/Return FX (parallel):** Tape Echo, Reverb — merge at preMasterBus before inserts

---

## Signal Chain

```
[8 Generators] → Channel Strips (vol/pan/EQ)
                         ↓
                    Per-gen sends tap here (post-fader)
                         ↓
                    ┌────┴────┐
                    ↓         ↓
              drySumBus    Send A → Tape Echo (100% wet) → echoReturnBus
                    ↓         ↓
                    ↓      Send B → Reverb (100% wet) → verbReturnBus
                    ↓         ↓
                    └────┬────┘
                         ↓
                   preMasterBus (dry + returns @ return levels)
                         ↓
                   ══════════════════════════════
                   ║    MASTER INSERT CHAIN     ║
                   ══════════════════════════════
                         ↓
                   DJ Isolator EQ (existing)
                         ↓
                   Filterbank (INSERT-only)
                         ↓
                   Heat (saturation)
                         ↓
                   SSL Compressor (existing)
                         ↓
                   Limiter (existing)
                         ↓
                       Output
```

### Design Decision: Returns Pre-Dynamics

FX returns merge BEFORE the master insert chain. This means:
- Echo and reverb tails go through Heat saturation and SSL compression
- Creates cohesive "one box" analog character
- Reverb pumping is a feature for dub/shoegaze aesthetics
- Consistent with Noise Engine as a character instrument, not a mixing console

**Tradeoff:** Less separation between dry and FX. If clean reverb tails are needed, reduce return level and increase send level.

---

## Module Specifications

### 1. Heat (Saturation Module Saturation)

**Purpose:** Add analog warmth and harmonic density to master bus.

**Architecture:** Single SynthDef with circuits as parameter presets.

#### Design Decision: Single Topology

All four circuits use the same DSP graph with different coefficients:

```
HPF(dc_cut) → PreGain → Waveshaper(curve, asymmetry) → LPF(hf_loss) → PostGain
```

This enables click-free Lag'd switching between circuits. True hysteresis/sag modeling deferred to future "Studio Tape" module if requested.

#### Circuits

| Circuit | Curve | Asymmetry | HF Loss | Character |
|---------|-------|-----------|---------|-----------|
| CLEAN | Soft tanh | Low | None | Subtle mixer warmth |
| TAPE | Soft tanh | Medium | Yes (-3dB @ 8kHz) | Woolly, rolled-off |
| TUBE | Softer curve | High (even harmonics) | Slight | Glowing sheen |
| CRUNCH | Harder clip | Medium | Slight | Gritty aggressive |

#### Controls

| Control | Range | Function |
|---------|-------|----------|
| CIRCUIT | Clean/Tape/Tube/Crunch | Preset selector |
| DRIVE | 0-100% | Gain into saturation |
| MIX | 0-100% | Wet/dry blend |
| ON/OFF | Toggle | Bypass (click-free crossfade) |

#### Implementation Notes

```supercollider
// Circuit switching via VarLag (50ms, no clicks)
curve = VarLag.kr(\curve.kr, 0.05);
asymmetry = VarLag.kr(\asymmetry.kr, 0.05);
hfLoss = VarLag.kr(\hfLoss.kr, 0.05);
```

---

### 2. Tape Echo (RE-201 Inspired)

**Purpose:** Tape delay with degradation character, optional spring reverb, and reverb bus cross-feed.

**Architecture:** Send/return bus with per-generator send amounts. Single SynthDef with internal feedback loop.

#### Core Character

- Multi-tap delay (3 virtual playback heads)
- Tape saturation in feedback path (repeats degrade/warm)
- High-cut filter in feedback (progressive darkening)
- Wow/flutter from motor variation (subtle pitch modulation)
- Optional spring reverb (internal to unit)
- **Reverb cross-feed** (wet signal can feed main Reverb bus)

#### Controls

| Control | Range | Default | Function |
|---------|-------|---------|----------|
| TIME | 50-500ms | 200ms | Delay time (linear scale) |
| FEEDBACK | 0-100% | 30% | Regeneration/intensity |
| TONE | 0-100% | 70% | High-cut on feedback path |
| WOW | 0-100% | 10% | Pitch modulation depth |
| SPRING | 0-100% | 0% | Internal spring reverb |
| VERB SEND | 0-100% | 0% | Echo wet → Reverb input (classic tape echo vibe) |
| RETURN | 0-100% | 50% | Return level to preMasterBus |

#### Implementation Notes

```supercollider
// Internal feedback loop - NOT external bus routing
SynthDef(\spaceEcho, {
    var input, delayed, feedback, output;
    
    input = In.ar(~echoSendBus, 2);
    feedback = LocalIn.ar(2);
    
    // Delay with feedback processing
    delayed = DelayC.ar(input + (feedback * fbAmount), 0.5, time);
    delayed = LPF.ar(delayed, toneFreq);  // Progressive darkening
    delayed = (delayed * 0.99).tanh;       // Tape saturation
    
    // Wow/flutter
    delayed = DelayC.ar(delayed, 0.01, SinOsc.kr(wowRate, 0, wowDepth * 0.001));
    
    LocalOut.ar(delayed);
    
    // Optional spring + verb send
    output = delayed + (spring * SpringVerb.ar(delayed));
    
    Out.ar(~echoReturnBus, output);
    Out.ar(~verbSendBus, output * verbSend);  // Cross-feed to reverb
});
```

---

### 3. Reverb (Clean Plate/Room)

**Purpose:** Spatial ambience separate from Tape Echo's character.

**Architecture:** Send/return bus with per-generator send amounts. 100% wet on bus.

#### Controls

| Control | Range | Default | Function |
|---------|-------|---------|----------|
| SIZE | 0-100% | 50% | Room size |
| DECAY | 0-100% | 50% | Tail length |
| TONE | 0-100% | 70% | Damping / brightness |
| RETURN | 0-100% | 30% | Return level to preMasterBus |

#### Implementation Notes

- Use FreeVerb for v1.0 (low CPU, decent quality)
- HPF at 80Hz before reverb (prevent low-end wash)
- 100% wet output — blend via return level only

---

### 4. Filterbank (Dual Filter Style)

**Purpose:** Dual resonant filters with tube overdrive for aggressive sound design.

**Architecture:** Master INSERT only (no send mode in v1.0). Simplifies routing and matches typical dual-filter usage.

#### Signal Flow

```
preMasterBus → HPF(dc) → Drive → Filter1 ─┬─ Serial ─→ Filter2 → Output
                                          └─ Parallel → Mix → Output
```

#### Controls

| Control | Range | Default | Function |
|---------|-------|---------|----------|
| DRIVE | 0-100% | 0% | Input tube overdrive |
| FREQ 1 | 20Hz-20kHz | 1kHz | Filter 1 frequency |
| RESO 1 | 0-100% | 0% | Filter 1 resonance |
| MODE 1 | LP/BP/HP | BP | Filter 1 type |
| FREQ 2 | 20Hz-20kHz | 500Hz | Filter 2 frequency |
| RESO 2 | 0-100% | 0% | Filter 2 resonance |
| MODE 2 | LP/BP/HP | BP | Filter 2 type |
| HARMONICS | Free/1/2/3/4/5/8/16 | Free | Filter 2 sync ratio |
| ROUTING | Serial/Parallel | Serial | Filter topology |
| MIX | 0-100% | 100% | Wet/dry blend |
| ON/OFF | Toggle | OFF | Bypass (click-free crossfade) |

#### Harmonics Sync Ratios

Filter 2 frequency = Filter 1 frequency / ratio (subharmonics):

| Setting | Formula | Musical Interval |
|---------|---------|------------------|
| Free | Independent | No sync |
| 1 | F2 = F1 | Unison |
| 2 | F2 = F1 / 2 | Octave down |
| 3 | F2 = F1 / 3 | Octave + fifth down |
| 4 | F2 = F1 / 4 | 2 octaves down |
| 5 | F2 = F1 / 5 | 2 oct + major 3rd down |
| 8 | F2 = F1 / 8 | 3 octaves down |
| 16 | F2 = F1 / 16 | 4 octaves down |

#### Safety Features (Critical)

```supercollider
// Resonance output limiting
output = Limiter.ar(output, 0.95);

// Frequency smoothing (exponential for musical response)
freq1 = VarLag.kr(\freq1.kr, 0.02, warp: \exp);
freq2 = VarLag.kr(\freq2.kr, 0.02, warp: \exp);

// Resonance smoothing (linear OK)
reso1 = Lag.kr(\reso1.kr, 0.02);
reso2 = Lag.kr(\reso2.kr, 0.02);

// Click-free bypass
output = XFade2.ar(dry, wet, Lag.kr(\bypass.kr, 0.05) * 2 - 1);
```

#### Implementation Notes

- Lives permanently in masterGroup (no group switching)
- HPF at 20Hz before drive stage (DC protection)
- Output limiter internal to module (don't rely on master limiter)
- Self-oscillation possible — safety limiter catches it

---

## Routing Architecture

### Per-Generator Sends

Each generator gets 2 send amounts (Filterbank is INSERT, not send):

```
Channel Strip Click → Popover:
  [HI] [MID] [LO]         ← Existing EQ
  [ECHO] [VERB]           ← Sends (0-100% each)
```

#### Send Behavior

- Post-fader (FX follow channel volume)
- Tap after channel EQ, before drySumBus
- 0% = no signal to FX bus

### Master Section Returns

```
Master Section:
  [ECHO RTN] [VERB RTN]   ← Return levels to preMasterBus
```

### preMasterBus Mixer

Explicit mixer synth sums dry + returns:

```supercollider
SynthDef(\preMasterMixer, {
    var dry, echoRtn, verbRtn, mixed;
    
    dry = In.ar(~drySumBus, 2);
    echoRtn = In.ar(~echoReturnBus, 2) * \echoReturn.kr(0.5);
    verbRtn = In.ar(~verbReturnBus, 2) * \verbReturn.kr(0.3);
    
    mixed = dry + echoRtn + verbRtn;
    
    ReplaceOut.ar(~preMasterBus, mixed);
}).add;
```

---

## UI Layout

### Channel Strip Popover (Updated)

```
┌─────────────────────────┐
│  CHANNEL 1 SETTINGS     │
├─────────────────────────┤
│  EQ                     │
│  [HI]  [MID]  [LO]      │
├─────────────────────────┤
│  SENDS                  │
│  [ECHO]  [VERB]         │
└─────────────────────────┘
```

### Master FX Panel (Popup Window)

Click "FX" button in master section to open:

```
┌─────────────────────────────────────────────────────────┐
│  MASTER FX                                        [X]   │
├─────────────────────────────────────────────────────────┤
│  HEAT                                           [ON]    │
│  [CIRCUIT: Tape ▼]  [DRIVE ●───]  [MIX ●───]            │
├─────────────────────────────────────────────────────────┤
│  SPACE ECHO                                             │
│  [TIME]  [FDBK]  [TONE]  [WOW]  [SPRING]  [→VRB]  [RTN] │
├─────────────────────────────────────────────────────────┤
│  REVERB                                                 │
│  [SIZE]  [DECAY]  [TONE]  [RTN]                         │
├─────────────────────────────────────────────────────────┤
│  FILTERBANK                                     [ON]    │
│  [DRIVE]  [F1 ●]  [R1]  [M1▼]  [F2 ●]  [R2]  [M2▼]     │
│  [HARMONICS: Free ▼]  [ROUTING: Serial ▼]  [MIX]        │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Infrastructure

- [ ] Create bus architecture in SC:
  - `~drySumBus` (stereo)
  - `~echoSendBus`, `~verbSendBus` (stereo)
  - `~echoReturnBus`, `~verbReturnBus` (stereo)
  - `~preMasterBus` (stereo)
- [ ] Allocate buses ONCE at boot (store indices in config)
- [ ] Create `preMasterMixer` synth
- [ ] Define synth groups with correct order:
  ```
  genGroup → stripGroup → sendGroup → fxGroup → mixerGroup → masterGroup
  ```
- [ ] Add per-generator send amounts to channel strips
- [ ] OSC messages for sends and returns

### Phase 2: Heat + Tape Echo

- [ ] Heat SynthDef (single topology, 4 circuit presets)
- [ ] Heat UI in FX popup (circuit, drive, mix, bypass)
- [ ] Tape Echo SynthDef (LocalIn/LocalOut feedback, spring, verb send)
- [ ] Tape Echo UI (time, feedback, tone, wow, spring, verb send, return)
- [ ] Per-generator echo send in channel strip popover
- [ ] Echo return control in master section

### Phase 3: Reverb + Filterbank

- [ ] Reverb SynthDef (FreeVerb with pre-HPF)
- [ ] Reverb UI (size, decay, tone, return)
- [ ] Per-generator verb send in channel strip popover
- [ ] Verb return control in master section
- [ ] Filterbank SynthDef (dual filter, drive, harmonics sync, safety limiter)
- [ ] Filterbank UI (all controls + bypass)
- [ ] VarLag for filter frequencies (exp warp)

### Phase 4: Polish

- [ ] Modulation targets (selected FX params in mod matrix):
  - Heat: drive
  - Echo: time, feedback
  - Filterbank: freq1, freq2, reso1, reso2
- [ ] FX state save/load with presets
- [ ] Tempo sync for Tape Echo time (optional)
- [ ] Documentation

---

## SuperCollider Architecture

### Bus Allocation (at boot, ONCE)

```supercollider
// Allocate all buses at startup - indices stored for SSOT
~drySumBus = Bus.audio(s, 2);
~echoSendBus = Bus.audio(s, 2);
~verbSendBus = Bus.audio(s, 2);
~echoReturnBus = Bus.audio(s, 2);
~verbReturnBus = Bus.audio(s, 2);
~preMasterBus = Bus.audio(s, 2);

// Store indices for Python/OSC reference
~busIndices = (
    drySumBus: ~drySumBus.index,
    echoSendBus: ~echoSendBus.index,
    // ... etc
);
```

### Group Order

```supercollider
~genGroup = Group.new(s);
~stripGroup = Group.after(~genGroup);
~sendGroup = Group.after(~stripGroup);      // Taps sends from strips
~fxGroup = Group.after(~sendGroup);         // Echo, Reverb processors
~mixerGroup = Group.after(~fxGroup);        // preMasterMixer
~masterGroup = Group.after(~mixerGroup);    // EQ, Filterbank, Heat, Comp, Limiter
```

### Out vs ReplaceOut Rules

- **Generators → Out.ar** (summing into drySumBus)
- **Channel strips → Out.ar** (summing)
- **Send taps → Out.ar** (summing into send buses)
- **FX processors → Out.ar** (into return buses, 100% wet)
- **preMasterMixer → ReplaceOut.ar** (overwrites preMasterBus)
- **Master inserts → ReplaceOut.ar** (in series)

### OSC Messages

```
// Per-slot sends
/slot/{n}/echo_send {0.0-1.0}
/slot/{n}/verb_send {0.0-1.0}

// Master returns
/master/echo_return {0.0-1.0}
/master/verb_return {0.0-1.0}

// Heat
/master/heat/circuit {0-3}
/master/heat/drive {0.0-1.0}
/master/heat/mix {0.0-1.0}
/master/heat/bypass {0|1}

// Tape Echo
/master/echo/time {0.0-1.0}      → maps to 50-500ms linear
/master/echo/feedback {0.0-1.0}
/master/echo/tone {0.0-1.0}
/master/echo/wow {0.0-1.0}
/master/echo/spring {0.0-1.0}
/master/echo/verb_send {0.0-1.0}

// Reverb
/master/verb/size {0.0-1.0}
/master/verb/decay {0.0-1.0}
/master/verb/tone {0.0-1.0}

// Filterbank
/master/fb/drive {0.0-1.0}
/master/fb/freq1 {0.0-1.0}      → maps to 20Hz-20kHz exponential
/master/fb/reso1 {0.0-1.0}
/master/fb/mode1 {0-2}          → LP/BP/HP
/master/fb/freq2 {0.0-1.0}      → maps to 20Hz-20kHz exponential
/master/fb/reso2 {0.0-1.0}
/master/fb/mode2 {0-2}
/master/fb/harmonics {0-7}      → Free/1/2/3/4/5/8/16
/master/fb/routing {0|1}        → Serial/Parallel
/master/fb/mix {0.0-1.0}
/master/fb/bypass {0|1}
```

### Parameter Mapping

```supercollider
// Echo time: linear 50-500ms
time = \time.kr(0.4).linlin(0, 1, 0.05, 0.5);

// Filter freq: exponential 20Hz-20kHz
freq1 = \freq1.kr(0.5).linexp(0, 1, 20, 20000);

// All other params: linear 0-1 (scaled in SynthDef as needed)
```

---

## Config Integration (SSOT)

```python
# src/config/__init__.py additions

FX_DEFAULTS = {
    'heat': {
        'circuit': 0,      # CLEAN
        'drive': 0.0,
        'mix': 1.0,
        'bypass': True
    },
    'echo': {
        'time': 0.4,       # ~200ms
        'feedback': 0.3,
        'tone': 0.7,
        'wow': 0.1,
        'spring': 0.0,
        'verb_send': 0.0,  # Echo → Reverb cross-feed
        'return': 0.5
    },
    'verb': {
        'size': 0.5,
        'decay': 0.5,
        'tone': 0.7,
        'return': 0.3
    },
    'filterbank': {
        'drive': 0.0,
        'freq1': 0.5,      # ~1kHz
        'reso1': 0.0,
        'mode1': 1,        # BP
        'freq2': 0.35,     # ~500Hz
        'reso2': 0.0,
        'mode2': 1,        # BP
        'harmonics': 0,    # Free
        'routing': 0,      # Serial
        'mix': 1.0,
        'bypass': True
    }
}

SLOT_SEND_DEFAULTS = {
    'echo': 0.0,
    'verb': 0.0
}
```

---

## Testing Requirements

### Unit Tests

- [ ] Heat circuit switching (verify Lag, no clicks)
- [ ] Echo feedback doesn't runaway (verify internal limiting)
- [ ] Filterbank resonance clamped (verify safety limiter)
- [ ] Harmonics ratios calculate correctly
- [ ] Bus allocation indices stable across reload

### Integration Tests

- [ ] Send/return signal flow correct (verify with test tone)
- [ ] preMasterMixer sums correctly
- [ ] Master insert chain order verified
- [ ] FX params appear in mod matrix

### Manual Tests

- [ ] Block-alignment: change sends while audio runs, verify no one-buffer-late
- [ ] Filterbank bypass: toggle rapidly under signal, verify no dropouts
- [ ] Return + limiter interaction: extreme feedback, check for ugly pumping
- [ ] All knobs respond without clicks/zips
- [ ] CPU usage acceptable with all FX enabled

---

## Stereo Handling

- Generators: Mono source, `~stereoSpread` creates stereo
- Channel strips: Stereo processing (pan, EQ)
- Send buses: Stereo
- FX processors: Stereo in/out
- Master chain: Stereo throughout

---

## Future Additions (v1.1+)

- Filterbank SEND mode (per-generator sends) if requested
- Post-dynamics return option (toggle)
- Tempo sync for Tape Echo
- Quadraverb-style multi-algorithm reverb
- Shimmer reverb
- Spectral freeze
- Granular smear
- Bit reducer
- Chorus/ensemble
- Stereo width control
- Sidechain ducking

---

## References (Design Inspiration)

*The following hardware informed design approach. Noise Engine's implementation is original.*

- Elektron saturation circuits (Heat module topology)
- Roland RE-201 tape echo (Tape Echo character)
- Sherman dual-filter design (Dual Filter concept)
- AI1/AI2 consultation (2025-12-19)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| DRAFT 1.0 | 2025-12-19 | Initial draft |
| v1.0 | 2025-12-19 | AI review incorporated: Filterbank INSERT-only, Heat single topology, returns pre-dynamics, 4 phases, Echo verb_send, explicit bus architecture |

---

*Document version: v1.0 APPROVED*
