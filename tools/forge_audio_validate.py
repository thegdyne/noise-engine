#!/usr/bin/env python3
"""
tools/forge_audio_validate.py
Audio validation for CQD_Forge packs

Renders each generator via NRT and runs:
- Safety gates (silence, clipping, DC, runaway) from Imaginarium
- Loudness analysis with trim recommendations

Usage:
    python tools/forge_audio_validate.py packs/nerve_glow/ --render
    python tools/forge_audio_validate.py packs/nerve_glow/ --render --env-mode drone
    python tools/forge_audio_validate.py packs/nerve_glow/ --render --env-mode clocked
    python tools/forge_audio_validate.py packs/nerve_glow/ --render -v

Env modes:
    drone   - Sustained gate (for pad/drone generators)
    clocked - Rhythmic triggers at ~3Hz (for percussive/rhythmic generators)
    both    - Test both modes, fail if either fails (default)
"""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

# Target RMS for balanced output (-18 dBFS is standard for synths)
TARGET_RMS_DB = -18.0
# Headroom target (peak should be below this)
TARGET_PEAK_DB = -3.0


class SafetyStatus(Enum):
    PASS = "pass"
    SILENCE = "silence"
    SPARSE = "sparse"
    CLIPPING = "clipping"
    DC_OFFSET = "dc_offset"
    RUNAWAY = "runaway"
    RENDER_FAILED = "render_failed"


@dataclass
class SafetyConfig:
    """Audio safety thresholds from IMAGINARIUM_SPEC §9."""
    sample_rate: int = 48000
    frame_length: int = 2048
    hop_length: int = 1024
    min_rms_db: float = -40.0
    active_threshold_db: float = -45.0
    min_active_frames_pct: float = 0.30
    max_sample_value: float = 0.999
    max_dc_offset: float = 0.01
    max_level_growth_db: float = 6.0
    
    # Sparse/impulsive sound detection
    # If crest factor > this, relax RMS thresholds (it's impulsive, not silent)
    impulsive_crest_db: float = 15.0
    impulsive_min_rms_db: float = -55.0  # Relaxed threshold for impulsive sounds
    impulsive_min_active_pct: float = 0.05  # Much lower for sparse sounds


@dataclass
class ValidationResult:
    """Result for a single generator."""
    generator_id: str
    passed: bool
    status: SafetyStatus
    peak_db: float = -100.0
    rms_db: float = -100.0
    trim_adjustment: float = 0.0
    active_pct: float = 0.0
    dc_offset: float = 0.0
    level_growth_db: float = 0.0
    crest_db: float = 0.0
    is_impulsive: bool = False
    error: Optional[str] = None


def find_sclang() -> Optional[Path]:
    """Find sclang binary."""
    candidates = []
    
    sclang_in_path = shutil.which("sclang")
    if sclang_in_path:
        candidates.append(Path(sclang_in_path))
    
    # macOS
    candidates.extend([
        Path("/Applications/SuperCollider.app/Contents/MacOS/sclang"),
        Path("/Applications/SuperCollider/SuperCollider.app/Contents/MacOS/sclang"),
        Path.home() / "Applications/SuperCollider.app/Contents/MacOS/sclang",
    ])
    
    # Linux
    candidates.extend([
        Path("/usr/bin/sclang"),
        Path("/usr/local/bin/sclang"),
    ])
    
    for path in candidates:
        if path.exists():
            return path
    
    return None


def load_audio(path: Path) -> Tuple[any, int]:
    """Load audio file, return (samples, sample_rate)."""
    try:
        import soundfile as sf
        data, sr = sf.read(path, dtype='float32')
        return data, sr
    except ImportError:
        pass
    
    try:
        import librosa
        data, sr = librosa.load(path, sr=None, mono=False)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        else:
            data = data.T
        return data.astype('float32'), sr
    except ImportError:
        pass
    
    raise ImportError("Install soundfile or librosa: pip install soundfile")


def rms_db(samples) -> float:
    """Calculate RMS level in dB."""
    import numpy as np
    rms = np.sqrt(np.mean(samples ** 2))
    if rms < 1e-10:
        return -100.0
    return 20 * np.log10(rms)


def peak_db(samples) -> float:
    """Calculate peak level in dB."""
    import numpy as np
    peak = np.max(np.abs(samples))
    if peak < 1e-10:
        return -100.0
    return 20 * np.log10(peak)


def transform_synthdef_for_nrt(scd_content: str, synthdef_name: str) -> str:
    """
    Transform a Forge SynthDef for NRT rendering.
    
    Replaces bus reads with fixed values, helper functions with inline equivalents.
    Based on imaginarium/render.py _transform_for_nrt().
    """
    code = scd_content
    
    # === 1. REPLACE BUS READS WITH FIXED VALUES ===
    code = re.sub(r'In\.kr\(freqBus\)', '220', code)
    code = re.sub(r'In\.kr\(cutoffBus\)', '2000', code)
    code = re.sub(r'In\.kr\(resBus\)', '0.5', code)
    code = re.sub(r'In\.kr\(attackBus\)', '0.1', code)
    code = re.sub(r'In\.kr\(decayBus\)', '0.5', code)
    code = re.sub(r'In\.kr\(filterTypeBus\)', '0', code)
    code = re.sub(r'In\.kr\(envSourceBus\)', '0', code)
    code = re.sub(r'In\.kr\(envEnabledBus\)', '1', code)
    code = re.sub(r'In\.kr\(clockRateBus\)', '6', code)
    code = re.sub(r'In\.kr\(portamentoBus\)', '0', code)
    code = re.sub(r'In\.kr\(~params\[\\amplitude\]\)', '0.5', code)
    
    # Custom param buses -> use defaults (0.5)
    for i in range(5):
        code = re.sub(rf'In\.kr\(customBus{i}\)', '0.5', code)
    
    # === CHANGE 1: Trigger buses — handle both .ar and .kr, preserve channel count ===
    code = re.sub(r'In\.ar\(clockTrigBus,\s*(\d+)\)', r'DC.ar(0) ! \1', code)
    code = re.sub(r'In\.kr\(clockTrigBus,\s*(\d+)\)', r'DC.kr(0) ! \1', code)
    code = re.sub(r'In\.ar\(midiTrigBus,\s*(\d+)\)',  r'DC.ar(0) ! \1', code)
    code = re.sub(r'In\.kr\(midiTrigBus,\s*(\d+)\)',  r'DC.kr(0) ! \1', code)
    
    # === 2. REPLACE HELPER FUNCTIONS ===
    
    # ~multiFilter -> simple RLPF
    code = re.sub(
        r'~multiFilter\.\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
        r'RLPF.ar(\1, (\2).clip(20, 18000), (\3).clip(0.1, 2))',
        code
    )
    
    # ~stereoSpread -> Pan2
    code = re.sub(
        r'~stereoSpread\.\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^)]+\s*\)',
        r'Pan2.ar(\1, 0)',
        code
    )
    
    # ~envVCA -> simple ADSR envelope
    code = re.sub(
        r'~envVCA\.\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^,]+\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^,]+\s*,\s*[^)]+\s*\)',
        r'(\1 * EnvGen.kr(Env.adsr((\2).linexp(0,1,0.001,2), (\3).linexp(0,1,0.05,4), 0.7, 0.3), \\gate.kr(1), doneAction: 2) * \4)',
        code
    )
    
    # ~ensure2ch -> pass through (we use Pan2 which is already stereo)
    code = re.sub(r'~ensure2ch\.\(\s*([^)]+)\s*\)', r'\1', code)

    # === 3. HANDLE SELECT.AR TRIGGER PATTERN ===
    code = re.sub(
        r'trig\s*=\s*Select\.ar\(envSource[^;]+\]\);',
        'trig = Impulse.ar(3);  // NRT: continuous trigger',
        code,
        flags=re.DOTALL
    )

    # Also handle envTrig = Select.ar(envSource...) pattern
    code = re.sub(
        r'envTrig\s*=\s*Select\.ar\(envSource[^;]+\]\);',
        'envTrig = Impulse.ar(3);  // NRT: continuous trigger',
        code,
        flags=re.DOTALL
    )

    # Replace slotIndex
    code = re.sub(r'slotIndex', '0', code)
    
    # === CHANGE 3: Neutralize acid_bloom-style amp selection before arg stripping ===
    # This replaces the complex In.kr(Select.kr(...)) pattern with a constant 0.5
    code = re.sub(
        r'In\.kr\(\s*Select\.kr\(\s*\(\s*ampBus\s*>=\s*0\s*\)\s*,\s*\[\s*fallbackAmpBus\s*,\s*ampBus\s*\]\s*\)\s*\)',
        '0.5',
        code
    )
    
    # === CHANGE 2: SIMPLIFY ARGUMENT LIST — keep ampBus for generators that reference it ===
    code = re.sub(
        r'\|\s*out\s*,\s*freqBus\s*,[^|]+\|',
        '|out=0, gate=1, ampBus=(-1)|',
        code
    )
    code = re.sub(
        r'\{\s*\|out,\s*freqBus,\s*cutoffBus[^|]+\|',
        '{ |out=0, gate=1, ampBus=(-1)|',
        code,
        flags=re.DOTALL
    )
    
    # === 5. RENAME SYNTHDEF ===
    code = re.sub(
        r'SynthDef\(\\[^,]+,',
        f'SynthDef(\\\\{synthdef_name},',
        code
    )
    
    # Remove .add; and wrap
    code = re.sub(r'\)\.add;', ');', code)
    code = re.sub(r'(SynthDef\()', r'def = \1', code.strip(), count=1)
    
    # Remove postln lines
    lines = code.split('\n')
    lines = [l for l in lines if 'postln' not in l]
    code = '\n'.join(lines)
    
    # Remove RandSeed (not needed for NRT)
    code = re.sub(r'RandSeed\.ir\([^;]+;\s*', '', code)
    
    return code


def generate_nrt_script(
    synthdef_code: str,
    synthdef_name: str,
    output_path: Path,
    duration: float = 3.0,
    sample_rate: int = 48000,
    env_mode: str = "drone",
) -> str:
    """
    Generate sclang script for NRT rendering.
    
    Args:
        env_mode: "drone" (sustained gate) or "clocked" (rhythmic triggers)
    """
    output_str = str(output_path).replace("\\", "\\\\").replace('"', '\\"')
    
    if env_mode == "clocked":
        # Rhythmic gate pattern: 3 Hz triggers with 0.2s gate time
        # This exercises attack/decay envelopes properly
        gate_events = []
        t = 0.001
        gate_interval = 0.333  # ~3 Hz
        gate_duration = 0.2
        while t < duration - 0.5:
            gate_events.append(f'    [{t:.3f}, [\\n_set, 1000, \\gate, 1]],')
            gate_events.append(f'    [{t + gate_duration:.3f}, [\\n_set, 1000, \\gate, 0]],')
            t += gate_interval
        gate_score = '\n'.join(gate_events)
        
        return f'''
// Forge NRT Render: {synthdef_name} (CLOCKED mode)
(
var def, defBytes, score, options;

{synthdef_code}

defBytes = def.asBytes;

score = Score([
    [0.0, [\\d_recv, defBytes]],
    [0.001, [\\s_new, \\{synthdef_name}, 1000, 0, 0, \\gate, 0]],
{gate_score}
    [{duration + 0.3:.3f}, [\\c_set, 0, 0]]
]);

options = ServerOptions.new;
options.numOutputBusChannels = 2;
options.sampleRate = {sample_rate};

score.recordNRT(
    nil,
    "{output_str}",
    sampleRate: {sample_rate},
    headerFormat: "WAV",
    sampleFormat: "int16",
    options: options,
    duration: {duration + 0.5:.2f},
    action: {{ "RENDER_COMPLETE".postln; 0.exit }}
);
)
'''
    else:
        # Drone mode: sustained gate
        return f'''
// Forge NRT Render: {synthdef_name} (DRONE mode)
(
var def, defBytes, score, options;

{synthdef_code}

defBytes = def.asBytes;

score = Score([
    [0.0, [\\d_recv, defBytes]],
    [0.001, [\\s_new, \\{synthdef_name}, 1000, 0, 0]],
    [{duration - 0.3:.3f}, [\\n_set, 1000, \\gate, 0]],
    [{duration + 0.3:.3f}, [\\c_set, 0, 0]]
]);

options = ServerOptions.new;
options.numOutputBusChannels = 2;
options.sampleRate = {sample_rate};

score.recordNRT(
    nil,
    "{output_str}",
    sampleRate: {sample_rate},
    headerFormat: "WAV",
    sampleFormat: "int16",
    options: options,
    duration: {duration + 0.5:.2f},
    action: {{ "RENDER_COMPLETE".postln; 0.exit }}
);
)
'''


def run_safety_checks(
    audio_path: Path,
    config: SafetyConfig,
) -> Tuple[SafetyStatus, Dict[str, float]]:
    """Run safety gate checks on audio file."""
    import numpy as np
    
    try:
        samples, sr = load_audio(audio_path)
    except Exception as e:
        return SafetyStatus.RENDER_FAILED, {"error": str(e)}
    
    # Convert to mono for analysis
    if samples.ndim > 1:
        mono = np.mean(samples, axis=1)
    else:
        mono = samples
    
    details = {}
    
    # === Metrics ===
    details["peak_db"] = peak_db(samples)
    details["rms_db"] = rms_db(mono)
    
    # === Crest factor detection (peak - RMS in dB) ===
    crest_factor = details["peak_db"] - details["rms_db"]
    details["crest_db"] = crest_factor
    is_impulsive = crest_factor > config.impulsive_crest_db
    details["is_impulsive"] = is_impulsive
    
    # Use relaxed thresholds for impulsive sounds
    min_rms = config.impulsive_min_rms_db if is_impulsive else config.min_rms_db
    min_active = config.impulsive_min_active_pct if is_impulsive else config.min_active_frames_pct
    
    # === Gate 1: Audibility ===
    if details["rms_db"] < min_rms:
        return SafetyStatus.SILENCE, details
    
    # === Gate 2: Active frames ===
    n_frames = 1 + (len(mono) - config.frame_length) // config.hop_length
    active_frames = 0
    
    for i in range(n_frames):
        start = i * config.hop_length
        end = start + config.frame_length
        frame = mono[start:end]
        if rms_db(frame) > config.active_threshold_db:
            active_frames += 1
    
    active_pct = active_frames / max(n_frames, 1)
    details["active_pct"] = active_pct
    
    if active_pct < min_active:
        return SafetyStatus.SPARSE, details
    
    # === Gate 3: Clipping ===
    max_sample = np.max(np.abs(samples))
    details["max_sample"] = float(max_sample)
    
    if max_sample >= config.max_sample_value:
        return SafetyStatus.CLIPPING, details
    
    # === Gate 4: DC offset ===
    dc = np.abs(np.mean(mono))
    details["dc_offset"] = float(dc)
    
    if dc > config.max_dc_offset:
        return SafetyStatus.DC_OFFSET, details
    
    # === Gate 5: Runaway ===
    mid = len(mono) // 2
    first_rms = rms_db(mono[:mid])
    second_rms = rms_db(mono[mid:])
    growth = second_rms - first_rms
    details["level_growth_db"] = growth
    
    if growth > config.max_level_growth_db:
        return SafetyStatus.RUNAWAY, details
    
    return SafetyStatus.PASS, details


def calculate_trim_adjustment(rms_db_measured: float, peak_db_measured: float) -> float:
    """
    Calculate recommended output_trim_db adjustment.
    
    Target: RMS around -18 dBFS with peak headroom of -3 dBFS.
    Returns adjustment in dB (negative = reduce, positive = boost).
    """
    # How much would we need to adjust to hit target RMS?
    rms_adjustment = TARGET_RMS_DB - rms_db_measured
    
    # But don't let peak exceed target
    peak_after_rms_adj = peak_db_measured + rms_adjustment
    if peak_after_rms_adj > TARGET_PEAK_DB:
        # Limit by peak headroom instead
        peak_adjustment = TARGET_PEAK_DB - peak_db_measured
        return round(peak_adjustment, 1)
    
    return round(rms_adjustment, 1)


def render_generator(
    scd_path: Path,
    sclang_path: Path,
    work_dir: Path,
    generator_id: str,
    env_mode: str = "drone",
) -> Optional[Path]:
    """Render a single generator SynthDef to audio."""
    
    # Read SynthDef
    scd_content = scd_path.read_text()
    
    # Generate unique name
    nrt_name = f"forge_nrt_{generator_id}"
    
    # Transform for NRT
    try:
        transformed = transform_synthdef_for_nrt(scd_content, nrt_name)
    except Exception as e:
        print(f"  Transform error: {e}")
        return None
    
    # Output path
    output_path = work_dir / f"{generator_id}_{env_mode}.wav"
    
    # Generate script
    script = generate_nrt_script(transformed, nrt_name, output_path, env_mode=env_mode)
    script_path = work_dir / f"{generator_id}_{env_mode}_render.scd"
    script_path.write_text(script)
    
    # Run sclang
    try:
        result = subprocess.run(
            [str(sclang_path), str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=work_dir,
        )
        
        if "RENDER_COMPLETE" not in result.stdout and result.returncode != 0:
            print(f"  sclang error: {result.stderr[:200]}")
            return None
        
        if not output_path.exists() or output_path.stat().st_size < 1000:
            print(f"  Output file missing or too small")
            return None
        
        return output_path
        
    except subprocess.TimeoutExpired:
        print(f"  Render timeout (30s)")
        return None
    except Exception as e:
        print(f"  Render exception: {e}")
        return None


def validate_pack(
    pack_dir: Path,
    do_render: bool = False,
    verbose: bool = False,
    env_mode: str = "both",
) -> List[ValidationResult]:
    """
    Validate all generators in a pack.
    
    Args:
        env_mode: "drone", "clocked", or "both" (renders both and reports worst-case)
    """
    
    results = []
    config = SafetyConfig()
    
    # Load manifest
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: No manifest.json in {pack_dir}")
        return results
    
    manifest = json.loads(manifest_path.read_text())
    generators = manifest.get("generators", [])
    pack_id = manifest.get("pack_id", pack_dir.name)
    
    modes_to_test = ["drone", "clocked"] if env_mode == "both" else [env_mode]
    mode_str = " + ".join(modes_to_test)
    
    print(f"\n{pack_id}: {'Rendering' if do_render else 'Checking'} {len(generators)} generators ({mode_str})...\n")
    
    if do_render:
        sclang = find_sclang()
        if not sclang:
            print("ERROR: sclang not found - install SuperCollider")
            return results
        
        work_dir = Path(tempfile.mkdtemp(prefix="forge_validate_"))
    
    for gen_id in generators:
        scd_path = pack_dir / "generators" / f"{gen_id}.scd"
        json_path = pack_dir / "generators" / f"{gen_id}.json"
        
        if not scd_path.exists():
            results.append(ValidationResult(
                generator_id=gen_id,
                passed=False,
                status=SafetyStatus.RENDER_FAILED,
                error="SynthDef file not found",
            ))
            continue
        
        # Get current output_trim_db from JSON
        current_trim = -6.0
        if json_path.exists():
            gen_config = json.loads(json_path.read_text())
            current_trim = gen_config.get("output_trim_db", -6.0)
        
        if do_render:
            if verbose:
                print(f"  Rendering {gen_id}...", end=" ", flush=True)
            
            # Render each mode and collect results
            mode_results = []
            
            for mode in modes_to_test:
                audio_path = render_generator(scd_path, sclang, work_dir, gen_id, env_mode=mode)
                
                if audio_path is None:
                    mode_results.append((mode, SafetyStatus.RENDER_FAILED, {}))
                    continue
                
                status, details = run_safety_checks(audio_path, config)
                mode_results.append((mode, status, details))
            
            # If both modes, use worst-case for pass/fail but report both
            if len(mode_results) == 0:
                results.append(ValidationResult(
                    generator_id=gen_id,
                    passed=False,
                    status=SafetyStatus.RENDER_FAILED,
                    error="No renders succeeded",
                ))
                if verbose:
                    print("FAILED")
                continue
            
            # Find worst status (any failure = fail)
            failed_modes = [(m, s, d) for m, s, d in mode_results if s != SafetyStatus.PASS]
            
            if failed_modes:
                # Report first failure
                mode, status, details = failed_modes[0]
                peak = details.get("peak_db", -100)
                rms = details.get("rms_db", -100)
                trim_adj = calculate_trim_adjustment(rms, peak) if rms > -99 else 0
                
                results.append(ValidationResult(
                    generator_id=gen_id,
                    passed=False,
                    status=status,
                    peak_db=peak,
                    rms_db=rms,
                    trim_adjustment=trim_adj,
                    active_pct=details.get("active_pct", 0),
                    dc_offset=details.get("dc_offset", 0),
                    level_growth_db=details.get("level_growth_db", 0),
                    crest_db=details.get("crest_db", 0),
                    is_impulsive=details.get("is_impulsive", False),
                    error=f"Failed in {mode} mode",
                ))
                if verbose:
                    print(f"✗ {status.value} ({mode})")
            else:
                # All passed - use drone mode metrics for trim recommendation
                # (drone is continuous so gives more accurate loudness reading)
                drone_result = next((d for m, s, d in mode_results if m == "drone"), mode_results[0][2])
                details = drone_result
                
                peak = details.get("peak_db", -100)
                rms = details.get("rms_db", -100)
                trim_adj = calculate_trim_adjustment(rms, peak)
                
                results.append(ValidationResult(
                    generator_id=gen_id,
                    passed=True,
                    status=SafetyStatus.PASS,
                    peak_db=peak,
                    rms_db=rms,
                    trim_adjustment=trim_adj,
                    active_pct=details.get("active_pct", 0),
                    dc_offset=details.get("dc_offset", 0),
                    level_growth_db=details.get("level_growth_db", 0),
                    crest_db=details.get("crest_db", 0),
                    is_impulsive=details.get("is_impulsive", False),
                ))
                if verbose:
                    print(f"✓ PASS")
        else:
            # Static check only
            results.append(ValidationResult(
                generator_id=gen_id,
                passed=True,
                status=SafetyStatus.PASS,
            ))
    
    # Cleanup
    if do_render and work_dir.exists():
        shutil.rmtree(work_dir)
    
    return results


def print_results(results: List[ValidationResult], pack_id: str):
    """Print formatted results table."""
    
    if not any(r.peak_db > -99 for r in results):
        # No audio analysis done
        print(f"\n{pack_id}: {len(results)} generators found")
        print("Run with --render to perform audio validation")
        return
    
    print(f"\n{'Generator':<16} {'Peak':>7} {'RMS':>7} {'Crest':>6} {'Trim Adj':>9} {'Active':>7} {'Status'}")
    print("─" * 75)
    
    for r in results:
        status_icon = "✓" if r.passed else "⚠"
        # Add ~ suffix for impulsive sounds (relaxed thresholds used)
        imp_marker = "~" if r.is_impulsive else ""
        status_str = f"{status_icon} {r.status.value.upper()}{imp_marker}"
        
        if r.status == SafetyStatus.RENDER_FAILED:
            print(f"{r.generator_id:<16} {'--':>7} {'--':>7} {'--':>6} {'--':>9} {'--':>7} {status_str}")
        else:
            trim_str = f"{r.trim_adjustment:+.1f} dB" if r.trim_adjustment != 0 else "OK"
            active_str = f"{r.active_pct*100:.0f}%"
            crest_str = f"{r.crest_db:.0f}dB"
            print(f"{r.generator_id:<16} {r.peak_db:>6.1f} {r.rms_db:>6.1f} {crest_str:>6} {trim_str:>9} {active_str:>7} {status_str}")
    
    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    impulsive_count = sum(1 for r in results if r.is_impulsive)
    
    print("─" * 75)
    if failed == 0:
        summary = f"✓ All {passed} generators passed"
        if impulsive_count > 0:
            summary += f" ({impulsive_count} impulsive~)"
        print(summary)
    else:
        print(f"Summary: {passed}/{len(results)} passed, {failed} issues found")
        if impulsive_count > 0:
            print(f"  ({impulsive_count} generators detected as impulsive, relaxed thresholds applied)")
    
    # Trim recommendations
    needs_trim = [r for r in results if abs(r.trim_adjustment) >= 2.0]
    if needs_trim:
        print(f"\n⚠ Trim recommendations (adjust output_trim_db):")
        for r in needs_trim:
            print(f"  {r.generator_id}: {r.trim_adjustment:+.1f} dB")


def main():
    parser = argparse.ArgumentParser(
        description="Audio validation for CQD_Forge packs"
    )
    parser.add_argument("pack_dir", type=Path, help="Pack directory to validate")
    parser.add_argument("--render", action="store_true", help="Render and analyze audio")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--env-mode",
        choices=["drone", "clocked", "both"],
        default="both",
        help="Envelope mode: drone (sustained), clocked (rhythmic triggers), both (default)"
    )
    
    args = parser.parse_args()
    
    if not args.pack_dir.exists():
        print(f"ERROR: Pack directory not found: {args.pack_dir}")
        sys.exit(1)
    
    results = validate_pack(
        args.pack_dir,
        do_render=args.render,
        verbose=args.verbose,
        env_mode=args.env_mode,
    )
    print_results(results, args.pack_dir.name)
    
    # Exit code
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
