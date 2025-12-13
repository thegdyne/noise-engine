# Debugging Guide

## ⚠️ CRITICAL: OSC Message Forwarding Bug (READ THIS FIRST!)

**This bug has bitten us TWICE. Don't let it happen again!**

### The Problem

When SuperCollider forwards OSC messages to Python, it **strips the nodeID and replyID** from SendReply messages. This means:

| Source | Raw SendReply Format | Forwarded Format |
|--------|---------------------|------------------|
| SC synth | `[nodeID, replyID, slotID, ampL, ampR]` | `[slotID, ampL, ampR]` |
| Python expects | ❌ 5 args (wrong!) | ✅ 3 args (correct!) |

### Symptoms

- OSC trace shows messages being sent from SC
- Python handler silently fails (no error, just doesn't fire)
- GUI doesn't update even though data is flowing
- `if len(args) >= 5` check fails because only 3 args arrive

### The Fix

**SC forwarder sends ONLY the useful data:**
```supercollider
// In channel_strips.scd or master_passthrough.scd
OSCdef(\forwarder, { |msg|
    // msg = ['/path', nodeID, replyID, data1, data2, ...]
    // Forward ONLY the data we need:
    ~pythonAddr.sendMsg('/path', msg[3], msg[4], msg[5]);
}, '/internal/path');
```

**Python handler expects ONLY the forwarded data:**
```python
def _handle_levels(self, address, *args):
    # Forwarded format: [data1, data2, data3]
    if len(args) >= 3:  # NOT >= 5!
        data1 = args[0]  # NOT args[2]!
        data2 = args[1]  # NOT args[3]!
        data3 = args[2]  # NOT args[4]!
```

### Where This Applies

1. **Master levels** (`/noise/levels`) - Fixed in master_passthrough.scd
2. **Channel levels** (`/noise/gen/levels`) - Fixed in channel_strips.scd

### How To Avoid This Bug

When adding ANY new OSC forwarding:
1. Document the FORWARDED format, not the raw SendReply format
2. Test with debug prints showing `len(args)` and actual arg values
3. Remember: SC forwarder = data extractor, Python = data receiver

---

## In-App Console

The app has a built-in console that shows real-time logs. This is the first place to look when troubleshooting.

### Opening the Console
- Click the **`>_`** button in the top-right corner, OR
- Press **`Ctrl+``** (backtick key, above Tab)

### What You'll See
- **Grey** - DEBUG: Detailed info (parameter changes, OSC messages)
- **Green** - INFO: Normal operation (connected, generator started)
- **Orange** - WARNING: Something unexpected but recoverable
- **Red** - ERROR: Something failed (connection lost, file not found)

### Console Controls
- **Filter dropdown** - Show only INFO/WARN/ERROR levels
- **Auto ↓** - Toggle auto-scroll (click to pause and inspect)
- **Clear** - Wipe the log
- **Copy** - Copy entire log to clipboard (useful for bug reports)

---

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

1. **Check connection status in Python GUI:**
   - Green "● Connected" = good
   - Red "● Connection Failed" = SC not responding
   - Red "● CONNECTION LOST" = connection dropped mid-session

2. **If "Connection Failed" on startup:**
   - Is SuperCollider running?
   - Did you run init.scd? (Cmd+A, Cmd+Return)
   - Check SC post window for errors

3. **Verify SC is listening on correct port:**
   ```supercollider
   NetAddr.langPort.postln;  // Should be 57120 (forced by init.scd)
   ```

4. **Verify OSC messages are received:**
   ```supercollider
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

### 2. Connection Lost Mid-Session

**Symptoms:**
- Red "● CONNECTION LOST" in Python GUI
- "⚠ RECONNECT" button appears
- Audio stops

**What happened:**
- SC crashed, was quit, or the server rebooted
- 3 consecutive heartbeats missed (6 seconds)

**Recovery:**
1. **If SC is still running:** Click "⚠ RECONNECT" button
2. **If SC crashed:** Restart SC, run init.scd, then click "⚠ RECONNECT"
3. **Check SC post window** for error messages

---

### 3. OSC Connection Issues

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
   - SC langPort: `NetAddr.langPort.postln;` (should be 57120, forced by init.scd)
   - SC server port: 57110 (DO NOT send OSC here)
   - Python sends to: `OSC_SEND_PORT` in config (57120)

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
