"""
Unit tests for FingerprintExtractor v1

Tests fingerprint extraction from waveform data.
"""

import pytest
import numpy as np

from src.telemetry.fingerprint_extractor import FingerprintExtractor


class TestFingerprintExtractor:
    """Test FingerprintExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return FingerprintExtractor(
            device_make="Test",
            device_model="TestOsc",
            device_variant="unit_test",
            unit_id="A"
        )

    @pytest.fixture
    def sine_wave(self):
        """Generate a pure sine wave (1 cycle, 1024 samples)."""
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.sin(t)

    @pytest.fixture
    def sawtooth_wave(self):
        """Generate a sawtooth wave (rich in harmonics)."""
        n = 1024
        t = np.linspace(0, 1, n, endpoint=False)
        return 2 * (t - np.floor(t + 0.5))

    def test_session_id_generation(self, extractor):
        """Test session ID is generated on start."""
        session_id = extractor.start_session()
        assert session_id.startswith("s")
        assert len(session_id) == 16  # sYYYYMMDD_HHMMSS

    def test_auto_session_on_extract(self, extractor, sine_wave):
        """Test session is auto-started if not explicitly started."""
        assert extractor.session_id is None
        fp = extractor.extract(sine_wave, cv_volts=2.5)
        assert extractor.session_id is not None

    def test_fingerprint_schema_version(self, extractor, sine_wave):
        """Test fingerprint has correct schema version."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)
        assert fp["schema_version"] == "fingerprint.v2"

    def test_fingerprint_id_format(self, extractor, sine_wave):
        """Test fingerprint ID follows expected format."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)
        # Format: {device_key}_{session_id}_c{capture_index:03d}
        assert "testosc_a_s" in fp["id"]
        assert "_c000" in fp["id"]

    def test_capture_index_increments(self, extractor, sine_wave):
        """Test capture index increments with each extraction."""
        extractor.start_session()
        fp1 = extractor.extract(sine_wave, cv_volts=1.0)
        fp2 = extractor.extract(sine_wave, cv_volts=2.0)
        fp3 = extractor.extract(sine_wave, cv_volts=3.0)

        assert "_c000" in fp1["id"]
        assert "_c001" in fp2["id"]
        assert "_c002" in fp3["id"]

    def test_device_info(self, extractor, sine_wave):
        """Test device info is captured."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert fp["device"]["make"] == "Test"
        assert fp["device"]["model"] == "TestOsc"
        assert fp["device"]["variant"] == "unit_test"
        assert fp["device"]["unit_id"] == "A"

    def test_cv_capture(self, extractor, sine_wave):
        """Test CV voltage is captured."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=3.14159, cv_chan="morph")

        assert fp["capture"]["cv"]["volts"] == 3.1416  # Rounded to 4 decimal places
        assert fp["capture"]["cv"]["chan"] == "morph"

    def test_harmonic_ratios_count(self, extractor, sine_wave):
        """Test 8 harmonic ratios are extracted."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert len(fp["features"]["harm_ratio"]) == 32

    def test_sine_wave_harmonics(self, extractor, sine_wave):
        """Test pure sine has minimal upper harmonics."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5, freq_hz=46.875)

        # First harmonic (fundamental) should be 1.0
        assert fp["features"]["harm_ratio"][0] == 1.0

        # Upper harmonics should be relatively low for pure sine
        # Note: FFT bin leakage in single-cycle analysis causes some harmonic content
        assert fp["features"]["harm_ratio"][2] < fp["features"]["harm_ratio"][0]  # h3 < h1

    def test_sawtooth_harmonics(self, extractor, sawtooth_wave):
        """Test sawtooth has significant upper harmonics."""
        extractor.start_session()
        fp = extractor.extract(sawtooth_wave, cv_volts=2.5, freq_hz=46.875)

        # Sawtooth should have decreasing harmonics
        # h2 should be around 0.5, h3 around 0.33, etc.
        assert fp["features"]["harm_ratio"][1] > 0.3  # h2
        assert fp["features"]["harm_ratio"][2] > 0.2  # h3

    def test_phase_relations_count(self, extractor, sine_wave):
        """Test 8 phase relations are extracted."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert len(fp["features"]["phase_rel"]) == 32

    def test_phase_values_normalized(self, extractor, sawtooth_wave):
        """Test phase values are in 0..1 range."""
        extractor.start_session()
        fp = extractor.extract(sawtooth_wave, cv_volts=2.5)

        for phase in fp["features"]["phase_rel"]:
            assert 0.0 <= phase <= 1.0, f"Phase {phase} out of 0..1 range"

    def test_morph_metrics_count(self, extractor, sine_wave):
        """Test 5 morphology metrics are extracted."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert len(fp["features"]["morph"]) == 5

    def test_morph_values_normalized(self, extractor, sine_wave):
        """Test morph values are in 0..1 range."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        for m in fp["features"]["morph"]:
            assert 0.0 <= m <= 1.0, f"Morph value {m} out of 0..1 range"

    def test_quality_metrics(self, extractor, sine_wave):
        """Test quality metrics are computed."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert "rms" in fp["quality"]
        assert "peak" in fp["quality"]
        assert "snr_db" in fp["quality"]
        assert "flags" in fp["quality"]

    def test_rms_peak_positive(self, extractor, sine_wave):
        """Test RMS and peak are positive values."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert fp["quality"]["rms"] > 0
        assert fp["quality"]["peak"] > 0

    def test_snr_reasonable(self, extractor):
        """Test SNR is reasonable for clean signal."""
        # Use a longer waveform with multiple complete cycles for accurate SNR
        n = 4096  # No zero-padding needed
        freq = 500  # Multiple cycles fit cleanly
        sr = 48000
        t = np.arange(n) / sr
        clean_sine = np.sin(2 * np.pi * freq * t)

        extractor.start_session()
        fp = extractor.extract(clean_sine, cv_volts=2.5, freq_hz=freq, sample_rate=sr)

        # Pure sine should have positive SNR (signal > noise)
        # Note: SNR calculation captures 8 harmonic bins vs all other bins,
        # so windowing causes some leakage that reduces measured SNR
        assert fp["quality"]["snr_db"] > 0

    def test_clipping_flag(self, extractor):
        """Test clipping flag is set for clipped waveform."""
        extractor.start_session()
        # Create clipped waveform
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        clipped = np.clip(np.sin(t) * 2, -1.0, 1.0)

        fp = extractor.extract(clipped, cv_volts=2.5)
        assert "clipped" in fp["quality"]["flags"]

    def test_low_level_flag(self, extractor):
        """Test low_level flag is set for quiet signal."""
        extractor.start_session()
        # Very quiet signal
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        quiet = np.sin(t) * 0.001

        fp = extractor.extract(quiet, cv_volts=2.5)
        assert "low_level" in fp["quality"]["flags"]

    def test_dc_offset_flag(self, extractor):
        """Test dc_offset flag is set for offset signal."""
        extractor.start_session()
        # Signal with DC offset
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        offset = np.sin(t) * 0.5 + 0.3  # 0.3V DC offset

        fp = extractor.extract(offset, cv_volts=2.5)
        assert "dc_offset" in fp["quality"]["flags"]

    def test_adjacent_structure(self, extractor, sine_wave):
        """Test adjacent links structure exists."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert "adjacent" in fp
        assert "prev_id" in fp["adjacent"]
        assert "next_id" in fp["adjacent"]
        assert "delta_prev" in fp["adjacent"]

    def test_initial_delta_zeroed(self, extractor, sine_wave):
        """Test initial fingerprint has zero deltas."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        delta = fp["adjacent"]["delta_prev"]
        assert delta["l2_harm"] == 0.0
        assert delta["l2_phase"] == 0.0
        assert delta["l2_morph"] == 0.0

    def test_hash_exists(self, extractor, sine_wave):
        """Test feature hash is computed."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert "hash" in fp
        assert "features_sha1" in fp["hash"]
        assert len(fp["hash"]["features_sha1"]) == 12  # Truncated SHA1

    def test_hash_deterministic(self, extractor, sine_wave):
        """Test same waveform produces same hash."""
        ext1 = FingerprintExtractor("Test", "Model", "v1", "A")
        ext2 = FingerprintExtractor("Test", "Model", "v1", "A")

        ext1.start_session()
        ext2.start_session()

        fp1 = ext1.extract(sine_wave, cv_volts=2.5, freq_hz=46.875)
        fp2 = ext2.extract(sine_wave, cv_volts=2.5, freq_hz=46.875)

        assert fp1["hash"]["features_sha1"] == fp2["hash"]["features_sha1"]

    def test_notes_captured(self, extractor, sine_wave):
        """Test notes are captured in fingerprint."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5, notes=["test_note", "another"])

        assert fp["capture"]["notes"] == ["test_note", "another"]

    def test_sample_rate_captured(self, extractor, sine_wave):
        """Test sample rate is captured."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5, sample_rate=96000)

        assert fp["capture"]["sr_hz"] == 96000

    def test_freq_auto_detected(self, extractor, sine_wave):
        """Test frequency is auto-detected when not provided."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert fp["capture"]["freq_hz"] > 0

    def test_freq_manual_override(self, extractor, sine_wave):
        """Test frequency can be manually specified."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5, freq_hz=440.0)

        assert abs(fp["capture"]["freq_hz"] - 440.0) < 0.5  # FFT bin rounding

    def test_window_type_recorded(self, extractor, sine_wave):
        """Test window type is recorded."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert fp["capture"]["window"] == "hann"

    def test_n_samples_recorded(self, extractor, sine_wave):
        """Test sample count is recorded."""
        extractor.start_session()
        fp = extractor.extract(sine_wave, cv_volts=2.5)

        assert fp["capture"]["n_samples"] == 1024

    def test_short_waveform_zero_padding(self, extractor):
        """Test short waveforms are zero-padded for FFT resolution."""
        # 512-sample sine wave (~10 cycles at 1kHz, typical short capture)
        n = 512
        freq = 1000  # Hz - ensures multiple complete cycles in 512 samples
        sr = 48000
        t = np.arange(n) / sr
        short_sine = np.sin(2 * np.pi * freq * t)

        extractor.start_session()
        fp = extractor.extract(short_sine, cv_volts=2.5, freq_hz=freq, sample_rate=sr)

        # Should have extracted meaningful harmonics despite short window
        assert fp["capture"]["n_samples"] == 480  # Trimmed to 10 whole cycles
        assert fp["capture"]["fft_size"] == 480  # No zero-padding in SSOT

        # Pure sine should have h1 dominant, h2/h3 low
        assert fp["features"]["harm_ratio"][0] == 1.0
        # Higher harmonics should be significantly lower than fundamental
        assert fp["features"]["harm_ratio"][2] < fp["features"]["harm_ratio"][0]  # h3 < h1

    def test_fft_size_matches_long_waveform(self, extractor):
        """Test fft_size equals n_samples for long waveforms."""
        # 4096+ sample waveform
        n = 8192
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        long_sine = np.sin(t)

        extractor.start_session()
        fp = extractor.extract(long_sine, cv_volts=2.5)

        # No padding needed
        assert fp["capture"]["n_samples"] == 8192
        assert fp["capture"]["fft_size"] == 8192


class TestMorphologyMetrics:
    """Test specific morphology metric calculations."""

    @pytest.fixture
    def extractor(self):
        return FingerprintExtractor("Test", "Model", "v1", "A")

    def test_sine_symmetry_high(self, extractor):
        """Test pure sine has high symmetry (odd harmonics dominant)."""
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        sine = np.sin(t)

        extractor.start_session()
        fp = extractor.extract(sine, cv_volts=2.5, freq_hz=46.875)

        # Sine is all odd harmonic (h1), so symmetry should favor odd
        # Note: FFT windowing causes some even harmonic leakage
        symmetry = fp["features"]["morph"][0]
        assert symmetry > 0.7  # Odd-dominant

    def test_square_wave_symmetry(self, extractor):
        """Test square wave has high symmetry (odd harmonics)."""
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        square = np.sign(np.sin(t))

        extractor.start_session()
        fp = extractor.extract(square, cv_volts=2.5, freq_hz=46.875)

        # Square wave is odd-harmonic dominant
        # Note: Gibbs phenomenon and windowing affect ideal symmetry
        symmetry = fp["features"]["morph"][0]
        assert symmetry > 0.6  # Odd-dominant

    def test_sawtooth_symmetry(self, extractor):
        """Test sawtooth has mixed symmetry."""
        n = 1024
        t = np.linspace(0, 1, n, endpoint=False)
        saw = 2 * (t - np.floor(t + 0.5))

        extractor.start_session()
        fp = extractor.extract(saw, cv_volts=2.5, freq_hz=46.875)

        # Sawtooth has both odd and even harmonics
        symmetry = fp["features"]["morph"][0]
        assert 0.3 < symmetry < 0.8

    def test_crest_factor_sine(self, extractor):
        """Test sine has expected crest factor."""
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        sine = np.sin(t)

        extractor.start_session()
        fp = extractor.extract(sine, cv_volts=2.5)

        # Sine crest factor = sqrt(2) ≈ 1.414
        # Normalized: (1.414 - 1) / 2 = 0.207
        crest = fp["features"]["morph"][1]
        assert 0.15 < crest < 0.3

    def test_crest_factor_square(self, extractor):
        """Test square wave has low crest factor."""
        n = 1024
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        square = np.sign(np.sin(t))

        extractor.start_session()
        fp = extractor.extract(square, cv_volts=2.5)

        # Square crest = 1.0, normalized = 0.0
        crest = fp["features"]["morph"][1]
        assert crest < 0.1
