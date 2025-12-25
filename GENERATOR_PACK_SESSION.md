# CQD_Forge Pack Generation Session

## Task
Generate a themed 8-generator pack for Noise Engine synthesizer. Each generator has custom DSP where P1-P5 parameters implement thematic concepts (not just relabeled generic params).

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
    sig = ~stereoSpread.(sig, rate, width);  // optional
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_{pack}_{name} loaded".postln;
```

## Pack Structure
```
packs/{pack_id}/
    manifest.json
    generators/
        {gen_id}.json
        {gen_id}.scd
```

## Manifest Schema
```json
{
  "pack_id": "slug_24char_max",
  "pack_format": 1,
  "enabled": true,
  "name": "Display Name",
  "description": "...", 
  "author": "CQD_Forge",
  "version": "1.0.0",
  "generators": ["gen1", "gen2", "gen3", "gen4", "gen5", "gen6", "gen7", "gen8"]
}
```

**CRITICAL: Manifest MUST include:**
- `"pack_format": 1` -- Required for pack loader
- `"enabled": true` -- Pack won't appear in UI without this
- `"generators"` array with exactly 8 entries

## Generator JSON Schema
```json
{"generator_id": "slug", "name": "Display", "synthdef": "forge_pack_name",
 "custom_params": [
   {"key": "x", "label": "XXX", "tooltip": "Description", "default": 0.5, 
    "min": 0.0, "max": 1.0, "curve": "lin", "unit": ""}
 ], "output_trim_db": -6.0, "midi_retrig": false, "pitch_target": null}
```

## Role Balance
Each pack needs: 1-2 **bed** (foundation), 1-2 **accent** (hits/stabs), 1-2 **foreground** (melodic), 1-2 **motion** (movement/texture)

## Labels
- 3 chars uppercase A-Z/0-9
- Thematic and evocative
- Unique within generator

## Synthesis Methods Catalog

Reference: `GENERATOR_SPEC.md` for contract details, `imaginarium/methods/` for implementation patterns.

### Family Overview (30 methods)

| Family | Count | Character |
|--------|-------|-----------|
| **subtractive** | 5 | Warm, analog, filter-focused |
| **fm** | 7 | Metallic, bells, digital |
| **physical** | 7 | Organic, acoustic, plucked/bowed |
| **texture** | 6 | Noise, granular, atmospheric |
| **spectral** | 5 | Additive, harmonic, evolving |

### Subtractive Methods
| Method | Character | Typical P1-P5 |
|--------|-----------|---------------|
| `bright_saw` | Classic detuned saws, warm/rich | Detune, Mix, Spread, Bright, Sub |
| `dark_pulse` | Hollow PWM, dark/moving | Width, PWM, Rate, Cut, Res |
| `noise_filtered` | Filtered noise, windy/airy | Color, Reso, Sweep, Mod, Mix |
| `supersaw` | Massive unison, huge/thick | Voices, Detune, Mix, Width, Fat |
| `wavefold` | West coast, metallic/complex | Fold, Sym, Drive, Harm, Thick |

### FM Methods
| Method | Character | Typical P1-P5 |
|--------|-----------|---------------|
| `simple_fm` | Classic 2-op, bell-like | Ratio, Index, Decay, Bright, Harm |
| `feedback_fm` | Harsh self-mod, aggressive | Feed, Drive, Tone, Chaos, Edge |
| `ratio_stack` | Complex harmonics, rich | R1, R2, R3, Index, Blend |
| `ring_mod` | Inharmonic, metallic/sci-fi | Ratio, Depth, Shape, Detune, Mix |
| `hard_sync` | Aggressive sweep, lead/bass | Slave, Sweep, Hard, Tone, Punch |
| `phase_mod` | CZ-style, digital/clean | Phase, Depth, Shape, Bright, Mod |
| `am_chorus` | AM with motion, shimmery | Depth, Rate, Voices, Spread, Warm |

### Physical Methods
| Method | Character | Typical P1-P5 |
|--------|-----------|---------------|
| `karplus` | Plucked string, guitar/harp | Decay, Damp, Bright, Excite, Body |
| `modal` | Resonant body, bells/marimba | Modes, Decay, Bright, Spread, Ring |
| `bowed` | Friction string, cello/drone | Bow, Press, Pos, Bright, Body |
| `formant` | Vocal/choir, breathy/human | Vowel, Breath, Track, Shift, Chorus |
| `membrane` | Drum/percussion, thud/punch | Tens, Decay, Strike, Tone, Size |
| `tube` | Pipe/flute, airy/blown | Length, Breath, Tone, Turb, Vib |
| `comb_resonator` | Tuned delay, metallic/ringing | Feed, Damp, Bright, Mix, Mod |

### Texture Methods
| Method | Character | Typical P1-P5 |
|--------|-----------|---------------|
| `granular_cloud` | Diffuse particles, ambient | Dens, Size, Pitch, Jitter, Shimmer |
| `dust_resonator` | Crackle/rain, organic | Dens, Decay, Bright, Spread, Pitch |
| `noise_drone` | Filtered drone, dark/deep | Color, Move, Reso, Mod, Width |
| `chaos_osc` | Unpredictable, glitchy | Chaos, Rate, Fold, Mix, Smooth |
| `bitcrush` | Lo-fi, crunchy/retro | Bits, Rate, Mix, Tone, Alias |
| `noise_rhythm` | Rhythmic noise, percussive | Shape, Decay, Dens, Tone, Swing |

### Spectral Methods
| Method | Character | Typical P1-P5 |
|--------|-----------|---------------|
| `additive` | Organ-like, pure/harmonic | Partials, Roll, Stretch, Bright, Odd |
| `harmonic_series` | Natural overtones, rich | Num, Decay, Bright, Spread, Fund |
| `spectral_drone` | FFT-based, evolving | Freeze, Blur, Shift, Feedback, Mix |
| `vocoder` | Robotic, processed | Bands, Q, Mod, Carrier, Breath |
| `wavetable` | Morphing, animated | Pos, Morph, Warp, Spread, Bright |

### Choosing Methods for Image Themes

| Image Mood | Best Methods |
|------------|--------------|
| **Dark/ominous** | dark_pulse, noise_drone, bowed, tube |
| **Bright/airy** | bright_saw, additive, granular_cloud |
| **Metallic/industrial** | ring_mod, wavefold, comb_resonator |
| **Organic/natural** | karplus, formant, dust_resonator |
| **Digital/sci-fi** | bitcrush, chaos_osc, phase_mod |
| **Warm/analog** | supersaw, simple_fm, dark_pulse |
| **Percussion** | membrane, noise_rhythm, modal |
| **Ambient/evolving** | granular_cloud, spectral_drone, bowed |
| **Aggressive/harsh** | feedback_fm, hard_sync, wavefold |

### DSP Pattern Reference

```supercollider
// === Subtractive core ===
sig = Saw.ar(freq) + Pulse.ar(freq * 1.01, width);
sig = RLPF.ar(sig, cutoff, rq);

// === FM core ===
var mod = SinOsc.ar(freq * ratio) * index * freq;
sig = SinOsc.ar(freq + mod);

// === Karplus-Strong ===
sig = Pluck.ar(noise, trig, freq.reciprocal, freq.reciprocal, decay, coef);

// === Modal resonators ===
sig = Ringz.ar(exciter, [freq, freq*2.3, freq*4.1], decays).sum;

// === Granular ===
sig = GrainBuf.ar(2, Dust.ar(density), grainDur, bufnum, rate, pos);

// === Wavefold ===
sig = sig.fold2(threshold);
sig = (sig * drive).tanh;

// === Trigger selection (for non-envVCA methods) ===
trig = Select.ar(envSource.round.clip(0, 2), [
    DC.ar(0),
    Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
    Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
]);
```

## SuperCollider Syntax Pitfalls (AVOID THESE)

### 1. Mix.fill(ugen, ...) -- UGen count not allowed
```supercollider
// WRONG - prayer is a UGen, count must be compile-time constant
harmonics = Mix.fill(prayer.round, { |i| ... });

// CORRECT - fixed count with amplitude crossfade
harmonics = Mix.fill(6, { |i|
    var amp = (prayer * 6 - i).clip(0, 1);  // Fades in layers
    SinOsc.ar(freq * (i + 1)) * amp
});
```

### 2. LocalBuf.collect -- LocalBuf is not an array
```supercollider
// WRONG - LocalBuf returns a buffer ref, not an array
spray = LocalBuf(1024).collect({ |buf| ... });

// CORRECT - create buffer, fill separately
buf = LocalBuf(SampleRate.ir * 0.01, 1);
BufWr.ar(WhiteNoise.ar(1), buf, Phasor.ar(0, 1, 0, BufFrames.ir(buf)));
spray = TGrains.ar(2, trig, buf, ...);
```

### 3. -variable * n -- Parser rejects leading minus
```supercollider
// WRONG - parser error
sig = sig + (-contrast * 0.3);

// CORRECT - multiply by negative
sig = sig + (contrast * -0.3);
```

### 4. Mid-block var -- All vars must be at block start
```supercollider
// WRONG
sig = SinOsc.ar(freq);
var extra = 0.5;  // ERROR: var after statement

// CORRECT
var sig, extra;
sig = SinOsc.ar(freq);
extra = 0.5;
```

### General Rule
The UGen graph must be **compile-time determinable**. You cannot use runtime values (UGens, bus reads) to control:
- Number of oscillators/filters
- Array sizes
- Loop counts

## Output
Create all files:
1. `packs/{pack_id}/manifest.json`
2. `packs/{pack_id}/generators/{gen_id}.json` x 8
3. `packs/{pack_id}/generators/{gen_id}.scd` x 8  
4. `{pack_id}_preset.json` - loads all 8 generators into slots

Deliver as downloadable archive.

## Preset Schema (Full)

**CRITICAL FORMAT RULES:**
- Use `"generator"` (NOT `"generator_id"`) with the display name from JSON
- Add `"pack"` at top level to specify which pack
- Generator names are typically UPPERCASE (match the `"name"` field in generator JSON)
- `midi_channel`: 0 (not 1)
- `env_source`: 0 = OFF/drone, 1 = CLK, 2 = MIDI

```json
{
  "version": 2,
  "mapping_version": 1,
  "name": "{pack_display_name}",
  "pack": "{pack_id}",
  "slots": [
    {"generator": "GEN1_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0},
    {"generator": "GEN2_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0},
    {"generator": "GEN3_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0},
    {"generator": "GEN4_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0},
    {"generator": "GEN5_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0},
    {"generator": "GEN6_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0},
    {"generator": "GEN7_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0},
    {"generator": "GEN8_NAME", "params": {"frequency": 0.5, "cutoff": 1.0, "resonance": 0.0, "attack": 0.0, "decay": 0.73, "custom_0": 0.5, "custom_1": 0.5, "custom_2": 0.5, "custom_3": 0.5, "custom_4": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 6, "midi_channel": 0, "transpose": 2, "portamento": 0.0}
  ],
  "mixer": {
    "channels": [
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false},
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false},
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false},
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false},
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false},
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false},
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false},
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false, "eq_hi": 100, "eq_mid": 100, "eq_lo": 100, "gain": 0, "echo_send": 0, "verb_send": 0, "lo_cut": false, "hi_cut": false}
    ],
    "master_volume": 0.8
  },
  "bpm": 120,
  "master": {
    "volume": 0.8,
    "eq_hi": 120, "eq_mid": 120, "eq_lo": 120,
    "eq_hi_kill": 0, "eq_mid_kill": 0, "eq_lo_kill": 0,
    "eq_locut": 0, "eq_bypass": 0,
    "comp_threshold": 100, "comp_makeup": 0, "comp_ratio": 1,
    "comp_attack": 4, "comp_release": 4, "comp_sc": 0, "comp_bypass": 0,
    "limiter_ceiling": 590, "limiter_bypass": 0
  },
  "mod_sources": {
    "slots": [
      {"generator_name": "LFO", "params": {"rate": 0.5, "shape": 0.5, "pattern": 0.0, "rotate": 0.0}, "output_wave": [0,0,0,0], "output_phase": [0,0,0,0], "output_polarity": [0,0,0,0]},
      {"generator_name": "Sloth", "params": {"bias": 0.5}, "output_wave": [0,0,0,0], "output_phase": [0,0,0,0], "output_polarity": [0,0,0,0]},
      {"generator_name": "LFO", "params": {"rate": 0.5, "shape": 0.5, "pattern": 0.0, "rotate": 0.0}, "output_wave": [0,0,0,0], "output_phase": [0,0,0,0], "output_polarity": [0,0,0,0]},
      {"generator_name": "Sloth", "params": {"bias": 0.5}, "output_wave": [0,0,0,0], "output_phase": [0,0,0,0], "output_polarity": [0,0,0,0]}
    ]
  },
  "mod_routing": {"connections": []}
}
```

**Key field mappings:**
- `"generator"` = the `"name"` value from generator JSON (e.g., `"DROWNEDBELL"`)
- `"pack"` = the `"pack_id"` from manifest (e.g., `"rlyeh"`)
- `custom_0` through `custom_4` = use defaults from each generator's JSON `custom_params[].default`

**Preset defaults:**
- `cutoff`: 1.0 (filter open)
- `decay`: 0.73 (~1.5 seconds)
- `env_source`: 0 (OFF/drone mode -- change to 1 for CLK rhythmic)
- `clock_rate`: 6 (1/6 division)
- `transpose`: 2 (index for 0 semitones)
- `midi_channel`: 0 (not 1!)
- `custom_0-4`: Use each generator's JSON `default` values

## Install Commands
```bash
cd ~/repos/noise-engine

# Extract pack
tar -xzf {pack_id}.tar.gz -C packs/

# Validate pack (check contract compliance)
python tools/forge_validate.py packs/{pack_id}/ --verbose

# Audio validation (renders and checks safety gates)
python tools/forge_audio_validate.py packs/{pack_id}/ --render

# Move preset to presets directory  
mv packs/{pack_id}/_preset.json ~/noise-engine-presets/{pack_id}_preset.json

# Restart Noise Engine, select pack from dropdown
```

## Audio Validation

**`forge_audio_validate.py`** renders each generator via NRT and checks for audio issues.

### Usage
```bash
# Full validation (both drone and clocked envelope modes)
python tools/forge_audio_validate.py packs/{pack_id}/ --render

# Drone only (for pad/ambient packs)
python tools/forge_audio_validate.py packs/{pack_id}/ --render --env-mode drone

# Clocked only (for rhythmic/percussive packs)
python tools/forge_audio_validate.py packs/{pack_id}/ --render --env-mode clocked

# Verbose (shows render progress)
python tools/forge_audio_validate.py packs/{pack_id}/ --render -v
```

### Safety Gates (from Imaginarium §9)
| Gate | Threshold | Catches |
|------|-----------|---------|
| Silence | RMS > -40 dB | Dead/broken generators |
| Sparse | >30% active frames | Extremely intermittent output |
| Clipping | peak < 0.999 | Digital overs |
| DC Offset | abs(mean) < 0.01 | Asymmetric waveforms |
| Runaway | growth < +6 dB | Unstable feedback |

### Impulsive Detection
Generators with high crest factor (peak - RMS > 15 dB) are detected as **impulsive** (sparse/percussive). These use relaxed thresholds:
- RMS: -55 dB (vs -40 dB)
- Active frames: 5% (vs 30%)

Impulsive generators show `~` suffix in output: `✓ PASS~`

### Example Output
```
nerve_glow: Rendering 8 generators (drone + clocked)...

Generator         Peak     RMS  Crest  Trim Adj  Active Status
───────────────────────────────────────────────────────────────────────────
nervespk         -22.6  -45.2   23dB  +19.6 dB     31% ✓ PASS~
myofiber         -19.8  -26.7    7dB   +8.7 dB    100% ✓ PASS
cartglow         -23.5  -45.2   22dB  +20.5 dB     22% ✓ PASS~
...
───────────────────────────────────────────────────────────────────────────
✓ All 8 generators passed (3 impulsive~)

⚠ Trim recommendations (adjust output_trim_db):
  nervespk: +19.6 dB
  cartglow: +20.5 dB
```

### Trim Recommendations
The tool reports loudness vs target (-18 dBFS RMS). Large adjustments are informational – generators may be designed quiet or the NRT test defaults (freq=220, cutoff=2000, customs=0.5) may not match the generator's sweet spot.

### Requirements
- SuperCollider installed (sclang in PATH or standard location)
- `pip install soundfile` (or librosa)

## Archive Structure
```
{pack_id}.tar.gz
    {pack_id}/
        manifest.json
        _preset.json          <- moved to ~/noise-engine-presets/ after install
        generators/
            gen1.json
            gen1.scd
            ... (8 generators total)
```

---

## Troubleshooting

### Pack doesn't appear in dropdown
**Cause:** Missing `pack_format` or `enabled` in manifest.json

**Fix all broken manifests:**
```bash
cd ~/repos/noise-engine
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

### Validation warnings about seed/RandSeed
**Expected** for CQD_Forge packs. These are Imaginarium determinism requirements -- hand-crafted packs don't need them unless using random UGens.

### Audio validation: SILENCE on impulsive generators
**Expected** if crest factor is high. Tool auto-detects impulsive sounds (crest > 15 dB) and uses relaxed thresholds. If still failing:
- Check generator produces output at default params
- Try `--env-mode clocked` to test with rhythmic triggers

### Audio validation: DC_OFFSET
**Cause:** Asymmetric waveforms, often from unipolar sources like `Impulse.ar`.

**Fix:** Add `LeakDC.ar(sig)` before the output chain:
```supercollider
sig = LeakDC.ar(sig);  // Remove DC offset
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
```

### Audio validation: Large trim recommendations
**Informational only** – not failures. NRT test defaults (freq=220, cutoff=2000, customs=0.5) may not match the generator's intended use. Verify perceived loudness in-app before adjusting `output_trim_db`.

---

Ready to forge. What's the pack theme/image?
