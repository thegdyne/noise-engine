---
status: approved
version: 0.2.3
platform: macOS (Phase 1 portable)
date: 2025-01-04
---

# One-Click Launch Specification

## Goal

Reduce Noise Engine startup to **one action** while remaining:
- **Non-destructive** — doesn't overwrite user's existing SuperCollider setup
- **Predictable** — no surprise audio unless configured
- **Recoverable** — easy to disable
- **Diagnosable** — clear logs + ready.json state file

---

## Success Criteria

| ID | Pass Condition |
|----|----------------|
| A1 | User can launch full stack from single action |
| A2 | SC boots, loads init, prints `NoiseEngine: READY` |
| A3 | Audio device configurable via config file |
| A4 | Missing device prints list + continues with default |
| A5 | Python auto-launch controlled by config |
| A6 | Init is safe to run multiple times |
| A7 | Works even if SC IDE already open |

---

## Architecture

### Two Supported Modes

**Mode A — Portable (Phase 1 default)**

No system edits. Launcher opens bootstrap file directly.

**Mode B — Installed Hook (Phase 2)**

`startup.scd` loads bootstrap on every SC launch. Sets `~NOISE_ENGINE_HOOK = true` to disable autoPython.

---

## User Flows

### Double-Click (Non-Technical)

1. Double-click `tools/Run_NoiseEngine.command`
2. SC opens → bootstrap runs → init loads → Python auto-starts
3. Click "Connect to SuperCollider" in GUI

### Terminal (Power User)

```bash
./tools/ne-run
```

1. Clears stale ready.json
2. Opens SC with bootstrap
3. Waits for ready.json (up to 20s)
4. Starts Python

### Hook Mode (Phase 2)

SC always loads NE on launch. autoPython forced off to prevent surprise Python windows.

---

## File Layout

```
~/Library/Application Support/
└── NoiseEngine/
    ├── config.scd              # User settings
    └── state/
        └── ready.json          # Ready handshake

noise-engine/
├── supercollider/
│   ├── bootstrap/
│   │   └── noise_engine_startup.scd
│   └── init.scd
└── tools/
    ├── Run_NoiseEngine.command  # Double-click launcher
    ├── ne-run                   # Terminal launcher (SC + wait + Python)
    ├── ne-py                    # Python-only runner
    └── test-launcher.sh         # Verification script
```

---

## Component Specifications

### 1. Bootstrap — `supercollider/bootstrap/noise_engine_startup.scd`

**Responsibilities:**
- Resolve repo root
- Load/create config at fixed OS location
- Set audio device (fallback to default if missing)
- Boot server (or reuse running)
- Load init.scd
- Write ready.json
- Optionally launch Python (via ne-py)

**Output Contract:**
- `NoiseEngine: READY` — success
- `NoiseEngine: init already loaded; skipping` — repeat load
- `NoiseEngine: requested device not found` — device missing
- `NoiseEngine: using default device` — fallback
- `NoiseEngine: python launch FAILED` — Python error
- `NoiseEngine: boot timeout` — SC didn't boot in time

### 2. Config — `~/Library/Application Support/NoiseEngine/config.scd`

```supercollider
(
  device: nil,              // e.g. "MOTU M6"
  bootTimeoutSec: 15,
  autoPython: true,         // Portable default
  pythonCmd: "cd /path && ./tools/ne-py",
  writeReadyFile: true
)
```

### 3. Launchers

| Script | Purpose |
|--------|---------|
| `Run_NoiseEngine.command` | Double-click: opens SC with bootstrap |
| `ne-run` | Terminal: opens SC, waits for ready, starts Python |
| `ne-py` | Python-only: used by bootstrap's pythonCmd |

### 4. Init Idempotency

Init wrapped with guard:
```supercollider
~noiseEngine = ~noiseEngine ? ();
if (~noiseEngine[\initDone] == true) {
    "NoiseEngine: init already loaded; skipping".postln;
} { ... };
```

---

## Edge Cases

| Case | Behavior |
|------|----------|
| E1: Device missing | Print list, continue with default |
| E2: SC already running | Skip boot, load init |
| E3: Init already loaded | Skip (guard) |
| E4: Python fails | Warn, SC continues |
| E5: No config | Create default |
| E6: venv missing | Print fix instructions, exit 1 |
| E7: Stale ready.json | ne-run deletes before launching |

---

## Phase Roadmap

### Phase 1 — macOS Portable (Complete)
- [x] Bootstrap script
- [x] Run_NoiseEngine.command
- [x] ne-run with ready-wait
- [x] ne-py for bootstrap
- [x] test-launcher.sh
- [ ] Init idempotency wrap (manual edit)

### Phase 2 — Hook Installer
- [ ] setup-launcher.sh
- [ ] uninstall-launcher.sh
- [ ] startup.scd hook with backup

### Phase 3 — Python Auto-Connect
- [ ] Python reads ready.json
- [ ] Removes "Connect to SC" click

### Phase 4 — Cross-Platform
- [ ] Windows PowerShell launcher
- [ ] Linux .desktop file

---

## Key Design Decisions

| Decision | Resolution |
|----------|------------|
| autoPython default | **true** in portable mode (one-click) |
| Hook mode Python | **disabled** (prevents surprise) |
| Terminal launcher | Opens SC + waits + Python (Option B) |
| pythonCmd target | ne-py (no recursion) |
| Stale state handling | Delete ready.json before launch |

---

*Consolidated from AI1/AI2 review sessions 2025-01-04*
