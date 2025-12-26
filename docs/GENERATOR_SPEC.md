# Noise Engine Generator Specification

*How to create new generators for Noise Engine*

---

## Overview

Each generator consists of **two files**:
1. `generator_name.json` — UI config and custom parameter definitions
2. `generator_name.scd` — SuperCollider SynthDef

**File locations:**
- **Core generators**: `supercollider/generators/`
- **Pack generators**: `packs/{pack_id}/generators/`

The system auto-discovers both.

---

## JSON Config Structure

```json
{
    "generator_id": "generator_slug",
    "name": "Display Name",
    "synthdef": "synthdef_name",
    "custom_params": [
        {
            "key": "param_key",
            "label": "LBL",
            "tooltip": "Human readable description",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0,
            "curve": "lin",
            "unit": ""
        }
    ],
    "output_trim_db": -6.0,
    "midi_retrig": false,
    "pitch_target": null
}
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `generator_id` | string | Slug identifier (matches filename, no spaces) |
| `name` | string | Display name in UI dropdown |
| `synthdef` | string | Must match `SynthDef(\name, ...)` exactly |
| `custom_params` | array | Array of up to 5 custom parameters (P1-P5) |
| `output_trim_db` | float | Output level trim in dB (typically -6.0 to 0.0) |
| `midi_retrig` | bool | If true, MIDI notes retrigger envelope |
| `pitch_target` | null or int | Which param receives pitch CV (see below) |

### Parameter Fields

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Internal identifier |
| `label` | string | 3-char label shown on slider (A-Z, 0-9) |
| `tooltip` | string | Hover text description (required, non-empty) |
| `default` | float | Initial value |
| `min` / `max` | float | Value range |
| `curve` | string | `"lin"` or `"exp"` |
| `unit` | string | Display unit (Hz, ms, dB, etc.) — may be empty |
| `steps` | int | Optional: for stepped/discrete params |

### pitch_target Field

**Type:** `null` or `int` (0-4) — **never a string**

| Value | Meaning |
|-------|---------|
| `null` | Standard pitch from freqBus (most generators) |
| `0` | P1 receives pitch CV |
| `1` | P2 receives pitch CV |
| `2` | P3 receives pitch CV |
| `3` | P4 receives pitch CV |
| `4` | P5 receives pitch CV |

Use `null` for 99% of generators. Only use an integer if a custom param specifically controls pitch and needs keyboard/MIDI note input.

**Examples:**
```json
"pitch_target": null    // ✓ Most generators
"pitch_target": 0       // ✓ P1 receives pitch CV
"pitch_target": "freq"  // ✗ WRONG — strings not allowed
```

---

## SynthDef Structure

```supercollider
SynthDef(\synthdef_name, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                            filterTypeBus, envEnabledBus, envSourceBus=0,
                            clockRateBus, clockTrigBus,
                            midiTrigBus=0, slotIndex=0,
                            customBus0, customBus1, customBus2, customBus3, customBus4,
                            portamentoBus|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    
    // === READ STANDARD PARAMS ===
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
    
    // === READ CUSTOM PARAMS ===
    // customBus0 = P1, customBus1 = P2, etc.
    myParam = In.kr(customBus0);
    
    // === SOUND SOURCE ===
    sig = /* your synthesis code */;
    
    // === PROCESSING CHAIN (MANDATORY ORDER) ===
    sig = LeakDC.ar(sig);  // Prevent DC offset
    sig = ~stereoSpread.(sig, rate, width);  // Optional: mono→stereo
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    
    Out.ar(out, sig);
}).add;

"  ✓ synthdef_name loaded".postln;
```

---

## Standard Parameters (Always Available)

| Param | Bus | Range | Description |
|-------|-----|-------|-------------|
| FRQ | freqBus | 20-8000 Hz | Base frequency (exp) |
| CUT | cutoffBus | 20-16000 Hz | Filter cutoff (exp) |
| RES | resBus | 0.1-1.0 | Filter resonance (inverted: low = more res) |
| ATK | attackBus | 0.001-2s | Envelope attack |
| DEC | decayBus | 0.01-10s | Envelope decay |
| PRT | portamentoBus | 0.0-1.0 | Portamento/glide time |
| filterType | filterTypeBus | 0-5 | Filter mode (see below) |
| envSource | envSourceBus | 0/1/2 | OFF/CLK/MIDI |
| clockRate | clockRateBus | 0-12 | Clock division index |

### Filter Types

| Value | Mode | Description |
|-------|------|-------------|
| 0 | LP | Low-pass (12dB/oct) |
| 1 | HP | High-pass (12dB/oct) |
| 2 | BP | Band-pass |
| 3 | Notch | Band-reject |
| 4 | LP2 | Low-pass (24dB/oct, steeper) |
| 5 | OFF | Filter bypassed |

---

## Helper Functions

### `~stereoSpread.(sig, rate, width)`
Converts mono to stereo with LFO-modulated panning.
- `sig`: Input signal (mono)
- `rate`: LFO speed for pan movement (0.2 = slow)
- `width`: Pan range 0-1 (0.3 = subtle, 1.0 = full L-R)

### `~multiFilter.(sig, filterType, freq, rq)`
State-variable filter with multiple modes.
- `sig`: Input signal
- `filterType`: 0=LP, 1=HP, 2=BP, 3=Notch, 4=LP2, 5=OFF
- `freq`: Cutoff frequency in Hz
- `rq`: Reciprocal of Q (lower = more resonant, 0.1 = high res)

### `~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex)`
Envelope-controlled VCA with clock/MIDI triggering.
- `sig`: Input signal
- `envSource`: 0=OFF (drone), 1=CLK, 2=MIDI
- `clockRate`: Clock rate index (0-12, selects from 13 rates)
- `attack`, `decay`: Envelope times in seconds
- `amp`: Output amplitude
- `clockTrigBus`: Bus index for clock triggers (audio rate, 13 channels)
- `midiTrigBus`: Bus index for MIDI triggers (audio rate, 8 channels)
- `slotIndex`: 0-7, selects MIDI trigger channel

### `~ensure2ch.(sig)`
Ensures output is exactly 2 channels (stereo).
- Mono → dual-mono
- 2ch → passthrough
- >2ch → mixdown to stereo

### Important: Trigger Buses are Audio Rate!

If you need to create your own filter envelope (like TB-303), read triggers at audio rate:

```supercollider
// CORRECT - audio rate triggers
envTrig = Select.ar(envSource, [
    DC.ar(0),                                    // OFF
    Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),  // CLK (13 rates)
    Select.ar(slotIndex, In.ar(midiTrigBus, 8))  // MIDI (8 channels)
]);
filtEnv = EnvGen.ar(Env.perc(0.001, decay), envTrig);

// WRONG - control rate won't work!
// envTrig = In.kr(clockTrigBus + clockRate);  // DON'T DO THIS
```

---

## Example: Minimal Generator

**minimal.json**
```json
{
    "generator_id": "minimal",
    "name": "Minimal",
    "synthdef": "minimal",
    "custom_params": [
        {
            "key": "brightness",
            "label": "BRT",
            "tooltip": "Harmonic brightness",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0,
            "curve": "lin",
            "unit": ""
        }
    ],
    "output_trim_db": -6.0,
    "midi_retrig": false,
    "pitch_target": null
}
```

**minimal.scd**
```supercollider
SynthDef(\minimal, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4,
                      portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var brightness;
    
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
    
    brightness = In.kr(customBus0);
    
    // Simple saw with brightness-controlled harmonics
    sig = Saw.ar(freq) * brightness.linexp(0, 1, 0.3, 1);
    
    sig = LeakDC.ar(sig);
    sig = ~stereoSpread.(sig, 0.3, 0.1);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ minimal loaded".postln;
```

---

## Tips

1. **Always use `In.kr()`** to read from control buses
2. **Include `LeakDC.ar()`** before the filter to prevent DC offset
3. **Use `~ensure2ch.`** at the end — generator buses are stereo
4. **Keep CPU low** — these run 8× simultaneously
5. **Test edge cases** — extreme freq, cutoff, resonance values
6. **Add the print statement** — confirms successful load
7. **Set `output_trim_db`** appropriately — typically -6.0 for safe headroom

---

## Register in GENERATOR_CYCLE

After creating core generator files, add to `src/config/__init__.py`:

```python
GENERATOR_CYCLE = [
    "Empty",
    # ... existing generators ...
    "Minimal",  # Your new generator
]
```

The name must match `"name"` in the JSON exactly.

**Note:** Pack generators don't need registration — they're discovered automatically from `packs/{pack_id}/manifest.json`.

---

## Forbidden Parameter Labels

These labels are reserved for core UI and must not be used in custom params:

```
FRQ, CUT, RES, ATK, DEC, PRT
```

---

## Pack Generator Naming

For pack generators, use namespaced SynthDef names:

```
forge_{pack_id}_{generator_id}
imaginarium_{pack_id}_{method}_{variant}
```

This prevents collisions between packs.
