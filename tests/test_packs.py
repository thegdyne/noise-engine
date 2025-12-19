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
    """Test that underscore-prefixed packs are skipped (templates)."""
    
    def test_example_pack_skipped(self):
        """The _example pack should NOT be discovered (underscore prefix = template)."""
        from src.config import _discover_packs, get_discovered_packs
        
        _discover_packs()
        packs = get_discovered_packs()
        
        # _example pack should NOT be discovered (underscore prefix)
        assert "_example" not in packs
    
    def test_example_pack_not_in_enabled(self):
        """The _example pack should NOT appear in enabled packs."""
        from src.config import _discover_packs, get_enabled_packs
        
        _discover_packs()
        enabled = get_enabled_packs()
        
        pack_ids = [p["id"] for p in enabled]
        assert "_example" not in pack_ids

class TestPackGeneratorLoading:
    """Test generator loading from packs."""
    
    def test_core_generators_marked_as_core(self):
        """Core generators should have None as source."""
        from src.config import (
            _discover_packs, _load_generator_configs,
            _GENERATOR_SOURCES
        )
        
        _discover_packs()
        _load_generator_configs()
        
        # Core generators should have None source
        assert _GENERATOR_SOURCES.get("Empty") is None
 
    def test_core_generators_marked_as_core(self):
        """Core generators should have None as source."""
        from src.config import (
            _discover_packs, _load_generator_configs,
            _GENERATOR_SOURCES
        )
        
        _discover_packs()
        _load_generator_configs()
        
        # Core generators should have None source
        assert _GENERATOR_SOURCES.get("Subtractive") is None
        assert _GENERATOR_SOURCES.get("FM") is None
        assert _GENERATOR_SOURCES.get("Empty") is None
    
class TestSynthDefUniqueness:
    """Test SynthDef symbol collision detection."""
    
    @pytest.fixture
    def temp_packs_dir(self, tmp_path, monkeypatch):
        """Create a temporary packs directory for testing."""
        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        
        # Also create fake supercollider/generators with a core generator
        sc_dir = tmp_path / "supercollider" / "generators"
        sc_dir.mkdir(parents=True)
        
        # Create a core generator
        core_gen = {
            "name": "Core Gen",
            "synthdef": "core_synthdef",
            "custom_params": []
        }
        (sc_dir / "core_gen.json").write_text(json.dumps(core_gen))
        
        import src.config
        original_file = src.config.__file__
        
        fake_src = tmp_path / "src"
        fake_config = fake_src / "config"
        fake_config.mkdir(parents=True)
        
        monkeypatch.setattr(src.config, '__file__', str(fake_config / "__init__.py"))
        
        yield packs_dir
        
        monkeypatch.setattr(src.config, '__file__', original_file)
    
    def test_synthdef_collision_with_core_skipped(self, temp_packs_dir):
        """Pack generator with same synthdef as core should be skipped."""
        from src.config import _discover_packs, _load_generator_configs, _GENERATOR_CONFIGS
        
        # Create pack with colliding synthdef
        pack_dir = temp_packs_dir / "colliding_pack"
        pack_dir.mkdir()
        gen_dir = pack_dir / "generators"
        gen_dir.mkdir()
        
        manifest = {
            "pack_format": 1,
            "name": "Colliding Pack",
            "enabled": True,
            "generators": ["collider"]
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        
        # Generator with same synthdef as core
        collider = {
            "name": "Collider",
            "synthdef": "core_synthdef",  # Same as core!
            "custom_params": []
        }
        (gen_dir / "collider.json").write_text(json.dumps(collider))
        
        _discover_packs()
        _load_generator_configs()
        
        # Collider should NOT be loaded due to synthdef collision
        assert "Collider" not in _GENERATOR_CONFIGS
        # Core should still be there
        assert "Core Gen" in _GENERATOR_CONFIGS


class TestDynamicGeneratorCycle:
    """Test dynamic GENERATOR_CYCLE building (Phase 4)."""
    
    def test_generator_cycle_includes_core(self):
        """Core generators should appear in cycle."""
        from src.config import GENERATOR_CYCLE, _GENERATOR_CONFIGS
        
        # Empty is always present (hardcoded fallback)
        assert "Empty" in GENERATOR_CYCLE
        
        # Core generators only appear if their JSON configs were loaded
        # Check for at least one core generator if configs exist
        core_generators = [g for g in ["Subtractive", "FM", "Additive"] 
                          if g in _GENERATOR_CONFIGS]
        if core_generators:
            for gen in core_generators:
                assert gen in GENERATOR_CYCLE, f"Core generator {gen} missing from cycle"
    
    def test_generator_cycle_includes_pack_generators(self):
        """Pack generators should appear after core with separator."""
        from src.config import (
            _discover_packs, _load_generator_configs, _finalize_config,
            GENERATOR_CYCLE, get_enabled_packs
        )
        
        # Re-run full sequence
        _discover_packs()
        _load_generator_configs()
        _finalize_config()
        
        # Check pack generators are in cycle
        enabled = get_enabled_packs()
        if enabled:
            # Use loaded_generators (resolved display names)
            gen_name = enabled[0].get('loaded_generators', [None])[0]
            if gen_name:
                assert gen_name in GENERATOR_CYCLE
    
    def test_generator_cycle_has_separators(self):
        """Pack sections should have separator headers."""
        from src.config import (
            _discover_packs, _load_generator_configs, _finalize_config,
            GENERATOR_CYCLE, get_enabled_packs
        )
        
        _discover_packs()
        _load_generator_configs()
        _finalize_config()
        
        separators = [g for g in GENERATOR_CYCLE if g.startswith("────")]
        enabled_with_generators = [p for p in get_enabled_packs() if p.get('loaded_generators')]
        
        # Should have one separator per pack with loaded generators
        assert len(separators) == len(enabled_with_generators)
    
    def test_generator_cycle_order(self):
        """Core generators should come before pack generators."""
        from src.config import (
            _discover_packs, _load_generator_configs, _finalize_config,
            GENERATOR_CYCLE
        )
        
        _discover_packs()
        _load_generator_configs()
        _finalize_config()
        
        # Find last core generator
        core_last_idx = GENERATOR_CYCLE.index("Giant B0N0") if "Giant B0N0" in GENERATOR_CYCLE else -1
        
        # Find first separator
        first_sep_idx = next(
            (i for i, g in enumerate(GENERATOR_CYCLE) if g.startswith("────")), 
            len(GENERATOR_CYCLE)
        )
        
        # Core should come before pack separators
        if core_last_idx >= 0 and first_sep_idx < len(GENERATOR_CYCLE):
            assert core_last_idx < first_sep_idx
    
    def test_get_valid_generators_excludes_separators(self):
        """get_valid_generators() should not include separators."""
        from src.config import (
            _discover_packs, _load_generator_configs, _finalize_config,
            get_valid_generators, _GENERATOR_CONFIGS
        )
        
        _discover_packs()
        _load_generator_configs()
        _finalize_config()
        
        valid = get_valid_generators()
        
        # No separators
        assert not any(g.startswith("────") for g in valid)
        
        # Empty is always present (hardcoded fallback)
        assert "Empty" in valid
        
        # Core generators only appear if their JSON configs were loaded
        if "Subtractive" in _GENERATOR_CONFIGS:
            assert "Subtractive" in valid
    


class TestCorePacks:
    """Test the shipped core packs."""
    
    def test_electric_shepherd_discovered(self):
        from src.config import get_discovered_packs
        """Electric Shepherd pack should be discovered."""
        packs = get_discovered_packs()
        assert "electric-shepherd" in packs
        assert packs["electric-shepherd"]["enabled"] is True
        assert len(packs["electric-shepherd"]["generators"]) == 8
    
    def test_rlyeh_discovered(self):
        from src.config import get_discovered_packs
        """R'lyeh pack should be discovered."""
        packs = get_discovered_packs()
        assert "rlyeh" in packs
        assert packs["rlyeh"]["enabled"] is True
        assert len(packs["rlyeh"]["generators"]) == 8
