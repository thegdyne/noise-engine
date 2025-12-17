# Pin Matrix - Comprehensive Design

**Status:** Design  
**Created:** December 17, 2025  
**Updated:** December 17, 2025 - Quadrature expansion as prerequisite

---

## Vision

A dedicated second-screen modulation routing matrix that feels like a proper hardware pin matrix / patch bay. Professional, immediate, visual. The kind of thing you'd put on a second monitor and leave open during a session.

**NOT** a cramped dialog box. **NOT** a menu system. A proper instrument panel.

---

## Architecture: 16 Mod Buses

The matrix is built around **16 mod buses** from 4 slots × 4 outputs.

### Flexible Slot System

**Any mod generator type can occupy any slot.** The default arrangement is:

| Slot | Default Type | Outputs | Buses |
|------|--------------|---------|-------|
| MOD 1 | LFO | A, B, C, D | 0-3 |
| MOD 2 | Sloth | X, Y, Z, R | 4-7 |
| MOD 3 | LFO | A, B, C, D | 8-11 |
| MOD 4 | Sloth | X, Y, Z, R | 12-15 |

But you could have 4× LFO, 4× Sloth, or any combination. Future generator types (Env Follower, S&H, etc.) will also be selectable per-slot.

**Current status:** Type selection UI not yet implemented. Slots currently fixed to default types. This is a known gap.

### Generator Types

Each type outputs to 4 buses with different characteristics:

**LFO** - Classic quadrature arrangement (Buchla, Serge style)
- A = 0° (In-phase)
- B = 90° (Quadrature)  
- C = 180° (Inverted)
- D = 270° (Inverted Quadrature)

**Sloth** - Triple Sloth inspired chaos
- X = Torpor (15-30s cycles)
- Y = Apathy (60-90s cycles)
- Z = Inertia inverted (30-40min cycles)
- R = Rectified sum - gate-like bursts when slow outputs overcome fast

### Matrix Row Labels

Row labels are **dynamic**, derived from the generator type currently loaded in each slot:

```
Slot 1 = LFO    → rows labeled "LFO 1 A", "LFO 1 B", "LFO 1 C", "LFO 1 D"
Slot 2 = Sloth  → rows labeled "SLTH 2 X", "SLTH 2 Y", "SLTH 2 Z", "SLTH 2 R"
Slot 3 = LFO    → rows labeled "LFO 3 A", "LFO 3 B", "LFO 3 C", "LFO 3 D"
Slot 4 = LFO    → rows labeled "LFO 4 A", "LFO 4 B", "LFO 4 C", "LFO 4 D"  ← if user loads LFO here
```

The matrix listens for slot type changes and updates row headers accordingly.

---

## Reality Check: Prerequisites

Before the matrix can work, several things need doing:

### 1. Quadrature Expansion (3→4 outputs)

| Component | Current | Target |
|-----------|---------|--------|
| `MOD_OUTPUTS_PER_SLOT` | 3 | 4 |
| `MOD_BUS_COUNT` | 12 | 16 |
| LFO SynthDef outputs | A, B, C | A, B, C, D |
| Sloth SynthDef outputs | X, Y, Z | X, Y, Z, R |
| Scope traces | 3 | 4 |
| UI output rows | 3 | 4 |

See: `docs/FEATURE_LFO_QUADRATURE.md` for full spec.

### 2. Mod Sources Actually Working

| Component | Status | Gap |
|-----------|--------|-----|
| Python UI | ✅ Exists | Sends OSC to void |
| SC mod buses | ⚠️ Allocated | Only 12, need 16 |
| SC LFO SynthDef | ⚠️ Written | Only 3 outputs |
| SC Sloth SynthDef | ⚠️ Written | Only 3 outputs |
| SC OSC handlers | ❌ Missing | ~40 lines needed |
| SC mod slot management | ❌ Missing | Start/stop logic |

### 3. Type Selection Per Slot

| Component | Status | Gap |
|-----------|--------|-----|
| Type selector UI | ❌ Missing | Currently hardcoded defaults |
| Generator cycle | ⚠️ Partial | Config exists but no UI to change |
| Dynamic row labels | ❌ Missing | Matrix needs to read slot types |

**Note:** Type selection is not blocking for initial matrix development. We can build against the default LFO/Sloth/LFO/Sloth arrangement, then add type switching later. The architecture supports any combination.

---

## Phased Rollout

### Phase 0: Quadrature Expansion

**Goal:** Expand mod sources from 3 to 4 outputs per slot. 16 total mod buses.

**Deliverables:**

1. **Config updates:**
```python
MOD_OUTPUTS_PER_SLOT = 4
MOD_BUS_COUNT = 16
MOD_LFO_OUTPUTS = ["A", "B", "C", "D"]
MOD_SLOTH_OUTPUTS = ["X", "Y", "Z", "R"]
MOD_LFO_PHASE_PATTERNS = {
    "QUAD": [0, 90, 180, 270],
    "PAIR": [0, 0, 180, 180],
    "SPREAD": [0, 45, 180, 225],
    "TIGHT": [0, 22, 45, 67],
    "WIDE": [0, 120, 180, 300],
    "SYNC": [0, 0, 0, 0],
}
```

2. **LFO SynthDef:** 4 output buses, pattern presets, rotate parameter
3. **Sloth SynthDef:** 4 outputs including rectified sum (R)
4. **UI:** 4 output rows, PAT button, ROT control, 4-trace scope
5. **SC bus allocation:** 16 control buses for mod outputs

**Success criteria:** LFO shows 4 traces in scope at 0°/90°/180°/270°. Sloth R output pulses irregularly.

**Estimated effort:** 1-2 sessions

---

### Phase 1: Wire Mod Sources (Foundation)

**Goal:** Mod sources output real CV to buses. Scopes show real waveforms.

**Deliverables:**
1. `supercollider/core/mod_osc.scd` - OSC handlers for mod messages
2. `supercollider/core/mod_slots.scd` - `~startModSlot`, `~freeModSlot` functions
3. Scope receives real bus values (not simulated)
4. Verify: change LFO rate → scope changes

**Success criteria:** Move a slider in Python → see it in SC post window → see waveform change in scope.

**Estimated effort:** 1 session

---

### Phase 2: Mod Bus → Generator Param (Hardcoded Test)

**Goal:** Prove modulation works end-to-end before building UI.

**Deliverables:**
1. SC helper: `~applyModulation.(targetBus, modBusIndex, depth)`
2. Hardcode test: LFO bus 0 → Gen 1 cutoff at 50% depth
3. Hear the modulation (filter sweep synced to clock)

**Success criteria:** Load a generator, hear cutoff being modulated by LFO without touching any routing UI.

**Estimated effort:** 1 session

---

### Phase 3: Connection Data Model

**Goal:** Define how connections are stored, transmitted, saved.

**Deliverables:**
1. Connection schema in Python:
```python
@dataclass
class ModConnection:
    source_bus: int      # 0-15 (mod bus index)
    target_slot: int     # 1-8 (generator slot)
    target_param: str    # 'cutoff', 'frequency', 'custom_0', etc.
    depth: float         # -1.0 to +1.0
    enabled: bool        # Can disable without deleting
```

2. `ModRoutingState` class - holds all connections, emits change signals
3. OSC message design:
   - `/noise/mod/route/add [source_bus, slot, param, depth]`
   - `/noise/mod/route/remove [source_bus, slot, param]`
   - `/noise/mod/route/depth [source_bus, slot, param, depth]`
   - `/noise/mod/route/enable [source_bus, slot, param, 0/1]`

4. SC-side connection storage: `~modRouting` dictionary
5. Preset JSON schema for connections

**Success criteria:** Can programmatically add/remove connections, SC responds, state survives reconnect.

**Estimated effort:** 1-2 sessions

---

### Phase 4: Matrix Window - Basic Grid

**Goal:** Visual matrix appears, shows connection state, click to toggle.

**Deliverables:**
1. `src/gui/mod_matrix_window.py` - QMainWindow (not dialog)
2. Grid layout:
   - Rows: 16 mod buses (grouped by slot, 4 per slot)
   - Columns: 8 generators × params (FRQ CUT RES ATK DEC + customs)
3. Cell widget: clickable, shows filled/empty state
4. **Dynamic row headers:** Read generator type from each slot, label accordingly
   - Slot with LFO → "LFO n A/B/C/D"
   - Slot with Sloth → "SLTH n X/Y/Z/R"
   - Row colours match source type
5. Column headers: "G1 FRQ", "G1 CUT", etc.
6. Click cell → toggle connection (default 50% depth)
7. Open via Cmd+M or menu
8. Listen for slot type changes → update row headers

**Layout (example with default LFO/Sloth/LFO/Sloth):**
```
┌────────────────────────────────────────────────────────────────────────────┐
│  MOD MATRIX                                                    [×]         │
├──────────┬─────────────────────┬─────────────────────┬─────────────────────┤
│          │ GEN 1               │ GEN 2               │ GEN 3          ...  │
│          │ F  C  R  A  D  P1-5 │ F  C  R  A  D  P1-5 │ F  C  R  A  D       │
├──────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ LFO 1 A  │ ●     ○             │    ●                │                     │  ← cyan
│ LFO 1 B  │    ○                │       ○             │                     │
│ LFO 1 C  │                     │          ●          │                     │
│ LFO 1 D  │       ●             │                     │                     │
├──────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ SLTH 2 X │       ●             │ ●                   │                     │  ← orange
│ SLTH 2 Y │                     │                     │    ○                │
│ SLTH 2 Z │                     │       ●             │                     │
│ SLTH 2 R │ ○                   │                     │                     │
├──────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ LFO 3 A  │                     │                     │                     │  ← cyan
│ LFO 3 B  │                     │    ●                │                     │
│ LFO 3 C  │                     │                     │                     │
│ LFO 3 D  │                     │                     │ ●                   │
├──────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│ SLTH 4 X │                     │                     │                     │  ← orange
│ SLTH 4 Y │ ●                   │                     │                     │
│ SLTH 4 Z │                     │                     │                     │
│ SLTH 4 R │                     │ ○                   │                     │
└──────────┴─────────────────────┴─────────────────────┴─────────────────────┘

● = Connected (depth > 0)
○ = Connected but disabled
  = No connection

Colours: Cyan = LFO, Orange = Sloth, Purple = MIDI (future)
```

**Success criteria:** Matrix opens, shows current connections, click toggles, audio responds.

**Estimated effort:** 2-3 sessions

---

### Phase 5: Depth Control

**Goal:** Set modulation depth per connection.

**Deliverables:**
1. Click connected cell → depth popup appears
2. Depth popup:
```
┌─────────────────────────────┐
│  LFO 1 A → Gen 1 Cutoff     │
│                             │
│  -100% ════●════════ +100%  │
│           +50%              │
│                             │
│  [Disable]  [Remove]  [OK]  │
└─────────────────────────────┘
```
3. Horizontal slider: -100% to +100% (centre = 0)
4. Visual feedback: cell size/intensity reflects depth magnitude
5. Right-click context menu: Set depth, Disable, Remove, Copy to row

**Success criteria:** Can set different depths on same source to different targets.

**Estimated effort:** 1-2 sessions

---

### Phase 6: Visual Polish & Interaction

**Goal:** Matrix feels like a proper instrument, not a prototype.

**Deliverables:**
1. **Generator grouping:** Visual separators between generator columns
2. **Mod source grouping:** Visual separators between slots (every 4 rows)
3. **Active highlighting:** 
   - Highlight row when mod source is outputting non-zero
   - Highlight column when generator is active
4. **Keyboard shortcuts:**
   - Arrow keys: navigate cells
   - Space: toggle connection
   - Delete: remove connection
   - D: open depth editor
   - 1-9: quick depth (10%-90%)
5. **Drag operations:**
   - Drag across row: assign source to multiple destinations
   - Shift-drag: copy depth value
6. **Colour coding:**
   - LFO connections: cyan
   - Sloth connections: orange
   - MIDI connections: purple (future)
7. **Window behaviour:**
   - Remembers position/size
   - "Always on top" option
   - Resizable with sensible minimums

**Success criteria:** Can route an entire patch quickly using keyboard + mouse.

**Estimated effort:** 2 sessions

---

### Phase 7: Modulation Visualisation on Main UI

**Goal:** See modulation happening on the actual sliders (Korg wavestate style).

**Deliverables:**
1. `ModulatedSlider` class (extends FaderSlider):
   - Draws base value (normal handle)
   - Draws mod range brackets (static)
   - Draws current modulated value (animated line)
2. SC sends modulated values:
   - `/noise/gen/{slot}/{param}/modulated [value]`
   - Batched at ~30fps to reduce traffic
3. Only active modulated params get visualised (no CPU waste)
4. Colour matches source type (cyan for LFO, orange for Sloth)

**Visual:**
```
    ┃  ╭─ max
    ┃  │
    ╞══╡  ← current (moving)
    ●━━│  ← base (user set)
    ┃  │
    ┃  ╰─ min
    ┃
```

**Success criteria:** Move LFO rate → see cutoff slider bracket animate in real-time.

**Estimated effort:** 2-3 sessions

---

### Phase 8: Multi-Source Summation

**Goal:** Multiple mod sources can target the same parameter.

**Deliverables:**
1. Summation mode select (per destination or global):
   - **Add:** values sum (can exceed range, clipped)
   - **Average:** values averaged
   - **Max:** highest absolute value wins
2. SC-side summing in modulation apply logic
3. Matrix shows multiple connections per column cell:
```
│ G1 CUT │
├────────┤
│  ●●    │  ← Two sources connected
│  ●     │
│        │
```
4. Visualisation shows combined range on slider

**Success criteria:** LFO + Sloth both modulating cutoff, hear combined movement.

**Estimated effort:** 1-2 sessions

---

### Phase 9: MIDI as Mod Source

**Goal:** MIDI CCs appear as mod sources in the matrix.

**Deliverables:**
1. Additional mod source rows (below the 16 internal sources):
   - Velocity (per-slot, captured on note-on)
   - Mod Wheel (CC1)
   - Aftertouch
   - Expression (CC11)
   - Assignable CC (user picks CC number)
2. MIDI values scaled to 0-1 (unipolar) or -1 to +1 (bipolar)
3. MIDI sources in matrix with purple colour coding
4. Optional: MIDI learn - click cell, move controller, auto-assign

**Matrix with MIDI rows:**
```
├──────────┼─────────────────────┼─────────────────────┤
│ SLTH 4 R │                     │                     │
├──────────┼─────────────────────┼─────────────────────┤  ← separator
│ Velocity │ ●                   │ ●                   │  ← purple
│ ModWheel │       ●             │                     │
│ AftTch   │                     │       ●             │
└──────────┴─────────────────────┴─────────────────────┘
```

**Success criteria:** Route mod wheel to filter cutoff via matrix.

**Estimated effort:** 2 sessions

---

### Phase 10: Preset Integration

**Goal:** Matrix state saves/loads with presets.

**Deliverables:**
1. Preset JSON includes `modulation.connections` array
2. Load preset → matrix updates → audio routes update
3. "Init" preset clears all connections
4. Option: "Keep modulation" when loading preset (checkbox)

**Success criteria:** Save preset with complex routing, load it fresh, sounds identical.

**Estimated effort:** 1 session (depends on preset system existing)

---

### Phase 11: Meta-Modulation (MatrixBrute-style)

**Goal:** Modulate the depth of a mod route with another mod source.

**Concept:** Instead of LFO 1 → Cutoff at fixed 50% depth, have Mod Wheel → (LFO 1 → Cutoff depth). As you push the mod wheel, the LFO effect intensifies.

**Deliverables:**
1. "Mod depth" as virtual destination type
2. When assigning meta-mod, select: Source → existing route's depth
3. SC-side: depth becomes dynamic bus, not static value
4. Matrix visualisation: meta-routes shown differently (dashed line?)

**Success criteria:** Mod wheel at 0 = no LFO effect. Mod wheel at 127 = full LFO sweep.

**Estimated effort:** 2-3 sessions

---

### Phase 12: Envelope Follower as Mod Source

**Goal:** External audio or generator output drives modulation (Cric-style).

**Deliverables:**
1. Env Follower mod generator type (joins LFO/Sloth cycle)
2. Input selection: Audio In, Gen 1-8 output, Master out
3. Attack/Release controls for follower smoothing
4. Output to mod bus like other sources

**Success criteria:** Drum loop into audio in → envelope drives filter cutoff.

**Estimated effort:** 2 sessions

---

## Future Expansion (Post-Phase 12)

- **Matrix presets:** Save/load just the routing (independent of sound)
- **Mod source sends:** Route mod sources to FX parameters
- **Global mod amount:** Master depth scaler per source
- **Audio through matrix:** Route generator outputs through matrix (Cric-style)
- **Scope in matrix:** Small waveform preview in row header
- **CFG hybrid:** Attack/Decay envelope that can also cycle (Cric-style)
- **LFO ROT as mod target:** Sloth → LFO phase rotation for evolving relationships

---

## Technical Decisions

### Where Does Modulation Happen?

**Decision:** SuperCollider (audio thread)

**Rationale:**
- Modulation needs to be sample-accurate for audio-rate sources
- SC already has the parameter buses
- Python just sends routing changes, doesn't process audio

**Implementation:**
- Each parameter bus gets an optional mod input
- `~applyModulation` helper sums base value + (mod bus × depth)
- Routing table in SC: `~modRouting[slot][param] = [[modBus, depth], ...]`

### Visualisation Data Flow

**Decision:** SC calculates, sends snapshots to Python

**Flow:**
```
SC: param base value + mod = actual value
         │
         ├──► Audio output (continuous)
         │
         └──► OSC snapshot @ 30fps ──► Python ──► Slider repaint
```

**Batching:** SC collects all modulated values, sends one message per frame:
```
/noise/mod/values [slot1_cut, slot1_res, slot2_cut, ...]
```

### Connection Storage

**Decision:** Dual storage (Python primary, SC mirror)

- Python: Source of truth, saves to preset
- SC: Mirror for audio processing, rebuilt on connect

On connect, Python sends all connections to SC. On disconnect, SC clears routing.

---

## Files Overview

```
src/gui/mod_matrix_window.py     # Main matrix window
src/gui/mod_matrix_cell.py       # Individual cell widget
src/gui/mod_depth_popup.py       # Depth editor popup
src/gui/modulated_slider.py      # Extended slider with visualisation
src/gui/mod_routing_state.py     # Connection data model
src/config/mod_routing.py        # OSC paths, constants

supercollider/core/mod_osc.scd        # OSC handlers (Phase 1)
supercollider/core/mod_slots.scd      # Slot management (Phase 1)
supercollider/core/mod_routing.scd    # Routing logic (Phase 2-3)
supercollider/core/mod_apply.scd      # Parameter modulation (Phase 2)
```

---

## Open Questions

1. **Column ordering:** FRQ-CUT-RES-ATK-DEC-P1-P5 or group by type?
2. **Empty generators:** Show columns for empty slots or hide?
3. **Custom param labels:** Show "P1" or actual label ("Chaos")?
4. **Negative depth display:** Different colour or just negative number?
5. **Matrix size on small screens:** Scrollable or zoom?
6. **4th scope trace colour:** Need to add to skin system

---

## Reference Hardware

### Arturia MatrixBrute

16×16 physical button grid. Key learnings:

- **Bipolar depth (±99)** - not just 0-100%, allows inverted modulation
- **Meta-modulation** - mod wheel can control the *amount* of LFO→Cutoff, not just target the same param. Implemented via user-assignable destinations that point to other mod routes.
- **Visual states**: Pink = currently selected, Blue = connected, Dark = empty
- **12 fixed + 16 user-assignable destinations** - lets you modulate anything with a knob
- **Source list**: ENV1-3, Env Follower, LFO1-3, Mod Wheel, Kbd/Seq, Aftertouch, Velocity, Seq Mod, Macro 1-4

**Steal for Noise Engine:**
- Meta-modulation (Phase 11): depth-of-route as destination
- User-assignable destinations pointing to any parameter

### Future Sound Systems Cric

Physical pin matrix (actual coloured pins). Key learnings:

- **Pins by colour** - visual distinction at a glance
- **Nothing hardwired** - even audio I/O routes through matrix
- **CFGs (Cyclical Function Generators)** - envelope/LFO hybrids with Attack+Decay stages, can cycle or one-shot
- **S&H switchable source** - noise OR any input
- **VCA as gain stage** - self-feedback loop for overdrive

**Steal for Noise Engine:**
- Colour-coded connections by source type (cyan=LFO, orange=Sloth, purple=MIDI)
- Consider CFG-style hybrid modulators (envelope that can cycle)
- Future: audio routing through matrix (effects as destinations)

### Quadrature References

- Buchla 281 Quad Function Generator
- Make Noise Maths (complementary outputs)
- Joranalogue Orbit (3-phase system)
- Doepfer A-143-9 Quadrature LFO

---

## Success Vision

You open Noise Engine. Second monitor has the matrix. You're tweaking a patch:

1. Click LFO 1-A row, drag across Gen 1 and Gen 2 cutoff columns
2. Both cutoffs now have cyan brackets showing mod range
3. Sliders animate as LFO cycles - all 4 outputs visible in scope at 90° offsets
4. Click Gen 1 cutoff cell, drag depth to +80%
5. Click Gen 2 cutoff cell, drag depth to -30% (inverse)
6. Route LFO 1-B (90° offset) to Gen 3 cutoff - phase-shifted sweep
7. Route Sloth 2-R (gate output) to Gen 4 frequency - irregular pitch bursts
8. Gen 1 filter sweeps up, Gen 2 sweeps down, Gen 3 follows 90° behind, Gen 4 gets chaos gates

That's the goal. Immediate, visual, musical. 16 mod sources ready to route anywhere.
