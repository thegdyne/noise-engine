# Noise Engine Backlog

*Single source of truth for what to work on.*

---

## Now

**Presets System** — users can't save work, nothing else matters

- [ ] Define preset JSON schema (generator types + all param values)
- [ ] Save preset to file
- [ ] Load preset from file
- [ ] Wire up UI (save button, load button, file picker)

Scope: JSON files in a folder. No browser, no categories, no cloud.

---

## Next

- [ ] Integration tests that boot SC (smoke test, envelope test, mod routing test)
- [ ] Generator Envelope Compliance — Phase 2: CI enforcement (`~envVCA` test)
- [ ] Pack System — Phase 3: Preset Integration

---

## Tech Debt

| Issue | Priority | Notes |
|-------|----------|-------|
| Hardcoded paths in tools/*.sh | Medium | Use `$SCRIPT_DIR` or git root detection |
| WIP features visible (greyed out) | Low | Hide completely or finish |
| No OSC error recovery | Low | Auto-reconnect with backoff |
| SC bus exhaustion on reinit | Low | Add cleanup or document workaround |

---

## Small Fixes (Just Do It)

- [ ] Selector box width — widen for long generator names
- [ ] UI font audit — improve visibility across all labels
- [ ] Review mixer section for button sizing issues

---

## Done (Recent)

- ✅ Generator Envelope Compliance — Phase 1 (all 16 pack generators fixed)
- ✅ Pack System — Phase 1 & 2
- ✅ FX System v1 — HEAT, ECHO, REVERB, FILTER modules
- ✅ Quadrature modulation (4 outputs per mod slot)
- ✅ Channel strips + Master section
- ✅ CI/CD pipeline (207 tests)
- ✅ Layout debug tools (F9 toggle)
- ✅ In-app console logging

---

## Parked (Needs Presets First)

These are blocked until presets ship:

- MIDI Learn (needs parameter IDs)
- Recording (nice to have, not blocking)
- Output Assignment (nice to have, not blocking)

---

## References

Ideas and future dreams moved to `docs/ideas/`. Completed specs moved to `docs/archive/`.
