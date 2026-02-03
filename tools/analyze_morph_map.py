#!/usr/bin/env python3
"""
Morph Map Analyzer - Standalone analysis of captured morph maps.

No Noise Engine dependencies - just reads JSON and produces analysis.

Usage:
    python analyze_morph_map.py maps/morph_map_buchla_258_20260203_132752.json
"""

import json
import sys
from pathlib import Path


def load_morph_map(filepath: str) -> dict:
    """Load morph map from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def analyze_snapshot(snap: dict) -> dict:
    """Extract key metrics from a snapshot."""
    if snap.get('snapshot') is None:
        return {'failed': True}
    
    frame = snap['snapshot']['frame']
    hw_dna = snap['snapshot'].get('hw_dna', {})
    
    return {
        'failed': False,
        'cv_voltage': snap['cv_voltage'],
        'midi_cc': snap['midi_cc_value'],
        'freq': frame.get('freq', 0),
        'rms1': frame.get('rms_stage1', 0),
        'rms3': frame.get('rms_stage3', 0),
        'peak': frame.get('peak', 0),
        'dc_bias': hw_dna.get('hw_dc_bias', 0),
        'rms_error': hw_dna.get('rms_error', 0),
        'harmonics': hw_dna.get('harmonic_signature', []),
        'symmetry': hw_dna.get('symmetry', 0),
        'saturation': hw_dna.get('saturation', 0),
    }


def print_summary(morph_map: dict):
    """Print summary of morph map."""
    print("=" * 70)
    print(f"MORPH MAP ANALYSIS: {morph_map['device_name']}")
    print("=" * 70)
    print()
    print(f"Capture date: {morph_map['capture_date']}")
    print(f"CV range: {morph_map['cv_range'][0]}V - {morph_map['cv_range'][1]}V")
    print(f"Points: {morph_map['captured_points']}/{morph_map['points']}")
    print(f"CV mode: {morph_map['test_config']['cv_mode']}")
    print(f"Vmax calibrated: {morph_map['test_config']['vmax_calibrated']}V")
    print()


def print_table(morph_map: dict):
    """Print data table for all points."""
    snapshots = morph_map['snapshots']
    
    print("-" * 70)
    print(f"{'#':>2} {'CV(V)':>6} {'CC':>4} {'Freq':>7} {'RMS1':>6} {'RMS3':>6} {'Peak':>6} {'Err%':>6}")
    print("-" * 70)
    
    for snap in snapshots:
        data = analyze_snapshot(snap)
        
        if data['failed']:
            print(f"{snap['cv_index']:>2} {snap['cv_voltage']:>6.2f} {snap['midi_cc_value']:>4}  ** TIMEOUT **")
            continue
        
        err_pct = data['rms_error'] * 100 if data['rms_error'] else 0
        
        print(f"{snap['cv_index']:>2} {data['cv_voltage']:>6.2f} {data['midi_cc']:>4} "
              f"{data['freq']:>7.1f} {data['rms1']:>6.3f} {data['rms3']:>6.3f} "
              f"{data['peak']:>6.3f} {err_pct:>5.1f}%")
    
    print("-" * 70)
    print()


def print_harmonic_analysis(morph_map: dict):
    """Print harmonic signature evolution."""
    snapshots = morph_map['snapshots']
    
    print("HARMONIC SIGNATURES (8 FFT bands)")
    print("-" * 70)
    print(f"{'#':>2} {'CV(V)':>6} | {'Band0':>6} {'Band1':>6} {'Band2':>6} {'Band3':>6} ...")
    print("-" * 70)
    
    for snap in snapshots:
        data = analyze_snapshot(snap)
        
        if data['failed'] or not data['harmonics']:
            continue
        
        h = data['harmonics']
        print(f"{snap['cv_index']:>2} {data['cv_voltage']:>6.2f} | "
              f"{h[0]:>6.2f} {h[1]:>6.2f} {h[2]:>6.2f} {h[3]:>6.2f} ...")
    
    print("-" * 70)
    print()


def print_morph_behavior(morph_map: dict):
    """Analyze how parameters change across the sweep."""
    snapshots = morph_map['snapshots']
    
    # Collect valid data points
    points = []
    for snap in snapshots:
        data = analyze_snapshot(snap)
        if not data['failed']:
            points.append(data)
    
    if len(points) < 2:
        print("Not enough valid points for morph analysis")
        return
    
    print("MORPH BEHAVIOR ANALYSIS")
    print("-" * 70)
    
    # RMS change
    rms_start = points[0]['rms3']
    rms_end = points[-1]['rms3']
    rms_change = ((rms_end - rms_start) / rms_start) * 100 if rms_start > 0 else 0
    
    print(f"RMS (stage 3): {rms_start:.3f} → {rms_end:.3f} ({rms_change:+.1f}%)")
    
    # Peak change
    peak_start = points[0]['peak']
    peak_end = points[-1]['peak']
    peak_change = ((peak_end - peak_start) / peak_start) * 100 if peak_start > 0 else 0
    
    print(f"Peak:          {peak_start:.3f} → {peak_end:.3f} ({peak_change:+.1f}%)")
    
    # Frequency stability
    freqs = [p['freq'] for p in points]
    freq_min, freq_max = min(freqs), max(freqs)
    freq_drift = freq_max - freq_min
    
    print(f"Frequency:     {freq_min:.1f}Hz - {freq_max:.1f}Hz (drift: {freq_drift:.2f}Hz)")
    
    # Find biggest RMS jump (potential sweet spot)
    max_jump = 0
    jump_idx = 0
    for i in range(1, len(points)):
        jump = abs(points[i]['rms3'] - points[i-1]['rms3'])
        if jump > max_jump:
            max_jump = jump
            jump_idx = i
    
    if max_jump > 0.01:
        print(f"\nBiggest RMS jump: {max_jump:.3f} between points {jump_idx-1} and {jump_idx}")
        print(f"  CV: {points[jump_idx-1]['cv_voltage']:.2f}V → {points[jump_idx]['cv_voltage']:.2f}V")
        print(f"  (Potential sweet spot / transition)")
    
    # Harmonic evolution
    if points[0]['harmonics'] and points[-1]['harmonics']:
        h_start = points[0]['harmonics'][0]  # Fundamental
        h_end = points[-1]['harmonics'][0]
        h_change = ((h_end - h_start) / h_start) * 100 if h_start > 0 else 0
        print(f"\nFundamental:   {h_start:.2f} → {h_end:.2f} ({h_change:+.1f}%)")
    
    print("-" * 70)
    print()


def print_data_quality(morph_map: dict):
    """Check data quality indicators."""
    snapshots = morph_map['snapshots']
    
    print("DATA QUALITY CHECK")
    print("-" * 70)
    
    failed = sum(1 for s in snapshots if s.get('snapshot') is None)
    print(f"Failed captures: {failed}/{len(snapshots)}")
    
    # Check for garbage values (the 1829469184.0 bug)
    garbage_count = 0
    for snap in snapshots:
        if snap.get('snapshot'):
            hw_dna = snap['snapshot'].get('hw_dna', {})
            if hw_dna.get('hw_dc_bias', 0) > 1000:
                garbage_count += 1
    
    if garbage_count > 0:
        print(f"⚠️  Corrupted hw_dna: {garbage_count} snapshots (waveform buffer bug)")
    else:
        print(f"✅ hw_dna values: Clean")
    
    # Check frequency stability
    freqs = []
    for snap in snapshots:
        if snap.get('snapshot'):
            freqs.append(snap['snapshot']['frame'].get('freq', 0))
    
    if freqs:
        freq_std = (sum((f - sum(freqs)/len(freqs))**2 for f in freqs) / len(freqs)) ** 0.5
        if freq_std < 1.0:
            print(f"✅ Frequency stability: Good (σ={freq_std:.2f}Hz)")
        else:
            print(f"⚠️  Frequency stability: Drift detected (σ={freq_std:.2f}Hz)")
    
    print("-" * 70)
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_morph_map.py <morph_map.json>")
        print()
        print("Example:")
        print("  python analyze_morph_map.py maps/morph_map_buchla_258_20260203_132752.json")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not Path(filepath).exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    morph_map = load_morph_map(filepath)
    
    print_summary(morph_map)
    print_data_quality(morph_map)
    print_table(morph_map)
    print_harmonic_analysis(morph_map)
    print_morph_behavior(morph_map)


if __name__ == "__main__":
    main()
