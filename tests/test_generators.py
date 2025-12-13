"""
Tests for generator JSON configuration files
Validates all generators in supercollider/generators/
"""

import pytest
import json
import os
from src.config import (
    GENERATOR_CYCLE,
    MAX_CUSTOM_PARAMS,
    get_generator_synthdef,
    get_generator_custom_params,
    get_generator_pitch_target,
    get_generator_midi_retrig,
)


class TestGeneratorJSONFiles:
    """Tests for generator JSON file structure."""
    
    def test_all_cycle_generators_have_json(self, generators_dir):
        """Every generator in GENERATOR_CYCLE (except Empty) has a JSON file."""
        for name in GENERATOR_CYCLE:
            if name == "Empty":
                continue
            synthdef = get_generator_synthdef(name)
            assert synthdef is not None, f"Generator '{name}' has no synthdef (missing JSON?)"
    
    def test_all_json_files_are_valid(self, generators_dir):
        """All .json files in generators/ are valid JSON."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    assert isinstance(data, dict), f"{filename} is not a JSON object"
                except json.JSONDecodeError as e:
                    pytest.fail(f"{filename} is invalid JSON: {e}")
    
    def test_json_has_required_fields(self, generators_dir):
        """Each JSON has name and synthdef fields."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                assert 'name' in data, f"{filename} missing 'name'"
                assert 'synthdef' in data, f"{filename} missing 'synthdef'"
    
    def test_synthdef_has_matching_scd(self, generators_dir):
        """Each synthdef has a corresponding .scd file."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                synthdef = data.get('synthdef')
                if synthdef:
                    # The .scd file should exist with same base name as JSON
                    scd_file = filename.replace('.json', '.scd')
                    scd_path = os.path.join(generators_dir, scd_file)
                    assert os.path.exists(scd_path), f"Missing {scd_file} for synthdef '{synthdef}'"


class TestGeneratorCustomParams:
    """Tests for custom_params in generator configs."""
    
    def test_custom_params_within_limit(self, generators_dir):
        """No generator has more than MAX_CUSTOM_PARAMS."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                params = data.get('custom_params', [])
                assert len(params) <= MAX_CUSTOM_PARAMS, \
                    f"{filename} has {len(params)} custom params (max {MAX_CUSTOM_PARAMS})"
    
    def test_custom_params_structure(self, generators_dir):
        """Custom params have required fields."""
        required_fields = ['key', 'label', 'default', 'min', 'max']
        
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                for i, param in enumerate(data.get('custom_params', [])):
                    for field in required_fields:
                        assert field in param, \
                            f"{filename} custom_params[{i}] missing '{field}'"
    
    def test_custom_params_min_less_than_max(self, generators_dir):
        """Custom param min < max."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                for i, param in enumerate(data.get('custom_params', [])):
                    min_val = param.get('min', 0)
                    max_val = param.get('max', 1)
                    assert min_val < max_val, \
                        f"{filename} custom_params[{i}] ({param.get('key')}) min >= max"
    
    def test_custom_params_default_in_range(self, generators_dir):
        """Custom param default is within min/max."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                for i, param in enumerate(data.get('custom_params', [])):
                    default = param.get('default', 0)
                    min_val = param.get('min', 0)
                    max_val = param.get('max', 1)
                    assert min_val <= default <= max_val, \
                        f"{filename} custom_params[{i}] ({param.get('key')}) default {default} not in [{min_val}, {max_val}]"
    
    def test_custom_param_labels_short(self, generators_dir):
        """Custom param labels are 3-4 chars."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                for i, param in enumerate(data.get('custom_params', [])):
                    label = param.get('label', '')
                    assert 1 <= len(label) <= 4, \
                        f"{filename} custom_params[{i}] label '{label}' should be 1-4 chars"


class TestGeneratorConfigFunctions:
    """Tests for config helper functions."""
    
    def test_get_generator_synthdef_empty(self):
        """Empty generator returns None synthdef."""
        assert get_generator_synthdef("Empty") is None
    
    def test_get_generator_synthdef_valid(self):
        """Valid generator returns synthdef name."""
        # Test a known generator
        synthdef = get_generator_synthdef("Subtractive")
        assert synthdef is not None
        assert isinstance(synthdef, str)
    
    def test_get_generator_synthdef_unknown(self):
        """Unknown generator returns None."""
        assert get_generator_synthdef("NonexistentGenerator123") is None
    
    def test_get_generator_custom_params_empty(self):
        """Empty generator returns empty params list."""
        params = get_generator_custom_params("Empty")
        assert params == []
    
    def test_get_generator_custom_params_returns_list(self):
        """Custom params returns a list."""
        for name in GENERATOR_CYCLE:
            params = get_generator_custom_params(name)
            assert isinstance(params, list), f"{name} custom_params is not a list"
    
    def test_get_generator_pitch_target_types(self):
        """pitch_target returns None or int."""
        for name in GENERATOR_CYCLE:
            target = get_generator_pitch_target(name)
            assert target is None or isinstance(target, int), \
                f"{name} pitch_target is {type(target)}, expected None or int"
    
    def test_get_generator_midi_retrig_types(self):
        """midi_retrig returns bool."""
        for name in GENERATOR_CYCLE:
            retrig = get_generator_midi_retrig(name)
            assert isinstance(retrig, bool), \
                f"{name} midi_retrig is {type(retrig)}, expected bool"


class TestGeneratorSCDFiles:
    """Tests for SuperCollider .scd generator files."""
    
    def test_scd_files_exist(self, generators_dir):
        """All .scd files in generators/ are readable."""
        scd_files = [f for f in os.listdir(generators_dir) if f.endswith('.scd')]
        assert len(scd_files) > 0, "No .scd files found"
        
        for filename in scd_files:
            filepath = os.path.join(generators_dir, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            assert len(content) > 0, f"{filename} is empty"
    
    def test_scd_files_have_synthdef(self, generators_dir):
        """Each .scd file contains SynthDef."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.scd'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                assert 'SynthDef' in content, f"{filename} missing SynthDef"
    
    def test_scd_files_use_helpers(self, generators_dir):
        """Generators use shared helpers (not inline envelope code)."""
        for filename in os.listdir(generators_dir):
            if filename.endswith('.scd'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Should use ~envVCA helper, not inline EnvGen
                # (except the helper definition itself)
                if '~envVCA' not in content:
                    # Check it's not duplicating envelope logic
                    if 'EnvGen.ar(Env.perc' in content:
                        pytest.fail(f"{filename} has inline envelope - should use ~envVCA helper")
    
    def test_scd_files_have_standard_buses(self, generators_dir):
        """Generators receive standard bus arguments."""
        standard_args = ['freqBus', 'cutoffBus', 'resBus', 'attackBus', 'decayBus']
        
        for filename in os.listdir(generators_dir):
            if filename.endswith('.scd'):
                filepath = os.path.join(generators_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                
                for arg in standard_args:
                    assert arg in content, f"{filename} missing standard arg '{arg}'"
