# ARSEq+ Implementation - Lessons Learned

## What Went Well
- CDD phased approach (5 phases) provided structure
- Spec was comprehensive and approved before coding
- Edit delivery format (find/replace with context) worked well
- Quick iterations when issues found

## What We Missed

### 1. SC Boot Sequence Not Updated
**Issue:** Created `mod_arseq_plus.scd` but forgot to add it to `init.scd`
**Impact:** SynthDef never loaded, no output
**Fix:** Added to init.scd manually after debugging
**Prevention:** Add "update boot sequence" as explicit phase step

### 2. OSC Parameter Naming Mismatch
**Issue:** Python sent `atkEnv0`, SC expected `atkA`
**Impact:** Attack/release sliders had no effect
**Fix:** Mapped indices to A/B/C/D in main_frame.py handlers
**Prevention:** Define OSC contract explicitly in spec, verify both ends match

### 3. Synth Instantiation Case Missing
**Issue:** mod_slots.scd had no case for "ARSEq+" in the spawn switch
**Impact:** Synth never created when selecting ARSEq+
**Fix:** Added case block with all parameters
**Prevention:** Checklist: SynthDef + init.scd + mod_slots.scd spawn case

### 4. Polarity Handler Generator Check
**Issue:** Polarity handler only checked for "LFO" to use polarityA/B/C/D
**Impact:** ARSEq+ polarity used wrong param names (polarityX/Y/Z/R)
**Fix:** Added `|| (genName == "ARSEq+")` to condition
**Prevention:** Review all existing handlers when adding new generator type

### 5. SC UGen Comparison Syntax
**Issue:** Used `==` for comparison which returns boolean, not UGen
**Impact:** `binary operator '*' failed` error
**Fix:** Changed to range comparisons `(seqStep < 0.5)` etc.
**Prevention:** Remember SC rules: use `<` `>` for UGen comparisons

### 6. UI Button Visibility
**Issue:** gen_button had `setSizePolicy(Ignored)` + `setMinimumWidth(0)`
**Impact:** Button squished to 0 width, invisible for weeks
**Fix:** Removed those lines, kept only `setFixedSize`
**Prevention:** Test UI changes visually before committing

### 7. Slider Style Missing Horizontal
**Issue:** `slider_style()` only defined vertical styling
**Impact:** Horizontal sliders had giant default handles
**Fix:** Added horizontal groove/handle styles
**Prevention:** When adding new orientation, check style coverage

### 8. Mode Button Label Logic
**Issue:** `is_mode_btn` only matched `key == 'mode'`
**Impact:** clock_mode rendered as slider instead of button
**Fix:** Changed to `key in ('mode', 'clock_mode')`
**Prevention:** Review button detection logic when adding stepped params

### 9. CD4017 Sequencing Logic Wrong
**Issue:** Initial implementation triggered all envelopes together
**Impact:** Not sequencing (1→2→3→4), firing simultaneously
**Fix:** Implemented SetResetFF with separate atk/rel triggers per step
**Prevention:** Study reference hardware behavior before coding

### 10. DragSlider Horizontal Direction
**Issue:** DragSlider always used Y-axis delta
**Impact:** Horizontal sliders felt reversed
**Fix:** Added orientation check, use X-axis for horizontal
**Prevention:** Test both orientations when modifying input handling

## Checklist for Future Modulators

### SuperCollider Side
- [ ] Create SynthDef file in `supercollider/core/`
- [ ] Add to `init.scd` boot sequence
- [ ] Add spawn case in `mod_slots.scd`
- [ ] Verify all parameter names match Python side
- [ ] Test UGen comparisons (no `==` for signals)

### Python Side
- [ ] Add to `MOD_GENERATOR_CYCLE` in config
- [ ] Add generator config with custom_params
- [ ] Add output labels in `MOD_OUTPUT_LABELS`
- [ ] Add accent color to theme
- [ ] Create preset state dataclass
- [ ] Add OSC handlers in main_frame.py
- [ ] Verify parameter names match SC side
- [ ] Update any conditional handlers (polarity, wave, etc.)

### UI Side
- [ ] Test button visibility after layout changes
- [ ] Test both slider orientations
- [ ] Verify mode buttons have correct labels
- [ ] Check style coverage for new widgets

### Integration
- [ ] Test full signal path: UI → OSC → SC → output
- [ ] Verify scope shows expected waveforms
- [ ] Test all modes/combinations

## Time Cost of Missed Items

| Issue | Debug Time |
|-------|------------|
| SC boot sequence | 10 min |
| OSC param naming | 15 min |
| Synth spawn case | 10 min |
| Polarity handler | 5 min |
| UGen comparison | 10 min |
| Button visibility | 15 min |
| Slider styling | 5 min |
| Mode button logic | 5 min |
| Sequencing logic | 30 min |
| Slider direction | 10 min |
| **Total** | **~2 hours** |

## Recommendations

1. **Pre-flight checklist** — Run through checklist before "complete"
2. **OSC contract in spec** — Explicit param names for both ends
3. **Integration test step** — Verify signal path before UI polish
4. **Visual smoke test** — Check UI renders correctly, not just compiles
