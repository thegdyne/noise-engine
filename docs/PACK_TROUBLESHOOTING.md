# Pack Troubleshooting Guide

Quick reference for diagnosing and fixing generator validation failures.

---

## Quick Commands

```bash
# Full validation (ASCII, SC syntax, contract, audio render)
python tools/forge_gate.py packs/my_pack/

# Quick validation (skip audio render)
python tools/forge_gate.py packs/my_pack/ --quick

# Audio validation only with verbose output
python tools/forge_audio_validate.py packs/my_pack/ --render -v

# Contract validation only
python tools/forge_validate.py packs/my_pack/

# Test single generator NRT render
python -c "
import sys
sys.path.insert(0, 'tools')
from forge_audio_validate import transform_synthdef_for_nrt, generate_nrt_script
from pathlib import Path
scd = Path('packs/my_pack/generators/my_gen.scd')
transformed = transform_synthdef_for_nrt(scd.read_text(), 'test')
script = generate_nrt_script(transformed, 'test', Path('/tmp/test.wav'))
Path('/tmp/test_nrt.scd').write_text(script)
"
timeout 15 sclang /tmp/test_nrt.scd 2>&1 | tail -30
```

---

## RENDER_FAILED (Timeout)

Generator hangs during NRT render (30s timeout), no SC error output.

### Unary Minus Before Variable

SC can't parse `-varName` in NRT context.

**Diagnose:**
```bash
grep -n "\-[a-z][a-zA-Z]*[^a-zA-Z0-9]" packs/my_pack/generators/*.scd
```

**Fix:** Replace `-varName` with `varName.neg`
```bash
sed -i '' 's/-ne_panWidth/ne_panWidth.neg/g' packs/my_pack/generators/my_gen.scd
```

### Unary Minus Before Parenthesis

SC can't parse `-(expr).method` in NRT context.

**Diagnose:**
```bash
grep -n "\-([^)]*)\." packs/my_pack/generators/*.scd
```

**Fix:** Replace `-(0.6).clip(...)` with `(-0.6).clip(...)` or a negative literal
```bash
sed -i '' 's/-(0.6).clip(0,1)/-0.6/g' packs/my_pack/generators/my_gen.scd
```

### Boolean in Arithmetic

`(numRays > 2) * 0.5` fails when numRays is a constant (evaluates to `true * 0.5`).

**Diagnose:**
```bash
grep -n "\* *([^)]*[<>=!]" packs/my_pack/generators/*.scd
```

**Fix:** Add `.asInteger`
```bash
sed -i '' 's/(numRays > 2)/(numRays > 2).asInteger/g' packs/my_pack/generators/my_gen.scd
```

### Variable Name Collision with `gate`

NRT wrapper adds `gate=1` argument. If your generator has a custom param named `gate`, it collides.

**Diagnose:**
```bash
grep -n "var.*gate" packs/my_pack/generators/my_gen.scd
```

**Fix:** Rename the variable
```bash
sed -i '' 's/var gate,/var gpos,/; s/gate = In/gpos = In/; s/= gate\./= gpos./; s/(gate /(gpos /g' packs/my_pack/generators/my_gen.scd
```

### Complex Buffer Patterns

`TGrains` + `LocalBuf.collect` or similar runtime buffer allocation can hang NRT.

**Diagnose:**
```bash
grep -n "TGrains\|LocalBuf.*collect" packs/my_pack/generators/*.scd
```

**Fix:** No easy fix—add to `KNOWN_AUDIO_ISSUES.md` and accept.

---

## SILENCE

RMS below -40 dB (or -55 dB for impulsive).

### Missing Triggers for Percussive Generator

Generator uses `envTrig = Select.ar(envSource, ...)` but NRT sets envSource=0.

**Diagnose:**
```bash
grep -n "envTrig.*Select\|trig.*Select" packs/my_pack/generators/my_gen.scd
```

**Fix:** The NRT transform should handle this. If not, check `tools/forge_audio_validate.py` has the `envTrig` pattern.

### Wrong midi_retrig Setting

Percussive generator has `midi_retrig: false`.

**Diagnose:**
```bash
grep "midi_retrig" packs/my_pack/generators/my_gen.json
```

**Fix:**
```bash
sed -i '' 's/"midi_retrig": false/"midi_retrig": true/' packs/my_pack/generators/my_gen.json
```

### Squelch/Gate Logic at Test Defaults

Generator has gating logic that closes at the 0.5 test defaults.

**Diagnose:**
```bash
grep -n "squelch\|> sql\|signalLevel" packs/my_pack/generators/my_gen.scd
```

**Fix:** Either adjust the logic or accept as known issue (works with JSON defaults in real use).

### Borderline Quiet

Generator produces audio but RMS is just below -40 dB threshold.

**Diagnose:**
```bash
python -c "
import soundfile as sf
import numpy as np
data, sr = sf.read('/tmp/test.wav')
rms = np.sqrt(np.mean(data**2))
print(f'RMS: {20*np.log10(rms+1e-10):.1f} dB (threshold: -40 dB)')
"
```

**Fix:** Accept as known issue if close to threshold, or increase output level in DSP.

---

## SPARSE

Active frames below 30% (or 5% for impulsive).

### Percussive Generator Tested in Drone Mode

Generator needs triggers but drone mode provides none.

**Diagnose:** Check if `midi_retrig: true` in JSON.

**Fix:** Usually acceptable—generator works correctly when triggered. Add to `KNOWN_AUDIO_ISSUES.md`.

---

## CLIPPING

Peak at or above 0.0 dB.

**Fix:** Add Limiter before output:
```bash
# Find the output chain
grep -n "Out.ar\|ensure2ch" packs/my_pack/generators/my_gen.scd

# Add Limiter before ~ensure2ch or Out.ar
sed -i '' 's/sig = ~ensure2ch/sig = Limiter.ar(sig, 0.95); sig = ~ensure2ch/' packs/my_pack/generators/my_gen.scd
```

---

## DC_OFFSET

Mean signal significantly above 0.

**Common Causes:**
- Impulse/trigger sources (unipolar)
- Asymmetric waveshaping
- Comb/delay feedback

**Fix:** Add LeakDC early in output chain:
```bash
sed -i '' '/sig = ~multiFilter/i\
    sig = LeakDC.ar(sig);
' packs/my_pack/generators/my_gen.scd
```

For inline post-chain generators, add after the main DSP block.

---

## RUNAWAY

Level grows >6 dB over render duration.

**Common Causes:**
- Resonant filters near self-oscillation
- Feedback loops (delay, comb)
- Additive with many partials

**Fix:** Add Limiter before output:
```bash
sed -i '' 's/sig = ~ensure2ch/sig = Limiter.ar(sig, 0.95); sig = ~ensure2ch/' packs/my_pack/generators/my_gen.scd
```

---

## CONTRACT_FAILED

### Missing pack_id

```bash
python3 -c "
import json
from pathlib import Path
p = Path('packs/my_pack/manifest.json')
d = json.load(open(p))
d['pack_id'] = 'my_pack'
json.dump(d, open(p, 'w'), indent=2)
"
```

### Reserved pack_id

Legacy packs with reserved names (e.g., "core") fail Forge validation. The gate auto-skips legacy packs (no `forge_` prefix in SynthDefs).

### Undeclared Variable

Check error message for variable name, then add to `var` declaration:
```bash
sed -i '' 's/var exciter/var exciter, myVar/' packs/my_pack/generators/my_gen.scd
```

---

## UTF-8 / ASCII Corruption

Mojibake characters, syntax errors with `??` or similar.

**Diagnose:**
```bash
cdd-utils utf8 --report packs/my_pack/
```

**Fix:**
```bash
cdd-utils utf8 --fix packs/my_pack/
```

---

## Debugging a Single Generator

```bash
PACK=my_pack
GEN=my_generator

# 1. Generate NRT script
python -c "
import sys
sys.path.insert(0, 'tools')
from forge_audio_validate import transform_synthdef_for_nrt, generate_nrt_script
from pathlib import Path
scd = Path('packs/${PACK}/generators/${GEN}.scd')
transformed = transform_synthdef_for_nrt(scd.read_text(), 'test')
script = generate_nrt_script(transformed, 'test', Path('/tmp/test.wav'))
Path('/tmp/test_nrt.scd').write_text(script)
print('Script written to /tmp/test_nrt.scd')
"

# 2. Try to render
timeout 15 sclang /tmp/test_nrt.scd 2>&1

# 3. If timeout with no output, check the script
head -80 /tmp/test_nrt.scd

# 4. If SC error, fix the pattern mentioned

# 5. If renders but silent, check the wav
python -c "
import soundfile as sf
import numpy as np
data, sr = sf.read('/tmp/test.wav')
peak = np.max(np.abs(data))
rms = np.sqrt(np.mean(data**2))
print(f'Peak: {20*np.log10(peak+1e-10):.1f} dB')
print(f'RMS: {20*np.log10(rms+1e-10):.1f} dB')
"
```

---

## Known Issues to Accept

| Pattern | Reason | Action |
|---------|--------|--------|
| Percussive + SPARSE in drone | Needs triggers | Accept if `midi_retrig: true` |
| Borderline SILENCE (-40 to -42 dB) | Test defaults don't match design | Accept |
| Squelch/gate logic + SILENCE | Test defaults close gate | Accept if JSON defaults work |
| TGrains+LocalBuf + RENDER_FAILED | Complex buffer patterns | Accept |
| Marginal RUNAWAY (6-7 dB) | Slight resonance buildup | Accept with Limiter |

Document accepted issues in `docs/KNOWN_AUDIO_ISSUES.md`.
