"""
imaginarium/render.py
Non-Real-Time (NRT) rendering using SuperCollider's sclang

Renders candidates to audio files for safety analysis and feature extraction.

Per IMAGINARIUM_SPEC v10:
- 3 second previews
- 48kHz sample rate
- Stereo output
"""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from .config import RENDER_CONFIG
from .models import Candidate
from .methods import get_method

logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    """Result of rendering a single candidate."""
    candidate_id: str
    success: bool
    audio_path: Optional[Path] = None
    error: Optional[str] = None
    duration_sec: float = 0.0


@dataclass
class BatchRenderResult:
    """Result of batch rendering."""
    results: List[RenderResult]
    successful: int = 0
    failed: int = 0
    output_dir: Optional[Path] = None


def find_sclang() -> Optional[Path]:
    """
    Find sclang binary.
    
    Returns:
        Path to sclang or None if not found
    """
    candidates = []
    
    # Check PATH first
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
    
    # Windows
    candidates.extend([
        Path("C:/Program Files/SuperCollider/sclang.exe"),
        Path("C:/Program Files (x86)/SuperCollider/sclang.exe"),
    ])
    
    for path in candidates:
        if path.exists():
            return path
    
    return None


class NRTRenderer:
    """
    Non-Real-Time renderer using SuperCollider's sclang.
    
    Uses Score.recordNRT for clean NRT rendering without needing
    a running server.
    """
    
    def __init__(
        self,
        sclang_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize renderer.
        
        Args:
            sclang_path: Path to sclang (auto-detected if None)
            output_dir: Directory for rendered audio (temp dir if None)
        """
        self.sclang_path = sclang_path or find_sclang()
        self.output_dir = output_dir
        self._temp_dir: Optional[Path] = None
    
    @property
    def available(self) -> bool:
        """Check if rendering is available."""
        return self.sclang_path is not None
    
    def _get_work_dir(self) -> Path:
        """Get or create working directory for temp files."""
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            return self.output_dir
        
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="imaginarium_"))
        return self._temp_dir
    
    def _generate_nrt_script(
        self,
        candidate: Candidate,
        output_path: Path,
        synthdef_name: str,
    ) -> str:
        """
        Generate sclang script for NRT rendering.
        
        Uses the method template to generate the SynthDef, then wraps it
        in NRT Score recording code.
        """
        duration = RENDER_CONFIG.duration_sec
        sample_rate = RENDER_CONFIG.sample_rate
        
        # Escape path for SC string
        output_path_str = str(output_path).replace("\\", "\\\\").replace('"', '\\"')
        
        # Generate family-specific SynthDef
        synthdef_code = self._generate_synthdef_for_family(candidate, synthdef_name)
        
        return f'''
// Imaginarium NRT Render: {candidate.candidate_id}
(
var def, defBytes, score, options;

// Create SynthDef
{synthdef_code}

// Get synthdef as bytes for d_recv
defBytes = def.asBytes;

// Build score with synthdef load + synth
score = Score([
    [0.0, [\\d_recv, defBytes]],
    [0.001, [\\s_new, \\{synthdef_name}, 1000, 0, 0]],
    [{duration - 0.3:.3f}, [\\n_set, 1000, \\gate, 0]],
    [{duration + 0.3:.3f}, [\\c_set, 0, 0]]
]);

// NRT options
options = ServerOptions.new;
options.numOutputBusChannels = 2;
options.sampleRate = {sample_rate};

// Render
score.recordNRT(
    nil,
    "{output_path_str}",
    sampleRate: {sample_rate},
    headerFormat: "WAV",
    sampleFormat: "int16",
    options: options,
    duration: {duration + 0.5:.2f},
    action: {{ "RENDER_COMPLETE".postln; 0.exit }}
);
)
'''
    
    def _generate_synthdef_for_family(
        self,
        candidate: Candidate,
        synthdef_name: str,
    ) -> str:
        """Generate SynthDef code based on candidate's family."""
        params = candidate.params
        family = candidate.family
        
        if family == "subtractive":
            return self._synthdef_subtractive(params, synthdef_name, candidate.method_id)
        elif family == "fm":
            return self._synthdef_fm(params, synthdef_name)
        elif family == "physical":
            return self._synthdef_physical(params, synthdef_name)
        else:
            # Fallback: simple sine
            return f'''def = SynthDef(\\{synthdef_name}, {{
    |out=0, gate=1|
    var sig, env;
    sig = SinOsc.ar(220) * 0.3;
    env = EnvGen.kr(Env.adsr(0.01, 0.1, 0.5, 0.3), gate, doneAction: 2);
    sig = sig * env;
    sig = sig ! 2;
    Out.ar(out, sig);
}});'''
    
    def _synthdef_subtractive(self, params: Dict, name: str, method_id: str) -> str:
        """Generate subtractive synthesis SynthDef."""
        if "dark_pulse" in method_id:
            # Dark pulse parameters
            pw = float(params.get("pulse_width", 0.5))
            pwm_depth = float(params.get("pwm_depth", 0.1))
            pwm_rate = float(params.get("pwm_rate", 0.5))
            cutoff = float(params.get("cutoff_hz", 800))
            res = float(params.get("resonance", 0.2))
            rq = max(0.1, 1.0 - res * 0.8)
            
            return f'''def = SynthDef(\\{name}, {{
    |out=0, gate=1|
    var sig, width, env;
    var freq = 110;
    
    // PWM
    width = {pw} + (SinOsc.kr({pwm_rate}) * {pwm_depth});
    width = width.clip(0.1, 0.9);
    
    // Pulse oscillator
    sig = Pulse.ar(freq, width);
    
    // Low-pass filter
    sig = RLPF.ar(sig, {cutoff}, {rq});
    
    // Envelope
    env = EnvGen.kr(Env.adsr(0.01, 0.2, 0.6, 0.5), gate, doneAction: 2);
    sig = sig * env * 0.4;
    
    sig = sig ! 2;
    Out.ar(out, sig);
}});'''
        else:
            # Bright saw parameters (default)
            cutoff_ratio = float(params.get('cutoff_ratio', 0.5))
            resonance = float(params.get('resonance', 0.3))
            drive = float(params.get('drive', 0.3))
            detune = float(params.get('detune', 0.01))
            
            base_freq = 220.0
            actual_cutoff = 2000.0 * cutoff_ratio
            rq = max(0.1, 1.0 - (resonance * 0.7))
            
            return f'''def = SynthDef(\\{name}, {{
    |out=0, gate=1|
    var sig, env;
    var freq = {base_freq};
    
    // Triple saw with detune
    sig = Mix.ar([
        Saw.ar(freq),
        Saw.ar(freq * {1.0 + detune:.6f}),
        Saw.ar(freq * {1.0 - detune:.6f})
    ]) / 3;
    
    // Saturation
    sig = (sig * {1.0 + drive * 3:.4f}).tanh;
    
    // Filter  
    sig = RLPF.ar(sig, {actual_cutoff:.1f}, {rq:.4f});
    
    // Envelope
    env = EnvGen.kr(Env.adsr(0.01, 0.1, 0.8, 0.5), gate, doneAction: 2);
    sig = sig * env * 0.5;
    
    sig = sig ! 2;
    Out.ar(out, sig);
}});'''
    
    def _synthdef_fm(self, params: Dict, name: str) -> str:
        """Generate FM synthesis SynthDef."""
        ratio = float(params.get("ratio", 2.0))
        index = float(params.get("index", 3.0))
        index_decay = float(params.get("index_decay", 1.0))
        mod_env = float(params.get("mod_env_amt", 0.5))
        bright = float(params.get("brightness", 0.5))
        
        return f'''def = SynthDef(\\{name}, {{
    |out=0, gate=1|
    var mod, car, modEnv, carEnv, sig, idx;
    var freq = 220;
    
    // Modulator envelope
    modEnv = EnvGen.kr(Env.perc(0.01, {index_decay}));
    modEnv = (modEnv * {mod_env}) + (1 - {mod_env});
    
    // Dynamic index
    idx = {index} * modEnv;
    
    // Modulator
    mod = SinOsc.ar(freq * {ratio}) * idx * freq;
    
    // Carrier
    car = SinOsc.ar(freq + mod);
    
    // Carrier envelope
    carEnv = EnvGen.kr(Env.adsr(0.01, 0.3, 0.5, 0.5), gate, doneAction: 2);
    
    // Brightness filter
    sig = LPF.ar(car, {1000 + bright * 6000});
    sig = sig * carEnv * 0.4;
    
    sig = sig ! 2;
    Out.ar(out, sig);
}});'''
    
    def _synthdef_physical(self, params: Dict, name: str) -> str:
        """Generate physical modeling SynthDef."""
        decay = float(params.get("decay_time", 2.0))
        damp = float(params.get("damping", 0.3))
        bright = float(params.get("brightness", 0.5))
        exciter = float(params.get("exciter_color", 0.5))
        body = float(params.get("body_size", 0.3))
        
        coef = 0.1 + damp * 0.4
        
        return f'''def = SynthDef(\\{name}, {{
    |out=0, gate=1|
    var exc, sig, env, bodyRes;
    var freq = 220;
    
    // Exciter
    exc = PinkNoise.ar * {0.3 + exciter * 0.7};
    exc = exc + (Impulse.ar(0) * {1.0 - exciter * 0.5});
    exc = LPF.ar(exc, {2000 + bright * 8000});
    exc = exc * EnvGen.kr(Env.perc(0.001, 0.01));
    
    // Karplus-Strong
    sig = Pluck.ar(exc, Impulse.kr(0), 0.2, freq.reciprocal, {decay}, {coef});
    
    // Body resonance
    bodyRes = BPF.ar(sig, freq * 1.5, 0.5) * {body * 0.3};
    bodyRes = bodyRes + (BPF.ar(sig, freq * 2.5, 0.3) * {body * 0.2});
    sig = sig + bodyRes;
    
    // Gate envelope
    env = EnvGen.kr(Env.asr(0.001, 1, 0.1), gate, doneAction: 2);
    sig = sig * env * 0.5;
    
    sig = sig ! 2;
    Out.ar(out, sig);
}});'''
    
    def render_candidate(
        self,
        candidate: Candidate,
        output_path: Optional[Path] = None,
    ) -> RenderResult:
        """
        Render a single candidate to audio.
        
        Args:
            candidate: Candidate to render
            output_path: Output WAV path (auto-generated if None)
            
        Returns:
            RenderResult with success status and audio path
        """
        if not self.available:
            return RenderResult(
                candidate_id=candidate.candidate_id,
                success=False,
                error="sclang not found - install SuperCollider",
            )
        
        work_dir = self._get_work_dir()
        
        # Generate unique synthdef name (alphanumeric only)
        synthdef_name = f"imag_{abs(candidate.seed) % 1000000}"
        
        # Output path
        if output_path is None:
            safe_id = candidate.candidate_id.replace('/', '_').replace(':', '_')
            output_path = work_dir / f"{safe_id}.wav"
        
        try:
            # Generate SC script
            script = self._generate_nrt_script(candidate, output_path, synthdef_name)
            
            # Write to temp file
            script_path = work_dir / f"{synthdef_name}_render.scd"
            script_path.write_text(script)
            
            # Run sclang
            result = subprocess.run(
                [str(self.sclang_path), str(script_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=work_dir,
            )
            
            # Check for success
            if "RENDER_COMPLETE" not in result.stdout and result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                return RenderResult(
                    candidate_id=candidate.candidate_id,
                    success=False,
                    error=f"sclang error: {error_msg}",
                )
            
            # Verify output exists
            if not output_path.exists():
                return RenderResult(
                    candidate_id=candidate.candidate_id,
                    success=False,
                    error="Output file not created",
                )
            
            # Check file has content
            if output_path.stat().st_size < 1000:
                return RenderResult(
                    candidate_id=candidate.candidate_id,
                    success=False,
                    error=f"Output file too small ({output_path.stat().st_size} bytes)",
                )
            
            return RenderResult(
                candidate_id=candidate.candidate_id,
                success=True,
                audio_path=output_path,
                duration_sec=RENDER_CONFIG.duration_sec,
            )
            
        except subprocess.TimeoutExpired:
            return RenderResult(
                candidate_id=candidate.candidate_id,
                success=False,
                error="Render timed out (30s)",
            )
        except Exception as e:
            return RenderResult(
                candidate_id=candidate.candidate_id,
                success=False,
                error=str(e),
            )
    
    def render_batch(
        self,
        candidates: List[Candidate],
        progress_callback=None,
    ) -> BatchRenderResult:
        """
        Render multiple candidates.
        
        Args:
            candidates: List of candidates to render
            progress_callback: Optional callback(current, total, candidate_id)
            
        Returns:
            BatchRenderResult with all results
        """
        results = []
        successful = 0
        failed = 0
        
        for i, candidate in enumerate(candidates):
            if progress_callback:
                progress_callback(i, len(candidates), candidate.candidate_id)
            
            result = self.render_candidate(candidate)
            results.append(result)
            
            if result.success:
                successful += 1
                candidate.audio_path = result.audio_path
            else:
                failed += 1
                logger.warning(f"Render failed for {candidate.candidate_id}: {result.error}")
        
        return BatchRenderResult(
            results=results,
            successful=successful,
            failed=failed,
            output_dir=self._get_work_dir(),
        )
    
    def cleanup(self):
        """Clean up temporary files."""
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)
            self._temp_dir = None


def render_candidates(
    candidates: List[Candidate],
    output_dir: Optional[Path] = None,
    sclang_path: Optional[Path] = None,
) -> BatchRenderResult:
    """
    Convenience function for batch rendering.
    
    Args:
        candidates: Candidates to render
        output_dir: Output directory (temp if None)
        sclang_path: Path to sclang (auto-detected if None)
        
    Returns:
        BatchRenderResult
    """
    renderer = NRTRenderer(
        sclang_path=sclang_path,
        output_dir=output_dir,
    )
    
    try:
        return renderer.render_batch(candidates)
    finally:
        if output_dir is None:
            renderer.cleanup()

