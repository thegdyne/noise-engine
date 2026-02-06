#!/usr/bin/env python3
"""
CV Sweep Waveform Analyzer v3 — Three-Track Decomposition + Spectral Features

General-purpose waveform-level analyzer for any hardware CV sweep capture.
Decomposes sweep data into three independent tracks: Gain, DC, and Shape.
Spectral features (centroid, tilt, peak, THD) computed via SSOT module.

Works with any device type (oscillator morph, filter cutoff, waveshaper drive,
VCA response) — the metrics and decomposition are waveform-universal.

Usage:
    # Basic analysis (console output)
    python tools/analyze_morph_map.py maps/sweep_sine_saw.json

    # CSV export
    python tools/analyze_morph_map.py maps/sweep_sine_saw.json --csv

    # Plot
    python tools/analyze_morph_map.py maps/sweep_sine_saw.json --plot

    # Dual-sweep comparison
    python tools/analyze_morph_map.py maps/sweep_A.json maps/sweep_B.json --plot

    # Suppress theoretical guides on plot
    python tools/analyze_morph_map.py maps/sweep.json --plot --no-guides

    # Patch missing spectral fields back into morph map JSON
    python tools/analyze_morph_map.py maps/sweep.json --patch-json

Depends on: numpy, src.telemetry.fft_features (SSOT), matplotlib (--plot only)
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# Add project root to path for SSOT module import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.telemetry.fft_features import (
    compute_all as fft_compute_all,
    normalize_harmonics,
    MAX_HARMONICS,
)

# Numerical safety constant
EPS = 1e-12


def _json_num(x):
    """Sanitize float for JSON: NaN → None."""
    if isinstance(x, float) and math.isnan(x):
        return None
    return x

# Device-type defaults (P0.7)
DEVICE_DEFAULTS = {
    'oscillator': {'num_harmonics': 8,  'region_detection': True,  'plot_guides': True},
    'filter':     {'num_harmonics': 16, 'region_detection': False, 'plot_guides': False},
    'wavefolder': {'num_harmonics': 16, 'region_detection': False, 'plot_guides': False},
    'vca':        {'num_harmonics': 8,  'region_detection': False, 'plot_guides': False},
    'effect':     {'num_harmonics': 16, 'region_detection': False, 'plot_guides': False},
}

# Analysis version tag for --patch-json
ANALYSIS_VERSION = "fft_features.v1"


# =============================================================================
# JSON Loading with Fallbacks
# =============================================================================

def load_morph_map(filepath: str) -> dict:
    """Load morph map from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def get_field(data: dict, path: str, default: Any = None) -> Any:
    """
    Get nested field from dict using dot-separated path.

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "test_config.settle_ms")
        default: Default value if not found

    Returns:
        Value at path or default
    """
    keys = path.split('.')
    val = data
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val


def extract_metadata(morph_map: dict) -> dict:
    """
    Extract metadata from morph map with fallback defaults.

    Returns dict with all expected fields, using fallbacks where needed.
    """
    snapshots = morph_map.get('snapshots', [])

    # Device type: default to 'oscillator' if missing (P0.7)
    raw_type = morph_map.get('device_type', 'oscillator')
    device_type = raw_type if raw_type in DEVICE_DEFAULTS else 'oscillator'

    return {
        'device_name': morph_map.get('device_name', 'Unknown'),
        'device_type': device_type,
        'cv_range': morph_map.get('cv_range', [0.0, 5.0]),
        'format_version': morph_map.get('format_version', 'unknown'),
        'points': morph_map.get('points', len(snapshots)),
        'captured_points': morph_map.get('captured_points', len(snapshots)),
        'settle_ms': get_field(morph_map, 'test_config.settle_ms', 'unknown'),
        'total_time_sec': get_field(morph_map, 'metadata.total_time_sec', 'unknown'),
        'failed_points': get_field(morph_map, 'metadata.failed_points', []),
    }


# =============================================================================
# Waveform Detection and Validation
# =============================================================================

def extract_waveform(snapshot: dict) -> Optional[np.ndarray]:
    """
    Extract waveform array from snapshot with fallback paths.

    Detection strategy (try in order):
        1. snapshot["snapshot"]["waveform"] — standard v6.2 path
        2. snapshot["waveform"] — possible flat schema
        3. None — missing/invalid

    Validation rules:
        - Must be list or array-like
        - Length >= 16 samples
        - All values must be finite (no NaN/Inf)

    Returns:
        numpy array or None if invalid/missing
    """
    # Try standard v6.2 path
    waveform = get_field(snapshot, 'snapshot.waveform')

    # Fallback to flat schema
    if waveform is None:
        waveform = snapshot.get('waveform')

    # Validate
    if waveform is None:
        return None

    if not isinstance(waveform, (list, np.ndarray)):
        return None

    arr = np.array(waveform, dtype=np.float64)

    if len(arr) < 16:
        return None

    if not np.all(np.isfinite(arr)):
        return None

    return arr


# =============================================================================
# Waveform-Level Metrics Computation
# =============================================================================

def compute_waveform_metrics(w: np.ndarray) -> dict:
    """
    Compute all waveform-level metrics from raw N-sample waveform.

    Every division uses eps = 1e-12 denominator clamp.
    Non-finite results mark the point as invalid.
    If rms < eps (silence/dropout), all derived metrics become nan.

    Returns dict with all metrics, or nan values if computation fails.
    """
    n = len(w)

    # Basic metrics
    dc = np.mean(w)
    rms = np.sqrt(np.mean(w ** 2))

    # Near-zero RMS guard: silence/dropout invalidates all derived metrics
    if rms < EPS:
        return {
            'dc': dc,
            'rms': rms,
            'peak': float('nan'),
            'pos_peak': float('nan'),
            'neg_peak': float('nan'),
            'span': float('nan'),
            'range_asym': float('nan'),
            'crest': float('nan'),
            'hf': float('nan'),
            'shape_rms': float('nan'),
            'shape_crest': float('nan'),
            'norm_crest': float('nan'),
            'norm_range_asym': float('nan'),
            'norm_hf': float('nan'),
            'skew': float('nan'),
            'waveform_n': n,
        }

    peak = np.max(np.abs(w))
    pos_peak = np.max(w)
    neg_peak = np.min(w)
    span = pos_peak - neg_peak

    # Range asymmetry
    abs_pos = abs(pos_peak)
    abs_neg = abs(neg_peak)
    range_asym = abs_pos / (abs_pos + abs_neg + EPS)

    # Crest factor
    crest = peak / (rms + EPS)

    # HF (edge sharpness) - mean absolute first difference normalized by RMS
    diff_w = np.diff(w)
    hf = np.mean(np.abs(diff_w)) / (rms + EPS)

    # DC-removed metrics
    x = w - dc
    shape_rms = np.sqrt(np.mean(x ** 2))
    shape_peak = np.max(np.abs(x))
    shape_crest = shape_peak / (shape_rms + EPS)

    # Shape-invariant metrics (unit-RMS normalized)
    s = x / (shape_rms + EPS)
    norm_crest = np.max(np.abs(s))
    norm_pos = np.max(s)
    norm_neg = np.min(s)
    norm_range_asym = abs(norm_pos) / (abs(norm_pos) + abs(norm_neg) + EPS)
    diff_s = np.diff(s)
    norm_hf = np.mean(np.abs(diff_s))

    # Skew (third moment on normalized waveform)
    skew = np.mean(s ** 3)

    metrics = {
        # Raw metrics
        'dc': dc,
        'rms': rms,
        'peak': peak,
        'pos_peak': pos_peak,
        'neg_peak': neg_peak,
        'span': span,
        'range_asym': range_asym,
        'crest': crest,
        'hf': hf,
        # DC-removed shape metrics
        'shape_rms': shape_rms,
        'shape_crest': shape_crest,
        # Shape-invariant (normalized)
        'norm_crest': norm_crest,
        'norm_range_asym': norm_range_asym,
        'norm_hf': norm_hf,
        'skew': skew,
        # Metadata
        'waveform_n': n,
    }

    # Check all values are finite
    for key, val in metrics.items():
        if isinstance(val, (float, np.floating)) and not np.isfinite(val):
            metrics[key] = float('nan')

    return metrics


def compute_hw_dna_fallback(snapshot: dict) -> dict:
    """
    Extract hw_dna metrics as fallback when waveform is missing.

    Returns dict with available metrics from hw_dna/frame.
    """
    frame = get_field(snapshot, 'snapshot.frame', {})
    hw_dna = get_field(snapshot, 'snapshot.hw_dna', {})

    return {
        'rms': frame.get('rms_stage3', float('nan')),
        'peak': frame.get('peak', float('nan')),
        'dc': hw_dna.get('hw_dc_bias', float('nan')),
        'harmonics': hw_dna.get('harmonic_signature', []),
    }


# =============================================================================
# Spectral Feature Computation (SSOT)
# =============================================================================

def compute_spectral_features(waveform: np.ndarray, freq_hz: Optional[float],
                              num_harmonics: int = 8,
                              sample_rate: int = 48000) -> dict:
    """
    Compute spectral features from waveform via SSOT module.

    Returns dict with centroid, tilt, spectral_peak, thd, etc.
    Returns nan values if computation fails.
    """
    try:
        result = fft_compute_all(
            waveform, freq_hz=freq_hz,
            sample_rate=sample_rate,
            num_harmonics=num_harmonics
        )
        return {
            'spectral_centroid_hz': result['spectral_centroid_hz'],
            'spectral_tilt': result['spectral_tilt'],
            'spectral_tilt_slope': result['spectral_tilt_slope'],
            'spectral_peak_hz': result['spectral_peak_hz'],
            'spectral_peak_bin': result['spectral_peak_bin'],
            'spectral_peak_bin_frac': result['spectral_peak_bin_frac'],
            'thd': result['thd'],
            'thd_valid': result['thd_valid'],
            'harm_ratio_ssot': result['harm_ratio'],
            'num_harmonics_actual': result['num_harmonics_actual'],
        }
    except Exception:
        return {
            'spectral_centroid_hz': float('nan'),
            'spectral_tilt': float('nan'),
            'spectral_tilt_slope': float('nan'),
            'spectral_peak_hz': float('nan'),
            'spectral_peak_bin': 0,
            'spectral_peak_bin_frac': 0.0,
            'thd': float('nan'),
            'thd_valid': False,
            'harm_ratio_ssot': [],
            'num_harmonics_actual': 0,
        }


def check_existing_spectral(snapshot: dict) -> Optional[dict]:
    """
    Check if spectral features already exist in snapshot (from --patch-json).

    Returns dict if found, None if missing.
    """
    spectral = get_field(snapshot, 'snapshot.spectral')
    if spectral and 'spectral_centroid_hz' in spectral:
        return spectral
    return None


# =============================================================================
# Data Point Processing
# =============================================================================

def process_snapshot(snap: dict, num_harmonics: int = 8) -> dict:
    """
    Process a single snapshot into analysis data point.

    Returns dict with:
        - cv_voltage, midi_cc, freq (required)
        - All waveform metrics (if waveform available)
        - Spectral features (from SSOT or existing data)
        - has_waveform flag
        - valid flag
        - spectral_computed flag
    """
    # Required fields
    cv_voltage = snap.get('cv_voltage')
    midi_cc = snap.get('midi_cc_value')
    frame = get_field(snap, 'snapshot.frame', {})
    freq = frame.get('freq')

    if cv_voltage is None or midi_cc is None:
        return {'valid': False, 'reason': 'missing required fields'}

    point = {
        'cv_voltage': cv_voltage,
        'midi_cc': midi_cc,
        'freq': freq if freq is not None else float('nan'),
        'valid': True,
        'has_waveform': False,
        'spectral_computed': False,
    }

    # Try to extract and process waveform
    waveform = extract_waveform(snap)
    if waveform is not None:
        metrics = compute_waveform_metrics(waveform)
        point.update(metrics)
        point['has_waveform'] = True

        # Check if spectral features already exist (from --patch-json)
        existing = check_existing_spectral(snap)
        if existing:
            point.update(existing)
        else:
            # Compute via SSOT (P0.4)
            spectral = compute_spectral_features(
                waveform, freq_hz=freq,
                num_harmonics=num_harmonics
            )
            point.update(spectral)
            point['spectral_computed'] = True
    else:
        # Fallback to hw_dna
        fallback = compute_hw_dna_fallback(snap)
        point['rms'] = fallback['rms']
        point['peak'] = fallback['peak']
        point['dc'] = fallback['dc']
        point['waveform_n'] = float('nan')

    # Extract harmonics from hw_dna (one extraction point for both paths)
    hw_dna = get_field(snap, 'snapshot.hw_dna', {})
    point['harmonics'] = hw_dna.get('harmonic_signature', [])

    return point


def process_all_snapshots(morph_map: dict, num_harmonics: int = 8) -> List[dict]:
    """Process all snapshots into data points."""
    snapshots = morph_map.get('snapshots', [])
    return [process_snapshot(snap, num_harmonics) for snap in snapshots]


# =============================================================================
# Harmonic Analysis
# =============================================================================

def compute_harm_brightness(harmonics: List[float]) -> float:
    """
    Compute harmonic brightness: sum(h5..h8) / sum(h1..h4).

    Returns nan if harmonics not available.
    """
    if not harmonics or len(harmonics) < 8:
        return float('nan')

    low = sum(harmonics[0:4])
    high = sum(harmonics[4:8])
    return high / (low + EPS)


# =============================================================================
# Region Detection (Oscillator Sweeps Only — P0.7)
# =============================================================================

def detect_regions(points: List[dict], device_type: str) -> dict:
    """
    Automatically identify sweep regions for oscillator sweeps.

    Only runs for device_type == "oscillator" (P0.7).
    Returns dict with detected region CC values (not indices) and metadata.
    """
    defaults = DEVICE_DEFAULTS.get(device_type, DEVICE_DEFAULTS['oscillator'])
    if not defaults['region_detection']:
        return {'enabled': False, 'reason': f'disabled for device_type={device_type}'}

    # Filter valid points with waveform data
    valid_points = [(i, p) for i, p in enumerate(points)
                    if p.get('valid') and p.get('has_waveform')
                    and not math.isnan(p.get('crest', float('nan')))]

    if len(valid_points) < 4:
        return {'enabled': False, 'reason': 'insufficient valid points'}

    # Build arrays - use CC values, not indices
    ccs = np.array([p['midi_cc'] for _, p in valid_points])
    crests = np.array([p['crest'] for _, p in valid_points])
    range_asyms = np.array([p['range_asym'] for _, p in valid_points])
    shape_rmss = np.array([p.get('shape_rms', float('nan')) for _, p in valid_points])
    dcs = np.array([p['dc'] for _, p in valid_points])

    regions = {
        'enabled': True,
        'sine_end_cc': None,
        'knee_cc': None,
        'knee_cc_to': None,
        'knee_crest_from': None,
        'knee_crest_to': None,
        'compression_cc': None,
        'compression_shape_rms': None,
        'endpoint_start_cc': None,
        'warnings': [],
    }

    # Find sine zone end: last array position where crest < 1.8 AND range_asym ~= 0.5
    # for 2+ consecutive points
    sine_end_pos = None
    consecutive = 0
    for i in range(len(crests)):
        if crests[i] < 1.8 and abs(range_asyms[i] - 0.5) < 0.03:
            consecutive += 1
            if consecutive >= 2:
                sine_end_pos = i
        else:
            consecutive = 0

    if sine_end_pos is not None:
        regions['sine_end_cc'] = int(ccs[sine_end_pos])

    # Find transition knee: argmax of |diff(crest)| after sine zone
    start_pos = 0
    if sine_end_pos is not None:
        start_pos = sine_end_pos + 1

    if start_pos < len(crests) - 1:
        crest_diff = np.abs(np.diff(crests[start_pos:]))
        if len(crest_diff) > 0:
            knee_rel = np.argmax(crest_diff)
            knee_pos = start_pos + knee_rel
            knee_cc = int(ccs[knee_pos])
            # Validate ordering (compare CC values)
            if regions['sine_end_cc'] is None or knee_cc > regions['sine_end_cc']:
                regions['knee_cc'] = knee_cc
                # Store crest jump endpoints (both CC and crest values)
                regions['knee_crest_from'] = float(crests[knee_pos])
                if knee_pos + 1 < len(crests):
                    regions['knee_cc_to'] = int(ccs[knee_pos + 1])
                    regions['knee_crest_to'] = float(crests[knee_pos + 1])
            else:
                regions['warnings'].append('knee_cc <= sine_end_cc')

    # Find energy compression: local minimum of shape_rms after knee
    if regions['knee_cc'] is not None:
        # Find position of knee in array
        knee_pos = np.where(ccs == regions['knee_cc'])[0]
        if len(knee_pos) > 0:
            knee_pos = knee_pos[0]
            shape_after_knee = shape_rmss[knee_pos:]
            if len(shape_after_knee) > 0 and np.any(np.isfinite(shape_after_knee)):
                finite_mask = np.isfinite(shape_after_knee)
                if np.any(finite_mask):
                    min_rel = np.argmin(np.where(finite_mask, shape_after_knee, np.inf))
                    comp_pos = knee_pos + min_rel
                    comp_cc = int(ccs[comp_pos])
                    if comp_cc > regions['knee_cc']:
                        regions['compression_cc'] = comp_cc
                        regions['compression_shape_rms'] = float(shape_rmss[comp_pos])
                    else:
                        regions['warnings'].append('compression_cc <= knee_cc')

    # Find endpoint start: first of last 3 points where all diffs are below tolerance
    if len(ccs) >= 3:
        tol_crest = 0.1
        tol_shape = 0.01
        tol_dc = 0.01
        for i in range(len(ccs) - 3, len(ccs) - 1):
            if i < 0:
                continue
            c_diff = abs(crests[i + 1] - crests[i]) if i + 1 < len(crests) else 999
            s_diff = abs(shape_rmss[i + 1] - shape_rmss[i]) if i + 1 < len(shape_rmss) else 999
            d_diff = abs(dcs[i + 1] - dcs[i]) if i + 1 < len(dcs) else 999

            if c_diff < tol_crest and s_diff < tol_shape and d_diff < tol_dc:
                ep_cc = int(ccs[i])
                # Check ordering (compare CC values)
                if regions['compression_cc'] is None or ep_cc > regions['compression_cc']:
                    regions['endpoint_start_cc'] = ep_cc
                    break

    return regions


# =============================================================================
# Sweep Behavior Summary
# =============================================================================

def compute_sweep_behavior(points: List[dict]) -> dict:
    """
    Compute sweep behavior summary: start->end deltas and largest jumps.

    Returns dict with gain, dc, and shape track summaries.
    """
    valid_points = [p for p in points if p.get('valid') and p.get('has_waveform')]

    if len(valid_points) < 2:
        return {'valid': False}

    first = valid_points[0]
    last = valid_points[-1]

    # Gain track
    shape_rms_start = first.get('shape_rms', float('nan'))
    shape_rms_end = last.get('shape_rms', float('nan'))
    peak_start = first.get('peak', float('nan'))
    peak_end = last.get('peak', float('nan'))

    shape_rms_change = ((shape_rms_end - shape_rms_start) / (shape_rms_start + EPS)) * 100
    peak_change = ((peak_end - peak_start) / (peak_start + EPS)) * 100

    # DC track
    dc_start = first.get('dc', float('nan'))
    dc_end = last.get('dc', float('nan'))

    # Find peak DC
    dcs = [p.get('dc', float('nan')) for p in valid_points]
    ccs = [p.get('midi_cc', 0) for p in valid_points]
    dc_peak_idx = np.argmax(np.abs(dcs)) if len(dcs) > 0 else 0
    dc_peak_cc = ccs[dc_peak_idx] if dc_peak_idx < len(ccs) else 0
    dc_peak_val = dcs[dc_peak_idx] if dc_peak_idx < len(dcs) else float('nan')

    dc_drift = 'positive' if dc_end > dc_start else 'negative' if dc_end < dc_start else 'stable'

    # Shape track
    crest_start = first.get('crest', float('nan'))
    crest_end = last.get('crest', float('nan'))
    skew_start = first.get('skew', float('nan'))
    skew_end = last.get('skew', float('nan'))

    # HF monotonicity
    hfs = [p.get('hf', float('nan')) for p in valid_points]
    hf_diffs = np.diff([h for h in hfs if not math.isnan(h)])
    hf_rising = np.all(hf_diffs >= -0.01) if len(hf_diffs) > 0 else False

    return {
        'valid': True,
        'gain': {
            'shape_rms_start': shape_rms_start,
            'shape_rms_end': shape_rms_end,
            'shape_rms_change_pct': shape_rms_change,
            'peak_start': peak_start,
            'peak_end': peak_end,
            'peak_change_pct': peak_change,
        },
        'dc': {
            'start': dc_start,
            'end': dc_end,
            'drift': dc_drift,
            'peak_cc': dc_peak_cc,
            'peak_val': dc_peak_val,
        },
        'shape': {
            'crest_start': crest_start,
            'crest_end': crest_end,
            'skew_start': skew_start,
            'skew_end': skew_end,
            'hf_rising': hf_rising,
        },
    }


# =============================================================================
# Console Output
# =============================================================================

def print_header(filepath: str, metadata: dict, points: List[dict]):
    """Print analysis header."""
    waveform_count = sum(1 for p in points if p.get('has_waveform'))
    missing_count = len(points) - waveform_count

    print("=== CV SWEEP ANALYSIS ===")
    print(f"File: {filepath}")
    print(f"Device: {metadata['device_name']}")
    print(f"Type: {metadata['device_type']}")
    cv_range = metadata['cv_range']
    print(f"CV Range: [{cv_range[0]}, {cv_range[1]}]")
    print(f"Points: {metadata['captured_points']} captured, {metadata['points']} requested")
    print(f"Waveforms: {waveform_count}/{len(points)} present ({missing_count} missing)")
    fv = metadata['format_version']
    print(f"Format: {fv}" if fv == 'unknown' else f"Format: v{fv}")
    print()


def print_cv_sweep_data(points: List[dict]):
    """Print basic CV sweep data table."""
    print("=== CV SWEEP DATA ===")
    print(f"{'Point':>5}  {'CV(V)':>6}  {'CC':>4}  {'Freq(Hz)':>9}  {'RMS':>6}  {'Peak':>6}  {'Waveform':<10}")
    print("-" * 60)

    for i, p in enumerate(points):
        if not p.get('valid'):
            print(f"{i+1:>5}  ** INVALID **")
            continue

        wf_info = f"N={p.get('waveform_n', 0)}" if p.get('has_waveform') else "---"
        rms = p.get('rms', float('nan'))
        peak = p.get('peak', float('nan'))
        freq = p.get('freq', float('nan'))

        rms_str = f"{rms:>6.3f}" if not math.isnan(rms) else "   ---"
        peak_str = f"{peak:>6.3f}" if not math.isnan(peak) else "   ---"
        freq_str = f"{freq:>9.1f}" if not math.isnan(freq) else "      ---"

        print(f"{i+1:>5}  {p['cv_voltage']:>6.3f}  {p['midi_cc']:>4}  "
              f"{freq_str}  {rms_str}  {peak_str}  {wf_info:<10}")

    print()


def print_three_track_table(points: List[dict]):
    """Print three-track decomposition table."""
    print("=== THREE-TRACK DECOMPOSITION ===")
    print(f"{'Point':>5}  {'CC':>4}  {'DC':>8}  {'ShapeRMS':>9}  {'Peak':>6}  "
          f"{'Crest':>6}  {'Span':>6}  {'RangeAsym':>9}  {'HF':>6}")
    print("-" * 80)

    for i, p in enumerate(points):
        if not p.get('valid') or not p.get('has_waveform'):
            print(f"{i+1:>5}  {p.get('midi_cc', 0):>4}  {'---':>8}  (no waveform)")
            continue

        dc = p.get('dc', float('nan'))
        shape_rms = p.get('shape_rms', float('nan'))
        peak = p.get('peak', float('nan'))
        crest = p.get('crest', float('nan'))
        span = p.get('span', float('nan'))
        range_asym = p.get('range_asym', float('nan'))
        hf = p.get('hf', float('nan'))

        def fmt(val, width=6, precision=3):
            if math.isnan(val):
                return " " * (width - 3) + "---"
            return f"{val:>{width}.{precision}f}"

        print(f"{i+1:>5}  {p['midi_cc']:>4}  {dc:>+8.4f}  {fmt(shape_rms, 9)}  "
              f"{fmt(peak)}  {fmt(crest)}  {fmt(span)}  {fmt(range_asym, 9)}  {fmt(hf)}")

    print()


def print_shape_invariant_table(points: List[dict]):
    """Print shape-invariant metrics table (DC removed, unit RMS)."""
    print("=== SHAPE-INVARIANT METRICS (DC removed, unit RMS) ===")
    print(f"{'Point':>5}  {'CC':>4}  {'NormCrest':>10}  {'NormAsym':>9}  {'NormHF':>7}  {'Skew':>8}")
    print("-" * 55)

    for i, p in enumerate(points):
        if not p.get('valid') or not p.get('has_waveform'):
            continue

        norm_crest = p.get('norm_crest', float('nan'))
        norm_asym = p.get('norm_range_asym', float('nan'))
        norm_hf = p.get('norm_hf', float('nan'))
        skew = p.get('skew', float('nan'))

        def fmt(val, width=7, precision=3):
            if math.isnan(val):
                return " " * (width - 3) + "---"
            return f"{val:>{width}.{precision}f}"

        print(f"{i+1:>5}  {p['midi_cc']:>4}  {fmt(norm_crest, 10)}  "
              f"{fmt(norm_asym, 9)}  {fmt(norm_hf)}  {skew:>+8.4f}")

    print()


def print_harmonic_table(points: List[dict]):
    """Print harmonic signatures table."""
    # Check if any points have harmonics
    has_harmonics = any(len(p.get('harmonics', [])) >= 8 for p in points if p.get('valid'))
    if not has_harmonics:
        return

    print("=== HARMONIC SIGNATURES (8 FFT bands) ===")
    print(f"{'Point':>5}  {'CC':>4}  |  {'h1':>6}  {'h2':>6}  {'h3':>6}  {'h4':>6}  "
          f"{'h5':>6}  {'h6':>6}  {'h7':>6}  {'h8':>6}  {'Bright':>7}")
    print("-" * 90)

    for i, p in enumerate(points):
        if not p.get('valid'):
            continue

        harmonics = p.get('harmonics', [])
        if len(harmonics) < 8:
            continue

        brightness = compute_harm_brightness(harmonics)

        h_strs = [f"{h:>6.2f}" for h in harmonics[:8]]
        br_str = f"{brightness:>7.3f}" if not math.isnan(brightness) else "    ---"

        print(f"{i+1:>5}  {p['midi_cc']:>4}  |  {'  '.join(h_strs)}  {br_str}")

    print()


def print_spectral_table(points: List[dict]):
    """Print spectral features table (centroid, tilt, peak, THD)."""
    has_spectral = any(
        not math.isnan(p.get('spectral_centroid_hz', float('nan')))
        for p in points if p.get('valid') and p.get('has_waveform')
    )
    if not has_spectral:
        return

    print("=== SPECTRAL FEATURES (SSOT) ===")
    print(f"{'Point':>5}  {'CC':>4}  {'Centroid':>9}  {'Tilt':>6}  "
          f"{'PeakHz':>9}  {'THD':>7}  {'Valid':>5}")
    print("-" * 58)

    for i, p in enumerate(points):
        if not p.get('valid') or not p.get('has_waveform'):
            continue

        centroid = p.get('spectral_centroid_hz', float('nan'))
        tilt = p.get('spectral_tilt', float('nan'))
        peak_hz = p.get('spectral_peak_hz', float('nan'))
        thd = p.get('thd', float('nan'))
        thd_valid = p.get('thd_valid', False)

        def fmt(val, width=7, precision=1):
            if isinstance(val, float) and math.isnan(val):
                return " " * (width - 3) + "---"
            return f"{val:>{width}.{precision}f}"

        valid_str = "  yes" if thd_valid else "   no"
        print(f"{i+1:>5}  {p['midi_cc']:>4}  {fmt(centroid, 9)}  {fmt(tilt, 6, 3)}  "
              f"{fmt(peak_hz, 9)}  {fmt(thd, 7, 4)}  {valid_str}")

    print()


def print_region_analysis(regions: dict, points: List[dict]):
    """Print region analysis section."""
    if not regions.get('enabled'):
        return

    print("=== REGION ANALYSIS ===")

    # Sine zone
    if regions.get('sine_end_cc') is not None:
        sine_end_cc = regions['sine_end_cc']
        # Find range of points in sine zone
        sine_points = [p for p in points if p.get('valid') and p.get('midi_cc', 999) <= sine_end_cc]
        if sine_points:
            cc_start = sine_points[0].get('midi_cc', 0)
            crest_range = [p.get('crest', 0) for p in sine_points if p.get('has_waveform')]
            asym_range = [p.get('range_asym', 0) for p in sine_points if p.get('has_waveform')]
            if crest_range:
                print(f"Sine zone:          CC {cc_start}-{sine_end_cc}  "
                      f"(crest {min(crest_range):.2f}-{max(crest_range):.2f}, "
                      f"range_asym {min(asym_range):.2f}-{max(asym_range):.2f})")
    else:
        print("Sine zone:          not detected")

    # Transition knee (use pre-computed crest jump values)
    if regions.get('knee_cc') is not None:
        knee_cc = regions['knee_cc']
        knee_cc_to = regions.get('knee_cc_to', knee_cc)
        crest_from = regions.get('knee_crest_from')
        crest_to = regions.get('knee_crest_to')
        if crest_from is not None and crest_to is not None:
            print(f"Transition knee:    CC {knee_cc}->{knee_cc_to}  "
                  f"(crest {crest_from:.2f}->{crest_to:.2f})")
        else:
            print(f"Transition knee:    CC {knee_cc}->{knee_cc_to}")
    else:
        print("Transition knee:    not detected")

    # Energy compression (use pre-computed shape_rms)
    if regions.get('compression_cc') is not None:
        comp_cc = regions['compression_cc']
        comp_shape_rms = regions.get('compression_shape_rms')
        if comp_shape_rms is not None:
            print(f"Energy compression: CC {comp_cc}    "
                  f"(shape_rms minimum: {comp_shape_rms:.3f})")
        else:
            print(f"Energy compression: CC {comp_cc}")
    else:
        print("Energy compression: not detected")

    # Endpoint character
    if regions.get('endpoint_start_cc') is not None:
        ep_cc = regions['endpoint_start_cc']
        ep_points = [p for p in points if p.get('valid') and p.get('midi_cc', 0) >= ep_cc]
        if ep_points:
            cc_end = ep_points[-1].get('midi_cc', ep_cc)
            crest_range = [p.get('crest', 0) for p in ep_points if p.get('has_waveform')]
            span_range = [p.get('span', 0) for p in ep_points if p.get('has_waveform')]
            if crest_range:
                print(f"Endpoint character: CC {ep_cc}-{cc_end} "
                      f"(crest {min(crest_range):.2f}-{max(crest_range):.2f}, "
                      f"span {min(span_range):.2f}-{max(span_range):.2f})")
    else:
        print("Endpoint character: not detected")

    # Warnings
    for warning in regions.get('warnings', []):
        print(f"  Warning: {warning}")

    print()


def print_sweep_behavior(behavior: dict):
    """Print sweep behavior summary."""
    if not behavior.get('valid'):
        return

    print("=== SWEEP BEHAVIOR ===")

    # Gain track
    g = behavior['gain']
    print(f"Gain track:  ShapeRMS {g['shape_rms_start']:.3f}->{g['shape_rms_end']:.3f} "
          f"({g['shape_rms_change_pct']:+.1f}%), "
          f"Peak {g['peak_start']:.3f}->{g['peak_end']:.3f} ({g['peak_change_pct']:+.1f}%)")

    # DC track
    d = behavior['dc']
    print(f"DC track:    {d['start']:+.3f}->{d['end']:+.3f} "
          f"({d['drift']} drift, peak at CC{d['peak_cc']}: {d['peak_val']:+.3f})")

    # Shape track
    s = behavior['shape']
    hf_desc = "rising monotonically" if s['hf_rising'] else "non-monotonic"
    print(f"Shape track: Crest {s['crest_start']:.2f}->{s['crest_end']:.2f}, "
          f"HF {hf_desc}, Skew {s['skew_start']:+.2f}->{s['skew_end']:+.2f}")

    print()


def print_metadata_section(metadata: dict, points: List[dict]):
    """Print metadata section."""
    print("=== METADATA ===")

    if metadata['total_time_sec'] != 'unknown':
        print(f"Total time: {metadata['total_time_sec']:.1f}s")
    else:
        print("Total time: unknown")

    print(f"Failed points: {metadata['failed_points']}")

    if metadata['settle_ms'] != 'unknown':
        print(f"Settle time: {metadata['settle_ms']}ms")
    else:
        print("Settle time: unknown")

    # Count invalid metrics (points that are invalid or have nan waveform metrics)
    invalid_count = sum(1 for p in points if not p.get('valid') or
                        (p.get('has_waveform') and math.isnan(p.get('crest', float('nan')))))
    print(f"Invalid metrics: {invalid_count} points")
    print()


def print_console_output(filepath: str, morph_map: dict, points: List[dict],
                        metadata: dict, regions: dict, behavior: dict):
    """Print full console output."""
    print_header(filepath, metadata, points)
    print_cv_sweep_data(points)
    print_three_track_table(points)
    print_shape_invariant_table(points)
    print_harmonic_table(points)
    print_spectral_table(points)

    if regions.get('enabled'):
        print_region_analysis(regions, points)

    print_sweep_behavior(behavior)
    print_metadata_section(metadata, points)


# =============================================================================
# CSV Export
# =============================================================================

def export_csv(points: List[dict], output_path: Path):
    """
    Export analysis data to CSV.

    One row per sweep point, all metrics as columns.
    Waveform-derived numeric columns are nan when waveform is missing or invalid.
    Invalid points are kept (spec: "Kept in output tables... nan in CSV").
    """
    columns = [
        'cv_voltage', 'midi_cc', 'freq',
        'dc', 'rms', 'peak', 'crest', 'pos_peak', 'neg_peak', 'span', 'range_asym', 'hf',
        'shape_rms', 'shape_crest',
        'norm_crest', 'norm_range_asym', 'norm_hf', 'skew',
        'spectral_centroid_hz', 'spectral_tilt', 'spectral_tilt_slope', 'spectral_peak_hz', 'thd',
        'waveform_n'
    ]

    with open(output_path, 'w') as f:
        f.write(','.join(columns) + '\n')

        for p in points:
            values = []
            for col in columns:
                val = p.get(col, float('nan'))
                if val is None:
                    values.append('nan')
                elif isinstance(val, float) and math.isnan(val):
                    values.append('nan')
                elif isinstance(val, (float, np.floating)):
                    values.append(f"{float(val):.6f}")
                elif isinstance(val, (int, np.integer)):
                    values.append(str(int(val)))
                else:
                    values.append(str(val))

            f.write(','.join(values) + '\n')

    print(f"CSV exported to: {output_path}")


# =============================================================================
# PNG Plot Generation
# =============================================================================

def _ratio_ok(arr: np.ndarray, threshold: float = 0.5) -> bool:
    """Check if >= threshold fraction of values are finite (not nan/inf)."""
    return np.isfinite(arr).mean() >= threshold


def generate_plot(points_list: List[List[dict]], labels: List[str],
                 output_path: Path, device_type: str, show_guides: bool):
    """
    Generate six-row analysis plot.

    Each plotted metric requires >= 50% valid points; otherwise that trace
    is omitted and a warning is printed.

    Args:
        points_list: List of point lists (1 for single, 2 for dual-sweep)
        labels: Labels for each sweep
        output_path: Where to save the PNG
        device_type: Device type for theoretical guides
        show_guides: Whether to show crest factor guides
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
    except ImportError:
        print("ERROR: matplotlib not installed. Cannot generate plot.")
        print("Install with: pip install matplotlib")
        return

    # Determine guide visibility from device type (P0.7)
    defaults = DEVICE_DEFAULTS.get(device_type, DEVICE_DEFAULTS['oscillator'])
    show_guides = show_guides and defaults['plot_guides']

    n_sweeps = len(points_list)
    fig = plt.figure(figsize=(8 * n_sweeps, 18))
    gs = gridspec.GridSpec(6, n_sweeps, hspace=0.3, wspace=0.2)

    colors = ['#2196F3', '#FF5722']  # Blue, Orange
    skipped_warnings = []

    for sweep_idx, (points, label) in enumerate(zip(points_list, labels)):
        # Build arrays across ALL valid points — nan for missing waveforms.
        # This makes _ratio_ok() reflect true waveform coverage.
        base = [p for p in points if p.get('valid')]
        if not base:
            skipped_warnings.append(f"{label}: No valid points")
            continue

        ccs = np.array([p.get('midi_cc', float('nan')) for p in base], dtype=float)

        def _wf_val(p, key):
            """Return waveform metric if present, else nan."""
            if p.get('has_waveform'):
                return p.get(key, float('nan'))
            return float('nan')

        shape_rmss  = np.array([_wf_val(p, 'shape_rms')  for p in base], dtype=float)
        peaks       = np.array([_wf_val(p, 'peak')       for p in base], dtype=float)
        dcs         = np.array([_wf_val(p, 'dc')         for p in base], dtype=float)
        range_asyms = np.array([_wf_val(p, 'range_asym') for p in base], dtype=float)
        crests      = np.array([_wf_val(p, 'crest')      for p in base], dtype=float)
        pos_peaks   = np.array([_wf_val(p, 'pos_peak')   for p in base], dtype=float)
        neg_peaks   = np.array([_wf_val(p, 'neg_peak')   for p in base], dtype=float)
        hfs         = np.array([_wf_val(p, 'hf')         for p in base], dtype=float)
        spec_peaks  = np.array([_wf_val(p, 'spectral_peak_hz') for p in base], dtype=float)

        # Row 1: Gain Track - ShapeRMS + Peak (gate on both)
        ax1 = fig.add_subplot(gs[0, sweep_idx])
        if _ratio_ok(shape_rmss) and _ratio_ok(peaks):
            ax1.plot(ccs, shape_rmss, 'o-', color=colors[0], label='ShapeRMS', linewidth=2)
            ax1.plot(ccs, peaks, 's-', color=colors[1], label='Peak', linewidth=2)
            ax1.legend(loc='best')
        else:
            skipped_warnings.append(f"{label} Row 1: <50% valid for Gain Track")
            ax1.text(0.5, 0.5, 'Insufficient data', ha='center', va='center',
                    transform=ax1.transAxes, fontsize=12, color='gray')
        ax1.set_xlabel('MIDI CC')
        ax1.set_ylabel('Amplitude')
        ax1.set_title(f'{label} - Gain Track')
        ax1.grid(True, alpha=0.3)

        # Row 2: DC Offset + Range Asymmetry (gate on both)
        ax2 = fig.add_subplot(gs[1, sweep_idx])
        if _ratio_ok(dcs) and _ratio_ok(range_asyms):
            ax2_r = ax2.twinx()
            l1, = ax2.plot(ccs, dcs, 'o-', color=colors[0], label='DC Offset', linewidth=2)
            l2, = ax2_r.plot(ccs, range_asyms, 's-', color=colors[1], label='Range Asym', linewidth=2)
            ax2.set_ylabel('DC Offset', color=colors[0])
            ax2_r.set_ylabel('Range Asymmetry', color=colors[1])
            ax2.legend([l1, l2], ['DC Offset', 'Range Asym'], loc='best')
        else:
            skipped_warnings.append(f"{label} Row 2: <50% valid for DC & Asymmetry")
            ax2.text(0.5, 0.5, 'Insufficient data', ha='center', va='center',
                    transform=ax2.transAxes, fontsize=12, color='gray')
        ax2.set_xlabel('MIDI CC')
        ax2.set_title(f'{label} - DC & Asymmetry')
        ax2.grid(True, alpha=0.3)

        # Row 3: Crest Factor (gate)
        ax3 = fig.add_subplot(gs[2, sweep_idx])
        if _ratio_ok(crests):
            ax3.plot(ccs, crests, 'o-', color=colors[0], label='Crest Factor', linewidth=2)

            # Theoretical guides for oscillators (P0.7)
            if show_guides:
                guides = {
                    'sine': np.sqrt(2),      # ~1.414
                    'saw': np.sqrt(3),       # ~1.732
                    'square': 1.0,
                }
                for name, val in guides.items():
                    ax3.axhline(y=val, color='gray', linestyle='--', alpha=0.5)
                    ax3.text(ccs.max() + 2, val, name, va='center', fontsize=8, color='gray',
                            clip_on=False)
                # Add right margin so text isn't clipped
                ax3.set_xlim(ccs.min() - 2, ccs.max() + 15)
        else:
            skipped_warnings.append(f"{label} Row 3: <50% valid for Crest Factor")
            ax3.text(0.5, 0.5, 'Insufficient data', ha='center', va='center',
                    transform=ax3.transAxes, fontsize=12, color='gray')
        ax3.set_xlabel('MIDI CC')
        ax3.set_ylabel('Crest Factor')
        ax3.set_title(f'{label} - Crest Factor')
        ax3.grid(True, alpha=0.3)

        # Row 4: Waveform Envelope (gate on pos_peak, neg_peak, dc)
        ax4 = fig.add_subplot(gs[3, sweep_idx])
        if _ratio_ok(pos_peaks) and _ratio_ok(neg_peaks) and _ratio_ok(dcs):
            ax4.fill_between(ccs, neg_peaks, pos_peaks, alpha=0.3, color=colors[0])
            ax4.plot(ccs, pos_peaks, '-', color=colors[0], label='Pos Peak', linewidth=1)
            ax4.plot(ccs, neg_peaks, '-', color=colors[0], label='Neg Peak', linewidth=1)
            ax4.plot(ccs, dcs, '--', color=colors[1], label='DC', linewidth=2)
            ax4.legend(loc='best')
        else:
            skipped_warnings.append(f"{label} Row 4: <50% valid for Waveform Envelope")
            ax4.text(0.5, 0.5, 'Insufficient data', ha='center', va='center',
                    transform=ax4.transAxes, fontsize=12, color='gray')
        ax4.set_xlabel('MIDI CC')
        ax4.set_ylabel('Amplitude')
        ax4.set_title(f'{label} - Waveform Envelope')
        ax4.grid(True, alpha=0.3)

        # Row 5: HF Energy (gate)
        ax5 = fig.add_subplot(gs[4, sweep_idx])
        if _ratio_ok(hfs):
            ax5.plot(ccs, hfs, 'o-', color=colors[0], label='HF', linewidth=2)
        else:
            skipped_warnings.append(f"{label} Row 5: <50% valid for HF Energy")
            ax5.text(0.5, 0.5, 'Insufficient data', ha='center', va='center',
                    transform=ax5.transAxes, fontsize=12, color='gray')
        ax5.set_xlabel('MIDI CC')
        ax5.set_ylabel('HF (Edge Sharpness)')
        ax5.set_title(f'{label} - HF Energy')
        ax5.grid(True, alpha=0.3)

        # Row 6: Spectral Peak Frequency (gate)
        ax6 = fig.add_subplot(gs[5, sweep_idx])
        if _ratio_ok(spec_peaks):
            ax6.plot(ccs, spec_peaks, 'o-', color=colors[0], label='Spectral Peak', linewidth=2)
        else:
            skipped_warnings.append(f"{label} Row 6: <50% valid for Spectral Peak")
            ax6.text(0.5, 0.5, 'Insufficient data', ha='center', va='center',
                    transform=ax6.transAxes, fontsize=12, color='gray')
        ax6.set_xlabel('MIDI CC')
        ax6.set_ylabel('Frequency (Hz)')
        ax6.set_title(f'{label} - Spectral Peak')
        ax6.grid(True, alpha=0.3)

    # Print warnings for skipped traces
    for warning in skipped_warnings:
        print(f"Plot warning: {warning}")

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved to: {output_path}")


# =============================================================================
# Dual-Sweep Alignment
# =============================================================================

def align_sweeps(points_a: List[dict], points_b: List[dict]) -> Tuple[List[dict], List[dict]]:
    """
    Align two sweeps for comparison (one-to-one matching).

    Primary: align by midi_cc (exact match)
    Fallback: align by cv_voltage (nearest within 0.1V)
    Tie-break: smallest |deltaV|, then nearest CC, then index

    Each B point can only be matched once (one-to-one).
    Unmatched A points become gaps.

    Returns aligned copies of both point lists.
    """
    # Build indexed list of valid B points for one-to-one tracking
    b_valid = [(i, p) for i, p in enumerate(points_b) if p.get('valid')]
    used_b_indices = set()

    aligned_a = []
    aligned_b = []
    warnings = []

    for p_a in points_a:
        if not p_a.get('valid'):
            continue

        cc_a = p_a['midi_cc']
        cv_a = p_a['cv_voltage']
        match_b = None
        match_b_idx = None

        # Try exact CC match (first unused)
        for b_idx, p_b in b_valid:
            if b_idx in used_b_indices:
                continue
            if p_b['midi_cc'] == cc_a:
                match_b = p_b
                match_b_idx = b_idx
                break

        # Fallback: nearest CV within 0.1V (unused, sorted by |deltaV| then CC then index)
        if match_b is None:
            candidates = []
            for b_idx, p_b in b_valid:
                if b_idx in used_b_indices:
                    continue
                delta_v = abs(p_b['cv_voltage'] - cv_a)
                if delta_v <= 0.1:
                    delta_cc = abs(p_b['midi_cc'] - cc_a)
                    candidates.append((delta_v, delta_cc, b_idx, p_b))

            if candidates:
                # Sort by |deltaV|, then |deltaCC|, then index
                candidates.sort(key=lambda x: (x[0], x[1], x[2]))
                _, _, match_b_idx, match_b = candidates[0]

        if match_b is not None:
            aligned_a.append(p_a)
            aligned_b.append(match_b)
            used_b_indices.add(match_b_idx)
        else:
            warnings.append(f"No match for CC {cc_a} / {cv_a:.3f}V")
            # Produce gap in B trace (placeholder with no waveform data)
            aligned_a.append(p_a)
            aligned_b.append({
                'valid': True,
                'has_waveform': False,
                'cv_voltage': cv_a,
                'midi_cc': cc_a,
                'freq': float('nan'),
            })

    if warnings:
        print(f"Alignment warnings: {len(warnings)} points unmatched")
        for w in warnings[:3]:
            print(f"  {w}")
        if len(warnings) > 3:
            print(f"  ... and {len(warnings) - 3} more")

    return aligned_a, aligned_b


# =============================================================================
# Patch JSON (P0.5)
# =============================================================================

def patch_morph_map(filepath: Path, morph_map: dict,
                    points: List[dict], num_harmonics: int) -> bool:
    """
    Write computed spectral fields back into morph map JSON (opt-in only).

    Tags patched files with analysis_version and fft_params.
    Returns True if file was modified.
    """
    snapshots = morph_map.get('snapshots', [])
    patched_count = 0

    for i, snap in enumerate(snapshots):
        if i >= len(points):
            break

        p = points[i]
        if not p.get('has_waveform') or not p.get('spectral_computed'):
            continue

        # Ensure snapshot dict exists
        if 'snapshot' not in snap or snap['snapshot'] is None:
            continue

        # Write spectral features (NaN → None for valid JSON)
        snap['snapshot']['spectral'] = {
            'spectral_centroid_hz': _json_num(p.get('spectral_centroid_hz')),
            'spectral_tilt': _json_num(p.get('spectral_tilt')),
            'spectral_tilt_slope': _json_num(p.get('spectral_tilt_slope')),
            'spectral_peak_hz': _json_num(p.get('spectral_peak_hz')),
            'spectral_peak_bin': p.get('spectral_peak_bin', 0),
            'spectral_peak_bin_frac': p.get('spectral_peak_bin_frac', 0.0),
            'thd': _json_num(p.get('thd')),
            'thd_valid': p.get('thd_valid', False),
            'num_harmonics_actual': p.get('num_harmonics_actual', 0),
        }
        patched_count += 1

    if patched_count == 0:
        print("No snapshots needed patching.")
        return False

    # Tag metadata
    if 'metadata' not in morph_map:
        morph_map['metadata'] = {}
    morph_map['metadata']['analysis_version'] = ANALYSIS_VERSION
    morph_map['metadata']['fft_params'] = {
        'window': 'hann',
        'zero_pad': False,
        'num_harmonics': num_harmonics,
    }

    # Write back
    with open(filepath, 'w') as f:
        json.dump(morph_map, f, indent=2)

    print(f"Patched {patched_count} snapshots in {filepath}")
    print(f"  Tagged with analysis_version={ANALYSIS_VERSION}")
    return True


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='CV Sweep Waveform Analyzer v3 — Three-Track + Spectral',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/analyze_morph_map.py maps/sweep.json
  python tools/analyze_morph_map.py maps/sweep.json --csv
  python tools/analyze_morph_map.py maps/sweep.json --plot
  python tools/analyze_morph_map.py maps/A.json maps/B.json --plot
  python tools/analyze_morph_map.py maps/sweep.json --plot --no-guides
  python tools/analyze_morph_map.py maps/sweep.json --patch-json
"""
    )

    parser.add_argument('files', nargs='+', help='Morph map JSON file(s) to analyze')
    parser.add_argument('--csv', nargs='?', const=True, default=False,
                       help='Export to CSV (optional: specify path)')
    parser.add_argument('--plot', nargs='?', const=True, default=False,
                       help='Generate PNG plot (optional: specify path)')
    parser.add_argument('--no-guides', action='store_true',
                       help='Suppress theoretical crest guides on plot')
    parser.add_argument('--patch-json', action='store_true',
                       help='Write computed spectral fields back into morph map JSON (P0.5)')

    args = parser.parse_args()

    # Validate input files
    filepaths = []
    for f in args.files:
        p = Path(f)
        if not p.exists():
            print(f"Error: File not found: {f}")
            sys.exit(1)
        filepaths.append(p)

    if len(filepaths) > 2:
        print("Error: Maximum 2 files supported for dual-sweep comparison")
        sys.exit(1)

    # Load and process files
    all_morph_maps = []
    all_points = []
    all_metadata = []

    for fp in filepaths:
        morph_map = load_morph_map(str(fp))
        metadata = extract_metadata(morph_map)

        # Device-aware harmonic count (P0.7)
        device_type = metadata['device_type']
        defaults = DEVICE_DEFAULTS.get(device_type, DEVICE_DEFAULTS['oscillator'])
        num_harmonics = defaults['num_harmonics']

        points = process_all_snapshots(morph_map, num_harmonics)

        all_morph_maps.append(morph_map)
        all_points.append(points)
        all_metadata.append(metadata)

    # Primary analysis (first file)
    morph_map = all_morph_maps[0]
    points = all_points[0]
    metadata = all_metadata[0]
    filepath = filepaths[0]
    device_type = metadata['device_type']

    # P0.5: Warn about missing fields that were computed in-memory
    computed_count = sum(1 for p in points if p.get('spectral_computed'))
    if computed_count > 0 and not args.patch_json:
        print(f"Note: {computed_count} snapshots had spectral features computed in-memory.")
        print(f"  Use --patch-json to write these fields back to the JSON file.\n")

    # Compute analysis
    regions = detect_regions(points, device_type)
    behavior = compute_sweep_behavior(points)

    # Console output
    print_console_output(str(filepath), morph_map, points, metadata, regions, behavior)

    # --patch-json (P0.5)
    if args.patch_json:
        defaults = DEVICE_DEFAULTS.get(device_type, DEVICE_DEFAULTS['oscillator'])
        for i, fp in enumerate(filepaths):
            patch_morph_map(fp, all_morph_maps[i], all_points[i],
                          defaults['num_harmonics'])

    # CSV export
    if args.csv:
        if len(all_points) == 1:
            # Single sweep
            if args.csv is True:
                csv_path = filepath.parent / f"{filepath.stem}_analysis.csv"
            else:
                csv_path = Path(args.csv)
            export_csv(points, csv_path)
        else:
            # Dual-sweep: separate CSV files with _A/_B suffixes in their own directories
            if args.csv is True:
                csv_path_a = filepaths[0].parent / f"{filepaths[0].stem}_analysis_A.csv"
                csv_path_b = filepaths[1].parent / f"{filepaths[1].stem}_analysis_B.csv"
            else:
                # Custom path provided - add _A/_B suffixes
                base_path = Path(args.csv)
                csv_path_a = base_path.parent / f"{base_path.stem}_A{base_path.suffix}"
                csv_path_b = base_path.parent / f"{base_path.stem}_B{base_path.suffix}"
            export_csv(all_points[0], csv_path_a)
            export_csv(all_points[1], csv_path_b)

    # Plot generation
    if args.plot:
        if args.plot is True:
            plot_path = filepath.parent / f"{filepath.stem}_analysis.png"
        else:
            plot_path = Path(args.plot)

        labels = [fp.stem for fp in filepaths]
        show_guides = not args.no_guides

        # Align sweeps for dual-sweep comparison
        plot_points = all_points
        if len(all_points) == 2:
            a_aligned, b_aligned = align_sweeps(all_points[0], all_points[1])
            plot_points = [a_aligned, b_aligned]

        generate_plot(plot_points, labels, plot_path, device_type, show_guides)


if __name__ == "__main__":
    main()
