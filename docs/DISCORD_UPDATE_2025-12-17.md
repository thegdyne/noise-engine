# Discord Update - December 17, 2025

## 🎛️ PIN MATRIX - Design Complete

Designing a proper second-screen modulation routing matrix. Not a dialog box. A real instrument panel you leave open on monitor 2.

### The Vision

```
┌─────────────────────────────────────────────────────────────────┐
│  MOD MATRIX                                                     │
├──────────┬──────────────────┬──────────────────┬────────────────┤
│          │ GEN 1            │ GEN 2            │ GEN 3     ...  │
│          │ F  C  R  A  D    │ F  C  R  A  D    │ F  C  R  A     │
├──────────┼──────────────────┼──────────────────┼────────────────┤
│ LFO 1 A  │ ●     ○          │    ●             │                │ ← cyan
│ LFO 1 B  │    ○             │       ○          │                │
│ LFO 1 C  │                  │          ●       │                │
│ LFO 1 D  │       ●          │                  │                │
├──────────┼──────────────────┼──────────────────┼────────────────┤
│ SLTH 2 X │       ●          │ ●                │                │ ← orange
│ SLTH 2 Y │                  │                  │    ○           │
│ SLTH 2 Z │                  │       ●          │                │
│ SLTH 2 R │ ○                │                  │                │
└──────────┴──────────────────┴──────────────────┴────────────────┘
```

- **16 mod sources** (4 slots × 4 outputs) → rows
- **8 generators × 10 params** → columns
- Click to connect, drag for depth (-100% to +100%)
- Same LFO can hit cutoff at +80% AND resonance at -20%

### Wavestate-Style Visualisation

Modulated sliders show live brackets:
```
    ┃  ╭─ max range
    ╞══╡  ← current value (animates)
    ●━━│  ← your setting
    ┃  ╰─ min range
```

### Phased Rollout

| Phase | What | Sessions |
|-------|------|----------|
| 0 | **Quadrature expansion** (3→4 outputs, 12→16 buses) | 1-2 |
| 1 | Wire mod sources (OSC handlers, slot management) | 1 |
| 2 | Hardcoded test: LFO → cutoff | 1 |
| 3 | Connection data model + OSC | 1-2 |
| 4 | Matrix window - basic grid (16 rows!) | 2-3 |
| 5 | Depth control popup | 1-2 |
| 6 | Polish: keyboard nav, colours, drag ops | 2 |
| 7 | Slider visualisation (wavestate-style) | 2-3 |
| 8 | Multi-source summation | 1-2 |
| 9 | MIDI as mod source (velocity, mod wheel) | 2 |
| 10 | Preset integration | 1 |
| 11 | Meta-modulation (MatrixBrute-style) | 2-3 |
| 12 | Envelope follower | 2 |

### 16 Mod Buses

Phase 0 expands mod sources from 3→4 outputs per slot:

**LFO:** A (0°), B (90°), C (180°), D (270°) - classic quadrature  
**Sloth:** X (Torpor), Y (Apathy), Z (Inertia), R (rectified gate bursts)

**Flexible slots** - any generator type can occupy any slot:

| Slot | Default | Could be |
|------|---------|----------|
| MOD 1 | LFO | LFO, Sloth, (future: EnvFollow, S&H...) |
| MOD 2 | Sloth | LFO, Sloth, ... |
| MOD 3 | LFO | LFO, Sloth, ... |
| MOD 4 | Sloth | LFO, Sloth, ... |

4× LFO? Sure. 4× Sloth? Why not. Matrix row labels update dynamically based on what's loaded.

**Gap:** Type selector UI not implemented yet - slots currently fixed to defaults. Architecture supports any combo.

### Honest Status

Before we build the matrix, Phase 0 and 1 need doing:

**Phase 0 - Quadrature:** Current mod sources have 3 outputs. Need 4 for proper quadrature (LFO) and the rectified gate output (Sloth). That's 16 buses instead of 12.

**Phase 1 - Wiring:** The mod source panel looks real but:
- Python sends OSC → nowhere
- SC has buses allocated but no handlers
- ~40 lines of SC code to actually connect things

Foundation first, then the fun stuff.

### Design Doc

Full spec: `docs/PIN_MATRIX_DESIGN.md`

Covers: data model, OSC messages, where modulation happens (SC, not Python), visualisation data flow, file structure, open questions.

### Reference Hardware

Read through the **Arturia MatrixBrute** and **Future Sound Systems Cric** manuals. Key steals:

- **MatrixBrute**: Meta-modulation (mod wheel controls *how much* LFO affects cutoff, not just targeting the same param). User-assignable destinations. ±99 bipolar depth.
- **Cric**: Physical coloured pins for visual distinction. Nothing hardwired - even audio routes through matrix. CFG (Cyclical Function Generator) - envelope/LFO hybrids.

Both influenced the phased design. Meta-modulation now Phase 10. Env follower Phase 11.

### The Goal

Second monitor. Matrix open. Drag LFO 1-A across two generators. Watch both cutoffs animate with cyan brackets. Route LFO 1-B (90° offset) to a third gen - phase-shifted sweep. Drop Sloth 2-R (gate) on gen 4 frequency for irregular pitch bursts.

16 mod sources. 4 outputs per slot. Quadrature LFOs. Chaos gates. Immediate. Visual. Musical.

Phase 0 this week - quadrature expansion.
