"""
imaginarium/score.py
Fit scoring per IMAGINARIUM_SPEC v10 §11

Computes how well a candidate matches the target SoundSpec.
Phase 2a: Uses expanded features + method affinity biasing.
"""

from typing import List

from .config import MIN_FIT_THRESHOLD
from .models import SoundSpec, CandidateFeatures, Candidate


def compute_fit(spec: SoundSpec, features: CandidateFeatures) -> float:
    """
    Compute fit score between target spec and candidate features.
    
    Phase 2a mapping:
    - brightness → centroid (spectral centroid)
    - noisiness → flatness (spectral flatness)
    - warmth → harmonicity (harmonic = warm)
    - contrast → crest (dynamic range)
    - density → onset_density (busy = dense)
    
    Args:
        spec: Target SoundSpec from input
        features: Extracted features from rendered audio
        
    Returns:
        Fit score 0-1 (higher = better match)
    """
    weights = spec.weights
    
    # Phase 1 core features (always used)
    brightness_fit = 1.0 - abs(spec.brightness - features.centroid)
    noisiness_fit = 1.0 - abs(spec.noisiness - features.flatness)
    
    # Phase 2a features
    warmth_fit = 1.0 - abs(spec.warmth - features.harmonicity)
    contrast_fit = 1.0 - abs(spec.contrast - features.crest)
    density_fit = 1.0 - abs(spec.density - features.onset_density)
    
    # Weighted average
    total_weight = (
        weights.get("brightness", 1.0) +
        weights.get("noisiness", 1.0) +
        weights.get("warmth", 0.7) +
        weights.get("contrast", 0.7) +
        weights.get("density", 0.7)
    )
    
    weighted_fit = (
        weights.get("brightness", 1.0) * brightness_fit +
        weights.get("noisiness", 1.0) * noisiness_fit +
        weights.get("warmth", 0.7) * warmth_fit +
        weights.get("contrast", 0.7) * contrast_fit +
        weights.get("density", 0.7) * density_fit
    ) / total_weight
    
    return float(weighted_fit)


def score_candidate(candidate: Candidate, spec: SoundSpec) -> float:
    """
    Score a single candidate against the spec.
    
    Applies method affinity as a multiplier on the base fit score.
    Updates candidate.fit_score in place and returns the score.
    
    Args:
        candidate: Candidate with features already extracted
        spec: Target SoundSpec
        
    Returns:
        Fit score (also stored in candidate.fit_score)
    """
    if candidate.features is None:
        raise ValueError(f"Candidate {candidate.candidate_id} has no features")
    
    # Base fit from feature matching
    base_score = compute_fit(spec, candidate.features)
    
    # Apply method affinity as multiplier
    affinity = spec.method_affinity.get(candidate.method_id, 1.0)
    
    # Affinity is 0.5-1.5, center on 1.0
    # Score is multiplied, then re-normalized to 0-1 range
    # Affinity 1.5 at base 0.8 → 0.8 * 1.25 = 1.0 (clamped)
    # Affinity 0.5 at base 0.8 → 0.8 * 0.75 = 0.6
    affinity_boost = 0.5 + (affinity / 2)  # Maps 0.5-1.5 → 0.75-1.25
    
    score = min(1.0, base_score * affinity_boost)
    candidate.fit_score = score
    return score


def score_candidates(
    candidates: List[Candidate],
    spec: SoundSpec,
) -> List[float]:
    """
    Score multiple candidates against the spec.
    
    Updates each candidate.fit_score in place.
    
    Args:
        candidates: List of candidates with features
        spec: Target SoundSpec
        
    Returns:
        List of fit scores in same order
    """
    scores = []
    for c in candidates:
        if c.features is not None:
            score = score_candidate(c, spec)
        else:
            score = 0.0
            c.fit_score = score
        scores.append(score)
    return scores


def filter_by_fit(
    candidates: List[Candidate],
    threshold: float = MIN_FIT_THRESHOLD,
) -> List[Candidate]:
    """
    Filter candidates by minimum fit threshold.
    
    Args:
        candidates: Scored candidates
        threshold: Minimum fit score (default from config)
        
    Returns:
        List of candidates meeting threshold
    """
    return [c for c in candidates if c.fit_score is not None and c.fit_score >= threshold]
