---
feature: Pack System
spec: docs/PACK_SYSTEM_SPEC.md
status: approved
author: Gareth
created: 2025-12-18
approved_date: 2025-12-18
---

# Pack System Rollout Plan

**Spec:** `docs/PACK_SYSTEM_SPEC.md`

---

## Phase 1: Infrastructure (No UI)

**Goal:** Pack discovery and loading without UI changes

**Tasks:**
- [ ] Create `packs/` directory with `_template/`
- [ ] Create `src/config/packs.py` with discovery logic
- [ ] Validate manifests (pack_format, name, generators)
- [ ] Load pack generators into GENERATOR_CONFIGS
- [ ] Add pack info to each generator config

**Tests:**
| Test | Expected | Status |
|------|----------|--------|
| No packs directory exists | Core only, no errors | ⬜ |
| Valid manifest.json | Pack discovered, generators loaded | ⬜ |
| Invalid manifest (missing name) | Warning logged, pack skipped | ⬜ |
| Missing .scd file | Warning logged, generator skipped | ⬜ |
| Duplicate synthdef symbol | Warning logged, second skipped | ⬜ |

**Exit Criteria:**
- [ ] All Phase 1 tests pass
- [ ] Existing tests still pass (207+)
- [ ] App starts with packs in `packs/` directory

---

## Phase 2: Pack Selector UI

**Goal:** Dropdown to select pack, filters generator dropdowns

**Depends on:** Phase 1 complete

**Tasks:**
- [ ] Add `PackSelector` widget to toolbar
- [ ] Wire `pack_changed` signal to main_frame
- [ ] Add `set_current_pack()` to config module
- [ ] Add `get_generators_for_pack()` helper
- [ ] Repopulate generator dropdowns on pack change
- [ ] Reset all slots to Empty on pack switch

**Tests:**
| Test | Expected | Status |
|------|----------|--------|
| Startup shows "Core" selected | Default pack is Core | ⬜ |
| Switch Core → Pack | Dropdowns show pack generators only | ⬜ |
| Switch Pack → Core | Dropdowns show core generators only | ⬜ |
| Pack switch resets slots | All slots show Empty | ⬜ |
| Generator plays after switch | Audio works from pack generator | ⬜ |

**Exit Criteria:**
- [ ] All Phase 2 tests pass
- [ ] All Phase 1 tests still pass
- [ ] Demo-able at ModCaf

---

## Phase 3: Demo Packs

**Goal:** Create 2-3 packs from existing generators

**Depends on:** Phase 2 complete

**Tasks:**
- [ ] Create `packs/classic_synths/` with TB-303, Juno, SH-101, C64
- [ ] Create `packs/808_drums/` with Kick, Snare, Hat, Clap
- [ ] Create `packs/ambient/` with Abyss, Drone, Liminal, etc.
- [ ] Move generator files from core to packs
- [ ] Update GENERATOR_CYCLE to remove moved generators
- [ ] Test all packs load and play

**Tests:**
| Test | Expected | Status |
|------|----------|--------|
| Classic Synths pack loads | 4 generators available | ⬜ |
| 808 Drums pack loads | 4 generators available | ⬜ |
| Ambient pack loads | Generators available | ⬜ |
| Rapid pack switching | No crashes, audio stable | ⬜ |

**Exit Criteria:**
- [ ] All packs work
- [ ] Core still has original generators
- [ ] Ready for demo

---

## Sign-Off

| Phase | Tests Pass | Reviewed | Merged | Date |
|-------|------------|----------|--------|------|
| Phase 1 | ✅ | ✅ | ✅ | 2025-12-18 |
| Phase 2 | ✅ | ✅ | ✅ | 2025-12-18 |
| Phase 3 | ⬜ | ⬜ | ⬜ | |

**Feature Complete:** ⬜
