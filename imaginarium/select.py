"""
imaginarium/select.py
Diversity selection per IMAGINARIUM_SPEC v10 §12

Farthest-first selection with constraints:
- min_family_count: Minimum families represented
- max_per_family: Maximum from any single family  
- min_pair_distance: Minimum distance between any pair
- Relaxation ladder for constraint failures
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from .config import (
    FAMILIES,
    PHASE1_CONSTRAINTS,
    RELAXATION_LADDER,
    MAX_LADDER_STEPS,
    W_FEAT,
    W_TAG,
)
from .models import Candidate, SelectionResult, SelectionDeadlock


def jaccard_distance(tags_a: Set[str], tags_b: Set[str]) -> float:
    """
    Compute Jaccard distance between two tag sets.
    
    Returns 1 - Jaccard similarity (0 = identical, 1 = disjoint).
    """
    if not tags_a and not tags_b:
        return 0.0
    
    intersection = len(tags_a & tags_b)
    union = len(tags_a | tags_b)
    
    if union == 0:
        return 0.0
    
    similarity = intersection / union
    return 1.0 - similarity


def candidate_distance(a: Candidate, b: Candidate) -> float:
    """
    Compute distance between two candidates.
    
    Combines feature distance and tag distance per §12.1.
    """
    # Feature distance (requires signatures)
    if a.features is not None and b.features is not None:
        sig_a = a.compute_signature()
        sig_b = b.compute_signature()
        feat_dist = float(np.linalg.norm(sig_a - sig_b))
    else:
        feat_dist = 0.0
    
    # Tag distance
    tag_dist = jaccard_distance(a.tag_set, b.tag_set)
    
    # Weighted combination
    return W_FEAT * feat_dist + W_TAG * tag_dist


def min_distance_to_set(candidate: Candidate, selected: List[Candidate]) -> float:
    """Find minimum distance from candidate to any in selected set."""
    if not selected:
        return float('inf')
    
    return min(candidate_distance(candidate, s) for s in selected)


@dataclass
class SelectionConstraints:
    """Active constraints for selection."""
    n_select: int = 8
    min_family_count: int = 3
    max_per_family: int = 3
    min_pair_distance: float = 0.15
    
    def apply_relaxation(self, level: int) -> "SelectionConstraints":
        """Apply relaxation ladder at given level."""
        if level <= 0 or level > len(RELAXATION_LADDER):
            return self
        
        # Start from baseline and apply all relaxations up to level
        result = SelectionConstraints(
            n_select=self.n_select,
            min_family_count=self.min_family_count,
            max_per_family=self.max_per_family,
            min_pair_distance=self.min_pair_distance,
        )
        
        for i in range(1, level + 1):
            if i < len(RELAXATION_LADDER):
                relax = RELAXATION_LADDER[i]
                for key, value in relax.items():
                    if hasattr(result, key):
                        if isinstance(value, str) and value.startswith("+"):
                            setattr(result, key, getattr(result, key) + int(value[1:]))
                        elif isinstance(value, str) and value.startswith("-"):
                            setattr(result, key, getattr(result, key) - int(value[1:]))
                        else:
                            setattr(result, key, value)
        
        return result


def check_constraints(
    selected: List[Candidate],
    candidate: Candidate,
    constraints: SelectionConstraints,
) -> Tuple[bool, Optional[str]]:
    """
    Check if adding candidate would violate constraints.
    
    Returns (ok, failure_reason).
    """
    # Check max_per_family
    family_counts = Counter(c.family for c in selected)
    if family_counts.get(candidate.family, 0) >= constraints.max_per_family:
        return False, f"max_per_family ({constraints.max_per_family}) exceeded for {candidate.family}"
    
    # Check min_pair_distance
    for s in selected:
        dist = candidate_distance(candidate, s)
        if dist < constraints.min_pair_distance:
            return False, f"min_pair_distance ({constraints.min_pair_distance}) violated"
    
    return True, None


def can_satisfy_family_constraint(
    pool: List[Candidate],
    selected: List[Candidate],
    constraints: SelectionConstraints,
) -> bool:
    """Check if it's still possible to satisfy min_family_count."""
    current_families = set(c.family for c in selected)
    remaining = [c for c in pool if c not in selected]
    available_families = set(c.family for c in remaining) | current_families
    
    return len(available_families) >= constraints.min_family_count


def farthest_first_select(
    pool: List[Candidate],
    constraints: SelectionConstraints,
) -> Tuple[List[Candidate], List[str]]:
    """
    Farthest-first selection with constraints.
    
    Args:
        pool: Usable candidates to select from
        constraints: Selection constraints
        
    Returns:
        Tuple of (selected candidates, constraint failures)
    """
    if not pool:
        return [], ["empty pool"]
    
    failures = []
    
    # Start with highest-fit candidate
    selected = [max(pool, key=lambda c: c.fit_score or 0)]
    
    while len(selected) < constraints.n_select:
        remaining = [c for c in pool if c not in selected]
        if not remaining:
            failures.append("pool exhausted")
            break
        
        # Sort by distance to selected set (farthest first)
        remaining.sort(key=lambda c: min_distance_to_set(c, selected), reverse=True)
        
        # Find first candidate that satisfies constraints
        added = False
        for candidate in remaining:
            ok, reason = check_constraints(selected, candidate, constraints)
            if ok:
                selected.append(candidate)
                added = True
                break
        
        if not added:
            # No valid candidate found
            failures.append("no valid candidate found")
            break
    
    # Check final family count
    family_counts = Counter(c.family for c in selected)
    if len(family_counts) < constraints.min_family_count:
        failures.append(f"min_family_count ({constraints.min_family_count}) not met: {len(family_counts)}")
    
    return selected, failures


def select_diverse(
    pool: List[Candidate],
    n_select: int = 8,
    use_relaxation: bool = True,
) -> SelectionResult:
    """
    Select diverse candidates using farthest-first with relaxation ladder.
    
    Args:
        pool: Candidates to select from (should be filtered to usable)
        n_select: Target number to select
        use_relaxation: Whether to use relaxation ladder on failure
        
    Returns:
        SelectionResult with selected candidates and metadata
    """
    # Filter to usable candidates
    usable = [c for c in pool if c.usable]
    
    if not usable:
        return SelectionResult(
            selected=[],
            pairwise_distances={"min": 0, "mean": 0, "max": 0},
            family_counts={},
            relaxations_applied=[],
            deadlock=SelectionDeadlock(
                pool_size=len(pool),
                family_counts={},
                constraint_failures=["no usable candidates"],
                nearest_neighbor_distances=[],
                relaxation_level=0,
                fallback_used=False,
            ),
        )
    
    # Try with baseline constraints
    base_constraints = SelectionConstraints(
        n_select=n_select,
        min_family_count=PHASE1_CONSTRAINTS.min_family_count,
        max_per_family=PHASE1_CONSTRAINTS.max_per_family,
        min_pair_distance=PHASE1_CONSTRAINTS.min_pair_distance,
    )
    
    selected, failures = farthest_first_select(usable, base_constraints)
    relaxations_applied = [0]
    
    # Apply relaxation ladder if needed
    if use_relaxation and (failures or len(selected) < n_select):
        for level in range(1, MAX_LADDER_STEPS):
            relaxed = base_constraints.apply_relaxation(level)
            selected, failures = farthest_first_select(usable, relaxed)
            relaxations_applied.append(level)
            
            if not failures and len(selected) >= relaxed.n_select:
                break
    
    # Mark selected candidates
    for c in selected:
        c.selected = True
    
    # Compute pairwise distances
    distances = []
    for i, a in enumerate(selected):
        for b in selected[i+1:]:
            distances.append(candidate_distance(a, b))
    
    if distances:
        pairwise = {
            "min": float(min(distances)),
            "mean": float(np.mean(distances)),
            "max": float(max(distances)),
        }
    else:
        pairwise = {"min": 0, "mean": 0, "max": 0}
    
    # Family counts
    family_counts = dict(Counter(c.family for c in selected))
    
    # Build result
    deadlock = None
    if failures:
        deadlock = SelectionDeadlock(
            pool_size=len(usable),
            family_counts=family_counts,
            constraint_failures=failures,
            nearest_neighbor_distances=[
                min_distance_to_set(c, [s for s in selected if s != c])
                for c in selected
            ] if selected else [],
            relaxation_level=relaxations_applied[-1] if relaxations_applied else 0,
            fallback_used=True,
        )
    
    return SelectionResult(
        selected=selected,
        pairwise_distances=pairwise,
        family_counts=family_counts,
        relaxations_applied=relaxations_applied,
        deadlock=deadlock,
    )
