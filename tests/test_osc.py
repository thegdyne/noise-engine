"""
Tests for OSC path consistency between Python and SuperCollider
Validates that paths used in Python match those handled in SC
"""

import pytest
import os
import re
from src.config import OSC_PATHS


class TestOSCPathFormat:
    """Tests for OSC path formatting conventions."""
    
    def test_all_paths_start_with_noise(self):
        """All paths use /noise/ prefix."""
        for key, path in OSC_PATHS.items():
            assert path.startswith('/noise/'), f"'{key}': '{path}' missing /noise/ prefix"
    
    def test_no_trailing_slash(self):
        """Paths don't end with slash."""
        for key, path in OSC_PATHS.items():
            assert not path.endswith('/'), f"'{key}': '{path}' has trailing slash"
    
    def test_no_double_slashes(self):
        """Paths don't have double slashes."""
        for key, path in OSC_PATHS.items():
            assert '//' not in path, f"'{key}': '{path}' has double slash"
    
    def test_lowercase_paths(self):
        """Path segments are lowercase or camelCase."""
        for key, path in OSC_PATHS.items():
            # Split path and check each segment
            segments = path.split('/')[1:]  # Skip empty first element
            for seg in segments:
                # Allow lowercase, numbers, and camelCase
                assert seg[0].islower() or seg[0].isdigit(), \
                    f"'{key}': segment '{seg}' should start lowercase"


class TestOSCPathsInSuperCollider:
    """Tests that Python OSC paths exist in SuperCollider code."""
    
    def get_all_sc_content(self, supercollider_dir):
        """Read all .scd files and return combined content."""
        content = ""
        for root, dirs, files in os.walk(supercollider_dir):
            for filename in files:
                if filename.endswith('.scd'):
                    filepath = os.path.join(root, filename)
                    with open(filepath, 'r') as f:
                        content += f.read() + "\n"
        return content
    
    def test_critical_paths_in_sc(self, supercollider_dir):
        """Critical OSC paths are handled in SuperCollider."""
        sc_content = self.get_all_sc_content(supercollider_dir)
        
        # These paths MUST be in SC for basic functionality
        critical_paths = [
            'start_generator',
            'stop_generator',
            'gen_frequency',
            'gen_cutoff',
            'gen_resonance',
            'gen_attack',
            'gen_decay',
            'gen_filter_type',
            'gen_env_source',
            'gen_clock_rate',
            'gen_trim',
            'clock_bpm',
            'ping',
            'heartbeat',
        ]
        
        for path_key in critical_paths:
            osc_path = OSC_PATHS[path_key]
            assert osc_path in sc_content, \
                f"Critical path '{osc_path}' not found in SC files"
    
    def test_gen_custom_path_in_sc(self, supercollider_dir):
        """Custom param path is handled in SC."""
        sc_content = self.get_all_sc_content(supercollider_dir)
        custom_path = OSC_PATHS['gen_custom']
        
        # The path might be constructed dynamically, so check base
        assert '/noise/gen/custom' in sc_content, \
            f"Custom param path not found in SC files"


class TestOSCPathsConsistency:
    """Tests for internal consistency of OSC paths."""
    
    def test_gen_paths_use_gen_prefix(self):
        """Generator-specific paths use gen_ prefix in key."""
        gen_related = ['frequency', 'cutoff', 'resonance', 'attack', 'decay', 
                       'filter_type', 'env_source', 'clock_rate', 'mute', 
                       'midi_channel', 'custom']
        
        for param in gen_related:
            key = f'gen_{param}'
            if key in OSC_PATHS:
                path = OSC_PATHS[key]
                assert '/gen/' in path, \
                    f"'{key}' path '{path}' should contain '/gen/'"
    
    def test_connection_paths_paired(self):
        """Connection paths have request/response pairs."""
        assert 'ping' in OSC_PATHS
        assert 'pong' in OSC_PATHS
        assert 'heartbeat' in OSC_PATHS
        assert 'heartbeat_ack' in OSC_PATHS
    
    def test_no_duplicate_paths(self):
        """No two keys map to the same path."""
        paths = list(OSC_PATHS.values())
        unique_paths = set(paths)
        
        if len(paths) != len(unique_paths):
            # Find duplicates for error message
            seen = set()
            duplicates = []
            for path in paths:
                if path in seen:
                    duplicates.append(path)
                seen.add(path)
            pytest.fail(f"Duplicate OSC paths: {duplicates}")


class TestOSCPathsDocumented:
    """Tests that OSC paths match documentation."""
    
    def test_path_keys_are_descriptive(self):
        """Path keys describe their purpose."""
        for key in OSC_PATHS.keys():
            # Key should be lowercase with underscores
            assert key == key.lower(), f"Key '{key}' should be lowercase"
            assert ' ' not in key, f"Key '{key}' should not have spaces"
    
    def test_generator_param_paths_match_config(self):
        """Generator param paths match GENERATOR_PARAMS keys."""
        from src.config import GENERATOR_PARAMS
        
        param_keys = [p['key'] for p in GENERATOR_PARAMS]
        
        for param_key in param_keys:
            osc_key = f'gen_{param_key}'
            assert osc_key in OSC_PATHS, \
                f"Missing OSC path for generator param '{param_key}'"


class TestOSCPortConfiguration:
    """Tests for OSC port configuration."""
    
    def test_ports_in_valid_range(self):
        """Ports are in non-privileged range."""
        from src.config import OSC_SEND_PORT, OSC_RECEIVE_PORT
        
        assert 1024 <= OSC_SEND_PORT <= 65535
        assert 1024 <= OSC_RECEIVE_PORT <= 65535
    
    def test_send_port_matches_sc(self, supercollider_dir):
        """Python send port matches SC receive port."""
        from src.config import OSC_SEND_PORT
        
        # Read init.scd to find the port SC opens
        init_path = os.path.join(supercollider_dir, 'init.scd')
        with open(init_path, 'r') as f:
            content = f.read()
        
        # Look for openUDPPort call
        match = re.search(r'openUDPPort\((\d+)\)', content)
        if match:
            sc_port = int(match.group(1))
            assert sc_port == OSC_SEND_PORT, \
                f"SC port {sc_port} != Python send port {OSC_SEND_PORT}"


class TestOSCHandlerDuplicates:
    """Test for duplicate OSCdef registrations in SuperCollider files."""
    
    def _count_osc_handlers(self, osc_path):
        """Count how many files register an OSCdef for given path."""
        import os
        
        sc_dir = 'supercollider'
        handlers = []
        
        for root, dirs, files in os.walk(sc_dir):
            for file in files:
                if file.endswith('.scd') and 'backup' not in file:
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r') as f:
                        content = f.read()
                    # Simple string search for the path
                    if f"'{osc_path}'" in content or f'"{osc_path}"' in content:
                        # Make sure it's in an OSCdef context
                        if 'OSCdef' in content:
                            handlers.append(filepath)
        
        return handlers
    
    def test_no_duplicate_gen_mute_handler(self):
        """Ensure /noise/gen/mute is only registered once."""
        handlers = self._count_osc_handlers('/noise/gen/mute')
        assert len(handlers) == 1, f"Expected 1 mute handler, found {len(handlers)} in: {handlers}"
    
    def test_no_duplicate_gen_volume_handler(self):
        """Ensure /noise/gen/volume is only registered once."""
        handlers = self._count_osc_handlers('/noise/gen/volume')
        assert len(handlers) == 1, f"Expected 1 volume handler, found {len(handlers)} in: {handlers}"

    def test_no_duplicate_gen_solo_handler(self):
        """Ensure /noise/gen/solo is only registered once."""
        handlers = self._count_osc_handlers('/noise/gen/solo')
        assert len(handlers) == 1, f"Expected 1 solo handler, found {len(handlers)} in: {handlers}"
