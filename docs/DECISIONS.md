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

---

### [2025-12-11] Full Theme Centralization (Fonts, Colors, Sizes)
**Decision:** All visual styling flows from `src/gui/theme.py`

**FONT_SIZES dict:**
```python
'display': 32,     # Large displays (BPM)
'title': 16,       # Main titles
'section': 12,     # Section headers
'slot_title': 11,  # Generator/effect slot titles
'label': 10,       # Labels
'small': 9,        # Smaller labels
'tiny': 8,         # Button text, values
'micro': 7,        # Smallest (mute/solo buttons)
```

**COLORS dict additions:**
- `background_dark` - deepest background (#0a0a0a)
- `active_bg` - active slot background (#1a2a1a)
- `text_label` - label text (#666)
- `bpm_text` - LED display color (#ff3333)
- `*_hover` variants for button states

**Rationale:**
- Changing a color/font = one place in theme.py
- Enables future skin system
- Consistent visual language across components

**DO NOT:**
- Use hex color literals outside theme.py
- Use numeric font sizes in QFont() calls
- Create inline QSlider stylesheets (use `slider_style()`)

**Files affected:** All `src/gui/*.py` components now import from theme

---

### [2025-12-11] SSOT Validation Tool
**Decision:** `tools/check_ssot.sh` validates single-source-of-truth compliance

**Checks (critical - ❌):**
- Hardcoded fonts in QFont() calls
- Hardcoded hex colors outside theme.py
- Hardcoded font sizes
- Inline slider stylesheets

**Checks (warnings - ⚠️):**
- Hardcoded effect type strings
- Hardcoded widget sizes

**Usage:** Run before commits to catch violations early
```bash
~/repos/noise-engine/tools/check_ssot.sh
```

**Rationale:** Automated enforcement prevents drift back to scattered definitions
**Files affected:** `tools/check_ssot.sh`

---

### [2025-12-11] Per-Generator Custom Parameters
**Decision:** Each generator can define up to 5 custom parameters in a companion JSON file

**File structure:**
```
supercollider/generators/
    pt2399_grainy.scd       # SynthDef code
    pt2399_grainy.json      # Custom params definition
    test_synth.scd
    test_synth.json         # Empty custom_params for generators with no custom params
```

**JSON format:**
```json
{
    "name": "PT2399",
    "synthdef": "pt2399Grainy",
    "custom_params": [
        {
            "key": "delay_time",
            "label": "DLY",
            "tooltip": "Delay Time",
            "default": 0.5,
            "min": 0.01,
            "max": 0.5,
            "curve": "exp",
            "unit": "s",
            "invert": false
        }
    ]
}
```

**UI layout:**
```
┌─────────────────────────────────────────┐
│ GEN 1                        Test Synth │
│  P1    P2    P3    P4    P5  [LP][ENV]  │  ← custom params (greyed if unused)
│   │     │     │     │     │  [CLK]      │
│  FRQ   CUT   RES   ATK   DEC            │  ← standard params (shared)
│   │     │     │     │     │             │
│ 🔊 Audio    🎹 MIDI                     │
└─────────────────────────────────────────┘
```

**Config changes:**
- `GENERATOR_CYCLE` stays in main config (explicit ordering)
- `GENERATORS` dict built dynamically from JSON files
- New functions: `get_generator_custom_params()`, `get_generator_synthdef()`
- OSC path: `/noise/gen/custom/{slot}/{param_index}`

**Rationale:**
- Definition lives with the generator code
- Adding custom params = edit JSON, update SynthDef
- UI adapts automatically per generator
- Standard params still shared across all generators

**DO NOT:**
- Define more than 5 custom params per generator
- Forget to add JSON when creating new generator

**Files affected:**
- `src/config/__init__.py` (JSON loading, new functions)
- `src/gui/generator_slot.py` (custom params row)
- `src/gui/generator_grid.py` (signal forwarding)
- `src/gui/main_frame.py` (OSC routing)
- `supercollider/core/buses.scd` (custom param buses)
- `supercollider/core/osc_handlers.scd` (custom param handlers)
- `supercollider/core/helpers.scd` (pass custom buses to Synth)
- `supercollider/generators/*.scd` (accept custom buses)
- `supercollider/generators/*.json` (new files)

---

### [2025-12-11] pitch_target System
**Decision:** Per-generator JSON config can specify which parameter receives MIDI note pitch
**Rationale:** Different generators have different "pitch" concepts (VCO frequency vs delay time vs sample rate)
**Implementation:**
- `pitch_target: null` or missing → FRQ is pitch param (default)
- `pitch_target: 0-4` → custom param at that index is pitch param
- GUI: FRQ greyed out when overridden, target param shows ♪ indicator
**DO NOT:**
- Hardcode pitch routing in Python
- Assume FRQ always means pitch
**Files affected:**
- `supercollider/generators/*.json` (pitch_target field)
- `src/config/__init__.py` (get_generator_pitch_target function)
- `src/gui/generator_slot.py` (grey out FRQ, show ♪ indicator)

---

### [2025-12-11] Shared Filter Helper
**Decision:** All generators use `~multiFilter` helper for LP/HP/BP filtering
**Rationale:** DRY - filter logic defined once, consistent behavior across generators
**Implementation:**
```supercollider
sig = ~multiFilter.(sig, filterType, cutoff, res);
// filterType: 0=LP, 1=HP, 2=BP
```
**DO NOT:**
- Duplicate filter logic in each SynthDef
- Forget the 4th argument (filterType)
**Files affected:**
- `supercollider/core/helpers.scd` (~multiFilter definition)
- `supercollider/generators/*.scd` (all use ~multiFilter)

---

### [2025-12-11] Generator SynthDef Auto-Loading
**Decision:** init.scd automatically loads all .scd files from generators/ directory
**Rationale:** Adding new generator = drop in files, no manual init.scd editing
**Implementation:**
```supercollider
~generatorFiles = PathName(~generatorPath).files.select({ |f| f.extension == "scd" });
~generatorFiles.do({ |file| file.fullPath.load; });
```
**DO NOT:**
- Manually list generators in init.scd
- Put non-generator .scd files in generators/ directory
**Files affected:**
- `supercollider/init.scd`

---

### [2025-12-11] MIT License
**Decision:** Project uses MIT License (same as Mutable Instruments)
**Rationale:** Permissive, compatible with hardware/synth community norms
**Files affected:**
- `LICENSE`
- `README.md` (license section)
- `docs/index.html` (footer attribution)

---

### [2025-12-12] Envelope Source System (envSource replaces envEnabled)
**Decision:** Generators use `envSource` (0=OFF, 1=CLK, 2=MIDI) instead of binary `envEnabled`
**Rationale:** 
- Supports three distinct modes: drone, clock-triggered, MIDI-triggered
- MIDI mode triggers envelope from external keyboard, ignores internal clock
- Clean separation of trigger sources

**Implementation:**
```supercollider
// SynthDef signature includes:
envSourceBus=0, midiTrigBus=0, slotIndex=0

// Trigger selection:
trig = Select.ar(envSource, [
    DC.ar(0),      // 0: OFF - drone, no triggers
    clockTrig,     // 1: CLK - clock triggers only  
    midiTrig       // 2: MIDI - midi triggers only
]);

// Apply envelope only when envSource > 0
sig = sig * Select.kr(envSource > 0, [1.0, env]) * amp;
```

**DO NOT:**
- Use old `envEnabled` binary toggle in new generators
- Mix clock and MIDI triggers (it's one or the other)
- Forget `midiTrigBus` and `slotIndex` in SynthDef signature

**Files affected:**
- All `supercollider/generators/*.scd`
- `supercollider/core/buses.scd` (envSource bus, midiTrigBus)
- `supercollider/core/helpers.scd` (passes envSourceBus, midiTrigBus, slotIndex)
- `supercollider/core/midi_handler.scd` (triggers midiTrigBus)

---

### [2025-12-12] Sticky Slot Settings (ENV, Clock Rate, MIDI Channel, Filter)
**Decision:** Slot configuration (ENV source, clock rate, MIDI channel, filter type) persists when changing generator type. Settings are reapplied to the new generator, not reset.

**Rationale:** 
- Slot = Eurorack slot with its own trigger/clock patching
- Swapping the module doesn't change the patching
- User expectation: "I set this slot to MIDI channel 3, it stays on channel 3"
- Reduces friction when auditioning different generators

**Behavior:**
```
Gen 1: Additive, ENV=CLK, rate=/4, filter=HP
  ↓ change to FM
Gen 1: FM, ENV=CLK, rate=/4, filter=HP  ← settings preserved
```

**What IS sticky (per-slot):**
- ENV source (OFF/CLK/MIDI)
- Clock rate (/32 to x32)
- MIDI channel (OFF/1-16)
- Filter type (LP/HP/BP)

**What IS NOT sticky (per-generator):**
- Parameter values (FRQ, CUT, RES, ATK, DEC) - reset to generator defaults
- Custom parameters - reset to generator defaults

**DO NOT:**
- Reset ENV/clock/MIDI/filter when changing generator type
- Forget to reapply (emit signals) when generator changes

**Files affected:**
- `src/gui/generator_slot.py` (set_generator_type preserves settings)

---

### [2025-12-12] OSC Port Configuration - Fixed Port with Verification
**Decision:** SC forces port 57120 on startup. Python verifies connection with ping/pong and monitors with heartbeat.

**Architecture:**
```
SC init.scd:
  thisProcess.openUDPPort(57120);  // Force fixed port

Python connect():
  1. Send /noise/ping
  2. Wait for /noise/pong (1 second timeout)
  3. If no response → connection failed
  4. If response → start heartbeat monitoring

Heartbeat (every 2 seconds):
  1. Python sends /noise/heartbeat
  2. SC responds with /noise/heartbeat_ack
  3. If 3 missed responses → CONNECTION LOST signal
  4. UI shows prominent warning, one-click reconnect
```

**Connection states:**
- **Connected** - Green "● Connected", heartbeat active
- **Connection Failed** - Red warning on initial connect attempt
- **CONNECTION LOST** - Prominent red warning, "⚠ RECONNECT" button
- **Disconnected** - Gray, manual disconnect by user

**Files affected:**
- `supercollider/init.scd` - Forces port 57120
- `supercollider/core/osc_handlers.scd` - Ping/pong and heartbeat handlers
- `src/audio/osc_bridge.py` - Connection verification and heartbeat
- `src/gui/main_frame.py` - Connection lost/restored UI handling

---

### [2025-12-12] Shared Helper Functions for Generators (~envVCA, ~multiFilter, ~stereoSpread)
**Decision:** All generators use shared helper functions for common signal processing

**Helpers defined in `supercollider/core/helpers.scd`:**
```supercollider
~multiFilter.(sig, filterType, filterFreq, rq)  // LP/HP/BP filter
~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex)  // Envelope + VCA
~stereoSpread.(sig, rate, width)  // Subtle stereo movement
```

**Standard generator structure:**
```supercollider
SynthDef(\genName, { |out, freqBus, cutoffBus, ...|
    var sig, freq, ...;
    
    // Read params from buses
    freq = In.kr(freqBus);
    // ...
    
    // === SOUND SOURCE === (unique per generator)
    sig = ...;
    
    // === PROCESSING CHAIN === (standardized)
    sig = ~stereoSpread.(sig, 0.2, 0.3);  // optional
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;
```

**Benefits:**
- Single source of truth for envelope logic (bug fix = 1 file, not 22)
- 50% code reduction (2853 → 1440 lines across generators)
- Consistent behavior across all generators
- Easier to add new generators

**DO NOT:**
- Duplicate envelope/filter code inline in generators
- Use `~clockRates.size` inside helpers (hardcode 13 for clock rates, 8 for MIDI channels)
- Forget to pass all required arguments to helpers

**Files affected:**
- `supercollider/core/helpers.scd` (helper definitions)
- `supercollider/generators/*.scd` (all 22 generators use helpers)

---

### [2025-12-12] MIDI Retrig Mode for Struck/Plucked Generators
**Decision:** Generators with internal retrigger (modal, karplus) use continuous triggering in MIDI mode

**Problem:** 
Modal and Karplus-Strong have internal `Impulse.ar(retrigRate)` for self-triggering. When playing via MIDI keyboard, the VCA opens but the exciter fires on its own schedule, causing laggy/unresponsive feel.

**Solution:**
- Add `"midi_retrig": true` flag to generator JSON config
- In MIDI mode (envSource=2), generators use MIDI trigger bus instead of internal retrigger
- SC sends continuous 30Hz triggers while key is held (via `midiRetrigContinuous` synth)
- RTG knob is greyed out in MIDI mode (not applicable)
- Drone/CLK modes unchanged - still use internal retrig rate

**Architecture:**
```
Generator JSON:
  "midi_retrig": true  // Flag for modal, karplus

Python:
  on_generator_changed → send /noise/gen/midiRetrig [slot, 1/0]
  env_source_changed → grey out RTG if midi_retrig && envSource==MIDI

SC midi_handler.scd:
  ~genMidiRetrig[slot] = true/false
  Note on + midi_retrig → start midiRetrigContinuous synth (30Hz triggers)
  Note off → free midiRetrigContinuous synth

Generator SynthDef:
  exciterTrig = Select.ar(envSource > 1, [
      Impulse.ar(retrigRate),  // Internal (OFF/CLK)
      midiTrig                  // External (MIDI)
  ]);
```

**Files affected:**
- `supercollider/generators/modal.json` - add midi_retrig flag
- `supercollider/generators/karplus_strong.json` - add midi_retrig flag
- `supercollider/generators/modal.scd` - use midiTrig for exciter in MIDI mode
- `supercollider/generators/karplus_strong.scd` - use midiTrig for exciter in MIDI mode
- `supercollider/core/midi_handler.scd` - handle midi_retrig, continuous trigger synth
- `src/config/__init__.py` - add get_generator_midi_retrig(), OSC path
- `src/gui/generator_slot.py` - grey out RTG in MIDI mode
- `src/gui/main_frame.py` - send midi_retrig flag on generator change

---

### [2025-12-13] Central Logging System with In-App Console
**Decision:** Replace all print statements with centralized logging via `src/utils/logger.py`, viewable in slide-out console panel.

**Architecture:**
```
src/utils/logger.py:
  - NoiseEngineLogger class wrapping Python logging
  - QtSignalHandler emits to PyQt signal (thread-safe)
  - Component tagging for filtering (OSC, MIDI, GEN, APP, UI, CONFIG)
  - Console + GUI handlers with separate log levels

src/gui/console_panel.py:
  - Slide-out panel from right edge
  - Toggle: button (>_) or Ctrl+`
  - Color-coded levels, auto-scroll, max 500 lines
  - Filter dropdown, clear/copy buttons
```

**Usage:**
```python
from src.utils.logger import logger

logger.info("Message", component="OSC")
logger.debug("Detail", component="GEN", details="extra info")
logger.warning("Caution", component="MIDI")
logger.error("Failed", component="APP")

# Convenience
logger.osc("OSC specific")
logger.gen(slot_id, "Generator action")
```

**Benefits:**
- Thread-safe GUI updates via Qt signals
- Centralized control of log levels
- Visible history for debugging
- No more lost print output

**DO NOT:**
- Use print() anywhere in production code
- Log sensitive information
- Emit signals from non-GUI threads directly (use logger)

**Files affected:**
- `src/utils/logger.py` (new)
- `src/utils/__init__.py` (new)
- `src/gui/console_panel.py` (new)
- `src/gui/main_frame.py` (console integration)
- `src/audio/osc_bridge.py` (converted to logger)
- `src/config/__init__.py` (converted to logger)
- `src/gui/midi_selector.py` (converted to logger)
- `src/main.py` (converted to logger)

---

### [2025-12-13] Generator Slot UI/Logic Split
**Decision:** Split `generator_slot.py` (562 lines) into two files for separation of concerns.

**Files:**
- `generator_slot.py` (332 lines) - Class definition, signals, state management, event handlers
- `generator_slot_builder.py` (273 lines) - UI construction functions

**Architecture:**
```python
# generator_slot.py
from .generator_slot_builder import build_slot_ui

class GeneratorSlot(QWidget):
    def __init__(self, ...):
        build_slot_ui(self)  # Delegate UI construction
```

**Rationale:**
- Follows BLUEPRINT.md: widgets emit signals, components do layout
- Builder is pure layout construction
- Main file is state/signals/handlers
- Public interface unchanged

**DO NOT:**
- Mix UI construction back into the main class
- Add state management to the builder

**Files affected:**
- `src/gui/generator_slot.py` (refactored)
- `src/gui/generator_slot_builder.py` (new)

---

### [2025-12-13] Master Section with Integrated Metering
**Decision:** Master section is a separate component with fader and level meters. Metering is integrated into the masterPassthrough synth, not a separate synth.

**Architecture:**
```
masterPassthrough synth:
  - Reads from ~masterBus
  - Applies fidelity effect
  - Applies master volume
  - Sends level data via SendReply at 24fps
  - Outputs to hardware

Python:
  - MasterSection widget in right panel (below mixer)
  - LevelMeter with peak hold and clip detection
  - OSC levels_received signal for thread-safe updates
```

**Rationale:**
- Integrated metering avoids DC offset issues from reading hardware output
- Single synth is simpler than separate meter synth
- 24fps metering is responsive without excessive CPU

**DO NOT:**
- Create separate metering synth that reads from hardware output (causes DC)
- Put master fader in mixer panel (it's now in master_section)

**Files affected:**
- `src/gui/master_section.py` (new)
- `src/gui/mixer_panel.py` (master fader removed)
- `supercollider/effects/master_passthrough.scd` (metering added)
- `supercollider/core/master.scd` (volume OSC handler)
- `src/audio/osc_bridge.py` (levels_received signal)

---

### [2025-12-13] Channel Strips - Per-Generator Routing

**Decision:** Each generator routes through its own channel strip before the master bus

**Architecture:**
```
Generator 1 → ~genBus[0] → channelStrip (vol/mute/solo) ─┐
Generator 2 → ~genBus[1] → channelStrip (vol/mute/solo) ─┤
...                                                       ├→ ~masterBus → masterPassthrough → Output
Generator 8 → ~genBus[7] → channelStrip (vol/mute/solo) ─┘
```

**Signal Flow:**
- 8 stereo `~genBus` buses (one per generator slot)
- `~stripGroup` runs after `~genGroup`, before `~fxGroup`
- Node order: `~clockGroup → ~genGroup → ~stripGroup → ~fxGroup`

**Channel Strip Features:**
- Volume (default 0.8)
- Mute (applied first)
- Solo-in-place (only soloed channels pass when any solo active)
- State persists across generator changes

**Solo Logic:**
- `~soloCount` tracks number of active solos
- `~soloActive` control bus (1 if any solo, 0 if none)
- When `soloActive=1`, only channels with `solo=1` pass audio
- Mute is applied before solo check

**State Persistence:**
- `~stripMuteState[8]` and `~stripSoloState[8]` track per-slot state
- When generator changes, new channel strip inherits stored state
- Python mixer buttons keep visual state across generator changes

**OSC Paths:**
- `/noise/gen/volume [slot, 0-1]`
- `/noise/gen/mute [slot, 0/1]`
- `/noise/gen/solo [slot, 0/1]`

**Known Issue - OSCdef Timing:**
Channel strip OSCdefs must be re-registered after `s.sync` in init.scd.
The inline re-registration at the end of init.scd is a workaround for a
SuperCollider timing issue where OSCdefs registered during file load
don't respond until manually reloaded.

**DO NOT:**
- Route generators directly to `~masterBus` (breaks channel strip routing)
- Reset mute/solo state on generator change (state should persist)
- Remove the inline OSCdef re-registration in init.scd (breaks mute/solo)

**Files affected:**
- `supercollider/core/buses.scd` (~genBus, ~soloActive, ~stripGroup, etc.)
- `supercollider/core/channel_strips.scd` (new - SynthDef and helpers)
- `supercollider/core/clock.scd` (~stripGroup creation)
- `supercollider/core/helpers.scd` (routes to ~genBus, manages strips)
- `supercollider/core/osc_handlers.scd` (volume/mute/solo handlers)
- `supercollider/init.scd` (loads channel_strips, inline OSCdef fix)
- `src/config/__init__.py` (OSC paths)
- `src/gui/mixer_panel.py` (enabled, state persistence)
- `src/gui/main_frame.py` (wired signals, channel active state)
