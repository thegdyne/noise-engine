# CQD_Forge Pack Generation Session

---

## Prerequisites

This doc assumes you have the noise-engine repo with:
- `contracts/gate.pack.yaml` - CDD validation contract
- `tools/forge_validate.py` - structure validation
- `tools/forge_audio_validate.py` - audio safety checks
- CDD installed: `pip install git+https://github.com/thegdyne/cdd.git@main`

Without these, packs can be created but not validated.

---

## Task
Generate a themed 8-generator pack for Noise Engine synthesizer. Each generator has custom DSP where P1-P5 parameters implement thematic concepts (not just relabeled generic params).

---

## CRITICAL: Check Existing Pack First

**Before generating any files, always examine an existing working pack:**

```bash
cat packs/nerve_glow/manifest.json
cat packs/nerve_glow/generators/nervespk.json
```

This prevents format errors. The JSON schema has required fields that are easy to miss.

---

## Generator Contract (CRITICAL)

```supercollider
SynthDef(\forge_{pack}_{name}, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    // Theme params from customBus0-4...

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // DSP here...

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);  // ALWAYS — prevents DC offset
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    // sig = Limiter.ar(sig, 0.95);  // ADD if using feedback/resonance/wavefold
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_{pack}_{name} loaded".postln;
```

---

## SC Syntax Rules (NRT Compatibility)

These patterns break NRT rendering. **Never generate them:**

| DON'T | DO | Why |
|-------|-----|-----|
| `-panWidth` | `panWidth.neg` | Unary minus before variable fails NRT parse |
| `-(0.6).clip(0,1)` | `(-0.6).clip(0,1)` | Unary minus before parens fails NRT parse |
| `(count > 2) * 0.5` | `(count > 2).asInteger * 0.5` | Boolean in arithmetic evaluates to `true * 0.5` |
| `var gate;` | `var gateVal;` | `gate` reserved by NRT wrapper |
| `var amp;` | `var ampVal;` | Can conflict with NRT amp handling |
| `TGrains` + `LocalBuf.collect` | Avoid or accept failure | Complex buffer patterns hang NRT |
| `TRand.kr(a, b, Dust.kr(r))` | `LFNoise0.kr(r).range(a, b)` | TRand with Dust trigger hangs NRT |
| `Ringz.ar(...).sum` (single) | `Ringz.ar(..., [f1, f2])` | `.sum` on non-array causes SC error |

**Variable declarations:** Must appear at **beginning of code blocks** only.

### .sum Safety Rule

`.sum` only works on arrays. If a UGen returns a single channel, `.sum` fails with "Message 'sum' not understood".

```supercollider
// WRONG - single Ringz, .sum fails
sig = Ringz.ar(trig, freq * 2, 0.1).sum;

// RIGHT - make it an array first
sig = Ringz.ar(trig, freq * [2, 3], 0.1).sum;

// RIGHT - or just don't use .sum for single UGen
sig = Ringz.ar(trig, freq * 2, 0.1);
```

---

## Drone Mode Compatibility (CRITICAL)

**Audio validation runs in drone mode (sustained gate) AND clocked mode. Generators must produce sound in at least one mode.**

### Silent Generator Causes

| Pattern | Problem | Fix |
|---------|---------|-----|
| `Impulse.ar(0)` | Fires once at start, then silent | Use `Dust.ar(density)` for continuous triggers |
| `Impulse.ar(0) * exciter` | Same issue | Use `Dust.ar(rate)` or add `+ Impulse.ar(0)` for initial hit |
| Narrow BPF on noise | Too quiet | Widen bandwidth or boost gain (×4 to ×8) |
| Formant filters | Often too quiet | Use `Resonz` with gain multiplier (×4 to ×6) |
| Percussive-only (bells, hits) | SILENCE in drone mode | Set `midi_retrig: true` - will pass in clocked mode |

### Drone-Safe Excitation Patterns

```supercollider
// WRONG - silent after first instant
trig = Impulse.ar(0);
sig = DynKlank.ar(specs, trig * 0.3, freq);

// RIGHT - continuous triggering
trig = Dust.ar(density);  // density param from customBus
sig = DynKlank.ar(specs, trig * 0.3, freq);

// RIGHT - hybrid (initial hit + continuous)
trig = Impulse.ar(0) + Dust.ar(density);
sig = DynKlank.ar(specs, trig * 0.3, freq);
```

---

## DSP Pre-Check

**Before generating code, identify which safety patterns are required:**

| If the generator uses... | Required |
|--------------------------|----------|
| `Impulse`, `Dust`, `Trig` | LeakDC |
| Waveshaping (`tanh`, `clip2`, `fold2`) | LeakDC |
| Physical models (`DWGBowed`, membranes) | LeakDC |
| Subharmonic generation (`PulseDivider`) | LeakDC |
| Comb/delay feedback > 0.5 | LeakDC + Limiter |
| Resonant filter (rq < 0.3) | Limiter |
| Feedback FM (`SinOscFB`) | Limiter |
| Ring mod with feedback | Limiter |
| Additive with >16 partials | Limiter |
| Wavefolder cascades | Limiter |

**Default:** Always include `LeakDC.ar(sig)`. Add `Limiter.ar(sig, 0.95)` when any Limiter pattern applies.

---

## Output Chain Variants

**Minimal (simple oscillators, no feedback):**
```supercollider
sig = LeakDC.ar(sig);
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
sig = ~ensure2ch.(sig);
Out.ar(out, sig);
```

**Full (feedback, resonance, physical models):**
```supercollider
sig = LeakDC.ar(sig);
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
sig = Limiter.ar(sig, 0.95);
sig = ~ensure2ch.(sig);
Out.ar(out, sig);
```

---

## Validation Pipeline

**Run in order. Stop at first failure.**

### CDD Gate (Recommended)
Single command validates everything:
```bash
cdd test contracts/gate.pack.yaml --var pack_id={pack_id}
```

### Manual Steps (if CDD not available)

#### 1. UTF-8 Check (instant)
Catches copy-paste corruption from AI context switching.
```bash
python tools/utf8_fix.py --report packs/{pack_id}/
```
If issues found: `python tools/utf8_fix.py --fix packs/{pack_id}/`

#### 2. SC Syntax Lint (5s)
Catches NRT-breaking patterns before render attempt.
```bash
# Check for problematic patterns
grep -rn '\-[a-z][a-zA-Z]*[^a-zA-Z0-9]' packs/{pack_id}/generators/*.scd   # unary minus
grep -rn '\-([^)]*)\\.' packs/{pack_id}/generators/*.scd                    # minus-paren
grep -rn 'var.*\bgate\b' packs/{pack_id}/generators/*.scd                   # reserved name
```

#### 3. Contract Check (10s)
Ensures helper usage, arg signature, manifest validity.
```bash
python tools/forge_validate.py packs/{pack_id}/
```

#### 4. Audio Render (2-3 min)
Full safety gates — silence, clipping, DC offset, runaway.
```bash
python tools/forge_audio_validate.py packs/{pack_id}/ --render
```

### Quick Single-Generator Test
```bash
python tools/forge_audio_validate.py packs/{pack_id}/generators/{gen}.scd --render -v
```

### Full Gate (All Checks)
```bash
python tools/forge_gate.py packs/{pack_id}/
```

---

## Safety Gates

| Gate | Threshold | Catches |
|------|-----------|---------|
| Silence | RMS > -40 dB (-55 dB impulsive) | Dead/broken generators |
| Sparse | >30% active (>5% impulsive) | Extremely intermittent output |
| Clipping | peak < 0.999 | Digital overs |
| DC Offset | abs(mean) < 0.01 | Asymmetric waveforms |
| Runaway | growth < +6 dB | Unstable feedback |

**Impulsive detection:** Generators with crest factor > 15 dB auto-detected, use relaxed thresholds.

---

## Known NRT Limitations

These patterns work live but may fail NRT validation:

| Pattern | NRT Behavior | Action |
|---------|--------------|--------|
| `TGrains` + `LocalBuf.collect` | Hangs (timeout) | Accept, document |
| Percussive without sustained gate | SILENCE in drone mode | Accept if `midi_retrig: true` |
| Squelch/gate logic at 0.5 defaults | SILENCE | Accept if JSON defaults work |
| Demand-rate complex triggers | May timeout | Case-by-case |
| Borderline quiet (-40 to -42 dB) | SILENCE | Accept |
| Marginal runaway (6-7 dB) | RUNAWAY | Accept with Limiter added |

Document accepted issues in `docs/KNOWN_AUDIO_ISSUES.md`.

---

## Inline Post-Chain Pattern

For generators needing custom filter/envelope behavior (e.g., acid-style filter sweep).

### Directive
Add after `var` declarations to opt out of helper requirements:
```supercollider
var sig, freq, filterFreq, rq, ...;
var myCustomVars;
// @forge: inline_post_chain
```

### When to Use
- Custom filter envelope (303-style squelch)
- Non-standard envelope (multi-stage, custom triggers)
- Specialized stereo (width tied to parameter)
- Performance optimization

### Inline Implementation
```supercollider
    // Standard bus reads (same as always)
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = 0.2;

    // ... DSP here ...

    // Inline output chain
    sig = LeakDC.ar(sig);
    
    // Inline stereo ensure
    neArr = sig.asArray;
    if(neArr.size == 1, { sig = [neArr[0], neArr[0]] }, { sig = neArr });

    // Inline filter
    ne_cut = filterFreq.clip(20, 18000);
    ne_rq = rq.clip(0.05, 2);
    ne_lp = RLPF.ar(sig, ne_cut, ne_rq);
    ne_hp = RHPF.ar(sig, ne_cut, ne_rq);
    ne_bp = BPF.ar(sig, ne_cut, ne_rq);
    ne_nt = BRF.ar(sig, ne_cut, ne_rq);
    ne_lp2 = RLPF.ar(ne_lp, ne_cut, ne_rq);
    ne_off = sig;
    sig = Select.ar(filterType.round.clip(0, 5), [ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off]);

    // Inline envelope VCA
    ne_atkT = attack.linexp(0, 1, 0.001, 2);
    ne_relT = decay.linexp(0, 1, 0.05, 4);
    trig = Select.kr(envSource.round.clip(0, 2), [
        0,
        Select.kr(clockRate.round.clip(0, 12), In.kr(clockTrigBus, 13)),
        Select.kr(slotIndex.clip(0, 7), In.kr(midiTrigBus, 8))
    ]);
    ne_env = Select.kr(envSource.round.clip(0, 2), [
        1.0,
        Decay2.kr(trig, ne_atkT, ne_relT),
        Decay2.kr(trig, ne_atkT, ne_relT)
    ]);
    sig = sig * ne_env * amp;

    // Final stereo ensure
    neArr = sig.asArray;
    if(neArr.size == 1, { sig = [neArr[0], neArr[0]] }, { sig = neArr });
    Out.ar(out, sig);
```

---

## Generator JSON Schema (FULL)

**CRITICAL: All fields shown are REQUIRED. Check an existing pack if unsure.**

```json
{
  "generator_id": "my_gen",
  "name": "MY GEN",
  "synthdef": "forge_{pack}_{name}",
  "custom_params": [
    {"key": "param1", "label": "P1X", "tooltip": "Thematic description", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "param2", "label": "P2X", "tooltip": "Thematic description", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "param3", "label": "P3X", "tooltip": "Thematic description", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "param4", "label": "P4X", "tooltip": "Thematic description", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""},
    {"key": "param5", "label": "P5X", "tooltip": "Thematic description", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""}
  ],
  "output_trim_db": -6.0,
  "midi_retrig": false,
  "pitch_target": null
}
```

### Required custom_params Fields

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Internal parameter name (lowercase, no spaces) |
| `label` | string | **Exactly 3 characters**, uppercase A-Z or 0-9 |
| `tooltip` | string | Description shown on hover |
| `default` | float | Initial value (0.0-1.0) |
| `min` | float | Minimum value (usually 0.0) |
| `max` | float | Maximum value (usually 1.0) |
| `curve` | string | `"lin"` or `"exp"` |
| `unit` | string | Display unit (usually `""`) |

### Rules
- `pitch_target`: `null` or integer (never string)
- `midi_retrig`: `true` for percussive, `false` for pads/drones
- `output_trim_db`: typically -6.0, adjust per validation trim recommendations
- `name`: UPPERCASE display name
- **Forbidden labels:** `FRQ`, `CUT`, `RES`, `ATK`, `DEC`, `PRT` (reserved for standard controls)

---

## Manifest Schema (FULL)

**CRITICAL: `generators` array is REQUIRED.**

```json
{
  "pack_format": 1,
  "pack_id": "my_pack",
  "name": "Display Name",
  "version": "1.0.0",
  "author": "CQD_Forge",
  "description": "Pack description",
  "enabled": true,
  "generators": [
    "gen1",
    "gen2",
    "gen3",
    "gen4",
    "gen5",
    "gen6",
    "gen7",
    "gen8"
  ]
}
```

---

## Pack Structure

```
packs/{pack_id}/
├── manifest.json
├── {pack_id}.json          <- init preset
└── generators/
    ├── gen1.json
    ├── gen1.scd
    └── ... (8 generators)
```

---

## Archive Structure

```
{pack_id}.tar.gz
    {pack_id}/
        manifest.json
        {pack_id}.json
        generators/
            gen1.json
            gen1.scd
            ... (8 generators total)
```

---

## Quick Fixes

### Batch LeakDC/Limiter
```bash
# Edit patch_out_inserts.sh arrays:
# - limiters=(...) for clipping/runaway
# - leakdcs=(...) for DC offset

DRY_RUN=1 bash patch_out_inserts.sh   # Preview
bash patch_out_inserts.sh              # Apply
python tools/forge_audio_validate.py packs/{pack_id}/ --render  # Re-validate
```

### Fix Unary Minus
```bash
sed -i '' 's/-varName/varName.neg/g' packs/{pack_id}/generators/*.scd
```

### Fix Boolean Arithmetic
```bash
sed -i '' 's/(count > 2)/(count > 2).asInteger/g' packs/{pack_id}/generators/*.scd
```

### Fix UTF-8 Corruption
```bash
python tools/utf8_fix.py --fix packs/{pack_id}/
```

### Fix Missing Manifest Fields
```bash
python3 << 'EOF'
import json
from pathlib import Path
for manifest_path in Path("packs").glob("*/manifest.json"):
    with open(manifest_path) as f:
        data = json.load(f)
    changed = False
    if "pack_format" not in data:
        data["pack_format"] = 1
        changed = True
    if "enabled" not in data:
        data["enabled"] = True
        changed = True
    if changed:
        ordered = {"pack_format": data.pop("pack_format")}
        if "pack_id" in data:
            ordered["pack_id"] = data.pop("pack_id")
        ordered["name"] = data.pop("name", "Unknown")
        ordered["version"] = data.pop("version", "1.0.0")
        ordered["author"] = data.pop("author", "Unknown")
        ordered["description"] = data.pop("description", "")
        ordered["enabled"] = data.pop("enabled")
        ordered.update(data)
        with open(manifest_path, "w") as f:
            json.dump(ordered, f, indent=2)
        print(f"Fixed: {manifest_path.parent.name}")
print("Done!")
EOF
```

---

## Pre-Flight Checklist

Before archiving a pack:

- [ ] `cdd test contracts/gate.pack.yaml --var pack_id={pack_id}` — all 5 tests pass
- [ ] OR manual checks:
  - [ ] `python tools/utf8_fix.py --report packs/{pack_id}/` — no corruption
  - [ ] `python tools/forge_validate.py packs/{pack_id}/` — contract PASS
  - [ ] `python tools/forge_audio_validate.py packs/{pack_id}/ --render` — all 8 PASS
- [ ] All generators have `LeakDC.ar(sig)` in output chain
- [ ] Generators with feedback/resonance have `Limiter.ar(sig, 0.95)`
- [ ] `manifest.json` has `"pack_format": 1`, `"enabled": true`, and `"generators": [...]`
- [ ] Init preset `{pack_id}.json` exists and loads all 8 generators
- [ ] `pitch_target` is `null` or integer (never string)
- [ ] `midi_retrig` matches generator type (percussive=true, pad=false)
- [ ] Add pack to `.gitignore` exceptions: `!packs/{pack_id}/`

---

## Audio Validation Modes

| Generator Type | Expected Pass Mode | `midi_retrig` |
|----------------|-------------------|---------------|
| Pad/Drone | drone | `false` |
| Percussive/Hit | clocked | `true` |
| Hybrid | both | depends |

```bash
# Full (both modes, passes if either works)
python tools/forge_audio_validate.py packs/{pack_id}/ --render

# Drone only (pads/ambient)
python tools/forge_audio_validate.py packs/{pack_id}/ --render --env-mode drone

# Clocked only (percussive)
python tools/forge_audio_validate.py packs/{pack_id}/ --render --env-mode clocked

# Verbose
python tools/forge_audio_validate.py packs/{pack_id}/ --render -v
```

---

## Debugging Single Generator

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

# 3. If timeout, inspect script
head -80 /tmp/test_nrt.scd

# 4. If renders, analyze audio
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

## Historical Issues Reference

Generators that needed post-hoc LeakDC:
`maratus/eye_gleam`, `leviathan/abyss_drone`, `leviathan/whale_song`, `rlyeh/RLYEH`, `rakshasa/fang_strike`, `seagrass_bay/current_drift`

Generators that needed post-hoc Limiter:
`astro_command/alert_pulse`, `barbican_hound/routemaster`, `arctic_henge/aurora`, `arctic_henge/icebell`, `beacon_vigil/crown`, `rlyeh/VESSEL`, `rakshasa/gold_ring`, `summer_of_love/golden_haze`, `amber-threshold/StonePath`, `seagrass_bay/submerged_drone`

Generators fixed for drone mode (Impulse.ar(0) → Dust.ar):
`hoar_frost/crystal_chime`

Generators fixed for NRT compatibility:
- `rlyeh/dagon`: `TRand.kr` → `LFNoise0.kr` (TRand with Dust trigger hangs NRT)
- `rlyeh/dagon`: `.sum` on single Ringz removed
- `rlyeh/vessel`: `.sum` on single Ringz removed, gain boosted

---

## Troubleshooting Reference

For detailed diagnosis and fix commands, see `PACK_TROUBLESHOOTING.md`.

| Symptom | Quick Reference |
|---------|-----------------|
| RENDER_FAILED (timeout) | Check unary minus, boolean arithmetic, `gate` variable, `TRand` with `Dust` trigger |
| RENDER_FAILED (SC error) | Check `.sum` on single UGen, syntax errors |
| SILENCE | Check `midi_retrig`, squelch logic, borderline levels, `Impulse.ar(0)` |
| SPARSE | Percussive in drone mode — usually acceptable |
| CLIPPING | Add `Limiter.ar(sig, 0.95)` |
| DC_OFFSET | Add `LeakDC.ar(sig)` |
| RUNAWAY | Add `Limiter.ar(sig, 0.95)` |
| CONTRACT_FAILED | Check manifest `generators` array, JSON required fields |
| UTF-8 errors | Run `utf8_fix.py --fix` |

---

## CDD Gate Validation (Single Command)

After creating a pack, validate everything with:
```bash
cdd test contracts/gate.pack.yaml --var pack_id={pack_id}
```

This runs 5 tests:
1. **T001** - UTF-8 clean (.scd files)
2. **T002** - UTF-8 clean (.json files)
3. **T003** - SC static patterns (Mix.fill, Array.fill, unary minus)
4. **T004** - Structure validation (manifest, JSON schema)
5. **T005** - Audio safety (silence, clipping, DC offset, runaway)

If T005 fails, run audio validate directly for details:
```bash
python tools/forge_audio_validate.py packs/{pack_id}/ --render
```

Common fixes:
- **SILENCE/SPARSE**: Add continuous noise bed (PinkNoise, BrownNoise)
- **CLIPPING/RUNAWAY**: Add `Limiter.ar(sig, 0.95)` before output
- **DC_OFFSET**: Add `LeakDC.ar(sig)` before filter chain

---

## Pack Delivery Template

When delivering a completed pack archive, always include:
````markdown
## {pack_name} Pack

**Extract:**
```bash

cd ~/repos/noise-engine
tar -xzvf ~/Downloads/{pack_id}.tar.gz -C packs/
```

**Validate:**
```bash
cdd test contracts/gate.pack.yaml --var pack_id={pack_id}
```

**If CDD unavailable:**
```bash
python tools/forge_validate.py packs/{pack_id}/
python tools/forge_audio_validate.py packs/{pack_id}/ --render
```

**Generators:** gen1, gen2, gen3, gen4, gen5, gen6, gen7, gen8
````

This ensures users always get actionable instructions with the archive.

---

## Install Pack Preset

After validation, install the pack preset to your presets directory:
```bash
python tools/forge_gen_preset.py packs/{pack_id}/ --install
```

This creates:
- `packs/{pack_id}/{pack_id}.json` - preset in pack directory
- `~/noise-engine-presets/{pack_id}.json` - installed preset

**Other options:**
```bash
# Generate preset only (no install)
python tools/forge_gen_preset.py packs/{pack_id}/

# Generate for all Forge packs
python tools/forge_gen_preset.py --all --install

# Generate only for packs missing presets
python tools/forge_gen_preset.py --missing --install
```

**Note:** Only run after pack passes gate validation.**Note:** Only run after pack passes gate validation.
---

Ready to forge. What's the pack theme/image?

