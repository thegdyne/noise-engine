"""
Tests for boid target scaling system.

Tests the BoidScales class which:
- Loads per-target scaling factors from JSON config
- Maps 176 target indices to their scale values (v3 bus layout)
- Applies scaling to offset snapshots
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from src.utils.boid_scales import (
    BoidScales,
    get_boid_scales,
    reload_boid_scales,
    DEFAULT_SCALES,
)


class TestDefaultScales:
    """Tests for default scale values."""

    def test_default_scales_has_all_categories(self):
        """DEFAULT_SCALES contains all expected categories."""
        expected = [
            "generator_core",
            "generator_custom",
            "mod_slots",
            "channels",
            "fx_slots",
            "fx_dualFilter",
            "fx_heat",
        ]
        for category in expected:
            assert category in DEFAULT_SCALES, f"Missing category: {category}"

    def test_generator_core_params(self):
        """Generator core has all 5 params."""
        params = ["freq", "cutoff", "res", "attack", "decay"]
        for param in params:
            assert param in DEFAULT_SCALES["generator_core"]

    def test_generator_custom_params(self):
        """Generator custom has custom0-4."""
        for i in range(5):
            assert f"custom{i}" in DEFAULT_SCALES["generator_custom"]

    def test_mod_slots_params(self):
        """Mod slots have p0-p6."""
        for i in range(7):
            assert f"p{i}" in DEFAULT_SCALES["mod_slots"]

    def test_channel_params(self):
        """Channels have fx1-fx4 and pan (v3 layout)."""
        for param in ["fx1", "fx2", "fx3", "fx4", "pan"]:
            assert param in DEFAULT_SCALES["channels"]

    def test_fx_slots_params(self):
        """FX slots have p1-p4 and return."""
        for param in ["p1", "p2", "p3", "p4", "return"]:
            assert param in DEFAULT_SCALES["fx_slots"]

    def test_fx_dualfilter_params(self):
        """DualFilter has all 7 params."""
        for param in ["drive", "freq1", "reso1", "freq2", "reso2", "syncAmt", "harmonics"]:
            assert param in DEFAULT_SCALES["fx_dualFilter"]

    def test_fx_heat_params(self):
        """Heat has drive param."""
        assert "drive" in DEFAULT_SCALES["fx_heat"]

    def test_all_scales_in_valid_range(self):
        """All default scales are between 0 and 1."""
        for category, params in DEFAULT_SCALES.items():
            for param, value in params.items():
                assert 0 <= value <= 1, f"{category}.{param} = {value} out of range"


class TestBoidScalesIndexMapping:
    """Tests for target index to scale mapping."""

    @pytest.fixture
    def scales(self):
        """Create BoidScales with defaults (no config file)."""
        with patch('os.path.exists', return_value=False):
            return BoidScales(config_path="/nonexistent/path.json")

    def test_generator_core_indices(self, scales):
        """Indices 0-39 map to generator core params."""
        # 8 slots x 5 params = 40 indices
        for slot in range(8):
            base = slot * 5
            # freq
            assert scales.get_scale(base + 0) == DEFAULT_SCALES["generator_core"]["freq"]
            # cutoff
            assert scales.get_scale(base + 1) == DEFAULT_SCALES["generator_core"]["cutoff"]
            # res
            assert scales.get_scale(base + 2) == DEFAULT_SCALES["generator_core"]["res"]
            # attack
            assert scales.get_scale(base + 3) == DEFAULT_SCALES["generator_core"]["attack"]
            # decay
            assert scales.get_scale(base + 4) == DEFAULT_SCALES["generator_core"]["decay"]

    def test_generator_custom_indices(self, scales):
        """Indices 40-79 map to generator custom params."""
        # 8 slots x 5 custom params = 40 indices
        for slot in range(8):
            base = 40 + slot * 5
            for custom_idx in range(5):
                expected = DEFAULT_SCALES["generator_custom"][f"custom{custom_idx}"]
                assert scales.get_scale(base + custom_idx) == expected

    def test_mod_slot_indices(self, scales):
        """Indices 80-107 map to mod slot params."""
        # 4 slots x 7 params = 28 indices
        for slot in range(4):
            base = 80 + slot * 7
            for p_idx in range(7):
                expected = DEFAULT_SCALES["mod_slots"][f"p{p_idx}"]
                assert scales.get_scale(base + p_idx) == expected

    def test_channel_indices(self, scales):
        """Indices 108-147 map to channel params (v3: 8 x 5)."""
        chan_params = ["fx1", "fx2", "fx3", "fx4", "pan"]
        for chan in range(8):
            base = 108 + chan * 5
            for param_idx, param in enumerate(chan_params):
                expected = DEFAULT_SCALES["channels"][param]
                assert scales.get_scale(base + param_idx) == expected

    def test_fx_slot_indices(self, scales):
        """Indices 148-167 map to FX slot params (v3: 4 x 5)."""
        slot_params = ["p1", "p2", "p3", "p4", "return"]
        for slot in range(4):
            base = 148 + slot * 5
            for param_idx, param in enumerate(slot_params):
                expected = DEFAULT_SCALES["fx_slots"][param]
                assert scales.get_scale(base + param_idx) == expected

    def test_fx_dualfilter_indices(self, scales):
        """Indices 168-174 map to fx_dualFilter params."""
        params = ["drive", "freq1", "reso1", "freq2", "reso2", "syncAmt", "harmonics"]
        for idx, param in enumerate(params):
            expected = DEFAULT_SCALES["fx_dualFilter"][param]
            assert scales.get_scale(168 + idx) == expected

    def test_fx_heat_index(self, scales):
        """Index 175 maps to fx_heat drive."""
        assert scales.get_scale(175) == DEFAULT_SCALES["fx_heat"]["drive"]

    def test_unknown_index_returns_default(self, scales):
        """Unknown indices return 1.0."""
        assert scales.get_scale(999) == 1.0
        assert scales.get_scale(-1) == 1.0


class TestBoidScalesApply:
    """Tests for applying scales to offsets."""

    @pytest.fixture
    def scales(self):
        """Create BoidScales with defaults."""
        with patch('os.path.exists', return_value=False):
            return BoidScales(config_path="/nonexistent/path.json")

    def test_apply_scale_multiplies(self, scales):
        """apply_scale multiplies offset by scale factor."""
        # Index 0 = gen_1_freq, scale = 0.3
        result = scales.apply_scale(0, 1.0)
        assert result == 0.3

    def test_apply_scale_negative_offset(self, scales):
        """apply_scale works with negative offsets."""
        result = scales.apply_scale(0, -1.0)
        assert result == -0.3

    def test_apply_scale_zero_offset(self, scales):
        """apply_scale with zero offset returns zero."""
        result = scales.apply_scale(0, 0.0)
        assert result == 0.0

    def test_scale_snapshot(self, scales):
        """scale_snapshot applies scales to entire dict."""
        snapshot = {
            0: 1.0,   # gen_1_freq, scale 0.3
            1: 1.0,   # gen_1_cutoff, scale 0.4
            175: 1.0  # fx_heat_drive, scale 0.5
        }
        result = scales.scale_snapshot(snapshot)

        assert result[0] == pytest.approx(0.3)
        assert result[1] == pytest.approx(0.4)
        assert result[175] == pytest.approx(0.5)

    def test_scale_snapshot_preserves_keys(self, scales):
        """scale_snapshot preserves all keys."""
        snapshot = {0: 0.5, 10: 0.5, 100: 0.5}
        result = scales.scale_snapshot(snapshot)
        assert set(result.keys()) == set(snapshot.keys())


class TestBoidScalesConfigReload:
    """Tests for config file loading and reload."""

    def test_reload_with_valid_config(self, tmp_path):
        """reload() loads values from config file."""
        config = {
            "generator_core": {"freq": 0.1},
            "generator_custom": {"custom0": 0.2},
        }
        config_path = tmp_path / "test_scales.json"
        config_path.write_text(json.dumps(config))

        scales = BoidScales(config_path=str(config_path))

        # freq scale should be 0.1 from config
        assert scales.get_scale(0) == 0.1

    def test_reload_returns_true_on_success(self, tmp_path):
        """reload() returns True when config loads successfully."""
        config = {"generator_core": {"freq": 0.5}}
        config_path = tmp_path / "test_scales.json"
        config_path.write_text(json.dumps(config))

        scales = BoidScales(config_path=str(config_path))
        result = scales.reload()

        assert result is True

    def test_reload_returns_false_when_no_file(self):
        """reload() returns False when config file doesn't exist."""
        scales = BoidScales(config_path="/nonexistent/path.json")
        result = scales.reload()

        assert result is False

    def test_reload_returns_false_on_invalid_json(self, tmp_path):
        """reload() returns False on invalid JSON."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text("not valid json {{{")

        scales = BoidScales(config_path=str(config_path))
        result = scales.reload()

        assert result is False

    def test_reload_uses_defaults_for_missing_categories(self, tmp_path):
        """Missing categories use default values."""
        config = {"generator_core": {"freq": 0.1}}
        config_path = tmp_path / "test_scales.json"
        config_path.write_text(json.dumps(config))

        scales = BoidScales(config_path=str(config_path))

        # fx_heat not in config, should use 0.5 default for params
        assert scales.get_scale(175) == 0.5


class TestGlobalBoidScales:
    """Tests for global instance functions."""

    def test_get_boid_scales_returns_instance(self):
        """get_boid_scales returns a BoidScales instance."""
        scales = get_boid_scales()
        assert isinstance(scales, BoidScales)

    def test_get_boid_scales_returns_same_instance(self):
        """get_boid_scales returns the same instance on repeated calls."""
        scales1 = get_boid_scales()
        scales2 = get_boid_scales()
        assert scales1 is scales2


class TestBoidScalesIntegration:
    """Integration tests with real config file."""

    def test_real_config_file_if_exists(self, project_root):
        """Load real config file if it exists."""
        config_path = project_root / "config" / "boid_target_scales.json"

        if config_path.exists():
            scales = BoidScales(config_path=str(config_path))

            # Should have scales for all 176 targets
            for i in range(176):
                scale = scales.get_scale(i)
                assert 0 <= scale <= 2, f"Scale at index {i} = {scale} out of range"


class TestBoidScalesBoundaryValues:
    """Tests for edge cases and boundary values."""

    @pytest.fixture
    def scales(self):
        """Create BoidScales with defaults."""
        with patch('os.path.exists', return_value=False):
            return BoidScales(config_path="/nonexistent/path.json")

    def test_boundary_index_0(self, scales):
        """Index 0 (first gen core) works."""
        assert scales.get_scale(0) is not None

    def test_boundary_index_39(self, scales):
        """Index 39 (last gen core) works."""
        assert scales.get_scale(39) is not None

    def test_boundary_index_40(self, scales):
        """Index 40 (first gen custom) works."""
        assert scales.get_scale(40) is not None

    def test_boundary_index_79(self, scales):
        """Index 79 (last gen custom) works."""
        assert scales.get_scale(79) is not None

    def test_boundary_index_80(self, scales):
        """Index 80 (first mod slot) works."""
        assert scales.get_scale(80) is not None

    def test_boundary_index_107(self, scales):
        """Index 107 (last mod slot) works."""
        assert scales.get_scale(107) is not None

    def test_boundary_index_108(self, scales):
        """Index 108 (first channel) works."""
        assert scales.get_scale(108) is not None

    def test_boundary_index_147(self, scales):
        """Index 147 (last channel) works."""
        assert scales.get_scale(147) is not None

    def test_boundary_index_148(self, scales):
        """Index 148 (first FX slot) works."""
        assert scales.get_scale(148) is not None

    def test_boundary_index_167(self, scales):
        """Index 167 (last FX slot) works."""
        assert scales.get_scale(167) is not None

    def test_boundary_index_168(self, scales):
        """Index 168 (first master insert - fx_fb_drive) works."""
        assert scales.get_scale(168) is not None

    def test_boundary_index_175(self, scales):
        """Index 175 (last target - fx_heat_drive) works."""
        assert scales.get_scale(175) is not None

    def test_all_176_targets_have_scales(self, scales):
        """All 176 target indices return valid scales."""
        for i in range(176):
            scale = scales.get_scale(i)
            assert isinstance(scale, float), f"Index {i} returned non-float"
            assert scale > 0, f"Index {i} has zero or negative scale"
