"""
Tests for ModRoutingState synchronization and preset loading.

PyQt5 mock is set up in conftest.py to avoid StopIteration errors.
"""

import pytest
from src.gui.mod_routing_state import (
    ModConnection,
    ModRoutingState,
    Polarity,
)


class TestToDict:
    """Tests for ModRoutingState.to_dict() serialization."""

    def test_empty_state_to_dict(self):
        """Empty state serializes to empty lists."""
        state = ModRoutingState()
        data = state.to_dict()
        assert data['connections'] == []
        assert data['ext_mod_routes'] == []

    def test_generator_routes_in_connections(self):
        """Generator routes go into 'connections' key."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_slot=2, target_param="freq"))
        data = state.to_dict()
        assert len(data['connections']) == 2
        assert len(data['ext_mod_routes']) == 0

    def test_extended_routes_in_ext_mod_routes(self):
        """Extended routes go into 'ext_mod_routes' key."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_str="mod:1:p1"))
        state.add_connection(ModConnection(source_bus=1, target_str="send:2:ec"))
        data = state.to_dict()
        assert len(data['connections']) == 0
        assert len(data['ext_mod_routes']) == 2

    def test_mixed_routes_separated(self):
        """Generator and extended routes are separated correctly."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_str="mod:1:p1"))
        data = state.to_dict()
        assert len(data['connections']) == 1
        assert len(data['ext_mod_routes']) == 1


class TestFromDict:
    """Tests for ModRoutingState.from_dict() deserialization."""

    def test_load_empty(self):
        """Loading empty data results in empty state."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.from_dict({'connections': [], 'ext_mod_routes': []})
        assert len(state) == 0

    def test_load_generator_routes(self):
        """Load generator routes from connections key."""
        state = ModRoutingState()
        data = {
            'connections': [
                {'source_bus': 0, 'target_slot': 1, 'target_param': 'cutoff', 'depth': 1.0, 'amount': 0.5},
                {'source_bus': 2, 'target_slot': 3, 'target_param': 'freq', 'depth': 0.8, 'amount': 0.7},
            ],
            'ext_mod_routes': []
        }
        state.from_dict(data)
        assert len(state) == 2
        assert len(state.get_generator_connections()) == 2

    def test_load_extended_routes(self):
        """Load extended routes from ext_mod_routes key."""
        state = ModRoutingState()
        data = {
            'connections': [],
            'ext_mod_routes': [
                {'source_bus': 0, 'target_str': 'mod:1:p1', 'depth': 1.0, 'amount': 0.5},
                {'source_bus': 4, 'target_str': 'send:2:ec', 'depth': 1.0, 'amount': 0.6},
            ]
        }
        state.from_dict(data)
        assert len(state) == 2
        assert len(state.get_extended_connections()) == 2

    def test_load_legacy_ext_connections(self):
        """Load extended routes from legacy 'ext_connections' key."""
        state = ModRoutingState()
        data = {
            'connections': [],
            'ext_connections': [  # Legacy key
                {'source_bus': 0, 'target_str': 'mod:1:p1', 'depth': 1.0, 'amount': 0.5},
            ]
        }
        state.from_dict(data)
        assert len(state.get_extended_connections()) == 1

    def test_load_replaces_existing(self):
        """Loading replaces all existing connections."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_slot=2, target_param="freq"))

        data = {
            'connections': [
                {'source_bus': 5, 'target_slot': 6, 'target_param': 'resonance', 'depth': 1.0, 'amount': 0.5},
            ],
            'ext_mod_routes': []
        }
        state.from_dict(data)
        assert len(state) == 1
        conn = state.get_connection(5, target_slot=6, target_param='resonance')
        assert conn is not None


class TestLoadFromPreset:
    """Tests for ModRoutingState.load_from_preset() with delta tracking."""

    def test_load_from_preset_returns_deltas(self):
        """load_from_preset returns removal and addition lists."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))

        data = {
            'connections': [
                {'source_bus': 2, 'target_slot': 3, 'target_param': 'freq', 'depth': 1.0, 'amount': 0.5},
            ],
            'ext_mod_routes': []
        }
        removed_gen, removed_ext, added_gen, added_ext = state.load_from_preset(data)

        assert len(removed_gen) == 1  # Old connection removed
        assert len(removed_ext) == 0
        assert len(added_gen) == 1    # New connection added
        assert len(added_ext) == 0

    def test_load_from_preset_empty_removes_all(self):
        """Loading empty preset removes all existing connections."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_str="mod:1:p1"))

        removed_gen, removed_ext, added_gen, added_ext = state.load_from_preset({})

        assert len(removed_gen) == 1
        assert len(removed_ext) == 1
        assert len(added_gen) == 0
        assert len(added_ext) == 0
        assert len(state) == 0

    def test_load_from_preset_mixed_deltas(self):
        """Load preset with both generator and extended routes."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_str="mod:1:p1"))

        data = {
            'connections': [
                {'source_bus': 2, 'target_slot': 3, 'target_param': 'freq', 'depth': 1.0, 'amount': 0.5},
            ],
            'ext_mod_routes': [
                {'source_bus': 4, 'target_str': 'send:2:ec', 'depth': 1.0, 'amount': 0.6},
            ]
        }
        removed_gen, removed_ext, added_gen, added_ext = state.load_from_preset(data)

        assert len(removed_gen) == 1
        assert len(removed_ext) == 1
        assert len(added_gen) == 1
        assert len(added_ext) == 1


class TestGetAllKeys:
    """Tests for ModRoutingState.get_all_keys()."""

    def test_get_all_keys_empty(self):
        """Empty state returns empty sets."""
        state = ModRoutingState()
        gen_keys, ext_keys = state.get_all_keys()
        assert len(gen_keys) == 0
        assert len(ext_keys) == 0

    def test_get_all_keys_separated(self):
        """Keys are separated by route type."""
        state = ModRoutingState()
        state.add_connection(ModConnection(source_bus=0, target_slot=1, target_param="cutoff"))
        state.add_connection(ModConnection(source_bus=1, target_str="mod:1:p1"))

        gen_keys, ext_keys = state.get_all_keys()

        assert len(gen_keys) == 1
        assert len(ext_keys) == 1
        assert "0_1_cutoff" in gen_keys
        assert "1_mod:1:p1" in ext_keys
