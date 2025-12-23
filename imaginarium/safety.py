"""
imaginarium/safety.py
Audio safety gates per IMAGINARIUM_SPEC v10 §9

Checks rendered audio for:
- Silence (RMS too low)
- Sparse activity (not enough active frames)
- Clipping (samples at max)
- DC offset (mean too far from zero)
- Runaway (level growth over time)
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import logging

from .config import SAFETY_CONFIG
from .models import SafetyResult, SafetyStatus

logger = logging.getLogger(__name__)


def load_audio(path: Path) -> Tuple[np.ndarray, int]:
    """
    Load audio file and return samples + sample rate.
    
    Returns:
        Tuple of (samples as float32 -1 to 1, sample_rate)
    """
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
            data = data.T  # librosa returns (channels, samples)
        return data.astype(np.float32), sr
    except ImportError:
        pass
    
    raise ImportError("Install soundfile or librosa for audio loading")


def rms_db(samples: np.ndarray) -> float:
    """Calculate RMS level in dB."""
    rms = np.sqrt(np.mean(samples ** 2))
    if rms < 1e-10:
        return -100.0
    return 20 * np.log10(rms)


def check_safety(
    audio_path: Path,
    config: Optional[SAFETY_CONFIG.__class__] = None,
) -> SafetyResult:
    """
    Run all safety gate checks on an audio file.
    
    Args:
        audio_path: Path to WAV file
        config: Safety configuration (uses default if None)
        
    Returns:
        SafetyResult with pass/fail status and details
    """
    if config is None:
        config = SAFETY_CONFIG
    
    try:
        samples, sr = load_audio(audio_path)
    except Exception as e:
        return SafetyResult(
            passed=False,
            status=SafetyStatus.SILENCE,
            details={"error": str(e)},
        )
    
    # Convert to mono for analysis
    if samples.ndim > 1:
        mono = np.mean(samples, axis=1)
    else:
        mono = samples
    
    details = {}
    
    # === Gate 1: Audibility (RMS level) ===
    overall_rms = rms_db(mono)
    details["rms_db"] = overall_rms
    
    if overall_rms < config.min_rms_db:
        return SafetyResult(
            passed=False,
            status=SafetyStatus.SILENCE,
            details=details,
        )
    
    # === Gate 2: Active frames ===
    frame_length = config.frame_length
    hop_length = config.hop_length
    
    n_frames = 1 + (len(mono) - frame_length) // hop_length
    active_frames = 0
    
    for i in range(n_frames):
        start = i * hop_length
        end = start + frame_length
        frame = mono[start:end]
        frame_rms = rms_db(frame)
        if frame_rms > config.active_threshold_db:
            active_frames += 1
    
    active_pct = active_frames / max(n_frames, 1)
    details["active_frames_pct"] = active_pct
    details["n_frames"] = n_frames
    
    if active_pct < config.min_active_frames_pct:
        return SafetyResult(
            passed=False,
            status=SafetyStatus.SPARSE,
            details=details,
        )
    
    # === Gate 3: Clipping ===
    max_sample = np.max(np.abs(samples))
    details["max_sample"] = float(max_sample)
    
    if max_sample >= config.max_sample_value:
        return SafetyResult(
            passed=False,
            status=SafetyStatus.CLIPPING,
            details=details,
        )
    
    # === Gate 4: DC offset ===
    dc_offset = np.abs(np.mean(mono))
    details["dc_offset"] = float(dc_offset)
    
    if dc_offset > config.max_dc_offset:
        return SafetyResult(
            passed=False,
            status=SafetyStatus.DC_OFFSET,
            details=details,
        )
    
    # === Gate 5: Runaway (level growth) ===
    # Compare RMS of first half vs second half
    mid = len(mono) // 2
    first_half_rms = rms_db(mono[:mid])
    second_half_rms = rms_db(mono[mid:])
    level_growth = second_half_rms - first_half_rms
    details["level_growth_db"] = level_growth
    
    if level_growth > config.max_level_growth_db:
        return SafetyResult(
            passed=False,
            status=SafetyStatus.RUNAWAY,
            details=details,
        )
    
    # All gates passed
    return SafetyResult(
        passed=True,
        status=SafetyStatus.PASS,
        details=details,
    )


def check_safety_batch(
    audio_paths: list[Path],
    config: Optional[SAFETY_CONFIG.__class__] = None,
) -> list[SafetyResult]:
    """
    Run safety checks on multiple audio files.
    
    Args:
        audio_paths: List of paths to check
        config: Safety configuration
        
    Returns:
        List of SafetyResults in same order
    """
    return [check_safety(p, config) for p in audio_paths]
