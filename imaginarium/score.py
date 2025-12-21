"""
imaginarium/score.py
Fit scoring per IMAGINARIUM_SPEC v10 §11

Computes how well a candidate matches the target SoundSpec.
Phase 1: brightness + noisiness only.
"""

from typing import List

from .config import MIN_FIT_THRESHOLD
from .models import SoundSpec, CandidateFeatures, Candidate


def compute_fit(spec: SoundSpec, features: CandidateFeatures) -> float:
    """
    Compute fit score between target spec and candidate features.
    
    Phase 1 mapping:
    - brightness → centroid (spectral centroid)
    - noisiness → flatness (spectral flatness)
    
    Args:
        spec: Target SoundSpec from input
        features: Extracted features from rendered audio
        
    Returns:
        Fit score 0-1 (higher = better match)
    """
    # Phase 1: only brightness and noisiness
    brightness_fit = 1.0 - abs(spec.brightness - features.centroid)
    noisiness_fit = 1.0 - abs(spec.noisiness - features.flatness)
    
    # Weighted average
    weights = spec.weights
    total_weight = weights.get("brightness", 1.0) + weights.get("noisiness", 1.0)
    
    weighted_fit = (
        weights.get("brightness", 1.0) * brightness_fit +
        weights.get("noisiness", 1.0) * noisiness_fit
    ) / total_weight
    
    return float(weighted_fit)


def score_candidate(candidate: Candidate, spec: SoundSpec) -> float:
    """
    Score a single candidate against the spec.
    
    Updates candidate.fit_score in place and returns the score.
    
    Args:
        candidate: Candidate with features already extracted
        spec: Target SoundSpec
        
    Returns:
        Fit score (also stored in candidate.fit_score)
    """
    if candidate.features is None:
        raise ValueError(f"Candidate {candidate.candidate_id} has no features")
    
    score = compute_fit(spec, candidate.features)
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
