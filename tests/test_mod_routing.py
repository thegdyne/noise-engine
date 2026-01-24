"""
Tests for ModRoutingState class.

PyQt5 is mocked to allow testing without Qt installation.
The mock setup uses a simple stub class for QObject to avoid
StopIteration errors from exhausted MagicMock iterators.
"""

import sys
from unittest.mock import MagicMock


# Create a simple QObject stub that doesn't interfere with Python magic methods
class QObjectStub:
    """Minimal QObject stub for testing."""
    def __init__(self, parent=None):
        pass


def pyqtSignal_stub(*args, **kwargs):
    """Return a MagicMock that acts as a signal."""
    signal = MagicMock()
    signal.emit = MagicMock()
    signal.connect = MagicMock()
    return signal


# Mock PyQt5.QtCore BEFORE importing ModRoutingState
mock_qt_core = MagicMock()
mock_qt_core.QObject = QObjectStub  # Use stub class, not MagicMock
mock_qt_core.pyqtSignal = pyqtSignal_stub
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = mock_qt_core

import pytest
from src.gui.mod_routing_state import (
    ModConnection,
    ModRoutingState,
    Polarity,
    DEFAULT_ROUTE_PARAMS,
    make_default_route_params,
    create_default_connection,
    is_valid_ext_target,
    VALID_EXT_TARGETS,
    EXTENDED_PARAMS,
)


class TestModConnection:
    """Tests for ModConnection dataclass."""

    def test_generator_route_key(self):
        """Generator route key format: source_slot_param."""
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
        assert conn.key == "0_1_cutoff"

    def test_extended_route_key(self):
        """Extended route key format: source_targetstr."""
        conn = ModConnection(source_bus=5, target_str="mod:2:p1")
        assert conn.key == "5_mod:2:p1"

    def test_is_extended_false(self):
        """Generator routes are not extended."""
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
        assert conn.is_extended is False

    def test_is_extended_true(self):
        """Routes with target_str are extended."""
        conn = ModConnection(source_bus=0, target_str="send:1:ec")
        assert conn.is_extended is True

    def test_effective_range(self):
        """Effective range = depth * amount."""
        conn = ModConnection(
            source_bus=0, target_slot=1, target_param="cutoff",
            depth=0.8, amount=0.5
        )
        assert abs(conn.effective_range - 0.4) < 0.001

    def test_default_values(self):
        """Check default parameter values."""
        conn = ModConnection(source_bus=0, target_slot=1, target_param="freq")
        assert conn.depth == 1.0
        assert conn.amount == 0.5
        assert conn.offset == 0.0
        assert conn.polarity == Polarity.BIPOLAR
        assert conn.invert is False

    def test_to_dict_generator(self):
        """Serialize generator route to dict."""
        conn = ModConnection(
            source_bus=3, target_slot=2, target_param="resonance",
            depth=0.7, amount=0.6, offset=0.1, polarity=Polarity.UNI_POS, invert=True
        )
        data = conn.to_dict()
        assert data['source_bus'] == 3
        assert data['target_slot'] == 2
        assert data['target_param'] == "resonance"
        assert data['depth'] == 0.7
        assert data['amount'] == 0.6
        assert data['offset'] == 0.1
        assert data['polarity'] == 1  # UNI_POS value
        assert data['invert'] is True
        assert 'target_str' not in data

    def test_to_dict_extended(self):
        """Serialize extended route to dict."""
        conn = ModConnection(
            source_bus=8, target_str="chan:3:pan",
            amount=0.8, offset=-0.2
        )
        data = conn.to_dict()
        assert data['source_bus'] == 8
        assert data['target_str'] == "chan:3:pan"
        assert 'target_slot' not in data
        assert 'target_param' not in data

    def test_from_dict_generator(self):
        """Deserialize generator route from dict."""
        data = {
            'source_bus': 4,
            'target_slot': 3,
            'target_param': 'frequency',
            'depth': 0.5,
            'amount': 0.7,
            'offset': 0.0,
            'polarity': 2,  # UNI_NEG
            'invert': False
        }
        conn = ModConnection.from_dict(data)
        assert conn.source_bus == 4
        assert conn.target_slot == 3
        assert conn.target_param == 'frequency'
        assert conn.polarity == Polarity.UNI_NEG

    def test_from_dict_extended(self):
        """Deserialize extended route from dict."""
        data = {
            'source_bus': 10,
            'target_str': 'mod:1:p2',
            'depth': 1.0,
            'amount': 0.5,
            'offset': 0.0,
            'polarity': 0,
        }
        conn = ModConnection.from_dict(data)
        assert conn.source_bus == 10
        assert conn.target_str == 'mod:1:p2'
        assert conn.is_extended is True

    def test_from_dict_negative_depth_migration(self):
        """Old presets with negative depth should migrate to positive depth + invert."""
        data = {
            'source_bus': 0,
            'target_slot': 1,
            'target_param': 'cutoff',
            'depth': -0.6,  # Old format: negative = inverted
        }
        conn = ModConnection.from_dict(data)
        assert conn.depth == 0.6  # Absolute value
        assert conn.invert is True  # Migrated to invert flag


class TestModRoutingState:
    """Tests for ModRoutingState class."""

    def test_instantiation(self):
        """Can create ModRoutingState instance."""
        state = ModRoutingState()
        assert state is not None

    def test_initial_empty(self):
        """New state has no connections."""
        state = ModRoutingState()
        assert len(state) == 0

    def test_add_connection(self):
        """Add a connection."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
        result = state.add_connection(conn)
        assert result is True
        assert len(state) == 1

    def test_add_duplicate_returns_false(self):
        """Adding duplicate connection returns False."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
        state.add_connection(conn)
        result = state.add_connection(conn)
        assert result is False
        assert len(state) == 1

    def test_remove_connection(self):
        """Remove a connection."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
        state.add_connection(conn)
        result = state.remove_connection(0, target_slot=1, target_param="cutoff")
        assert result is True
        assert len(state) == 0

    def test_remove_nonexistent_returns_false(self):
        """Removing non-existent connection returns False."""
        state = ModRoutingState()
        result = state.remove_connection(0, target_slot=1, target_param="cutoff")
        assert result is False

    def test_get_connection(self):
        """Get a specific connection."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff", amount=0.8)
        state.add_connection(conn)
        retrieved = state.get_connection(0, target_slot=1, target_param="cutoff")
        assert retrieved is not None
        assert retrieved.amount == 0.8

    def test_get_connection_extended(self):
        """Get an extended connection."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=4, target_str="mod:2:p1", amount=0.6)
        state.add_connection(conn)
        retrieved = state.get_connection(4, target_str="mod:2:p1")
        assert retrieved is not None
        assert retrieved.amount == 0.6

    def test_update_connection(self):
        """Update connection parameters."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff", amount=0.5)
        state.add_connection(conn)
        result = state.update_connection(0, target_slot=1, target_param="cutoff", amount=0.9)
        assert result is True
        updated = state.get_connection(0, target_slot=1, target_param="cutoff")
        assert updated.amount == 0.9

    def test_clear(self):
        """Clear all connections."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_slot=2, target_param="freq"))
        state.clear()
        assert len(state) == 0

    def test_get_connections_for_bus(self):
        """Get all connections from a specific bus."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=0, target_slot=2, target_param="freq"))
        state.add_connection(ModConnection(source_bus=1, target_slot=1, target_param="cutoff"))
        conns = state.get_connections_for_bus(0)
        assert len(conns) == 2

    def test_get_connections_for_target(self):
        """Get all connections to a specific target slot."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_slot=1, target_param="freq"))
        state.add_connection(ModConnection(source_bus=2, target_slot=2, target_param="cutoff"))
        conns = state.get_connections_for_target(target_slot=1)
        assert len(conns) == 2

    def test_get_generator_connections(self):
        """Get only generator (non-extended) connections."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_str="mod:1:p1"))
        gen_conns = state.get_generator_connections()
        assert len(gen_conns) == 1
        assert gen_conns[0].target_slot == 1

    def test_get_extended_connections(self):
        """Get only extended connections."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_str="mod:1:p1"))
        ext_conns = state.get_extended_connections()
        assert len(ext_conns) == 1
        assert ext_conns[0].target_str == "mod:1:p1"

    def test_get_all_connections(self):
        """Get all connections."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_str="mod:1:p1"))
        all_conns = state.get_all_connections()
        assert len(all_conns) == 2

    def test_contains(self):
        """Test __contains__ method."""
        state = ModRoutingState()
        conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
        state.add_connection(conn)
        assert conn.key in state
        assert "nonexistent" not in state


class TestDefaultRouteParams:
    """Tests for default route parameter helpers."""

    def test_default_route_params_values(self):
        """Check DEFAULT_ROUTE_PARAMS values."""
        assert DEFAULT_ROUTE_PARAMS['depth'] == 1.0
        assert DEFAULT_ROUTE_PARAMS['amount'] == 0.5
        assert DEFAULT_ROUTE_PARAMS['offset'] == 0.0
        assert DEFAULT_ROUTE_PARAMS['polarity'] == 0
        assert DEFAULT_ROUTE_PARAMS['invert'] is False

    def test_make_default_route_params(self):
        """make_default_route_params returns a copy."""
        params1 = make_default_route_params()
        params2 = make_default_route_params()
        params1['amount'] = 0.9
        assert params2['amount'] == 0.5  # Unchanged

    def test_create_default_connection_generator(self):
        """create_default_connection for generator route."""
        conn = create_default_connection(0, target_slot=1, target_param="cutoff")
        assert conn.source_bus == 0
        assert conn.target_slot == 1
        assert conn.target_param == "cutoff"
        assert conn.amount == 0.5
        assert conn.polarity == Polarity.BIPOLAR

    def test_create_default_connection_extended(self):
        """create_default_connection for extended route."""
        conn = create_default_connection(4, target_str="send:1:ec")
        assert conn.source_bus == 4
        assert conn.target_str == "send:1:ec"
        assert conn.is_extended is True


class TestExtendedTargetValidation:
    """Tests for extended target validation."""

    def test_valid_mod_target(self):
        """mod:slot:param targets are valid."""
        assert is_valid_ext_target("mod:1:p1") is True
        assert is_valid_ext_target("mod:4:p4") is True

    def test_valid_send_target(self):
        """send:slot:type targets are valid."""
        assert is_valid_ext_target("send:1:ec") is True
        assert is_valid_ext_target("send:8:vb") is True

    def test_valid_chan_target(self):
        """chan:slot:param targets are valid."""
        assert is_valid_ext_target("chan:1:pan") is True
        assert is_valid_ext_target("chan:8:pan") is True

    def test_invalid_target(self):
        """Invalid target strings return False."""
        assert is_valid_ext_target("invalid") is False
        assert is_valid_ext_target("mod:99:p1") is False
        assert is_valid_ext_target("fx:heat:drive") is False  # Not in current valid set

    def test_extended_params_count(self):
        """EXTENDED_PARAMS should have expected count."""
        # 16 mod params + 24 chan params = 40
        assert len(EXTENDED_PARAMS) == 40
        assert len(VALID_EXT_TARGETS) == 40
