"""
Tests for Bus Unification v3 (176 targets)

Validates the UI Refresh expansion of the unified bus system from 149 to 176 targets.
"""

import unittest
import re
from typing import List


class TestBusUnificationKeyCount(unittest.TestCase):
    """Test that UNIFIED_BUS_TARGET_KEYS has exactly 176 entries."""

    def test_unified_bus_target_keys_count(self):
        """Validate 176 keys in the unified bus target list."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        self.assertEqual(len(UNIFIED_BUS_TARGET_KEYS), 176,
            f"Expected 176 keys, got {len(UNIFIED_BUS_TARGET_KEYS)}")

    def test_historical_v2_keys_count(self):
        """Validate 149 keys in the historical v2 list."""
        from src.config.target_keys_v2 import TARGET_KEYS_V2
        self.assertEqual(len(TARGET_KEYS_V2), 149,
            f"Expected 149 keys in v2, got {len(TARGET_KEYS_V2)}")


class TestBusUnificationIndicesUnchanged(unittest.TestCase):
    """Test that indices 0-107 are unchanged from v2."""

    def test_gen_core_indices_unchanged(self):
        """Indices 0-39 (gen core) must match v2 exactly."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        from src.config.target_keys_v2 import TARGET_KEYS_V2

        for i in range(40):
            self.assertEqual(UNIFIED_BUS_TARGET_KEYS[i], TARGET_KEYS_V2[i],
                f"Index {i} mismatch: v3='{UNIFIED_BUS_TARGET_KEYS[i]}' vs v2='{TARGET_KEYS_V2[i]}'")

    def test_gen_custom_indices_unchanged(self):
        """Indices 40-79 (gen custom) must match v2 exactly."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        from src.config.target_keys_v2 import TARGET_KEYS_V2

        for i in range(40, 80):
            self.assertEqual(UNIFIED_BUS_TARGET_KEYS[i], TARGET_KEYS_V2[i],
                f"Index {i} mismatch: v3='{UNIFIED_BUS_TARGET_KEYS[i]}' vs v2='{TARGET_KEYS_V2[i]}'")

    def test_mod_slot_indices_unchanged(self):
        """Indices 80-107 (mod slots) must match v2 exactly."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        from src.config.target_keys_v2 import TARGET_KEYS_V2

        for i in range(80, 108):
            self.assertEqual(UNIFIED_BUS_TARGET_KEYS[i], TARGET_KEYS_V2[i],
                f"Index {i} mismatch: v3='{UNIFIED_BUS_TARGET_KEYS[i]}' vs v2='{TARGET_KEYS_V2[i]}'")


class TestBusUnificationZoneBoundaries(unittest.TestCase):
    """Test zone boundary indices (108, 148, 168, 175)."""

    def test_channel_zone_start(self):
        """Index 108 is first channel param (chan_1_fx1)."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        self.assertEqual(UNIFIED_BUS_TARGET_KEYS[108], "chan_1_fx1",
            f"Index 108 should be 'chan_1_fx1', got '{UNIFIED_BUS_TARGET_KEYS[108]}'")

    def test_channel_zone_end(self):
        """Index 147 is last channel param (chan_8_pan)."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        self.assertEqual(UNIFIED_BUS_TARGET_KEYS[147], "chan_8_pan",
            f"Index 147 should be 'chan_8_pan', got '{UNIFIED_BUS_TARGET_KEYS[147]}'")

    def test_fx_slot_zone_start(self):
        """Index 148 is first FX slot param (fx_slot1_p1)."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        self.assertEqual(UNIFIED_BUS_TARGET_KEYS[148], "fx_slot1_p1",
            f"Index 148 should be 'fx_slot1_p1', got '{UNIFIED_BUS_TARGET_KEYS[148]}'")

    def test_fx_slot_zone_end(self):
        """Index 167 is last FX slot param (fx_slot4_return)."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        self.assertEqual(UNIFIED_BUS_TARGET_KEYS[167], "fx_slot4_return",
            f"Index 167 should be 'fx_slot4_return', got '{UNIFIED_BUS_TARGET_KEYS[167]}'")

    def test_master_insert_zone_start(self):
        """Index 168 is first master insert param (fx_fb_drive)."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        self.assertEqual(UNIFIED_BUS_TARGET_KEYS[168], "fx_fb_drive",
            f"Index 168 should be 'fx_fb_drive', got '{UNIFIED_BUS_TARGET_KEYS[168]}'")

    def test_master_insert_zone_end(self):
        """Index 175 is last master insert param (fx_heat_drive)."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        self.assertEqual(UNIFIED_BUS_TARGET_KEYS[175], "fx_heat_drive",
            f"Index 175 should be 'fx_heat_drive', got '{UNIFIED_BUS_TARGET_KEYS[175]}'")


class TestBusUnificationKeyFormats(unittest.TestCase):
    """Test key format validation."""

    def test_channel_keys_format(self):
        """Channel keys follow pattern chan_N_fxM or chan_N_pan."""
        from src.config import UNIFIED_BUS_TARGET_KEYS

        chan_pattern = re.compile(r'^chan_[1-8]_(fx[1-4]|pan)$')
        for i in range(108, 148):
            key = UNIFIED_BUS_TARGET_KEYS[i]
            self.assertIsNotNone(chan_pattern.match(key),
                f"Index {i} key '{key}' doesn't match channel pattern")

    def test_fx_slot_keys_format(self):
        """FX slot keys follow pattern fx_slotN_pM or fx_slotN_return."""
        from src.config import UNIFIED_BUS_TARGET_KEYS

        fx_slot_pattern = re.compile(r'^fx_slot[1-4]_(p[1-4]|return)$')
        for i in range(148, 168):
            key = UNIFIED_BUS_TARGET_KEYS[i]
            self.assertIsNotNone(fx_slot_pattern.match(key),
                f"Index {i} key '{key}' doesn't match FX slot pattern")

    def test_master_insert_keys_format(self):
        """Master insert keys follow expected patterns."""
        from src.config import UNIFIED_BUS_TARGET_KEYS

        expected_master_keys = [
            "fx_fb_drive",
            "fx_fb_freq1",
            "fx_fb_reso1",
            "fx_fb_freq2",
            "fx_fb_reso2",
            "fx_fb_syncAmt",
            "fx_fb_harmonics",
            "fx_heat_drive",
        ]
        for i, expected in enumerate(expected_master_keys):
            idx = 168 + i
            self.assertEqual(UNIFIED_BUS_TARGET_KEYS[idx], expected,
                f"Index {idx} should be '{expected}', got '{UNIFIED_BUS_TARGET_KEYS[idx]}'")


class TestBusUnificationZoneRanges(unittest.TestCase):
    """Test zone range calculations in boid_state."""

    def test_zone_ranges_gen(self):
        """Generator zone: 0-79."""
        from src.boids.boid_state import BoidState
        state = BoidState(zone_gen=True, zone_mod=False, zone_chan=False, zone_fx=False)
        ranges = state.get_allowed_column_ranges()
        self.assertEqual(ranges, [(0, 79)], f"Expected [(0, 79)], got {ranges}")

    def test_zone_ranges_mod(self):
        """Mod zone: 80-107."""
        from src.boids.boid_state import BoidState
        state = BoidState(zone_gen=False, zone_mod=True, zone_chan=False, zone_fx=False)
        ranges = state.get_allowed_column_ranges()
        self.assertEqual(ranges, [(80, 107)], f"Expected [(80, 107)], got {ranges}")

    def test_zone_ranges_chan(self):
        """Channel zone: 108-147 (v3 expansion)."""
        from src.boids.boid_state import BoidState
        state = BoidState(zone_gen=False, zone_mod=False, zone_chan=True, zone_fx=False)
        ranges = state.get_allowed_column_ranges()
        self.assertEqual(ranges, [(108, 147)], f"Expected [(108, 147)], got {ranges}")

    def test_zone_ranges_fx(self):
        """FX zone: 148-175 (v3 expansion)."""
        from src.boids.boid_state import BoidState
        state = BoidState(zone_gen=False, zone_mod=False, zone_chan=False, zone_fx=True)
        ranges = state.get_allowed_column_ranges()
        self.assertEqual(ranges, [(148, 175)], f"Expected [(148, 175)], got {ranges}")


class TestBusUnificationColumnAllowed(unittest.TestCase):
    """Test column allowed checks in boid_state."""

    def test_column_allowed_chan_boundary(self):
        """Channel zone boundary checks."""
        from src.boids.boid_state import BoidState
        state = BoidState(zone_gen=False, zone_mod=False, zone_chan=True, zone_fx=False)

        self.assertTrue(state.is_column_allowed(108), "Column 108 should be allowed in chan zone")
        self.assertTrue(state.is_column_allowed(147), "Column 147 should be allowed in chan zone")
        self.assertFalse(state.is_column_allowed(107), "Column 107 should NOT be allowed in chan zone")
        self.assertFalse(state.is_column_allowed(148), "Column 148 should NOT be allowed in chan zone")

    def test_column_allowed_fx_boundary(self):
        """FX zone boundary checks."""
        from src.boids.boid_state import BoidState
        state = BoidState(zone_gen=False, zone_mod=False, zone_chan=False, zone_fx=True)

        self.assertTrue(state.is_column_allowed(148), "Column 148 should be allowed in fx zone")
        self.assertTrue(state.is_column_allowed(175), "Column 175 should be allowed in fx zone")
        self.assertFalse(state.is_column_allowed(147), "Column 147 should NOT be allowed in fx zone")
        self.assertFalse(state.is_column_allowed(176), "Column 176 should NOT be allowed (out of range)")


class TestBusUnificationGridConstants(unittest.TestCase):
    """Test grid constant updates."""

    def test_boid_engine_grid_cols(self):
        """GRID_COLS in boid_engine should be 176."""
        from src.boids.boid_engine import GRID_COLS
        self.assertEqual(GRID_COLS, 176, f"Expected GRID_COLS=176, got {GRID_COLS}")

    def test_boid_bus_grid_total_columns(self):
        """GRID_TOTAL_COLUMNS in boid_bus should be 176."""
        from src.utils.boid_bus import GRID_TOTAL_COLUMNS
        self.assertEqual(GRID_TOTAL_COLUMNS, 176, f"Expected GRID_TOTAL_COLUMNS=176, got {GRID_TOTAL_COLUMNS}")


class TestBusUnificationTargetIndexToKey(unittest.TestCase):
    """Test target_index_to_key function."""

    def test_target_index_to_key_channel(self):
        """Channel indices map to correct keys."""
        from src.utils.boid_bus import target_index_to_key

        self.assertEqual(target_index_to_key(108), "chan_1_fx1")
        self.assertEqual(target_index_to_key(112), "chan_1_pan")
        self.assertEqual(target_index_to_key(113), "chan_2_fx1")
        self.assertEqual(target_index_to_key(147), "chan_8_pan")

    def test_target_index_to_key_fx_slot(self):
        """FX slot indices map to correct keys."""
        from src.utils.boid_bus import target_index_to_key

        self.assertEqual(target_index_to_key(148), "fx_slot1_p1")
        self.assertEqual(target_index_to_key(152), "fx_slot1_return")
        self.assertEqual(target_index_to_key(153), "fx_slot2_p1")
        self.assertEqual(target_index_to_key(167), "fx_slot4_return")

    def test_target_index_to_key_master_insert(self):
        """Master insert indices map to correct keys."""
        from src.utils.boid_bus import target_index_to_key

        self.assertEqual(target_index_to_key(168), "fx_fb_drive")
        self.assertEqual(target_index_to_key(174), "fx_fb_harmonics")
        self.assertEqual(target_index_to_key(175), "fx_heat_drive")

    def test_target_index_to_key_out_of_range(self):
        """Out of range indices return None."""
        from src.utils.boid_bus import target_index_to_key

        self.assertIsNone(target_index_to_key(176))
        self.assertIsNone(target_index_to_key(-1))


class TestBusUnificationUniqueKeys(unittest.TestCase):
    """Test that all keys are unique."""

    def test_all_keys_unique(self):
        """All 176 keys must be unique."""
        from src.config import UNIFIED_BUS_TARGET_KEYS
        unique_keys = set(UNIFIED_BUS_TARGET_KEYS)
        self.assertEqual(len(unique_keys), 176,
            f"Expected 176 unique keys, got {len(unique_keys)} (duplicates exist)")


if __name__ == '__main__':
    unittest.main()
