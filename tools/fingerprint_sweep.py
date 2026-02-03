#!/usr/bin/env python3
"""
CLI tool for running fingerprint sweeps.

This tool extracts fingerprints from existing morph map JSON files.
For running new sweeps, use the Ctrl+Shift+M shortcut in the app.

Usage:
    # Extract fingerprints from existing morph map
    python tools/fingerprint_sweep.py --from-map maps/morph_map_buchla_258_20260203_125417.json

    # List fingerprints for a device
    python tools/fingerprint_sweep.py --list --device buchla_258
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from telemetry.fingerprint_extractor import FingerprintExtractor
from telemetry.fingerprint_store import FingerprintStore


def extract_from_morph_map(map_path: str, output_dir: str = "fingerprints"):
    """Extract fingerprints from an existing morph map JSON file."""
    with open(map_path, "r") as f:
        morph_map = json.load(f)

    device_name = morph_map.get("device_name", "Unknown")
    print(f"Extracting fingerprints from: {map_path}")
    print(f"Device: {device_name}")

    # Setup extractor and store
    extractor = FingerprintExtractor(
        device_make="Custom",
        device_model=device_name,
        device_variant="hardware"
    )
    store = FingerprintStore(output_dir)

    extractor.start_session()

    # Extract fingerprints from snapshots
    fingerprints = []
    snapshots = morph_map.get("snapshots", [])

    for i, snap in enumerate(snapshots):
        if snap.get("snapshot") and snap["snapshot"].get("waveform"):
            import numpy as np
            waveform = np.array(snap["snapshot"]["waveform"])
            cv_volts = snap.get("cv_voltage", 0.0)
            freq_hz = snap["snapshot"]["frame"].get("freq", None)

            fp = extractor.extract(
                waveform=waveform,
                cv_volts=cv_volts,
                cv_chan="morph",
                freq_hz=freq_hz,
                notes=[f"from_{Path(map_path).stem}"]
            )
            fingerprints.append(fp)
            print(f"  [{i + 1}/{len(snapshots)}] CV={cv_volts:.3f}V → {fp['id']}")
        else:
            print(f"  [{i + 1}/{len(snapshots)}] SKIPPED (no waveform)")

    if fingerprints:
        device_key = device_name.lower().replace(" ", "_")
        sweep_name = store.save_sweep(fingerprints, device_key)
        print(f"\n{'=' * 60}")
        print(f"EXTRACTION COMPLETE")
        print(f"{'=' * 60}")
        print(f"Fingerprints extracted: {len(fingerprints)}")
        print(f"Sweep ID: {sweep_name}")
        print(f"Device key: {device_key}")
        print(f"\nFiles created in: {output_dir}/devices/{device_key}/")
        print(f"  - raw/fingerprints.jsonl")
        print(f"  - raw/fingerprints.csv")
        print(f"  - sweeps/{sweep_name}.json")
        print(f"  - deltas/{sweep_name}.jsonl")
        print(f"  - summaries/{sweep_name}_evolution.json")
    else:
        print("\nNo fingerprints extracted (no valid waveforms found)")


def list_fingerprints(device_key: str, base_path: str = "fingerprints"):
    """List fingerprints for a device."""
    store = FingerprintStore(base_path)

    try:
        fingerprints = store.load_fingerprints(device_key)
        print(f"Fingerprints for device: {device_key}")
        print(f"Total: {len(fingerprints)}")
        print()
        print(f"{'ID':<50} {'CV (V)':<10} {'Freq (Hz)':<12} {'RMS':<8}")
        print("-" * 80)
        for fp in fingerprints:
            print(f"{fp['id']:<50} {fp['capture']['cv']['volts']:<10.3f} "
                  f"{fp['capture']['freq_hz']:<12.1f} {fp['quality']['rms']:<8.4f}")
    except FileNotFoundError:
        print(f"No fingerprints found for device: {device_key}")
        print(f"Available devices:")
        index_path = Path(base_path) / "index.json"
        if index_path.exists():
            with open(index_path, "r") as f:
                index = json.load(f)
            for dev in index.get("devices", []):
                print(f"  - {dev['key']}")
        else:
            print("  (no index.json found)")


def show_index(base_path: str = "fingerprints"):
    """Show fingerprint store index."""
    index_path = Path(base_path) / "index.json"
    if not index_path.exists():
        print(f"No index found at {index_path}")
        return

    with open(index_path, "r") as f:
        index = json.load(f)

    print(f"Fingerprint Store Index")
    print(f"Updated: {index.get('updated_utc', 'unknown')}")
    print()
    print(f"{'Device Key':<30} {'Sweeps':<10} {'Sessions':<10}")
    print("-" * 50)
    for dev in index.get("devices", []):
        print(f"{dev['key']:<30} {dev['sweeps']:<10} {dev['sessions']:<10}")


def main():
    parser = argparse.ArgumentParser(
        description="Fingerprint extraction and management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("--from-map", type=str,
                        help="Extract fingerprints from morph map JSON file")
    parser.add_argument("--list", action="store_true",
                        help="List fingerprints")
    parser.add_argument("--index", action="store_true",
                        help="Show fingerprint store index")
    parser.add_argument("--device", type=str,
                        help="Device key (for --list)")
    parser.add_argument("--output", default="fingerprints",
                        help="Output directory (default: fingerprints)")

    args = parser.parse_args()

    if args.from_map:
        extract_from_morph_map(args.from_map, args.output)
    elif args.index:
        show_index(args.output)
    elif args.list:
        if not args.device:
            print("Error: --device required with --list")
            sys.exit(1)
        list_fingerprints(args.device, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
