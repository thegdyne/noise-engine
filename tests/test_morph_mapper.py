"""
Unit tests for Hardware Morph Mapper v6.2

Tests MIDI CV controller and MorphMapper validation.
Does NOT require hardware - tests mapping logic only.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

# Import test subjects
from src.hardware.midi_cv import MidiCV, find_preferred_port


class TestMidiCV:
    """Test MIDI CV class (R6, R10, R11, R12)."""

    def test_unipolar_mapping_endpoints(self):
        """Test unipolar voltage to CC mapping at endpoints."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='unipolar')
        assert cv.volts_to_cc(0.0) == 0
        assert cv.volts_to_cc(5.0) == 127

    def test_unipolar_mapping_midpoint(self):
        """Test unipolar voltage to CC mapping at midpoint."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='unipolar')
        # 2.5V / 5.0V * 127 = 63.5 -> rounds to 64
        assert cv.volts_to_cc(2.5) == 64

    def test_unipolar_safe_cc(self):
        """Test unipolar safe CC value."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='unipolar')
        assert cv.safe_cc == 0

    def test_bipolar_mapping_zero_volts(self):
        """Test bipolar 0V maps to CC 64 (R10)."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='bipolar')
        assert cv.volts_to_cc(0.0) == 64  # R10: 0V = CC 64

    def test_bipolar_mapping_endpoints(self):
        """Test bipolar voltage to CC mapping at endpoints."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='bipolar')
        assert cv.volts_to_cc(-2.5) == 0   # -Vmax/2
        assert cv.volts_to_cc(2.5) == 127  # +Vmax/2

    def test_bipolar_safe_cc(self):
        """Test bipolar safe CC value (R10)."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='bipolar')
        assert cv.safe_cc == 64  # R10: Safe neutral for bipolar

    def test_calibration_custom_vmax(self):
        """Test voltage calibration with custom vmax (R6)."""
        cv = MidiCV("test", vmax_calibrated=4.9, mode='unipolar')
        assert cv.volts_to_cc(4.9) == 127
        assert cv.volts_to_cc(0.0) == 0

    def test_calibration_midpoint_custom(self):
        """Test calibration midpoint with custom vmax."""
        cv = MidiCV("test", vmax_calibrated=4.9, mode='unipolar')
        # 2.45V / 4.9V * 127 = 63.5 -> rounds to 64
        assert cv.volts_to_cc(2.45) == 64

    def test_clamping_below_zero(self):
        """Test voltage clamping below minimum."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='unipolar')
        assert cv.volts_to_cc(-1.0) == 0  # Clamp below

    def test_clamping_above_vmax(self):
        """Test voltage clamping above maximum."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='unipolar')
        assert cv.volts_to_cc(10.0) == 127  # Clamp above

    def test_bipolar_clamping(self):
        """Test bipolar voltage clamping."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='bipolar')
        assert cv.volts_to_cc(-5.0) == 0    # Below -Vmax/2
        assert cv.volts_to_cc(5.0) == 127   # Above +Vmax/2

    def test_cc_value_range(self):
        """Test CC values are always in valid MIDI range."""
        cv = MidiCV("test", vmax_calibrated=5.0, mode='unipolar')
        for v in [-10, -1, 0, 1, 2.5, 4, 5, 6, 10]:
            cc = cv.volts_to_cc(v)
            assert 0 <= cc <= 127, f"CC {cc} out of range for {v}V"


class TestMorphMapperValidation:
    """Test MorphMapper parameter validation."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for MorphMapper."""
        sc_client = Mock()
        telem_controller = Mock(spec=['history', 'current_waveform', 'set_generator_context',
                                       'enable', 'disable', 'snapshot'])
        telem_controller.history = []
        telem_controller.current_waveform = None
        return sc_client, telem_controller

    def test_points_validation(self, mock_dependencies):
        """Test points must be >= 2."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            with pytest.raises(ValueError, match="points must be >= 2"):
                MorphMapper(
                    sc_client=sc_client,
                    telemetry_controller=telem,
                    device_name="Test",
                    points=1
                )

    def test_cv_range_validation(self, mock_dependencies):
        """Test cv_max must be > cv_min."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            with pytest.raises(ValueError, match="cv_max must be > cv_min"):
                MorphMapper(
                    sc_client=sc_client,
                    telemetry_controller=telem,
                    device_name="Test",
                    cv_range=(5.0, 0.0)  # Reversed
                )

    def test_slot_validation(self, mock_dependencies):
        """Test slot must be 0-7."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            with pytest.raises(ValueError, match="slot must be 0-7"):
                MorphMapper(
                    sc_client=sc_client,
                    telemetry_controller=telem,
                    device_name="Test",
                    slot=8
                )

    def test_unipolar_cv_range_validation(self, mock_dependencies):
        """Test unipolar cv_max must be <= vmax (R8)."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            with pytest.raises(ValueError, match="must be <="):
                MorphMapper(
                    sc_client=sc_client,
                    telemetry_controller=telem,
                    device_name="Test",
                    cv_range=(0.0, 6.0),  # Exceeds vmax
                    vmax_calibrated=5.0,
                    cv_mode='unipolar'
                )

    def test_bipolar_cv_range_validation(self, mock_dependencies):
        """Test bipolar range must be within ±Vmax/2 (R8)."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            with pytest.raises(ValueError, match="Bipolar"):
                MorphMapper(
                    sc_client=sc_client,
                    telemetry_controller=telem,
                    device_name="Test",
                    cv_range=(-3.0, 3.0),  # Exceeds ±2.5V
                    vmax_calibrated=5.0,
                    cv_mode='bipolar'
                )

    def test_cv_mode_validation(self, mock_dependencies):
        """Test cv_mode must be 'unipolar' or 'bipolar'."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            with pytest.raises(ValueError, match="cv_mode must be"):
                MorphMapper(
                    sc_client=sc_client,
                    telemetry_controller=telem,
                    device_name="Test",
                    cv_mode='invalid'
                )

    def test_no_midi_port_validation(self, mock_dependencies):
        """Test error when no MIDI port available."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value=None):
            with patch('src.telemetry.morph_mapper.MidiCV.list_ports', return_value=[]):
                from src.telemetry.morph_mapper import MorphMapper

                with pytest.raises(ValueError, match="No MIDI port found"):
                    MorphMapper(
                        sc_client=sc_client,
                        telemetry_controller=telem,
                        device_name="Test"
                    )

    def test_valid_unipolar_config(self, mock_dependencies):
        """Test valid unipolar configuration succeeds."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            mapper = MorphMapper(
                sc_client=sc_client,
                telemetry_controller=telem,
                device_name="Buchla 258 Clone",
                cv_range=(0.0, 5.0),
                points=12,
                slot=0,
                vmax_calibrated=5.0,
                cv_mode='unipolar'
            )

            assert mapper.device_name == "Buchla 258 Clone"
            assert mapper.cv_min == 0.0
            assert mapper.cv_max == 5.0
            assert mapper.points == 12

    def test_valid_bipolar_config(self, mock_dependencies):
        """Test valid bipolar configuration succeeds."""
        sc_client, telem = mock_dependencies

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper

            mapper = MorphMapper(
                sc_client=sc_client,
                telemetry_controller=telem,
                device_name="Test Device",
                cv_range=(-2.5, 2.5),  # Within ±2.5V for 5V vmax
                points=8,
                slot=0,
                vmax_calibrated=5.0,
                cv_mode='bipolar'
            )

            assert mapper.cv_mode == 'bipolar'
            assert mapper.cv_min == -2.5
            assert mapper.cv_max == 2.5


class TestFindPreferredPort:
    """Test MIDI port detection (R5)."""

    def test_finds_cvocd_first(self):
        """Test CV.OCD port is found before MOTU."""
        with patch('mido.get_output_names', return_value=["MOTU M6", "CV.OCD MIDI"]):
            port = find_preferred_port()
            assert port == "CV.OCD MIDI"

    def test_finds_motu_fallback(self):
        """Test MOTU port is found when no CV.OCD."""
        with patch('mido.get_output_names', return_value=["MOTU M6", "Other Port"]):
            port = find_preferred_port()
            assert port == "MOTU M6"

    def test_finds_m6_fallback(self):
        """Test M6 port is found when no full MOTU name."""
        with patch('mido.get_output_names', return_value=["M6", "Other Port"]):
            port = find_preferred_port()
            assert port == "M6"

    def test_returns_none_when_no_match(self):
        """Test returns None when no matching ports."""
        with patch('mido.get_output_names', return_value=["Unknown Port 1", "Unknown Port 2"]):
            port = find_preferred_port()
            assert port is None

    def test_custom_substrings(self):
        """Test custom substring priority list."""
        with patch('mido.get_output_names', return_value=["PortA", "PortB", "CustomPort"]):
            port = find_preferred_port(["Custom", "PortA"])
            assert port == "CustomPort"


class TestMorphMapSchema:
    """Test morph map output schema (R17)."""

    @pytest.fixture
    def mock_mapper(self):
        """Create mapper with mocked dependencies."""
        sc_client = Mock()
        telem = Mock()
        telem.history = []
        telem.current_waveform = None

        with patch('src.telemetry.morph_mapper.find_preferred_port', return_value="TestPort"):
            from src.telemetry.morph_mapper import MorphMapper
            mapper = MorphMapper(
                sc_client=sc_client,
                telemetry_controller=telem,
                device_name="Test Device",
                cv_range=(0.0, 5.0),
                points=4,
                vmax_calibrated=5.0
            )
            return mapper

    def test_morph_map_format_version(self, mock_mapper):
        """Test morph map has correct format version."""
        morph_map = mock_mapper._build_morph_map(0)
        assert morph_map['format_version'] == '6.2'

    def test_morph_map_cv_method(self, mock_mapper):
        """Test morph map specifies MIDI CV method."""
        morph_map = mock_mapper._build_morph_map(0)
        assert morph_map['cv_method'] == 'midi_cv'

    def test_morph_map_test_config(self, mock_mapper):
        """Test morph map includes test configuration."""
        morph_map = mock_mapper._build_morph_map(0)
        config = morph_map['test_config']

        assert 'settle_ms' in config
        assert 'input_channel' in config
        assert 'midi_port' in config
        assert 'vmax_calibrated' in config
        assert 'cv_mode' in config

    def test_morph_map_metadata(self, mock_mapper):
        """Test morph map includes metadata."""
        morph_map = mock_mapper._build_morph_map(0)
        metadata = morph_map['metadata']

        assert 'interrupted' in metadata
        assert 'total_time_sec' in metadata
        assert 'failed_points' in metadata
        assert 'pack_used' in metadata


class TestTimingOrder:
    """Test R4 timing order compliance."""

    def test_t0_is_after_settle_in_docstring(self):
        """Verify _wait_for_fresh_snapshot documents t0 as post-settle."""
        from src.telemetry.morph_mapper import MorphMapper
        docstring = MorphMapper._wait_for_fresh_snapshot.__doc__
        assert "AFTER settle" in docstring or "after settle" in docstring, \
            "Docstring should document that t0 is AFTER settle period"

    def test_docstring_describes_post_settle_frames(self):
        """Verify docstring clarifies only post-settle frames are accepted."""
        from src.telemetry.morph_mapper import MorphMapper
        docstring = MorphMapper._wait_for_fresh_snapshot.__doc__
        assert "only frames after" in docstring.lower() or "post-settle" in docstring.lower(), \
            "Docstring should clarify that only post-settle frames are accepted"
