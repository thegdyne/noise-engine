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

---

### [2025-12-10] DRY Code and Standard Interfaces
**Decision:** Keep code DRY (Don't Repeat Yourself) - use functions to assign common values wherever possible
**Rationale:** 
- Reduces duplication and maintenance burden
- Makes adding new generators/effects easier
- Single point of change for shared behavior
- Clearer code structure

**Examples:**
- SuperCollider: `~startGenerator` function handles starting any generator with standard params
- All generators share same interface: `freqBus, cutoffBus, resBus, attackBus, decayBus, filterTypeBus`
- New generators just implement the interface, don't repeat bus wiring

**DO NOT:**
- Copy/paste parameter wiring for each generator type
- Hardcode bus assignments in multiple places
- Create one-off handlers when a shared function works

**Standard Generator Interface (SuperCollider):**
```
Arguments: out, freqBus, cutoffBus, resBus, attackBus, decayBus, filterTypeBus
- freqBus: frequency/pitch (0-1 normalized)
- cutoffBus: filter cutoff (0-1 normalized)  
- resBus: filter resonance (0-1 normalized)
- attackBus: VCA attack time (0-1 normalized)
- decayBus: VCA decay time (0-1 normalized)
- filterTypeBus: 0=LP, 1=HP, 2=BP
```

**Files affected:** `supercollider/init.scd`, all generator SynthDefs

---

### [2025-12-10] Per-Generator Parameters
**Decision:** Each generator slot has 5 sliders + 3 buttons
**Parameters:** FRQ, CUT, RES, ATK, DEC
**Buttons:** Filter type (LP/HP/BP), ENV toggle, CLK rate
**Rationale:** Independent control per generator, consistent interface

### [2025-12-10] ENV Toggle Behavior  
**Decision:** ENV OFF = drone (VCA always open), ENV ON = triggered envelope
**Rationale:** Simple mental model - off means continuous, on means rhythmic

### [2025-12-10] Generator Files Separated
**Decision:** Each generator in its own file: `supercollider/generators/*.scd`
**Rationale:** Edit one generator without touching init.scd, easy rollback, low-impact changes

### [2025-12-10] Standard Generator Interface
**Arguments:** out, freqBus, cutoffBus, resBus, attackBus, decayBus, filterTypeBus, envEnabledBus, clockDivBus
**Rationale:** Any generator can be started with ~startGenerator helper, consistent wiring

### [2025-12-10] Filter Range
**Decision:** Cutoff range 80Hz - 16kHz for all generators
**Rationale:** Full usable sweep from nearly closed to fully open

---

### [2025-12-10] SuperCollider Modular Structure
**Decision:** Split SuperCollider code into separate files by function
**Structure:**
```
supercollider/
├── init.scd                    # Loader only
├── core/
│   ├── buses.scd               # ~setupBuses
│   ├── clock.scd               # ~setupClock, ~startClock
│   ├── helpers.scd             # ~startGenerator, ~stopGenerator
│   └── osc_handlers.scd        # ~setupOSC
├── generators/
│   ├── test_synth.scd          # Standalone SynthDef
│   └── pt2399_grainy.scd       # Standalone SynthDef
└── effects/
    └── master_passthrough.scd  # ~setupMasterPassthrough, ~startMasterPassthrough
```
**Rationale:**
- Each file has one purpose
- Edit generators without touching core
- Easy rollback per component
- Clear load order dependencies
- Works well with Claude session workflow

### [2025-12-10] Master Clock System
**Decision:** Central clock with divisions for envelope sync
**Implementation:**
- masterClock synth generates BPM-based triggers
- PulseDivider.ar for clean divisions (CLK, /2, /4, /8, /16)
- ENV OFF = drone or free-running (FRQ rate)
- ENV ON = synced to master clock division
**Rationale:** Musical timing, polyrhythmic possibilities

---

### [2025-12-10] Vertical Sliders Only
**Decision:** All sliders in the UI must be vertical, no horizontal sliders
**Rationale:** Consistent visual language, matches hardware mixer/synth paradigm
**Applies to:** All components - modulation panel, mixer, effects, LFOs, generators

---

### [2025-12-10] Reusable Widget Pattern
**Decision:** Separate UI behavior from business logic
**Location:** `src/gui/widgets.py`
**Widgets:**
- `MiniSlider` - compact vertical slider
- `CycleButton` - click/scroll to cycle through values

**Rationale:**
- DRY: widgets reusable across components
- Separation: UI behavior vs application logic
- Single responsibility: each widget does one thing
- Testable: widgets can be tested in isolation

**Rule:** When adding UI behavior (scroll, cycle, drag), create a widget first, then use it.

---

### [2025-12-10] Centralized Configuration
**Decision:** All constants, mappings, and magic numbers in `src/config/__init__.py`
**Location:** `src/config/__init__.py`

**Contains:**
- Clock rates and mappings (CLOCK_RATES, CLOCK_RATE_INDEX)
- Filter types and mappings (FILTER_TYPES, FILTER_TYPE_INDEX)
- BPM limits (BPM_DEFAULT, BPM_MIN, BPM_MAX)
- Generator registry (GENERATORS, GENERATOR_CYCLE)
- OSC settings (OSC_HOST, OSC_PATHS, etc.)
- Widget sizes (SIZES dict)

**Rationale:**
- Single source of truth
- Adding a generator = one line change
- Changing OSC paths = one place
- Widget sizes consistent across components

**Rule:** If it's a constant, mapping, or magic number, it belongs in config.

---

### [2025-12-11] Font Centralization in Theme
**Decision:** All fonts defined in `src/gui/theme.py`, not scattered in components
**Implementation:**
```python
FONT_FAMILY = 'Helvetica'
MONO_FONT = 'Menlo'  # or 'Courier New' on non-Mac
FONT_SIZES = {
    'title': 16,    # Main titles (NOISE ENGINE)
    'section': 12,  # Section headers (MIXER, EFFECTS)
    'label': 10,    # Labels
    'small': 9,     # Smaller labels
    'tiny': 8,      # Button text, values
}
```
**Rationale:** Single source of truth for typography, easy to change globally
**DO NOT:** Hardcode font names or sizes in component files
**Files affected:** `src/gui/theme.py`, all component files updated to import from theme

---

### [2025-12-11] UI Layout Reorganization
**Decision:** New layout arrangement for main window
**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  TOP BAR (BPM, Connect, Preset)                        │
├──────────┬─────────────────────────────────┬───────────┤
│          │                                 │           │
│   MOD    │      GENERATORS (2x4)           │   MIXER   │
│ SOURCES  │                                 │           │
│  (LFOs)  │                                 │           │
│          │                                 │           │
├──────────┴─────────────────────────────────┴───────────┤
│  EFFECTS CHAIN                                         │
└────────────────────────────────────────────────────────┘
```
**Rationale:** 
- MOD SOURCES on left (fixed 220px) - modulation is input/control
- GENERATORS in center - main focus, most screen space
- MIXER on right - output stage
- EFFECTS at bottom - final processing before output

**DO NOT:** Move modulation back to bottom, put mixer in center
**Files affected:** `src/gui/main_frame.py`, `src/gui/modulation_sources.py`

---

### [2025-12-11] Effects Chain Compact Design
**Decision:** Effect slots are compact vertical cards (70px wide)
**Layout per slot:**
```
┌────────┐
│  Name  │  ← Click to change type
│  ░░░░  │  ← Vertical slider
│  75%   │  ← Value display
└────────┘
```
**Rationale:** Matches generator slider style, compact, clear hierarchy
**DO NOT:** Use horizontal sliders, put slider outside the card boundary
**Files affected:** `src/gui/effects_chain.py`

---

### [2025-12-11] GitHub Pages Documentation Site
**Decision:** Project landing page hosted via GitHub Pages at `/docs/index.html`
**Contains:** Features, architecture, future plans, milestones, skin previews
**Rationale:** Public-facing project overview, shareable, always current
**DO NOT:** Put sensitive/internal info on public page
**Files affected:** `docs/index.html`

---

### [2025-12-11] Milestone Update Tool
**Decision:** Shell script to add dated milestones to landing page
**Usage:** `./tools/add_milestone.sh "Description of milestone"`
**Rationale:** Quick way to log progress without manual HTML editing
**DO NOT:** Use for every commit - only significant features/milestones
**Files affected:** `tools/add_milestone.sh`, `docs/index.html`

---

### [2025-12-11] Mockups Directory for Skin Concepts
**Decision:** Static HTML/CSS mockups stored in `docs/mockups/`
**Purpose:** Design reference only, not production code
**Rationale:** Visualize skin ideas before implementing in PyQt
**DO NOT:** Use mockup code directly - real skins will use centralized theme
**Files affected:** `docs/mockups/`, `docs/mockups/README.md`

---

### [2025-12-11] Config-Driven Generator Parameters (Single Source of Truth)
**Decision:** All generator parameters defined once in `GENERATOR_PARAMS` list in `src/config/__init__.py`
**Parameter Definition:**
```python
{
    'key': 'cutoff',      # Internal name
    'label': 'CUT',       # UI display
    'tooltip': 'Filter Cutoff',
    'default': 0.5,       # Normalized default (0-1)
    'min': 80.0,          # Real minimum value
    'max': 16000.0,       # Real maximum value  
    'curve': 'exp',       # 'lin' or 'exp' mapping
    'unit': 'Hz',         # Display unit
    'invert': False,      # High slider = low value?
}
```
**Value Flow:**
1. User moves slider (0-1000 internal range)
2. Python normalizes to 0-1
3. `map_value()` converts to real value using config (curve, range, invert)
4. Real value sent over OSC
5. SuperCollider receives and uses directly (no mapping in SynthDefs)

**Rationale:** 
- Adding a parameter = one dict entry in config
- UI labels, tooltips, ranges, curves all in one place
- SynthDefs become simpler (no linexp/linlin)
- Display formatting centralized in `format_value()`

**DO NOT:** 
- Hardcode parameter lists in UI components
- Do value mapping in SuperCollider SynthDefs
- Add parameters without updating GENERATOR_PARAMS

**Files affected:** 
- `src/config/__init__.py` (GENERATOR_PARAMS, map_value, format_value)
- `src/gui/widgets.py` (MiniSlider accepts param_config)
- `src/gui/generator_slot.py` (builds sliders from config)
- `supercollider/generators/*.scd` (receive real values)
- `supercollider/core/buses.scd` (default values are real)

---

### [2025-12-11] ValuePopup Widget for Live Parameter Display
**Decision:** Floating popup shows real value during slider drag
**Behavior:**
- Appears when drag starts
- Follows slider handle position  
- Shows formatted value with unit (e.g., "1.1kHz", "22ms")
- Disappears on drag release

**Rationale:** Performance instrument needs value feedback without cluttering static UI
**DO NOT:** Show popup when not actively dragging
**Files affected:** `src/gui/widgets.py` (ValuePopup class, DragSlider integration)
