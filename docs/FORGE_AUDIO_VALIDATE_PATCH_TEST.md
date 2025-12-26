# Testing Instructions for forge_audio_validate.py Patch

## Summary of Changes

Three changes to `transform_synthdef_for_nrt()`:

| Change | Lines | Purpose |
|--------|-------|---------|
| 1. Trigger bus `.kr` handling | ~182-186 | Fix `In.kr(clockTrigBus/midiTrigBus)` patterns |
| 2. Keep `ampBus` in arg list | ~224-234 | Prevent undefined `ampBus` after arg stripping |
| 3. Neutralize amp selection | ~219-222 | Replace complex `In.kr(Select.kr(...))` with constant |

---

## Step 1: Install the Patch

```bash
# Backup original
cp tools/forge_audio_validate.py tools/forge_audio_validate.py.bak

# Install patched version
cp ~/Downloads/forge_audio_validate_patched.py tools/forge_audio_validate.py
```

---

## Step 2: Verify Transform Output (No Render)

Test that transforms produce valid code without undefined symbols.

### Test crystal_spring.scd (Change 1)

```bash
python3 -c "
import sys
sys.path.insert(0, 'tools')
from forge_audio_validate import transform_synthdef_for_nrt

code = open('packs/seagrass_bay/generators/crystal_spring.scd').read()
transformed = transform_synthdef_for_nrt(code, 'test_crystal_spring')

# Check for undefined trigger buses
for sym in ['clockTrigBus', 'midiTrigBus']:
    if sym in transformed:
        print(f'FAIL: {sym} still present')
        sys.exit(1)

# Check DC.kr replacement happened
if 'DC.kr(0) !' in transformed:
    print('PASS: In.kr trigger buses transformed to DC.kr')
else:
    print('FAIL: DC.kr replacement not found')
    sys.exit(1)
"
```

### Test acid_bloom.scd (Changes 2 & 3)

```bash
python3 -c "
import sys
sys.path.insert(0, 'tools')
from forge_audio_validate import transform_synthdef_for_nrt

code = open('packs/summer_of_love/generators/acid_bloom.scd').read()
transformed = transform_synthdef_for_nrt(code, 'test_acid_bloom')

# Check ampBus is in arg list
if 'ampBus=(-1)' in transformed:
    print('PASS: ampBus preserved in arg list')
else:
    print('FAIL: ampBus not in arg list')
    sys.exit(1)

# Check amp selection pattern was neutralized
if 'In.kr(Select.kr((ampBus' in transformed:
    print('FAIL: amp selection pattern not neutralized')
    sys.exit(1)
else:
    print('PASS: amp selection pattern neutralized')
"
```

---

## Step 3: Full Render Test (Two Failing Packs)

Test actual audio rendering on the two packs that previously failed.

### Sequential (verbose, see each result)

```bash
python tools/forge_audio_validate.py packs/seagrass_bay --render -v --env-mode both
python tools/forge_audio_validate.py packs/summer_of_love --render -v --env-mode both
```

### Parallel (faster)

```bash
echo "packs/seagrass_bay
packs/summer_of_love" | xargs -P 2 -I {} python tools/forge_audio_validate.py {} --render --env-mode both
```

**Expected:** Both packs should pass (no RENDER_FAILED status).

---

## Step 4: Regression Test (All CQD_Forge Packs)

Ensure the patch doesn't break previously passing packs.

### List all CQD_Forge packs

```bash
for d in packs/*/; do
  if grep -q '"author".*"CQD_Forge"' "$d/manifest.json" 2>/dev/null; then
    echo "$d"
  fi
done
```

### Parallel render validation (8 workers)

```bash
for d in packs/*/; do
  if grep -q '"author".*"CQD_Forge"' "$d/manifest.json" 2>/dev/null; then
    echo "$d"
  fi
done | xargs -P 8 -I {} python tools/forge_audio_validate.py {} --render --env-mode both 2>&1 | tee /tmp/forge_validate_all.log
```

### Check for failures

```bash
grep -E "RENDER_FAILED|FAIL" /tmp/forge_validate_all.log
```

**Expected:** No RENDER_FAILED results.

---

## Step 5: Contract Check (Separate Issue)

The contract check in `forge_validate.py` still has false positives for inlined implementations. This is a separate fix, but you can verify current state:

```bash
for d in packs/*/; do 
  if grep -q '"author".*"CQD_Forge"' "$d/manifest.json" 2>/dev/null; then
    out=$(python tools/forge_validate.py "$d" 2>/dev/null | grep -E "^Pack:|FAIL|missing")
    if echo "$out" | grep -q "FAIL"; then
      echo "$out"
      echo ""
    fi
  fi
done
```

**Note:** These failures are expected until `forge_validate.py` is updated to:
1. Strip comments before scanning
2. Match `~multiFilter.(` not just `~multiFilter`

---

## Rollback (if needed)

```bash
cp tools/forge_audio_validate.py.bak tools/forge_audio_validate.py
```

---

## Quick Validation Commands

| Test | Command |
|------|---------|
| Transform only (crystal_spring) | See Step 2 |
| Transform only (acid_bloom) | See Step 2 |
| Render seagrass_bay | `python tools/forge_audio_validate.py packs/seagrass_bay --render -v` |
| Render summer_of_love | `python tools/forge_audio_validate.py packs/summer_of_love --render -v` |
| All packs parallel | See Step 4 |
| Check failures | `grep RENDER_FAILED /tmp/forge_validate_all.log` |
