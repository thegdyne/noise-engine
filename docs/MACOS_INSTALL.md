# macOS Installation Guide

> **Tested on:** macOS Sonoma / Ventura  
> **Method:** Homebrew + Python venv

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

### Verify Installation

```bash
# Check sclang is available
/Applications/SuperCollider.app/Contents/MacOS/sclang -v
```

---

## 3. Install Python

### Option A: Homebrew (recommended)

```bash
brew install python@3.11
```

### Option B: python.org

Download from: https://www.python.org/downloads/

### Verify Installation

```bash
python3 --version
# Should show 3.11 or higher
```

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

## 5. Run

```bash
# Activate environment (if not already)
source venv/bin/activate

# Start Noise Engine
python main.py
```

The app will start SuperCollider automatically. Watch the status indicator in the header — it should turn green when connected.

---

## Audio Setup

macOS Core Audio works out of the box. No additional configuration needed.

### Selecting Audio Device

SuperCollider uses the system default audio device. To change:

1. Open **System Settings → Sound**
2. Select your preferred output device
3. Restart Noise Engine

### Aggregate Devices (Advanced)

For multi-output setups, create an Aggregate Device in **Audio MIDI Setup.app**.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "sclang not found" | Add to PATH: `export PATH="/Applications/SuperCollider.app/Contents/MacOS:$PATH"` |
| SC won't start | Check Security & Privacy settings — may need to allow SC |
| No sound | Verify output device in System Settings → Sound |
| PyQt5 import error | `pip install PyQt5` in your venv |
| Permission denied | Run `xattr -cr /Applications/SuperCollider.app` to clear quarantine |

### Gatekeeper Issues

If macOS blocks SuperCollider:

```bash
# Clear quarantine flag
xattr -cr /Applications/SuperCollider.app

# Or allow in System Settings → Privacy & Security
```

---

## Quick Reference

```bash
# Full setup (one-liner after Homebrew)
brew install --cask supercollider && brew install python@3.11

# Run Noise Engine
cd noise-engine
source venv/bin/activate
python main.py
```

---

*Last updated: 2025-12-26*
