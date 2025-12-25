#!/usr/bin/env python3
"""Generate init presets for CQD_Forge packs.

Usage:
    python tools/forge_gen_preset.py packs/pack_name/
    python tools/forge_gen_preset.py --all
    python tools/forge_gen_preset.py --missing
    python tools/forge_gen_preset.py --all --install
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

PRESETS_DIR = Path.home() / "noise-engine-presets"

DEFAULT_SLOT = {
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
        "custom_4": 0.5,
    },
    "filter_type": 0,
    "env_source": 0,
    "clock_rate": 6,
    "midi_channel": 0,
    "transpose": 2,
    "portamento": 0.0,
}

DEFAULT_CHANNEL = {
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
    "hi_cut": False,
}

DEFAULT_MASTER = {
    "volume": 0.8,
    "eq_hi": 120,
    "eq_mid": 120,
    "eq_lo": 120,
    "comp_threshold": 0.8,
    "comp_ratio": 2.0,
    "limiter": True,
}


def get_generator_names(pack_path: Path) -> list[str]:
    """Read generator display names from pack."""
    manifest_path = pack_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json in {pack_path}")

    with open(manifest_path) as f:
        manifest = json.load(f)

    generators = manifest.get("generators", [])
    names = []

    for gen_id in generators:
        gen_json = pack_path / "generators" / f"{gen_id}.json"
        if gen_json.exists():
            with open(gen_json) as f:
                gen_data = json.load(f)
                names.append(gen_data.get("name", gen_id.upper()))
        else:
            names.append(gen_id.upper())

    return names


def generate_preset(pack_path: Path) -> dict:
    """Generate a full preset for a pack."""
    manifest_path = pack_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    pack_id = manifest.get("pack_id", pack_path.name)
    pack_name = manifest.get("name", pack_id.replace("_", " ").title())
    gen_names = get_generator_names(pack_path)

    slots = []
    for name in gen_names:
        slot = {"generator": name}
        slot.update(DEFAULT_SLOT)
        slots.append(slot)

    while len(slots) < 8:
        slot = {"generator": ""}
        slot.update(DEFAULT_SLOT)
        slots.append(slot)

    preset = {
        "version": 2,
        "mapping_version": 1,
        "name": pack_name,
        "pack": pack_id,
        "slots": slots,
        "mixer": {
            "channels": [DEFAULT_CHANNEL.copy() for _ in range(8)],
            "master_volume": 0.8,
        },
        "bpm": 120,
        "master": DEFAULT_MASTER.copy(),
    }

    return preset


def get_pack_id(pack_path: Path) -> str:
    """Get pack_id from manifest or directory name."""
    manifest_path = pack_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    return manifest.get("pack_id", pack_path.name)


def save_preset(pack_path: Path, install: bool = False, dry_run: bool = False) -> Path:
    """Generate and save preset for a pack."""
    pack_id = get_pack_id(pack_path)
    preset = generate_preset(pack_path)

    preset_filename = f"{pack_id}.json"
    pack_preset_path = pack_path / preset_filename

    if dry_run:
        print(f"Would create: {pack_preset_path}")
        if install:
            print(f"Would install to: {PRESETS_DIR / preset_filename}")
    else:
        with open(pack_preset_path, "w") as f:
            json.dump(preset, f, indent=2)
        print(f"Created: {pack_preset_path}")

        if install:
            PRESETS_DIR.mkdir(parents=True, exist_ok=True)
            install_path = PRESETS_DIR / preset_filename
            shutil.copy(pack_preset_path, install_path)
            print(f"Installed: {install_path}")

    return pack_preset_path


def get_forge_packs(packs_dir: Path) -> list[Path]:
    """Get all CQD_Forge packs."""
    forge_packs = []
    for pack_path in sorted(packs_dir.iterdir()):
        if not pack_path.is_dir():
            continue
        manifest_path = pack_path / "manifest.json"
        if not manifest_path.exists():
            continue
        with open(manifest_path) as f:
            manifest = json.load(f)
        if manifest.get("author") == "CQD_Forge":
            forge_packs.append(pack_path)
    return forge_packs


def pack_has_preset(pack_path: Path) -> bool:
    """Check if pack has {pack_id}.json preset."""
    pack_id = get_pack_id(pack_path)
    return (pack_path / f"{pack_id}.json").exists()


def main():
    parser = argparse.ArgumentParser(description="Generate init presets for Forge packs")
    parser.add_argument("pack_path", nargs="?", help="Path to pack directory")
    parser.add_argument("--all", action="store_true", help="Generate for all Forge packs")
    parser.add_argument("--missing", action="store_true", help="Generate only for packs without preset")
    parser.add_argument("--install", action="store_true", help="Also copy preset to ~/noise-engine-presets/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    parser.add_argument("--packs-dir", default="packs", help="Packs directory (default: packs)")
    args = parser.parse_args()

    packs_dir = Path(args.packs_dir)

    if args.all or args.missing:
        forge_packs = get_forge_packs(packs_dir)
        print(f"Found {len(forge_packs)} Forge packs\n")

        created = 0
        skipped = 0

        for pack_path in forge_packs:
            if args.missing and pack_has_preset(pack_path):
                print(f"Skipping {pack_path.name} (has preset)")
                skipped += 1
                continue

            save_preset(pack_path, install=args.install, dry_run=args.dry_run)
            created += 1

        print(f"\nCreated: {created}, Skipped: {skipped}")

    elif args.pack_path:
        pack_path = Path(args.pack_path)
        if not pack_path.exists():
            print(f"Error: {pack_path} does not exist", file=sys.stderr)
            sys.exit(1)
        save_preset(pack_path, install=args.install, dry_run=args.dry_run)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
