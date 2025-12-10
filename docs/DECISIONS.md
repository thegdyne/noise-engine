# Noise Engine - Decision Log

**Purpose:** Track all major design decisions to prevent regressions and maintain consistency.

---

## Format
```
### [Date] Decision Title
**Decision:** What we decided
**Rationale:** Why we decided this
**DO NOT:** Things to avoid/not change
**Files affected:** Where this is implemented
```

---

### [2025-12-10] Component-Based Modular Architecture
**Decision:** Each UI section is a self-contained, independent component  
**Rationale:** Like Eurorack - modules can be rearranged without breaking functionality  
**DO NOT:** Create dependencies between components, hardcode layout positions  
**Files affected:** All files in `src/gui/`

---

### [2025-12-10] Frame Layout Proportions
**Decision:** Left 25% (Modulation) | Center 60% (Generators) | Right 15% (Mixer)  
**Rationale:** Balances visibility - generators are the focus, modulation has space, mixer is compact  
**DO NOT:** Change these proportions without updating PROJECT_STRATEGY.md  
**Files affected:** `src/gui/main_frame.py`

---

### [2025-12-10] All Faders Vertical (Except Sequencer)
**Decision:** All sliders/faders are vertical orientation  
**Rationale:** Consistent with hardware mixers, better use of screen space, muscle memory  
**DO NOT:** Create horizontal sliders outside of sequencer  
**Files affected:** `src/gui/modulation_panel.py`, `src/gui/mixer_panel.py`

---

### [2025-12-10] Config-Based Routing
**Decision:** Routing defined in YAML/JSON config files, not in UI  
**Rationale:** Clean UI, flexible setups, version controllable, shareable presets  
**DO NOT:** Build visual patching UI, hardcode routing in Python  
**Files affected:** Future `config/routing.yaml`

---

### [2025-12-10] PyQt5 Slider Ghosting Fix
**Decision:** Apply custom stylesheet + repaint() on sliderReleased for all QSliders  
**Rationale:** macOS has visual artifacts with default QSlider styling  
**DO NOT:** Remove this fix or use default QSlider styling  
**Files affected:** All files with QSlider widgets

---

### [2025-12-10] High-Resolution Performance Sliders
**Decision:** Sliders use 10000 steps (not 1000) for smooth, expressive control  
**Rationale:** Performance instrument needs precision without stepping/jumping  
**Features:**
- 10000 steps (0-10000 range)
- Shift+drag = 10x fine control
- Mouse wheel = micro adjustments
- Display as percentage (0-100%)

**DO NOT:** 
- Reduce slider resolution below 10000
- Remove fine control mode
- Change to decimal display instead of percentage

**Files affected:** `src/gui/modulation_panel.py` (PerformanceSlider class)

---

### [2025-12-10] Generator Control via Python
**Decision:** Python GUI controls all generator start/stop via OSC  
**Rationale:** Keeps GUI and audio state synchronized  
**DO NOT:** Auto-start generators in SuperCollider init.scd  
**Files affected:** `supercollider/init.scd`, `src/gui/main_frame.py`

---

### [2025-12-10] Multi-Generator System
**Decision:** 8 generator slots, each can run different generator type independently  
**Rationale:** Allows layering, experimentation, complex patches  
**DO NOT:** Limit to single generator, force all generators to be same type  
**Files affected:** `supercollider/init.scd`, `src/gui/generator_grid.py`

---

### [2025-12-10] Everything Visible - No Menu Diving
**Decision:** All controls visible on main screen, no tabs/hidden menus  
**Rationale:** Hardware synth philosophy - what you see is what you control  
**DO NOT:** Add tabs, modal dialogs, hidden sub-menus for basic functions  
**Files affected:** `src/gui/main_frame.py`

---

## Adding New Decisions

When making significant design choices, add them here with:
1. Date
2. Clear decision statement
3. Why we chose this
4. What to avoid
5. Which files implement it

Update this file via git commit whenever decisions are made.

---

### [2025-12-10] Master Bus Architecture with Effects Chain
**Decision:** All generators route through internal audio bus before output, with master effects processing
**Architecture:**
```
Generators → Internal Bus (~masterBus) → [Master Passthrough + Effects] → Output
```
**Rationale:** 
- Allows global effects processing on all generators uniformly
- Clean separation between generation and output processing
- Always-on passthrough ensures audio flows even without effects active
- Effect slots modulate the passthrough synth parameters

**DO NOT:** 
- Route generators directly to hardware output (bypass master bus)
- Require effects to be "on" for audio to pass through
- Create per-generator effect chains (use master chain)

**Files affected:** `supercollider/init.scd`, `src/gui/effects_chain.py`, `src/gui/effect_slot.py`, `src/gui/main_frame.py`

---

### [2025-12-10] Fidelity Effect as Master Effect
**Decision:** Fidelity is a master effect applied to all generators uniformly
**Parameters:**
- Bit crushing (16-bit → 4-bit)
- Sample rate reduction (44.1kHz → 4kHz) 
- Bandwidth limiting (18kHz → 2kHz)
- Amount: 100% = clean/transparent, 0% = maximum degradation

**Rationale:** Global aesthetic control - affects entire output, not individual generators
**DO NOT:** Make fidelity per-generator (it's a master effect)
**Files affected:** `supercollider/init.scd` (masterPassthrough SynthDef)

---

### [2025-12-10] Effects Chain UI in Bottom Section
**Decision:** Effects chain occupies bottom section (replaced sequencer placeholder)
**Rationale:** Effects are more immediately useful than sequencer for early development
**Layout:** 4 horizontal effect slots with vertical amount faders
**DO NOT:** Move sequencer back to bottom until effects chain is complete
**Files affected:** `src/gui/main_frame.py`, `src/gui/effects_chain.py`, `src/gui/effect_slot.py`

---

### [2025-12-10] Start with Empty Generators
**Decision:** Application starts with all generator slots empty (no auto-loaded generators)
**Rationale:** 
- Prevents confusion (GUI showing generator that isn't actually running)
- Clear cause-effect (click slot → generator starts → hear sound)
- User explicitly chooses first generator

**DO NOT:** Auto-load generators on startup
**Files affected:** `src/main.py` (removed set_pt2399_generator call)
