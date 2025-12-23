"""
imaginarium/generate.py
Candidate generation using Sobol quasi-random sampling

Per IMAGINARIUM_SPEC v10 §15:
- Adaptive batching (BATCH_SIZE=32, MAX_BATCHES=15)
- Per-family allocation based on METHOD_PRIORS
- Deterministic seeds from candidate identity
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from .validate_methods import validate_all_methods

from .config import (
    FAMILIES,
    METHOD_PRIORS,
    POOL_CONFIG,
    PHASE1_CONSTRAINTS,
)
from .models import Candidate, SoundSpec
from .seeds import GenerationContext
from .methods import get_all_methods, list_methods_by_family, get_method


@dataclass
class GenerationBatch:
    """Result of a single batch generation."""
    candidates: List[Candidate]
    batch_num: int
    sobol_indices: List[int]  # For reproducibility tracking


@dataclass
class GenerationPool:
    """Complete candidate pool from generation."""
    candidates: List[Candidate]
    context: GenerationContext
    spec: SoundSpec
    batches_generated: int
    total_candidates: int
    
    # Stats
    by_family: Dict[str, int] = field(default_factory=dict)
    by_method: Dict[str, int] = field(default_factory=dict)


def run_validation_gate() -> bool:
    """
    Run validation gate (R6).

    Returns:
        True if all methods pass, False otherwise
    """
    passed, failed, results = validate_all_methods()

    if failed > 0:
        print(f"❌ VALIDATION FAILED: {failed} methods non-compliant")
        for result in results:
            if not result.passed:
                print(f"  ✗ {result.method_id}")
        print("Generation blocked. Fix method compliance first.")
        return False

    return True

class CandidateGenerator:
    """
    Generate synthesis candidates using Sobol quasi-random sampling.
    
    The generator:
    1. Allocates candidates across families based on METHOD_PRIORS
    2. Within each family, distributes across available methods
    3. Samples parameters using Sobol sequences for uniform coverage
    4. Creates Candidate objects with deterministic seeds
    """
    
    def __init__(self, context: GenerationContext, spec: SoundSpec):
        self.context = context
        self.spec = spec
        self._sobol_engine = None
        self._sobol_index = 0
        
        # Get available methods grouped by family
        self._methods_by_family: Dict[str, List[str]] = {}
        for family in FAMILIES:
            methods = list_methods_by_family(family)
            if methods:
                self._methods_by_family[family] = methods
        
        # Calculate per-family allocation
        self._family_allocation = self._compute_family_allocation()
    
    def _compute_family_allocation(self) -> Dict[str, int]:
        """
        Compute how many candidates to generate per family.
        
        Based on METHOD_PRIORS, but only for families with registered methods.
        """
        # Filter to families with methods
        active_families = [f for f in FAMILIES if f in self._methods_by_family]
        
        if not active_families:
            return {}
        
        # Renormalize priors for active families
        total_prior = sum(METHOD_PRIORS.get(f, 0) for f in active_families)
        if total_prior == 0:
            # Equal distribution if no priors
            total_prior = len(active_families)
            normalized = {f: 1.0 / len(active_families) for f in active_families}
        else:
            normalized = {
                f: METHOD_PRIORS.get(f, 0) / total_prior 
                for f in active_families
            }
        
        # Allocate batch size
        allocation = {}
        remaining = POOL_CONFIG.batch_size
        
        for i, family in enumerate(active_families):
            if i == len(active_families) - 1:
                # Last family gets remainder
                allocation[family] = remaining
            else:
                count = int(POOL_CONFIG.batch_size * normalized[family])
                count = max(1, count)  # At least 1 per family
                allocation[family] = count
                remaining -= count
        
        return allocation
    
    def _get_sobol_samples(self, n_samples: int, n_dims: int) -> np.ndarray:
        """
        Get Sobol quasi-random samples.
        
        Returns array of shape (n_samples, n_dims) with values in [0, 1].
        """
        try:
            from scipy.stats import qmc
            
            if self._sobol_engine is None:
                # Initialize with deterministic seed from context
                self._sobol_engine = qmc.Sobol(
                    d=n_dims, 
                    scramble=True,
                    seed=self.context.sobol_seed
                )
            
            # Generate samples
            samples = self._sobol_engine.random(n_samples)
            self._sobol_index += n_samples
            return samples
            
        except ImportError:
            # Fallback to pseudo-random if scipy not available
            rng = np.random.default_rng(self.context.sobol_seed + self._sobol_index)
            self._sobol_index += n_samples
            return rng.random((n_samples, n_dims))
    
    def generate_batch(self, batch_num: int = 0) -> GenerationBatch:
        """
        Generate a single batch of candidates.
        
        Args:
            batch_num: Batch number for tracking
            
        Returns:
            GenerationBatch with candidates
        """
        candidates = []
        sobol_indices = []
        
        for family, count in self._family_allocation.items():
            methods = self._methods_by_family[family]
            
            # Distribute across methods in family
            for i in range(count):
                # Round-robin across methods
                method_id = methods[i % len(methods)]
                method = get_method(method_id)
                
                if method is None:
                    continue
                
                defn = method.definition
                n_params = len(defn.param_axes)
                
                # Get Sobol sample for this candidate's parameters
                if n_params > 0:
                    samples = self._get_sobol_samples(1, n_params)[0]
                else:
                    samples = np.array([])
                
                # Sample parameters from axes
                params = {}
                for j, axis in enumerate(defn.param_axes):
                    t = samples[j] if j < len(samples) else 0.5
                    params[axis.name] = axis.sample(t)
                
                # Generate candidate ID (identity-based, not position-based)
                param_index = batch_num * POOL_CONFIG.batch_size + len(candidates)
                candidate_id = method.generate_candidate_id(
                    macro_name="sobol",  # Using direct Sobol sampling
                    param_index=param_index,
                )
                
                # Get seed from candidate identity
                seed = self.context.candidate_seed(candidate_id)
                
                # Get tags
                tags = method.get_tags(params)
                
                # Create candidate
                candidate = Candidate(
                    candidate_id=candidate_id,
                    seed=seed,
                    method_id=method_id,
                    family=family,
                    params=params,
                    tags=tags,
                )
                
                candidates.append(candidate)
                sobol_indices.append(self._sobol_index - 1)
        
        return GenerationBatch(
            candidates=candidates,
            batch_num=batch_num,
            sobol_indices=sobol_indices,
        )
    
    def generate_pool(
        self, 
        max_batches: Optional[int] = None,
        target_usable: Optional[int] = None,
    ) -> GenerationPool:
        """
        Generate full candidate pool.
        
        Args:
            max_batches: Maximum batches to generate (default: POOL_CONFIG.max_batches)
            target_usable: Stop early if this many usable candidates (for adaptive batching)
            
        Returns:
            GenerationPool with all candidates
        """
        max_batches = max_batches or POOL_CONFIG.max_batches
        target_usable = target_usable or PHASE1_CONSTRAINTS.n_select
        
        all_candidates = []
        
        for batch_num in range(max_batches):
            batch = self.generate_batch(batch_num)
            all_candidates.extend(batch.candidates)
            
            # Adaptive batching: check if we have enough usable candidates
            # (This will be more useful after safety/scoring fills in usable status)
            usable = [c for c in all_candidates if c.usable]
            if len(usable) >= target_usable * 2:  # 2x buffer
                break
        
        # Compute stats
        by_family: Dict[str, int] = {}
        by_method: Dict[str, int] = {}
        
        for c in all_candidates:
            by_family[c.family] = by_family.get(c.family, 0) + 1
            by_method[c.method_id] = by_method.get(c.method_id, 0) + 1
        
        return GenerationPool(
            candidates=all_candidates,
            context=self.context,
            spec=self.spec,
            batches_generated=batch_num + 1,
            total_candidates=len(all_candidates),
            by_family=by_family,
            by_method=by_method,
        )


def generate_candidates(
        context: GenerationContext,
        spec: SoundSpec,
        max_batches: Optional[int] = None,
) -> GenerationPool:
    # R6: Validation gate
    if not run_validation_gate():
        raise RuntimeError("Validation gate failed - generation blocked")

    generator = CandidateGenerator(context, spec)
    return generator.generate_pool(max_batches=max_batches)
