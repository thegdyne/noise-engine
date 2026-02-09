"""Wavetable loader for B258 Telemetry Wavetable generator.

Reads morph map JSON captures from hardware telemetry and uploads
raw waveform data to SuperCollider via OSC. SC converts to wavetable
format and loads into pre-allocated VOsc buffer banks.

Data contract:
  - 26 snapshots per JSON (ordered by cv_index)
  - 1024 samples per waveform
  - No bad_value flags
"""

import json
import logging
import os
import time

logger = logging.getLogger(__name__)

# Wavetable asset paths (relative to project root)
_WAVETABLE_ASSETS = {
    'saw': 'wavetables/258__sine-to-saw__26p__20260206_140115.json',
    'sqr': 'wavetables/258__sine-to-square__26p__20260206_140441.json',
}

EXPECTED_SNAPSHOTS = 26
EXPECTED_WAVEFORM_LENGTH = 1024

# OSC path for uploading waveform data to SC
OSC_PATH_WT_LOAD = '/noise/b258_wt/load'


def _find_project_root():
    """Find project root by walking up from this file's location."""
    path = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(path, 'packs')):
            return path
        path = os.path.dirname(path)
    return None


def _load_morph_map(filepath):
    """Load and validate a morph map JSON file.

    Returns:
        list: 26 waveforms (each a list of 1024 floats), or None on error.
    """
    if not os.path.exists(filepath):
        logger.error(f"Wavetable file not found: {filepath}")
        return None

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read wavetable JSON {filepath}: {e}")
        return None

    snapshots = data.get('snapshots', [])
    if len(snapshots) != EXPECTED_SNAPSHOTS:
        logger.error(
            f"Expected {EXPECTED_SNAPSHOTS} snapshots in {filepath}, "
            f"got {len(snapshots)}"
        )
        return None

    # Sort by cv_index to ensure correct morph order
    snapshots.sort(key=lambda s: s.get('cv_index', 0))

    waveforms = []
    for i, snap in enumerate(snapshots):
        snapshot_data = snap.get('snapshot', {})
        frame = snapshot_data.get('frame', {})

        # Validate no bad captures
        if frame.get('bad_value', 0) != 0:
            logger.error(
                f"Snapshot {i} in {filepath} has bad_value="
                f"{frame.get('bad_value')}"
            )
            return None

        waveform = snapshot_data.get('waveform', [])
        if len(waveform) != EXPECTED_WAVEFORM_LENGTH:
            logger.error(
                f"Snapshot {i} in {filepath}: expected "
                f"{EXPECTED_WAVEFORM_LENGTH} samples, got {len(waveform)}"
            )
            return None

        waveforms.append([float(s) for s in waveform])

    return waveforms


def upload_wavetables(osc_client):
    """Load wavetable JSON files and upload waveform data to SuperCollider.

    Sends raw 1024-sample waveforms via OSC. SC-side handler converts
    to wavetable format and loads into pre-allocated VOsc buffers.

    Args:
        osc_client: pythonosc SimpleUDPClient instance.

    Returns:
        True if all tables uploaded successfully, False otherwise.
    """
    root = _find_project_root()
    if root is None:
        logger.error("Could not find project root for wavetable loading")
        return False

    success = True
    total_uploaded = 0

    for table_type_idx, (table_name, rel_path) in enumerate(
        _WAVETABLE_ASSETS.items()
    ):
        filepath = os.path.join(root, rel_path)
        logger.info(f"Loading {table_name} wavetables from {filepath}")

        waveforms = _load_morph_map(filepath)
        if waveforms is None:
            logger.error(f"Failed to load {table_name} wavetables — skipping")
            success = False
            continue

        # Send each waveform to SC (1024 floats per message)
        for table_index, waveform in enumerate(waveforms):
            osc_client.send_message(
                OSC_PATH_WT_LOAD,
                [table_type_idx, table_index] + waveform
            )
            total_uploaded += 1

        # Brief pause between table sets to let SC process
        time.sleep(0.1)

        logger.info(
            f"Uploaded {len(waveforms)} {table_name} wavetables to SC"
        )

    if success:
        logger.info(f"B258 wavetable upload complete: {total_uploaded} tables")

    return success
