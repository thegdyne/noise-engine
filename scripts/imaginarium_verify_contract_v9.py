#!/usr/bin/env python3
"""
imaginarium_verify_contract.py
Phase 0: Generator Contract Verification for Imaginarium

- Regex-based SynthDef arglist parsing (not substring matching)
- Sentinel token verification for SC scripts
- Missing 'seed' arg is ERROR for Imaginarium packs
- PCM-only hash for determinism (handles WAV chunks properly)

Usage:
    python scripts/imaginarium_verify_contract.py [--repo /path/to/noise-engine]
"""

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

VERSION = "9.0"

# =============================================================================
# Contract Definition (SSOT)
# =============================================================================

REQUIRED_SYNTHDEF_ARGS = {
    "out",
    "freqBus", "cutoffBus", "resBus", "attackBus", "decayBus",
    "filterTypeBus", "envEnabledBus", "envSourceBus",
    "clockRateBus", "clockTrigBus", "midiTrigBus", "slotIndex",
    "customBus0", "customBus1", "customBus2", "customBus3", "customBus4",
}

SC_SENTINEL_OK = "IMAGINARIUM_VERIFY_OK"
SC_SENTINEL_FAIL = "IMAGINARIUM_VERIFY_FAIL"
DETERMINISM_SENTINEL_OK = "IMAGINARIUM_DETERMINISM_OK"
DETERMINISM_SENTINEL_FAIL = "IMAGINARIUM_DETERMINISM_FAIL"


# =============================================================================
# SynthDef Arglist Parser
# =============================================================================

_SYNTHDEF_PATTERN = re.compile(
    r'SynthDef\s*\(\s*'
    r'(?P<n>\\[A-Za-z0-9_-]+|"[^"]+")\s*,\s*'
    r'\{\s*\|(?P<args>[^|]+)\|',
    re.DOTALL
)

_SYNTHDEF_ARG_PATTERN = re.compile(
    r'SynthDef\s*\(\s*'
    r'(?P<n>\\[A-Za-z0-9_-]+|"[^"]+")\s*,\s*'
    r'\{\s*arg\s+(?P<args>[^;]+);',
    re.DOTALL
)


def _normalize_synthdef_name(token: str) -> str:
    token = token.strip()
    if token.startswith("\\"):
        return token[1:]
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    return token


def parse_synthdef_arglist(scd_text: str, expected_name: Optional[str] = None) -> tuple[set[str], list[str]]:
    errors = []
    
    if "SynthDef" not in scd_text:
        return set(), ["No SynthDef found in file"]
    
    matches = list(_SYNTHDEF_PATTERN.finditer(scd_text))
    if not matches:
        matches = list(_SYNTHDEF_ARG_PATTERN.finditer(scd_text))
    
    if not matches:
        return set(), ["Could not parse SynthDef arglist"]
    
    if expected_name is not None:
        target_match = None
        for m in matches:
            name = _normalize_synthdef_name(m.group("n"))
            if name == expected_name:
                target_match = m
                break
        if target_match is None:
            found_names = [_normalize_synthdef_name(m.group("n")) for m in matches]
            return set(), [f"SynthDef '{expected_name}' not found (found: {', '.join(found_names)})"]
        matches = [target_match]
    
    m = matches[0]
    raw_args = m.group("args")
    
    args = set()
    for part in raw_args.replace('\n', ' ').replace('\r', '').split(','):
        part = part.strip()
        if not part:
            continue
        arg_name = part.split('=')[0].strip()
        if arg_name:
            args.add(arg_name)
    
    return args, errors


def verify_synthdef_contract(
    scd_path: Path, 
    expected_synthdef: Optional[str] = None,
    is_imaginarium: bool = False
) -> tuple[bool, list[str], list[str]]:
    errors = []
    warnings = []
    
    try:
        content = scd_path.read_text(encoding='utf-8')
    except IOError as e:
        return False, [f"Cannot read file: {e}"], []
    
    args_set, parse_errors = parse_synthdef_arglist(content, expected_name=expected_synthdef)
    if parse_errors:
        return False, parse_errors, []
    
    missing = sorted(REQUIRED_SYNTHDEF_ARGS - args_set)
    if missing:
        errors.append(f"Missing required args: {', '.join(missing)}")
    
    if "seed" not in args_set:
        if is_imaginarium:
            errors.append("Missing 'seed' arg (REQUIRED for Imaginarium)")
        else:
            warnings.append("No 'seed' arg (determinism not guaranteed)")
    
    if "~ensure2ch" not in content:
        warnings.append("Does not call ~ensure2ch")
    if "~envVCA" not in content:
        warnings.append("Does not call ~envVCA")
    
    return len(errors) == 0, errors, warnings


# =============================================================================
# Sentinel Checking
# =============================================================================

def require_sentinel(output: str, ok_token: str, fail_token: str) -> tuple[bool, str]:
    if fail_token in output:
        return False, f"SC reported failure: {fail_token}"
    if ok_token in output:
        return True, "OK"
    return False, f"No sentinel found (expected {ok_token} or {fail_token})"


# =============================================================================
# WAV PCM Extraction
# =============================================================================

def extract_pcm_data(wav_path: Path) -> bytes:
    """Extract raw PCM from WAV by parsing RIFF chunks."""
    with open(wav_path, 'rb') as f:
        riff = f.read(4)
        if riff != b'RIFF':
            raise ValueError(f"Not a RIFF file")
        
        f.read(4)  # file size
        wave = f.read(4)
        if wave != b'WAVE':
            raise ValueError(f"Not a WAVE file")
        
        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                raise ValueError("No 'data' chunk found")
            
            chunk_size = struct.unpack('<I', f.read(4))[0]
            
            if chunk_id == b'data':
                return f.read(chunk_size)
            else:
                skip = chunk_size + (chunk_size % 2)
                f.seek(skip, 1)


def pcm_hash(wav_path: Path) -> str:
    """Hash PCM frames only."""
    try:
        import soundfile as sf
        data, sr = sf.read(str(wav_path), dtype="int16", always_2d=True)
        return hashlib.sha256(data.tobytes()).hexdigest()
    except ImportError:
        pass
    
    try:
        pcm_data = extract_pcm_data(wav_path)
        return hashlib.sha256(pcm_data).hexdigest()
    except Exception:
        raw = wav_path.read_bytes()
        return hashlib.sha256(raw[44:] if len(raw) > 44 else raw).hexdigest()


# =============================================================================
# SC Verification
# =============================================================================

def run_sc_verification(repo: Path) -> tuple[bool, str]:
    # Try versioned names first, then canonical
    for name in ["imaginarium_verify_contract_v9.scd", "imaginarium_verify_contract_v8.scd", "imaginarium_verify_contract.scd"]:
        sc_script = repo / "scripts" / name
        if sc_script.exists():
            break
    else:
        return False, f"Missing verify script in scripts/ (tried v9, v8, canonical)"
    
    try:
        result = subprocess.run(
            ["sclang", str(sc_script)],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        
        passed, reason = require_sentinel(output, SC_SENTINEL_OK, SC_SENTINEL_FAIL)
        if not passed:
            return False, output + f"\n{reason}"
        
        return True, output
        
    except subprocess.TimeoutExpired:
        return False, "sclang timed out after 60s"
    except FileNotFoundError:
        return False, "sclang not found"


# =============================================================================
# Determinism Test
# =============================================================================

def test_determinism(repo: Path) -> tuple[bool, str]:
    # Try versioned names first, then canonical
    sc_script = None
    for name in ["imaginarium_determinism_test_v9.scd", "imaginarium_determinism_test_v8.scd", "imaginarium_determinism_test.scd"]:
        p = repo / "scripts" / name
        if p.exists():
            sc_script = p
            break
    
    if sc_script is None:
        return True, "SKIP: No determinism test script"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        out1 = tmpdir / "render1.wav"
        out2 = tmpdir / "render2.wav"
        out3 = tmpdir / "render_diff.wav"
        seed_a = 12345
        seed_b = 54321
        
        try:
            # Render twice with same seed
            for out_path in [out1, out2]:
                result = subprocess.run(
                    ["sclang", str(sc_script), str(out_path), str(seed_a)],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                output = (result.stdout or "") + (result.stderr or "")
                passed, reason = require_sentinel(output, DETERMINISM_SENTINEL_OK, DETERMINISM_SENTINEL_FAIL)
                if not passed:
                    return False, f"Render failed: {reason}"
                if not out_path.exists():
                    return False, f"No output file: {out_path}"
            
            hash1 = pcm_hash(out1)
            hash2 = pcm_hash(out2)
            
            if hash1 != hash2:
                return False, f"Same seed produced different PCM:\n  {hash1[:16]}...\n  {hash2[:16]}..."
            
            # Render with different seed
            result = subprocess.run(
                ["sclang", str(sc_script), str(out3), str(seed_b)],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = (result.stdout or "") + (result.stderr or "")
            passed, reason = require_sentinel(output, DETERMINISM_SENTINEL_OK, DETERMINISM_SENTINEL_FAIL)
            if not passed:
                return False, f"Render with different seed failed: {reason}"
            
            hash3 = pcm_hash(out3)
            
            if hash1 == hash3:
                return False, "Different seeds produced identical PCM (seed has no effect)"
            
            return True, f"Determinism OK: same→identical, different→different"
            
        except subprocess.TimeoutExpired:
            return False, "Render timed out"
        except Exception as e:
            return False, f"Error: {e}"


# =============================================================================
# Pack Validation
# =============================================================================

def verify_generator_json(json_path: Path) -> tuple[bool, list[str]]:
    errors = []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    
    if "name" not in config:
        errors.append("Missing 'name'")
    if "synthdef" not in config:
        errors.append("Missing 'synthdef'")
    
    if "custom_params" in config:
        params = config["custom_params"]
        if not isinstance(params, list):
            errors.append("'custom_params' must be array")
        elif len(params) > 5:
            errors.append(f"Too many custom_params: {len(params)}")
    
    return len(errors) == 0, errors


def verify_pack(pack_path: Path, is_imaginarium_pack: bool = False) -> tuple[bool, list[str]]:
    errors = []
    
    manifest_path = pack_path / "manifest.json"
    if not manifest_path.exists():
        return False, ["Missing manifest.json"]
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid manifest.json: {e}"]
    
    required = ["pack_format", "name", "generators"]
    missing = [f for f in required if f not in manifest]
    if missing:
        errors.append(f"manifest.json missing: {', '.join(missing)}")
        return False, errors
    
    generators_dir = pack_path / "generators"
    if not generators_dir.exists():
        errors.append("Missing generators/ directory")
        return False, errors
    
    for gen_stem in manifest["generators"]:
        json_path = generators_dir / f"{gen_stem}.json"
        scd_path = generators_dir / f"{gen_stem}.scd"
        
        if not json_path.exists():
            errors.append(f"{gen_stem}: missing .json")
            continue
        if not scd_path.exists():
            errors.append(f"{gen_stem}: missing .scd")
            continue
        
        json_ok, json_errors = verify_generator_json(json_path)
        for e in json_errors:
            errors.append(f"{gen_stem}.json: {e}")
        
        try:
            with open(json_path, 'r') as f:
                gen_config = json.load(f)
            expected_synthdef = gen_config.get("synthdef")
        except:
            expected_synthdef = None
        
        scd_ok, scd_errors, scd_warnings = verify_synthdef_contract(
            scd_path,
            expected_synthdef=expected_synthdef,
            is_imaginarium=is_imaginarium_pack
        )
        for e in scd_errors:
            errors.append(f"{gen_stem}.scd: {e}")
        for w in scd_warnings:
            print(f"  WARN {gen_stem}.scd: {w}")
    
    return len(errors) == 0, errors


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description=f"Imaginarium Phase 0 Verification v{VERSION}")
    parser.add_argument("--repo", type=Path, default=Path(os.environ.get("NOISE_ENGINE_REPO", ".")))
    parser.add_argument("--skip-sc", action="store_true")
    parser.add_argument("--skip-determinism", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s v{VERSION}")
    args = parser.parse_args()
    
    repo = args.repo.resolve()
    
    print("=" * 60)
    print(f"IMAGINARIUM PHASE 0 VERIFICATION v{VERSION}")
    print("=" * 60)
    print(f"Repository: {repo}")
    print()
    
    if not (repo / "supercollider").exists():
        print(f"ERROR: Not a Noise Engine repo")
        return 2
    
    results = {}
    
    # SC Contract
    print("[1/3] SuperCollider Contract")
    print("-" * 40)
    if args.skip_sc:
        print("  SKIP")
        results["sc_contract"] = True
    else:
        passed, output = run_sc_verification(repo)
        for line in output.split('\n'):
            if any(x in line for x in ['OK:', 'FAIL:', 'WARN:', 'Loaded:', 'IMAGINARIUM']):
                print(f"  {line}")
        results["sc_contract"] = passed
        print(f"  Result: {'PASS' if passed else 'FAIL'}")
    print()
    
    # Determinism
    print("[2/3] Determinism Test")
    print("-" * 40)
    if args.skip_determinism:
        print("  SKIP")
        results["determinism"] = True
    else:
        passed, msg = test_determinism(repo)
        print(f"  {msg}")
        results["determinism"] = passed
        print(f"  Result: {'PASS' if passed else 'FAIL'}")
    print()
    
    # Smoke Pack
    print("[3/3] Smoke Pack")
    print("-" * 40)
    smoke_pack = repo / "packs" / "_imaginarium_contract_smoke"
    if smoke_pack.exists():
        passed, pack_errors = verify_pack(smoke_pack, is_imaginarium_pack=True)
        for e in pack_errors:
            print(f"  ERROR: {e}")
        results["smoke_pack"] = passed
        print(f"  Result: {'PASS' if passed else 'FAIL'}")
    else:
        print("  SKIP: No smoke pack")
        results["smoke_pack"] = True
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    
    print()
    if all_passed:
        print("✓ Phase 0 verified")
        return 0
    else:
        print("✗ Phase 0 FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
