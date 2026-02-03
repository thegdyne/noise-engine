"""
Fingerprint Extractor v1

Extracts waveform fingerprints from telemetry snapshots.
Optimized for AI consumption across Claude/ChatGPT/Gemini.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np


class FingerprintExtractor:
    """Extract fingerprint from telemetry waveform data."""

    SCHEMA_VERSION = "fingerprint.v1"
    N_HARMONICS = 8
    N_MORPH = 5

    def __init__(self, device_make: str, device_model: str,
                 device_variant: str = "original", unit_id: str = "A"):
        self.device = {
            "make": device_make,
            "model": device_model,
            "variant": device_variant,
            "unit_id": unit_id
        }
        self.session_id = None
        self.operator = "noise_engine"
        self.capture_index = 0

    def start_session(self, operator: str = "noise_engine") -> str:
        """Start a new capture session."""
        self.session_id = datetime.now().strftime("s%Y%m%d_%H%M%S")
        self.operator = operator
        self.capture_index = 0
        return self.session_id

    def extract(self, waveform: np.ndarray, cv_volts: float,
                cv_chan: str = "cv1", freq_hz: float = None,
                sample_rate: int = 48000, notes: List[str] = None) -> Dict:
        """
        Extract fingerprint from waveform.

        Args:
            waveform: Single-cycle or multi-cycle waveform samples
            cv_volts: CV voltage at capture
            cv_chan: CV channel name
            freq_hz: Detected fundamental (computed if None)
            sample_rate: Audio sample rate
            notes: Optional capture notes

        Returns:
            Fingerprint dict matching schema v1
        """
        if self.session_id is None:
            self.start_session()

        waveform = np.asarray(waveform, dtype=np.float64)
        n_samples = len(waveform)

        # Zero-pad to minimum 4096 samples for adequate frequency resolution
        # This ensures we can resolve harmonics even from short captures
        MIN_FFT_SIZE = 4096
        if n_samples < MIN_FFT_SIZE:
            # Window the original samples, then zero-pad
            windowed = waveform * np.hanning(n_samples)
            padded = np.zeros(MIN_FFT_SIZE)
            padded[:n_samples] = windowed
            fft = np.fft.rfft(padded)
            fft_size = MIN_FFT_SIZE
        else:
            # Sufficient samples - just window and transform
            windowed = waveform * np.hanning(n_samples)
            fft = np.fft.rfft(windowed)
            fft_size = n_samples

        magnitudes = np.abs(fft)
        phases = np.angle(fft)

        # Find fundamental frequency
        if freq_hz is None:
            # Auto-detect: find strongest bin (skip DC)
            fund_bin = np.argmax(magnitudes[1:]) + 1
            freq_hz = fund_bin * sample_rate / fft_size
        else:
            # Use provided frequency
            fund_bin = int(round(freq_hz * fft_size / sample_rate))
            fund_bin = max(1, fund_bin)  # Ensure we don't use DC bin

        # Extract harmonic ratios and phases
        harm_ratio = self._extract_harmonics(magnitudes, fund_bin)
        phase_rel = self._extract_phases(phases, fund_bin)

        # Morphology metrics (use original waveform, not padded)
        morph = self._compute_morphology(waveform, harm_ratio)

        # Quality metrics (use original waveform)
        rms = float(np.sqrt(np.mean(waveform ** 2)))
        peak = float(np.max(np.abs(waveform)))
        snr_db = self._estimate_snr(magnitudes, fund_bin)
        flags = self._check_quality_flags(waveform, rms, peak, snr_db)

        # Build fingerprint
        device_key = f"{self.device['model'].lower()}_{self.device['unit_id'].lower()}"
        device_key = device_key.replace(" ", "_")
        fp_id = f"{device_key}_{self.session_id}_c{self.capture_index:03d}"

        fingerprint = {
            "schema_version": self.SCHEMA_VERSION,
            "id": fp_id,
            "device": self.device.copy(),
            "session": {
                "id": self.session_id,
                "utc": datetime.utcnow().isoformat() + "Z",
                "operator": self.operator
            },
            "capture": {
                "index": self.capture_index,
                "cv": {"chan": cv_chan, "volts": round(cv_volts, 4)},
                "freq_hz": round(freq_hz, 2),
                "sr_hz": sample_rate,
                "n_samples": n_samples,  # Original sample count
                "fft_size": fft_size,    # Actual FFT size used
                "window": "hann",
                "notes": notes or []
            },
            "features": {
                "harm_ratio": harm_ratio,
                "phase_rel": phase_rel,
                "morph": morph
            },
            "quality": {
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "snr_db": round(snr_db, 1),
                "flags": flags
            },
            "adjacent": {
                "prev_id": None,  # Set by datastore
                "next_id": None,
                "delta_prev": {"l2_harm": 0.0, "l2_phase": 0.0, "l2_morph": 0.0}
            },
            "hash": {
                "features_sha1": self._hash_features(harm_ratio, phase_rel, morph)
            }
        }

        self.capture_index += 1
        return fingerprint

    def _extract_harmonics(self, magnitudes: np.ndarray, fund_bin: int) -> List[float]:
        """Extract harmonic magnitude ratios normalized to fundamental."""
        ratios = []
        fund_mag = magnitudes[fund_bin] if fund_bin < len(magnitudes) else 1.0
        if fund_mag < 1e-10:
            fund_mag = 1e-10

        for h in range(1, self.N_HARMONICS + 1):
            bin_idx = fund_bin * h
            if bin_idx < len(magnitudes):
                ratios.append(round(magnitudes[bin_idx] / fund_mag, 4))
            else:
                ratios.append(0.0)
        return ratios

    def _extract_phases(self, phases: np.ndarray, fund_bin: int) -> List[float]:
        """Extract phase relationships in cycles (0..1) relative to fundamental."""
        phase_rel = []
        fund_phase = phases[fund_bin] if fund_bin < len(phases) else 0.0

        for h in range(1, self.N_HARMONICS + 1):
            bin_idx = fund_bin * h
            if bin_idx < len(phases):
                # Relative phase in radians, then convert to cycles
                rel = phases[bin_idx] - (fund_phase * h)
                # Wrap to 0..1 cycles
                cycles = (rel / (2 * np.pi)) % 1.0
                phase_rel.append(round(cycles, 4))
            else:
                phase_rel.append(0.0)
        return phase_rel

    def _compute_morphology(self, waveform: np.ndarray, harm_ratio: List[float]) -> List[float]:
        """
        Compute 5 morphology metrics, all normalized 0..1.

        [0] symmetry: 1.0=odd harmonics dominant, 0.0=even dominant
        [1] crest_factor: normalized (actual-1)/(3-1)
        [2] spectral_centroid: center of mass in harmonic space, normalized
        [3] spectral_tilt: rolloff slope, normalized
        [4] brightness: high frequency energy ratio
        """
        # Symmetry: odd vs even harmonic energy
        odd_energy = sum(harm_ratio[i] ** 2 for i in range(0, 8, 2))   # h1,h3,h5,h7
        even_energy = sum(harm_ratio[i] ** 2 for i in range(1, 8, 2))  # h2,h4,h6,h8
        total = odd_energy + even_energy
        symmetry = odd_energy / total if total > 1e-10 else 0.5

        # Crest factor normalized
        rms = np.sqrt(np.mean(waveform ** 2))
        peak = np.max(np.abs(waveform))
        crest = peak / rms if rms > 1e-10 else 1.0
        crest_norm = np.clip((crest - 1.0) / 2.0, 0.0, 1.0)  # 1..3 -> 0..1

        # Spectral centroid (center of mass in harmonic space)
        weights = np.array(harm_ratio)
        indices = np.arange(1, self.N_HARMONICS + 1)
        total_weight = np.sum(weights)
        if total_weight > 1e-10:
            centroid = np.sum(weights * indices) / total_weight
            centroid_norm = (centroid - 1) / (self.N_HARMONICS - 1)  # 1..8 -> 0..1
        else:
            centroid_norm = 0.0

        # Spectral tilt (linear regression slope of log magnitudes)
        log_mags = np.log10(np.array(harm_ratio) + 1e-10)
        slope, _ = np.polyfit(indices, log_mags, 1)
        tilt_norm = np.clip((slope + 1) / 2, 0.0, 1.0)  # -1..1 -> 0..1

        # Brightness (energy in h5-h8 vs total)
        high_energy = sum(harm_ratio[i] ** 2 for i in range(4, 8))
        brightness = high_energy / total if total > 1e-10 else 0.0

        return [
            round(symmetry, 4),
            round(crest_norm, 4),
            round(centroid_norm, 4),
            round(tilt_norm, 4),
            round(brightness, 4)
        ]

    def _estimate_snr(self, magnitudes: np.ndarray, fund_bin: int) -> float:
        """Estimate signal-to-noise ratio in dB from FFT magnitudes."""
        # Signal = sum of harmonic magnitudes
        signal_power = 0.0
        for h in range(1, self.N_HARMONICS + 1):
            bin_idx = fund_bin * h
            if bin_idx < len(magnitudes):
                signal_power += magnitudes[bin_idx] ** 2

        # Noise = everything else
        total_power = np.sum(magnitudes ** 2)
        noise_power = total_power - signal_power

        if noise_power < 1e-10:
            return 60.0  # Very clean signal
        return 10 * np.log10(signal_power / noise_power)

    def _check_quality_flags(self, waveform: np.ndarray, rms: float,
                             peak: float, snr_db: float) -> List[str]:
        """Check for quality issues."""
        flags = []
        if peak > 0.99:
            flags.append("clipped")
        if snr_db < 20:
            flags.append("low_snr")
        if abs(np.mean(waveform)) > 0.05:
            flags.append("dc_offset")
        if rms < 0.01:
            flags.append("low_level")
        return flags

    def _hash_features(self, harm_ratio: List[float], phase_rel: List[float],
                       morph: List[float]) -> str:
        """Compute SHA1 hash of features for integrity verification."""
        data = json.dumps({
            "harm_ratio": harm_ratio,
            "phase_rel": phase_rel,
            "morph": morph
        }, sort_keys=True)
        return hashlib.sha1(data.encode()).hexdigest()[:12]
