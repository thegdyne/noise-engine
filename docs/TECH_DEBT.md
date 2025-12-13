# Technical Debt

Issues to address, roughly prioritised.

---

## Critical

*No critical issues.*

---

## High Priority

### Automated Tests ✓ RESOLVED
~~The `test_*.py` files are manual visual tests, not pytest. Zero automated coverage.~~

**Fix:** Added `tests/` directory with 93 pytest tests covering:
- Config loading and constants validation
- Generator JSON parsing and structure
- Value mapping edge cases (linear, exponential, inversion)
- OSC path consistency between Python and SuperCollider

Run with: `pytest` or `python -m pytest tests/`

### Print Debugging (31 statements) ✓ RESOLVED
~~Production code has `print()` scattered throughout.~~

**Fix:** Replaced with Python `logging` module via `src/utils/logger.py`. In-App Console implemented in `src/gui/console_panel.py`.

### Hardcoded Paths in Scripts
`~/repos/noise-engine` hardcoded in:
- `tools/ssot.sh`
- `tools/_check_ssot.sh`
- `tools/_update_ssot_badge.sh`
- `tools/update_from_claude.sh`

**Risk:** Won't work if someone clones to different location.

**Fix:** Use `$SCRIPT_DIR` relative paths or detect repo root from git.

---

## Medium Priority

### generator_slot.py is 558 lines
Does too much. Mixed UI and logic.

**Fix:** Split into:
- `generator_slot_ui.py` (layout/widgets)
- `generator_slot_logic.py` (state management)

### WIP Features Visible
Mod Sources and Mixer are visible but greyed out. Looks broken.

**Options:**
1. Hide completely until working
2. Finish them
3. Keep as-is (current choice)

### No Preset System
Can't save/load patches. #1 user expectation for a synth.

**Fix:** JSON preset files. See FUTURE_IDEAS.md.

---

## Low Priority

### No Error Recovery for OSC
Heartbeat detects SC crash but recovery is manual (click Reconnect).

**Fix:** Auto-reconnect with backoff, or clearer UI guidance.

### SC Bus Exhaustion
Re-running init.scd without server reboot leaks buses until crash.

**Fix:** Add cleanup/free in init.scd, or document "reboot server between runs".

---

## Tracking

| Issue | Status | Fixed In |
|-------|--------|----------|
| Bare excepts | ✓ Fixed | All use `except Exception as e:` or specific types |
| No tests | ✓ Fixed | tests/ directory with 93 pytest tests |
| Print debugging | ✓ Fixed | src/utils/logger.py |
| Hardcoded paths | Open | |
| generator_slot.py size | Open | |
| WIP features visible | Open | |
| No presets | Open | |
| OSC error recovery | Open | |
| SC bus exhaustion | Open | |
