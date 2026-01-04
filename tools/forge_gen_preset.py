#!/usr/bin/env python3
"""Generate init presets for CQD_Forge packs.

Usage:
    python tools/forge_gen_preset.py packs/pack_name/
    python tools/forge_gen_preset.py packs/pack_name/ --install-only
    python tools/forge_gen_preset.py --all
    python tools/forge_gen_preset.py --all --install-only
    python tools/forge_gen_preset.py --missing
    python tools/forge_gen_preset.py --all --install
    python tools/forge_gen_preset.py --sync
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
    "env_source": 2,
    "clock_rate": 6,
    "midi_channel": 0,
    "transpose": 2,
    "portamento": 0.0,
}

DEFAULT_CHANNEL = {
    "volume": 0.0,
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

# Match MasterState defaults from preset_schema.py
DEFAULT_MASTER = {
    "volume": 0.8,
    # EQ
    "eq_hi": 120,
    "eq_mid": 120,
    "eq_lo": 120,
    "eq_hi_kill": 0,
    "eq_mid_kill": 0,
    "eq_lo_kill": 0,
    "eq_locut": 0,
    "eq_bypass": 0,
    # Compressor
    "comp_threshold": 100,   # 0-400, 200=0dB, 100 is gentle
    "comp_makeup": 0,        # 0-200
    "comp_ratio": 1,         # index: 0=2:1, 1=4:1, 2=10:1
    "comp_attack": 4,        # index 0-5
    "comp_release": 4,       # index 0-4
    "comp_sc": 0,            # index 0-5
    "comp_bypass": 0,        # 0=on, 1=bypassed
    # Limiter
    "limiter_ceiling": 590,  # 0-600, 590=-0.1dB
    "limiter_bypass": 0,     # 0=on, 1=bypassed
}

# Match FXState defaults from preset_schema.py
DEFAULT_FX = {
    "heat": {
        "bypass": True,
        "circuit": 0,
        "drive": 0,
        "mix": 100,
    },
    "echo": {
        "time": 40,
        "feedback": 30,
        "tone": 70,
        "wow": 10,
        "spring": 0,
        "verb_send": 0,
        "return_level": 50,
    },
    "reverb": {
        "size": 50,
        "decay": 50,
        "tone": 70,
        "return_level": 30,
    },
    "dual_filter": {
        "bypass": True,
        "drive": 0,
        "freq1": 50,
        "reso1": 0,
        "mode1": 1,
        "freq2": 35,
        "reso2": 0,
        "mode2": 1,
        "harmonics": 0,
        "routing": 0,
        "mix": 100,
    },
}

# =============================================================================
# Modulator Defaults
# =============================================================================
# These match what modulator_slot.py get_state() returns and set_state() expects.
#
# MOD_CLOCK_RATES = ['/64', '/32', '/16', '/8', '/4', '/2', '1', 'x2', 'x4', 'x8', 'x16', 'x32']
#                     0      1      2      3     4     5    6    7     8     9     10     11
#
# Rate mapping: idx = round(rate_norm * 11) for 12 items (indices 0-11)
#   /32 → idx 1 → rate_norm = 1/11 ≈ 0.091
#   /8  → idx 3 → rate_norm = 3/11 ≈ 0.273
#
# Waveforms (output_wave): 0=SAW, 1=TRI, 2=SQR, 3=SIN, 4=S&H
# Phases (output_phase): 0=0°, 1=45°, 2=90°, 3=135°, 4=180°, 5=225°, 6=270°, 7=315°
# Sloth modes: 0=Torpor (15-30s), 1=Apathy (60-90s), 2=Inertia (30-40min)
# Polarity: 0=NORM, 1=INV
# =============================================================================

# LFO: Has wave, phase, polarity per output
DEFAULT_MOD_SLOT_LFO = {
    "generator_name": "LFO",
    "params": {
        "mode": 0,           # 0=CLK
        "rate": 0.091,       # /32 (index 1 of 12)
    },
    "output_wave": [3, 3, 3, 3],      # TRI on all 4
    "output_phase": [0, 2, 4, 6],     # 0°, 90°, 180°, 270° (quadrature)
    "output_polarity": [0, 0, 0, 0],  # NORM on all 4
}

# Sloth: Only mode param, polarity per output
DEFAULT_MOD_SLOT_SLOTH = {
    "generator_name": "Sloth",
    "params": {
        "mode": 1,           # 1=Apathy (60-90s cycles)
    },
    "output_polarity": [0, 0, 0, 0],  # X=NORM, Y=NORM, Z=NORM, R=NORM
}

# ARSEq+: mode, clock_mode, rate params; envelope settings per output
DEFAULT_MOD_SLOT_ARSEQ = {
    "generator_name": "ARSEq+",
    "params": {
        "mode": 0,           # 0=SEQ
        "clock_mode": 0,     # 0=CLK
        "rate": 0.489,       # /8 (index 3 of 12)
    },
    "output_polarity": [0, 0, 0, 0],  # NORM on all 4
    "env_attack": [0.0, 0.0, 0.0, 0.0],       # Fast attack
    "env_release": [0.2, 0.2, 0.2, 0.2],      # Medium release
    "env_curve": [0.5, 0.5, 0.5, 0.5],        # Linear (0.5 = center)
    "env_sync_mode": [0, 0, 0, 0],            # All SYN (follow master)
    "env_loop_rate": [6, 6, 6, 6],            # 1:1 rate if in LOP mode
}

# SauceOfGrav: Has tension, mass, polarity per output
DEFAULT_MOD_SLOT_SAUCEGRAV = {
    "generator_name": "SauceOfGrav",
    "params": {
        "clock_mode": 0,     # 0=CLK
        "rate": 0.5,
        "depth": 0.5,
        "gravity": 0.5,
        "resonance": 0.5,
        "excursion": 0.5,
        "calm": 0.5,
    },
    "output_polarity": [0, 0, 0, 0],
    "output_tension": [0.30, 0.45, 0.55, 0.70],  # Matches builder defaults
    "output_mass": [0.65, 0.55, 0.45, 0.35],     # Matches builder defaults
}


def _deep_copy_fx():
    """Deep copy DEFAULT_FX to avoid mutation."""
    import copy
    return copy.deepcopy(DEFAULT_FX)


def _deep_copy_mod_slot(slot_dict):
    """Deep copy a mod slot dict to avoid mutation."""
    import copy
    return copy.deepcopy(slot_dict)


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
        "mod_sources": {
            "slots": [
                _deep_copy_mod_slot(DEFAULT_MOD_SLOT_LFO),
                _deep_copy_mod_slot(DEFAULT_MOD_SLOT_SLOTH),
                _deep_copy_mod_slot(DEFAULT_MOD_SLOT_ARSEQ),
                _deep_copy_mod_slot(DEFAULT_MOD_SLOT_SAUCEGRAV),
            ]
        },
        "mod_routing": {"connections": []},
        "fx": _deep_copy_fx(),
    }

    return preset


def get_pack_id(pack_path: Path) -> str:
    """Get pack_id from manifest or directory name."""
    manifest_path = pack_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    return manifest.get("pack_id", pack_path.name)


def install_preset(pack_path: Path, dry_run: bool = False) -> bool:
    """Install existing preset to ~/noise-engine-presets/."""
    pack_id = get_pack_id(pack_path)
    preset_filename = f"{pack_id}.json"
    pack_preset_path = pack_path / preset_filename

    if not pack_preset_path.exists():
        print(f"No preset found: {pack_preset_path}")
        return False

    if dry_run:
        print(f"Would install: {pack_preset_path} -> {PRESETS_DIR / preset_filename}")
    else:
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        install_path = PRESETS_DIR / preset_filename
        shutil.copy(pack_preset_path, install_path)
        print(f"Installed: {install_path}")

    return True


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
    parser.add_argument("--install-only", action="store_true", help="Only install existing presets (no regeneration)")
    parser.add_argument("--sync", action="store_true", help="Install presets missing from ~/noise-engine-presets/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    parser.add_argument("--packs-dir", default="packs", help="Packs directory (default: packs)")
    args = parser.parse_args()

    packs_dir = Path(args.packs_dir)

    if args.sync:
        forge_packs = get_forge_packs(packs_dir)
        print(f"Found {len(forge_packs)} Forge packs\n")

        installed = 0
        skipped = 0
        missing_preset = 0

        for pack_path in forge_packs:
            pack_id = get_pack_id(pack_path)
            preset_filename = f"{pack_id}.json"
            pack_preset_path = pack_path / preset_filename
            installed_path = PRESETS_DIR / preset_filename

            if not pack_preset_path.exists():
                print(f"No preset in pack: {pack_path.name}")
                missing_preset += 1
                continue

            if installed_path.exists():
                skipped += 1
                continue

            if args.dry_run:
                print(f"Would install: {pack_preset_path} -> {installed_path}")
            else:
                PRESETS_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy(pack_preset_path, installed_path)
                print(f"Installed: {installed_path}")
            installed += 1

        print(f"\nInstalled: {installed}, Already present: {skipped}, No pack preset: {missing_preset}")
        return

    if args.all or args.missing:
        forge_packs = get_forge_packs(packs_dir)
        print(f"Found {len(forge_packs)} Forge packs\n")

        created = 0
        installed = 0
        skipped = 0

        for pack_path in forge_packs:
            if args.install_only:
                if install_preset(pack_path, dry_run=args.dry_run):
                    installed += 1
                else:
                    skipped += 1
                continue

            if args.missing and pack_has_preset(pack_path):
                print(f"Skipping {pack_path.name} (has preset)")
                skipped += 1
                continue

            save_preset(pack_path, install=args.install, dry_run=args.dry_run)
            created += 1

        if args.install_only:
            print(f"\nInstalled: {installed}, Skipped: {skipped}")
        else:
            print(f"\nCreated: {created}, Skipped: {skipped}")

    elif args.pack_path:
        pack_path = Path(args.pack_path)
        if not pack_path.exists():
            print(f"Error: {pack_path} does not exist", file=sys.stderr)
            sys.exit(1)
        if args.install_only:
            install_preset(pack_path, dry_run=args.dry_run)
        else:
            save_preset(pack_path, install=args.install, dry_run=args.dry_run)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
