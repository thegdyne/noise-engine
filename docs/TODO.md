# Noise Engine TODO

**Updated:** 2025-12-16

---

## Completed This Session ✅

- [x] Generator slot layout refactor (compact, theme-driven)
- [x] CycleButton text clipping and elision
- [x] Layout tuning tool (`tools/tune_layout.py`)
- [x] Tools documentation (`tools/README.md`)

---

## Immediate / Polish

- [ ] **Selector box width** - Widen for long generator names like "Wavetable"
  ```bash
  sed -i '' "s/'header_type_width': 40/'header_type_width': 56/" src/gui/theme.py
  ```
- [ ] **Modulator slot layout** - Apply same compactness treatment as generators
- [ ] **Scroll area dead zones** - Test and verify scroll behavior

---

## Short Term (v1.x)

### UI Polish
- [ ] Generator type labels - full names or better abbreviations
- [ ] Consistent button strip heights across all generators
- [ ] Level meter smoothing refinement
- [ ] Fader popup positioning edge cases

### Modulation System
- [ ] Pin matrix window (visual mod routing)
- [ ] Modulation visualization on sliders
- [ ] Mod amount display on hover

---

## Medium Term (v2.0)

### Presets System (High Priority)
- [ ] Parameter ID system for all controls
- [ ] Central ParameterRegistry
- [ ] Save/load to JSON
- [ ] Preset browser UI

### MIDI Learn (High Priority)
- [ ] MIDI CC mapping to parameters
- [ ] Learn mode (click param, move CC)
- [ ] Save/load mappings
- [ ] Visual feedback during learn
- **Blocked by:** Parameter ID system

### Output Assignment
- [ ] Output pair selector: 1-2, 3-4, 5-6
- [ ] Multi-output mode
- [ ] Query available outputs from device

### Recording
- [ ] Record button (arm/disarm)
- [ ] WAV 24-bit output
- [ ] Auto-naming with timestamp
- [ ] Recording indicator + elapsed time
- [ ] Configurable output directory

---

## Long Term (v2.x+)

### Effects
- [ ] FX send buses
- [ ] Additional insert effects
- [ ] Compressor thrust modes
- [ ] Compressor wet/dry mix

### Input
- [ ] External audio input channels
- [ ] Sidechain input routing

### Skinning
- [ ] Component migration to skin system
- [ ] Additional skin presets (dark, light, vintage)
- [ ] Runtime skin switching
- [ ] Skin editor (future)

### Advanced
- [ ] Quadraphonic output support
- [ ] Project templates
- [ ] Mixer channel reordering

---

## Technical Debt

- [ ] Review generator slot vertical alignment consistency
- [ ] Audit theme values for unused keys
- [ ] Test all generators with new compact layout

---

## Ideas Parking Lot

- Imaginarium (natural language preset generation)
- Voice-to-Sample Factory
- Elektor circuit mining for new generators
- Crystalline ice structure synthesis algorithms

---

## Quick Reference

### Layout Tuning
```bash
python tools/tune_layout.py show
python tools/tune_layout.py gen right 4
python tools/tune_layout.py reset
```

### Run Tests
```bash
python -m pytest tests/ -q
```

### Check Code Quality
```bash
./tools/check_all.sh
```
