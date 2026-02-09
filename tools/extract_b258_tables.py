#!/usr/bin/env python3
"""
Extract 26-point harmonic tables from Buchla 258 morph map captures.

Reads morph map JSON files (sine→saw and sine→square sweeps),
runs SSOT FFT (fft_features.compute_all) on each waveform snapshot,
and outputs SuperCollider-ready #[...] table arrays for b258_dna.

Usage:
    python tools/extract_b258_tables.py \
        for_claude/morph_map_buchla_258_20260206_140115.json \
        for_claude/morph_map_buchla_258_20260206_140441.json

First file = sine→saw, second file = sine→square.
"""

import json
import sys
from pathlib import Path

import numpy as np

# Add project root for SSOT import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.telemetry.fft_features import compute_all


def load_morph_map(filepath: str) -> dict:
    with open(filepath, 'r') as f:
        return json.load(f)


def extract_tables(morph_map: dict, label: str) -> dict:
    """Extract h2-h8 harmonic ratios and RMS from all snapshots."""
    snapshots = morph_map.get('snapshots', [])
    n = len(snapshots)

    # Storage: h2..h8 tables + RMS
    h_tables = {h: [] for h in range(2, 9)}  # h2 through h8
    rms_values = []
    cc_values = []

    for i, snap in enumerate(snapshots):
        # Get waveform
        waveform = snap.get('snapshot', {}).get('waveform')
        if waveform is None:
            waveform = snap.get('waveform')
        if waveform is None:
            print(f"  WARNING: snapshot {i} has no waveform, skipping")
            continue

        w = np.array(waveform, dtype=np.float64)

        # Get frequency from frame
        frame = snap.get('snapshot', {}).get('frame', {})
        freq = frame.get('freq')

        # Get RMS from frame
        rms = frame.get('rms_stage1', frame.get('rms_stage2', 0.0))
        rms_values.append(rms)

        # Get CC value
        cc = snap.get('midi_cc_value', i)
        cc_values.append(cc)

        # Run SSOT FFT
        result = compute_all(w, freq_hz=freq, num_harmonics=8)
        harm = result['harm_ratio_raw']  # [h1=1.0, h2, h3, ..., h8]

        # Store h2-h8 (indices 1-7 in harm_ratio_raw)
        for h in range(2, 9):
            idx = h - 1
            val = harm[idx] if idx < len(harm) else 0.0
            h_tables[h].append(val)

    # Normalize RMS so max = 1.0
    max_rms = max(rms_values) if rms_values else 1.0
    rms_norm = [r / max_rms for r in rms_values]

    return {
        'label': label,
        'n': len(rms_values),
        'cc_values': cc_values,
        'h_tables': h_tables,
        'rms_norm': rms_norm,
        'rms_raw': rms_values,
    }


def fmt_sc_array(values: list, precision: int = 4) -> str:
    """Format as SuperCollider literal array #[...]."""
    formatted = ', '.join(f'{v:.{precision}f}' for v in values)
    return f'#[{formatted}]'


def print_tables(data: dict, prefix: str):
    """Print SC-ready table declarations."""
    label = data['label']
    n = data['n']
    ccs = data['cc_values']

    print(f"    // =======================================================")
    print(f"    // {label.upper()} HARMONIC TABLES (FFT from 1024-sample hardware waveforms)")
    print(f"    // {n} points: CC {', '.join(str(c) for c in ccs)}")
    print(f"    // =======================================================")

    for h in range(2, 9):
        vals = data['h_tables'][h]
        print(f"    var h{h}{prefix}T = {fmt_sc_array(vals)};")

    print()
    print(f"    // =======================================================")
    print(f"    // {label.upper()} RMS GAIN TABLE (normalized amplitude tracking)")
    print(f"    // =======================================================")
    print(f"    var rms{prefix}T = {fmt_sc_array(data['rms_norm'])};")
    print()


def main():
    if len(sys.argv) != 3:
        print("Usage: python tools/extract_b258_tables.py <saw_morph_map.json> <sqr_morph_map.json>")
        sys.exit(1)

    saw_path = sys.argv[1]
    sqr_path = sys.argv[2]

    print(f"Loading SAW morph map: {saw_path}")
    saw_map = load_morph_map(saw_path)
    print(f"  Device: {saw_map.get('device_name')}, Points: {saw_map.get('points')}")
    print(f"  Capture: {saw_map.get('capture_date', 'unknown')}")

    print(f"\nLoading SQR morph map: {sqr_path}")
    sqr_map = load_morph_map(sqr_path)
    print(f"  Device: {sqr_map.get('device_name')}, Points: {sqr_map.get('points')}")
    print(f"  Capture: {sqr_map.get('capture_date', 'unknown')}")

    print("\n--- Extracting SAW tables ---")
    saw_data = extract_tables(saw_map, "SAW")
    print(f"  Extracted {saw_data['n']} points")

    print("\n--- Extracting SQR tables ---")
    sqr_data = extract_tables(sqr_map, "SQR")
    print(f"  Extracted {sqr_data['n']} points")

    print("\n" + "=" * 70)
    print("SUPERCOLLIDER TABLE OUTPUT")
    print("=" * 70 + "\n")

    print_tables(saw_data, "Saw")
    print_tables(sqr_data, "Sqr")

    # Summary
    print("    // =======================================================")
    print("    // INDEX MATH (26-point tables)")
    print("    // =======================================================")
    print(f"    // sawK * {saw_data['n'] - 1}  (was * 11 for 12-point)")
    print(f"    // .clip(0, {saw_data['n'] - 2})  (was .clip(0, 10))")
    print(f"    // .clip(0, {saw_data['n'] - 1})  (was .clip(0, 11))")


if __name__ == '__main__':
    main()
