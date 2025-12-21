"""
imaginarium/analyze.py
Audio feature extraction per IMAGINARIUM_SPEC v10 §4.2, §10

Extracts normalized features from rendered audio:
- centroid: spectral centroid (brightness)
- flatness: spectral flatness (noisiness)
- onset_density: attack transients per second
- crest: peak-to-RMS ratio (dynamics)
- width: stereo correlation
- harmonicity: harmonic content ratio
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import logging

from .config import NORMALIZATION_V1, RENDER_CONFIG
from .models import CandidateFeatures

logger = logging.getLogger(__name__)


def load_audio(path: Path) -> Tuple[np.ndarray, int]:
    """Load audio file, returns (samples, sample_rate)."""
    try:
        import soundfile as sf
        data, sr = sf.read(path, dtype='float32')
        return data, sr
    except ImportError:
        pass
    
    try:
        import librosa
        data, sr = librosa.load(path, sr=None, mono=False)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        else:
            data = data.T
        return data.astype(np.float32), sr
    except ImportError:
        pass
    
    raise ImportError("Install soundfile or librosa for audio loading")


def normalize_value(value: float, feature_name: str) -> float:
    """
    Normalize a raw feature value to 0-1 range.
    
    Uses NORMALIZATION_V1 from config.
    """
    spec = NORMALIZATION_V1.get(feature_name)
    if spec is None:
        return float(np.clip(value, 0, 1))
    
    lo, hi = spec["range"]
    curve = spec.get("curve", "linear")
    
    if curve == "log":
        # Log scale normalization
        value = max(value, lo)  # Avoid log(0)
        value = min(value, hi)
        return float((np.log(value) - np.log(lo)) / (np.log(hi) - np.log(lo)))
    else:
        # Linear normalization
        return float(np.clip((value - lo) / (hi - lo), 0, 1))


def extract_features(
    audio_path: Path,
    sample_rate: Optional[int] = None,
) -> CandidateFeatures:
    """
    Extract acoustic features from an audio file.
    
    Args:
        audio_path: Path to WAV file
        sample_rate: Override sample rate (uses file's rate if None)
        
    Returns:
        CandidateFeatures with all values normalized 0-1
    """
    try:
        import librosa
    except ImportError:
        raise ImportError("librosa required for feature extraction: pip install librosa")
    
    # Load audio
    samples, sr = load_audio(audio_path)
    
    # Convert to mono for most features
    if samples.ndim > 1:
        mono = np.mean(samples, axis=1)
        stereo = samples
    else:
        mono = samples
        stereo = None
    
    # === Spectral Centroid (brightness) ===
    centroid = librosa.feature.spectral_centroid(y=mono, sr=sr)[0]
    centroid_mean = float(np.mean(centroid))
    centroid_norm = normalize_value(centroid_mean, "centroid")
    
    # === Spectral Flatness (noisiness) ===
    flatness = librosa.feature.spectral_flatness(y=mono)[0]
    flatness_mean = float(np.mean(flatness))
    flatness_norm = normalize_value(flatness_mean, "flatness")
    
    # === Onset Density (transients per second) ===
    onset_env = librosa.onset.onset_strength(y=mono, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    duration = len(mono) / sr
    onset_rate = len(onsets) / max(duration, 0.1)
    onset_norm = normalize_value(onset_rate, "onset_density")
    
    # === Crest Factor (peak/RMS ratio in dB) ===
    rms = np.sqrt(np.mean(mono ** 2))
    peak = np.max(np.abs(mono))
    if rms > 1e-10:
        crest_db = 20 * np.log10(peak / rms)
    else:
        crest_db = 0.0
    crest_norm = normalize_value(crest_db, "crest")
    
    # === Stereo Width ===
    if stereo is not None and stereo.shape[1] >= 2:
        left = stereo[:, 0]
        right = stereo[:, 1]
        # Correlation: 1 = identical (mono), 0 = uncorrelated, -1 = inverted
        # Width = 1 - correlation (higher = wider)
        if np.std(left) > 1e-10 and np.std(right) > 1e-10:
            correlation = np.corrcoef(left, right)[0, 1]
            width = (1 - correlation) / 2  # Map to 0-1
        else:
            width = 0.0
    else:
        width = 0.0
    width_norm = normalize_value(width, "width")
    
    # === Harmonicity ===
    # Use harmonic-percussive separation ratio
    try:
        harmonic, percussive = librosa.effects.hpss(mono)
        harm_energy = np.sum(harmonic ** 2)
        perc_energy = np.sum(percussive ** 2)
        total_energy = harm_energy + perc_energy
        if total_energy > 1e-10:
            harmonicity = harm_energy / total_energy
        else:
            harmonicity = 0.5
    except Exception:
        # Fallback if HPSS fails
        harmonicity = 0.5
    harmonicity_norm = normalize_value(harmonicity, "harmonicity")
    
    return CandidateFeatures(
        centroid=centroid_norm,
        flatness=flatness_norm,
        onset_density=onset_norm,
        crest=crest_norm,
        width=width_norm,
        harmonicity=harmonicity_norm,
    )


def extract_features_batch(
    audio_paths: list[Path],
    progress_callback=None,
) -> list[CandidateFeatures]:
    """
    Extract features from multiple audio files.
    
    Args:
        audio_paths: List of paths
        progress_callback: Optional callback(current, total, path)
        
    Returns:
        List of CandidateFeatures
    """
    results = []
    for i, path in enumerate(audio_paths):
        if progress_callback:
            progress_callback(i, len(audio_paths), path)
        
        try:
            features = extract_features(path)
            results.append(features)
        except Exception as e:
            logger.warning(f"Feature extraction failed for {path}: {e}")
            # Return default features on failure
            results.append(CandidateFeatures())
    
    return results
