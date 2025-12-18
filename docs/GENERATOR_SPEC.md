# Noise Engine Generator Specification

*How to create new generators for Noise Engine*

---

## Overview

Each generator consists of **two files**:
1. `generator_name.json` — UI config and custom parameter definitions
2. `generator_name.scd` — SuperCollider SynthDef

Place both in `supercollider/generators/`. The system auto-discovers them.

---

## JSON Config Structure

```json
{
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
    ]
}
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Display name in UI dropdown |
| `synthdef` | Must match `SynthDef(\name, ...)` exactly |
| `custom_params` | Array of up to 5 custom parameters (P1-P5) |

### Parameter Fields

| Field | Description |
|-------|-------------|
| `key` | Internal identifier (used in SynthDef arg name) |
| `label` | 3-char label shown on slider |
| `tooltip` | Hover text description |
| `default` | Initial value |
| `min` / `max` | Value range |
| `curve` | `"lin"` or `"exp"` |
| `unit` | Display unit (Hz, ms, dB, etc.) |
| `steps` | Optional: for stepped/discrete params |

---

## SynthDef Structure

```supercollider
SynthDef(\synthdef_name, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                            filterTypeBus, envEnabledBus, envSourceBus=0, 
                            clockRateBus, clockTrigBus,
                            midiTrigBus=0, slotIndex=0,
                            customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    
    // === READ STANDARD PARAMS ===
    freq = In.kr(freqBus);
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
    
    // === PROCESSING CHAIN (use helper functions) ===
    sig = ~stereoSpread.(sig, width, random);
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
| filterType | filterTypeBus | 0/1/2 | LP/HP/BP |
| envSource | envSourceBus | 0/1/2 | OFF/CLK/MIDI |
| clockRate | clockRateBus | 0-12 | Clock division index |

---

## Helper Functions

### `~stereoSpread.(sig, rate, width)`
Converts mono to stereo with LFO-modulated panning.
- `sig`: Input signal (mono)
- `rate`: LFO speed for pan movement (0.2 = slow)
- `width`: Pan range 0-1 (0.3 = subtle, 1.0 = full L-R)

### `~multiFilter.(sig, filterType, freq, rq)`
State-variable filter with LP/HP/BP modes.
- `sig`: Input signal
- `filterType`: 0=LP, 1=HP, 2=BP
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
    ]
}
```

**minimal.scd**
```supercollider
SynthDef(\minimal, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var brightness;
    
    freq = In.kr(freqBus);
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
2. **Use `~ensure2ch.`** at the end — generator buses are stereo
3. **Keep CPU low** — these run 8× simultaneously
4. **Test edge cases** — extreme freq, cutoff, resonance values
5. **Add the print statement** — confirms successful load

---

## Register in GENERATOR_CYCLE

After creating files, add to `src/config/__init__.py`:

```python
GENERATOR_CYCLE = [
    "Empty",
    # ... existing generators ...
    "Minimal",  # Your new generator
]
```

The name must match `"name"` in the JSON exactly.
