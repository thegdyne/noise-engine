Good question. Let me break it down honestly:

---

## Effort Estimate: Tertiary Musical Context Layer

### Phase Breakdown

| Phase | Work | Sessions | Hours |
|-------|------|----------|-------|
| **1. Visual features (3a)** | 9 feature extractors, normalization, axis scoring, tests | 2 | 4-6 |
| **2. ONNX integration** | New dependency, model bundling, preprocessing, detection wrapper | 2 | 4-6 |
| **3. Concept database** | YAML loading, alias resolution, vote aggregation, tests | 1 | 2-3 |
| **4. Fusion logic** | Distribution blending, confidence, fallback, tests | 1 | 2-3 |
| **5. CLI integration** | Wire to existing CLI, debug JSON, `--show-context` | 0.5 | 1-2 |
| **6. Golden validation** | Curate 10 images, expected outputs, stability tests | 1 | 2-3 |

**Subtotal: ~7.5 sessions / 15-23 hours**

---

### Hidden Work (Often Underestimated)

| Item | Sessions | Notes |
|------|----------|-------|
| Axis weight tuning | 0.5 | Apply fixes from analysis, verify numerically |
| Model acquisition | 0.5 | Download, verify SHA256, bundle correctly |
| Cross-platform testing | 1 | macOS works, but Windows/Linux ONNX? |
| Selection integration | 1 | Hook context bias into existing candidate scoring (R34 dependency) |
| Candidate tags metadata | 1-2 | Synthesis methods need `tags` field — may not exist yet |

**Hidden subtotal: 4-5 sessions / 8-12 hours**

---

### Realistic Total

| Scenario | Sessions | Hours | Calendar Time |
|----------|----------|-------|---------------|
| **Optimistic** (everything works) | 8-10 | 20-25 | 1.5-2 weeks |
| **Realistic** (normal friction) | 12-14 | 28-35 | 2-3 weeks |
| **Pessimistic** (dependency issues, ONNX pain) | 16-18 | 40-45 | 3-4 weeks |

---

### Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| **ONNX cross-platform** | Medium | Test early on all 3 OS |
| **Candidate tags don't exist** | High | May need to add tags to all synthesis methods first |
| **Model size bloat** | Low | 20MB is acceptable, but check bundle process |
| **Axis weights need iteration** | Medium | Golden set will expose issues early |
| **3a alone isn't useful enough** | Low | 3a provides baseline even without object detection |

---

### Dependency Check

Before starting, verify:

```
[ ] Synthesis methods have `tags` metadata (R34)
[ ] Selection accepts external bias weights (R32)
[ ] ONNX Runtime installs cleanly on all platforms
[ ] MobileNet-SSD ONNX model available and licensed appropriately
```

If **R34 (candidate tags)** isn't done, add **1-2 sessions** to tag all existing synthesis methods.

---

### My Recommendation

**Realistic estimate: 12-14 sessions over 2-3 weeks**

This is a **medium-sized feature** — bigger than a mopup task, but not a multi-month epic. The spec is solid, the prep work de-risks the design phase, and the phased approach means you get value incrementally (3a works standalone).

**If you want to trim scope:**
- Skip Phase 2 (ONNX/object detection) initially — ship 3a-only as v1
- Reduces to **5-6 sessions / 1-1.5 weeks**
- Add 3b later when you want the object→concept layer

---

Does that help frame it? Want me to add this to the backlog with the effort estimate?
