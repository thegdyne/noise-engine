# Noise Engine Roadmap

**Consolidated feature roadmap — December 2025**

---

## Progress Overview

| Section | Progress | Spec | Rollout | Status |
|---------|----------|------|---------|--------|
| 1. Core Architecture | 100% | ✅ Approved | ✅ Complete | ✅ Done |
| 2. Generator System | 100% | ✅ Approved | ✅ Complete | ✅ Done |
| 3. Modulation System | 95% | ✅ Approved | ✅ Complete | ✅ Done |
| 4. Channel Strips | 100% | ✅ Approved | ✅ Complete | ✅ Done |
| 5. Master Section | 85% | ✅ Approved | ✅ Complete | 🔶 Partial |
| 6. Pack System | 30% | ✅ Approved | ⬜ Not Created | 🔶 Blocked |
| 7. FX System | 5% | 📝 Draft | ⬜ Not Created | ⬜ Blocked |
| 8. Preset System | 0% | ⬜ None | ⬜ Not Created | ⬜ Blocked |
| 9. MIDI Learn | 0% | ⬜ None | ⬜ Not Created | ⬜ Blocked |
| 10. Keyboard Mode | 5% | 📝 Draft | ⬜ Not Created | ⬜ Blocked |
| 11. UI Polish | 60% | ⬜ None | ⬜ Not Created | ⬜ Blocked |
| 12. Mod Matrix Expansion | 0% | ⬜ None | ⬜ Not Created | ⬜ Blocked |
| 13. Imaginarium | 5% | 📝 Draft | ⬜ Not Created | ⬜ Blocked |
| 14. Filter Improvements | 0% | ⬜ None | ⬜ Not Created | ⬜ Blocked |
| 15. Performance | 0% | ⬜ None | ⬜ Not Created | ⬜ Blocked |

**Status Key:**
- ✅ Done — Feature complete
- 🔶 Partial — In progress (spec + rollout approved)
- ⬜ Blocked — Cannot implement until spec AND rollout approved

**Document Key:**
- ✅ Approved — Ready for implementation
- 📝 Draft — Exists, needs approval
- ⬜ None/Not Created — Needs to be written

**Overall Estimated Progress: ~52%**

---

## 1. Core Architecture ✅ 100%

*Python/PyQt5 GUI + SuperCollider audio engine via OSC*

| Feature | Status | Notes |
|---------|--------|-------|
| PyQt5 GUI framework | ✅ Done | Main window, panels, widgets |
| SuperCollider integration | ✅ Done | OSC communication both directions |
| Bus architecture | ✅ Done | Per-generator buses, master bus |
| Config system | ✅ Done | JSON-driven, SSOT compliant |
| Startup sequence | ✅ Done | SC boot, SynthDef loading, UI init |
| CI/CD pipeline | ✅ Done | GitHub Actions, 207 tests passing |

---

## 2. Generator System ✅ 100%

*22+ core generators with JSON config + SCD SynthDef pairs*

| Feature | Status | Notes |
|---------|--------|-------|
| Auto-discovery from JSON | ✅ Done | Scans `supercollider/generators/` |
| 8 generator slots | ✅ Done | Independent selection per slot |
| Standard params (FRQ/CUT/RES/AMP/ATK/DEC) | ✅ Done | All generators |
| Custom params (P1-P5) | ✅ Done | Per-generator JSON config |
| Trigger modes (OFF/CLK/MIDI) | ✅ Done | Per-slot selection |
| MIDI pitch/gate | ✅ Done | Note → FRQ, velocity → gate |
| Generator dropdown cycling | ✅ Done | Click to change |
| 30+ generators available | ✅ Done | Classic synths, 808, atmospheric |

---

## 3. Modulation System ✅ 95%

*Quadrature LFO + Sloth chaos with 4 outputs per slot*

| Feature | Status | Notes |
|---------|--------|-------|
| 3 mod source slots | ✅ Done | LFO, Sloth, Empty |
| 4 outputs per slot (A/B/C/D) | ✅ Done | Quadrature architecture |
| LFO with rate/waveform | ✅ Done | SIN/SAW/SQR/S&H |
| Sloth chaos generator | ✅ Done | Torpor/Apathy/Inertia modes |
| Phase presets (QUAD/PAIR/SPREAD/etc) | ✅ Done | 6 phase configurations |
| NORM/INV polarity per output | ✅ Done | Output-level inversion |
| Mod matrix routing | ✅ Done | Any output → any target |
| Amount control per routing | ✅ Done | Bipolar depth |
| Visual scope per mod slot | ✅ Done | Real-time waveform display |
| Target popup with search | ✅ Done | Quick target selection |
| Empty state handling | 🔶 Partial | Needs polish |

### Planned Additions (Section 12)
- Per-routing INV button
- Auto-allocation system
- Mod locks
- Row/column mute

---

## 4. Channel Strips ✅ 100%

*SSL G-Series inspired mixing per generator*

| Feature | Status | Notes |
|---------|--------|-------|
| Volume fader | ✅ Done | Per-channel level |
| Level meters | ✅ Done | Real-time peak display |
| Pan control | ✅ Done | L/R stereo position |
| Mute button | ✅ Done | Silences channel |
| Solo button | ✅ Done | Solo-in-place with exclusive mode |
| 3-band EQ (LO/MID/HI) | ✅ Done | DJ-style isolator |
| Gain trim | ✅ Done | Input level adjustment |

### Planned Additions
- [ ] Labels on EQ knobs (HI/MID/LO)
- [ ] Send controls for FX buses

---

## 5. Master Section 🔶 85%

*Master output processing chain*

| Feature | Status | Notes |
|---------|--------|-------|
| Master fader | ✅ Done | Output level control |
| Master meters | ✅ Done | Stereo peak display |
| 3-band EQ | ✅ Done | Master tone shaping |
| Compressor | ✅ Done | Bus compression |
| Limiter | ✅ Done | Output protection |
| Device selection | ✅ Done | Shows system default, uses OS setting |
| Output assignment (1-2, 3-4, 5-6) | ⬜ Todo | Route to different outputs |
| Recording | ⬜ Todo | Bounce to disk |

---

## 6. Pack System 🔶 30%

*Organise generators into selectable packs*

**Spec:** `docs/PACK_SYSTEM_SPEC.md`

| Feature | Status | Notes |
|---------|--------|-------|
| Directory structure | ✅ Done | `packs/` with manifest.json |
| Example pack template | ✅ Done | `packs/_example/` |
| Pack discovery code | ✅ Done | Scans manifests at startup |
| Generator loading from packs | ✅ Done | Adds to GENERATOR_CONFIGS |
| test_packs.py | ✅ Done | Unit tests for pack system |
| Pack selector UI | ⬜ Todo | Dropdown in toolbar |
| Exclusive filtering | ⬜ Todo | Pack selection filters dropdowns |
| Preset save/load with pack ref | ⬜ Todo | Phase 2 |
| Pack info tooltip | ⬜ Todo | Hover to see details |
| Pack Manager dialog | ⬜ Todo | Phase 3 |

---

## 7. FX System ⬜ 5%

*Send/return effects buses + master inserts*

**Spec:** `docs/FXBUS.md`

| Feature | Status | Notes |
|---------|--------|-------|
| Architecture design | ✅ Done | 2 send buses, return faders |
| UI space reserved | ✅ Done | Below mixer panel |
| FX Bus A infrastructure | ⬜ Todo | SC buses + routing |
| FX Bus B infrastructure | ⬜ Todo | SC buses + routing |
| Per-channel send controls | ⬜ Todo | Below meters in strip |
| Return faders + meters | ⬜ Todo | FX return section |
| Effect type selector | ⬜ Todo | Dropdown like generators |
| Reverb SynthDef | ⬜ Todo | Room/Hall/Plate |
| Delay SynthDef | ⬜ Todo | Clock-synced, ping-pong |
| Chorus SynthDef | ⬜ Todo | Classic tri-chorus |
| Phaser SynthDef | ⬜ Todo | 4/8/12 stage |
| Distortion SynthDef | ⬜ Todo | Tube/tape/fuzz |

---

## 8. Preset System ⬜ 0%

*Save and recall full configurations*

| Feature | Status | Notes |
|---------|--------|-------|
| Preset format design | ⬜ Todo | JSON structure |
| Save current state | ⬜ Todo | All params to file |
| Load preset | ⬜ Todo | Restore full state |
| Preset browser | ⬜ Todo | Browse/search/filter |
| Categories/tags | ⬜ Todo | Ambient, rhythmic, etc |
| Pack reference in preset | ⬜ Todo | Ties to pack system |
| FX settings in preset | ⬜ Todo | Ties to FX system |
| Modulation matrix in preset | ⬜ Todo | Full mod state |

---

## 9. MIDI Learn ⬜ 0%

*Map hardware controllers to parameters*

| Feature | Status | Notes |
|---------|--------|-------|
| MIDI input detection | ⬜ Todo | See incoming CCs |
| Learn mode (click → move → mapped) | ⬜ Todo | Standard learn UX |
| Visual indication of mapped params | ⬜ Todo | Highlight/badge |
| CC → any parameter | ⬜ Todo | Full parameter access |
| Velocity → depth | ⬜ Todo | Dynamic control |
| Aftertouch support | ⬜ Todo | Pressure modulation |
| Pitch bend config | ⬜ Todo | Range setting |
| Save mappings in preset | ⬜ Todo | Persist with presets |
| MPE support | ⬜ Todo | Future - per-note expression |

---

## 10. Keyboard Mode (CMD+K) ⬜ 5%

*Computer keyboard as musical input*

**Spec:** `docs/KEYBOARD_MODE.md`

| Feature | Status | Notes |
|---------|--------|-------|
| Design complete | ✅ Done | Full spec written |
| CMD+K toggle | ⬜ Todo | Enter/exit keyboard mode |
| QWERTY → chromatic notes | ⬜ Todo | Two-row layout |
| Z/X octave shift | ⬜ Todo | Up/down octave |
| Target last-clicked slot | ⬜ Todo | Focus follows click |
| Auto-switch to MIDI mode | ⬜ Todo | On enter if OFF/CLK |
| Restore mode on exit | ⬜ Todo | Return to previous |
| Status bar indicator | ⬜ Todo | Show `⌨ 3` |
| Slot visual glow | ⬜ Todo | Highlight target |

---

## 11. UI Polish 🔶 60%

*Visual refinements and keyboard shortcuts*

| Feature | Status | Notes |
|---------|--------|-------|
| Consistent widget styling | ✅ Done | Eurorack-inspired |
| Tooltips on controls | ✅ Done | Most controls |
| Keyboard navigation | ✅ Done | Arrow keys, Tab |
| Numeric input (1-0 keys) | ✅ Done | Quick value entry |
| Shift+arrows fine control | ✅ Done | Smaller increments |
| EQ knob labels (HI/MID/LO) | ⬜ Todo | Channel strip |
| Numeric keys while arrows held | ⬜ Todo | Combined input |
| Shift + -/+ for offset | ⬜ Todo | Fine tune offset |
| Generator waveform display | ⬜ Todo | Small scope per slot |

---

## 12. Mod Matrix Expansion ⬜ 0%

*New targets and modulation features*

### Per-Routing Inversion
| Feature | Status | Notes |
|---------|--------|-------|
| INV button in target popup | ⬜ Todo | Per-routing polarity |
| Keyboard shortcut (I key?) | ⬜ Todo | Quick toggle |
| Visual indicator on cell | ⬜ Todo | Show inverted state |

### Auto-Allocation System
| Feature | Status | Notes |
|---------|--------|-------|
| Random flavour | ⬜ Todo | Any source → any target |
| Gentle flavour | ⬜ Todo | Small amounts, standard params |
| Deep flavour | ⬜ Todo | Targets P1-P5 |
| Rhythmic flavour | ⬜ Todo | Fast LFO, envelope targets |
| Textural flavour | ⬜ Todo | Sloth, slow mod, filter/pan |
| Flavour selector UI | ⬜ Todo | Dropdown or buttons |
| Randomise button | ⬜ Todo | Apply selected flavour |

### Modulation Lock
| Feature | Status | Notes |
|---------|--------|-------|
| Right-click → Mod Lock | ⬜ Todo | Toggle lock on param |
| Padlock overlay on locked | ⬜ Todo | Visual indicator |
| Locks respected by auto-alloc | ⬜ Todo | Skip locked params |
| Lock state in presets | ⬜ Todo | Persist locks |

### Row/Column Mute
| Feature | Status | Notes |
|---------|--------|-------|
| Row mute buttons | ⬜ Todo | Mute all FROM source |
| Column mute buttons | ⬜ Todo | Mute all TO target |
| Visual grey-out | ⬜ Todo | Show muted state |

### New Mod Targets
| Target | Status | Notes |
|--------|--------|-------|
| Filter Type (LP/HP/BP) | ⬜ Todo | Generator filter |
| Channel Pan | ⬜ Todo | Stereo position |
| Channel Volume | ⬜ Todo | Level modulation |
| Channel Mute | ⬜ Todo | On/off modulation |
| Channel EQ LO | ⬜ Todo | Low band |
| Channel EQ MID | ⬜ Todo | Mid band |
| Channel EQ HI | ⬜ Todo | High band |
| Master EQ LO | ⬜ Todo | Master low |
| Master EQ MID | ⬜ Todo | Master mid |
| Master EQ HI | ⬜ Todo | Master high |
| LFO Rate | ⬜ Todo | Cross-modulation |
| LFO Waveform | ⬜ Todo | Shape modulation |
| Sloth Mode | ⬜ Todo | Chaos mode selection |

---

## 13. Imaginarium ⬜ 5%

*Natural language → generator configuration*

**Spec:** `docs/IMAGINARIUM.md`, `docs/IMAGINARIUM_LEARNING_SYSTEM.md`

| Feature | Status | Notes |
|---------|--------|-------|
| Concept design | ✅ Done | Full spec written |
| Concept input field | ⬜ Todo | "Dungeon Synth" |
| Percussive ↔ Ambient slider | ⬜ Todo | Balance control |
| Genre database | ⬜ Todo | Generator pools per genre |
| Distribution algorithm | ⬜ Todo | Select generators by ratio |
| P1-P5 class mapping | ⬜ Todo | Semantic param assignment |
| Reload button | ⬜ Todo | Generate new variant |
| Save button | ⬜ Todo | Store preset |
| User feedback collection | ⬜ Todo | Rating + notes |
| Learning system | ⬜ Todo | Improve from feedback |

---

## 14. Filter Improvements ⬜ 0%

*Better filter quality and more types*

### Quality
| Feature | Status | Notes |
|---------|--------|-------|
| SVF coefficient review | ⬜ Todo | Verify calculations |
| Smoother resonance curve | ⬜ Todo | Less digital character |
| Parameter smoothing (Lag.kr) | ⬜ Todo | Reduce zipper noise |
| Consider oversampling | ⬜ Todo | For extreme settings |

### New Filter Types
| Type | Status | Notes |
|------|--------|-------|
| Moog ladder | ⬜ Todo | Classic 24dB/oct |
| MS-20 (Sallen-Key) | ⬜ Todo | Aggressive character |
| Oberheim SEM | ⬜ Todo | Smooth 12dB/oct |
| Formant (vowel) | ⬜ Todo | A/E/I/O/U shapes |
| Comb filter | ⬜ Todo | Resonator effect |

---

## 15. Performance ⬜ 0%

*Profiling and optimisation*

### Python/GUI
| Feature | Status | Notes |
|---------|--------|-------|
| Profile GUI responsiveness | ⬜ Todo | Find bottlenecks |
| Measure OSC latency | ⬜ Todo | Round-trip timing |
| Memory leak check | ⬜ Todo | Long session stability |
| Scope rendering optimisation | ⬜ Todo | mod_scope.py |

### SuperCollider
| Feature | Status | Notes |
|---------|--------|-------|
| CPU per generator audit | ⬜ Todo | Measure each type |
| Identify expensive UGens | ⬜ Todo | Optimisation targets |
| SynthDef lite variants | ⬜ Todo | Lower CPU options |
| Group ordering review | ⬜ Todo | Node execution |

---

## 16. Future Ideas (Parking Lot)

*Lower priority / longer term*

- Sequencer (bottom panel placeholder exists)
- Sample loading / playback
- Granular sampler with file import
- Wavetable import
- Project save/load (full session)
- Undo/redo system
- Themes / dark mode variations
- Tutorial / onboarding mode
- Server control panel (s.freeAll, s.reboot)
- Eurorack send/return integration
- CV output via CV.OCD
- Per-generator transpose
- Multitimbral mode (chords)
- Generator initial filter type setting
- New noise types (velvet, blue, violet, grey)

---

## Document References

### Specs

| Feature | Spec | Status |
|---------|------|--------|
| Pack System | `docs/PACK_SYSTEM_SPEC.md` | ✅ Approved |
| Generator Authoring | `docs/GENERATOR_SPEC.md` | ✅ Approved |
| Keyboard Mode | `docs/KEYBOARD_MODE.md` | 📝 Draft |
| FX Buses | `docs/FXBUS.md` | 📝 Draft |
| Master Output | `docs/MASTER_OUT.md` | ✅ Approved |
| Imaginarium | `docs/IMAGINARIUM.md` | 📝 Draft |
| Architecture | `docs/ARCHITECTURE.md` | ✅ Approved |
| Decisions | `docs/DECISIONS.md` | ✅ Approved |
| Preset System | — | ⬜ Not Created |
| MIDI Learn | — | ⬜ Not Created |
| Mod Matrix Expansion | — | ⬜ Not Created |
| Filter Improvements | — | ⬜ Not Created |
| UI Polish | — | ⬜ Not Created |

### Rollout Plans

| Feature | Rollout Plan | Status |
|---------|--------------|--------|
| Pack System | `docs/rollout/PACK_SYSTEM_ROLLOUT.md` | ⬜ Not Created |
| FX System | `docs/rollout/FX_ROLLOUT.md` | ⬜ Not Created |
| Preset System | `docs/rollout/PRESET_ROLLOUT.md` | ⬜ Not Created |
| MIDI Learn | `docs/rollout/MIDI_LEARN_ROLLOUT.md` | ⬜ Not Created |
| Keyboard Mode | `docs/rollout/KEYBOARD_MODE_ROLLOUT.md` | ⬜ Not Created |
| Mod Matrix Expansion | `docs/rollout/MOD_MATRIX_ROLLOUT.md` | ⬜ Not Created |
| Imaginarium | `docs/rollout/IMAGINARIUM_ROLLOUT.md` | ⬜ Not Created |

### Templates

| Template | Location |
|----------|----------|
| Spec Template | `docs/SPEC_TEMPLATE.md` |
| Rollout Template | `docs/ROLLOUT_TEMPLATE.md` |

---

## Spec-First Workflow

**Rule: No implementation without approved spec AND rollout plan.**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   1. SPEC   │────▶│ 2. ROLLOUT  │────▶│ 3. APPROVE  │────▶│ 4. IMPLEMENT│
│   (what)    │     │   (how)     │     │   (gate)    │     │   (build)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     draft              draft            both approved        CI checks
```

### Step 1: Create Spec
- Use `docs/SPEC_TEMPLATE.md`
- Define what the feature does and why
- Set `status: draft`

### Step 2: Create Rollout Plan  
- Use `docs/ROLLOUT_TEMPLATE.md`
- Break into phases (max 1-2 days each)
- Define tests for each phase
- Set `status: draft`

### Step 3: Approve Both
- Review spec and rollout in chat session
- When agreed, change both to `status: approved`
- Set `approved_date` on both

### Step 4: Implement
- Create PR with implementation
- CI checks for approved spec + rollout
- Each phase must pass its tests before next phase
- Update rollout sign-off table as phases complete

### CI Enforcement

`.github/workflows/spec-check.yml` runs on every PR:
- Maps changed files to features
- Verifies spec exists and is approved
- Verifies rollout plan exists and is approved
- **Blocks merge if either missing or draft**

### Directory Structure

```
docs/
├── SPEC_TEMPLATE.md
├── ROLLOUT_TEMPLATE.md
├── PACK_SYSTEM_SPEC.md          # Feature specs
├── FX_SPEC.md
├── ...
└── rollout/
    ├── PACK_SYSTEM_ROLLOUT.md   # Rollout plans
    ├── FX_ROLLOUT.md
    └── ...
```

---

*Last updated: December 2025*

## Effect Ideas (from hardware concepts)

### Second Harmonic Tracker
Pitch-tracking resonant filter locked to 2x fundamental. Creates singing overtone that follows played notes. Mix control for blend. Inspired by valve harmonic enhancement.

### Supply Sag / Rail Modulation  
Modulate signal amplitude (and optionally filter) with LFO to simulate unstable power supply. Sine = tube sag/bloom, square = choppy gate. Freq + depth + waveform controls.

### Feedback Sustainer
Compression + feedback loop for infinite sustain. Signal gradually crossfades from fundamental into upper harmonics. Like software EBow. Sustain + harmonic blend controls.

## Master Heat (Analog Heat style)

Saturation/distortion section for master output, inspired by Elektron Analog Heat.

### Core Circuits
- **CLEAN** — Subtle overdrive, old mixer character
- **TAPE** — Tape saturation, woolly warmth
- **TUBE** — Tube-like glow and sheen  
- **CRUNCH** — Gritty, aggressive character

### Controls
- Circuit selector (dropdown)
- DRIVE — Gain into circuit (0-100%)
- MIX — Wet/dry blend (0-100%)
- ON/OFF toggle

### Signal Flow
After compressor, before limiter:
`EQ → Compressor → Heat → Limiter → Master Vol`

### Implementation Notes
SuperCollider waveshaping with different transfer functions per circuit type.
Could use tanh, softclip, parabolic, or crossover distortion algorithms.

## Master Heat (Analog Heat style)

Saturation/distortion section for master output, inspired by Elektron Analog Heat.

### Core Circuits
- **CLEAN** — Subtle overdrive, old mixer character
- **TAPE** — Tape saturation, woolly warmth
- **TUBE** — Tube-like glow and sheen  
- **CRUNCH** — Gritty, aggressive character

### Controls
- Circuit selector (dropdown)
- DRIVE — Gain into circuit (0-100%)
- MIX — Wet/dry blend (0-100%)
- ON/OFF toggle

### Signal Flow
After compressor, before limiter:
`EQ → Compressor → Heat → Limiter → Master Vol`

### Implementation Notes
SuperCollider waveshaping with different transfer functions per circuit type.
Could use tanh, softclip, parabolic, or crossover distortion algorithms.

## Master FX Ideas

### Analog-Inspired

#### Master Heat (Analog Heat style)
Saturation/distortion section for master output.

**Circuits:**
- CLEAN — Subtle overdrive, old mixer character
- TAPE — Tape saturation, woolly warmth  
- TUBE — Tube-like glow and sheen
- CRUNCH — Gritty, aggressive character

**Controls:** Circuit selector, DRIVE, MIX, ON/OFF

**Signal Flow:** After compressor, before limiter

**Implementation:** SuperCollider waveshaping with different transfer functions per circuit. tanh, softclip, parabolic, crossover distortion.

---

#### Space Echo (Roland RE-201 style)
Tape delay with degradation and spring reverb character.

**Core Character:**
- Multi-tap delay (3 virtual playback heads)
- High frequency loss per repeat (darker echoes)
- Tape saturation on feedback path
- Wow/flutter from motor variation
- Optional spring reverb

**Controls:**
| Control | Function |
|---------|----------|
| TIME | Delay time 50-500ms |
| FEEDBACK | Regeneration/intensity |
| TONE | High-cut on feedback (darker repeats) |
| WOW | Pitch modulation depth |
| MIX | Wet/dry blend |
| MODE | Single / Multi-tap (3 heads) |
| REVERB | Spring reverb blend |

**Implementation:** DelayC with LPF in feedback, SinOsc for wow modulation, slight saturation per repeat.

---

### Digital FX

#### Shimmer Reverb
Pitch-shifted reverb for ethereal pads.

**Controls:** SIZE, DECAY, SHIMMER (pitch shift amount ±12st), TONE, MIX

**Implementation:** FreeVerb or GVerb with PitchShift in feedback loop. Octave up (+12st) is classic shimmer.

---

#### Spectral Freeze
FFT-based effect that captures and holds a spectral snapshot.

**Controls:** FREEZE (trigger/gate), BLUR (spectral smear), MIX

**Implementation:** FFT with PV_Freeze, PV_MagSmear for blur.

---

#### Granular Smear  
Buffer-based granular processing for texture and timestretching.

**Controls:** 
- GRAIN SIZE (10-500ms)
- DENSITY (grains per second)
- PITCH (±24st)
- SPREAD (stereo scatter)
- POSITION (playback position in buffer)
- MIX

**Implementation:** GrainBuf or TGrains with modulatable parameters.

---

#### Bit Reducer
Digital degradation — sample rate and bit depth reduction.

**Controls:**
- BITS (1-16 bit depth)
- RATE (sample rate reduction factor)
- MIX

**Implementation:** Decimator UGen or manual sample-and-hold with quantization.

---

#### Resonator Bank
Tuned comb filter bank for metallic/tonal coloring.

**Controls:**
- ROOT (fundamental frequency)
- CHORD (interval structure: unison, 5th, octave, etc.)
- DECAY (ring time)
- BRIGHTNESS (damping)
- MIX

**Implementation:** Bank of CombC filters tuned to harmonic intervals.

---

#### Frequency Shifter
True frequency shift (not pitch shift) — creates inharmonic content.

**Controls:**
- SHIFT (-500 to +500 Hz)
- MIX

**Implementation:** FreqShift UGen. Small shifts = phaser-like, large shifts = metallic/robotic.

---

#### Stutter / Glitch
Buffer capture with rhythmic retriggering.

**Controls:**
- SIZE (buffer length: 1/32 to 1/1 beat divisions)
- RETRIG (manual or sync'd trigger)
- REVERSE (probability or toggle)
- PITCH (repitch buffer ±12st)
- MIX

**Implementation:** BufWr/BufRd with trigger logic, tempo sync.

---

#### Infinite Reverb
Reverb with feedback >= 1 for drones and washes.

**Controls:**
- SIZE
- FREEZE (locks decay at infinity)
- TONE (LPF/HPF on feedback)
- MOD (subtle pitch modulation to avoid metallic buildup)
- MIX

**Implementation:** GVerb or custom FDN with controllable feedback, HPF/LPF in loop.

---

### FX Architecture Notes

**Master Section Chain (proposed):**
```
Channel Strips → Mixer Sum → EQ → Compressor → Heat → Space Echo → Master FX Slot → Limiter → Output
```

**Per-Channel FX (future):**
Each channel strip could have an FX slot before the mixer. Simpler effects only (filter, drive, delay send).

**Modulation:**
All FX parameters should be modulatable via the existing mod matrix system.
