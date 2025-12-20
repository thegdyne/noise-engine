# Server Controls - Design Document

**Status:** Planning  
**Created:** 2025-12-14

---

## Overview

A lockable server control panel near the Connect SuperCollider button, plus improved connection detection with clear error messages.

---

## Server Control Panel

### Location

Near existing Connect SuperCollider button.

### Layout

**Locked (default):**
```
┌─────────────────────────────────────────┐
│  [Connect SuperCollider]    🔓          │
└─────────────────────────────────────────┘
```

**Unlocked (after clicking 🔓):**
```
┌─────────────────────────────────────────┐
│  [Connect SuperCollider]    🔒          │
│  ┌───────────────────────────────────┐  │
│  │  [s.freeAll]    [s.reboot]        │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Controls

**s.freeAll:**
- Stops all running synths
- Clears audio buses
- Quick recovery from stuck sounds
- Server stays running

**s.reboot:**
- Full server restart
- Clears everything
- Reinitialises server
- Takes a few seconds

### Behaviour

| Action | Result |
|--------|--------|
| Click 🔓 | Panel expands, icon changes to 🔒 |
| Click 🔒 | Panel collapses, icon changes to 🔓 |
| Click s.freeAll | Sends freeAll command to SC |
| Click s.reboot | Sends reboot command to SC, shows "Rebooting..." status |

---

## Connection Detection

### Current State

Basic port check exists.

### Improved Detection

On connect attempt, check both:

1. **Port availability** - Is port 57120 already bound?
2. **Process scan** - Are `sclang` or `scsynth` processes running?

### Detection Flow

```
┌─────────────────────────────────────────┐
│          User clicks Connect            │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│      Check for SC processes             │
│      (sclang, scsynth)                  │
└─────────────────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│      Check port 57120 availability      │
└─────────────────────┬───────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
    ┌───────────┐           ┌───────────┐
    │  Issues   │           │   Clear   │
    │  Found    │           │           │
    ├───────────┤           ├───────────┤
    │ Show      │           │ Proceed   │
    │ specific  │           │ with      │
    │ error     │           │ connect   │
    └───────────┘           └───────────┘
```

### Error Messages

| Situation | Message |
|-----------|---------|
| Port in use, no SC process | "Port 57120 in use by another application." |
| SC process running, port free | "SuperCollider IDE is running. Close it or disconnect first." |
| SC process running, port in use | "SuperCollider IDE is running on port 57120. Close it and try again." |
| Port free, no SC process | Connects normally |

### Process Detection

**macOS:**
```bash
pgrep -x sclang
pgrep -x scsynth
```

**Python implementation:**
```python
import subprocess

def check_sc_processes():
    """Check if SuperCollider processes are running."""
    processes = []
    for proc in ['sclang', 'scsynth']:
        result = subprocess.run(['pgrep', '-x', proc], capture_output=True)
        if result.returncode == 0:
            processes.append(proc)
    return processes
```

---

## Storage (SSOT)

Panel state stored centrally:

```python
# In central config
server_panel = {
    "unlocked": False
}
```

---

## Implementation Notes

**Files to modify:**
- `src/gui/main_frame.py` - Add server control panel near connect button
- `src/audio/osc_bridge.py` - Add freeAll and reboot methods, improve connect detection
- `src/config/__init__.py` - Add server_panel state

**OSC messages to SC:**

```python
# s.freeAll equivalent
client.send_message("/noise/server/freeall", [])

# s.reboot equivalent  
client.send_message("/noise/server/reboot", [])
```

**SC handlers needed:**
```supercollider
OSCdef(\serverFreeAll, {
    s.freeAll;
    "Server: freeAll executed".postln;
}, '/noise/server/freeall');

OSCdef(\serverReboot, {
    s.reboot;
    "Server: rebooting...".postln;
}, '/noise/server/reboot');
```

---

## Visual States

**Connect button states:**
- Disconnected: "Connect SuperCollider"
- Connecting: "Connecting..."
- Connected: "Connected ✓" (or similar)
- Error: Shows specific error message

**Panel states:**
- Locked: 🔓 icon, panel hidden
- Unlocked: 🔒 icon, panel visible

**Button states (when panel open):**
- s.freeAll: Normal / "Clearing..." / Done
- s.reboot: Normal / "Rebooting..." / Done

---

## Edge Cases

**s.freeAll while generators running:**
- Generators stop
- UI state remains (slots still show generators)
- User needs to restart generators or reload

**s.reboot while connected:**
- Connection temporarily lost
- Auto-reconnect after reboot completes?
- Or require manual reconnect?

**Panel left open:**
- No auto-close timeout
- User must click 🔒 to close
- Prevents accidental clicks while keeping access available

---

## Future Enhancements

- Server status display (CPU %, synth count, bus usage)
- Auto-reconnect after reboot
- Confirmation dialog for s.reboot
- Log panel showing SC messages
