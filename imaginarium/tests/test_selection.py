# tests/test_selection.py
"""
Tests for Phase E: Role-based candidate selection.
"""
import pytest
from imaginarium.selection import (
    CandidateFeatures,
    SelectionCandidate,
    FloorConfig,
    passes_floor,
    role_affinity,
    compute_audio_affinity,
    matches_role_tags,
    select_by_role,
    wrap_candidate,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

def _mock_candidate(
    cid: str = "test",
    score: float = 0.5,
    crest: float = 0.5,
    onset: float = 0.5,
    noisiness: float = 0.5,
    harmonicity: float = 0.5,
    tags: dict = None,
) -> SelectionCandidate:
    """Create mock candidate with specified features."""
    return SelectionCandidate(
        candidate_id=cid,
        global_score=score,
        features=CandidateFeatures(
            crest=crest,
            onset_density=onset,
            noisiness=noisiness,
            harmonicity=harmonicity,
        ),
        tags=tags or {},
    )


def _make_candidate_pool(n: int = 20) -> list:
    """Create a pool of diverse candidates for selection tests."""
    candidates = []
    
    # Accent-like candidates (high crest/onset)
    for i in range(4):
        candidates.append(_mock_candidate(
            cid=f"accent_{i}",
            score=0.8 - i * 0.1,
            crest=0.7 + i * 0.05,
            onset=0.6 + i * 0.05,
            tags={"character": "plucked"} if i == 0 else {},
        ))
    
    # Motion-like candidates (mid onset)
    for i in range(4):
        candidates.append(_mock_candidate(
            cid=f"motion_{i}",
            score=0.75 - i * 0.1,
            onset=0.4 + i * 0.05,
            crest=0.3,
            tags={"movement": "sweeping"} if i == 0 else {},
        ))
    
    # Foreground-like candidates (harmonic, not noisy)
    for i in range(4):
        candidates.append(_mock_candidate(
            cid=f"foreground_{i}",
            score=0.7 - i * 0.1,
            harmonicity=0.7 + i * 0.05,
            noisiness=0.2 - i * 0.03,
            tags={"character": "vocal"} if i == 0 else {},
        ))
    
    # Bed-like candidates (calm, low onset)
    for i in range(8):
        candidates.append(_mock_candidate(
            cid=f"bed_{i}",
            score=0.6 - i * 0.05,
            onset=0.15 + i * 0.02,
            crest=0.2,
            noisiness=0.3,
            tags={"character": "gentle"} if i == 0 else {},
        ))
    
    return candidates


# -----------------------------------------------------------------------------
# Floor Tests
# -----------------------------------------------------------------------------

def test_accent_floor_requires_transient():
    """Accent floor requires high crest OR high onset."""
    cfg = FloorConfig()
    
    # High crest passes
    f = CandidateFeatures(crest=0.7, onset_density=0.2, noisiness=0.3, harmonicity=0.5)
    assert passes_floor("accent", f, cfg) == True
    
    # High onset passes
    f = CandidateFeatures(crest=0.3, onset_density=0.6, noisiness=0.3, harmonicity=0.5)
    assert passes_floor("accent", f, cfg) == True
    
    # Low both fails
    f = CandidateFeatures(crest=0.3, onset_density=0.2, noisiness=0.3, harmonicity=0.5)
    assert passes_floor("accent", f, cfg) == False


def test_motion_floor_requires_mid_onset():
    """Motion floor requires mid-range onset density."""
    cfg = FloorConfig()
    
    # Mid onset passes
    f = CandidateFeatures(crest=0.3, onset_density=0.5, noisiness=0.3, harmonicity=0.5)
    assert passes_floor("motion", f, cfg) == True
    
    # Too low fails
    f = CandidateFeatures(crest=0.3, onset_density=0.1, noisiness=0.3, harmonicity=0.5)
    assert passes_floor("motion", f, cfg) == False
    
    # Too high fails
    f = CandidateFeatures(crest=0.3, onset_density=0.95, noisiness=0.3, harmonicity=0.5)
    assert passes_floor("motion", f, cfg) == False


def test_foreground_floor_requires_harmonic_stable():
    """Foreground floor requires low noisiness AND high harmonicity."""
    cfg = FloorConfig()
    
    # Harmonic + clean passes
    f = CandidateFeatures(crest=0.3, onset_density=0.3, noisiness=0.2, harmonicity=0.7)
    assert passes_floor("foreground", f, cfg) == True
    
    # Too noisy fails
    f = CandidateFeatures(crest=0.3, onset_density=0.3, noisiness=0.7, harmonicity=0.7)
    assert passes_floor("foreground", f, cfg) == False
    
    # Not harmonic enough fails
    f = CandidateFeatures(crest=0.3, onset_density=0.3, noisiness=0.2, harmonicity=0.2)
    assert passes_floor("foreground", f, cfg) == False


def test_bed_floor_accepts_anything():
    """Bed floor accepts any candidate."""
    cfg = FloorConfig()
    
    f = CandidateFeatures(crest=0.9, onset_density=0.9, noisiness=0.9, harmonicity=0.1)
    assert passes_floor("bed", f, cfg) == True
    
    f = CandidateFeatures(crest=0.1, onset_density=0.1, noisiness=0.1, harmonicity=0.9)
    assert passes_floor("bed", f, cfg) == True


def test_floor_relaxation():
    """Relaxation makes floors easier to pass."""
    cfg = FloorConfig()
    
    # Fails strict floor
    f = CandidateFeatures(crest=0.4, onset_density=0.3, noisiness=0.3, harmonicity=0.5)
    assert passes_floor("accent", f, cfg, relax=1.0) == False
    
    # Passes relaxed floor
    assert passes_floor("accent", f, cfg, relax=0.7) == True


# -----------------------------------------------------------------------------
# Affinity Tests
# -----------------------------------------------------------------------------

def test_accent_affinity_prefers_transient():
    """Accent affinity prefers high crest/onset."""
    f_transient = CandidateFeatures(crest=0.8, onset_density=0.7, noisiness=0.3, harmonicity=0.5)
    f_calm = CandidateFeatures(crest=0.2, onset_density=0.2, noisiness=0.3, harmonicity=0.5)
    
    assert compute_audio_affinity("accent", f_transient) > compute_audio_affinity("accent", f_calm)


def test_foreground_affinity_prefers_harmonic():
    """Foreground affinity prefers harmonic, not noisy."""
    f_harmonic = CandidateFeatures(crest=0.3, onset_density=0.3, noisiness=0.1, harmonicity=0.9)
    f_noisy = CandidateFeatures(crest=0.3, onset_density=0.3, noisiness=0.8, harmonicity=0.3)
    
    assert compute_audio_affinity("foreground", f_harmonic) > compute_audio_affinity("foreground", f_noisy)


def test_tag_bonus_increases_affinity():
    """Matching tags add bonus to affinity."""
    f = CandidateFeatures(crest=0.5, onset_density=0.5, noisiness=0.3, harmonicity=0.5)
    
    no_tags = {}
    good_tags = {"character": "plucked"}
    
    affinity_no_tags = role_affinity("accent", f, no_tags)
    affinity_with_tags = role_affinity("accent", f, good_tags)
    
    assert affinity_with_tags > affinity_no_tags


def test_matches_role_tags():
    """Tag matching detects role-appropriate tags."""
    assert matches_role_tags("accent", {"character": "plucked"}) == True
    assert matches_role_tags("accent", {"exciter": "impulse"}) == True
    assert matches_role_tags("accent", {"character": "gentle"}) == False
    
    assert matches_role_tags("motion", {"movement": "sweeping"}) == True
    assert matches_role_tags("motion", {"topology": "hard_sync"}) == True
    
    assert matches_role_tags("foreground", {"character": "vocal"}) == True
    assert matches_role_tags("foreground", {"topology": "formant"}) == True
    
    assert matches_role_tags("bed", {"character": "gentle"}) == True
    assert matches_role_tags("bed", {"exciter": "continuous"}) == True


# -----------------------------------------------------------------------------
# Selection Tests
# -----------------------------------------------------------------------------

def test_select_fills_exactly_8():
    """Selection returns exactly 8 candidates."""
    candidates = _make_candidate_pool(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected, debug = select_by_role(candidates, slot_allocation)
    
    assert len(selected) == 8


def test_select_respects_slot_allocation():
    """Selection respects role slot counts."""
    candidates = _make_candidate_pool(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected, debug = select_by_role(candidates, slot_allocation)
    
    assert debug["fills"]["accent"]["picked"] == 1
    assert debug["fills"]["foreground"]["picked"] == 2
    assert debug["fills"]["motion"]["picked"] == 2
    assert debug["fills"]["bed"]["picked"] == 3


def test_select_is_deterministic():
    """Same input produces same output."""
    candidates = _make_candidate_pool(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected1, _ = select_by_role(candidates, slot_allocation)
    selected2, _ = select_by_role(candidates, slot_allocation)
    
    ids1 = [c.candidate_id for c in selected1]
    ids2 = [c.candidate_id for c in selected2]
    
    assert ids1 == ids2


def test_select_zero_slot_roles_excluded():
    """Roles with 0 slots don't get candidates."""
    candidates = _make_candidate_pool(20)
    slot_allocation = {"accent": 1, "foreground": 0, "motion": 0, "bed": 7}
    
    selected, debug = select_by_role(candidates, slot_allocation)
    
    assert debug["fills"]["foreground"]["picked"] == 0
    assert debug["fills"]["motion"]["picked"] == 0
    assert len(selected) == 8


def test_select_underfill_uses_global_score():
    """Underfilled role gets candidates by global score."""
    # Create pool with no accent-suitable candidates
    candidates = [
        _mock_candidate(
            cid=f"bed_{i}",
            score=0.8 - i * 0.05,
            crest=0.2,  # Low crest
            onset=0.15,  # Low onset
        )
        for i in range(20)
    ]
    
    slot_allocation = {"accent": 1, "foreground": 0, "motion": 0, "bed": 7}
    
    selected, debug = select_by_role(candidates, slot_allocation)
    
    # Should still fill 8, using global score for accent
    assert len(selected) == 8
    assert debug["fills"]["accent"]["picked"] == 1


def test_select_no_duplicate_candidates():
    """No candidate appears in multiple roles."""
    candidates = _make_candidate_pool(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    selected, debug = select_by_role(candidates, slot_allocation)
    
    ids = [c.candidate_id for c in selected]
    assert len(ids) == len(set(ids)), "Duplicate candidate selected"


def test_select_debug_contains_feature_stats():
    """Debug output includes feature statistics."""
    candidates = _make_candidate_pool(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    _, debug = select_by_role(candidates, slot_allocation)
    
    assert "feature_stats" in debug
    assert "crest" in debug["feature_stats"]
    assert "min" in debug["feature_stats"]["crest"]
    assert "mean" in debug["feature_stats"]["crest"]
    assert "max" in debug["feature_stats"]["crest"]


def test_select_debug_contains_bucket_attempts():
    """Debug output includes bucket relaxation attempts."""
    candidates = _make_candidate_pool(20)
    slot_allocation = {"accent": 1, "foreground": 2, "motion": 2, "bed": 3}
    
    _, debug = select_by_role(candidates, slot_allocation)
    
    assert "buckets" in debug
    for role in ["accent", "foreground", "motion", "bed"]:
        if slot_allocation.get(role, 0) > 0:
            assert role in debug["buckets"]
            assert len(debug["buckets"][role]) > 0
            assert "bucket_size" in debug["buckets"][role][0]


def test_wrap_candidate():
    """wrap_candidate creates valid SelectionCandidate."""
    c = wrap_candidate(
        candidate_id="test_1",
        global_score=0.75,
        features={"crest": 0.6, "onset_density": 0.4},
        tags={"character": "bright"},
    )
    
    assert c.candidate_id == "test_1"
    assert c.global_score == 0.75
    assert c.features.crest == 0.6
    assert c.features.onset_density == 0.4
    assert c.features.noisiness == 0.5  # default
    assert c.tags == {"character": "bright"}
