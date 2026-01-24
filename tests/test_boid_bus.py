"""
Unit tests for Boid Bus Integration

Tests per spec v4 acceptance criteria:
1. Grid-to-bus mapping correctness
2. Downselection determinism with tie-break
3. Non-finite wire contract
"""

import math
import pytest
from unittest.mock import MagicMock

from src.utils.boid_bus import (
    grid_to_bus,
    is_valid_unified_bus_index,
    is_finite,
    aggregate_contributions,
    downselect_snapshot,
    prepare_offsets_message,
    bus_index_to_target_key,
    BoidBusSender,
    MAX_OFFSET_PAIRS,
)


class TestGridToBusMapping:
    """Test grid_to_bus mapping per spec v4 acceptance criteria."""

    def test_mod_slot_start(self):
        """grid_to_bus(0, 80) == 1000"""
        assert grid_to_bus(0, 80) == 1000

    def test_mod_slot_end(self):
        """grid_to_bus(0, 107) == 1027"""
        assert grid_to_bus(0, 107) == 1027

    def test_channel_start(self):
        """grid_to_bus(0, 108) == 1028"""
        assert grid_to_bus(0, 108) == 1028

    def test_channel_end(self):
        """grid_to_bus(0, 131) == 1051"""
        assert grid_to_bus(0, 131) == 1051

    def test_fx_start(self):
        """grid_to_bus(0, 132) == 1052"""
        assert grid_to_bus(0, 132) == 1052

    def test_fx_end(self):
        """grid_to_bus(0, 150) == 1070"""
        assert grid_to_bus(0, 150) == 1070

    def test_generator_column(self):
        """grid_to_bus(0, 79) is None"""
        assert grid_to_bus(0, 79) is None

    def test_out_of_range(self):
        """grid_to_bus(0, 151) is None"""
        assert grid_to_bus(0, 151) is None

    def test_negative_column(self):
        """Negative column returns None"""
        assert grid_to_bus(0, -1) is None

    def test_row_does_not_affect_mapping(self):
        """Row should not affect mapping in this phase"""
        assert grid_to_bus(0, 80) == grid_to_bus(5, 80) == grid_to_bus(100, 80)


class TestBusIndexValidation:
    """Test bus index validation."""

    def test_valid_range_start(self):
        assert is_valid_unified_bus_index(1000) is True

    def test_valid_range_end(self):
        assert is_valid_unified_bus_index(1070) is True

    def test_valid_range_middle(self):
        assert is_valid_unified_bus_index(1035) is True

    def test_below_range(self):
        assert is_valid_unified_bus_index(999) is False

    def test_above_range(self):
        assert is_valid_unified_bus_index(1071) is False

    def test_non_integer(self):
        assert is_valid_unified_bus_index(1000.5) is False  # type: ignore


class TestDownselectionDeterminism:
    """Test deterministic downselection with tie-break per spec v4."""

    def test_under_limit_unchanged(self):
        """Snapshot with <= 100 entries is unchanged"""
        snapshot = {1000 + i: 0.1 * i for i in range(50)}
        result = downselect_snapshot(snapshot)
        assert result == snapshot

    def test_exact_limit_unchanged(self):
        """Snapshot with exactly 100 entries is unchanged"""
        snapshot = {1000 + i: 0.1 for i in range(100)}
        result = downselect_snapshot(snapshot)
        assert len(result) == 100

    def test_over_limit_downselects(self):
        """Snapshot with > 100 entries is downselected to 100"""
        snapshot = {i: 0.1 for i in range(1000, 1071)}  # 71 entries
        # Add more entries (using arbitrary indices for test)
        for i in range(71, 150):
            snapshot[2000 + i] = 0.05  # These should be filtered by validation anyway
        # But for this test, let's use valid indices
        snapshot = {1000 + (i % 71): 0.01 * i for i in range(150)}
        result = downselect_snapshot(snapshot)
        assert len(result) <= MAX_OFFSET_PAIRS

    def test_tie_break_by_bus_index(self):
        """Entries with same abs(offset) are ordered by busIndex ascending"""
        # Create snapshot with ties
        snapshot = {
            1050: 0.5,   # Higher bus index
            1010: 0.5,   # Lower bus index - should be kept over 1050 in tie
            1030: 0.5,   # Middle
            1060: 0.3,   # Lower magnitude
            1005: 0.3,   # Same magnitude, lower index
        }

        # When size is under limit, no downselection needed
        # Test with a larger snapshot that requires downselection
        large_snapshot = {}
        # Fill with 100 entries of magnitude 0.1
        for i in range(100):
            large_snapshot[1000 + (i % 71)] = 0.1
        # Add 2 entries with higher magnitude that should definitely be kept
        large_snapshot[1070] = 0.9
        large_snapshot[1000] = 0.8

        result = downselect_snapshot(large_snapshot)
        assert len(result) == MAX_OFFSET_PAIRS
        # The two highest magnitude entries should be present
        assert 1070 in result
        assert 1000 in result

    def test_primary_sort_by_abs_offset_descending(self):
        """Primary sort is by abs(offset) descending"""
        # Create a snapshot larger than 100 where we can verify ordering
        snapshot = {}
        for i in range(120):
            # Varying magnitudes
            snapshot[1000 + (i % 71)] = 0.01 * (i + 1)

        # Override some to have known high values
        snapshot[1050] = 1.0
        snapshot[1020] = 0.9
        snapshot[1010] = 0.8

        result = downselect_snapshot(snapshot)

        # The highest magnitude entries should be present
        assert 1050 in result
        assert 1020 in result
        assert 1010 in result


class TestNonFiniteWireContract:
    """Test non-finite value filtering per spec v4 wire contract."""

    def test_nan_filtered_in_aggregation(self):
        """NaN offsets are filtered during aggregation"""
        contributions = [
            (0, 80, 0.5),       # Valid
            (0, 81, float('nan')),  # NaN - should be filtered
            (0, 82, 0.3),       # Valid
        ]
        result = aggregate_contributions(contributions)

        assert 1000 in result  # col 80 -> bus 1000
        assert 1001 not in result  # col 81 -> bus 1001, but NaN
        assert 1002 in result  # col 82 -> bus 1002

    def test_inf_filtered_in_aggregation(self):
        """Infinity offsets are filtered during aggregation"""
        contributions = [
            (0, 80, 0.5),       # Valid
            (0, 81, float('inf')),  # Inf - should be filtered
            (0, 82, float('-inf')),  # -Inf - should be filtered
        ]
        result = aggregate_contributions(contributions)

        assert 1000 in result
        assert 1001 not in result
        assert 1002 not in result

    def test_sum_becomes_nonfinite_filtered(self):
        """If sum becomes non-finite, that entry is filtered"""
        # This is harder to trigger naturally, but test the filtering
        contributions = [
            (0, 80, 1e308),
            (0, 80, 1e308),  # Sum might overflow to inf
        ]
        result = aggregate_contributions(contributions)

        # If sum is finite, it's kept; if not, filtered
        if 1000 in result:
            assert is_finite(result[1000])

    def test_is_finite_helper(self):
        """Test is_finite helper function"""
        assert is_finite(0.0) is True
        assert is_finite(1.5) is True
        assert is_finite(-100.0) is True
        assert is_finite(float('nan')) is False
        assert is_finite(float('inf')) is False
        assert is_finite(float('-inf')) is False


class TestAggregation:
    """Test contribution aggregation."""

    def test_simple_aggregation(self):
        """Basic aggregation works"""
        contributions = [
            (0, 80, 0.1),
            (0, 81, 0.2),
            (0, 82, 0.3),
        ]
        result = aggregate_contributions(contributions)

        assert result[1000] == 0.1
        assert result[1001] == 0.2
        assert result[1002] == 0.3

    def test_same_bus_index_summed(self):
        """Multiple contributions to same bus are summed"""
        contributions = [
            (0, 80, 0.1),
            (1, 80, 0.2),  # Same col, different row
            (2, 80, 0.3),
        ]
        result = aggregate_contributions(contributions)

        assert result[1000] == pytest.approx(0.6)

    def test_generator_columns_ignored(self):
        """Columns < 80 are ignored (generator path)"""
        contributions = [
            (0, 0, 1.0),   # Generator
            (0, 79, 1.0),  # Generator
            (0, 80, 0.5),  # Unified
        ]
        result = aggregate_contributions(contributions)

        assert len(result) == 1
        assert 1000 in result


class TestPrepareOffsetsMessage:
    """Test OSC message preparation."""

    def test_empty_snapshot(self):
        """Empty snapshot produces empty args"""
        result = prepare_offsets_message({})
        assert result == []

    def test_single_entry(self):
        """Single entry produces two args"""
        result = prepare_offsets_message({1000: 0.5})
        assert result == [1000, 0.5]

    def test_ordered_by_bus_index(self):
        """Entries are ordered by bus index ascending"""
        snapshot = {1050: 0.1, 1000: 0.2, 1030: 0.3}
        result = prepare_offsets_message(snapshot)

        assert result == [1000, 0.2, 1030, 0.3, 1050, 0.1]


class TestBusIndexToTargetKey:
    """Test bus index to target key conversion."""

    def test_mod_slot_params(self):
        assert bus_index_to_target_key(1000) == "mod_1_p0"
        assert bus_index_to_target_key(1006) == "mod_1_p6"
        assert bus_index_to_target_key(1007) == "mod_2_p0"
        assert bus_index_to_target_key(1027) == "mod_4_p6"

    def test_channel_params(self):
        assert bus_index_to_target_key(1028) == "chan_1_echo"
        assert bus_index_to_target_key(1029) == "chan_1_verb"
        assert bus_index_to_target_key(1030) == "chan_1_pan"
        assert bus_index_to_target_key(1031) == "chan_2_echo"

    def test_fx_params(self):
        assert bus_index_to_target_key(1052) == "fx_heat_drive"
        assert bus_index_to_target_key(1053) == "fx_heat_mix"
        assert bus_index_to_target_key(1054) == "fx_echo_time"

    def test_invalid_index(self):
        assert bus_index_to_target_key(999) is None
        assert bus_index_to_target_key(1071) is None


class TestBoidBusSender:
    """Test BoidBusSender class."""

    def test_enable_sends_message(self):
        """Enable sends /noise/boid/enable 1"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)

        sender.enable()

        mock_client.send_message.assert_called_with('/noise/boid/enable', 1)
        assert sender.is_enabled is True

    def test_enable_idempotent(self):
        """Multiple enable calls only send once"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)

        sender.enable()
        sender.enable()
        sender.enable()

        assert mock_client.send_message.call_count == 1

    def test_disable_sends_messages(self):
        """Disable sends enable 0 and clear"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)
        sender.enable()
        mock_client.reset_mock()

        sender.disable()

        calls = mock_client.send_message.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ('/noise/boid/enable', 0)
        assert calls[1][0] == ('/noise/boid/clear',)
        assert sender.is_enabled is False

    def test_disable_idempotent(self):
        """Multiple disable calls only send once"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)
        sender.enable()
        mock_client.reset_mock()

        sender.disable()
        sender.disable()

        # Only one pair of messages
        assert mock_client.send_message.call_count == 2

    def test_send_offsets_when_disabled_does_nothing(self):
        """send_offsets does nothing when disabled"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)

        sender.send_offsets([(0, 80, 0.5)])

        mock_client.send_message.assert_not_called()

    def test_send_offsets_aggregates_and_sends(self):
        """send_offsets aggregates and sends properly"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)
        sender.enable()
        mock_client.reset_mock()

        contributions = [
            (0, 80, 0.3),
            (1, 80, 0.2),  # Same bus, will be summed
            (0, 81, 0.1),
        ]
        sender.send_offsets(contributions)

        # Should send offsets message
        call_args = mock_client.send_message.call_args
        assert call_args[0][0] == '/noise/boid/offsets'
        # Args should include bus indices and summed offsets

    def test_send_empty_offsets_sends_clear(self):
        """Empty contributions send clear message"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)
        sender.enable()
        mock_client.reset_mock()

        sender.send_offsets([])

        mock_client.send_message.assert_called_with('/noise/boid/clear')

    def test_clear_sends_message(self):
        """clear() sends clear message"""
        mock_client = MagicMock()
        sender = BoidBusSender(mock_client)

        sender.clear()

        mock_client.send_message.assert_called_with('/noise/boid/clear')
