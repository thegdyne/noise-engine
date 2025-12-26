"""
imaginarium/render.py
Non-Real-Time (NRT) rendering using SuperCollider's sclang

Renders candidates to audio files for safety analysis and feature extraction.

CONSOLIDATED VERSION:
Uses method templates as single source of truth.
Transforms the method's generate_synthdef() output for NRT compatibility.

Per IMAGINARIUM_SPEC v10:
- 3 second previews
- 48kHz sample rate
- Stereo output
"""

import os
import re
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
    
    CONSOLIDATED: Uses method templates as single source of truth,
    transforming them for NRT compatibility.
    """
    
    def __init__(
        self,
        sclang_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        timeout_s: int = 45,
    ):
        """
        Initialize renderer.
        
        Args:
            sclang_path: Path to sclang (auto-detected if None)
            output_dir: Directory for rendered audio (temp dir if None)
        """
        self.sclang_path = sclang_path or find_sclang()
        self.output_dir = output_dir
        self.timeout_s = timeout_s
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
    
    def _transform_for_nrt(self, method_synthdef: str, synthdef_name: str) -> str:
        """
        Transform a Noise Engine SynthDef into NRT-compatible form.
        
        This is the key consolidation function. It takes the method's
        generate_synthdef() output and transforms it for NRT rendering:
        1. Replace bus reads with fixed values
        2. Replace helper function calls with inline equivalents
        3. Simplify the argument list
        4. Adjust wrapper for NRT Score format
        
        Args:
            method_synthdef: Output from method.generate_synthdef()
            synthdef_name: Name for the NRT SynthDef
            
        Returns:
            NRT-compatible SynthDef code
        """
        code = method_synthdef
        
        # === 1. REPLACE BUS READS WITH FIXED VALUES ===
        # Frequency bus -> fixed pitch for preview
        code = re.sub(r'In\.kr\(freqBus\)', '220', code)
        
        # Filter controls
        code = re.sub(r'In\.kr\(cutoffBus\)', '2000', code)
        code = re.sub(r'In\.kr\(resBus\)', '0.5', code)
        
        # Envelope controls  
        code = re.sub(r'In\.kr\(attackBus\)', '0.1', code)
        code = re.sub(r'In\.kr\(decayBus\)', '0.5', code)
        
        # Mode controls
        code = re.sub(r'In\.kr\(filterTypeBus\)', '0', code)
        code = re.sub(r'In\.kr\(envSourceBus\)', '0', code)
        code = re.sub(r'In\.kr\(envEnabledBus\)', '1', code)
        code = re.sub(r'In\.kr\(clockRateBus\)', '6', code)

        # Portamento bus (not used in NRT, set to 0)
        code = re.sub(r'In\.kr\(portamentoBus\)', '0', code)
        
        # Amplitude - handle the ~params dictionary access
        code = re.sub(r'In\.kr\(~params\[\\amplitude\]\)', '0.5', code)
        
        # Custom param buses (not used in NRT, set to 0.5)
        for i in range(5):
            code = re.sub(rf'In\.kr\(customBus{i}\)', '0.5', code)
        
        # Trigger buses (not used in NRT OFF mode)
        code = re.sub(r'In\.kr\(clockTrigBus\)', '0', code)
        code = re.sub(r'In\.kr\(midiTrigBus\)', '0', code)
        code = re.sub(r'In\.ar\(clockTrigBus,\s*\d+\)', 'DC.ar(0) ! 13', code)
        code = re.sub(r'In\.ar\(midiTrigBus,\s*\d+\)', 'DC.ar(0) ! 8', code)
        
        # === 2. REPLACE HELPER FUNCTIONS WITH INLINE EQUIVALENTS ===
        
        # ~multiFilter.(sig, filterType, freq, rq) -> simple RLPF for NRT
        code = re.sub(
            r'~multiFilter\.\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'RLPF.ar(\1, (\2).clip(20, 18000), (\3).clip(0.1, 2))',
            code
        )
        
        # ~stereoSpread.(sig, rate, width) -> simple Pan2 for NRT
        code = re.sub(
            r'~stereoSpread\.\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^)]+\s*\)',
            r'Pan2.ar(\1, 0)',
            code
        )
        
        # ~envVCA.(...) -> simple gate-based envelope for NRT
        # This is the critical one - replaces the trigger-based VCA with a simple ADSR
        code = re.sub(
            r'~envVCA\.\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^,]+\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^,]+\s*,\s*[^)]+\s*\)',
            r'(\1 * EnvGen.kr(Env.adsr((\2).linexp(0,1,0.001,2), (\3).linexp(0,1,0.05,4), 0.7, 0.3), \\gate.kr(1), doneAction: 2) * \4)',
            code
        )
        
        # ~ensure2ch.(sig) -> check if already stereo, otherwise duplicate
        # Since we use Pan2 for stereoSpread, signal is already stereo
        # Just pass through (the ! 2 would break stereo signals)
        code = re.sub(r'~ensure2ch\.\(\s*([^)]+)\s*\)', r'\1', code)
        
        # === 3. HANDLE SELECT.AR TRIGGER PATTERN ===
        # For physical models that use Select.ar for trigger selection,
        # replace with a continuous trigger for NRT preview
        # This handles multi-line Select.ar blocks ending with ]);
        code = re.sub(
            r'trig\s*=\s*Select\.ar\(envSource[^;]+\]\);',
            'trig = Impulse.ar(3);  // NRT: continuous trigger for preview',
            code,
            flags=re.DOTALL
        )
        
        # Also remove any remaining slotIndex references (undefined in NRT)
        code = re.sub(r'slotIndex', '0', code)
        
        # === 4. SIMPLIFY ARGUMENT LIST ===
        # Replace full bus arg list with simple NRT args
        code = re.sub(
            r'\|\s*out\s*,\s*freqBus\s*,[^|]+\|',
            '|out=0, gate=1|',
            code
        )
        
        # Also handle alternate format with line breaks
        code = re.sub(
            r'\{\s*\|out,\s*freqBus,\s*cutoffBus[^|]+\|',
            '{ |out=0, gate=1|',
            code,
            flags=re.DOTALL
        )
        
        # === 5. ADJUST SYNTHDEF WRAPPER ===
        # Change: SynthDef(\name, { ... }).add;
        # To: def = SynthDef(\name, { ... });
        
        # First, extract the original name and replace with our NRT name
        code = re.sub(
            r'SynthDef\(\\[^,]+,',
            f'SynthDef(\\\\{synthdef_name},',
            code
        )
        
        # Remove .add; and wrap in def =
        code = re.sub(r'\)\.add;', ');', code)
        code = 'def = ' + code.strip()
        
        # Remove any postln lines
        lines = code.split('\n')
        lines = [l for l in lines if 'postln' not in l]
        code = '\n'.join(lines)
        
        # === 6. REMOVE RANDSEED (not needed for NRT preview) ===
        code = re.sub(r'RandSeed\.ir\([^;]+;\s*', '', code)
        
        return code
    
    def _generate_nrt_script(
        self,
        candidate: Candidate,
        output_path: Path,
        synthdef_name: str,
    ) -> str:
        """
        Generate sclang script for NRT rendering.
        
        Uses the method's generate_synthdef() as single source of truth,
        then transforms it for NRT compatibility.
        """
        duration = RENDER_CONFIG.duration_sec
        sample_rate = RENDER_CONFIG.sample_rate
        
        # Escape path for SC string
        output_path_str = str(output_path).replace("\\", "\\\\").replace('"', '\\"')
        
        # Get the method and generate REAL SynthDef (single source of truth!)
        method = get_method(candidate.method_id)
        if method is None:
            raise ValueError(f"Unknown method: {candidate.method_id}")
        
        original_synthdef = method.generate_synthdef(
            synthdef_name=f"original_{synthdef_name}",  # Placeholder name, will be replaced
            params=candidate.params,
            seed=candidate.seed,
        )
        
        # Transform for NRT
        synthdef_code = self._transform_for_nrt(original_synthdef, synthdef_name)
        
        return f'''
// Imaginarium NRT Render: {candidate.candidate_id}
// Method: {candidate.method_id}
// Using CONSOLIDATED synthesis from method template
(
var def, defBytes, score, options;

// Create SynthDef (transformed from method template)
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
                timeout=self.timeout_s,
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
                error=f"Render timeout ({self.timeout_s}s)"
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
