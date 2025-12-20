#!/usr/bin/env python3
"""
imaginarium_determinism_test.py
Determinism verification: proves seed contract works both ways

Tests:
1. Same seed → identical PCM (reproducibility)
2. Different seed → different PCM (seed actually affects output)

VERSION: 6.0
"""

import argparse
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "6.0"

DETERMINISM_SENTINEL_OK = "IMAGINARIUM_DETERMINISM_OK"
DETERMINISM_SENTINEL_FAIL = "IMAGINARIUM_DETERMINISM_FAIL"


def extract_pcm_data(wav_path: Path) -> bytes:
    """
    Extract raw PCM data from WAV file by parsing RIFF chunks.
    
    Handles arbitrary chunk ordering (doesn't assume 44-byte header).
    Returns the contents of the 'data' chunk only.
    """
    with open(wav_path, 'rb') as f:
        # Verify RIFF header
        riff = f.read(4)
        if riff != b'RIFF':
            raise ValueError(f"Not a RIFF file: {riff}")
        
        file_size = struct.unpack('<I', f.read(4))[0]
        wave = f.read(4)
        if wave != b'WAVE':
            raise ValueError(f"Not a WAVE file: {wave}")
        
        # Scan chunks until we find 'data'
        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                raise ValueError("Reached EOF without finding 'data' chunk")
            
            chunk_size = struct.unpack('<I', f.read(4))[0]
            
            if chunk_id == b'data':
                # Found it - read PCM data
                return f.read(chunk_size)
            else:
                # Skip this chunk (pad to even boundary per RIFF spec)
                skip = chunk_size + (chunk_size % 2)
                f.seek(skip, 1)


def pcm_hash(wav_path: Path) -> str:
    """Hash PCM frames only (ignores WAV header/metadata chunks)."""
    try:
        # Try soundfile first (most robust)
        import soundfile as sf
        data, sr = sf.read(str(wav_path), dtype="int16", always_2d=True)
        return hashlib.sha256(data.tobytes()).hexdigest()
    except ImportError:
        pass
    
    # Fallback: parse RIFF chunks manually
    try:
        pcm_data = extract_pcm_data(wav_path)
        return hashlib.sha256(pcm_data).hexdigest()
    except Exception as e:
        # Last resort: skip 44 bytes (standard header, no extra chunks)
        raw = wav_path.read_bytes()
        if len(raw) > 44:
            return hashlib.sha256(raw[44:]).hexdigest()
        return hashlib.sha256(raw).hexdigest()


def render_with_seed(sc_script: Path, output_path: Path, seed: int, repo: Path) -> tuple[bool, str]:
    """Render using SC determinism script."""
    try:
        result = subprocess.run(
            ["sclang", str(sc_script), str(output_path), str(seed)],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = (result.stdout or "") + (result.stderr or "")
        
        if DETERMINISM_SENTINEL_FAIL in output:
            return False, f"Render failed (seed={seed}): sentinel FAIL"
        if DETERMINISM_SENTINEL_OK not in output:
            if not output_path.exists():
                return False, f"No output file and no sentinel (seed={seed})"
        
        if not output_path.exists():
            return False, f"No output file (seed={seed})"
        
        return True, "OK"
        
    except subprocess.TimeoutExpired:
        return False, "Render timed out"
    except FileNotFoundError:
        return False, "sclang not found"


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Imaginarium Determinism Test v{VERSION}")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(os.environ.get("NOISE_ENGINE_REPO", ".")),
        help="Path to Noise Engine repository"
    )
    args = parser.parse_args()
    
    repo = args.repo.resolve()
    
    print("=" * 60)
    print(f"IMAGINARIUM DETERMINISM TEST v{VERSION}")
    print("=" * 60)
    print()
    
    # Find SC script (try versioned, then canonical)
    sc_script = None
    for name in ["imaginarium_determinism_test_v6.scd", "imaginarium_determinism_test_v5.scd", "imaginarium_determinism_test.scd"]:
        p = repo / "scripts" / name
        if p.exists():
            sc_script = p
            break
    
    if sc_script is None:
        print("ERROR: No determinism test script found in scripts/")
        return 2
    
    print(f"Using: {sc_script.name}")
    print()
    
    results = {}
    hash1 = None  # Will hold first render hash for comparison
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # ============================================================
        # TEST 1: Same seed → identical PCM
        # ============================================================
        print("[1/2] Testing: Same seed → identical output")
        print("-" * 40)
        
        seed_a = 12345
        out1 = tmpdir / "same_seed_1.wav"
        out2 = tmpdir / "same_seed_2.wav"
        
        ok1, msg1 = render_with_seed(sc_script, out1, seed_a, repo)
        if not ok1:
            print(f"  FAIL: First render: {msg1}")
            results["same_seed"] = False
        else:
            ok2, msg2 = render_with_seed(sc_script, out2, seed_a, repo)
            if not ok2:
                print(f"  FAIL: Second render: {msg2}")
                results["same_seed"] = False
            else:
                hash1 = pcm_hash(out1)
                hash2 = pcm_hash(out2)
                
                if hash1 == hash2:
                    print(f"  PASS: Identical PCM ({hash1[:16]}...)")
                    results["same_seed"] = True
                else:
                    print(f"  FAIL: Different PCM!")
                    print(f"    render1: {hash1[:16]}...")
                    print(f"    render2: {hash2[:16]}...")
                    results["same_seed"] = False
        
        print()
        
        # ============================================================
        # TEST 2: Different seed → different PCM
        # ============================================================
        print("[2/2] Testing: Different seed → different output")
        print("-" * 40)
        
        if hash1 is None:
            print("  SKIP: Cannot run (first test failed)")
            results["diff_seed"] = False
        else:
            seed_b = 54321
            out3 = tmpdir / "diff_seed.wav"
            
            ok3, msg3 = render_with_seed(sc_script, out3, seed_b, repo)
            if not ok3:
                print(f"  FAIL: Render with seed {seed_b}: {msg3}")
                results["diff_seed"] = False
            else:
                hash3 = pcm_hash(out3)
                
                if hash1 != hash3:
                    print(f"  PASS: Different PCM (seed {seed_a} vs {seed_b})")
                    print(f"    seed {seed_a}: {hash1[:16]}...")
                    print(f"    seed {seed_b}: {hash3[:16]}...")
                    results["diff_seed"] = True
                else:
                    print(f"  FAIL: Identical PCM despite different seeds!")
                    print(f"  The seed has NO EFFECT on the output signal.")
                    results["diff_seed"] = False
        
        print()
    
    # ============================================================
    # Summary
    # ============================================================
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    print()
    if all_passed:
        print("✓ Determinism contract verified")
        print("  - Same seed → identical output (reproducible)")
        print("  - Different seed → different output (seed works)")
        return 0
    else:
        print("✗ Determinism contract FAILED")
        if not results.get("same_seed", True):
            print("  - Same seed produced different output (non-deterministic)")
        if not results.get("diff_seed", True):
            print("  - Different seed produced same output (seed has no effect)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
