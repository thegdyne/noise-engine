# How to Use and Configure the Morph Mapper Hotkey

**Quick Reference:** Press **Ctrl+Shift+M** (or **Cmd+Shift+M** on Mac) to trigger a hardware CV sweep.

---

## What It Does

The hotkey runs a complete morph mapper sweep with hardcoded parameters optimized for the Buchla 258 oscillator. It:

1. ✅ Detects your MIDI port (CV.OCD or MOTU M6)
2. ✅ Sweeps CV from 0V to 5V in equal steps
3. ✅ Captures telemetry + waveforms at each point
4. ✅ Saves a morph map JSON to `maps/` directory
5. ✅ Logs completion with filename

---

## Current Configuration

**Location:** `src/gui/main_frame.py` (around line 1274-1290)
```python
mapper = MorphMapper(
    sc_client=self.osc.client,
    telemetry_controller=self.telemetry_controller,
    device_name="Buchla 258",
    cv_range=(0.0, 5.0),
    points=12,                    # ← Number of snapshots
    slot=current_slot,
    settle_ms=1000,               # ← Time to wait at each CV step (ms)
    vmax_calibrated=5.07,         # ← Calibrated max voltage
    midi_port=midi_port,
    cv_mode='unipolar'
)
```

**Default values:**
- **12 points** → CC step size = 125/11 ≈ 11.36 (rounded to integers)
- **1000ms settle** → 1 second per point
- **Total time:** ~12-15 seconds

---

## How to Change Parameters

### Change Number of Points

**Recommended values:**

| Points | CC Step | Resolution | Total Time (1000ms) | Total Time (200ms) | Use Case |
|--------|---------|------------|---------------------|--------------------|--------------------|
| 12     | ~11     | Low        | ~12s                | ~2.4s              | Quick test |
| 26     | 5       | Medium     | ~26s                | ~5.2s              | **Recommended** |
| 51     | 2.5     | High       | ~51s                | ~10s               | Detailed analysis |
| 126    | 1       | Maximum    | ~2m 6s              | ~25s               | Gold standard |

**Edit command (26 points):**
```bash
cd ~/repos/noise-engine
sed -i '' 's/points=12,/points=26,/' src/gui/main_frame.py
```

**Verify:**
```bash
grep "points=" src/gui/main_frame.py | grep MorphMapper -A 10
```

---

### Change Settle Time

**Recommended values:**

| Settle Time | Description | Use Case |
|-------------|-------------|----------|
| 200ms       | Fast        | Stable oscillators (Buchla 258) |
| 500ms       | Medium      | Most hardware |
| 1000ms      | Slow        | Complex modules, filters |
| 2000ms      | Very slow   | Thermal-sensitive gear |

**Why reduce settle time?**
- The Buchla 258 is a stable VCO
- CV changes settle in <100ms typically
- Default 1000ms is overly cautious
- Shorter settle = faster sweeps = less thermal drift

**Edit command (200ms):**
```bash
cd ~/repos/noise-engine
sed -i '' 's/settle_ms=1000,/settle_ms=200,/' src/gui/main_frame.py
```

---

### Change Device Name
```bash
# Example: Change to your specific module
sed -i '' 's/device_name="Buchla 258",/device_name="Intellijel Rubicon",/' src/gui/main_frame.py
```

The device name appears in:
- JSON metadata
- Log messages
- Output filenames

---

### Change CV Range

**Default:** 0V to 5V (unipolar)

**For different modules:**
```python
# Buchla-style 0-10V
cv_range=(0.0, 10.0),
vmax_calibrated=10.07,

# Eurorack ±5V (bipolar)
cv_range=(-5.0, 5.0),
cv_mode='bipolar'
vmax_calibrated=5.07,

# Limited range (zoom in on a region)
cv_range=(2.0, 4.0),
```

**Manual edit required** (no one-liner sed for this).

---

## Recommended Configurations

### Quick Test (Current Default)
```python
points=12,
settle_ms=1000,
```
- Fast, good for "does this work?"
- Under-samples the knee region

### **Recommended: Balanced Resolution**
```python
points=26,
settle_ms=200,
```
- 2× knee resolution
- 4× faster total time
- Best ROI for analysis

**Apply both:**
```bash
cd ~/repos/noise-engine
sed -i '' 's/points=12,/points=26,/' src/gui/main_frame.py
sed -i '' 's/settle_ms=1000,/settle_ms=200,/' src/gui/main_frame.py
```

### High-Resolution Reference
```python
points=51,
settle_ms=500,
```
- Excellent detail
- Still reasonable run time (~25s)

### Gold Standard Archive
```python
points=126,
settle_ms=500,
```
- Full CC resolution (step=1)
- Use for publication/archival
- Requires thermal stability

---

## Usage Workflow

### 1. Before Running

**Hardware checklist:**
- [ ] Buchla 258 oscillating (stable frequency)
- [ ] CV.OCD powered and configured (CVA = MIDI CC1)
- [ ] Audio output → MOTU M6 Input 1
- [ ] Noise Engine running, slot selected

### 2. Trigger the Sweep

Press **Ctrl+Shift+M** (or **Cmd+Shift+M**)

**Watch for:**
- Console log: `[MorphMapper] Starting sweep on slot X`
- Sweep progress: `[1/26] CV = 0.00V ... [26/26] CV = 5.00V`
- Completion: `[MorphMapper] Saved to: maps/morph_map_buchla_258_YYYYMMDD_HHMMSS.json`

### 3. Analyze the Results
```bash
# Quick view
python tools/analyze_morph_map.py maps/morph_map_buchla_258_YYYYMMDD_HHMMSS.json

# Full output
python tools/analyze_morph_map.py maps/morph_map_buchla_258_YYYYMMDD_HHMMSS.json --csv --plot --patch-json
```

---

## Troubleshooting

### "No MIDI port found"

**Check:**
1. CV.OCD powered from Eurorack PSU?
2. USB-MIDI cable connected?
3. Port appears in system MIDI devices?

**Test:**
```bash
python -c "from src.hardware.midi_cv import MidiCV; print(MidiCV.list_ports())"
```

### "Point 0 timeout"

**Possible causes:**
1. Generator not loaded in slot
2. `hw_profile_tap` not available
3. Audio input channel wrong
4. Hardware not generating audio

**Fix:**
- Load any generator into the target slot first
- Verify hardware is oscillating
- Check MOTU M6 input meters

### "Thermal drift / frequency unstable"

**Solutions:**
1. Reduce `settle_ms` (faster sweep = less drift)
2. Warm up hardware for 10 minutes first
3. Use climate-controlled room

---

## Advanced: Custom CC Lists

If you want non-uniform spacing (e.g., dense samples around the knee), you'll need to modify the code more extensively. The current hotkey uses uniform `cv_range` with fixed `points`.

**For custom sweeps, use the Python API directly:**
```python
from src.telemetry.morph_mapper import MorphMapper

# Example: Dense sampling 60-80, sparse elsewhere
cc_list = [0, 10, 20, 30, 40, 50, 
           60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70,  # Dense
           71, 72, 73, 74, 75, 76, 77, 78, 79, 80,      # Dense
           90, 100, 110, 120, 125]

# Convert CC to voltage (assuming vmax=5.07)
cv_list = [cc * 5.07 / 127 for cc in cc_list]

# Run custom sweep (not via hotkey)
mapper = MorphMapper(
    sc_client=audio_controller.sc_client,
    telemetry_controller=audio_controller.telemetry_controller,
    device_name="Buchla 258",
    cv_range=(0.0, 5.0),
    points=len(cv_list),
    slot=0,
    vmax_calibrated=5.07,
)
# ... (custom CV list injection requires code modification)
```

This is outside the scope of the hotkey. Use the hotkey for uniform sweeps only.

---

## Quick Reference Commands
```bash
# Apply recommended config (26 points, 200ms settle)
cd ~/repos/noise-engine
sed -i '' 's/points=12,/points=26,/' src/gui/main_frame.py
sed -i '' 's/settle_ms=1000,/settle_ms=200,/' src/gui/main_frame.py

# Verify changes
grep -A 5 "points=" src/gui/main_frame.py | grep "MorphMapper" -A 10

# Revert to defaults
git checkout src/gui/main_frame.py
```

---

## Summary

**Hotkey:** Ctrl+Shift+M  
**Location:** `src/gui/main_frame.py` line ~1279  
**Recommended change:** `points=12` → `points=26` + `settle_ms=1000` → `settle_ms=200`  
**Result:** 2× resolution, 4× faster, integer CC steps

---

**Last updated:** 2026-02-06
