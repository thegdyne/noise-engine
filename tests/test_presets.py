"""
Tests for preset system.
"""

import pytest
import json
import tempfile
from pathlib import Path

from src.presets import (
    PresetState,
    SlotState,
    ChannelState,
    MixerState,
    PresetManager,
    PresetError,
    validate_preset,
    PRESET_VERSION,
)


class TestSlotState:
    """Tests for SlotState dataclass."""
    
    def test_default_values(self):
        """Default slot state has expected values."""
        slot = SlotState()
        assert slot.generator is None
        assert slot.frequency == 0.5
        assert slot.cutoff == 0.5
        assert slot.filter_type == 0
        assert slot.env_source == 0
        assert slot.clock_rate == 4
        assert slot.midi_channel == 1
    
    def test_to_dict(self):
        """SlotState serializes to dict correctly."""
        slot = SlotState(generator="Subtractive", frequency=0.7, cutoff=0.3)
        d = slot.to_dict()
        assert d["generator"] == "Subtractive"
        assert d["params"]["frequency"] == 0.7
        assert d["params"]["cutoff"] == 0.3
    
    def test_from_dict(self):
        """SlotState deserializes from dict correctly."""
        d = {
            "generator": "FM",
            "params": {"frequency": 0.8, "cutoff": 0.2},
            "filter_type": 1,
            "env_source": 2,
        }
        slot = SlotState.from_dict(d)
        assert slot.generator == "FM"
        assert slot.frequency == 0.8
        assert slot.cutoff == 0.2
        assert slot.filter_type == 1
        assert slot.env_source == 2
    
    def test_round_trip(self):
        """SlotState survives dict round-trip."""
        original = SlotState(
            generator="Karplus",
            frequency=0.123,
            cutoff=0.456,
            custom_0=0.789,
            filter_type=2,
            env_source=1,
            clock_rate=7,
            midi_channel=5,
        )
        restored = SlotState.from_dict(original.to_dict())
        assert restored.generator == original.generator
        assert restored.frequency == original.frequency
        assert restored.custom_0 == original.custom_0
        assert restored.filter_type == original.filter_type


class TestPresetState:
    """Tests for PresetState dataclass."""
    
    def test_default_has_8_slots(self):
        """Default preset has 8 empty slots."""
        preset = PresetState()
        assert len(preset.slots) == 8
        for slot in preset.slots:
            assert slot.generator is None
    
    def test_to_json(self):
        """PresetState serializes to valid JSON."""
        preset = PresetState(name="Test Preset")
        preset.slots[0] = SlotState(generator="Subtractive")
        
        json_str = preset.to_json()
        data = json.loads(json_str)
        
        assert data["name"] == "Test Preset"
        assert data["slots"][0]["generator"] == "Subtractive"
        assert len(data["slots"]) == 8
    
    def test_from_json(self):
        """PresetState deserializes from JSON correctly."""
        json_str = '''
        {
            "version": 1,
            "name": "Loaded Preset",
            "slots": [
                {"generator": "FM", "params": {"frequency": 0.5}, "filter_type": 0, "env_source": 0, "clock_rate": 4, "midi_channel": 1}
            ],
            "mixer": {"channels": [], "master_volume": 0.7}
        }
        '''
        preset = PresetState.from_json(json_str)
        assert preset.name == "Loaded Preset"
        assert preset.slots[0].generator == "FM"
        assert preset.mixer.master_volume == 0.7


class TestValidation:
    """Tests for preset validation."""
    
    def test_valid_preset(self):
        """Valid preset passes validation."""
        data = PresetState(name="Valid").to_dict()
        is_valid, errors = validate_preset(data)
        assert is_valid
        assert len(errors) == 0
    
    def test_missing_version(self):
        """Preset without version fails."""
        data = {"name": "No Version", "slots": []}
        is_valid, errors = validate_preset(data)
        assert not is_valid
        assert any("version" in e for e in errors)
    
    def test_future_version(self):
        """Preset with future version fails."""
        data = {"version": 999, "slots": []}
        is_valid, errors = validate_preset(data)
        assert not is_valid
        assert any("newer" in e for e in errors)
    
    def test_invalid_param_range(self):
        """Param outside 0-1 range fails."""
        data = PresetState().to_dict()
        data["slots"][0]["params"]["frequency"] = 1.5
        is_valid, errors = validate_preset(data)
        assert not is_valid
        assert any("frequency" in e for e in errors)
    
    def test_invalid_filter_type(self):
        """Invalid filter type fails."""
        data = PresetState().to_dict()
        data["slots"][0]["filter_type"] = 99
        is_valid, errors = validate_preset(data)
        assert not is_valid
        assert any("filter_type" in e for e in errors)


class TestPresetManager:
    """Tests for PresetManager save/load operations."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create PresetManager with temp directory."""
        return PresetManager(presets_dir=temp_dir)
    
    def test_save_creates_file(self, manager, temp_dir):
        """Save creates a JSON file."""
        preset = PresetState(name="Test")
        filepath = manager.save(preset)
        
        assert filepath.exists()
        assert filepath.suffix == ".json"
        assert filepath.parent == temp_dir
    
    def test_save_with_name(self, manager, temp_dir):
        """Save with name uses that name."""
        preset = PresetState(name="My Patch")
        filepath = manager.save(preset, name="my_patch")
        
        assert filepath.stem == "my_patch"
    
    def test_save_avoids_overwrite(self, manager, temp_dir):
        """Save doesn't overwrite existing file."""
        preset = PresetState(name="Test")
        
        path1 = manager.save(preset, name="same")
        path2 = manager.save(preset, name="same")
        
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()
    
    def test_load_returns_preset(self, manager):
        """Load returns PresetState."""
        original = PresetState(name="Original")
        original.slots[0] = SlotState(generator="FM", frequency=0.8)
        filepath = manager.save(original)
        
        loaded = manager.load(filepath)
        
        assert loaded.name == "Original"
        assert loaded.slots[0].generator == "FM"
        assert loaded.slots[0].frequency == 0.8
    
    def test_load_nonexistent_raises(self, manager, temp_dir):
        """Load raises for missing file."""
        with pytest.raises(PresetError) as exc:
            manager.load(temp_dir / "nonexistent.json")
        assert "not found" in str(exc.value)
    
    def test_load_invalid_json_raises(self, manager, temp_dir):
        """Load raises for invalid JSON."""
        bad_file = temp_dir / "bad.json"
        bad_file.write_text("not valid json {{{")
        
        with pytest.raises(PresetError) as exc:
            manager.load(bad_file)
        assert "Invalid JSON" in str(exc.value)
    
    def test_list_presets(self, manager, temp_dir):
        """List returns saved presets."""
        manager.save(PresetState(name="One"), name="one")
        manager.save(PresetState(name="Two"), name="two")
        
        presets = manager.list_presets()
        
        assert len(presets) == 2
        names = {p.stem for p in presets}
        assert "one" in names
        assert "two" in names
    
    def test_delete_preset(self, manager):
        """Delete removes preset file."""
        filepath = manager.save(PresetState(name="ToDelete"))
        assert filepath.exists()
        
        result = manager.delete(filepath)
        
        assert result is True
        assert not filepath.exists()
    
    def test_delete_nonexistent(self, manager, temp_dir):
        """Delete returns False for missing file."""
        result = manager.delete(temp_dir / "nonexistent.json")
        assert result is False


class TestMixerState:
    """Tests for MixerState."""
    
    def test_default_has_8_channels(self):
        """Default mixer has 8 channels."""
        mixer = MixerState()
        assert len(mixer.channels) == 8
    
    def test_channel_defaults(self):
        """Channels have expected defaults."""
        channel = ChannelState()
        assert channel.volume == 0.8
        assert channel.pan == 0.5
        assert channel.mute is False
        assert channel.solo is False
    
    def test_round_trip(self):
        """MixerState survives dict round-trip."""
        original = MixerState(master_volume=0.65)
        original.channels[0] = ChannelState(volume=0.3, pan=0.7, mute=True)
        
        restored = MixerState.from_dict(original.to_dict())
        
        assert restored.master_volume == 0.65
        assert restored.channels[0].volume == 0.3
        assert restored.channels[0].pan == 0.7
        assert restored.channels[0].mute is True
