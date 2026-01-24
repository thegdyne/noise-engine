"""
Tests for channel FX modulation (send/pan targets).

PyQt5 mock is set up in conftest.py to avoid StopIteration errors.
"""

import pytest
from src.gui.mod_routing_state import (
    ModConnection,
    ModRoutingState,
    CHAN_PARAMS,
    is_valid_ext_target,
    build_send_target,
)


class TestChannelParams:
    """Tests for channel parameter definitions."""

    def test_chan_params_count(self):
        """CHAN_PARAMS should have 24 entries (8 channels x 3 params)."""
        # 8 echo sends + 8 verb sends + 8 pans = 24
        assert len(CHAN_PARAMS) == 24

    def test_send_ec_targets_valid(self):
        """All echo send targets are valid."""
        for ch in range(1, 9):
            target = f"send:{ch}:ec"
            assert is_valid_ext_target(target), f"{target} should be valid"

    def test_send_vb_targets_valid(self):
        """All verb send targets are valid."""
        for ch in range(1, 9):
            target = f"send:{ch}:vb"
            assert is_valid_ext_target(target), f"{target} should be valid"

    def test_chan_pan_targets_valid(self):
        """All pan targets are valid."""
        for ch in range(1, 9):
            target = f"chan:{ch}:pan"
            assert is_valid_ext_target(target), f"{target} should be valid"

    def test_build_send_target(self):
        """build_send_target creates correct format."""
        assert build_send_target(1, "ec") == "send:1:ec"
        assert build_send_target(3, "vb") == "send:3:vb"


class TestChannelFXRouting:
    """Tests for routing modulation to channel FX parameters."""

    def test_route_to_send_echo(self):
        """Can route to echo send."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=0, target_str="send:1:ec", amount=0.7)
        state.add_connection(conn)

        retrieved = state.get_connection(0, target_str="send:1:ec")
        assert retrieved is not None
        assert retrieved.amount == 0.7

    def test_route_to_send_verb(self):
        """Can route to verb send."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=4, target_str="send:3:vb", amount=0.5)
        state.add_connection(conn)

        retrieved = state.get_connection(4, target_str="send:3:vb")
        assert retrieved is not None

    def test_route_to_pan(self):
        """Can route to channel pan."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=8, target_str="chan:5:pan", amount=0.8, offset=-0.2)
        state.add_connection(conn)

        retrieved = state.get_connection(8, target_str="chan:5:pan")
        assert retrieved is not None
        assert retrieved.offset == -0.2

    def test_multiple_channel_routes(self):
        """Can have multiple routes to different channel params."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_str="send:1:ec"))
        state.add_connection(ModConnection(source_bus=1, target_str="send:1:vb"))
        state.add_connection(ModConnection(source_bus=2, target_str="chan:1:pan"))

        ext_conns = state.get_extended_connections()
        assert len(ext_conns) == 3
