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
    python tools/forge_audio_validate.py packs/nerve_glow/ --render --fail-csv

Env modes:
    drone   - Sustained gate (for pad/drone generators)
    clocked - Rhythmic triggers at ~3Hz (for percussive/rhythmic generators)
    both    - Test both modes, fail if either fails (default)

Output modes:
    --fail-csv  - Output CSV of failed generators with diagnostic info
"""

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Target RMS for balanced output (-18 dBFS is standard for synths)
TARGET_RMS_DB = -18.0
# Headroom target (peak should be below this)
TARGET_PEAK_DB = -3.0


NRT_HELPER_REWRITE_VERSION = "2025-12-25-bracket-fix-v2"


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
    failed_mode: str = ""  # "drone", "clocked", or "" if passed
    peak_db: float = -100.0
    rms_db: float = -100.0
    trim_adjustment: float = 0.0
    active_pct: float = 0.0
    dc_offset: float = 0.0
    level_growth_db: float = 0.0
    crest_db: float = 0.0
    is_impulsive: bool = False
    error: Optional[str] = None
    sc_stderr: Optional[str] = None  # SuperCollider error output
    threshold_violated: str = ""  # Which threshold was exceeded
    
    def diagnostic_summary(self) -> str:
        """One-line diagnostic summary for CSV."""
        parts = []
        if self.status == SafetyStatus.RENDER_FAILED:
            if self.sc_stderr:
                # Extract first meaningful error line
                lines = [l.strip() for l in self.sc_stderr.split('\n') if l.strip()]
                error_lines = [l for l in lines if 'ERROR' in l or 'error' in l.lower() or 'Parse' in l or 'unexpected' in l.lower()]
                if error_lines:
                    parts.append(error_lines[0][:200])
                elif self.error:
                    parts.append(self.error)
            elif self.error:
                parts.append(self.error)
        elif self.status == SafetyStatus.SILENCE:
            parts.append(f"RMS {self.rms_db:.1f}dB < threshold")
        elif self.status == SafetyStatus.SPARSE:
            parts.append(f"Active {self.active_pct*100:.0f}% < threshold")
        elif self.status == SafetyStatus.CLIPPING:
            parts.append(f"Peak {self.peak_db:.1f}dB clipping")
        elif self.status == SafetyStatus.DC_OFFSET:
            parts.append(f"DC offset {self.dc_offset:.4f}")
        elif self.status == SafetyStatus.RUNAWAY:
            parts.append(f"Level growth {self.level_growth_db:.1f}dB")
        return "; ".join(parts) if parts else ""


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
    
    # Trigger buses (not used in NRT OFF mode)
    code = re.sub(r'In\.ar\(clockTrigBus,\s*\d+\)', 'DC.ar(0) ! 13', code)
    code = re.sub(r'In\.ar\(midiTrigBus,\s*\d+\)', 'DC.ar(0) ! 8', code)
    
    # === 2. REPLACE HELPER FUNCTIONS (comma-safe) ===

    def _split_top_level_commas(s: str) -> list[str]:
        out, cur = [], []
        depth_paren = depth_brack = depth_brace = 0
        in_str = False
        esc = False

        for ch in s:
            if in_str:
                cur.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue

            if ch == '"':
                in_str = True
                cur.append(ch)
                continue

            if ch == "(":
                depth_paren += 1
            elif ch == ")":
                depth_paren -= 1
            elif ch == "[":
                depth_brack += 1
            elif ch == "]":
                depth_brack -= 1
            elif ch == "{":
                depth_brace += 1
            elif ch == "}":
                depth_brace -= 1

            if ch == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
                out.append("".join(cur).strip())
                cur = []
            else:
                cur.append(ch)

        if cur:
            out.append("".join(cur).strip())
        return out

    def _replace_tilde_call(code_in: str, fname: str, repl_fn) -> str:
        token = f"~{fname}.("
        i = 0
        out = []

        while True:
            j = code_in.find(token, i)
            if j == -1:
                out.append(code_in[i:])
                break

            out.append(code_in[i:j])

            k = j + len(token)  # points just after '('
            depth = 1
            in_str = False
            esc = False

            while k < len(code_in):
                ch = code_in[k]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            break
                k += 1

            if depth != 0:
                # Unbalanced parens; bail out (leave rest unchanged)
                out.append(code_in[j:])
                break

            arg_str = code_in[j + len(token):k]
            args = _split_top_level_commas(arg_str)

            out.append(repl_fn(args))
            i = k + 1  # continue after ')'

        return "".join(out)

    # ~multiFilter.(sig, filterType, cutoff, rq)  -> simple RLPF for NRT safety
    def _repl_multifilter(args: list[str]) -> str:
        if len(args) < 4:
            return f"/*NRT_ERR multiFilter args={args}*/"
        sig, _ft, cutoff, rq = args[0], args[1], args[2], args[3]
        return f"RLPF.ar({sig}, ({cutoff}).clip(20, 18000), ({rq}).clip(0.05, 2))"

    # ~stereoSpread.(sig, widthExpr, spread) -> safe stereo: Mix->Pan2
    def _repl_stereospread(args: list[str]) -> str:
        if len(args) < 1:
            return f"/*NRT_ERR stereoSpread args={args}*/"
        sig = args[0]
        return f"Pan2.ar(Mix({sig}), 0)"

    # ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex)
    # -> simple ASR using \gate; doneAction not needed for NRT duration, but safe to keep.
    def _repl_envvca(args: list[str]) -> str:
        if len(args) < 6:
            return f"/*NRT_ERR envVCA args={args}*/"
        sig = args[0]
        attack = args[3]
        decay = args[4]
        amp = args[5]
        return (
            f"(({sig})"
            f" * EnvGen.kr(Env.asr(({attack}).max(0.001), 1, ({decay}).max(0.001)), gate: \\gate.kr(1))"
            f" * ({amp}))"
        )

    # ~ensure2ch.(sig) -> pass-through (stereo ensured elsewhere)
    def _repl_ensure2ch(args: list[str]) -> str:
        return args[0] if args else "/*NRT_ERR ensure2ch*/"

    code = _replace_tilde_call(code, "multiFilter", _repl_multifilter)
    code = _replace_tilde_call(code, "stereoSpread", _repl_stereospread)
    code = _replace_tilde_call(code, "envVCA", _repl_envvca)
    code = _replace_tilde_call(code, "ensure2ch", _repl_ensure2ch)

    for bad in ("~stereoSpread", "~multiFilter", "~envVCA", "~ensure2ch", "..."):
        if bad in code:
            raise ValueError(f"NRT transform failed: found '{bad}' still present in transformed code")

    
    # === 3. HANDLE SELECT.AR TRIGGER PATTERN ===
    code = re.sub(
        r'trig\s*=\s*Select\.ar\(envSource[^;]+\]\);',
        'trig = Impulse.ar(3);  // NRT: continuous trigger',
        code,
        flags=re.DOTALL
    )
    
    # Replace slotIndex
    code = re.sub(r'slotIndex', '0', code)
    
    # === 4. SIMPLIFY ARGUMENT LIST ===
    code = re.sub(
        r'\|\s*out\s*,\s*freqBus\s*,[^|]+\|',
        '|out=0, gate=1|',
        code
    )
    code = re.sub(
        r'\{\s*\|out,\s*freqBus,\s*cutoffBus[^|]+\|',
        '{ |out=0, gate=1|',
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
    code = 'def = ' + code.strip()
    
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
    duration: float = 1.5,
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
        
        return f'''// Forge NRT Render: {synthdef_name} (CLOCKED mode)
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
        return f'''// Forge NRT Render: {synthdef_name} (DRONE mode)
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
) -> Tuple[SafetyStatus, Dict[str, float], str]:
    """
    Run safety gate checks on audio file.
    
    Returns: (status, details_dict, threshold_violated_description)
    """
    import numpy as np
    
    try:
        samples, sr = load_audio(audio_path)
    except Exception as e:
        return SafetyStatus.RENDER_FAILED, {"error": str(e)}, f"Load error: {e}"
    
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
        threshold = f"RMS {details['rms_db']:.1f}dB < {min_rms:.1f}dB threshold"
        return SafetyStatus.SILENCE, details, threshold
    
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
        threshold = f"Active {active_pct*100:.0f}% < {min_active*100:.0f}% threshold"
        return SafetyStatus.SPARSE, details, threshold
    
    # === Gate 3: Clipping ===
    max_sample = np.max(np.abs(samples))
    details["max_sample"] = float(max_sample)
    
    if max_sample >= config.max_sample_value:
        threshold = f"Peak {max_sample:.4f} >= {config.max_sample_value} (clipping)"
        return SafetyStatus.CLIPPING, details, threshold
    
    # === Gate 4: DC offset ===
    dc = np.abs(np.mean(mono))
    details["dc_offset"] = float(dc)
    
    if dc > config.max_dc_offset:
        threshold = f"DC offset {dc:.4f} > {config.max_dc_offset} threshold"
        return SafetyStatus.DC_OFFSET, details, threshold
    
    # === Gate 5: Runaway ===
    mid = len(mono) // 2
    first_rms = rms_db(mono[:mid])
    second_rms = rms_db(mono[mid:])
    growth = second_rms - first_rms
    details["level_growth_db"] = growth
    
    if growth > config.max_level_growth_db:
        threshold = f"Level growth {growth:.1f}dB > {config.max_level_growth_db}dB threshold"
        return SafetyStatus.RUNAWAY, details, threshold
    
    return SafetyStatus.PASS, details, ""


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


@dataclass
class RenderResult:
    """Result from rendering a generator."""
    success: bool
    audio_path: Optional[Path] = None
    stderr: str = ""
    error: str = ""


def render_generator(
    scd_path: Path,
    sclang_path: Path,
    work_dir: Path,
    generator_id: str,
    env_mode: str = "drone",
) -> RenderResult:
    """Render a single generator SynthDef to audio."""
    
    # Read SynthDef
    try:
        scd_content = scd_path.read_text()
    except Exception as e:
        return RenderResult(success=False, error=f"Cannot read file: {e}")
    
    # Generate unique name
    nrt_name = f"forge_nrt_{generator_id}"
    
    # Transform for NRT
    try:
        transformed = transform_synthdef_for_nrt(scd_content, nrt_name)
    except Exception as e:
        return RenderResult(success=False, error=f"Transform error: {e}")
    
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
            timeout=45,
            cwd=work_dir,
        )
        
        stderr = result.stderr or ""
        stdout = result.stdout or ""
        
        if "RENDER_COMPLETE" not in stdout and result.returncode != 0:
            return RenderResult(
                success=False,
                stderr=stderr,
                error=f"sclang exit code {result.returncode}"
            )
        
        if not output_path.exists():
            return RenderResult(
                success=False,
                stderr=stderr,
                error="Output file not created"
            )
        
        if output_path.stat().st_size < 1000:
            return RenderResult(
                success=False,
                stderr=stderr,
                error="Output file too small (likely empty audio)"
            )
        
        return RenderResult(success=True, audio_path=output_path, stderr=stderr)
        
    except subprocess.TimeoutExpired as te:
        # Handle both bytes and str for stderr/stdout
        stderr = getattr(te, 'stderr', None) or b''
        stdout = getattr(te, 'stdout', None) or b''
        if isinstance(stderr, bytes):
            stderr = stderr.decode('utf-8', errors='replace')
        if isinstance(stdout, bytes):
            stdout = stdout.decode('utf-8', errors='replace')
        diag = (stderr + "\n" + stdout)[-2000:]
        return RenderResult(success=False, stderr=diag, error="Render timeout (45s)")
    except Exception as e:
        return RenderResult(success=False, error=f"Render exception: {e}")


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
    work_dir = None
    
    # Load manifest
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: No manifest.json in {pack_dir}", file=sys.stderr)
        return results
    
    manifest = json.loads(manifest_path.read_text())
    generators = manifest.get("generators", [])
    pack_id = manifest.get("pack_id", pack_dir.name)
    
    modes_to_test = ["drone", "clocked"] if env_mode == "both" else [env_mode]
    mode_str = " + ".join(modes_to_test)
    
    print(f"\n{pack_id}: {'Rendering' if do_render else 'Checking'} {len(generators)} generators ({mode_str})...\n", file=sys.stderr)
    
    if do_render:
        sclang = find_sclang()
        if not sclang:
            print("ERROR: sclang not found - install SuperCollider", file=sys.stderr)
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
                print(f"  Rendering {gen_id}...", end=" ", flush=True, file=sys.stderr)
            
            # Render each mode and collect results
            mode_results = []
            
            for mode in modes_to_test:
                render_result = render_generator(scd_path, sclang, work_dir, gen_id, env_mode=mode)
                
                if not render_result.success:
                    mode_results.append((mode, SafetyStatus.RENDER_FAILED, {}, "", render_result))
                    continue
                
                status, details, threshold = run_safety_checks(render_result.audio_path, config)
                mode_results.append((mode, status, details, threshold, render_result))
            
            # If both modes, use worst-case for pass/fail but report both
            if len(mode_results) == 0:
                results.append(ValidationResult(
                    generator_id=gen_id,
                    passed=False,
                    status=SafetyStatus.RENDER_FAILED,
                    error="No renders succeeded",
                ))
                if verbose:
                    print("FAILED", file=sys.stderr)
                continue
            
            # Find worst status (any failure = fail)
            failed_modes = [(m, s, d, t, r) for m, s, d, t, r in mode_results if s != SafetyStatus.PASS]
            
            if failed_modes:
                # Report first failure
                mode, status, details, threshold, render_result = failed_modes[0]
                peak = details.get("peak_db", -100)
                rms = details.get("rms_db", -100)
                trim_adj = calculate_trim_adjustment(rms, peak) if rms > -99 else 0
                
                error_msg = render_result.error if render_result.error else f"Failed in {mode} mode"
                
                results.append(ValidationResult(
                    generator_id=gen_id,
                    passed=False,
                    status=status,
                    failed_mode=mode,
                    peak_db=peak,
                    rms_db=rms,
                    trim_adjustment=trim_adj,
                    active_pct=details.get("active_pct", 0),
                    dc_offset=details.get("dc_offset", 0),
                    level_growth_db=details.get("level_growth_db", 0),
                    crest_db=details.get("crest_db", 0),
                    is_impulsive=details.get("is_impulsive", False),
                    error=error_msg,
                    sc_stderr=render_result.stderr if render_result.stderr else None,
                    threshold_violated=threshold,
                ))
                if verbose:
                    print(f"✗ {status.value} ({mode})", file=sys.stderr)
            else:
                # All passed - use drone mode metrics for trim recommendation
                # (drone is continuous so gives more accurate loudness reading)
                drone_result = next((d for m, s, d, t, r in mode_results if m == "drone"), mode_results[0][2])
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
                    print("✓ PASS", file=sys.stderr)
        else:
            # Static check only
            results.append(ValidationResult(
                generator_id=gen_id,
                passed=True,
                status=SafetyStatus.PASS,
            ))
    
    # Cleanup
    if work_dir and work_dir.exists():
        if os.environ.get('FORGE_VALIDATE_KEEP_WORKDIR') == '1':
            print(f"KEEP_WORKDIR: {work_dir}", file=sys.stderr)
        else:
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
    print("-" * 75)
    
    for r in results:
        status_icon = "✓" if r.passed else "⚠"
        # Add ~ suffix for impulsive sounds (relaxed thresholds used)
        imp_marker = "~" if r.is_impulsive else ""
        mode_marker = f" [{r.failed_mode}]" if r.failed_mode else ""
        status_str = f"{status_icon} {r.status.value.upper()}{imp_marker}{mode_marker}"
        
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
    
    print("-" * 75)
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


def print_fail_csv(results: List[ValidationResult], pack_id: str):
    """Print CSV of failed generators with diagnostic info."""
    failed = [r for r in results if not r.passed]
    
    if not failed:
        print(f"# No failures in {pack_id}", file=sys.stderr)
        return
    
    writer = csv.writer(sys.stdout)
    
    # Header
    writer.writerow([
        "pack_id",
        "generator_id",
        "status",
        "mode",
        "peak_db",
        "rms_db",
        "active_pct",
        "threshold_violated",
        "diagnostic",
        "sc_error_excerpt"
    ])
    
    for r in failed:
        # Extract SC error excerpt (first error line, cleaned)
        sc_excerpt = ""
        if r.sc_stderr:
            lines = r.sc_stderr.split('\n')
            for line in lines:
                line = line.strip()
                if any(kw in line.lower() for kw in ['error', 'parse', 'unexpected', 'failed', 'exception']):
                    # Clean and truncate
                    sc_excerpt = line[:150].replace('"', "'")
                    break
            # If no error keyword found, take first non-empty line
            if not sc_excerpt:
                for line in lines:
                    if line.strip() and not line.startswith('compiling'):
                        sc_excerpt = line.strip()[:150].replace('"', "'")
                        break
        
        writer.writerow([
            pack_id,
            r.generator_id,
            r.status.value,
            r.failed_mode or "n/a",
            f"{r.peak_db:.1f}" if r.peak_db > -99 else "",
            f"{r.rms_db:.1f}" if r.rms_db > -99 else "",
            f"{r.active_pct*100:.0f}" if r.active_pct > 0 else "",
            r.threshold_violated,
            r.diagnostic_summary(),
            sc_excerpt,
        ])


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
    parser.add_argument(
        "--fail-csv",
        action="store_true",
        help="Output CSV of failures with diagnostic info (for debugging)"
    )
    
    args = parser.parse_args()
    
    if not args.pack_dir.exists():
        print(f"ERROR: Pack directory not found: {args.pack_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Suppress normal output when using --fail-csv
    verbose = args.verbose and not args.fail_csv
    
    results = validate_pack(
        args.pack_dir,
        do_render=args.render,
        verbose=verbose,
        env_mode=args.env_mode,
    )
    
    if args.fail_csv:
        print_fail_csv(results, args.pack_dir.name)
    else:
        print_results(results, args.pack_dir.name)
    
    # Exit code
    failed = sum(1 for r in results if not r.passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
