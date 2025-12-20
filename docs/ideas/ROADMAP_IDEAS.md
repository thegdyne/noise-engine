# Noise Engine Roadmap — Feature Ideas

*Captured 2025-12-18*

---

## Modulation System Enhancements

### Mod Rate as Mod Target
- [ ] Expose LFO rate as a modulation destination
- [ ] Allow Sloth speed to be modulated (chaos modulating chaos!)
- [ ] Cross-modulation between mod slots

### Source Waveform as Mod Target
- [ ] Per-output waveform selection via mod matrix
- [ ] Waveform morphing between shapes
- [ ] Could enable complex evolving timbres

### Quantizer Module
- [ ] New mod generator type: Quantizer
- [ ] Takes input from another mod bus, outputs quantized steps
- [ ] Scale selection (chromatic, major, minor, pentatonic, custom)
- [ ] Useful for melodic modulation of FRQ param

---

## New Generators

### Noise Module
- [ ] White noise (existing)
- [ ] Pink noise (existing)
- [ ] Brown noise (existing)
- [ ] **Velvet noise** — sparse impulse train, smooth spectrum
- [ ] Blue noise — high-frequency emphasis
- [ ] Violet noise — even steeper HF rise
- [ ] Grey noise — psychoacoustically flat
- [ ] Crackle variations

### Generator SCD Analysis
- [ ] Audit existing .scd files for:
  - CPU efficiency
  - Aliasing issues
  - DC offset problems
  - Proper normalization
- [ ] Document each generator's characteristics
- [ ] Identify candidates for optimization

---

## Filter Improvements

### Fine-Tune Existing Filters
- [ ] Review SVF implementation in core
- [ ] Check coefficient calculations
- [ ] Verify stable at extreme settings

### Better Resonance
- [ ] Smoother self-oscillation curve
- [ ] Less "digital" character at high Q
- [ ] Consider soft-clipping in feedback path

### Reduce Cutoff Stepping/Aliasing
- [ ] Implement parameter smoothing (Lag.kr)
- [ ] Check for zipper noise on fast sweeps
- [ ] Consider oversampling for filter section
- [ ] Review modulation rate vs parameter update rate

### Filter Type Expansion
- [ ] Moog ladder emulation
- [ ] MS-20 style (Sallen-Key)
- [ ] Oberheim SEM style
- [ ] Formant filter (vowel sounds)
- [ ] Comb filter option

---

## UI Enhancements

### Generator Waveform Display
- [ ] Small oscilloscope per generator slot
- [ ] Shows post-filter output
- [ ] Triggered or free-running display
- [ ] Color-coded by generator type
- [ ] Optional — togglable to save CPU

---

## Performance

### Code Performance Analysis
- [ ] Profile Python GUI responsiveness
- [ ] Measure OSC message latency
- [ ] Check for memory leaks in long sessions
- [ ] Optimize scope rendering (mod_scope.py)
- [ ] Review Qt signal/slot overhead

### SuperCollider Performance
- [ ] Measure CPU per generator type
- [ ] Identify expensive UGens
- [ ] Consider SynthDef variants (lite/full)
- [ ] Group optimization (node ordering)

---

## MIDI

### MIDI Learn
- [ ] Click param → move CC → mapped
- [ ] Store mappings in preset
- [ ] Visual indication of mapped params
- [ ] Multiple CCs to same param (layers)

### MIDI Control
- [ ] CC → any parameter
- [ ] Note → generator pitch (already partial)
- [ ] Velocity → amount/depth
- [ ] Aftertouch → mod amount
- [ ] Pitch bend range config
- [ ] MPE support (per-note expression)

---

## Effects Chain

### FX Completely Missing!
Currently no effects implementation. Need:

#### Core FX Types
- [ ] **Delay** — clock-synced, ping-pong, tape style
- [ ] **Reverb** — room, hall, plate, shimmer
- [ ] **Chorus** — classic tri-chorus, ensemble
- [ ] **Flanger** — through-zero capable
- [ ] **Phaser** — 4/8/12 stage options
- [ ] **Distortion** — tube, tape, fuzz, bitcrush
- [ ] **Filter** — additional filtering in FX chain
- [ ] **EQ** — parametric, graphic
- [ ] **Compressor** — per-channel option
- [ ] **Gate** — noise gate with sidechain

#### FX Architecture
- [ ] 4-slot serial chain (designed but not implemented)
- [ ] Per-slot wet/dry
- [ ] FX type selection per slot
- [ ] FX params exposed to mod matrix
- [ ] Preset save/load for FX chain
- [ ] Global bypass

#### FX Modulation
- [ ] Delay time as mod target (for tape wobble)
- [ ] Reverb decay as mod target
- [ ] FX wet/dry as mod target
- [ ] Clock-synced FX rates

---

## Priority Suggestions

### High Priority (Core Experience)
1. FX chain — huge gap in functionality
2. Filter improvements — affects every generator
3. MIDI learn — essential for live use

### Medium Priority (Polish)
4. Generator waveform display
5. Quantizer mod source
6. Cutoff smoothing/aliasing fixes

### Lower Priority (Nice to Have)
7. Velvet/additional noise types
8. Mod rate as target
9. Performance profiling
10. Generator SCD audit

---

## Notes

- FX chain architecture already designed (4 serial slots)
- UI space reserved in layout
- SuperCollider FX SynthDefs straightforward to add
- Consider FX as next major milestone after modulation stabilizes
