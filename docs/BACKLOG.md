# Noise Engine Backlog

*Updated: December 20, 2025*

---

## Now
- [ ] Cross-Platform Testing — Windows & Linux compatibility

## Next (spec approved, ready to plan)
- [ ] Integration Tests — tests that boot SuperCollider

---

## Cross-Platform Testing

**Goal:** Ensure Noise Engine runs on Windows and Linux, not just macOS.

**Tasks:**
- [ ] Recruit Windows tester (Discord?)
- [ ] Recruit Linux tester (Discord?)
- [ ] Document platform-specific setup (SC paths, Python env)
- [ ] Test PyQt5 rendering on Windows
- [ ] Test PyQt5 rendering on Linux (X11/Wayland)
- [ ] Verify OSC communication works cross-platform
- [ ] Check file paths (presets dir, pack loading)
- [ ] Create Windows install guide
- [ ] Create Linux install guide

**Known Risks:**
- SuperCollider paths differ per OS
- Audio device APIs vary (CoreAudio vs WASAPI vs ALSA/Jack)
- Font rendering may differ
- Keyboard shortcuts (Cmd vs Ctrl)

---

## Needs Spec (Large/Medium)
- [ ] MIDI Learn
- [ ] Mod Matrix Expansion
- [ ] SC State Sync on Restart

---

## Mopup (Small — just do it)
- [ ] UI font audit — improve visibility across all labels
- [ ] Empty mod state polish
- [x] MATRIX button on main UI + ENGINE return button (Dec 20)
- [ ] Preset overwrite confirmation — show "Overwrite / Save As New / Cancel" when saving with existing name

---

## Ideas (not committed)
- Keyboard Mode (CMD+K)
- Imaginarium natural language interface
- Filter improvements (ladder, MS-20, etc)
- Eurorack send/return
- Generator waveform display
- Performance profiling
- Per-generator transpose
- Multitimbral mode

---

## Done (recent)
- ✅ Preset System v2 — Full session state including channel EQ, BPM, master, mod sources, mod routing (Dec 20)
- ✅ Generator Envelope Compliance — All 16 pack generators fixed (Dec 20)
- ✅ Doc Reorganization — archive/, ideas/, demos/ (Dec 20)
- ✅ Pack System — Phase 1-3 complete
- ✅ FX System v1 — Inline FX strip with HEAT, ECHO, REVERB, FILTER
- ✅ TURBO presets (INI/T1/T2) for all FX modules
- ✅ Channel strips (volume, pan, mute, solo, EQ)
- ✅ Master section (fader, meters, EQ, compressor, limiter)
- ✅ Mod Matrix — 16×40 routing grid
- ✅ Mod Sources — LFO + Sloth
- ✅ 53 generators total
- ✅ CI/CD pipeline (280 tests)

---

## Web-Based Manual
- [ ] Create documentation website for Noise Engine
- Consider: GitHub Pages, MkDocs, or simple HTML
- Sections: Getting started, Generators, Packs, Modulation, MIDI, API reference
- Include screenshots, audio examples
- Auto-generate generator list from pack manifests

## FX System v1.1
- [ ] P1: State sync on reconnect - create _sync_master_state() method
- [ ] P2: fx_window.py uses hardcoded OSC paths - refactor to use OSC_PATHS
- [ ] P2: master_passthrough LR4 comment doesn't match implementation

## FX System Future
- [ ] Per-channel echo/verb send knobs in mixer strip
- [ ] Reverb pre-delay parameter
- [ ] FX audio tuning (adjust default values, ranges, response curves)

## Preset Backward Compatibility
**Problem:** Loading old v1 presets resets mod sources/routing to defaults, wiping current setup.
**Solution options:**
1. Only apply sections that were explicitly in the preset JSON (check key existence)
2. Add `saved_sections` list to preset metadata
3. Version-based logic: v1 presets skip mod_sources/mod_routing apply

**Tests needed:**
- [ ] Load v1 preset (no mod_sources) → mod state unchanged
- [ ] Load v1 preset (no mod_routing) → routing unchanged  
- [ ] Load v1 preset (no master) → master section unchanged
- [ ] Load v2 preset with all sections → all applied
- [ ] Round-trip: save v2, load v2 → exact match

## Preset Migration System
**Problem:** Schema changes can break or partially load old presets.
**Solution:** Automatic preset migration on app start or first load.

**Design:**
1. Detect presets with `version < PRESET_VERSION`
2. Backup to `presets/backup_v{old_version}/` before migration
3. Apply sequential migrations: v1→v2→v3 etc.
4. Each migration adds missing fields with sensible defaults
5. Update version number after migration
6. Log all migrations for user transparency

**Migration rules:**
- v1→v2: Add bpm=120, master={defaults}, mod_sources={empty}, mod_routing={empty}
- Future: v2→v3 migrations as needed

**User flow:**
- On load, if preset.version < current: show "Migrating X presets..." toast
- Backup folder preserves originals
- Migration is non-destructive (originals in backup)

**Tasks:**
- [ ] Create `migrate_preset(data: dict, from_version: int) -> dict`
- [ ] Create backup directory on first migration
- [ ] Add migration log to preset metadata
- [ ] Test v1→v2 migration
- [ ] Consider CLI tool: `python -m presets.migrate --dry-run`

## OSC: Remove CWD-dependent path resolution
**Problem:** OSC route registration uses relative paths, breaks when pytest runs from non-root CWD.
**Current workaround:** `tests/conftest.py` forces `os.chdir(ROOT)` at session start + provides fixtures.

**Proper fix:**
1. Create `src/utils/project_root.py`:
```python
import os
from pathlib import Path

def project_root() -> Path:
    """Resolve repo root independent of CWD."""
    env = os.getenv("NOISE_ENGINE_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]
```

2. Find all CWD-relative paths:
```bash
rg -n 'Path\("|open\(|\.exists\(\)|\.is_file\(\)' src/osc src/config
```

3. Replace relative paths with `ROOT / "..."`:
```python
# Before
Path("supercollider/generators").exists()
# After
(ROOT / "supercollider" / "generators").exists()
```

4. Core mixer routes (mute/solo/volume) should register unconditionally - only gate discovery/file-based routes on filesystem checks.

**Acceptance criteria:** pytest passes from repo root, `tests/`, and `/tmp` WITHOUT conftest.py `os.chdir()` workaround.

**Remove after fix:**
- `os.chdir(ROOT)` from `tests/conftest.py`
- Keep fixtures (they're still useful)
