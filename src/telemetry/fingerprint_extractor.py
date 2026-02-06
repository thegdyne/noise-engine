"""
Fingerprint Extractor v2

Extracts waveform fingerprints from telemetry snapshots.
Optimized for AI consumption across Claude/ChatGPT/Gemini.

All FFT-derived features computed via the SSOT module (fft_features.py).
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from src.telemetry.fft_features import compute_all as fft_compute_all


class FingerprintExtractor:
    """Extract fingerprint from telemetry waveform data."""

    SCHEMA_VERSION = "fingerprint.v2"
    N_MORPH = 5

    def __init__(self, device_make: str = "Unknown",
                 device_model: str = "Unknown",
                 device_variant: str = "original", unit_id: str = "A",
                 num_harmonics: int = 8):
        self.device = {
            "make": device_make,
            "model": device_model,
            "variant": device_variant,
            "unit_id": unit_id
        }
        self.num_harmonics = num_harmonics
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
            Fingerprint dict matching schema v2
        """
        if self.session_id is None:
            self.start_session()

        waveform = np.asarray(waveform, dtype=np.float64)

        # Trim to whole cycles to reduce spectral leakage
        if freq_hz is not None and 10 <= freq_hz <= 20000:
            samples_per_cycle = sample_rate / freq_hz
            num_cycles = int(len(waveform) / samples_per_cycle)
            if num_cycles >= 1:
                trim_length = round(num_cycles * samples_per_cycle)
                if trim_length >= 64:
                    waveform = waveform[:trim_length]

        n_samples = len(waveform)

        # All FFT features via SSOT module (Hann window + no zero-padding)
        fft_result = fft_compute_all(
            waveform, freq_hz=freq_hz,
            sample_rate=sample_rate,
            num_harmonics=self.num_harmonics
        )

        harm_ratio = fft_result['harm_ratio']
        phase_rel = fft_result['phase_rel']
        detected_freq = fft_result['freq_hz']

        # Morphology metrics (time-domain + harmonic-derived)
        morph = self._compute_morphology(waveform, harm_ratio)

        # Quality metrics (time-domain from original waveform)
        rms = float(np.sqrt(np.mean(waveform ** 2)))
        peak = float(np.max(np.abs(waveform)))
        snr_db = fft_result['snr_db']
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
                "freq_hz": round(detected_freq, 2),
                "sr_hz": sample_rate,
                "n_samples": n_samples,
                "fft_size": fft_result['n_fft'],
                "window": "hann",
                "num_harmonics": self.num_harmonics,
                "notes": notes or []
            },
            "features": {
                "harm_ratio": harm_ratio,
                "phase_rel": phase_rel,
                "morph": morph,
                "thd": fft_result['thd'],
                "thd_valid": fft_result['thd_valid'],
                "spectral_peak_bin": fft_result['spectral_peak_bin'],
                "spectral_peak_bin_frac": fft_result['spectral_peak_bin_frac'],
                "spectral_peak_hz": fft_result['spectral_peak_hz'],
                "spectral_centroid_hz": fft_result['spectral_centroid_hz'],
                "spectral_tilt": fft_result['spectral_tilt'],
                "num_harmonics_actual": fft_result['num_harmonics_actual'],
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

    def _compute_morphology(self, waveform: np.ndarray,
                            harm_ratio: List[float]) -> List[float]:
        """
        Compute 5 morphology metrics, all normalized 0..1.

        [0] symmetry: 1.0=odd harmonics dominant, 0.0=even dominant
        [1] crest_factor: normalized (actual-1)/(3-1)
        [2] spectral_centroid: center of mass in harmonic space, normalized
        [3] spectral_tilt: rolloff slope, normalized
        [4] brightness: high frequency energy ratio
        """
        n_harm = len(harm_ratio)

        # Symmetry: odd vs even harmonic energy
        odd_energy = sum(harm_ratio[i] ** 2 for i in range(0, n_harm, 2))
        even_energy = sum(harm_ratio[i] ** 2 for i in range(1, n_harm, 2))
        total = odd_energy + even_energy
        symmetry = odd_energy / total if total > 1e-10 else 0.5

        # Crest factor normalized
        rms = np.sqrt(np.mean(waveform ** 2))
        peak = np.max(np.abs(waveform))
        crest = peak / rms if rms > 1e-10 else 1.0
        crest_norm = np.clip((crest - 1.0) / 2.0, 0.0, 1.0)

        # Spectral centroid (center of mass in harmonic space)
        weights = np.array(harm_ratio)
        indices = np.arange(1, n_harm + 1)
        total_weight = np.sum(weights)
        if total_weight > 1e-10:
            centroid = np.sum(weights * indices) / total_weight
            centroid_norm = (centroid - 1) / max(n_harm - 1, 1)
        else:
            centroid_norm = 0.0

        # Spectral tilt (linear regression slope of log magnitudes)
        log_mags = np.log10(np.array(harm_ratio) + 1e-10)
        slope, _ = np.polyfit(indices, log_mags, 1)
        tilt_norm = np.clip((slope + 1) / 2, 0.0, 1.0)

        # Brightness (energy in upper half vs total)
        mid = n_harm // 2
        high_energy = sum(harm_ratio[i] ** 2 for i in range(mid, n_harm))
        brightness = high_energy / total if total > 1e-10 else 0.0

        return [
            round(float(symmetry), 4),
            round(float(crest_norm), 4),
            round(float(centroid_norm), 4),
            round(float(tilt_norm), 4),
            round(float(brightness), 4)
        ]

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
