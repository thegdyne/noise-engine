"""
Fingerprint Datastore v1

JSONL-based storage with CSV export and pre-computed deltas.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


class FingerprintStore:
    """Manages fingerprint storage and retrieval."""

    def __init__(self, base_path: str = "fingerprints"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._ensure_structure()

    def _ensure_structure(self):
        """Create directory structure."""
        (self.base_path / "schema").mkdir(exist_ok=True)
        (self.base_path / "devices").mkdir(exist_ok=True)
        (self.base_path / "comparisons").mkdir(exist_ok=True)

    def get_device_path(self, device_key: str) -> Path:
        """Get or create device directory."""
        device_path = self.base_path / "devices" / device_key
        for subdir in ["raw", "sweeps", "deltas", "summaries"]:
            (device_path / subdir).mkdir(parents=True, exist_ok=True)
        return device_path

    def save_fingerprint(self, fingerprint: Dict, device_key: str = None) -> str:
        """
        Append fingerprint to JSONL store.

        Returns fingerprint ID.
        """
        if device_key is None:
            d = fingerprint["device"]
            device_key = f"{d['model'].lower()}_{d['unit_id'].lower()}"
            device_key = device_key.replace(" ", "_")

        device_path = self.get_device_path(device_key)
        jsonl_path = device_path / "raw" / "fingerprints.jsonl"

        # Update adjacent links
        prev_fp = self._get_last_fingerprint(jsonl_path)
        if prev_fp:
            fingerprint["adjacent"]["prev_id"] = prev_fp["id"]
            fingerprint["adjacent"]["delta_prev"] = self._compute_delta(
                prev_fp["features"], fingerprint["features"]
            )

        with open(jsonl_path, "a") as f:
            f.write(json.dumps(fingerprint) + "\n")

        return fingerprint["id"]

    def save_sweep(self, fingerprints: List[Dict], device_key: str,
                   sweep_name: str = None) -> str:
        """
        Save a complete CV sweep with all derived files.

        Returns sweep ID.
        """
        if not fingerprints:
            raise ValueError("Empty fingerprint list")

        device_path = self.get_device_path(device_key)

        # Generate sweep name
        if sweep_name is None:
            session_id = fingerprints[0]["session"]["id"]
            cv_chan = fingerprints[0]["capture"]["cv"]["chan"]
            sweep_name = f"{session_id}_{cv_chan}"

        # Link adjacent fingerprints
        for i, fp in enumerate(fingerprints):
            if i > 0:
                fp["adjacent"]["prev_id"] = fingerprints[i - 1]["id"]
                fp["adjacent"]["delta_prev"] = self._compute_delta(
                    fingerprints[i - 1]["features"], fp["features"]
                )
            if i < len(fingerprints) - 1:
                fp["adjacent"]["next_id"] = fingerprints[i + 1]["id"]

        # Save JSONL
        jsonl_path = device_path / "raw" / "fingerprints.jsonl"
        with open(jsonl_path, "a") as f:
            for fp in fingerprints:
                f.write(json.dumps(fp) + "\n")

        # Save CSV
        self._export_csv(fingerprints, device_path / "raw" / "fingerprints.csv")

        # Save sweep definition
        sweep_def = {
            "schema_version": "sweep.v1",
            "sweep_id": sweep_name,
            "device_key": device_key,
            "cv_chan": fingerprints[0]["capture"]["cv"]["chan"],
            "points": len(fingerprints),
            "cv_range": [
                fingerprints[0]["capture"]["cv"]["volts"],
                fingerprints[-1]["capture"]["cv"]["volts"]
            ],
            "ids": [
                {"id": fp["id"], "volts": fp["capture"]["cv"]["volts"]}
                for fp in fingerprints
            ]
        }
        sweep_path = device_path / "sweeps" / f"{sweep_name}.json"
        with open(sweep_path, "w") as f:
            json.dump(sweep_def, f, indent=2)

        # Save deltas
        deltas = self._compute_sweep_deltas(fingerprints)
        delta_path = device_path / "deltas" / f"{sweep_name}.jsonl"
        with open(delta_path, "w") as f:
            for delta in deltas:
                f.write(json.dumps(delta) + "\n")

        # Compute and save harmonic evolution summary
        summary = self._compute_harmonic_evolution(fingerprints)
        summary_path = device_path / "summaries" / f"{sweep_name}_evolution.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        # Update device manifest
        self._update_manifest(device_path, fingerprints, sweep_name)

        # Update index
        self._update_index()

        return sweep_name

    def _compute_delta(self, feat_a: Dict, feat_b: Dict) -> Dict:
        """Compute L2 distances between feature vectors."""
        def l2(a, b):
            return float(np.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))))
        return {
            "l2_harm": round(l2(feat_a["harm_ratio"], feat_b["harm_ratio"]), 4),
            "l2_phase": round(l2(feat_a["phase_rel"], feat_b["phase_rel"]), 4),
            "l2_morph": round(l2(feat_a["morph"], feat_b["morph"]), 4)
        }

    def _compute_sweep_deltas(self, fingerprints: List[Dict]) -> List[Dict]:
        """Compute delta objects for entire sweep."""
        deltas = []
        for i in range(1, len(fingerprints)):
            a, b = fingerprints[i - 1], fingerprints[i]
            delta = {
                "schema_version": "delta.v1",
                "a_id": a["id"],
                "b_id": b["id"],
                "cv_delta": round(b["capture"]["cv"]["volts"] - a["capture"]["cv"]["volts"], 4),
                "l2_harm": b["adjacent"]["delta_prev"]["l2_harm"],
                "l2_phase": b["adjacent"]["delta_prev"]["l2_phase"],
                "l2_morph": b["adjacent"]["delta_prev"]["l2_morph"],
            }
            # Add per-feature changes above threshold
            changes = []
            for j, (va, vb) in enumerate(zip(a["features"]["harm_ratio"],
                                              b["features"]["harm_ratio"])):
                if abs(vb - va) > 0.02:
                    changes.append({
                        "path": f"harm_ratio[{j}]",
                        "a": va, "b": vb,
                        "delta": round(vb - va, 4)
                    })
            delta["changes"] = changes
            deltas.append(delta)
        return deltas

    def _compute_harmonic_evolution(self, fingerprints: List[Dict]) -> Dict:
        """Compute trajectory summaries for AI consumption."""
        cv_values = [fp["capture"]["cv"]["volts"] for fp in fingerprints]

        evolution = {
            "schema_version": "evolution.v1",
            "points": len(fingerprints),
            "cv_range": [min(cv_values), max(cv_values)],
            "harmonics": {},
            "morph": {}
        }

        # Analyze each harmonic
        for h in range(8):
            values = [fp["features"]["harm_ratio"][h] for fp in fingerprints]
            evolution["harmonics"][f"h{h + 1}"] = self._analyze_trajectory(cv_values, values)

        # Analyze morph metrics
        morph_names = ["symmetry", "crest", "centroid", "tilt", "brightness"]
        for m, name in enumerate(morph_names):
            values = [fp["features"]["morph"][m] for fp in fingerprints]
            evolution["morph"][name] = self._analyze_trajectory(cv_values, values)

        return evolution

    def _analyze_trajectory(self, x: List[float], y: List[float]) -> Dict:
        """Analyze a single parameter trajectory."""
        x, y = np.array(x), np.array(y)

        # Linear fit
        slope, intercept = np.polyfit(x, y, 1)
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0

        # Trend classification
        if abs(slope) < 0.01:
            trend = "flat"
        elif slope > 0:
            trend = "rising"
        else:
            trend = "falling"

        return {
            "min": round(float(np.min(y)), 4),
            "max": round(float(np.max(y)), 4),
            "mean": round(float(np.mean(y)), 4),
            "trend": trend,
            "slope": round(float(slope), 4),
            "r2": round(float(r2), 3)
        }

    def _export_csv(self, fingerprints: List[Dict], path: Path):
        """Export fingerprints to CSV format."""
        if not fingerprints:
            return

        # Build flat rows
        rows = []
        for fp in fingerprints:
            row = {
                "id": fp["id"],
                "cv_volts": fp["capture"]["cv"]["volts"],
                "freq_hz": fp["capture"]["freq_hz"],
                "rms": fp["quality"]["rms"],
                "peak": fp["quality"]["peak"],
                "snr_db": fp["quality"]["snr_db"],
            }
            # Expand arrays
            for i, v in enumerate(fp["features"]["harm_ratio"]):
                row[f"h{i + 1}"] = v
            for i, v in enumerate(fp["features"]["phase_rel"]):
                row[f"ph{i + 1}"] = v
            for i, v in enumerate(fp["features"]["morph"]):
                row[f"m{i + 1}"] = v
            # Delta
            row["l2_harm"] = fp["adjacent"]["delta_prev"]["l2_harm"]
            row["l2_phase"] = fp["adjacent"]["delta_prev"]["l2_phase"]
            row["l2_morph"] = fp["adjacent"]["delta_prev"]["l2_morph"]
            rows.append(row)

        # Write CSV
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def _get_last_fingerprint(self, jsonl_path: Path) -> Optional[Dict]:
        """Get last fingerprint from JSONL file."""
        if not jsonl_path.exists():
            return None
        with open(jsonl_path, "r") as f:
            last = None
            for line in f:
                if line.strip():
                    last = json.loads(line)
            return last

    def _update_manifest(self, device_path: Path, fingerprints: List[Dict],
                         sweep_name: str):
        """Update device manifest."""
        manifest_path = device_path / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        else:
            manifest = {
                "schema_version": "manifest.v1",
                "device": fingerprints[0]["device"],
                "sessions": [],
                "sweeps": []
            }

        # Add sweep if not present
        if sweep_name not in manifest["sweeps"]:
            manifest["sweeps"].append(sweep_name)

        # Update session
        session_id = fingerprints[0]["session"]["id"]
        if session_id not in [s["id"] for s in manifest["sessions"]]:
            manifest["sessions"].append({
                "id": session_id,
                "utc": fingerprints[0]["session"]["utc"],
                "operator": fingerprints[0]["session"]["operator"]
            })

        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    def _update_index(self):
        """Update top-level index."""
        index = {
            "schema_version": "index.v1",
            "updated_utc": datetime.utcnow().isoformat() + "Z",
            "devices": []
        }

        devices_path = self.base_path / "devices"
        for device_dir in devices_path.iterdir():
            if device_dir.is_dir():
                manifest_path = device_dir / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    index["devices"].append({
                        "key": device_dir.name,
                        "device": manifest.get("device", {}),
                        "sweeps": len(manifest.get("sweeps", [])),
                        "sessions": len(manifest.get("sessions", []))
                    })

        with open(self.base_path / "index.json", "w") as f:
            json.dump(index, f, indent=2)

    def load_sweep(self, device_key: str, sweep_name: str) -> List[Dict]:
        """Load all fingerprints from a sweep."""
        sweep_path = self.base_path / "devices" / device_key / "sweeps" / f"{sweep_name}.json"
        with open(sweep_path, "r") as f:
            sweep_def = json.load(f)

        ids = [item["id"] for item in sweep_def["ids"]]
        return self.load_fingerprints(device_key, ids)

    def load_fingerprints(self, device_key: str, ids: List[str] = None) -> List[Dict]:
        """Load fingerprints by ID (or all if ids=None)."""
        jsonl_path = self.base_path / "devices" / device_key / "raw" / "fingerprints.jsonl"
        fingerprints = []

        with open(jsonl_path, "r") as f:
            for line in f:
                if line.strip():
                    fp = json.loads(line)
                    if ids is None or fp["id"] in ids:
                        fingerprints.append(fp)

        return fingerprints
