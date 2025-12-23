"""
Imaginarium - Sound palette generator for Noise Engine

A deterministic system that converts input stimuli (images, text, audio)
into diverse synthesizer packs with 8 generators.

Usage:
    python -m imaginarium generate --image input.png --name my_pack
    python -m imaginarium list-methods
    python -m imaginarium preview --method subtractive/bright_saw
"""

__version__ = "0.1.0"
__spec_version__ = "0.3.0"

from .models import SoundSpec, Candidate, CandidateFeatures, SafetyResult
from .seeds import GenerationContext, stable_u32, input_fingerprint
from .extract import extract_from_image, ExtractionResult
from .generate import generate_candidates, CandidateGenerator, GenerationPool
from .render import render_candidates, NRTRenderer, RenderResult, BatchRenderResult
from .safety import check_safety, check_safety_batch
from .analyze import extract_features, extract_features_batch
from .score import compute_fit, score_candidates, filter_by_fit
from .select import select_diverse, candidate_distance
from .export import export_pack
from .config import (
    FAMILIES,
    PHASE1_CONSTRAINTS,
    SAFETY_CONFIG,
    RENDER_CONFIG,
)

__all__ = [
    # Version
    "__version__",
    "__spec_version__",
    # Models
    "SoundSpec",
    "Candidate", 
    "CandidateFeatures",
    "SafetyResult",
    # Seeds
    "GenerationContext",
    "stable_u32",
    "input_fingerprint",
    # Extraction
    "extract_from_image",
    "ExtractionResult",
    # Generation
    "generate_candidates",
    "CandidateGenerator",
    "GenerationPool",
    # Rendering
    "render_candidates",
    "NRTRenderer",
    "RenderResult",
    "BatchRenderResult",
    # Config
    "FAMILIES",
    "PHASE1_CONSTRAINTS",
    "SAFETY_CONFIG",
    "RENDER_CONFIG",
]
