# Dual-AI Development Workflow

A systematic process for feature development using two Claude sessions (AI1 and AI2) to ensure quality through iterative review and agreement.

---

## Overview

This workflow separates concerns between two AI sessions:
- **AI1** — Primary development session (spec creation, implementation, documentation)
- **AI2** — Review and validation session (fresh perspective, catches blind spots)

The human developer orchestrates the flow, carrying context between sessions via zip uploads and copy/paste of key artifacts.

---

## The Process (14 Steps + 2 Substeps)

### Phase A: Specification

| Step | Session | Action | Output |
|------|---------|--------|--------|
| 1 | AI1 | Create feature specification | `FEATURE_SPEC.md` |
| 2 | AI1 ↔ AI2 | Cross-validate and freeze spec | `FEATURE_SPEC.md` (FROZEN) |

**Step 1 — Spec Creation (AI1)**
- Define feature requirements as `R1..Rn`
- Define edge cases as `E1..En`
- Include constraints, success criteria, and "not in scope"
- Reference existing architecture (DECISIONS.md, BLUEPRINT.md)

**Step 2 — Spec Agreement & Freeze (AI1 ↔ AI2)**
- Upload spec to AI2 for fresh-eyes review
- AI2 identifies gaps, contradictions, or missing considerations
- Iterate until both sessions agree

**Freeze output:**
```
Scope: [feature name / branch]
FrozenAt: [YYYY-MM-DD]
Hash: [commit SHA or zip name]
Approvals: AI1 ✓ AI2 ✓
```

**Change control (post-freeze only):** Any spec change requires:
```
CHANGE REQUEST
- reason:
- spec impact: [R# affected]
- test impact: [tests affected]
- docs impact:
- approval: AI1 ✓ AI2 ✓
```

---

### Phase B: Implementation

| Step | Session | Action | Output |
|------|---------|--------|--------|
| 3 | AI1 | Create phased rollout plan | `FEATURE_ROLLOUT.md` |
| 4 | AI1 | Implement Phase N | PR/commit + implementation notes |
| 4b | AI2 | Review Phase N | Issues list + accept/reject |

*Steps 4 ↔ 4b repeat for each rollout phase*

**Step 3 — Phased Rollout Plan (AI1)**
- Break implementation into testable phases (typically 3-6)
- Each phase independently verifiable
- Include success criteria per phase
- Map phases to requirements: "Phase 1 implements R1, R2"
- **Each phase must have a verification command**, e.g.:
  - `Verify: pytest -k test_pack_discovery`
  - `Verify: python tools/smoke_load_pack.py`

**Step 4 — Implement Phase N (AI1)**
- Implement the current phase
- Commit with clear message referencing phase
- Note any deviations or discoveries

**Step 4b — Review Phase N (AI2)**
- Fresh-eyes review of implementation
- Check against frozen spec (flag any drift!)
- Output: issues list with accept/reject per item
- If rejected: return to Step 4 with specific fixes

**Accept criteria (all must be true):**
- Implements mapped R#/E# for this phase
- No spec drift detected
- No new lint/test regressions
- No new tech debt warnings (unless logged in TECH_DEBT.md)

---

### Phase C: Testing

| Step | Session | Action | Output |
|------|---------|--------|--------|
| 5 | AI1 | Create test plan | Test specifications with R#/E# mapping |
| 6 | AI1 ↔ AI2 | Validate and freeze test plan | Test plan (FROZEN) |
| 7 | Human + AI | Execute test plan | Test results |
| 8 | AI1 ↔ AI2 | Fix test failures | All tests passing |

**Step 5 — Test Plan (AI1)**
- Define unit, integration, and edge case tests
- **Each test must map to R# and/or E#** (traceability)
- Include manual verification steps where needed

Example test mapping:
```python
def test_cutoff_range():  # R1, E2
    """Cutoff frequency respects 20Hz-20kHz bounds."""
    ...
```

**Step 6 — Test Plan Agreement & Freeze (AI1 ↔ AI2)**
- AI2 reviews for coverage gaps
- Verify tests match spec, not just implementation
- Check all R# and E# have coverage

**Freeze output:**
```
Scope: [feature name / branch]
FrozenAt: [YYYY-MM-DD]
Hash: [commit SHA or zip name]
Coverage: R1-R5 ✓, E1-E3 ✓
Deferred: [R#/E# not covered, with reason] or "None"
Approvals: AI1 ✓ AI2 ✓
```

**Step 7 — Execute Tests**
- Run automated test suite: `pytest`
- Perform manual testing per plan
- Document any failures with R#/E# reference

**Step 8 — Bug Fix Iteration (AI1 ↔ AI2)**
- Fix failures, alternating sessions if stuck
- Re-run tests after each fix
- Continue until all tests pass

---

### Phase D: Documentation

| Step | Session | Action | Output |
|------|---------|--------|--------|
| 9 | AI1 | Write/update documentation | Updated docs/ files |
| 10 | AI1 ↔ AI2 | Documentation review & freeze | Docs (FROZEN) |

**Step 9 — Documentation (AI1)**
- Update relevant docs (DECISIONS.md, TECH_DEBT.md, etc.)
- User-facing docs reference visible R# features only (no internal IDs)
- Update CLAUDE.md with new conventions/patterns

**Step 10 — Documentation Agreement & Freeze (AI1 ↔ AI2)**
- AI2 verifies docs match implementation
- Check for clarity and completeness
- Verify no spec drift occurred

**Freeze output:**
```
Scope: [feature name / branch]
FrozenAt: [YYYY-MM-DD]
Hash: [commit SHA or zip name]
Approvals: AI1 ✓ AI2 ✓
```

---

### Phase E: Integration & Release

| Step | Session | Action | Output |
|------|---------|--------|--------|
| 11 | AI1 | Update index.html / UI | Updated interface |
| 12 | Human + AI | CI/CD gate verification | CI passes baseline |
| 13 | Human + AI | Full package verification | Exit code 0 on all checks |
| 13b | Human | Fresh clone smoke test | Clean env passes |
| 14 | Human | Release | Tagged release on main |

**Step 11 — UI Updates**
- Update index.html or relevant UI components
- Ensure new feature is accessible/visible as intended

**Step 12 — CI/CD Gate Verification**

Baseline CI gates (must all pass):
- [ ] Lint/format (ruff/black or equivalent)
- [ ] Unit tests (pytest)
- [ ] Integration smoke via `./tools/ci_smoke.sh`
- [ ] Artifact build check (if applicable)

**`./tools/ci_smoke.sh` should:**
- Boot SC headless
- Confirm OSC endpoints respond
- Load one core generator
- Load one pack generator (if feature touches packs)
- Exit 0 on success, 1 on failure

**Only add new CI gates if new risk appears:**
- Packaging changes
- Platform-specific code
- Race conditions / async behavior
- New external dependencies

**Step 13 — Full Package Verification**

"Green" means ALL of these exit code = 0:
```bash
./check_all.sh          # exit 0
pytest                  # exit 0
<linter> check .        # exit 0 (e.g. ruff check, flake8)
<formatter> --check .   # exit 0 (e.g. ruff format, black)
```

**If feature involves UI/packaging, also verify:**
```bash
./tools/build_artifact.sh           # exit 0 (if applicable)
./tools/verify_self_contained.sh    # exit 0 (if HTML artifact)
```

**Step 13b — Fresh Clone Smoke Test (Human)**

Catches "works on my machine" issues:
```bash
mkdir -p ~/tmp && cd ~/tmp
git clone [repo] fresh-test
cd fresh-test
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
./check_all.sh
# If applicable: open index.html, verify relative links work
```

**Step 14 — Release**

**Merge policy:**
- No direct commits to main
- Release only from clean dev branch with CI green
- If merge conflict: resolve on dev, re-run Steps 13/13b, then merge

```bash
git checkout main
git merge dev -m "Merge dev: [feature name]"
git tag -a v[X.Y.Z] -m "[Feature summary]"
git push && git push --tags
git checkout dev
```

Optional: Update CHANGELOG.md before merge.

---

## Traceability Matrix

Ensures spec → tests → docs alignment:

| Requirement | Test(s) | Docs | Status |
|-------------|---------|------|--------|
| R1: [description] | test_xxx, test_yyy | Section 2.1 | ✓ |
| R2: [description] | test_zzz | Section 2.2 | ✓ |
| E1: [edge case] | test_edge_xxx | — | ✓ |

Fill this out during Step 6 (test plan freeze).

---

## When to Switch Sessions

Switch from AI1 to AI2 when:
- Stuck on a bug for more than 2-3 attempts
- Implementation feels like it's going in circles
- Need validation of an approach before continuing
- Fresh eyes needed on accumulated assumptions
- **Spec drift detected** (implementation contradicts frozen spec)

Switch from AI2 back to AI1 when:
- AI2 has identified the issue or provided direction
- Review/agreement phase is complete
- Ready to continue primary implementation

---

## Session Handoff Protocol

### Minimal Handoff (quick question)
Copy/paste the relevant code or error message.

### Standard Handoff (implementation continues)
```bash
./tools/zip_for_claude.sh
# Upload ~/Downloads/noise-engine-dev.zip to new session
# Prompt: "Read CLAUDE.md and docs/, then [specific task]"
```

### Full Context Handoff (complex debugging)
1. Zip the project
2. Copy the current conversation summary
3. Include specific file paths and line numbers
4. Note current freeze status of spec/tests/docs

---

## Artifacts Generated

| Phase | Artifacts |
|-------|-----------|
| Specification | `FEATURE_SPEC.md` (FROZEN) |
| Implementation | `FEATURE_ROLLOUT.md`, code commits |
| Testing | Test files with R#/E# mapping, results |
| Documentation | Updated `docs/*.md` (FROZEN) |
| Release | Tag, CHANGELOG.md (optional) |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│  DUAL-AI WORKFLOW v1.2                                  │
├─────────────────────────────────────────────────────────┤
│  SPEC:    1. Create spec with R#/E# (AI1)               │
│           2. Agree + FREEZE (AI1 ↔ AI2)                 │
├─────────────────────────────────────────────────────────┤
│  BUILD:   3. Rollout plan + verify cmd (AI1)            │
│           4. Implement phase N (AI1)                    │
│          4b. Review phase N (AI2) ─┐                    │
│              [repeat per phase] ───┘                    │
├─────────────────────────────────────────────────────────┤
│  TEST:    5. Test plan with R#/E# mapping (AI1)         │
│           6. Agree + FREEZE (AI1 ↔ AI2)                 │
│           7. Execute tests                              │
│           8. Fix failures (AI1 ↔ AI2)                   │
├─────────────────────────────────────────────────────────┤
│  DOCS:    9. Write docs (AI1)                           │
│          10. Agree + FREEZE (AI1 ↔ AI2)                 │
├─────────────────────────────────────────────────────────┤
│  SHIP:   11. Update UI                                  │
│          12. CI/CD baseline gates ✓                     │
│          13. check_all.sh exit 0                        │
│         13b. Fresh clone smoke ✓                        │
│          14. Tag + release                              │
└─────────────────────────────────────────────────────────┘

FREEZE = Scope + Date + Hash + Approvals
CHANGE = Reason + Impact + Both approve
```

---

*Document version: 1.2*
*Based on Noise Engine development workflow, December 2025*
*Refined via AI1 ↔ AI2 review process*
