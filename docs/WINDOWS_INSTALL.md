# Windows Installation Guide

*Noise Engine on Windows 10/11*

---

## Prerequisites

Install these first:

**1. Git**
```powershell
winget install --id Git.Git -e
```
Or download from [git-scm.com](https://git-scm.com/download/win)

**2. Python 3.11+**
```powershell
winget install --id Python.Python.3.11 -e
```
Or download from [python.org](https://www.python.org/downloads/)

> ✅ During install, tick **Add Python to PATH** and **Install launcher**

**3. SuperCollider 3.14+**
```powershell
winget install --id SuperCollider.SuperCollider -e
```
Or download from [supercollider.github.io](https://supercollider.github.io/downloads)

**4. Validate installations** (open a NEW terminal window)
```powershell
py -V
py -3 -m pip -V
git --version
```

---

## Installation

### Using PowerShell (recommended)

```powershell
git clone https://github.com/thegdyne/noise-engine.git
cd noise-engine

py -3 -m venv venv
.\venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks venv activation, run once:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Using Command Prompt

```bat
git clone https://github.com/thegdyne/noise-engine.git
cd noise-engine

py -3 -m venv venv
venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt
```

> ⚠️ **Shell confusion:** `activate.bat` only works in CMD. PowerShell needs `Activate.ps1`. Using the wrong one silently fails—your venv won't activate.

---

## SuperCollider Configuration (Critical)

SuperCollider on Windows requires explicit audio device configuration. Without it, the server exits immediately with **exit code 1**.

### Step 1: Find your audio device name

Open **Windows Sound Settings** (right-click speaker icon → Sounds → Playback tab). Note the exact name of your active output device.

Common examples:
- `Speakers (Realtek(R) Audio)`
- `PA24A (NVIDIA High Definition Audio)`
- `Headphones (USB Audio Device)`

### Step 2: Create/modify your SC config

Before running `init.scd`, the SuperCollider server options must be configured. Create or edit your SC startup file, or add this block at the top of `init.scd`:

```supercollider
// === WINDOWS AUDIO CONFIGURATION ===
// Safe settings for Windows stability
s.options.numAudioBusChannels = 64;      // Lower for stability (default 256 may fail)
s.options.numControlBusChannels = 512;   // Lower for stability (default 4096 may fail)
s.options.memSize = 16384;               // Lower for stability (default 65536 may fail)

// REQUIRED: Set your output device (must match Windows device name exactly)
s.options.outDevice = "Speakers (Realtek(R) Audio)";  // ← Change this to YOUR device

// Optional: Set input device if you have one
// s.options.inDevice = "Microphone (Realtek HD Audio Mic input)";
```

### Step 3: Test the server boots

In SuperCollider IDE, run:
```supercollider
s.boot;
```

If successful, you'll see:
```
Booting server 'localhost' on address 127.0.0.1:57110.
SuperCollider 3 server ready.
```

If it says `Server 'localhost' exited with exit code 1`, see Troubleshooting below.

---

## Running Noise Engine

**1. Start SuperCollider**
- Launch SuperCollider IDE
- Open `supercollider/init.scd`
- Select all (`Ctrl+A`) then evaluate (`Ctrl+Enter`)
- Wait for "✔ Noise Engine ready!" message

**2. Start the GUI** (in a new terminal)

PowerShell:
```powershell
cd noise-engine
.\venv\Scripts\Activate.ps1
python src\main.py
```

Command Prompt:
```bat
cd noise-engine
venv\Scripts\activate.bat
python src\main.py
```

**3. Connect** — Click "Connect to SuperCollider" in the GUI

---

## Troubleshooting

### Server exits with code 1

This is the most common Windows issue. The SC server can't start.

**Checklist:**

| Check | Action |
|-------|--------|
| Audio device set? | `s.options.outDevice = "Your Device Name";` — must match exactly |
| Device name correct? | Copy the **exact** name from Windows Sound Settings |
| Other apps using audio? | Close Steam, Discord, Chrome, Spotify, DAWs |
| Bus/memory too high? | Try `numAudioBusChannels = 16; memSize = 8192;` |
| Port conflict? | Run `netstat -ano | findstr 57110` in PowerShell |

**Minimal safe test** (paste in SC IDE):
```supercollider
s.quit;

s.options.numAudioBusChannels = 16;
s.options.numControlBusChannels = 64;
s.options.memSize = 8192;
s.options.outDevice = "Speakers (Realtek(R) Audio)";  // ← Your device
s.options.inDevice = nil;

s.boot;
```

If this boots, gradually increase the values until you find the limit.

### Can't list audio devices in SC 3.13

SC 3.13.0 doesn't have `ServerOptions.localDevices` or `deviceNames` methods. You **must** manually specify the device name from Windows Sound Settings.

### "MME : ..." vs bare device names

Try different formats if one doesn't work:
```supercollider
s.options.outDevice = "Speakers (Realtek(R) Audio)";        // Option 1
s.options.outDevice = "MME : Speakers (Realtek(R) Audio)";  // Option 2
s.options.outDevice = "WASAPI : Speakers (Realtek(R) Audio)";  // Option 3
```

### venv not activating

**Symptom:** `pip` installs to global Python, not venv.

**Fix:** Make sure your prompt shows `(venv)` at the start:
```
(venv) PS C:\Users\brook\noise-engine>
```

If it doesn't, you're not in the venv. Re-run the activation command.

PowerShell: `.\venv\Scripts\Activate.ps1`  
CMD: `venv\Scripts\activate.bat`

### Check if venv is active
```powershell
python -c "import sys; print(sys.prefix != sys.base_prefix)"
# True = in venv, False = not in venv
```

### PyQt install fails

1. Ensure venv is activated
2. Run `python -m pip install --upgrade pip`
3. If still failing, you may need [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) → select "Desktop development with C++"

---

## Audio Driver Notes

| Driver Type | Latency | Notes |
|-------------|---------|-------|
| ASIO | Lowest | Best choice. Use your interface's native driver or [ASIO4ALL](https://asio4all.org/). Only one app can use ASIO at a time. |
| WASAPI | Low | Built into Windows. Good fallback. |
| MME | Higher | Most compatible but higher latency. |
| DirectSound | Higher | Legacy Windows driver. |

> **Tip:** ASIO drivers are exclusive—close all other audio apps before starting SC.

---

## Optional: PowerShell Shortcuts

Add to your PowerShell profile (`notepad $PROFILE`):

```powershell
function runnoise {
    python "C:\Users\brook\noise-engine\src\main.py"
}

function scinit {
    & "C:\Program Files\SuperCollider-3.13.0\scide.exe" "C:\Users\brook\noise-engine\supercollider\init.scd"
}
```

Create the profile if it doesn't exist:
```powershell
New-Item -Path $PROFILE -ItemType File -Force
```

Reload after editing:
```powershell
. $PROFILE
```

> **Note:** PowerShell `Set-Alias` can't include arguments—use functions instead.

---

## First-Run Notes

- Windows may prompt for network access on first run (Python and scsynth use OSC over localhost). Allow on "Private networks" at minimum.
- SC console can be cleared with `Ctrl+L` or `Post.clear;`
- If SC IDE Post window freezes, restart the IDE.

---

## Quick Reference

| Task | Command |
|------|---------|
| Activate venv (PS) | `.\venv\Scripts\Activate.ps1` |
| Activate venv (CMD) | `venv\Scripts\activate.bat` |
| Deactivate venv | `deactivate` |
| Check venv active | `python -c "import sys; print(sys.prefix != sys.base_prefix)"` |
| Clear SC console | `Ctrl+L` or `Post.clear;` |
| Quit SC server | `s.quit;` |
| Boot SC server | `s.boot;` |
| Check port in use | `netstat -ano \| findstr 57110` |
| Kill process by PID | `taskkill /PID 1234 /F` |

---

*See also: [README.md](../README.md) for general documentation*
