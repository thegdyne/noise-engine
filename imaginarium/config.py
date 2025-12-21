"""
imaginarium/config.py
Configuration constants for Imaginarium Phase 1

All values from IMAGINARIUM_SPEC v10
"""

from dataclasses import dataclass, field
from typing import Dict, List

# =============================================================================
# Version
# =============================================================================

SPEC_VERSION = "0.3.0"
PHASE = 1

# =============================================================================
# Families (§5)
# =============================================================================

# IMPORTANT: Order is stable - append only for future phases
# Signature vectors depend on this ordering
FAMILIES: List[str] = ["subtractive", "fm", "physical"]

METHOD_PRIORS: Dict[str, float] = {
    "subtractive": 0.35,
    "fm": 0.35,
    "physical": 0.30,
}

# =============================================================================
# Selection Constraints (§12.3)
# =============================================================================

@dataclass
class SelectionConstraints:
    """Phase 1 selection constraints."""
    n_select: int = 8
    min_family_count: int = 3
    max_per_family: int = 3
    min_pair_distance: float = 0.15
    min_archive_distance: float = 0.20


PHASE1_CONSTRAINTS = SelectionConstraints()

# =============================================================================
# Relaxation Ladder (§12.4)
# =============================================================================

# Each step progressively relaxes constraints
# Level 0 is baseline (same as PHASE1_CONSTRAINTS)
RELAXATION_LADDER = [
    {"min_pair_distance": 0.15},   # level 0: baseline
    {"min_pair_distance": 0.12},   # level 1
    {"min_pair_distance": 0.10},   # level 2
    {"max_per_family": 4},         # level 3: +1
    {"min_family_count": 2},       # level 4: -1
    {"n_select": 6},               # level 5
    {"n_select": 4},               # level 6
]

MAX_LADDER_STEPS = len(RELAXATION_LADDER)

# =============================================================================
# Safety Gates (§9)
# =============================================================================

@dataclass
class SafetyGateConfig:
    """Audio safety thresholds."""
    sample_rate: int = 48000
    frame_length: int = 2048
    hop_length: int = 1024
    
    # Audibility
    min_rms_db: float = -40.0
    active_threshold_db: float = -45.0
    min_active_frames_pct: float = 0.30
    
    # Clipping / DC
    max_sample_value: float = 0.999
    max_dc_offset: float = 0.01
    
    # Runaway detection
    max_level_growth_db: float = 6.0


SAFETY_CONFIG = SafetyGateConfig()

# =============================================================================
# Scoring (§11)
# =============================================================================

MIN_FIT_THRESHOLD = 0.6

# Distance metric weights (§12.1)
W_FEAT = 0.8
W_TAG = 0.2

# =============================================================================
# Feature Normalization (§10)
# =============================================================================

NORMALIZATION_V1 = {
    "centroid": {"range": [100, 12000], "curve": "log"},
    "flatness": {"range": [0, 1], "curve": "linear"},
    "onset_density": {"range": [0, 20], "curve": "linear"},
    "crest": {"range": [0, 24], "curve": "linear"},
    "width": {"range": [0, 1], "curve": "linear"},
    "harmonicity": {"range": [0, 1], "curve": "linear"},
}

# =============================================================================
# Candidate Pool (§15)
# =============================================================================

@dataclass
class PoolConfig:
    """Candidate generation pool settings."""
    batch_size: int = 32
    max_batches: int = 15  # Hard ceiling: 480 candidates
    min_p_usable: float = 0.05  # Floor to prevent unbounded pools


POOL_CONFIG = PoolConfig()

# =============================================================================
# Render Settings
# =============================================================================

@dataclass  
class RenderConfig:
    """NRT preview render settings."""
    duration_sec: float = 3.0
    sample_rate: int = 48000
    channels: int = 2
    format: str = "WAV"
    sample_format: str = "int16"


RENDER_CONFIG = RenderConfig()

# =============================================================================
# Paths
# =============================================================================

@dataclass
class PathConfig:
    """Default paths relative to Noise Engine repo."""
    packs_dir: str = "packs"
    templates_dir: str = "imaginarium/templates"
    archive_file: str = "imaginarium/archive.json"
    calibration_file: str = "imaginarium/calibration.json"


PATHS = PathConfig()
