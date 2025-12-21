# imaginarium/spatial.py
"""
Spatial-aware pack generation for Imaginarium.

Integrates spatial image analysis (Phases A-D) with role-based selection (Phase E)
into the existing candidate generation pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import json

import numpy as np

from .image_spatial import analyze_image_spatial
from .selection import (
    SelectionCandidate,
    CandidateFeatures as SelectionFeatures,
    select_by_role,
    FloorConfig,
)

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Result Types
# -----------------------------------------------------------------------------

@dataclass
class SpatialPackResult:
    """Result of spatial pack generation."""
    success: bool
    pack_path: Optional[Path] = None
    
    # Spatial analysis
    used_spatial: bool = False
    fallback_reason: Optional[str] = None
    slot_allocation: Dict[str, int] = field(default_factory=dict)
    quality_score: float = 0.0
    
    # Selection
    selected_ids: List[str] = field(default_factory=list)
    selection_debug: Dict[str, Any] = field(default_factory=dict)
    
    # Errors
    error: Optional[str] = None


# -----------------------------------------------------------------------------
# Feature Mapping
# -----------------------------------------------------------------------------

def map_candidate_features(features: Any) -> SelectionFeatures:
    """
    Map existing CandidateFeatures to selection.CandidateFeatures.
    
    Existing fields:
        centroid, flatness, onset_density, crest, width, harmonicity
    
    Selection fields:
        crest, onset_density, noisiness, harmonicity, brightness
    """
    # Handle dict or dataclass
    if hasattr(features, '__dict__'):
        f = features.__dict__
    elif isinstance(features, dict):
        f = features
    else:
        # Fallback defaults
        return SelectionFeatures(
            crest=0.5,
            onset_density=0.5,
            noisiness=0.5,
            harmonicity=0.5,
            brightness=0.5,
        )
    
    return SelectionFeatures(
        crest=f.get("crest", 0.5),
        onset_density=f.get("onset_density", 0.5),
        noisiness=f.get("flatness", f.get("noisiness", 0.5)),  # flatness → noisiness
        harmonicity=f.get("harmonicity", 0.5),
        brightness=f.get("centroid", f.get("brightness", 0.5)),  # centroid → brightness
    )


def wrap_pipeline_candidate(candidate: Any) -> SelectionCandidate:
    """
    Wrap existing pipeline Candidate for role-based selection.
    
    Expects candidate with:
        - candidate_id: str
        - fit_score: float (or None)
        - features: CandidateFeatures (or dict)
        - tags: dict
    """
    return SelectionCandidate(
        candidate_id=getattr(candidate, "candidate_id", str(id(candidate))),
        global_score=getattr(candidate, "fit_score", 0.5) or 0.5,
        features=map_candidate_features(getattr(candidate, "features", {})),
        tags=getattr(candidate, "tags", {}) or {},
    )


# -----------------------------------------------------------------------------
# Core Integration
# -----------------------------------------------------------------------------

def analyze_for_spatial(
    image: np.ndarray,
    quality_threshold: float = 0.7,
) -> Tuple[bool, Dict[str, int], Dict[str, Any]]:
    """
    Run spatial analysis and determine if spatial selection should be used.
    
    Args:
        image: RGB image as numpy array
        quality_threshold: Minimum quality score to use spatial
    
    Returns:
        Tuple of (use_spatial, slot_allocation, full_analysis)
    """
    try:
        analysis = analyze_image_spatial(
            image,
            quality_threshold=quality_threshold,
        )
        
        use_spatial = not analysis["fallback"]
        slot_allocation = analysis["slot_allocation"] if use_spatial else {}
        
        return use_spatial, slot_allocation, analysis
        
    except Exception as e:
        log.warning("Spatial analysis failed: %s", e)
        return False, {}, {"error": str(e)}


def select_with_spatial(
    candidates: List[Any],
    slot_allocation: Dict[str, int],
    floor_config: Optional[FloorConfig] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Apply role-based selection to candidates.
    
    Args:
        candidates: List of pipeline Candidate objects (must have features)
        slot_allocation: Role → slot count mapping
        floor_config: Optional custom floor thresholds
    
    Returns:
        Tuple of (selected_candidates, debug_info)
    """
    # Filter to usable candidates
    usable = [c for c in candidates if getattr(c, "usable", True)]
    
    if not usable:
        log.warning("No usable candidates for spatial selection")
        return [], {"error": "no_usable_candidates"}
    
    # Wrap for selection
    wrapped = [wrap_pipeline_candidate(c) for c in usable]
    
    # Build ID → original candidate mapping
    id_to_candidate = {
        getattr(c, "candidate_id", str(id(c))): c 
        for c in usable
    }
    
    # Run selection
    selected_wrapped, debug = select_by_role(
        wrapped,
        slot_allocation,
        cfg=floor_config,
    )
    
    # Map back to original candidates
    selected = [
        id_to_candidate[w.candidate_id]
        for w in selected_wrapped
        if w.candidate_id in id_to_candidate
    ]
    
    return selected, debug


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

def generate_spatial_pack(
    image_path: Path,
    output_dir: Path,
    seed: int,
    *,
    use_spatial: bool = True,
    quality_threshold: float = 0.7,
    # Pass-through to existing pipeline
    generate_candidates_fn=None,
    render_fn=None,
    safety_fn=None,
    extract_features_fn=None,
    score_fn=None,
    select_diverse_fn=None,
    export_fn=None,
    global_spec_fn=None,
) -> SpatialPackResult:
    """
    Spatial-aware pack generation.
    
    If use_spatial=True and image has sufficient variance:
      1. Analyze 4x4 grid → role assignments
      2. Generate candidates (global pool)
      3. Select by role allocation (3 bed + 2 motion + 2 fg + 1 accent)
    
    Falls back to existing global pipeline if:
      - use_spatial=False
      - Image too uniform (quality gate fails)
      - Spatial analysis errors
    
    Args:
        image_path: Path to input image
        output_dir: Directory for pack output
        seed: Random seed for generation
        use_spatial: Enable spatial analysis
        quality_threshold: Minimum quality score for spatial
        *_fn: Callback functions from existing pipeline (for dependency injection)
    
    Returns:
        SpatialPackResult with success status and debug info
    """
    result = SpatialPackResult(success=False)
    
    try:
        # Load image
        image = _load_image(image_path)
        if image is None:
            result.error = f"Failed to load image: {image_path}"
            return result
        
        # Spatial analysis
        if use_spatial:
            use_spatial_selection, slot_allocation, spatial_analysis = analyze_for_spatial(
                image,
                quality_threshold=quality_threshold,
            )
            
            result.quality_score = spatial_analysis.get("quality_score", 0.0)
            
            if use_spatial_selection:
                result.used_spatial = True
                result.slot_allocation = slot_allocation
                log.info(
                    "Using spatial selection: %s (quality=%.2f)",
                    slot_allocation,
                    result.quality_score,
                )
            else:
                result.fallback_reason = spatial_analysis.get("quality", {}).get(
                    "checks", "quality_below_threshold"
                )
                log.info(
                    "Falling back to global selection (quality=%.2f)",
                    result.quality_score,
                )
        else:
            use_spatial_selection = False
            result.fallback_reason = "spatial_disabled"
        
        # Generate global SoundSpec (existing)
        if global_spec_fn:
            global_spec = global_spec_fn(image)
        else:
            log.warning("No global_spec_fn provided, using defaults")
            global_spec = None
        
        # Generate candidates (existing pipeline)
        if generate_candidates_fn:
            candidates = generate_candidates_fn(seed, global_spec)
        else:
            result.error = "No generate_candidates_fn provided"
            return result
        
        # Render, safety, features, score (existing pipeline)
        if render_fn:
            render_fn(candidates)
        if safety_fn:
            safety_fn(candidates)
        if extract_features_fn:
            extract_features_fn(candidates)
        if score_fn:
            score_fn(candidates, global_spec)
        
        # Selection
        if use_spatial_selection and result.slot_allocation:
            # Spatial selection
            selected, selection_debug = select_with_spatial(
                candidates,
                result.slot_allocation,
            )
            result.selection_debug = selection_debug
        else:
            # Fallback to existing diverse selection
            if select_diverse_fn:
                selected = select_diverse_fn(candidates, n_select=8)
            else:
                # Basic fallback: top 8 by score
                usable = [c for c in candidates if getattr(c, "usable", True)]
                usable.sort(key=lambda c: getattr(c, "fit_score", 0) or 0, reverse=True)
                selected = usable[:8]
        
        result.selected_ids = [
            getattr(c, "candidate_id", str(i)) 
            for i, c in enumerate(selected)
        ]
        
        # Export (existing pipeline)
        if export_fn and selected:
            pack_path = export_fn(selected, output_dir)
            result.pack_path = pack_path
        
        result.success = len(selected) == 8
        
        if not result.success:
            result.error = f"Only selected {len(selected)} candidates (need 8)"
        
        return result
        
    except Exception as e:
        log.exception("Pack generation failed")
        result.error = str(e)
        return result


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _load_image(path: Path) -> Optional[np.ndarray]:
    """Load image as RGB numpy array."""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
        return np.array(img)
    except ImportError:
        log.warning("PIL not available, trying raw load")
        try:
            import imageio
            return imageio.imread(path)
        except ImportError:
            log.error("No image loading library available")
            return None
    except Exception as e:
        log.error("Failed to load image %s: %s", path, e)
        return None


def save_spatial_debug(
    analysis: Dict[str, Any],
    selection_debug: Dict[str, Any],
    output_path: Path,
) -> None:
    """Save spatial analysis and selection debug to JSON."""
    debug = {
        "spatial_analysis": {
            k: v for k, v in analysis.items()
            if k not in ("grids",)  # Exclude large grids
        },
        "selection": selection_debug,
    }
    
    with open(output_path, "w") as f:
        json.dump(debug, f, indent=2, default=str)


# -----------------------------------------------------------------------------
# Standalone Testing
# -----------------------------------------------------------------------------

def preview_spatial_analysis(image_path: Path) -> Dict[str, Any]:
    """
    Preview spatial analysis pipeline on an image without full generation.
    
    Useful for validating role assignments before running expensive generation.
    """
    image = _load_image(image_path)
    if image is None:
        return {"error": f"Failed to load {image_path}"}
    
    use_spatial, slot_allocation, analysis = analyze_for_spatial(image)
    
    return {
        "use_spatial": use_spatial,
        "slot_allocation": slot_allocation,
        "quality_score": analysis.get("quality_score"),
        "quality_checks": analysis.get("quality", {}).get("checks"),
        "role_grid": analysis.get("role_grid"),
        "spec_tokens": analysis.get("spec_tokens"),
    }
