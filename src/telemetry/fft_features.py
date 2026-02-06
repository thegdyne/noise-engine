"""
FFT Feature Extraction — Single Source of Truth (SSOT)

Shared module for spectral feature computation used by both
FingerprintExtractor and analyze_morph_map.py.

All FFT-derived metrics are computed here. No inline FFT logic
should exist in other modules.

Locked definitions:
    Windowing:  Hann
    DC handling: exclude bin 0
    Magnitude:  np.abs(np.fft.rfft(windowed))
    n_fft:      len(waveform) post-trim — no zero-padding
    Peak:       argmax + parabolic interpolation (log-magnitude)
    Harmonics:  nearest-bin to fund_bin * n
    Centroid:   sum(f * mag) / sum(mag) over bins > 0
    Tilt:       linear regression of log10(harmonic mags) vs index
    THD:        sqrt(sum(harmonic² excl peak)) / peak_mag
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


MAX_HARMONICS = 32
EPS = 1e-12


# =============================================================================
# Core FFT
# =============================================================================

def compute_fft(waveform: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Apply Hann window and compute FFT.

    n_fft = len(waveform). No zero-padding.

    Returns:
        (magnitudes, phases) arrays from rfft
    """
    w = np.asarray(waveform, dtype=np.float64)
    windowed = w * np.hanning(len(w))
    fft = np.fft.rfft(windowed)
    return np.abs(fft), np.angle(fft)


# =============================================================================
# Fundamental Detection
# =============================================================================

def find_fundamental_bin(magnitudes: np.ndarray, freq_hz: Optional[float],
                         sample_rate: int, n_fft: int) -> Tuple[int, float]:
    """Resolve fundamental bin from provided or auto-detected frequency.

    Returns (fund_bin, freq_hz).
    """
    if freq_hz is None or not (10 <= freq_hz <= 20000):
        # Auto-detect: strongest bin (skip DC)
        fund_bin = int(np.argmax(magnitudes[1:]) + 1)
        freq_hz = float(fund_bin * sample_rate / n_fft)
    else:
        fund_bin = int(round(freq_hz * n_fft / sample_rate))
        max_bin = len(magnitudes) - 1
        fund_bin = int(np.clip(fund_bin, 1, max_bin))
        freq_hz = float(fund_bin * sample_rate / n_fft)

    return fund_bin, freq_hz


# =============================================================================
# Spectral Peak (P0.3)
# =============================================================================

def find_spectral_peak(magnitudes: np.ndarray, sample_rate: int,
                       n_fft: int) -> Dict:
    """Find spectral peak with parabolic interpolation.

    Excludes DC bin (bin 0). Uses log-magnitude parabolic
    interpolation on (k-1, k, k+1) for sub-bin accuracy.

    Returns dict with:
        spectral_peak_bin (int)
        spectral_peak_bin_frac (float)
        spectral_peak_hz (float)
    """
    if len(magnitudes) < 3:
        return {
            'spectral_peak_bin': 0,
            'spectral_peak_bin_frac': 0.0,
            'spectral_peak_hz': 0.0,
        }

    # Find peak bin (skip DC)
    peak_bin = int(np.argmax(magnitudes[1:]) + 1)

    # Parabolic interpolation on log magnitudes
    frac_bin = float(peak_bin)
    if 1 <= peak_bin - 1 and peak_bin + 1 < len(magnitudes):
        alpha = np.log(magnitudes[peak_bin - 1] + EPS)
        beta = np.log(magnitudes[peak_bin] + EPS)
        gamma = np.log(magnitudes[peak_bin + 1] + EPS)

        denom = alpha - 2 * beta + gamma
        if abs(denom) > EPS:
            delta = 0.5 * (alpha - gamma) / denom
            frac_bin = peak_bin + delta

    freq_hz = frac_bin * sample_rate / n_fft

    return {
        'spectral_peak_bin': peak_bin,
        'spectral_peak_bin_frac': round(frac_bin, 4),
        'spectral_peak_hz': round(freq_hz, 2),
    }


# =============================================================================
# Harmonic Extraction
# =============================================================================

def extract_harmonics(magnitudes: np.ndarray, fund_bin: int,
                      num_harmonics: int = 8) -> List[float]:
    """Extract harmonic magnitude ratios normalized to fundamental.

    Uses nearest-bin selection: harmonic n is at bin fund_bin * n.
    h1 is always 1.0 (the fundamental itself).
    """
    fund_mag = magnitudes[fund_bin] if fund_bin < len(magnitudes) else 0.0
    if fund_mag < EPS:
        fund_mag = EPS

    ratios = []
    for h in range(1, num_harmonics + 1):
        bin_idx = fund_bin * h
        if bin_idx < len(magnitudes):
            ratios.append(round(float(magnitudes[bin_idx] / fund_mag), 4))
        else:
            ratios.append(0.0)
    return ratios


def extract_phases(phases: np.ndarray, fund_bin: int,
                   num_harmonics: int = 8) -> List[float]:
    """Extract phase relationships in cycles (0..1) relative to fundamental."""
    fund_phase = phases[fund_bin] if fund_bin < len(phases) else 0.0

    phase_rel = []
    for h in range(1, num_harmonics + 1):
        bin_idx = fund_bin * h
        if bin_idx < len(phases):
            rel = phases[bin_idx] - (fund_phase * h)
            cycles = (rel / (2 * np.pi)) % 1.0
            phase_rel.append(round(float(cycles), 4))
        else:
            phase_rel.append(0.0)
    return phase_rel


def normalize_harmonics(harmonics: List[float],
                        target_length: int = MAX_HARMONICS) -> List[float]:
    """Pad or truncate harmonic array to fixed length (P0.1).

    Pads with 0.0 if shorter, truncates if longer.
    """
    result = list(harmonics[:target_length])
    while len(result) < target_length:
        result.append(0.0)
    return result


# =============================================================================
# THD (P0.2)
# =============================================================================

def compute_thd(magnitudes: np.ndarray, fund_bin: int,
                num_harmonics: int = 8) -> Tuple[float, bool]:
    """Compute THD referenced to spectral peak (V1 — single reference).

    THD = sqrt(sum(harmonic_bins² excluding peak and fundamental)) / peak_mag

    Returns:
        (thd, thd_valid) — ratio 0..inf, validity flag.
        If peak magnitude < eps: thd=NaN, thd_valid=False.
    """
    if len(magnitudes) < 2:
        return float('nan'), False

    # Peak = spectral peak (skip DC)
    peak_bin = int(np.argmax(magnitudes[1:]) + 1)
    peak_mag = float(magnitudes[peak_bin])

    if peak_mag < EPS:
        return float('nan'), False

    # Sum harmonic power excluding peak bin and fundamental bin
    harmonic_power = 0.0
    for h in range(1, num_harmonics + 1):
        bin_idx = fund_bin * h
        if bin_idx < len(magnitudes) and bin_idx not in (peak_bin, fund_bin):
            harmonic_power += magnitudes[bin_idx] ** 2

    thd = float(np.sqrt(harmonic_power) / peak_mag)
    return round(thd, 6), True


# =============================================================================
# Spectral Shape
# =============================================================================

def compute_spectral_centroid(magnitudes: np.ndarray, sample_rate: int,
                              n_fft: int) -> float:
    """Compute spectral centroid: sum(f * mag) / sum(mag).

    Excludes DC bin. Returns frequency in Hz.
    """
    if len(magnitudes) < 2:
        return 0.0

    freqs = np.arange(1, len(magnitudes)) * sample_rate / n_fft
    mags = magnitudes[1:]

    total_mag = float(np.sum(mags))
    if total_mag < EPS:
        return 0.0

    return float(np.sum(freqs * mags) / total_mag)


def compute_spectral_tilt(magnitudes: np.ndarray, fund_bin: int,
                          num_harmonics: int = 8) -> float:
    """Compute spectral tilt: linear regression of log magnitudes.

    Fits log10(magnitude) vs harmonic index (1..N).
    Returns normalized 0..1:
        0.0 = steeply falling (-1 slope)
        0.5 = flat (0 slope)
        1.0 = rising (+1 slope)
    """
    mags = []
    indices = []
    for h in range(1, num_harmonics + 1):
        bin_idx = fund_bin * h
        if bin_idx < len(magnitudes):
            mags.append(float(magnitudes[bin_idx]))
            indices.append(h)

    if len(mags) < 2:
        return 0.5

    log_mags = np.log10(np.array(mags) + EPS)
    indices_arr = np.array(indices, dtype=float)

    slope, _ = np.polyfit(indices_arr, log_mags, 1)
    return round(float(np.clip((slope + 1) / 2, 0.0, 1.0)), 4)


# =============================================================================
# SNR
# =============================================================================

def estimate_snr(magnitudes: np.ndarray, fund_bin: int,
                 num_harmonics: int = 8) -> float:
    """Estimate signal-to-noise ratio in dB from FFT magnitudes.

    Signal = sum of harmonic bin magnitudes².
    Noise = total power - signal power.
    """
    signal_power = 0.0
    for h in range(1, num_harmonics + 1):
        bin_idx = fund_bin * h
        if bin_idx < len(magnitudes):
            signal_power += magnitudes[bin_idx] ** 2

    total_power = float(np.sum(magnitudes ** 2))
    noise_power = total_power - signal_power

    if noise_power < EPS:
        return 60.0
    return float(10 * np.log10(signal_power / noise_power))


# =============================================================================
# Primary Entry Point
# =============================================================================

def compute_all(waveform: np.ndarray, freq_hz: Optional[float] = None,
                sample_rate: int = 48000,
                num_harmonics: int = 8,
                include_raw: bool = False) -> Dict:
    """Compute all FFT features from a waveform.

    This is the primary entry point. Both FingerprintExtractor and
    analyze_morph_map.py call this — no inline FFT logic elsewhere.

    Procedure:
        1. Hann window
        2. FFT (n_fft = len(waveform), no zero-padding)
        3. Find fundamental
        4. Parabolic peak interpolation
        5. Extract harmonics + phases
        6. THD (peak-referenced)
        7. Centroid, tilt, SNR

    Args:
        waveform: Audio samples (post-trim, any length)
        freq_hz: Known fundamental (None = auto-detect)
        sample_rate: Sample rate in Hz
        num_harmonics: Number of harmonics to extract
        include_raw: If True, include 'magnitudes' and 'phases' numpy
            arrays in the result. Default False to prevent accidental
            JSON serialization failures.
    """
    w = np.asarray(waveform, dtype=np.float64)
    n_fft = len(w)

    # 1-2. Hann window + FFT
    magnitudes, phases = compute_fft(w)

    # 3. Find fundamental
    fund_bin, detected_freq = find_fundamental_bin(
        magnitudes, freq_hz, sample_rate, n_fft
    )

    # 4. Spectral peak (sub-bin accurate)
    peak_info = find_spectral_peak(magnitudes, sample_rate, n_fft)

    # 5. Harmonics + phases
    harm_ratio = extract_harmonics(magnitudes, fund_bin, num_harmonics)
    phase_rel = extract_phases(phases, fund_bin, num_harmonics)

    # 6. THD
    thd, thd_valid = compute_thd(magnitudes, fund_bin, num_harmonics)

    # 7. Centroid + tilt + SNR
    centroid_hz = compute_spectral_centroid(magnitudes, sample_rate, n_fft)
    tilt = compute_spectral_tilt(magnitudes, fund_bin, num_harmonics)
    snr_db = estimate_snr(magnitudes, fund_bin, num_harmonics)

    result = {
        # FFT parameters
        'n_fft': n_fft,
        'window': 'hann',
        'fund_bin': fund_bin,
        'freq_hz': round(detected_freq, 2),

        # Harmonics
        'harm_ratio': harm_ratio,
        'phase_rel': phase_rel,
        'num_harmonics_actual': len([r for r in harm_ratio if r > 0]) or len(harm_ratio),

        # THD (P0.2)
        'thd': thd,
        'thd_valid': thd_valid,

        # Spectral peak (P0.3)
        'spectral_peak_bin': peak_info['spectral_peak_bin'],
        'spectral_peak_bin_frac': peak_info['spectral_peak_bin_frac'],
        'spectral_peak_hz': peak_info['spectral_peak_hz'],

        # Spectral shape
        'spectral_centroid_hz': round(centroid_hz, 2),
        'spectral_tilt': tilt,
        'snr_db': round(snr_db, 1),
    }

    if include_raw:
        result['magnitudes'] = magnitudes
        result['phases'] = phases

    return result
