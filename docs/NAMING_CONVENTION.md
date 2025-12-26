# Noise Engine Naming Convention

*Per CQD_FORGE_SPEC.md v1.0 (FROZEN 2025-12-23)*

---

## SynthDef Naming

```
forge_{pack_id}_{generator_id}
```

**Examples:**
- `forge_leviathan_abyss_drone`
- `forge_crystal_shimmer_pad`
- `forge_808_drums_kick`

---

## Pack ID Rules

| Rule | Constraint |
|------|------------|
| Pattern | `[a-z][a-z0-9_]*` (lowercase slug) |
| Max length | 24 characters |
| Reserved | `core`, `mod`, `test` |

**Valid:** `leviathan`, `crystal_caves`, `808_drums`  
**Invalid:** `Leviathan` (uppercase), `crystal-caves` (hyphen), `123pack` (starts with digit)

---

## Generator ID Rules

| Rule | Constraint |
|------|------------|
| Pattern | `[a-z][a-z0-9_]*` (lowercase slug) |
| Max length | 24 characters |

**Valid:** `abyss_drone`, `shimmer_pad`, `kick_808`  
**Invalid:** `Abyss-Drone` (uppercase, hyphen)

---

## Combined Length

SynthDef names: `forge_` (6) + pack_id (≤24) + `_` (1) + generator_id (≤24) = **≤55 chars**

Max recommended: **56 characters** total.

---

## File Structure

```
packs/{pack_id}/
├── manifest.json
└── generators/
    ├── {generator_id}.json
    └── {generator_id}.scd
```

- JSON filename = generator_id
- SCD filename = generator_id
- SynthDef inside SCD = `forge_{pack_id}_{generator_id}`

---

## Other Prefixes

| Prefix | Source | Example |
|--------|--------|---------|
| `forge_` | CQD_Forge hand-crafted packs | `forge_leviathan_abyss_drone` |
| `imaginarium_` | Imaginarium auto-generated | `imaginarium_test_pack_simple_fm_000` |
| (none) | Core generators | `saw`, `drone`, `fm` |

---

## Validation

```bash
python tools/forge_validate.py packs/my_pack/
python tools/forge_validate.py packs/my_pack/ --verbose
```

Checks:
- Pack ID and generator ID format
- SynthDef naming matches convention
- Required bus arguments present
- Helper functions used
- Post-chain order correct
