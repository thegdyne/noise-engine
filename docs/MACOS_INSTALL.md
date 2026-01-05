# macOS Installation Guide

> **Tested on:** macOS Sonoma / Ventura  
> **Method:** One-Click Launch (Phase 1 Portable)

---

## Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Via Homebrew or python.org |
| SuperCollider | 3.13+ | 3.14 recommended |
| macOS | 12+ | Monterey or later |

---

## 1. Install Homebrew (if needed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## 2. Install SuperCollider

### Option A: Homebrew (recommended)

```bash
brew install --cask supercollider
```

### Option B: Direct Download

Download from: https://supercollider.github.io/downloads

Install the `.dmg` and drag to Applications.

---

## 3. Install Python

### Option A: Homebrew (recommended)

```bash
brew install python@3.11
```

### Option B: python.org

Download from: https://www.python.org/downloads/

---

## 4. Install Noise Engine

```bash
# Clone repository
git clone https://github.com/thegdyne/noise-engine.git
cd noise-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 5. Make Launchers Executable

```bash
chmod +x tools/Run_NoiseEngine.command tools/ne-run tools/ne-py tools/test-launcher.sh
```

If macOS blocks execution (quarantine from download), run:

```bash
xattr -dr com.apple.quarantine tools/Run_NoiseEngine.command tools/ne-run tools/ne-py tools/test-launcher.sh
```

---

## 6. Launch Noise Engine

### Option A: Double-Click (Non-Technical)

In Finder, double-click:

```
noise-engine/tools/Run_NoiseEngine.command
```

This:
1. Opens SuperCollider
2. Loads the bootstrap script
3. Selects audio device (if configured)
4. Loads init.scd
5. Starts Python GUI automatically

### Option B: Terminal (Power Users)

```bash
./tools/ne-run
```

This:
1. Clears any stale ready state
2. Opens SuperCollider with bootstrap
3. Waits for SC to signal READY (up to 20s)
4. Starts Python GUI

---

## 7. Connect

In the Noise Engine GUI, click **"Connect to SuperCollider"**. The status indicator should turn green.

---

## Audio Setup

macOS Core Audio works out of the box.

### Selecting Audio Device

A config file is created on first launch:

```
~/Library/Application Support/NoiseEngine/config.scd
```

Edit to set your device (exact name required):

```supercollider
(
  device: "MOTU M6",           // Your device name here
  bootTimeoutSec: 15,
  autoPython: true,
  pythonCmd: "cd /path/to/noise-engine && ./tools/ne-py",
  writeReadyFile: true
)
```

To find your device name, in SuperCollider run:

```supercollider
ServerOptions.devices.do(_.postln);
```

### Aggregate Devices

For multi-output setups, create an Aggregate Device in **Audio MIDI Setup.app**.

---

## Verify Installation

```bash
./tools/test-launcher.sh
```

Should output:
```
PASS: ready.json exists and status is ready
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| .command file blocked | `xattr -dr com.apple.quarantine tools/Run_NoiseEngine.command` |
| SC won't start | Check Security & Privacy settings — may need to allow SC |
| "sclang not found" | Add to PATH: `export PATH="/Applications/SuperCollider.app/Contents/MacOS:$PATH"` |
| No sound | Check device setting in config.scd; verify System Settings → Sound |
| PyQt5 import error | `pip install PyQt5` in your venv |
| venv not found | Run `python3 -m venv venv && pip install -r requirements.txt` |
| Device not found | Check exact spelling; run `ServerOptions.devices.do(_.postln)` |

### Gatekeeper Issues

If macOS blocks SuperCollider:

```bash
xattr -cr /Applications/SuperCollider.app
```

Or allow in System Settings → Privacy & Security.

### Checking Status

```bash
cat ~/Library/Application\ Support/NoiseEngine/state/ready.json
```

---

## Files Written to User Directory

| File | Purpose |
|------|---------|
| `~/Library/Application Support/NoiseEngine/config.scd` | User settings |
| `~/Library/Application Support/NoiseEngine/state/ready.json` | Ready handshake |

---

## Shell Alias (Optional)

Add to `~/.zshrc`:

```bash
alias noise="cd ~/repos/noise-engine && ./tools/ne-run"
```

Then just type `noise` to launch.

---

## Quick Reference

```bash
# Full setup after Homebrew
brew install --cask supercollider && brew install python@3.11

# First-time setup
cd noise-engine
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
chmod +x tools/Run_NoiseEngine.command tools/ne-run tools/ne-py

# Daily launch
./tools/ne-run
# or double-click tools/Run_NoiseEngine.command
```

---

*Last updated: 2025-01-04*
