# imaginarium/selection.py
"""
Phase E: Role-based candidate selection for Imaginarium.

Takes candidates (already safety-filtered + globally scored) and selects 8
based on spatial role allocation from image analysis.

Strategy:
1. Partition candidates by role affinity (floor gates)
2. Rank within buckets by audio + tag affinity
3. Fill slots in priority order: accent → foreground → motion → bed
4. Backoff ladder if buckets underfill
5. Global score fills any remaining shortfall
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import logging

log = logging.getLogger(__name__)

ROLE_ORDER = ["accent", "foreground", "motion", "bed"]


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class CandidateFeatures:
    """Audio features for role classification."""
    crest: float            # 0..1 peak/RMS ratio (transient-ness)
    onset_density: float    # 0..1 attacks per second normalized
    noisiness: float        # 0..1 spectral flatness
    harmonicity: float      # 0..1 harmonic vs noise ratio
    brightness: float = 0.5 # 0..1 spectral centroid normalized


@dataclass
class SelectionCandidate:
    """Candidate wrapper for selection process."""
    candidate_id: str
    global_score: float     # 0..1 fit to global SoundSpec
    features: CandidateFeatures
    tags: Dict[str, Any] = field(default_factory=dict)
    family: str = ""        # e.g., "fm", "subtractive", "physical", "spectral"


# -----------------------------------------------------------------------------
# Family Diversity (Soft Constraint)
# -----------------------------------------------------------------------------

def family_penalty(count: int) -> float:
    """
    Penalty for selecting too many candidates from the same family.
    
    Args:
        count: How many already selected from this family (before this pick)
    
    Returns:
        Penalty to subtract from affinity score (0.0 - 0.25)
    """
    if count <= 1:
        return 0.0
    if count == 2:
        return 0.08
    if count == 3:
        return 0.16
    return 0.25  # 4+


# -----------------------------------------------------------------------------
# Floor Configuration
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class FloorConfig:
    """
    Threshold configuration for role floor gates.
    Start with fixed values for spike; later replace with quantiles.
    """
    # Accent: transient, percussive
    accent_crest: float = 0.50
    accent_onset: float = 0.40

    # Motion: rhythmic, modulated (mid onset density)
    motion_onset_min: float = 0.20
    motion_onset_max: float = 0.80

    # Foreground: melodic, harmonic, not noisy
    fg_noisiness_max: float = 0.50
    fg_harmonicity_min: float = 0.30

    # Backoff multipliers (relaxation steps)
    relax_steps: Tuple[float, ...] = (1.00, 0.85, 0.70)


def passes_floor(
    role: str,
    f: CandidateFeatures,
    cfg: FloorConfig,
    relax: float = 1.0,
) -> bool:
    """
    Check if candidate passes minimum audio requirements for role.
    
    Args:
        role: Target role name
        f: Candidate audio features
        cfg: Floor configuration
        relax: Relaxation multiplier (<1.0 makes floors easier to pass)
    
    Returns:
        True if candidate meets floor requirements
    """
    if role == "accent":
        # Accent needs transient character (high crest OR high onset)
        return (
            f.crest >= cfg.accent_crest * relax or
            f.onset_density >= cfg.accent_onset * relax
        )

    if role == "motion":
        # Motion needs mid-range onset density (not static, not spray)
        lo = cfg.motion_onset_min * relax
        hi = 1.0 - (1.0 - cfg.motion_onset_max) * relax
        return lo <= f.onset_density <= hi

    if role == "foreground":
        # Foreground needs stability: harmonic, not noisy
        return (
            f.noisiness <= min(1.0, cfg.fg_noisiness_max / relax) and
            f.harmonicity >= cfg.fg_harmonicity_min * relax
        )

    # Bed accepts anything
    return True


# -----------------------------------------------------------------------------
# Affinity Scoring
# -----------------------------------------------------------------------------

def matches_role_tags(role: str, tags: Dict[str, Any]) -> bool:
    """Check if tags suggest affinity for this role."""
    # Check for role in tags list
    tag_list = tags.get("tags", [])
    if isinstance(tag_list, list) and role in tag_list:
        return True
    
    # Check specific tag patterns
    character = tags.get("character", "")
    exciter = tags.get("exciter", "")
    topology = tags.get("topology", "")
    movement = tags.get("movement", "")
    sustain = tags.get("sustain", "")
    
    if role == "accent":
        return (
            exciter in ("noise", "impulse") or
            character in ("plucked", "aggressive", "angular") or
            sustain == "short"
        )
    
    if role == "motion":
        return (
            movement == "sweeping" or
            tags.get("modulation") == "pwm" or
            topology in ("hard_sync", "fm", "ring_mod")
        )
    
    if role == "foreground":
        return (
            exciter in ("pulse", "sustained") or
            character in ("vocal", "expressive", "harmonic") or
            topology in ("formant", "physical", "additive")
        )
    
    if role == "bed":
        return (
            exciter == "continuous" or
            character in ("gentle", "smooth", "warm") or
            topology == "noise"
        )
    
    return False


def compute_audio_affinity(role: str, f: CandidateFeatures) -> float:
    """
    Compute audio-based affinity score for role (0-1).
    
    This is a ranking score, not a gate. Higher = better fit.
    """
    if role == "accent":
        # Prefer transient/peaky
        return max(f.crest, f.onset_density)

    if role == "motion":
        # Prefer medium-high onset density (movement)
        # Triangle peak around 0.45
        x = f.onset_density
        peak = 0.45
        width = 0.45
        return max(0.0, 1.0 - abs(x - peak) / width)

    if role == "foreground":
        # Prefer harmonic + not noisy
        return 0.6 * f.harmonicity + 0.4 * (1.0 - f.noisiness)

    # Bed: slightly prefer calmer sounds
    return 1.0 - 0.5 * f.onset_density


def role_affinity(
    role: str,
    f: CandidateFeatures,
    tags: Dict[str, Any],
) -> float:
    """
    Combined affinity score for role (0-1).
    
    Audio features are primary; tags provide a small bonus.
    """
    audio = compute_audio_affinity(role, f)
    bonus = 0.2 if matches_role_tags(role, tags) else 0.0
    return min(1.0, audio + bonus)


# -----------------------------------------------------------------------------
# Selection
# -----------------------------------------------------------------------------

def select_by_role(
    candidates: List[SelectionCandidate],
    slot_allocation: Dict[str, int],
    *,
    cfg: Optional[FloorConfig] = None,
) -> Tuple[List[SelectionCandidate], Dict[str, Any]]:
    """
    Select candidates to fill 8 slots respecting role allocation.
    
    Args:
        candidates: List of candidates with global_score, features, tags
        slot_allocation: Dict mapping role -> number of slots
        cfg: Floor configuration (uses defaults if None)
    
    Returns:
        Tuple of (selected_candidates, debug_info)
        
    Selection is deterministic: same input produces same output.
    Tiebreak order: affinity, global_score, candidate_id
    """
    cfg = cfg or FloorConfig()

    # Ensure all roles exist in allocation
    for r in ROLE_ORDER:
        slot_allocation.setdefault(r, 0)

    target_total = sum(slot_allocation[r] for r in ROLE_ORDER)
    if target_total != 8:
        log.warning(
            "slot_allocation total != 8 (got %s). Proceeding anyway.",
            target_total,
        )

    # Track remaining candidates
    remaining: Dict[str, SelectionCandidate] = {
        c.candidate_id: c for c in candidates
    }
    selected: List[SelectionCandidate] = []
    
    # Track family counts globally across all roles
    family_counts: Dict[str, int] = {}
    
    debug: Dict[str, Any] = {
        "slot_allocation": dict(slot_allocation),
        "buckets": {},
        "fills": {},
        "feature_stats": _compute_feature_stats(candidates),
        "family_penalties_applied": [],
    }

    def pop_pick(cid: str) -> SelectionCandidate:
        return remaining.pop(cid)
    
    def penalized_affinity(c: SelectionCandidate, role: str) -> float:
        """Compute affinity with family penalty applied."""
        base = role_affinity(role, c.features, c.tags)
        fam = c.family or c.tags.get("family", "")
        penalty = family_penalty(family_counts.get(fam, 0))
        return max(0.0, base - penalty)

    for role in ROLE_ORDER:
        needed = int(slot_allocation.get(role, 0))
        if needed <= 0:
            debug["fills"][role] = {"needed": 0, "picked": 0, "picked_ids": []}
            continue

        picked: List[SelectionCandidate] = []
        attempts = []

        # Try each relaxation level
        for relax in cfg.relax_steps:
            # Build bucket of candidates passing floor
            bucket = [
                c for c in remaining.values()
                if passes_floor(role, c.features, cfg, relax=relax)
            ]

            attempts.append({
                "relax": relax,
                "bucket_size": len(bucket),
            })

            # Pick from bucket, re-sorting after each pick to account for family penalty
            while bucket and len(picked) < needed:
                # Sort with current family penalties
                bucket.sort(
                    key=lambda c: (
                        penalized_affinity(c, role),
                        c.global_score,
                        c.candidate_id,
                    ),
                    reverse=True,
                )
                
                c = bucket.pop(0)
                if c.candidate_id in remaining:
                    # Record penalty if applied
                    fam = c.family or c.tags.get("family", "")
                    penalty = family_penalty(family_counts.get(fam, 0))
                    if penalty > 0:
                        debug["family_penalties_applied"].append({
                            "candidate_id": c.candidate_id,
                            "family": fam,
                            "count_before": family_counts.get(fam, 0),
                            "penalty": penalty,
                            "role": role,
                        })
                    
                    # Update family count
                    family_counts[fam] = family_counts.get(fam, 0) + 1
                    picked.append(pop_pick(c.candidate_id))

            if len(picked) >= needed:
                break

        # If still short, fill with best remaining by global_score (with penalty)
        if len(picked) < needed:
            shortfall = needed - len(picked)
            fillers = sorted(
                remaining.values(),
                key=lambda c: (
                    c.global_score - family_penalty(family_counts.get(c.family or c.tags.get("family", ""), 0)),
                    c.candidate_id,
                ),
                reverse=True,
            )[:shortfall]
            
            for c in fillers:
                fam = c.family or c.tags.get("family", "")
                family_counts[fam] = family_counts.get(fam, 0) + 1
                picked.append(pop_pick(c.candidate_id))
            
            if fillers:
                log.info(
                    "Role '%s' underfilled, used %d global-score fillers",
                    role,
                    len(fillers),
                )

        selected.extend(picked)

        debug["buckets"][role] = attempts
        debug["fills"][role] = {
            "needed": needed,
            "picked": len(picked),
            "picked_ids": [c.candidate_id for c in picked],
        }

    # Final safety: trim to 8 if overshot
    if len(selected) > 8:
        selected = sorted(
            selected,
            key=lambda c: (c.global_score, c.candidate_id),
            reverse=True,
        )[:8]
        log.warning("Selection overshot, trimmed to 8")

    # Check for family dominance
    debug["family_counts"] = dict(family_counts)
    for fam, count in family_counts.items():
        if count > 4:
            log.warning(
                "Family dominance: %s has %d/8 generators (>50%%)",
                fam, count,
            )

    # Log summary
    log.info(
        "Selection complete: %s (families: %s)",
        {role: debug["fills"].get(role, {}).get("picked", 0) for role in ROLE_ORDER},
        dict(family_counts),
    )

    debug["selected_ids"] = [c.candidate_id for c in selected]
    debug["selected_count"] = len(selected)
    
    return selected, debug


def _compute_feature_stats(candidates: List[SelectionCandidate]) -> Dict[str, Any]:
    """Compute min/mean/max for each feature (for threshold tuning)."""
    if not candidates:
        return {}
    
    import statistics
    
    stats = {}
    for feat in ["crest", "onset_density", "noisiness", "harmonicity", "brightness"]:
        values = [getattr(c.features, feat) for c in candidates]
        stats[feat] = {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
        }
    
    return stats


# -----------------------------------------------------------------------------
# Convenience: Wrap existing Candidate type
# -----------------------------------------------------------------------------

def wrap_candidate(
    candidate_id: str,
    global_score: float,
    features: Dict[str, float],
    tags: Optional[Dict[str, Any]] = None,
) -> SelectionCandidate:
    """
    Create SelectionCandidate from raw data.
    
    Args:
        candidate_id: Unique identifier
        global_score: 0-1 fit score from global SoundSpec
        features: Dict with crest, onset_density, noisiness, harmonicity
        tags: Optional generator tags
    
    Returns:
        SelectionCandidate ready for selection
    """
    return SelectionCandidate(
        candidate_id=candidate_id,
        global_score=global_score,
        features=CandidateFeatures(
            crest=features.get("crest", 0.5),
            onset_density=features.get("onset_density", 0.5),
            noisiness=features.get("noisiness", 0.5),
            harmonicity=features.get("harmonicity", 0.5),
            brightness=features.get("brightness", 0.5),
        ),
        tags=tags or {},
    )
