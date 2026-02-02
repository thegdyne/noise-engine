# How to Create a Pack

**Status:** Reference doc for creating standalone generator packs
**Prerequisite:** [How to Create a Generator](HOWTO_CREATE_GENERATOR.md)

## Overview

A pack is a folder in `packs/` that bundles one or more generators with a manifest. Packs are auto-discovered on startup -- no code changes needed. Drop the folder in, restart, and it appears in the pack dropdown.

## Directory Structure

```
packs/
  my_pack/
    manifest.json           # Pack metadata (required)
    generators/
      my_generator.json     # Generator config (one per generator)
      my_generator.scd      # SuperCollider SynthDef (one per generator)
```

Each generator is exactly 2 files (`.json` + `.scd`) in the `generators/` folder, same as core generators. See [How to Create a Generator](HOWTO_CREATE_GENERATOR.md) for the file format.

## Step 1: Create the Folder

```bash
mkdir -p packs/my_pack/generators
```

## Step 2: Write manifest.json

```json
{
  "pack_format": 1,
  "pack_id": "my_pack",
  "name": "My Pack",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Short description of the pack",
  "url": "",
  "enabled": true,
  "generators": [
    "my_generator"
  ]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `pack_format` | Yes | Always `1` |
| `pack_id` | Yes | Must match the folder name |
| `name` | Yes | Display name in the pack dropdown |
| `enabled` | Yes | Set `false` to hide the pack without deleting it |
| `generators` | Yes | List of file stems (no `.json` extension) |
| `version` | No | Semver string |
| `author` | No | Author name |
| `description` | No | Short description |
| `url` | No | Link to source repo |

## Step 3: Create Generator Files

### JSON Config

```json
{
  "name": "My Generator",
  "synthdef": "mypack_my_generator",
  "output_trim_db": -6.0,
  "custom_params": [
    {
      "key": "param1",
      "label": "P1",
      "tooltip": "What this knob does",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "curve": "lin",
      "unit": ""
    }
  ]
}
```

**Important:** The `synthdef` value must be globally unique. Use your pack ID as a prefix to avoid collisions (e.g. `mypack_my_generator`, not just `my_generator`). If a pack synthdef name matches a core generator, the pack generator will be skipped with a warning.

### SynthDef (.scd)

```supercollider
SynthDef(\mypack_my_generator, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 1);  // Number must match custom_params count

    freq = In.kr(freqBus);

    // === YOUR SOUND SOURCE ===
    sig = SinOsc.ar(freq) * p[0];

    // === MANDATORY TAIL ===
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] mypack_my_generator loaded".postln;
```

Rules:
- SynthDef symbol must match the `synthdef` field in the JSON
- Signature: `|out, freqBus, customBus0|` (minimum required args)
- Read custom params with `In.kr(customBus0, N)` where N = number of custom_params
- End with `NumChannels.ar(sig, 2)` then `ReplaceOut.ar(out, sig)`
- No filter, envelope, or limiter code -- the end-stage handles all of that
- Maximum 5 custom params

## Step 4: Restart

Restart Noise Engine. The pack appears in the pack dropdown automatically. SC auto-loads all `.scd` files from pack `generators/` folders on boot.

## How It Works

On startup:

1. **Python** (`src/config/__init__.py`) scans every folder in `packs/` for a `manifest.json`. Enabled packs get their generators added to the cycle after core generators.
2. **SuperCollider** (`supercollider/init.scd`) independently scans the same folders and loads every `.scd` file it finds, registering the SynthDefs.
3. When a user selects a pack generator, Python tells SC to swap to that SynthDef on the slot's intermediate bus.

Packs load **before** core in SC, so if a pack accidentally defines a SynthDef with the same name as a core generator, the core version wins (it loads second and overwrites).

## Worked Example: Buchla 258

The `packs/buchla_258/` pack wraps the B258 Dual Oscillator as a standalone pack:

```
packs/buchla_258/
  manifest.json
  generators/
    b258_osc.json
    b258_osc.scd
```

**manifest.json:**
```json
{
  "pack_format": 1,
  "pack_id": "buchla_258",
  "name": "Buchla 258",
  "version": "1.0.0",
  "author": "Noise Engine",
  "description": "Buchla 258 Dual Oscillator - forensic DNA clone",
  "enabled": true,
  "generators": ["b258_osc"]
}
```

The generator JSON and SCD are copies of the core b258_osc files with a different synthdef name (`buchla258_b258_osc` instead of `forge_core_b258_osc`).

## Disabling a Pack

Set `"enabled": false` in `manifest.json`. The pack folder stays on disk but its generators won't appear in the UI.

## Multiple Generators

A pack can contain any number of generators. List all file stems in the manifest:

```json
{
  "generators": ["osc_one", "osc_two", "noise_gen"]
}
```

Each needs its own `.json` + `.scd` pair in `generators/`.

## Checklist

- [ ] Folder created in `packs/` with `generators/` subfolder
- [ ] `manifest.json` has `pack_format: 1`, `pack_id` matches folder name, `enabled: true`
- [ ] `generators` array lists every generator file stem
- [ ] Each generator has matching `.json` and `.scd` files
- [ ] `synthdef` field in JSON matches SynthDef symbol in `.scd`
- [ ] `synthdef` name is globally unique (use pack prefix)
- [ ] `.scd` uses `ReplaceOut.ar` and `NumChannels.ar(sig, 2)` tail
- [ ] No filter/envelope/limiter code in the SynthDef
- [ ] Restart confirms pack appears in dropdown
