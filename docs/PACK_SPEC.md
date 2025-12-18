# Noise Engine Pack Specification

*How to create and distribute generator packs*

---

## Overview

Packs are collections of generators that extend Noise Engine. Each pack lives in its own folder inside `packs/` and contains a manifest plus generator files.

**Security note:** Packs contain executable SuperCollider code. Only install packs from trusted sources.

---

## Quick Start

1. Create a folder in `packs/` (e.g., `packs/my_synths/`)
2. Add a `manifest.json` (see below)
3. Create a `generators/` subfolder with your `.json` + `.scd` pairs
4. Restart Noise Engine

See `packs/_example/` for a working reference.

---

## Directory Structure

```
packs/
└── my_pack/
    ├── manifest.json          # Required: pack metadata
    ├── README.md              # Optional: documentation
    └── generators/
        ├── my_synth.json      # Generator UI config
        ├── my_synth.scd       # Generator SynthDef
        ├── another.json
        └── another.scd
```

---

## Manifest Format

**`manifest.json`**

```json
{
    "pack_format": 1,
    "name": "My Synth Pack",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "A collection of custom generators",
    "url": "https://github.com/you/my-pack",
    "enabled": true,
    "generators": [
        "my_synth",
        "another"
    ]
}
```

### Required Fields

| Field | Description |
|-------|-------------|
| `pack_format` | Always `1` (for future compatibility) |
| `name` | Display name shown in UI |
| `enabled` | `true` to load, `false` to skip |
| `generators` | List of generator file stems or display names |

### Optional Fields

| Field | Description |
|-------|-------------|
| `version` | Semver version (e.g., "1.0.0") |
| `author` | Pack creator name |
| `description` | Short description |
| `url` | Link to source/documentation |

### Generator List

Each entry in `generators` can be:
- **File stem** (recommended): `"my_synth"` matches `my_synth.json`
- **Display name**: `"My Synth"` matches the `"name"` field in a generator's JSON

File stem matching is faster and unambiguous. Display name lookup is fallback.

---

## Generator Files

Each generator needs two files with matching names:

### JSON Config (`generators/my_synth.json`)

```json
{
    "name": "My Synth",
    "synthdef": "mypack_my_synth",
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

| Field | Description |
|-------|-------------|
| `name` | Display name in generator dropdown |
| `synthdef` | Must match `SynthDef(\name, ...)` exactly |
| `custom_params` | Up to 5 custom parameters (P1-P5) |

### SynthDef (`generators/my_synth.scd`)

```supercollider
SynthDef(\mypack_my_synth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                              filterTypeBus, envEnabledBus, envSourceBus=0, 
                              clockRateBus, clockTrigBus,
                              midiTrigBus=0, slotIndex=0,
                              customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var brightness;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    brightness = In.kr(customBus0);
    
    // Your synthesis code
    sig = Saw.ar(freq) * brightness;
    
    // Processing chain (use helper functions)
    sig = ~stereoSpread.(sig, 0.3, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, 
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    
    Out.ar(out, sig);
}).add;

"  ✓ mypack_my_synth loaded".postln;
```

---

## SynthDef Naming

**Important:** SynthDef names must be globally unique across all packs and core generators.

Recommended: Prefix with your pack name to avoid collisions.

```supercollider
// Good - namespaced
SynthDef(\mypack_bass, { ... })
SynthDef(\mypack_lead, { ... })

// Bad - might collide with core or other packs
SynthDef(\bass, { ... })
SynthDef(\lead, { ... })
```

If a SynthDef name collides with a core generator or previously loaded pack, your generator will be skipped.

---

## Helper Functions

These are available in all SynthDefs:

| Function | Description |
|----------|-------------|
| `~stereoSpread.(sig, rate, width)` | Mono → stereo with LFO panning |
| `~multiFilter.(sig, type, freq, rq)` | LP/HP/BP filter (type: 0/1/2) |
| `~envVCA.(sig, envSource, ...)` | Envelope-controlled VCA |
| `~ensure2ch.(sig)` | Ensure stereo output |

See `docs/GENERATOR_SPEC.md` for full documentation.

---

## Custom Parameter Options

```json
{
    "key": "param_key",      // Internal name (used in SynthDef)
    "label": "LBL",          // 3-char display label
    "tooltip": "Description", 
    "default": 0.5,          // Initial value (0-1 normalized)
    "min": 0.0,              // Minimum real value
    "max": 1.0,              // Maximum real value
    "curve": "lin",          // "lin" or "exp"
    "unit": "",              // Display unit (Hz, ms, dB, etc.)
    "steps": 4               // Optional: discrete steps
}
```

---

## Enable/Disable Packs

Set `"enabled": false` in `manifest.json` to disable a pack without deleting it.

Disabled packs won't appear in the UI, but SuperCollider may still load the SynthDefs.

---

## Distribution

To share your pack:

1. Zip or tar your pack folder
2. Users extract to their `packs/` directory
3. Restart Noise Engine

```bash
# Create distributable
cd packs
tar -cvf my_pack.tar my_pack/

# Install
cd /path/to/noise-engine/packs
tar -xvf my_pack.tar
```

---

## Troubleshooting

**Generator doesn't appear in dropdown**
- Check `manifest.json` is valid JSON
- Verify generator name in manifest matches file stem or JSON `"name"`
- Check console for loading errors

**SynthDef conflicts**
- Rename your SynthDef with a unique prefix
- Check console for "synthdef already loaded" warnings

**No sound**
- Verify `Out.ar(out, sig)` at end of SynthDef
- Check `~ensure2ch.(sig)` is called
- Test with simple signal first

---

## See Also

- `docs/GENERATOR_SPEC.md` — Full generator creation guide
- `packs/_example/` — Working example pack
- `docs/PACK_LOADER_SPEC.md` — Implementation details
