# How to Analyze a Morph Map (CV Sweep Waveform Analyzer)

**Status:** Reference doc for post-sweep analysis of hardware morph maps  
**Prerequisite:** [Morph Mapper Current State](HARDWARE_MORPH_MAPPER_CURRENT_STATE.md), [Forensic Calibration Guide](HOWTO_FORENSIC_CALIBRATION.md)  
**Tool:** `tools/analyze_morph_map.py`

## Overview

After running a hardware CV sweep with the Morph Mapper (Ctrl+Shift+M), you get a JSON morph map in `maps/`. The analyzer decomposes that sweep into **three independent tracks** — Gain, DC, and Shape — revealing how the hardware actually behaves across its morph range.

This replaces the old ad-hoc `sym=` metric (never committed) which had regime changes and non-monotonic spikes that made it useless for curve fitting.

```
JSON morph map  →  Waveform-level metrics  →  Three-track decomposition
                                            →  Region detection
                                            →  CSV export
                                            →  PNG plot
```

**No Noise Engine dependencies.** The analyzer uses only stdlib + numpy (matplotlib for plots). It can run independently of the main application.

---

## Part 1: Quick Start

### Basic Console Analysis

```bash
python tools/analyze_morph_map.py maps/sweep_sine_saw.json
```

This prints everything to the console: header, CV sweep data table, three-track decomposition, shape-invariant metrics, harmonic signatures, region analysis, sweep behavior summary, and metadata.

### Export to CSV

```bash
# Auto-named (maps/sweep_sine_saw_analysis.csv)
python tools/analyze_morph_map.py maps/sweep_sine_saw.json --csv

# Custom path
python tools/analyze_morph_map.py maps/sweep_sine_saw.json --csv ~/Desktop/analysis.csv
```

### Generate PNG Plot

```bash
# Auto-named (maps/sweep_sine_saw_analysis.png)
python tools/analyze_morph_map.py maps/sweep_sine_saw.json --plot

# Custom path
python tools/analyze_morph_map.py maps/sweep_sine_saw.json --plot ~/Desktop/analysis.png

# Suppress theoretical crest factor guide lines
python tools/analyze_morph_map.py maps/sweep_sine_saw.json --plot --no-guides
```

### Dual-Sweep Comparison

Compare two sweeps side-by-side (e.g., sine→saw vs sine→square from the same module):

```bash
python tools/analyze_morph_map.py maps/sweep_sine_saw.json maps/sweep_sine_sqr.json --plot
```

This aligns the two sweeps by MIDI CC (exact match) or CV voltage (nearest within 0.1V) and generates a two-column plot. CSV export in dual mode produces separate `_A` and `_B` files.

### All Outputs at Once

```bash
python tools/analyze_morph_map.py maps/sweep_sine_saw.json --csv --plot
```

---

## Part 2: The Three-Track Model

The Buchla 258's morph is a **crossfade mixer** between derived waveforms, not a waveshaper. The analyzer separates the three independent behaviors that this crossfade produces:

```
output(CV) = G(CV) · shape(CV) + D(CV)

Where:
  G(CV)     = gain envelope (ShapeRMS, Peak — branch hotness)
  D(CV)     = DC offset (waveform mean — shaping asymmetry)
  shape(CV) = normalized waveform character (crest, harmonics, HF)
```

Each track is continuous and well-behaved across the full CC range.

### Gain Track

Measures energy level changes across the sweep.

| Metric | What It Shows |
|--------|---------------|
| `shape_rms` | AC energy only (DC removed) — the "loudness" of the waveform shape |
| `peak` | Absolute maximum amplitude — the ceiling |

**What to look for:** The gain track reveals energy compression zones where the crossfade between branches causes a dip in signal level. On a Buchla 258, expect a compression dip around CC 60–80 as the module transitions between waveform branches.

### DC Track

Measures waveform bias drift across the sweep.

| Metric | What It Shows |
|--------|---------------|
| `dc` | Mean value of the waveform (0.0 = centered) |
| `range_asym` | `|pos_peak| / (|pos_peak| + |neg_peak|)` — amplitude balance (0.5 = symmetric) |

**What to look for:** Asymmetric waveform shaping causes DC drift. On the 258 sine→saw sweep, DC drifts negative as the saw's asymmetric shape develops. The range asymmetry departs from 0.5 at the transition knee.

### Shape Track

Measures waveform character evolution, independent of gain and DC.

| Metric | What It Shows |
|--------|---------------|
| `crest` | Peak / RMS — "peakedness" of the waveform |
| `hf` | Edge sharpness (mean absolute first-difference / RMS) |
| `skew` | Third moment on unit-normalized waveform — directional asymmetry |

**What to look for:** Crest factor is the single most revealing diagnostic. A pure sine has crest = √2 ≈ 1.414, a saw has crest = √3 ≈ 1.732, a square has crest = 1.0. The plot includes these as guide lines for oscillator sweeps. HF energy should rise monotonically as the waveform gains harmonic content toward the saw/square end.

---

## Part 3: Console Output Walkthrough

The console output has six sections. Here's what each tells you:

### CV Sweep Data

```
=== CV SWEEP DATA ===
Point   CV(V)   CC  Freq(Hz)    RMS   Peak   Waveform
-------------------------------------------------------
    1   0.000    0      68.8  0.234  0.399   N=1024
```

Basic sanity check. Frequency should be roughly constant for a shape-only sweep (the morph knob doesn't change pitch). `N=1024` confirms the full waveform was captured; `---` means hw_dna fallback was used.

### Three-Track Decomposition

```
=== THREE-TRACK DECOMPOSITION ===
Point  CC   DC        ShapeRMS    Peak   Crest  Span   RangeAsym   HF
----------------------------------------------------------------------
    1   0   +0.0010    0.234     0.399   1.71  0.542    0.502    0.105
```

The main analysis table. All metrics computed from the raw 1024-sample waveform. This is where you spot trends across the sweep.

### Shape-Invariant Metrics

```
=== SHAPE-INVARIANT METRICS (DC removed, unit RMS) ===
Point  CC   NormCrest   NormAsym   NormHF    Skew
---------------------------------------------------
    1   0      1.710      0.502    0.105   +0.0012
```

Same shape metrics but **normalized** — DC removed, scaled to unit RMS. These let you compare waveform shape across points where gain and DC are different. Useful for identifying when the waveform character actually changes vs. when only the gain drifts.

### Harmonic Signatures

```
=== HARMONIC SIGNATURES (8 FFT bands) ===
Point  CC  |     h1     h2     h3     h4     h5     h6     h7     h8   Bright
```

Shown only when the morph map includes `hw_dna.harmonic_signature` data. The brightness ratio (sum h5–h8 / sum h1–h4) tracks high-frequency content development.

### Region Analysis

```
=== REGION ANALYSIS ===
Sine zone:          CC 0-34  (crest 1.71-1.74, range_asym 0.50-0.51)
Transition knee:    CC 46→68 (crest 1.89→2.21)
Energy compression: CC 68    (shape_rms minimum: 0.209)
Endpoint character: CC 114-125 (crest 2.09-2.21, span 0.67-0.71)
```

**Oscillator sweeps only.** Automatically identifies four regions from the metric gradients:

| Region | Detection | What It Means |
|--------|-----------|---------------|
| Sine zone | crest < 1.8 AND range_asym ≈ 0.5 for 2+ consecutive points | Module is still producing near-pure sine |
| Transition knee | Largest |Δcrest| between adjacent points | Where the crossfade kicks in — waveform shape changes fastest |
| Energy compression | Local minimum of shape_rms after knee | Crossfade dip — branches partially cancel |
| Endpoint character | Last points with stable metrics | Settled target waveform (saw, square, etc.) |

### Sweep Behavior

```
=== SWEEP BEHAVIOR ===
Gain track:  ShapeRMS 0.234→0.301 (+28.6%), Peak 0.399→0.628 (+57.4%)
DC track:    +0.001→-0.063 (negative drift, peak at CC80: -0.086)
Shape track: Crest 1.71→2.09, HF rising monotonically, Skew +0.00→-0.12
```

Start-to-end summary. Quick read of how the three tracks evolved across the full sweep.

---

## Part 4: PNG Plot Layout

The plot generates a five-row chart (single-column for one sweep, two-column for dual comparison):

| Row | Content | What to Look For |
|-----|---------|------------------|
| 1 | **Gain Track** — ShapeRMS + Peak vs CC | Compression dip, gain ramp |
| 2 | **DC & Asymmetry** — DC offset (left axis) + range asymmetry (right axis) | DC drift onset, asymmetry departure from 0.5 |
| 3 | **Crest Factor** — with theoretical guide lines (sine √2, saw √3, square 1.0) | Shape evolution trajectory, how close to ideal |
| 4 | **Waveform Envelope** — pos peak, neg peak, DC fill | Visual envelope shape, asymmetric growth |
| 5 | **HF Energy** — edge sharpness vs CC | Harmonic content development, should be monotonic |

Each row has a **50% valid data gate** — if fewer than half the points have waveform data for that metric, the trace is suppressed with an "Insufficient data" label and a warning is printed.

The `--no-guides` flag suppresses the theoretical crest factor guide lines on row 3, useful when analyzing non-oscillator devices where those references don't apply.

---

## Part 5: CSV Format

The CSV contains one row per sweep point with all waveform metrics as columns:

```
cv_voltage,midi_cc,freq,dc,rms,peak,crest,pos_peak,neg_peak,span,
range_asym,hf,shape_rms,shape_crest,norm_crest,norm_range_asym,
norm_hf,skew,waveform_n
```

Points without waveform data have `nan` for all waveform-derived columns. Invalid points are kept (not filtered out). This makes it straightforward to load into pandas, a spreadsheet, or any curve-fitting tool.

**Dual-sweep CSV:** Produces separate files with `_A` / `_B` suffixes, each in their respective input file's directory.

---

## Part 6: Dual-Sweep Comparison

### Alignment

When comparing two sweeps, the analyzer aligns them one-to-one:

1. **Primary:** Exact MIDI CC match
2. **Fallback:** Nearest CV voltage within 0.1V (tie-break: smallest |ΔV|, then nearest CC, then index)
3. **Unmatched:** A-side points without a B-side match produce gaps in the B trace

Each B point can only be matched once (no duplication). Alignment warnings are printed when points can't be matched.

### Use Cases

The main use case is comparing two morph directions from the same module — e.g., sine→saw vs sine→square on a Buchla 258. This reveals:

- Whether the sine zone is consistent across both morphs
- How transition knee position differs between morph targets
- Relative gain behavior (one branch may be hotter than the other)
- DC drift direction (positive vs negative depending on target waveform)

---

## Part 7: Interpreting Results for Digital Twin Work

### What Healthy Data Looks Like

- **Frequency stable** (±2Hz) across all points — morph should not affect pitch
- **Waveform coverage ≥90%** — most points have N=1024 samples
- **Crest factor monotonic** or at least smooth — no wild jumps (those indicate capture artifacts)
- **DC near zero at CC=0** — sine starting point should be centered
- **HF rising** toward the saw/square end — harmonic content developing as expected

### Red Flags

| Symptom | Likely Cause |
|---------|-------------|
| Many `---` in waveform column | Waveform lock failed; increase settle_ms or check telemetry rate |
| Frequency jumps between points | Morph also affects pitch (intentional on some modules) or hardware instability |
| Crest factor spikes > 3.0 | Possible capture glitch or signal dropout; re-run that region |
| DC offset > 0.2 at CC=0 | Hardware DC bias; may need calibration or LeakDC compensation |
| HF non-monotonic with drops | Possible waveform aliasing or capture timing issue |

### Feeding Results Into Calibration

The three-track decomposition directly feeds into the [Forensic Calibration Loop](HOWTO_FORENSIC_CALIBRATION.md):

1. **Gain track** → Sets the amplitude envelope targets for your digital generator across the morph range
2. **DC track** → Tells you how much DC offset your digital model needs to inject at each morph position
3. **Shape track** → Crest factor and HF targets for waveform shape matching

The CSV export is designed for exactly this workflow — load it, fit curves to each track, and use those curves as lookup tables in your SynthDef.

---

## Part 8: Dependencies

```
numpy          # Required — all waveform metric computation
matplotlib     # Optional — only needed for --plot flag (lazy import)
```

No Noise Engine imports. No SuperCollider connection needed. The tool operates entirely on saved JSON files.

---

## Part 9: File Locations

| File | Purpose |
|------|---------|
| `tools/analyze_morph_map.py` | The analyzer script (this guide) |
| `maps/*.json` | Morph map JSON files (sweep output) |
| `maps/*_analysis.csv` | CSV exports (auto-generated alongside JSON) |
| `maps/*_analysis.png` | Plot exports (auto-generated alongside JSON) |
| `MORPH_ANALYZER_SPEC.md` | Specification for v2 three-track decomposition |
| `HARDWARE_MORPH_MAPPER_CURRENT_STATE.md` | Current state of the sweep system |

---

## Quick Reference

```bash
# Single sweep — console only
python tools/analyze_morph_map.py maps/sweep.json

# Single sweep — all outputs
python tools/analyze_morph_map.py maps/sweep.json --csv --plot

# Dual comparison with custom plot path
python tools/analyze_morph_map.py maps/A.json maps/B.json --plot ~/Desktop/comparison.png

# Plot without theoretical guide lines (non-oscillator devices)
python tools/analyze_morph_map.py maps/filter_sweep.json --plot --no-guides

# Dual comparison — separate CSVs
python tools/analyze_morph_map.py maps/A.json maps/B.json --csv
# → maps/A_analysis_A.csv, maps/B_analysis_B.csv
```

---

**End of Guide**
