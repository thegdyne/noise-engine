"""
Tests for pack discovery system (Phase 2)
"""

import json
import os
import shutil
import tempfile
import pytest


class TestPackDiscovery:
    """Test pack discovery functionality."""
    
    @pytest.fixture
    def temp_packs_dir(self, tmp_path, monkeypatch):
        """Create a temporary packs directory for testing."""
        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        
        # Patch the project directory detection
        # We need to make _discover_packs look in our temp dir
        import src.config
        original_file = src.config.__file__
        
        # Create fake project structure
        fake_src = tmp_path / "src"
        fake_config = fake_src / "config"
        fake_config.mkdir(parents=True)
        
        # Monkeypatch __file__ to point to our fake location
        monkeypatch.setattr(src.config, '__file__', str(fake_config / "__init__.py"))
        
        yield packs_dir
        
        # Restore
        monkeypatch.setattr(src.config, '__file__', original_file)
    
    def test_discover_packs_empty(self, temp_packs_dir):
        """Empty packs directory should return empty dict."""
        from src.config import _discover_packs, _PACK_CONFIGS
        
        result = _discover_packs()
        
        assert result == {}
        assert _PACK_CONFIGS == {}
    
    def test_discover_packs_valid(self, temp_packs_dir):
        """Valid pack should be discovered."""
        from src.config import _discover_packs
        
        # Create a valid pack
        pack_dir = temp_packs_dir / "test_pack"
        pack_dir.mkdir()
        generators_dir = pack_dir / "generators"
        generators_dir.mkdir()
        
        manifest = {
            "pack_format": 1,
            "name": "Test Pack",
            "version": "1.0.0",
            "author": "Test Author",
            "enabled": True,
            "generators": ["test_gen"]
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        
        result = _discover_packs()
        
        assert "test_pack" in result
        assert result["test_pack"]["display_name"] == "Test Pack"
        assert result["test_pack"]["version"] == "1.0.0"
        assert result["test_pack"]["enabled"] is True
        assert result["test_pack"]["generators"] == ["test_gen"]
    
    def test_discover_packs_missing_manifest(self, temp_packs_dir):
        """Pack without manifest.json should be skipped."""
        from src.config import _discover_packs
        
        # Create pack without manifest
        pack_dir = temp_packs_dir / "no_manifest_pack"
        pack_dir.mkdir()
        
        result = _discover_packs()
        
        assert "no_manifest_pack" not in result
    
    def test_discover_packs_invalid_json(self, temp_packs_dir):
        """Pack with invalid JSON should be skipped."""
        from src.config import _discover_packs
        
        pack_dir = temp_packs_dir / "bad_json_pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text("{ invalid json }")
        
        result = _discover_packs()
        
        assert "bad_json_pack" not in result
    
    def test_discover_packs_missing_required_fields(self, temp_packs_dir):
        """Pack missing required fields should be skipped."""
        from src.config import _discover_packs
        
        pack_dir = temp_packs_dir / "incomplete_pack"
        pack_dir.mkdir()
        
        # Missing 'generators' field
        manifest = {
            "pack_format": 1,
            "name": "Incomplete",
            "enabled": True
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        
        result = _discover_packs()
        
        assert "incomplete_pack" not in result
    
    def test_discover_packs_wrong_format_version(self, temp_packs_dir):
        """Pack with unsupported format version should be skipped."""
        from src.config import _discover_packs
        
        pack_dir = temp_packs_dir / "future_pack"
        pack_dir.mkdir()
        
        manifest = {
            "pack_format": 99,  # Unsupported version
            "name": "Future Pack",
            "enabled": True,
            "generators": []
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        
        result = _discover_packs()
        
        assert "future_pack" not in result
    
    def test_discover_packs_disabled(self, temp_packs_dir):
        """Disabled pack should be discovered but marked disabled."""
        from src.config import _discover_packs
        
        pack_dir = temp_packs_dir / "disabled_pack"
        pack_dir.mkdir()
        
        manifest = {
            "pack_format": 1,
            "name": "Disabled Pack",
            "enabled": False,
            "generators": ["gen1"]
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        
        result = _discover_packs()
        
        assert "disabled_pack" in result
        assert result["disabled_pack"]["enabled"] is False
    
    def test_discover_packs_skips_hidden(self, temp_packs_dir):
        """Hidden directories (starting with .) should be skipped."""
        from src.config import _discover_packs
        
        hidden_dir = temp_packs_dir / ".hidden_pack"
        hidden_dir.mkdir()
        
        manifest = {
            "pack_format": 1,
            "name": "Hidden Pack",
            "enabled": True,
            "generators": []
        }
        (hidden_dir / "manifest.json").write_text(json.dumps(manifest))
        
        result = _discover_packs()
        
        assert ".hidden_pack" not in result
    
    def test_discover_packs_alphabetical_order(self, temp_packs_dir):
        """Packs should be discovered in alphabetical order."""
        from src.config import _discover_packs
        
        for name in ["zebra_pack", "alpha_pack", "middle_pack"]:
            pack_dir = temp_packs_dir / name
            pack_dir.mkdir()
            manifest = {
                "pack_format": 1,
                "name": name.title(),
                "enabled": True,
                "generators": []
            }
            (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        
        result = _discover_packs()
        
        pack_ids = list(result.keys())
        assert pack_ids == ["alpha_pack", "middle_pack", "zebra_pack"]


class TestPackAPI:
    """Test pack public API functions."""
    
    @pytest.fixture
    def temp_packs_dir(self, tmp_path, monkeypatch):
        """Create a temporary packs directory for testing."""
        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        
        import src.config
        original_file = src.config.__file__
        
        fake_src = tmp_path / "src"
        fake_config = fake_src / "config"
        fake_config.mkdir(parents=True)
        
        monkeypatch.setattr(src.config, '__file__', str(fake_config / "__init__.py"))
        
        yield packs_dir
        
        monkeypatch.setattr(src.config, '__file__', original_file)
    
    def test_get_discovered_packs_returns_copy(self, temp_packs_dir):
        """get_discovered_packs should return a copy, not the original."""
        from src.config import _discover_packs, get_discovered_packs, _PACK_CONFIGS
        
        pack_dir = temp_packs_dir / "test_pack"
        pack_dir.mkdir()
        manifest = {
            "pack_format": 1,
            "name": "Test",
            "enabled": True,
            "generators": []
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        
        _discover_packs()
        
        result = get_discovered_packs()
        result["modified"] = "should not affect original"
        
        assert "modified" not in _PACK_CONFIGS
    
    def test_get_enabled_packs_filters(self, temp_packs_dir):
        """get_enabled_packs should only return enabled packs."""
        from src.config import _discover_packs, get_enabled_packs
        
        # Create enabled pack
        enabled_dir = temp_packs_dir / "enabled_pack"
        enabled_dir.mkdir()
        (enabled_dir / "manifest.json").write_text(json.dumps({
            "pack_format": 1,
            "name": "Enabled",
            "enabled": True,
            "generators": []
        }))
        
        # Create disabled pack
        disabled_dir = temp_packs_dir / "disabled_pack"
        disabled_dir.mkdir()
        (disabled_dir / "manifest.json").write_text(json.dumps({
            "pack_format": 1,
            "name": "Disabled",
            "enabled": False,
            "generators": []
        }))
        
        _discover_packs()
        
        enabled = get_enabled_packs()
        
        assert len(enabled) == 1
        assert enabled[0]["id"] == "enabled_pack"
    
    def test_get_generator_source_none_for_unknown(self):
        """get_generator_source should return None for unknown generators."""
        from src.config import get_generator_source
        
        result = get_generator_source("nonexistent_generator")
        
        assert result is None


class TestExamplePackDiscovery:
    """Test that the shipped _example pack is discovered correctly."""
    
    def test_example_pack_discovered(self):
        """The _example pack should be discoverable."""
        from src.config import _discover_packs, get_discovered_packs
        
        # Re-run discovery to pick up actual packs
        _discover_packs()
        packs = get_discovered_packs()
        
        # _example pack should exist (from Phase 1)
        assert "_example" in packs
        assert packs["_example"]["display_name"] == "Example Pack"
        assert packs["_example"]["enabled"] is True
        assert "sine_drone" in packs["_example"]["generators"]
        assert "pulse_bass" in packs["_example"]["generators"]
    
    def test_example_pack_in_enabled(self):
        """The _example pack should appear in enabled packs."""
        from src.config import _discover_packs, get_enabled_packs
        
        _discover_packs()
        enabled = get_enabled_packs()
        
        pack_ids = [p["id"] for p in enabled]
        assert "_example" in pack_ids
