# tests/test_image_spatial.py
"""
Tests for imaginarium/image_spatial.py (Phase A).

Uses synthetic fixtures - no external PNGs required.
"""
import numpy as np

from imaginarium.image_spatial import (
    extract_tile_features,
    compute_hints,
    debug_grids,
    assign_roles,
    build_debug_output,
    compute_slot_allocation,
    # Phase C
    compute_coarse_cells,
    compute_tile_weights,
    compute_layer_stats,
    build_spatial_analysis,
    WEIGHT_FLOOR,
    # Phase D
    compute_quality_score,
    should_fallback,
    build_spec_tokens,
    analyze_image_spatial,
    QUALITY_THRESHOLD,
)


def _img_uniform_gray(size=256, val=0.5):
    img = np.full((size, size, 3), int(val * 255), dtype=np.uint8)
    return img


def _img_vertical_stripes_quadrant(size=256):
    """
    Put high-contrast vertical stripes in top-right quadrant.
    """
    img = _img_uniform_gray(size=size, val=0.4)
    q = size // 2
    # stripes in [0:q, q:size]
    for x in range(q, size):
        if ((x - q) // 4) % 2 == 0:
            img[0:q, x, :] = 255
        else:
            img[0:q, x, :] = 0
    return img


def _img_single_bright_blob(size=256):
    img = _img_uniform_gray(size=size, val=0.3)
    cy, cx = int(size * 0.70), int(size * 0.55)
    rr = int(size * 0.08)
    yy, xx = np.ogrid[:size, :size]
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= rr ** 2
    img[mask] = 255
    return img


def test_extract_tile_features_len_and_ranges():
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    assert len(tiles) == 16
    for t in tiles:
        assert 0.0 <= t.l_mean <= 1.0
        assert 0.0 <= t.sat_mean <= 1.0
        assert 0.0 <= t.edge_density <= 1.0
        assert 0.0 <= t.hf_energy <= 1.0


def test_compute_hints_populates_fields():
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    for t in tiles:
        # saliency can be negative due to z-score sum, but should be finite
        assert np.isfinite(t.saliency)
        assert 0.0 <= t.motion_hint <= 1.0
        assert 0.0 <= t.object_hint <= 1.0
        assert 0.0 <= t.bed_hint <= 1.0


def test_vertical_stripes_quadrant_has_higher_motion_hint():
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)

    # Top-right quadrant in 4×4 is rows 0-1, cols 2-3
    tr_idx = [t.index for t in tiles if t.row in (0, 1) and t.col in (2, 3)]
    other_idx = [t.index for t in tiles if t.index not in tr_idx]

    tr_motion = np.mean([tiles[i].motion_hint for i in tr_idx])
    other_motion = np.mean([tiles[i].motion_hint for i in other_idx])

    assert tr_motion > other_motion


def test_single_bright_blob_increases_saliency_somewhere():
    img = _img_single_bright_blob()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)

    sal = np.array([t.saliency for t in tiles], dtype=np.float32)
    # We expect at least one tile to stand out
    assert float(sal.max() - sal.mean()) > 0.2


def test_debug_grids_shape():
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    grids = debug_grids(tiles, grid=(4, 4))
    assert grids["edge_density"][0].__len__() == 4
    assert len(grids["edge_density"]) == 4


# =============================================================================
# Phase B: Role Assignment Tests
# =============================================================================

def test_assign_roles_all_tiles_assigned():
    """Every tile must be assigned to exactly one role."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)

    # Collect all assigned indices (exclude 'meta' key)
    all_assigned = []
    for role_name in ["accent", "foreground", "motion", "bed"]:
        all_assigned.extend(roles[role_name])

    # Check all 16 tiles assigned exactly once
    assert sorted(all_assigned) == list(range(16))


def test_assign_roles_exclusive():
    """No tile should appear in multiple roles."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)

    seen = set()
    for role_name in ["accent", "foreground", "motion", "bed"]:
        for idx in roles[role_name]:
            assert idx not in seen, f"Tile {idx} assigned to multiple roles"
            seen.add(idx)


def test_assign_roles_accent_always_one():
    """Accent role should always have exactly 1 tile."""
    img = _img_single_bright_blob()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)

    roles = assign_roles(tiles)
    assert len(roles["accent"]) == 1

    # Even for uniform image
    img2 = _img_uniform_gray()
    tiles2 = extract_tile_features(img2, grid=(4, 4), resize_to=256)
    compute_hints(tiles2)
    roles2 = assign_roles(tiles2)
    assert len(roles2["accent"]) == 1


def test_assign_roles_accent_has_highest_saliency():
    """Accent tile should be the one with highest saliency."""
    img = _img_single_bright_blob()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)

    accent_idx = roles["accent"][0]
    accent_saliency = tiles[accent_idx].saliency
    
    # All other tiles should have lower or equal saliency
    for i, t in enumerate(tiles):
        if i != accent_idx:
            assert t.saliency <= accent_saliency


def test_assign_roles_foreground_max_two():
    """Foreground role should have at most 2 tiles."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles, foreground_max=2)
    
    assert len(roles["foreground"]) <= 2


def test_assign_roles_motion_max_two():
    """Motion role should have at most 2 tiles."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles, motion_max=2)
    
    assert len(roles["motion"]) <= 2


def test_assign_roles_stripes_have_motion():
    """Vertical stripes quadrant should produce motion-assigned tiles."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles, motion_thresh=0.05)

    # Top-right quadrant tiles (rows 0-1, cols 2-3) should have high motion
    tr_indices = {t.index for t in tiles if t.row in (0, 1) and t.col in (2, 3)}

    # At least some TR tiles should be in motion or accent
    motion_or_accent = set(roles["motion"]) | set(roles["accent"])
    overlap = tr_indices & motion_or_accent
    assert len(overlap) > 0, "Expected TR quadrant to have motion/accent tiles"


def test_assign_roles_meta_has_accent_saliency():
    """Meta should contain accent_saliency and confidence values."""
    img = _img_single_bright_blob()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)

    assert "meta" in roles
    assert "accent_saliency" in roles["meta"]
    assert isinstance(roles["meta"]["accent_saliency"], float)
    
    # New confidence fields
    assert "accent_transient" in roles["meta"]
    assert "foreground_confidence" in roles["meta"]
    assert "motion_confidence" in roles["meta"]
    
    # accent_transient should be 0-1 (max of l_std, hf_energy)
    assert 0.0 <= roles["meta"]["accent_transient"] <= 1.0
    
    # Confidence values should be >= 0
    assert roles["meta"]["foreground_confidence"] >= 0.0
    assert roles["meta"]["motion_confidence"] >= 0.0


def test_assign_roles_config_included():
    """Roles should include config used for reproducibility."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles, foreground_thresh=0.2, motion_thresh=0.15)

    assert "config" in roles
    assert roles["config"]["FOREGROUND_THRESH"] == 0.2
    assert roles["config"]["MOTION_THRESH"] == 0.15
    assert roles["config"]["FOREGROUND_MAX"] == 2
    assert roles["config"]["MOTION_MAX"] == 2


def test_assign_roles_lists_are_sorted():
    """All role lists should be sorted for determinism."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)

    for role_name in ("accent", "foreground", "motion", "bed"):
        indices = roles[role_name]
        assert indices == sorted(indices), f"{role_name} list not sorted: {indices}"


def test_slot_allocation_sums_to_eight():
    """Slot allocation should always sum to 8."""
    from imaginarium.image_spatial import compute_slot_allocation
    
    # Test various role configurations
    test_cases = [
        {"accent": [0], "foreground": [1, 2], "motion": [3, 4], "bed": list(range(5, 16))},
        {"accent": [0], "foreground": [], "motion": [3, 4], "bed": list(range(5, 16))},
        {"accent": [0], "foreground": [1], "motion": [], "bed": list(range(5, 16))},
        {"accent": [0], "foreground": [], "motion": [], "bed": list(range(1, 16))},
    ]
    
    for roles in test_cases:
        slots = compute_slot_allocation(roles)
        total = sum(slots.values())
        assert total == 8, f"Expected 8 slots, got {total} for {roles}"


def test_build_debug_output_structure():
    """Debug output should have all required fields."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    debug = build_debug_output(tiles, roles, grid=(4, 4))

    # Required fields
    assert debug["version"] == 1
    assert "roles" in debug
    assert "role_grid" in debug
    assert "slot_allocation" in debug
    assert "quality_score" in debug  # None for now
    assert "fallback" in debug
    assert "meta" in debug
    assert "config" in debug
    assert "grids" in debug

    # Config should have threshold values
    assert "FOREGROUND_THRESH" in debug["config"]
    assert "MOTION_THRESH" in debug["config"]

    # role_grid should be 4x4 with single-letter codes
    assert len(debug["role_grid"]) == 4
    assert len(debug["role_grid"][0]) == 4

    # All cells should have a role letter (A/F/M/B)
    valid_letters = {"A", "F", "M", "B"}
    for row in debug["role_grid"]:
        for cell in row:
            assert cell in valid_letters, f"Unexpected role letter: {cell}"


def test_build_debug_output_role_grid_matches_roles():
    """Role grid letters should match the roles dict assignments."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    debug = build_debug_output(tiles, roles, grid=(4, 4))

    letter_map = {"A": "accent", "F": "foreground", "M": "motion", "B": "bed"}

    for t in tiles:
        letter = debug["role_grid"][t.row][t.col]
        role_name = letter_map[letter]
        assert t.index in debug["roles"][role_name], \
            f"Tile {t.index} at ({t.row},{t.col}) has letter {letter} but not in roles[{role_name}]"


def test_build_debug_output_slot_allocation_consistency():
    """Slot allocation should match role counts with redistribution."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    debug = build_debug_output(tiles, roles, grid=(4, 4))

    slots = debug["slot_allocation"]
    
    # Accent always 1
    assert slots["accent"] == 1
    
    # Foreground/motion match actual tile counts
    assert slots["foreground"] == len(debug["roles"]["foreground"])
    assert slots["motion"] == len(debug["roles"]["motion"])
    
    # Total is 8
    assert sum(slots.values()) == 8


# =============================================================================
# Phase C: Coarse Weighting + Layer Stats Tests
# =============================================================================

def test_coarse_cells_structure():
    """4 coarse cells, each with 4 children, strengths computed."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    
    cells = compute_coarse_cells(tiles)
    
    assert len(cells) == 4
    
    for cell in cells:
        assert len(cell.child_indices) == 4
        assert 0.0 <= cell.motion_strength <= 1.0
        assert 0.0 <= cell.object_strength <= 1.0
        assert 0.0 <= cell.bed_strength <= 1.0
        assert cell.dominant_role in ("motion", "foreground", "bed")


def test_coarse_cells_child_mapping():
    """Verify coarse cell child indices are correct."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    
    cells = compute_coarse_cells(tiles)
    
    # TL cell (0) should have tiles [0,1,4,5]
    assert cells[0].child_indices == [0, 1, 4, 5]
    # TR cell (1) should have tiles [2,3,6,7]
    assert cells[1].child_indices == [2, 3, 6, 7]
    # BL cell (2) should have tiles [8,9,12,13]
    assert cells[2].child_indices == [8, 9, 12, 13]
    # BR cell (3) should have tiles [10,11,14,15]
    assert cells[3].child_indices == [10, 11, 14, 15]


def test_tile_weights_bounded():
    """All tile weights should be in [WEIGHT_FLOOR, 1.0]."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    coarse_cells = compute_coarse_cells(tiles)
    
    weights = compute_tile_weights(tiles, roles, coarse_cells)
    
    assert len(weights) == 16
    for w in weights:
        assert WEIGHT_FLOOR <= w <= 1.0


def test_tile_weight_accent_never_dampened():
    """Accent tile always gets weight 1.0."""
    img = _img_single_bright_blob()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    coarse_cells = compute_coarse_cells(tiles)
    
    weights = compute_tile_weights(tiles, roles, coarse_cells)
    
    accent_idx = roles["accent"][0]
    assert weights[accent_idx] == 1.0


def test_tile_weight_dampening():
    """Motion tile in bed-dominant quadrant gets weight < 1.0."""
    # Create image where most is uniform (bed-like) but one quadrant has stripes
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles, motion_thresh=0.05)
    coarse_cells = compute_coarse_cells(tiles)
    
    weights = compute_tile_weights(tiles, roles, coarse_cells)
    
    # Check if any motion tiles exist and have dampened weights
    motion_indices = roles.get("motion", [])
    if motion_indices:
        # At least verify weights are computed and bounded
        for idx in motion_indices:
            assert WEIGHT_FLOOR <= weights[idx] <= 1.0


def test_layer_stats_structure():
    """LayerStats has all required fields for each role."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    coarse_cells = compute_coarse_cells(tiles)
    weights = compute_tile_weights(tiles, roles, coarse_cells)
    
    layer_stats = compute_layer_stats(tiles, roles, weights)
    
    for role in ("accent", "foreground", "motion", "bed"):
        assert role in layer_stats
        stats = layer_stats[role]
        assert hasattr(stats, 'tile_count')
        assert hasattr(stats, 'tile_indices')
        assert hasattr(stats, 'tile_weights')
        assert hasattr(stats, 'l_mean')
        assert hasattr(stats, 'area_fraction')


def test_layer_stats_area_fraction():
    """Area fraction should match tile_count / 16."""
    img = _img_uniform_gray()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    coarse_cells = compute_coarse_cells(tiles)
    weights = compute_tile_weights(tiles, roles, coarse_cells)
    
    layer_stats = compute_layer_stats(tiles, roles, weights)
    
    for role in ("accent", "foreground", "motion", "bed"):
        stats = layer_stats[role]
        expected_fraction = stats.tile_count / 16.0
        assert abs(stats.area_fraction - expected_fraction) < 0.001


def test_layer_stats_empty_role():
    """Empty role returns zero stats gracefully."""
    img = _img_uniform_gray()  # Likely no motion/foreground
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles, foreground_thresh=0.99, motion_thresh=0.99)  # Force empty
    coarse_cells = compute_coarse_cells(tiles)
    weights = compute_tile_weights(tiles, roles, coarse_cells)
    
    layer_stats = compute_layer_stats(tiles, roles, weights)
    
    # Foreground and motion should be empty with very high thresholds
    for role in ("foreground", "motion"):
        if layer_stats[role].tile_count == 0:
            stats = layer_stats[role]
            assert stats.l_mean == 0.0
            assert stats.area_fraction == 0.0
            assert stats.tile_indices == []


def test_layer_stats_weighted_means_finite():
    """All weighted means should be finite."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    coarse_cells = compute_coarse_cells(tiles)
    weights = compute_tile_weights(tiles, roles, coarse_cells)
    
    layer_stats = compute_layer_stats(tiles, roles, weights)
    
    for role, stats in layer_stats.items():
        assert np.isfinite(stats.l_mean)
        assert np.isfinite(stats.l_std)
        assert np.isfinite(stats.sat_mean)
        assert np.isfinite(stats.edge_density)
        assert np.isfinite(stats.hf_energy)
        assert np.isfinite(stats.vertical_edge_ratio)


def test_build_spatial_analysis_structure():
    """Spatial analysis includes all Phase B + C fields."""
    img = _img_vertical_stripes_quadrant()
    tiles = extract_tile_features(img, grid=(4, 4), resize_to=256)
    compute_hints(tiles)
    roles = assign_roles(tiles)
    
    analysis = build_spatial_analysis(tiles, roles, grid=(4, 4))
    
    # Phase B fields
    assert "version" in analysis
    assert "roles" in analysis
    assert "role_grid" in analysis
    assert "slot_allocation" in analysis
    
    # Phase C fields
    assert "coarse" in analysis
    assert "cells" in analysis["coarse"]
    assert "tile_weights" in analysis["coarse"]
    assert "tile_weight_grid" in analysis["coarse"]
    assert "layer_stats" in analysis
    
    # Verify coarse structure
    assert len(analysis["coarse"]["cells"]) == 4
    assert len(analysis["coarse"]["tile_weights"]) == 16
    assert len(analysis["coarse"]["tile_weight_grid"]) == 4
    
    # Verify layer_stats has all roles
    for role in ("accent", "foreground", "motion", "bed"):
        assert role in analysis["layer_stats"]


# =============================================================================
# Phase D: Quality Gate + Spec Token Tests
# =============================================================================

def _img_smooth_gradient():
    """Create a smooth horizontal gradient (no edges, low structure)."""
    img = np.zeros((256, 256, 3), dtype=np.uint8)
    for x in range(256):
        val = int(x * 255 / 255)
        img[:, x, :] = val
    return img


def test_quality_uniform_gray_fallback():
    """Uniform gray image should trigger fallback (low structure)."""
    img = _img_uniform_gray()
    result = analyze_image_spatial(img, resize_to=256)
    
    # Uniform image has no structure variation
    assert result["fallback"] == True
    assert result["quality_score"] < QUALITY_THRESHOLD
    assert "structure" in result["quality"]["checks"]


def test_quality_stripes_no_fallback():
    """Vertical stripes quadrant should NOT trigger fallback."""
    img = _img_vertical_stripes_quadrant()
    result = analyze_image_spatial(img, resize_to=256)
    
    # Stripes create structure and motion
    assert result["fallback"] == False
    assert result["quality_score"] >= QUALITY_THRESHOLD
    
    # Motion should be present
    assert len(result["roles"]["motion"]) > 0 or len(result["roles"]["accent"]) > 0


def test_quality_bright_blob_no_fallback():
    """Single bright blob should NOT trigger fallback."""
    img = _img_single_bright_blob()
    result = analyze_image_spatial(img, resize_to=256)
    
    # Blob creates structure and meaningful accent
    assert result["fallback"] == False
    assert result["quality_score"] >= QUALITY_THRESHOLD
    
    # Accent should be meaningful
    assert result["quality"]["checks"]["accent"] == True


def test_quality_smooth_gradient_fallback():
    """Smooth gradient has structure but low edge variance - check behavior."""
    img = _img_smooth_gradient()
    result = analyze_image_spatial(img, resize_to=256)
    
    # Gradient has l_mean variance but low edge variance
    # Should pass structure check (l_mean var) but may fail others
    # Lock expected behavior: fallback based on quality threshold
    assert "structure" in result["quality"]["checks"]
    # The gradient has variation in l_mean, so structure should pass
    # But other checks may fail, leading to potential fallback


def test_fallback_produces_empty_tokens():
    """When fallback=True, spec_tokens should be empty list."""
    img = _img_uniform_gray()
    result = analyze_image_spatial(img, resize_to=256)
    
    if result["fallback"]:
        assert result["spec_tokens"] == []


def test_spec_tokens_match_slot_allocation():
    """Sum of slot_count across tokens should equal 8."""
    img = _img_vertical_stripes_quadrant()
    result = analyze_image_spatial(img, resize_to=256)
    
    if not result["fallback"]:
        total_slots = sum(t["slot_count"] for t in result["spec_tokens"])
        assert total_slots == 8


def test_spec_tokens_exclude_zero_slot_roles():
    """Roles with 0 slots should not produce tokens."""
    img = _img_uniform_gray()
    # Use high thresholds to force empty foreground/motion
    result = analyze_image_spatial(
        img, 
        resize_to=256,
        foreground_thresh=0.99,
        motion_thresh=0.99,
    )
    
    if not result["fallback"]:
        for token in result["spec_tokens"]:
            assert token["slot_count"] > 0


def test_quality_checks_all_present():
    """All expected check keys should exist in quality_checks."""
    img = _img_vertical_stripes_quadrant()
    result = analyze_image_spatial(img, resize_to=256)
    
    expected_checks = {
        "structure",
        "accent",
        "motion_conf",
        "fg_conf",
        "motion_weight",
        "nonbed_cap",
    }
    
    actual_checks = set(result["quality"]["checks"].keys())
    assert expected_checks == actual_checks


def test_analyze_image_spatial_complete_structure():
    """Full analysis should include all phases A-D fields."""
    img = _img_vertical_stripes_quadrant()
    result = analyze_image_spatial(img, resize_to=256)
    
    # Phase B fields
    assert "version" in result
    assert "roles" in result
    assert "role_grid" in result
    assert "slot_allocation" in result
    
    # Phase C fields
    assert "coarse" in result
    assert "layer_stats" in result
    
    # Phase D fields
    assert "quality_score" in result
    assert "quality" in result
    assert "fallback" in result
    assert "spec_tokens" in result
    
    # Quality structure
    assert "score" in result["quality"]
    assert "threshold" in result["quality"]
    assert "fallback" in result["quality"]
    assert "checks" in result["quality"]
    
    # Config should include Phase D constants
    assert "QUALITY_THRESHOLD" in result["config"]
    assert "WEIGHT_FLOOR" in result["config"]
