"""
imaginarium/seeds.py
Deterministic seed generation per IMAGINARIUM_SPEC §7

CRITICAL: Do NOT use Python's built-in hash() - it's salted per-process.
All seeds must be reproducible across runs and platforms.
"""

import hashlib
from dataclasses import dataclass


def stable_u32(*parts) -> int:
    """
    Generate a stable 32-bit unsigned integer from arbitrary parts.
    
    Uses SHA-256 truncated to 4 bytes for cross-platform determinism.
    
    Example:
        stable_u32("sobol", 12345) -> consistent value across runs
    """
    s = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(s).digest()[:4], "big")


def input_fingerprint(data: bytes) -> str:
    """
    Generate SHA-256 fingerprint for input data (image, audio, etc.)
    
    Used to identify the input stimulus in generation reports.
    """
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


@dataclass
class GenerationContext:
    """
    Seed hierarchy for a single generation run.
    
    All randomness in the pipeline derives from run_seed to ensure
    reproducibility: same run_seed → identical outputs.
    
    Attributes:
        run_seed: Master seed for this generation run
    """
    run_seed: int
    
    @property
    def sobol_seed(self) -> int:
        """Seed for Sobol sequence initialization."""
        return stable_u32("sobol", self.run_seed)
    
    def candidate_seed(self, candidate_id: str) -> int:
        """
        Derive seed for a specific candidate.
        
        Seeds are derived from candidate identity (not position) to ensure
        stability when candidates are added/removed from the pool.
        
        Args:
            candidate_id: Unique identifier like "{method_id}:{macro}:{param_index}:{template_version}"
        """
        return stable_u32("cand", self.run_seed, candidate_id)
    
    def method_seed(self, method_id: str, index: int) -> int:
        """Seed for method-level randomness (e.g., parameter sampling)."""
        return stable_u32("method", self.run_seed, method_id, index)


# Convenience for generating run seeds from user input
def run_seed_from_string(s: str) -> int:
    """Convert arbitrary string to a run seed (e.g., pack name + timestamp)."""
    return stable_u32("run", s)
