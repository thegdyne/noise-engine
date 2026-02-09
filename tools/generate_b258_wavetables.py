#!/usr/bin/env python3
"""Generate wavetable WAV files from Buchla 258 morph map captures.

Reads 26-point morph map JSON files, resamples each 1024-sample waveform
to 2048 samples (SC standard), linearly interpolates to 128 frames,
and writes float32 WAV files for SC BufRd playback.

Usage:
    python tools/generate_b258_wavetables.py

Output:
    packs/buchla_258/generators/b258_wt_saw.wav  (128 * 2048 = 262144 samples)
    packs/buchla_258/generators/b258_wt_sqr.wav  (128 * 2048 = 262144 samples)
"""

import json
import os
import struct
import sys

# Paths relative to project root
SAW_JSON = 'for_claude/morph_map_buchla_258_20260206_140115.json'
SQR_JSON = 'for_claude/morph_map_buchla_258_20260206_140441.json'
OUT_DIR = 'packs/buchla_258/generators'

FRAME_SIZE = 2048    # samples per frame (SC standard)
NUM_FRAMES = 128     # interpolated output frames
SAMPLE_RATE = 48000


def find_project_root():
    path = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(path, 'packs')):
            return path
        path = os.path.dirname(path)
    return None


def load_waveforms(filepath):
    """Load morph map JSON and extract waveforms sorted by cv_index."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    snapshots = data.get('snapshots', [])
    snapshots.sort(key=lambda s: s.get('cv_index', 0))

    waveforms = []
    for snap in snapshots:
        sd = snap.get('snapshot', {})
        wf = sd.get('waveform', [])
        frame = sd.get('frame', {})
        if frame.get('bad_value', 0) != 0:
            print(f"  WARNING: skipping bad snapshot cv_index={snap.get('cv_index')}")
            continue
        waveforms.append([float(s) for s in wf])

    return waveforms


def resample(samples, target_len):
    """Resample with wrap-around for single-cycle waveforms."""
    n = len(samples)
    result = []
    for i in range(target_len):
        pos = i * n / target_len
        idx = int(pos)
        frac = pos - idx
        next_idx = (idx + 1) % n
        result.append(samples[idx] * (1 - frac) + samples[next_idx] * frac)
    return result


def interpolate_frames(frames, target_count):
    """Linearly interpolate frame list from N frames to target_count."""
    n = len(frames)
    frame_len = len(frames[0])
    result = []
    for i in range(target_count):
        if target_count == 1:
            pos = 0.0
        else:
            pos = i * (n - 1) / (target_count - 1)
        idx = int(pos)
        frac = pos - idx
        if idx >= n - 1:
            result.append(frames[-1][:])
        else:
            interp = []
            for j in range(frame_len):
                val = frames[idx][j] * (1 - frac) + frames[idx + 1][j] * frac
                interp.append(val)
            result.append(interp)
    return result


def write_float32_wav(filepath, samples, sample_rate=SAMPLE_RATE):
    """Write mono float32 WAV file."""
    num_samples = len(samples)
    data_size = num_samples * 4

    with open(filepath, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        # fmt chunk (IEEE float)
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 3))           # IEEE_FLOAT
        f.write(struct.pack('<H', 1))           # mono
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate * 4))  # byte rate
        f.write(struct.pack('<H', 4))           # block align
        f.write(struct.pack('<H', 32))          # bits per sample
        # data chunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        for s in samples:
            f.write(struct.pack('<f', s))


def process_morph_map(json_path, wav_path, label):
    """Full pipeline: JSON → resampled → interpolated → WAV."""
    print(f"\n=== {label} ===")
    print(f"  Source: {json_path}")

    waveforms = load_waveforms(json_path)
    print(f"  Loaded {len(waveforms)} waveforms ({len(waveforms[0])} samples each)")

    # Resample 1024 → 2048
    resampled = [resample(wf, FRAME_SIZE) for wf in waveforms]
    print(f"  Resampled to {FRAME_SIZE} samples per frame")

    # Interpolate 26 → 128 frames
    interpolated = interpolate_frames(resampled, NUM_FRAMES)
    print(f"  Interpolated to {NUM_FRAMES} frames")

    # Flatten to single buffer
    flat = []
    for frame in interpolated:
        flat.extend(frame)
    print(f"  Total samples: {len(flat)} ({NUM_FRAMES} x {FRAME_SIZE})")

    # Write WAV
    write_float32_wav(wav_path, flat)
    file_size = os.path.getsize(wav_path)
    print(f"  Written: {wav_path} ({file_size:,} bytes)")


def main():
    root = find_project_root()
    if root is None:
        print("ERROR: Could not find project root")
        sys.exit(1)

    saw_json = os.path.join(root, SAW_JSON)
    sqr_json = os.path.join(root, SQR_JSON)
    out_dir = os.path.join(root, OUT_DIR)

    if not os.path.exists(saw_json):
        print(f"ERROR: SAW morph map not found: {saw_json}")
        sys.exit(1)
    if not os.path.exists(sqr_json):
        print(f"ERROR: SQR morph map not found: {sqr_json}")
        sys.exit(1)

    process_morph_map(saw_json, os.path.join(out_dir, 'b258_wt_saw.wav'), 'SAW')
    process_morph_map(sqr_json, os.path.join(out_dir, 'b258_wt_sqr.wav'), 'SQR')

    print("\nDone. WAV files ready for SC buffer loading.")


if __name__ == '__main__':
    main()
