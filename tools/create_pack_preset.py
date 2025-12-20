#!/usr/bin/env python3
"""Create a base preset for a pack - loads all generators in order."""

import json
import sys
from pathlib import Path
from datetime import datetime

PRESETS_DIR = Path.home() / "noise-engine-presets"


def create_pack_preset(pack_name: str) -> dict:
    """Create a preset loading all generators from a pack."""
    
    packs_dir = Path(__file__).parent.parent / "packs"
    pack_path = packs_dir / pack_name
    
    if not pack_path.exists():
        print(f"Error: Pack '{pack_name}' not found")
        sys.exit(1)
    
    manifest_path = pack_path / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: No manifest.json in {pack_name}")
        sys.exit(1)
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    generators = manifest.get("generators", [])
    pack_display_name = manifest.get("name", pack_name)
    
    # Build slots (up to 8)
    slots = []
    for i, gen_name in enumerate(generators[:8]):
        slots.append({
            "generator": gen_name.upper(),
            "params": {
                "frequency": 0.5,
                "cutoff": 1.0,
                "resonance": 0.0,
                "attack": 0.0,
                "decay": 0.73,
                "custom_0": 0.5,
                "custom_1": 0.5,
                "custom_2": 0.5,
                "custom_3": 0.5,
                "custom_4": 0.5
            },
            "filter_type": 0,
            "env_source": 0,
            "clock_rate": 6,
            "midi_channel": 0
        })
    
    # Fill remaining slots with null generator
    for i in range(len(slots), 8):
        slots.append({
            "generator": None,
            "params": {
                "frequency": 0.5,
                "cutoff": 1.0,
                "resonance": 0.0,
                "attack": 0.0,
                "decay": 0.73,
                "custom_0": 0.5,
                "custom_1": 0.5,
                "custom_2": 0.5,
                "custom_3": 0.5,
                "custom_4": 0.5
            },
            "filter_type": 0,
            "env_source": 0,
            "clock_rate": 6,
            "midi_channel": 0
        })
    
    # Build mixer channels (default values)
    channels = []
    for i in range(8):
        channels.append({
            "volume": 0.8,
            "pan": 0.5,
            "mute": False,
            "solo": False,
            "eq_hi": 100,
            "eq_mid": 100,
            "eq_lo": 100,
            "gain": 0,
            "echo_send": 0,
            "verb_send": 0,
            "lo_cut": False,
            "hi_cut": False
        })
    
    # Build mod sources (4 slots, alternating LFO/Sloth)
    mod_slots = []
    for i in range(4):
        if i % 2 == 0:
            mod_slots.append({
                "generator_name": "LFO",
                "params": {
                    "rate": 0.5,
                    "shape": 0.5,
                    "pattern": 0.0,
                    "rotate": 0.0
                },
                "output_wave": [0, 0, 0, 0],
                "output_phase": [0, 0, 0, 0],
                "output_polarity": [0, 0, 0, 0]
            })
        else:
            mod_slots.append({
                "generator_name": "Sloth",
                "params": {
                    "bias": 0.5
                },
                "output_wave": [0, 0, 0, 0],
                "output_phase": [0, 0, 0, 0],
                "output_polarity": [0, 0, 0, 0]
            })
    
    # Build preset
    preset = {
        "version": 2,
        "mapping_version": 1,
        "name": f"{pack_display_name} Init",
        "created": datetime.now().isoformat(),
        "slots": slots,
        "mixer": {
            "channels": channels,
            "master_volume": 0.8
        },
        "bpm": 120,
        "master": {
            "volume": 0.8,
            "eq_hi": 120,
            "eq_mid": 120,
            "eq_lo": 120,
            "eq_hi_kill": 0,
            "eq_mid_kill": 0,
            "eq_lo_kill": 0,
            "eq_locut": 0,
            "eq_bypass": 0,
            "comp_threshold": 100,
            "comp_makeup": 0,
            "comp_ratio": 1,
            "comp_attack": 4,
            "comp_release": 4,
            "comp_sc": 0,
            "comp_bypass": 0,
            "limiter_ceiling": 590,
            "limiter_bypass": 0
        },
        "mod_sources": {
            "slots": mod_slots
        },
        "mod_routing": {
            "connections": []
        }
    }
    
    return preset


def main():
    if len(sys.argv) < 2:
        # List available packs
        packs_dir = Path(__file__).parent.parent / "packs"
        packs = [d.name for d in packs_dir.iterdir() 
                 if d.is_dir() and not d.name.startswith("_") and d.name != "user"]
        print("Usage: python create_pack_preset.py <pack-name>")
        print(f"\nAvailable packs: {', '.join(sorted(packs))}")
        sys.exit(1)
    
    pack_name = sys.argv[1]
    preset = create_pack_preset(pack_name)
    
    # Ensure presets directory exists
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    safe_name = preset["name"].lower().replace(" ", "-")
    preset_path = PRESETS_DIR / f"{safe_name}.json"
    
    # Check for overwrite
    if preset_path.exists():
        response = input(f"Preset '{preset_path.name}' exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled")
            sys.exit(0)
    
    with open(preset_path, 'w') as f:
        json.dump(preset, f, indent=2)
    
    print(f"✅ Created: {preset_path}")
    print(f"   Generators: {', '.join(s['generator'] for s in preset['slots'] if s['generator'])}")


if __name__ == "__main__":
    main()
