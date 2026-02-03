"""
Unit tests for FingerprintStore v1

Tests JSONL storage, sweep management, and delta computation.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path

from src.telemetry.fingerprint_store import FingerprintStore
from src.telemetry.fingerprint_extractor import FingerprintExtractor
import numpy as np


class TestFingerprintStore:
    """Test FingerprintStore class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def store(self, temp_dir):
        """Create store instance."""
        return FingerprintStore(temp_dir)

    @pytest.fixture
    def sample_fingerprint(self):
        """Create a sample fingerprint dict."""
        return {
            "schema_version": "fingerprint.v1",
            "id": "test_device_a_s20260203_120000_c000",
            "device": {
                "make": "Test",
                "model": "TestDevice",
                "variant": "v1",
                "unit_id": "A"
            },
            "session": {
                "id": "s20260203_120000",
                "utc": "2026-02-03T12:00:00Z",
                "operator": "test"
            },
            "capture": {
                "index": 0,
                "cv": {"chan": "cv1", "volts": 2.5},
                "freq_hz": 440.0,
                "sr_hz": 48000,
                "n_samples": 1024,
                "window": "hann",
                "notes": []
            },
            "features": {
                "harm_ratio": [1.0, 0.5, 0.33, 0.25, 0.2, 0.16, 0.14, 0.125],
                "phase_rel": [0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.5],
                "morph": [0.6, 0.3, 0.4, 0.5, 0.2]
            },
            "quality": {
                "rms": 0.35,
                "peak": 0.95,
                "snr_db": 45.0,
                "flags": []
            },
            "adjacent": {
                "prev_id": None,
                "next_id": None,
                "delta_prev": {"l2_harm": 0.0, "l2_phase": 0.0, "l2_morph": 0.0}
            },
            "hash": {
                "features_sha1": "abc123def456"
            }
        }

    def test_creates_directory_structure(self, temp_dir):
        """Test store creates required directories."""
        store = FingerprintStore(temp_dir)

        assert (Path(temp_dir) / "schema").exists()
        assert (Path(temp_dir) / "devices").exists()
        assert (Path(temp_dir) / "comparisons").exists()

    def test_get_device_path_creates_subdirs(self, store, temp_dir):
        """Test get_device_path creates device subdirectories."""
        device_path = store.get_device_path("test_device")

        assert (device_path / "raw").exists()
        assert (device_path / "sweeps").exists()
        assert (device_path / "deltas").exists()
        assert (device_path / "summaries").exists()

    def test_save_fingerprint_creates_jsonl(self, store, sample_fingerprint, temp_dir):
        """Test save_fingerprint creates JSONL file."""
        store.save_fingerprint(sample_fingerprint, "test_device")

        jsonl_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.jsonl"
        assert jsonl_path.exists()

    def test_save_fingerprint_appends(self, store, sample_fingerprint, temp_dir):
        """Test save_fingerprint appends to existing file."""
        fp1 = sample_fingerprint.copy()
        fp1["id"] = "test_1"
        fp2 = sample_fingerprint.copy()
        fp2["id"] = "test_2"

        store.save_fingerprint(fp1, "test_device")
        store.save_fingerprint(fp2, "test_device")

        jsonl_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.jsonl"
        with open(jsonl_path) as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_save_fingerprint_links_prev(self, store, sample_fingerprint, temp_dir):
        """Test save_fingerprint links to previous fingerprint."""
        fp1 = sample_fingerprint.copy()
        fp1["id"] = "test_1"
        fp2 = sample_fingerprint.copy()
        fp2["id"] = "test_2"
        fp2["adjacent"] = {"prev_id": None, "next_id": None,
                           "delta_prev": {"l2_harm": 0.0, "l2_phase": 0.0, "l2_morph": 0.0}}

        store.save_fingerprint(fp1, "test_device")
        store.save_fingerprint(fp2, "test_device")

        # Read back and verify link
        jsonl_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.jsonl"
        with open(jsonl_path) as f:
            lines = f.readlines()
        fp2_saved = json.loads(lines[1])
        assert fp2_saved["adjacent"]["prev_id"] == "test_1"

    def test_save_fingerprint_auto_device_key(self, store, sample_fingerprint, temp_dir):
        """Test device key is auto-generated from fingerprint."""
        fp = sample_fingerprint.copy()
        fp["device"]["model"] = "My Device"
        fp["device"]["unit_id"] = "B"

        store.save_fingerprint(fp)  # No device_key provided

        # Check device directory was created with auto-generated key
        device_dir = Path(temp_dir) / "devices" / "my_device_b"
        assert device_dir.exists()


class TestSweepOperations:
    """Test sweep save and load operations."""

    @pytest.fixture
    def temp_dir(self):
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def store(self, temp_dir):
        return FingerprintStore(temp_dir)

    @pytest.fixture
    def sweep_fingerprints(self):
        """Create a list of fingerprints for a sweep."""
        fps = []
        for i in range(5):
            fps.append({
                "schema_version": "fingerprint.v1",
                "id": f"test_device_a_s20260203_120000_c{i:03d}",
                "device": {
                    "make": "Test",
                    "model": "TestDevice",
                    "variant": "v1",
                    "unit_id": "A"
                },
                "session": {
                    "id": "s20260203_120000",
                    "utc": "2026-02-03T12:00:00Z",
                    "operator": "test"
                },
                "capture": {
                    "index": i,
                    "cv": {"chan": "morph", "volts": i * 1.0},  # 0V to 4V
                    "freq_hz": 440.0,
                    "sr_hz": 48000,
                    "n_samples": 1024,
                    "window": "hann",
                    "notes": []
                },
                "features": {
                    "harm_ratio": [1.0 - i * 0.1, 0.5, 0.33, 0.25, 0.2, 0.16, 0.14, 0.125],
                    "phase_rel": [0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.5],
                    "morph": [0.6 + i * 0.05, 0.3, 0.4, 0.5, 0.2]
                },
                "quality": {
                    "rms": 0.35,
                    "peak": 0.95,
                    "snr_db": 45.0,
                    "flags": []
                },
                "adjacent": {
                    "prev_id": None,
                    "next_id": None,
                    "delta_prev": {"l2_harm": 0.0, "l2_phase": 0.0, "l2_morph": 0.0}
                },
                "hash": {
                    "features_sha1": f"abc{i:03d}def456"
                }
            })
        return fps

    def test_save_sweep_empty_raises(self, store):
        """Test save_sweep raises on empty list."""
        with pytest.raises(ValueError, match="Empty"):
            store.save_sweep([], "test_device")

    def test_save_sweep_creates_files(self, store, sweep_fingerprints, temp_dir):
        """Test save_sweep creates all required files."""
        sweep_name = store.save_sweep(sweep_fingerprints, "test_device")

        device_dir = Path(temp_dir) / "devices" / "test_device"
        assert (device_dir / "raw" / "fingerprints.jsonl").exists()
        assert (device_dir / "raw" / "fingerprints.csv").exists()
        assert (device_dir / "sweeps" / f"{sweep_name}.json").exists()
        assert (device_dir / "deltas" / f"{sweep_name}.jsonl").exists()
        assert (device_dir / "summaries" / f"{sweep_name}_evolution.json").exists()
        assert (device_dir / "manifest.json").exists()

    def test_save_sweep_links_adjacent(self, store, sweep_fingerprints, temp_dir):
        """Test save_sweep links adjacent fingerprints."""
        store.save_sweep(sweep_fingerprints, "test_device")

        jsonl_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.jsonl"
        with open(jsonl_path) as f:
            fps = [json.loads(line) for line in f]

        # Check linking
        assert fps[0]["adjacent"]["prev_id"] is None
        assert fps[0]["adjacent"]["next_id"] == fps[1]["id"]
        assert fps[1]["adjacent"]["prev_id"] == fps[0]["id"]
        assert fps[1]["adjacent"]["next_id"] == fps[2]["id"]
        assert fps[-1]["adjacent"]["next_id"] is None

    def test_save_sweep_computes_deltas(self, store, sweep_fingerprints, temp_dir):
        """Test save_sweep computes L2 deltas."""
        store.save_sweep(sweep_fingerprints, "test_device")

        jsonl_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.jsonl"
        with open(jsonl_path) as f:
            fps = [json.loads(line) for line in f]

        # Second fingerprint should have non-zero delta
        assert fps[1]["adjacent"]["delta_prev"]["l2_harm"] > 0

    def test_sweep_definition_format(self, store, sweep_fingerprints, temp_dir):
        """Test sweep definition file format."""
        sweep_name = store.save_sweep(sweep_fingerprints, "test_device")

        sweep_path = Path(temp_dir) / "devices" / "test_device" / "sweeps" / f"{sweep_name}.json"
        with open(sweep_path) as f:
            sweep_def = json.load(f)

        assert sweep_def["schema_version"] == "sweep.v1"
        assert sweep_def["device_key"] == "test_device"
        assert sweep_def["cv_chan"] == "morph"
        assert sweep_def["points"] == 5
        assert sweep_def["cv_range"] == [0.0, 4.0]
        assert len(sweep_def["ids"]) == 5

    def test_deltas_file_format(self, store, sweep_fingerprints, temp_dir):
        """Test deltas file format."""
        sweep_name = store.save_sweep(sweep_fingerprints, "test_device")

        delta_path = Path(temp_dir) / "devices" / "test_device" / "deltas" / f"{sweep_name}.jsonl"
        with open(delta_path) as f:
            deltas = [json.loads(line) for line in f]

        # Should have n-1 deltas for n fingerprints
        assert len(deltas) == 4

        # Check format
        assert deltas[0]["schema_version"] == "delta.v1"
        assert "a_id" in deltas[0]
        assert "b_id" in deltas[0]
        assert "cv_delta" in deltas[0]
        assert "l2_harm" in deltas[0]
        assert "changes" in deltas[0]

    def test_evolution_summary_format(self, store, sweep_fingerprints, temp_dir):
        """Test evolution summary format."""
        sweep_name = store.save_sweep(sweep_fingerprints, "test_device")

        summary_path = Path(temp_dir) / "devices" / "test_device" / "summaries" / f"{sweep_name}_evolution.json"
        with open(summary_path) as f:
            summary = json.load(f)

        assert summary["schema_version"] == "evolution.v1"
        assert summary["points"] == 5
        assert "harmonics" in summary
        assert "morph" in summary

        # Check harmonic analysis
        h1 = summary["harmonics"]["h1"]
        assert "min" in h1
        assert "max" in h1
        assert "mean" in h1
        assert "trend" in h1
        assert "slope" in h1
        assert "r2" in h1

    def test_load_sweep(self, store, sweep_fingerprints, temp_dir):
        """Test loading a sweep by name."""
        sweep_name = store.save_sweep(sweep_fingerprints, "test_device")

        loaded = store.load_sweep("test_device", sweep_name)
        assert len(loaded) == 5
        assert loaded[0]["id"] == sweep_fingerprints[0]["id"]

    def test_load_fingerprints_all(self, store, sweep_fingerprints, temp_dir):
        """Test loading all fingerprints for a device."""
        store.save_sweep(sweep_fingerprints, "test_device")

        loaded = store.load_fingerprints("test_device")
        assert len(loaded) == 5

    def test_load_fingerprints_by_id(self, store, sweep_fingerprints, temp_dir):
        """Test loading specific fingerprints by ID."""
        store.save_sweep(sweep_fingerprints, "test_device")

        ids = [sweep_fingerprints[0]["id"], sweep_fingerprints[2]["id"]]
        loaded = store.load_fingerprints("test_device", ids)
        assert len(loaded) == 2


class TestManifestAndIndex:
    """Test manifest and index operations."""

    @pytest.fixture
    def temp_dir(self):
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def store(self, temp_dir):
        return FingerprintStore(temp_dir)

    @pytest.fixture
    def sweep_fingerprints(self):
        """Create a minimal sweep."""
        return [{
            "schema_version": "fingerprint.v1",
            "id": f"test_a_s20260203_120000_c{i:03d}",
            "device": {"make": "Test", "model": "Test", "variant": "v1", "unit_id": "A"},
            "session": {"id": "s20260203_120000", "utc": "2026-02-03T12:00:00Z", "operator": "test"},
            "capture": {"index": i, "cv": {"chan": "cv1", "volts": i}, "freq_hz": 440.0,
                       "sr_hz": 48000, "n_samples": 1024, "window": "hann", "notes": []},
            "features": {"harm_ratio": [1.0] * 8, "phase_rel": [0.0] * 8, "morph": [0.5] * 5},
            "quality": {"rms": 0.35, "peak": 0.95, "snr_db": 45.0, "flags": []},
            "adjacent": {"prev_id": None, "next_id": None,
                        "delta_prev": {"l2_harm": 0.0, "l2_phase": 0.0, "l2_morph": 0.0}},
            "hash": {"features_sha1": "abc123"}
        } for i in range(3)]

    def test_manifest_created(self, store, sweep_fingerprints, temp_dir):
        """Test device manifest is created."""
        store.save_sweep(sweep_fingerprints, "test_device")

        manifest_path = Path(temp_dir) / "devices" / "test_device" / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["schema_version"] == "manifest.v1"
        assert "device" in manifest
        assert len(manifest["sweeps"]) == 1
        assert len(manifest["sessions"]) == 1

    def test_manifest_updated(self, store, sweep_fingerprints, temp_dir):
        """Test manifest is updated with new sweeps."""
        # First sweep
        store.save_sweep(sweep_fingerprints, "test_device", "sweep1")

        # Second sweep with different session
        fps2 = sweep_fingerprints.copy()
        for fp in fps2:
            fp["session"]["id"] = "s20260203_130000"
            fp["id"] = fp["id"].replace("120000", "130000")
        store.save_sweep(fps2, "test_device", "sweep2")

        manifest_path = Path(temp_dir) / "devices" / "test_device" / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert len(manifest["sweeps"]) == 2
        assert len(manifest["sessions"]) == 2

    def test_index_created(self, store, sweep_fingerprints, temp_dir):
        """Test top-level index is created."""
        store.save_sweep(sweep_fingerprints, "test_device")

        index_path = Path(temp_dir) / "index.json"
        assert index_path.exists()

        with open(index_path) as f:
            index = json.load(f)

        assert index["schema_version"] == "index.v1"
        assert "updated_utc" in index
        assert len(index["devices"]) == 1
        assert index["devices"][0]["key"] == "test_device"

    def test_index_multiple_devices(self, store, sweep_fingerprints, temp_dir):
        """Test index tracks multiple devices."""
        store.save_sweep(sweep_fingerprints, "device_a")
        store.save_sweep(sweep_fingerprints, "device_b")

        index_path = Path(temp_dir) / "index.json"
        with open(index_path) as f:
            index = json.load(f)

        assert len(index["devices"]) == 2
        keys = [d["key"] for d in index["devices"]]
        assert "device_a" in keys
        assert "device_b" in keys


class TestCSVExport:
    """Test CSV export functionality."""

    @pytest.fixture
    def temp_dir(self):
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def store(self, temp_dir):
        return FingerprintStore(temp_dir)

    @pytest.fixture
    def sweep_fingerprints(self):
        """Create fingerprints with known values."""
        return [{
            "schema_version": "fingerprint.v1",
            "id": f"test_a_s20260203_120000_c{i:03d}",
            "device": {"make": "Test", "model": "Test", "variant": "v1", "unit_id": "A"},
            "session": {"id": "s20260203_120000", "utc": "2026-02-03T12:00:00Z", "operator": "test"},
            "capture": {"index": i, "cv": {"chan": "cv1", "volts": i * 0.5}, "freq_hz": 440.0 + i * 10,
                       "sr_hz": 48000, "n_samples": 1024, "window": "hann", "notes": []},
            "features": {
                "harm_ratio": [1.0, 0.5, 0.33, 0.25, 0.2, 0.16, 0.14, 0.125],
                "phase_rel": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
                "morph": [0.6, 0.3, 0.4, 0.5, 0.2]
            },
            "quality": {"rms": 0.35, "peak": 0.95, "snr_db": 45.0, "flags": []},
            "adjacent": {"prev_id": None, "next_id": None,
                        "delta_prev": {"l2_harm": 0.1, "l2_phase": 0.05, "l2_morph": 0.02}},
            "hash": {"features_sha1": "abc123"}
        } for i in range(3)]

    def test_csv_created(self, store, sweep_fingerprints, temp_dir):
        """Test CSV file is created."""
        store.save_sweep(sweep_fingerprints, "test_device")

        csv_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.csv"
        assert csv_path.exists()

    def test_csv_has_headers(self, store, sweep_fingerprints, temp_dir):
        """Test CSV has correct headers."""
        store.save_sweep(sweep_fingerprints, "test_device")

        csv_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.csv"
        with open(csv_path) as f:
            header = f.readline().strip()

        # Check key columns exist
        assert "id" in header
        assert "cv_volts" in header
        assert "freq_hz" in header
        assert "h1" in header  # Harmonics
        assert "ph1" in header  # Phases
        assert "m1" in header  # Morph metrics
        assert "l2_harm" in header  # Deltas

    def test_csv_row_count(self, store, sweep_fingerprints, temp_dir):
        """Test CSV has correct row count."""
        store.save_sweep(sweep_fingerprints, "test_device")

        csv_path = Path(temp_dir) / "devices" / "test_device" / "raw" / "fingerprints.csv"
        with open(csv_path) as f:
            lines = f.readlines()

        # Header + 3 data rows
        assert len(lines) == 4


class TestDeltaComputation:
    """Test L2 delta computations."""

    @pytest.fixture
    def temp_dir(self):
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def store(self, temp_dir):
        return FingerprintStore(temp_dir)

    def test_delta_l2_computation(self, store):
        """Test L2 distance computation."""
        feat_a = {
            "harm_ratio": [1.0, 0.5, 0.3, 0.2, 0.1, 0.1, 0.1, 0.1],
            "phase_rel": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "morph": [0.5, 0.5, 0.5, 0.5, 0.5]
        }
        feat_b = {
            "harm_ratio": [1.0, 0.4, 0.3, 0.2, 0.1, 0.1, 0.1, 0.1],  # h2 changed by 0.1
            "phase_rel": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "morph": [0.5, 0.5, 0.5, 0.5, 0.5]
        }

        delta = store._compute_delta(feat_a, feat_b)

        # L2 for harm should be sqrt(0.1^2) = 0.1
        assert abs(delta["l2_harm"] - 0.1) < 0.01
        assert delta["l2_phase"] == 0.0
        assert delta["l2_morph"] == 0.0

    def test_delta_changes_above_threshold(self, store, temp_dir):
        """Test delta changes are recorded above threshold."""
        fps = [{
            "schema_version": "fingerprint.v1",
            "id": f"test_c{i:03d}",
            "device": {"make": "T", "model": "T", "variant": "v1", "unit_id": "A"},
            "session": {"id": "s1", "utc": "2026-01-01T00:00:00Z", "operator": "t"},
            "capture": {"index": i, "cv": {"chan": "cv1", "volts": i}, "freq_hz": 440.0,
                       "sr_hz": 48000, "n_samples": 1024, "window": "hann", "notes": []},
            "features": {
                "harm_ratio": [1.0 if i == 0 else 0.9, 0.5, 0.33, 0.25, 0.2, 0.16, 0.14, 0.125],
                "phase_rel": [0.0] * 8,
                "morph": [0.5] * 5
            },
            "quality": {"rms": 0.35, "peak": 0.95, "snr_db": 45.0, "flags": []},
            "adjacent": {"prev_id": None, "next_id": None,
                        "delta_prev": {"l2_harm": 0.0, "l2_phase": 0.0, "l2_morph": 0.0}},
            "hash": {"features_sha1": "abc"}
        } for i in range(2)]

        store.save_sweep(fps, "test")

        delta_path = Path(temp_dir) / "devices" / "test" / "deltas"
        delta_files = list(delta_path.glob("*.jsonl"))
        assert len(delta_files) == 1

        with open(delta_files[0]) as f:
            deltas = [json.loads(line) for line in f]

        # h1 changed by 0.1, which is > 0.02 threshold
        assert len(deltas[0]["changes"]) > 0
        assert deltas[0]["changes"][0]["path"] == "harm_ratio[0]"


class TestTrajectoryAnalysis:
    """Test trajectory analysis for evolution summaries."""

    @pytest.fixture
    def temp_dir(self):
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def store(self, temp_dir):
        return FingerprintStore(temp_dir)

    def test_rising_trend_detection(self, store):
        """Test rising trend is detected."""
        x = [0.0, 1.0, 2.0, 3.0, 4.0]
        y = [0.1, 0.2, 0.3, 0.4, 0.5]  # Clearly rising

        result = store._analyze_trajectory(x, y)
        assert result["trend"] == "rising"
        assert result["slope"] > 0

    def test_falling_trend_detection(self, store):
        """Test falling trend is detected."""
        x = [0.0, 1.0, 2.0, 3.0, 4.0]
        y = [0.5, 0.4, 0.3, 0.2, 0.1]  # Clearly falling

        result = store._analyze_trajectory(x, y)
        assert result["trend"] == "falling"
        assert result["slope"] < 0

    def test_flat_trend_detection(self, store):
        """Test flat trend is detected."""
        x = [0.0, 1.0, 2.0, 3.0, 4.0]
        y = [0.5, 0.5, 0.5, 0.5, 0.5]  # Constant

        result = store._analyze_trajectory(x, y)
        assert result["trend"] == "flat"
        assert abs(result["slope"]) < 0.01

    def test_r2_perfect_linear(self, store):
        """Test R² is 1.0 for perfect linear relationship."""
        x = [0.0, 1.0, 2.0, 3.0, 4.0]
        y = [0.0, 0.25, 0.5, 0.75, 1.0]  # Perfect linear

        result = store._analyze_trajectory(x, y)
        assert result["r2"] > 0.99

    def test_min_max_mean(self, store):
        """Test min/max/mean are computed correctly."""
        x = [0.0, 1.0, 2.0]
        y = [0.1, 0.5, 0.3]

        result = store._analyze_trajectory(x, y)
        assert result["min"] == 0.1
        assert result["max"] == 0.5
        assert abs(result["mean"] - 0.3) < 0.01
