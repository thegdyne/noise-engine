# Noise Engine — Plan to 100%

## Current: 82%

---

## Phase A: Imaginarium Detail Layer (→ 88%)
**Effort:** 4-5 sessions | **Impact:** +6%

| Session | Deliverable |
|---------|-------------|
| 1 | `DETAIL_LAYER_SPEC.md` — Define 10 techniques, allocation rules, budget system |
| 2 | Implement 5 core techniques (sub, dust, drift, shimmer, beat) |
| 3 | Implement 5 remaining techniques (growl, ghost, swarm, breath, ping) |
| 4 | SC code generation, integration with method templates |
| 5 | Testing, tuning, A/B comparison vs non-detail packs |

**Outcome:** Generated packs have R'lyeh-level richness and movement.

---

## Phase B: Preset Expansion (→ 92%)
**Effort:** 2-3 sessions | **Impact:** +4%

| Session | Deliverable |
|---------|-------------|
| 1 | Channel EQ + BPM in schema, get/set methods |
| 2 | Master section (EQ, compressor, limiter) in schema |
| 3 | Mod sources + mod routing in schema, round-trip tests |

**Spec:** `PRESET_EXPANSION_SPEC.md` (frozen, ready)

**Outcome:** Full session state save/restore including modulation.

---

## Phase C: FX System v1.1 (→ 94%)
**Effort:** 1-2 sessions | **Impact:** +2%

| Task | Effort |
|------|--------|
| State sync on reconnect (`_sync_master_state()`) | 1 hr |
| Refactor hardcoded OSC paths to `OSC_PATHS` | 1 hr |
| Fix LR4 comment/implementation mismatch | 30 min |

**Outcome:** FX system robust to reconnects, SSOT compliance.

---

## Phase D: Mopup (→ 96%)
**Effort:** 1 session | **Impact:** +2%

| Task | Effort |
|------|--------|
| UI font audit | 1 hr |
| Empty mod state polish | 30 min |
| CWD-independent path resolution | 30 min |
| Generator type button width (120-140px) | 15 min |
| OSC shutdown race condition fix | 30 min |

**Outcome:** Polish and edge cases cleaned up.

---

## Phase E: Cross-Platform (→ 98%)
**Effort:** 2-3 sessions | **Impact:** +2%

**Blocked on:** Recruiting Windows/Linux testers

| Task | Owner |
|------|-------|
| Recruit Windows tester | Discord |
| Recruit Linux tester | Discord |
| Document platform-specific setup | You |
| Test + fix issues | You + testers |
| Create install guides | You |

**Outcome:** Noise Engine runs on Windows and Linux.

---

## Phase F: Needs Spec Features (→ 100%)
**Effort:** 6-8 sessions | **Impact:** +2%

| Feature | Effort | Priority |
|---------|--------|----------|
| MIDI Learn | 3-4 sessions | Medium |
| SC State Sync on Restart | 1-2 sessions | Low |
| Integration Tests | 1-2 sessions | Low |
| Mod Matrix Expansion | 2-3 sessions | Low |

**Outcome:** Full feature set, production-grade testing.

---

## Timeline Summary

| Phase | Sessions | Cumulative % |
|-------|----------|--------------|
| Current | — | 82% |
| A: Detail Layer | 5 | 88% |
| B: Preset Expansion | 3 | 92% |
| C: FX v1.1 | 2 | 94% |
| D: Mopup | 1 | 96% |
| E: Cross-Platform | 3 | 98% |
| F: Needs Spec | 6 | 100% |

**Total: ~20 sessions to 100%**

---

## Recommended Order

```
Detail Layer → Preset Expansion → FX v1.1 → Mopup → Cross-Platform → MIDI Learn
     ↑
  START HERE (biggest quality impact)
```

---

## Ideas (Not in 100% scope)

These are nice-to-haves, not required for "complete":

- Keyboard Mode (CMD+K)
- Filter improvements (ladder, MS-20)
- Eurorack send/return
- Generator waveform display
- Per-generator transpose
- Multitimbral mode
- Web-based manual
- MASTER MUTE / REMOVE MASTER FX buttons

---

## Success Definition

**100% = A complete, cross-platform modular synthesizer with:**
- Image-to-sound pack generation (with detail layer polish)
- Full session state presets
- MIDI learn
- Robust FX system
- Windows/Linux support
- Integration test coverage
