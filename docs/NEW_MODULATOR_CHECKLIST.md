# New Modulator Implementation Checklist

Use this checklist to avoid the mistakes made during ARSEq+ development.

## Phase 0: Spec Review
- [ ] Spec has explicit OSC parameter names (Python AND SC sides)
- [ ] Spec defines panel layout with actual dimensions
- [ ] Spec lists all files that need modification
- [ ] UI mockup fits in actual panel width (~176px for mod slots)

## Phase 1: SuperCollider

### SynthDef Creation
- [ ] Create `supercollider/core/mod_<name>.scd`
- [ ] SynthDef name matches config (`synthdef` key)
- [ ] All parameter names documented (these ARE the OSC contract)
- [ ] Test SynthDef loads without errors in SC

### Boot Sequence
- [ ] Add to `supercollider/init.scd` load list
- [ ] Verify load message appears on SC boot

### Synth Instantiation
- [ ] Add case in `supercollider/core/mod_slots.scd` `~setModGenerator`
- [ ] All params passed with correct names
- [ ] Post message confirms spawn: `"Mod slot X → <Name>"`

### Existing Handlers
- [ ] Check `~setModParam` — does it need special handling?
- [ ] Check `~setModOutputPolarity` — add generator name to condition if using A/B/C/D
- [ ] Check `~setModOutputWave` — if applicable
- [ ] Any other handlers that check generator type?

## Phase 2: Python Config

### config/__init__.py
- [ ] Add to `MOD_GENERATOR_CYCLE`
- [ ] Add time/range constants if needed
- [ ] Add to `MOD_OUTPUT_LABELS`
- [ ] Add `_MOD_GENERATOR_CONFIGS["<Name>"]` with:
  - `internal_id`
  - `synthdef` (must match SC)
  - `custom_params` (key names must match SC)
  - `output_config`
  - `outputs`

### presets/preset_schema.py
- [ ] Create state dataclass if needed
- [ ] Add `to_dict()` and `from_dict()` methods

## Phase 3: Python UI

### theme.py
- [ ] Add accent color: `accent_mod_<name>`
- [ ] Verify slider_style() covers needed orientations

### modulator_slot_builder.py
- [ ] Add output row builder if custom layout needed
- [ ] Check `build_output_row` branching for new `output_config`
- [ ] Verify panel width accommodates all controls
- [ ] Check button detection logic (`is_mode_btn`)
- [ ] Add mode labels if new stepped params

### modulator_slot.py
- [ ] Add signals for new parameter types
- [ ] Add handler methods for new signals
- [ ] Update `_update_style_for_generator` for accent color

### modulator_grid.py
- [ ] Connect new signals from slot to grid

### main_frame.py
- [ ] Connect grid signals to OSC handlers
- [ ] Add OSC handler methods
- [ ] **VERIFY PARAMETER NAMES MATCH SC EXACTLY**

## Phase 4: Integration Testing

### Signal Path Test
- [ ] Select modulator in UI
- [ ] Check SC post window: synth created?
- [ ] Move slider → check Python log: OSC sent?
- [ ] Check SC: parameter received?
- [ ] Check scope: output visible?

### All Controls Test
- [ ] Each slider affects output
- [ ] Each button toggles correctly
- [ ] Polarity inverts output
- [ ] Mode changes behavior

### Visual Test
- [ ] All buttons visible (not 0-width)
- [ ] All sliders usable (not too small)
- [ ] Labels readable
- [ ] Accent color applied

## Phase 5: Final Verification

- [ ] `git diff` — review all changed files
- [ ] No debug prints left in
- [ ] No commented-out code
- [ ] Restart app fresh — still works?
- [ ] Restart SC fresh — still works?

## Common Mistakes to Avoid

| Mistake | Prevention |
|---------|------------|
| Forgot init.scd | Check boot sequence immediately after SynthDef |
| OSC param mismatch | Copy param names from SC to Python, don't retype |
| Missing spawn case | Search mod_slots.scd for existing cases, add new |
| Wrong polarity params | Check condition includes new generator name |
| UGen `==` comparison | Use `<` `>` comparisons for signals |
| Button invisible | Don't use SizePolicy.Ignored + setMinimumWidth(0) |
| Slider style missing | Check slider_style() for both orientations |
| Mode button as slider | Add key to is_mode_btn check |

## Files Modified for a Typical Modulator
```
supercollider/
  init.scd                    # Add to boot sequence
  core/mod_<name>.scd         # NEW: SynthDef
  core/mod_slots.scd          # Add spawn case
  core/mod_osc.scd            # Only if new OSC paths needed

src/
  config/__init__.py          # Generator config, constants
  presets/preset_schema.py    # State dataclass
  gui/theme.py                # Accent color
  gui/modulator_slot.py       # Signals, handlers, style
  gui/modulator_slot_builder.py # UI building
  gui/modulator_grid.py       # Signal connections
  gui/main_frame.py           # OSC handlers
```
