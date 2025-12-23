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
Or download from [python.org](https://www.python.org/downloads/) — tick "Add Python to PATH" during install.

**3. SuperCollider 3.14+**
```powershell
winget install --id SuperCollider.SuperCollider -e
```
Or download from [supercollider.github.io](https://supercollider.github.io/downloads)

> **Audio note:** For best latency, use an ASIO driver (your interface's native driver, or [ASIO4ALL](https://asio4all.org/)). WASAPI works but may have higher latency.

---

## Installation

Open PowerShell and run:

```powershell
git clone https://github.com/thegdyne/noise-engine.git
cd noise-engine

py -3 -m venv venv
.\venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks venv activation:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## Running Noise Engine

**1. Start SuperCollider**
- Launch SuperCollider IDE
- Open `supercollider\init.scd`
- Select all (`Ctrl+A`) then evaluate (`Ctrl+Enter`)

**2. Start the GUI** (in a new PowerShell window)
```powershell
cd noise-engine
.\venv\Scripts\Activate.ps1
python src\main.py
```

Click "Connect to SuperCollider" in the GUI. You're ready to make noise.

---

## First-Run Notes

Windows may prompt for network access on first run (Python and/or scsynth use OSC over localhost). Allow on "Private networks" at minimum.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| PyQt install fails | Ensure venv is activated; run `python -m pip install --upgrade pip` |
| PowerShell won't activate venv | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| No sound / high latency | Switch SuperCollider to ASIO driver; check Windows sound settings |
| `py` command not found | Use `python` instead, or reinstall Python with PATH option |

---

## Optional: PowerShell Shortcuts

Add to your PowerShell profile (`notepad $PROFILE`):

```powershell
function noise-env { Set-Location "$HOME\repos\noise-engine"; . .\venv\Scripts\Activate.ps1 }
function noise { noise-env; python src\main.py }
```

Then just type `noise` to launch.

---

## CMD Alternative

If you prefer Command Prompt over PowerShell:

```bat
cd noise-engine
venv\Scripts\activate.bat
python src\main.py
```

---

*See also: [README.md](../README.md) for general documentation*
