# Debugging Guide

## Quick Debug Scripts

### Add Debug Output
```bash
./tools/debug_add.sh
```
This adds debug print statements to key functions and creates backups.

### Remove Debug Output
```bash
./tools/debug_remove.sh
```
This restores files from backups or cleans debug markers.

---

## Common Issues & Solutions

### 1. Generators Don't Start (No Sound)

**Symptoms:** 
- Select generator in Python, no sound
- Node tree shows empty genGroup

**Debug steps:**

1. **Check OSC port mismatch (MOST COMMON ISSUE):**
   ```supercollider
   // In SuperCollider - DO THIS FIRST
   NetAddr.langPort.postln;  // Note this value (57120 or 57122)
   ```
   
   ```bash
   # Check Python config
   grep OSC_SEND_PORT ~/repos/noise-engine/src/config/__init__.py
   ```
   
   **If they don't match:** Update `src/config/__init__.py` and restart Python:
   ```python
   OSC_SEND_PORT = 57120  # Use value from SC langPort
   ```

2. **Verify OSC messages are received:**
   ```supercollider
   // In SuperCollider
   OSCFunc.trace(true);
   // Select generator in Python
   // Look for: /noise/start_generator [1, testSynth]
   OSCFunc.trace(false);
   ```

3. **Check Python is sending:**
   ```bash
   ./tools/debug_add.sh
   python -m src.main
   # Look for: DEBUG [on_generator_changed]: slot=1, type=Test Synth, osc_connected=True
   ```

4. **Verify SynthDef exists:**
   ```supercollider
   SynthDescLib.global[\testSynth].postln;  // Should NOT be nil
   ```

5. **Manual test in SC:**
   ```supercollider
   ~startGenerator.(1, \testSynth);
   s.queryAllNodes;  // Should show testSynth in genGroup
   ```

---

### 2. OSC Connection Issues

**Symptoms:**
- Python shows "Connected" but no messages received in SC
- `osc_connected=True` but generators don't start

**Debug steps:**

1. **Check SC is listening:**
   ```supercollider
   OSCFunc.trace(true);
   // Any OSC activity will show here
   ```

2. **Check Python OSC client:**
   ```python
   # In Python console or add to code
   print(f"OSC target: {self.osc.client._address}:{self.osc.client._port}")
   ```

3. **Verify ports:**
   - SC langPort: `NetAddr.langPort.postln;` (typically 57122)
   - SC server port: 57110 (DO NOT send OSC here)
   - Python sends to: `OSC_SEND_PORT` in config (must match langPort)

---

### 3. SynthDef Compilation Errors

**Symptoms:**
- Generator loads but SynthDescLib shows nil
- No error message but SynthDef doesn't work

**Debug steps:**

1. **Check for silent failures:**
   ```supercollider
   // Try loading manually
   (~basePath +/+ "generators/test_synth.scd").load;
   ```

2. **Verify helpers exist:**
   ```supercollider
   ~multiFilter.postln;  // Should show a Function
   ~envVCA.postln;       // Should show a Function
   ```

3. **Test minimal SynthDef:**
   ```supercollider
   (
   SynthDef(\manualTest, { |out|
       var sig = SinOsc.ar(440) * 0.2;
       sig = ~multiFilter.(sig, 0, 1000, 0.5);
       Out.ar(out, sig ! 2);
   }).add;
   )
   SynthDescLib.global[\manualTest].postln;
   ```

---

### 4. SSOT Check Failures

**Symptoms:**
- `check_ssot.sh` shows violations
- Generators not using helpers

**Debug steps:**

1. **Run full check:**
   ```bash
   ./tools/check_ssot.sh
   ```

2. **Check specific generator:**
   ```bash
   grep "~envVCA\|~multiFilter" supercollider/generators/test_synth.scd
   ```

3. **Verify generator structure follows pattern:**
   ```supercollider
   // Must have these lines (not inline code):
   sig = ~multiFilter.(sig, filterType, filterFreq, rq);
   sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
   ```

---

## Debug Output Locations

| Component | Debug Location | What to Look For |
|-----------|---------------|------------------|
| Python GUI | Terminal | `DEBUG [function_name]: ...` |
| OSC Messages | SC Post Window | `OSCFunc.trace(true)` output |
| Node Tree | SC Post Window | `s.queryAllNodes;` output |
| SynthDefs | SC Post Window | `SynthDescLib.global[\name].postln;` |

---

## After Debugging

Always clean up:
```bash
./tools/debug_remove.sh
git add -A
git commit -m "Remove debug output"
```

Never commit debug output to main branch.
