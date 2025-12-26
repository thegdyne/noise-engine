# Linux Installation Guide

> **Tested on:** Fedora 39/40  
> **Status:** Linux audio setup varies by distro and desktop environment.

---

## Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Usually pre-installed |
| SuperCollider | 3.13+ | 3.14 recommended |
| Audio | JACK or PipeWire | Distro-dependent |

---

## 1. Python Environment

Most Linux distros include Python 3.11+. Verify:

```bash
python3 --version
```

Install pip and venv if needed:

```bash
# Fedora (tested)
sudo dnf install python3-pip python3-virtualenv

# Debian/Ubuntu
sudo apt install python3-pip python3-venv

# Arch
sudo pacman -S python-pip python-virtualenv
```

---

## 2. SuperCollider

**⚠️ Important:** Distro packages are often outdated. Check the version before installing.

### Option A: Distro Package (if version ≥ 3.13)

```bash
# Fedora (recommended — tested, usually current)
sudo dnf install supercollider supercollider-sc3-plugins

# Debian/Ubuntu — check version first!
apt-cache policy supercollider
sudo apt install supercollider

# Arch (usually current)
sudo pacman -S supercollider
```

### Option B: Build from Source (recommended for latest)

See official instructions:  
**https://github.com/supercollider/supercollider/blob/develop/README_LINUX.md**

### Option C: Flatpak (sandboxed, may have audio limitations)

```bash
flatpak install flathub org.supercollider.SuperCollider
```

### Verify Installation

```bash
sclang -v
# Should show 3.13.0 or higher
```

---

## 3. Audio Setup

SuperCollider needs a working audio backend. This varies by distro and desktop.

### PipeWire (Ubuntu 22.04+, Fedora 34+, most modern distros)

PipeWire often works out of the box. Test with:

```bash
scsynth -u 57110
# Should start without errors
```

If SC complains about JACK, install the JACK compatibility layer:

```bash
# Fedora (tested)
sudo dnf install pipewire-jack-audio-connection-kit

# Debian/Ubuntu
sudo apt install pipewire-jack
```

### JACK (traditional, more control)

```bash
# Fedora
sudo dnf install jack-audio-connection-kit qjackctl

# Debian/Ubuntu
sudo apt install jackd2 qjackctl

# Arch
sudo pacman -S jack2 qjackctl
```

Start JACK before running Noise Engine:

```bash
qjackctl &
# Click "Start" in QjackCtl
```

### Troubleshooting Audio

| Problem | Solution |
|---------|----------|
| "Could not open audio device" | Check JACK/PipeWire is running |
| Crackling/dropouts | Increase buffer size in JACK settings |
| No sound | Verify output routing in qjackctl/pavucontrol |
| Permission denied | Add user to `audio` group: `sudo usermod -aG audio $USER` |

---

## 4. Install Noise Engine

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/noise-engine.git
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

## Quick Troubleshooting

| Issue | Check |
|-------|-------|
| SC won't start | Run `scsynth -u 57110` manually to see errors |
| "sclang not found" | Add SC to PATH or install properly |
| PyQt5 issues | `pip install PyQt5` or use distro package |
| GUI looks wrong | Install Qt theme: `sudo dnf install qt5-qtbase` (Fedora) |

---

## Distro-Specific Notes

### Fedora (Tested)

Fedora typically has current SC packages and PipeWire works out of the box.

```bash
# Full install (one-liner)
sudo dnf install supercollider supercollider-sc3-plugins python3-pip python3-virtualenv pipewire-jack-audio-connection-kit
```

**Audio on Fedora:**
- PipeWire is default since Fedora 34
- Usually works without configuration
- If issues, check with: `pw-cli info all`

### Ubuntu / Debian
- SC in repos is often outdated — check version before installing
- May need to build from source for SC 3.13+
- PipeWire is default on Ubuntu 22.04+

### Arch / Manjaro
- SC package is typically current
- `supercollider` package includes everything needed

### NixOS
- SC available in nixpkgs
- Audio setup requires specific configuration

---

## Resources

- **SuperCollider Linux README:** https://github.com/supercollider/supercollider/blob/develop/README_LINUX.md
- **SC Linux Build Guide:** https://supercollider.github.io/development/building-linux
- **PipeWire + JACK:** https://pipewire.org/
- **JACK Audio:** https://jackaudio.org/

---

*Last updated: 2025-12-26*
