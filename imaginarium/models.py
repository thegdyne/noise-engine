"""
imaginarium/models.py
Core data models for Imaginarium

All structures from IMAGINARIUM_SPEC v10 §4
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import numpy as np

from .config import FAMILIES, SPEC_VERSION


# =============================================================================
# SoundSpec (§4.1)
# =============================================================================

@dataclass
class SoundSpec:
    """
    Target sound characteristics extracted from input stimulus.
    
    Phase 1: brightness, noisiness
    Phase 2a: warmth, saturation, contrast, density, movement
    """
    version: str = SPEC_VERSION
    fields_used: List[str] = field(default_factory=lambda: [
        "brightness", "noisiness", "warmth", "saturation", "contrast", "density"
    ])
    
    # Phase 1 fields (0-1 normalized)
    brightness: float = 0.5
    noisiness: float = 0.5
    
    # Phase 2a fields (0-1 normalized)
    warmth: float = 0.5       # Color temperature: 0=cool/blue, 1=warm/red
    saturation: float = 0.5   # Color saturation: 0=gray, 1=vivid
    contrast: float = 0.5     # Luminance contrast: 0=flat, 1=high
    density: float = 0.5      # Visual density: 0=sparse, 1=dense
    
    # Weights for scoring (default equal)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "brightness": 1.0,
        "noisiness": 1.0,
        "warmth": 0.7,
        "saturation": 0.7,
        "contrast": 0.7,
        "density": 0.7,
    })
    
    # Method biasing derived from features
    method_affinity: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "fields_used": self.fields_used,
            "brightness": self.brightness,
            "noisiness": self.noisiness,
            "warmth": self.warmth,
            "saturation": self.saturation,
            "contrast": self.contrast,
            "density": self.density,
            "weights": self.weights,
            "method_affinity": self.method_affinity,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "SoundSpec":
        return cls(
            version=d.get("version", SPEC_VERSION),
            fields_used=d.get("fields_used", ["brightness", "noisiness"]),
            brightness=d.get("brightness", 0.5),
            noisiness=d.get("noisiness", 0.5),
            warmth=d.get("warmth", 0.5),
            saturation=d.get("saturation", 0.5),
            contrast=d.get("contrast", 0.5),
            density=d.get("density", 0.5),
            weights=d.get("weights", {"brightness": 1.0, "noisiness": 1.0}),
            method_affinity=d.get("method_affinity", {}),
        )


# =============================================================================
# CandidateFeatures (§4.2)
# =============================================================================

@dataclass
class CandidateFeatures:
    """
    Acoustic features extracted from rendered candidate audio.
    
    All values normalized to 0-1 per NORMALIZATION_V1.
    """
    centroid: float = 0.0      # Spectral centroid (log 100-12000 Hz)
    flatness: float = 0.0      # Spectral flatness (0-1)
    onset_density: float = 0.0  # Onsets per second (0-20)
    crest: float = 0.0         # Peak/RMS ratio (0-24 dB)
    width: float = 0.0         # Stereo correlation (0-1)
    harmonicity: float = 0.0   # Harmonic ratio (0-1)
    rms_db: float = -20.0  # RMS loudness in dBFS (for trim calculation)
    
    def to_array(self) -> np.ndarray:
        """Return as numpy array for distance calculations."""
        return np.array([
            self.centroid,
            self.flatness,
            self.onset_density,
            self.crest,
            self.harmonicity,
            self.width,
        ], dtype=np.float32)


# =============================================================================
# SafetyResult
# =============================================================================

class SafetyStatus(Enum):
    PASS = "pass"
    SILENCE = "silence"
    SPARSE = "sparse"
    CLIPPING = "clipping"
    DC_OFFSET = "dc_offset"
    RUNAWAY = "runaway"


@dataclass
class SafetyResult:
    """Result of safety gate checks."""
    passed: bool
    status: SafetyStatus
    details: Dict[str, float] = field(default_factory=dict)
    
    @property
    def fail_reason(self) -> Optional[str]:
        return None if self.passed else self.status.value


# =============================================================================
# Candidate (§4.3)
# =============================================================================

@dataclass
class Candidate:
    """
    A synthesis candidate with its metadata, features, and scores.
    """
    # Identity
    candidate_id: str          # "{method_id}:{macro}:{param_index}:{template_version}"
    seed: int                  # Derived from candidate_id
    method_id: str             # e.g., "subtractive/bright_saw"
    family: str                # e.g., "subtractive"
    
    # Parameters (method-specific)
    params: Dict[str, float] = field(default_factory=dict)
    
    # Tags for Jaccard distance
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Render output
    audio_path: Optional[Path] = None
    
    # Analysis results (populated after render)
    features: Optional[CandidateFeatures] = None
    safety: Optional[SafetyResult] = None
    
    # Scoring (populated after analysis)
    fit_score: Optional[float] = None
    
    # Selection state
    selected: bool = False
    archive_blocked: bool = False
    
    @property
    def usable(self) -> bool:
        """Is this candidate eligible for selection? (§15.1)"""
        if self.safety is None or not self.safety.passed:
            return False
        if self.fit_score is None or self.fit_score < 0.6:  # MIN_FIT_THRESHOLD
            return False
        if self.archive_blocked:
            return False
        return True
    
    def compute_signature(self) -> np.ndarray:
        """
        Compute signature vector for distance calculations (§4.3).
        
        Returns:
            9-dimensional vector: 6 continuous features + 3 family one-hot
        """
        if self.features is None:
            raise ValueError("Cannot compute signature without features")
        
        continuous = self.features.to_array()  # 6 values
        
        # Family one-hot with dampening (0.1 instead of 1.0)
        family_onehot = np.array([
            0.1 if f == self.family else 0.0 
            for f in FAMILIES
        ], dtype=np.float32)
        
        return np.concatenate([continuous, family_onehot])
    
    @property
    def tag_set(self) -> Set[str]:
        """Tags as set of 'k=v' strings for Jaccard distance."""
        return {f"{k}={v}" for k, v in self.tags.items()}


# =============================================================================
# Selection Result
# =============================================================================

@dataclass
class SelectionResult:
    """Result of diversity selection."""
    selected: List[Candidate]
    pairwise_distances: Dict[str, float]  # min, mean, max
    family_counts: Dict[str, int]
    relaxations_applied: List[int]  # Ladder levels used
    deadlock: Optional["SelectionDeadlock"] = None


@dataclass
class SelectionDeadlock:
    """Diagnostic info when selection fails constraints (§12.5)."""
    pool_size: int
    family_counts: Dict[str, int]
    constraint_failures: List[str]
    nearest_neighbor_distances: List[float]
    relaxation_level: int
    fallback_used: bool


# =============================================================================
# Archive Entry (§13)
# =============================================================================

@dataclass
class ArchiveEntry:
    """Previously selected candidate for archive distance checking."""
    candidate_id: str
    signature: np.ndarray
    tags: Dict[str, str]
    run_seed: int
    input_fingerprint: str
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "signature": self.signature.tolist(),
            "tags": self.tags,
            "run_seed": self.run_seed,
            "input_fingerprint": self.input_fingerprint,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "ArchiveEntry":
        return cls(
            candidate_id=d["candidate_id"],
            signature=np.array(d["signature"], dtype=np.float32),
            tags=d["tags"],
            run_seed=d["run_seed"],
            input_fingerprint=d["input_fingerprint"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
        )


# =============================================================================
# Generation Report (§16.2)
# =============================================================================

@dataclass
class GenerationReport:
    """Full report of a generation run."""
    version: str
    input_fingerprint: str
    run_seed: int
    sobol_seed: int
    spec: SoundSpec
    candidates: List[Dict]  # Simplified candidate records
    selection: Optional[SelectionResult] = None
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "input_fingerprint": self.input_fingerprint,
            "run_seed": self.run_seed,
            "sobol_seed": self.sobol_seed,
            "spec": self.spec.to_dict(),
            "candidates": self.candidates,
            "selection": {
                "selected": [c.candidate_id for c in self.selection.selected],
                "pairwise_distances": self.selection.pairwise_distances,
                "family_counts": self.selection.family_counts,
                "relaxations_applied": self.selection.relaxations_applied,
            } if self.selection else None,
        }
