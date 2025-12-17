# Noise Engine TODO

**Updated:** 2025-12-17

---

## Completed This Session ✅

- [x] Modulator mode button width (48x22, was 19px)
- [x] Header bar stability (fixed-width button 180x27, status 130x16)
- [x] Layout debug F9 hotkey toggle
- [x] Red border highlighting for fixed-size widgets
- [x] Layout sandbox tool with torture testing
- [x] Shell aliases documentation

---

## Previously Completed ✅

- [x] Generator slot layout refactor (compact, theme-driven)
- [x] CycleButton text clipping and elision
- [x] Layout tuning tool (`tools/tune_layout.py`)
- [x] Tools documentation (`tools/README.md`)
- [x] Modulator slot layout compactness

---

## Immediate / Polish

- [ ] **Selector box width** - Widen for long generator names like "Wavetable"
- [ ] **Review mixer section** - Check for similar resizing button issues
- [ ] **Test all generators** - Verify compact layout with debug overlay

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

- [ ] Audit theme values for unused keys
- [ ] Review generator slot vertical alignment consistency
- [ ] Test all generators with new compact layout

---

## Ideas Parking Lot

- Imaginarium (natural language preset generation)
- Voice-to-Sample Factory
- Elektor circuit mining for new generators
- Crystalline ice structure synthesis algorithms

---

## Quick Reference

### Development Aliases
```bash
noise          # Run app
noise-debug    # Run with debug overlay
noise-sandbox  # Test generator in isolation
noise-torture  # Test with long names
```

### Layout Debugging
```bash
# In app: press Fn+F9 to toggle overlay
# Red borders = fixed-size widgets

# Quick check in code:
from gui.layout_debug import dump_layout
dump_layout(widget)  # Shows: geo, hint, policy, min/max
```

### Run Tests
```bash
python -m pytest tests/ -q
```

### Check Code Quality
```bash
./tools/check_all.sh
```
