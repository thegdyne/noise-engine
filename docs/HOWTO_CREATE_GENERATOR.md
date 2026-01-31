# How to Create a Generator

**Status:** Reference doc for the decoupled end-stage architecture

## Architecture Overview

Generators in Noise Engine are **lightweight** -- they produce raw sound only. All shared processing (filter, envelope, limiter, DC removal) is handled by a persistent **end-stage** synth that sits between the generator and the channel strip.

```
Generator  -->  Intermediate Bus  -->  End-Stage  -->  Channel Bus  -->  Channel Strip
(your code)     (per-slot, stereo)     (shared DSP)    (per-slot)       (volume/EQ/pan/FX sends)
```

The generator writes to an intermediate bus using `ReplaceOut`. The end-stage reads from that bus and applies the full output chain. This means:

- No filter code in generators
- No envelope/VCA code in generators
- No limiter or LeakDC in generators
- Generator swaps are glitch-free (ReplaceOut overwrites the bus)

## What You Need

Each generator is exactly **2 files** in `packs/core/generators/`:

| File | Purpose |
|------|---------|
| `my_generator.json` | Metadata, custom param definitions, output trim |
| `my_generator.scd` | SuperCollider SynthDef (sound source only) |

The `synthdef` field in the JSON must match the SynthDef symbol in the `.scd` file.

## JSON Config

```json
{
  "name": "My Generator",
  "synthdef": "myGenerator",
  "synthesis_method": "subtractive/filtered_osc",
  "custom_params": [
    {
      "key": "param_one",
      "label": "P1L",
      "tooltip": "What this parameter does",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    }
  ],
  "output_trim_db": 0.0,
  "midi_retrig": false
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name in the UI |
| `synthdef` | Yes | SynthDef symbol name (must match `.scd`) |
| `synthesis_method` | No | Category string for organisation |
| `custom_params` | Yes | Array of P1-P5 param definitions (max 5) |
| `output_trim_db` | No | dB attenuation for hot generators (default: 0.0) |
| `midi_retrig` | No | Enable per-note retriggering (default: false) |
| `pitch_target` | No | Pitch tracking target (default: null) |

### Custom Param Fields

| Field | Required | Description |
|-------|----------|-------------|
| `key` | Yes | Internal identifier (snake_case) |
| `label` | Yes | 3-character UI label (uppercase) |
| `tooltip` | No | Hover text description |
| `default` | Yes | Default value (within min/max range) |
| `min` | Yes | Minimum value |
| `max` | Yes | Maximum value |
| `curve` | Yes | `"lin"` or `"exp"` |
| `steps` | No | Discrete steps (e.g. `4` for a 4-position switch) |
| `unit` | No | Display unit (`"Hz"`, `"s"`, `"x"`, `""`) |

### output_trim_db

Use this to normalise loud generators. The value is applied as gain in the channel strip:

- `0.0` -- no change (default, use for most generators)
- `-3.0` -- attenuate by 3dB (use for generators that are noticeably hot)
- `-6.0` -- attenuate by 6dB (use for very hot generators)

### midi_retrig

Set `true` for percussive/struck generators that should retrigger their internal envelopes on each MIDI note. When `false`, the generator runs continuously and the end-stage envelope handles gating.

## SynthDef (.scd File)

### Template

```supercollider
// core/my_generator — Lightweight end-stage generator
/*
My Generator
Brief description of the synthesis approach

Features:
  - Feature one
  - Feature two

Custom params:
  - P1 param_one: What it controls
  - P2 param_two: What it controls
  - P3 param_three: What it controls
  - P4 param_four: What it controls
  - P5 param_five: What it controls
*/

SynthDef(\myGenerator, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var paramOne, paramTwo, paramThree, paramFour, paramFive;

    freq = In.kr(freqBus);

    paramOne = p[0];    // P1
    paramTwo = p[1];    // P2
    paramThree = p[2];  // P3
    paramFour = p[3];   // P4
    paramFive = p[4];   // P5

    // === SOUND SOURCE ===
    sig = SinOsc.ar(freq);  // Your DSP here

    // Optional: stereo movement
    sig = ~stereoSpread.(sig, 0.2, 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] myGenerator loaded".postln;
```

### Rules

1. **Function signature is always `|out, freqBus, customBus0|`** -- nothing else. The end-stage owns filter, envelope, clock, and MIDI buses.

2. **Read custom params as a block:** `var p = In.kr(customBus0, 5);` then index with `p[0]` through `p[4]`. Always read 5 even if you use fewer.

3. **Use `ReplaceOut.ar(out, sig)`** -- never `Out.ar`. ReplaceOut overwrites the intermediate bus, which prevents volume doubling and enables glitch-free generator swaps.

4. **Ensure stereo output:** End with `NumChannels.ar(sig, 2)` to guarantee exactly 2 channels. Mono signals become dual-mono, >2 channels get mixed down.

5. **Print load confirmation:** End with `"  [x] myGenerator loaded".postln;`

6. **Comment header:** Include the `// core/name — Lightweight end-stage generator` header and a block comment documenting features and custom params.

### What NOT to Put in Generators

The end-stage handles all of this -- do not duplicate:

| Do NOT include | Handled by |
|----------------|------------|
| `~multiFilter` | End-stage |
| `~envVCA` | End-stage |
| `Limiter.ar` | End-stage |
| `LeakDC.ar` | End-stage |
| `cutoffBus`, `resBus`, `attackBus`, `decayBus` | End-stage |
| `filterTypeBus`, `envSourceBus`, `envEnabledBus` | End-stage |
| `clockRateBus`, `clockTrigBus`, `midiTrigBus` | End-stage |
| `slotIndex` | End-stage |

### Available Helper

| Helper | Purpose | Example |
|--------|---------|---------|
| `~stereoSpread.(sig, rate, width)` | Slow stereo movement | `~stereoSpread.(sig, 0.2, 0.3)` |

This is the only helper generators should use. It adds gentle stereo animation. Parameters: `rate` (LFO speed in Hz, keep low ~0.05-0.3), `width` (pan range, 0-1).

## Complete Example: Drone Generator

### drone.json

```json
{
  "name": "Drone",
  "synthdef": "drone",
  "synthesis_method": "subtractive/filtered_osc",
  "custom_params": [
    {
      "key": "detune",
      "label": "DTN",
      "tooltip": "Oscillator detuning amount",
      "default": 0.3,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    },
    {
      "key": "voices",
      "label": "VOX",
      "tooltip": "Number of voices (thickness)",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    },
    {
      "key": "movement",
      "label": "MOV",
      "tooltip": "Internal movement/modulation",
      "default": 0.3,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    },
    {
      "key": "sub",
      "label": "SUB",
      "tooltip": "Sub oscillator level",
      "default": 0.3,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    },
    {
      "key": "air",
      "label": "AIR",
      "tooltip": "Breathy/airy texture",
      "default": 0.2,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    }
  ]
}
```

### drone.scd

```supercollider
// core/drone — Lightweight end-stage generator
SynthDef(\drone, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var detune, voices, movement, subLevel, air;

    freq = In.kr(freqBus);

    detune = p[0];
    voices = p[1];
    movement = p[2];
    subLevel = p[3];
    air = p[4];

    // Internal movement LFOs
    moveLFO1 = LFNoise2.kr(0.1) * movement * 0.02;

    // Multi-voice oscillators with detune
    sig = Saw.ar(freq * (1 + (detune * -0.04) + moveLFO1));
    sig = sig + Saw.ar(freq * (1 + (detune * 0.04) - moveLFO1));
    sig = sig * 0.3;

    // Sub oscillator
    sig = sig + (SinOsc.ar(freq * 0.5) * subLevel * 0.4);

    // Air texture
    sig = sig + (BPF.ar(PinkNoise.ar, freq * 3, 1.0) * air * 0.15);

    sig = ~stereoSpread.(sig, 0.08, 0.5);
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] drone loaded".postln;
```

## Complete Example: 808 Kick (Percussive)

### kick_808.json

```json
{
  "name": "808 Kick",
  "synthdef": "kick_808",
  "synthesis_method": "spectral/spectral_drone",
  "custom_params": [
    {
      "key": "punch",
      "label": "PCH",
      "tooltip": "Pitch envelope depth (click/punch)",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    },
    {
      "key": "tone",
      "label": "TNE",
      "tooltip": "Tone/Body balance (fundamental to harmonics)",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    },
    {
      "key": "decay_time",
      "label": "DKY",
      "tooltip": "Kick decay length",
      "default": 0.5,
      "min": 0.1,
      "max": 2.0,
      "curve": "exp",
      "unit": "s"
    },
    {
      "key": "drive",
      "label": "DRV",
      "tooltip": "Saturation/Drive amount",
      "default": 0.3,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    },
    {
      "key": "click",
      "label": "CLK",
      "tooltip": "Click transient level",
      "default": 0.3,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    }
  ],
  "output_trim_db": -3.0,
  "midi_retrig": true
}
```

Key differences from the drone:
- `output_trim_db: -3.0` because kicks are hot
- `midi_retrig: true` because each note should retrigger the internal envelope
- `curve: "exp"` on decay_time for natural time scaling (0.1s-2.0s)

### kick_808.scd

```supercollider
// core/kick_808 — Lightweight end-stage generator
SynthDef(\kick_808, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var punch, tone, decayTime, drive, click;
    var trig, pitchEnv, ampEnv, body, clickSig;

    freq = In.kr(freqBus);

    punch = p[0];
    tone = p[1];
    decayTime = p[2];
    drive = p[3];
    click = p[4];

    // One-shot trigger (end-stage handles retriggering via midi_retrig)
    trig = Impulse.ar(0);

    // Internal envelopes (these are part of the sound character, not gating)
    pitchEnv = EnvGen.ar(Env.perc(0.001, 0.06, 1, -8), trig);
    ampEnv = EnvGen.ar(Env.perc(0.001, decayTime, 1, -4), trig);

    // Sound source
    body = SinOsc.ar(freq + (pitchEnv * freq * punch * 4));
    sig = body * ampEnv;

    // Click transient
    clickSig = HPF.ar(WhiteNoise.ar, 1000) * EnvGen.ar(Env.perc(0.001, 0.015), trig);
    sig = sig + (clickSig * click);

    // Saturation
    sig = (sig * (1 + (drive * 3))).tanh;

    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] kick_808 loaded".postln;
```

Note: percussive generators use their own internal amplitude envelopes (part of the character of the sound), but the end-stage envelope still applies on top for gating/ducking.

## End-Stage Processing Chain

For reference, this is what the end-stage applies to your generator's output:

1. **LeakDC** -- removes DC offset
2. **multiFilter** -- LP / HP / BP / Notch / LP2 / OFF (user-selected per slot)
3. **envVCA** -- envelope with OFF / CLK / MIDI trigger sources
4. **Mute gate** -- click-free muting
5. **Limiter** -- safety limiter at 0.95
6. **ensure2ch** -- stereo safety (redundant with your NumChannels but belt-and-braces)

After the end-stage, the channel strip adds: trim (output_trim_db), 3-band EQ, gain, pan, volume fader, FX sends.

## Checklist

Before submitting a new generator:

- [ ] JSON `synthdef` matches SynthDef symbol in `.scd`
- [ ] Function signature is exactly `|out, freqBus, customBus0|`
- [ ] Custom params read with `In.kr(customBus0, 5)` (always 5)
- [ ] No filter/envelope/limiter code (end-stage handles it)
- [ ] Ends with `NumChannels.ar(sig, 2)` then `ReplaceOut.ar(out, sig)`
- [ ] Labels are 3 characters uppercase
- [ ] Defaults are within min/max range
- [ ] `output_trim_db` set if generator is hot
- [ ] `midi_retrig: true` if percussive
- [ ] Load confirmation print at end of `.scd`
- [ ] Max 5 custom params
