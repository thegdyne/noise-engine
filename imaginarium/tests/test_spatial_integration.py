# tests/test_spatial_integration.py
"""
Tests for spatial pack generation integration.
"""
import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import numpy as np

from imaginarium.spatial import (
    analyze_for_spatial,
    select_with_spatial,
    map_candidate_features,
    wrap_pipeline_candidate,
    generate_spatial_pack,
    preview_spatial_analysis,
    SpatialPackResult,
)
from imaginarium.selection import CandidateFeatures as SelectionFeatures


# -----------------------------------------------------------------------------
# Mock Pipeline Types
# -----------------------------------------------------------------------------

@dataclass
class MockCandidateFeatures:
    """Mock of existing pipeline CandidateFeatures."""
    centroid: float = 0.5
    flatness: float = 0.5
    onset_density: float = 0.5
    crest: float = 0.5
    width: float = 0.5
    harmonicity: float = 0.5


@dataclass
class MockCandidate:
    """Mock of existing pipeline Candidate."""
    candidate_id: str
    fit_score: float
    features: MockCandidateFeatures
    tags: Dict[str, Any]
    usable: bool = True


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------

def _img_uniform_gray() -> np.ndarray:
    return np.full((256, 256, 3), 128, dtype=np.uint8)


def _img_structured() -> np.ndarray:
    """Image with clear structure (stripes + blob)."""
    img = np.full((256, 256, 3), 100, dtype=np.uint8)
    # Vertical stripes in top-right
    for x in range(150, 220):
        if (x // 8) % 2 == 0:
            img[20:100, x, :] = 240
    # Bright blob
    img[180:220, 50:100, :] = 255
    return img


def _mock_candidates(n: int = 20) -> List[MockCandidate]:
    """Create mock candidates with varied characteristics."""
    candidates = []
    
    # Accent-like (high crest)
    for i in range(4):
        candidates.append(MockCandidate(
            candidate_id=f"accent_{i}",
            fit_score=0.8 - i * 0.1,
            features=MockCandidateFeatures(crest=0.7, onset_density=0.6),
            tags={"character": "plucked"},
        ))
    
    # Motion-like (mid onset)
    for i in range(4):
        candidates.append(MockCandidate(
            candidate_id=f"motion_{i}",
            fit_score=0.75 - i * 0.1,
            features=MockCandidateFeatures(onset_density=0.45, crest=0.3),
            tags={"movement": "sweeping"},
        ))
    
    # Foreground-like (harmonic)
    for i in range(4):
        candidates.append(MockCandidate(
            candidate_id=f"fg_{i}",
            fit_score=0.7 - i * 0.1,
            features=MockCandidateFeatures(harmonicity=0.8, flatness=0.2),
            tags={"character": "vocal"},
        ))
    
    # Bed-like (calm)
    for i in range(8):
        candidates.append(MockCandidate(
            candidate_id=f"bed_{i}",
            fit_score=0.6 - i * 0.05,
            features=MockCandidateFeatures(onset_density=0.15, crest=0.2),
            tags={"character": "gentle"},
        ))
    
    return candidates


# -----------------------------------------------------------------------------
# Feature Mapping Tests
# -----------------------------------------------------------------------------

def test_map_candidate_features_from_dataclass():
    """Map features from dataclass."""
    features = MockCandidateFeatures(
        centroid=0.7,
        flatness=0.3,
        onset_density=0.5,
        crest=0.6,
        harmonicity=0.8,
    )
    
    mapped = map_candidate_features(features)
    
    assert isinstance(mapped, SelectionFeatures)
    assert mapped.brightness == 0.7  # centroid → brightness
    assert mapped.noisiness == 0.3   # flatness → noisiness
    assert mapped.onset_density == 0.5
    assert mapped.crest == 0.6
    assert mapped.harmonicity == 0.8


def test_map_candidate_features_from_dict():
    """Map features from dict."""
    features = {
        "centroid": 0.6,
        "flatness": 0.4,
        "onset_density": 0.3,
        "crest": 0.5,
        "harmonicity": 0.7,
    }
    
    mapped = map_candidate_features(features)
    
    assert mapped.brightness == 0.6
    assert mapped.noisiness == 0.4


def test_map_candidate_features_defaults():
    """Missing features use defaults."""
    mapped = map_candidate_features({})
    
    assert mapped.crest == 0.5
    assert mapped.onset_density == 0.5
    assert mapped.noisiness == 0.5
    assert mapped.harmonicity == 0.5
    assert mapped.brightness == 0.5


def test_wrap_pipeline_candidate():
    """Wrap existing pipeline candidate."""
    candidate = MockCandidate(
        candidate_id="test_1",
        fit_score=0.75,
        features=MockCandidateFeatures(crest=0.6),
        tags={"character": "bright"},
    )
    
    wrapped = wrap_pipeline_candidate(candidate)
    
    assert wrapped.candidate_id == "test_1"
    assert wrapped.global_score == 0.75
    assert wrapped.features.crest == 0.6
    assert wrapped.tags == {"character": "bright"}


# -----------------------------------------------------------------------------
# Spatial Analysis Tests
# -----------------------------------------------------------------------------

def test_analyze_for_spatial_uniform_returns_fallback():
    """Uniform image should trigger fallback."""
    img = _img_uniform_gray()
    
    use_spatial, slot_allocation, analysis = analyze_for_spatial(img)
    
    assert use_spatial == False
    assert slot_allocation == {}
    assert analysis.get("fallback") == True


def test_analyze_for_spatial_structured_returns_allocation():
    """Structured image should return slot allocation."""
    img = _img_structured()
    
    use_spatial, slot_allocation, analysis = analyze_for_spatial(img)
    
    assert use_spatial == True
    assert sum(slot_allocation.values()) == 8
    assert "accent" in slot_allocation
    assert slot_allocation["accent"] == 1


def test_analyze_for_spatial_handles_errors():
    """Analysis errors should return fallback gracefully."""
    # Invalid image
    img = np.array([1, 2, 3])  # Not a valid image
    
    use_spatial, slot_allocation, analysis = analyze_for_spatial(img)
    
    assert use_spatial == False
    assert "error" in analysis


# -----------------------------------------------------------------------------
# Selection Integration Tests
# -----------------------------------------------------------------------------

def test_select_with_spatial_fills_allocation():
    """Selection should fill slot allocation."""
    candidates = _mock_candidates(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected, debug = select_with_spatial(candidates, slot_allocation)
    
    assert len(selected) == 8
    assert all(isinstance(c, MockCandidate) for c in selected)


def test_select_with_spatial_returns_original_candidates():
    """Selection should return original candidate objects, not wrapped."""
    candidates = _mock_candidates(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected, _ = select_with_spatial(candidates, slot_allocation)
    
    # Should be original MockCandidate instances
    for c in selected:
        assert hasattr(c, "features")
        assert isinstance(c.features, MockCandidateFeatures)


def test_select_with_spatial_no_duplicates():
    """Selection should not duplicate candidates."""
    candidates = _mock_candidates(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected, _ = select_with_spatial(candidates, slot_allocation)
    
    ids = [c.candidate_id for c in selected]
    assert len(ids) == len(set(ids))


def test_select_with_spatial_filters_unusable():
    """Selection should skip unusable candidates."""
    candidates = _mock_candidates(20)
    # Mark some as unusable
    for c in candidates[:5]:
        c.usable = False
    
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected, _ = select_with_spatial(candidates, slot_allocation)
    
    # All selected should be usable
    assert all(c.usable for c in selected)


def test_select_with_spatial_debug_info():
    """Selection should return debug info."""
    candidates = _mock_candidates(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    _, debug = select_with_spatial(candidates, slot_allocation)
    
    assert "fills" in debug
    assert "buckets" in debug
    assert "selected_ids" in debug


# -----------------------------------------------------------------------------
# End-to-End Tests
# -----------------------------------------------------------------------------

def test_generate_spatial_pack_missing_functions():
    """Should handle missing pipeline functions gracefully."""
    result = generate_spatial_pack(
        image_path=Path("/nonexistent.png"),
        output_dir=Path("/tmp"),
        seed=42,
    )
    
    assert result.success == False
    assert result.error is not None


def test_generate_spatial_pack_with_mocks():
    """Full pipeline with mock functions."""
    # Create temp image
    import tempfile
    from PIL import Image
    
    img = _img_structured()
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        Image.fromarray(img).save(f.name)
        image_path = Path(f.name)
    
    try:
        candidates = _mock_candidates(20)
        
        result = generate_spatial_pack(
            image_path=image_path,
            output_dir=Path("/tmp"),
            seed=42,
            use_spatial=True,
            generate_candidates_fn=lambda seed, spec: candidates,
            # Skip render/safety/features for test
            score_fn=lambda c, s: None,
            # No export, just test selection
        )
        
        assert result.used_spatial == True
        assert len(result.selected_ids) == 8
        assert sum(result.slot_allocation.values()) == 8
        
    finally:
        image_path.unlink()


def test_generate_spatial_pack_fallback():
    """Fallback to global selection when spatial disabled."""
    import tempfile
    from PIL import Image
    
    img = _img_uniform_gray()
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        Image.fromarray(img).save(f.name)
        image_path = Path(f.name)
    
    try:
        candidates = _mock_candidates(20)
        # Give them scores for fallback selection
        for i, c in enumerate(candidates):
            c.fit_score = 0.9 - i * 0.02
        
        result = generate_spatial_pack(
            image_path=image_path,
            output_dir=Path("/tmp"),
            seed=42,
            use_spatial=True,  # Will fallback due to uniform image
            generate_candidates_fn=lambda seed, spec: candidates,
            score_fn=lambda c, s: None,
        )
        
        assert result.used_spatial == False
        assert result.fallback_reason is not None
        assert len(result.selected_ids) == 8
        
    finally:
        image_path.unlink()


def test_preview_spatial_analysis():
    """Test the standalone pipeline preview function."""
    import tempfile
    from PIL import Image
    
    img = _img_structured()
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        Image.fromarray(img).save(f.name)
        image_path = Path(f.name)
    
    try:
        result = preview_spatial_analysis(image_path)
        
        assert "use_spatial" in result
        assert "slot_allocation" in result
        assert "quality_score" in result
        assert "role_grid" in result
        
    finally:
        image_path.unlink()
