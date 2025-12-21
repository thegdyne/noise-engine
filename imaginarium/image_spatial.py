# imaginarium/image_spatial.py
"""
Phase A: Tile-based spatial image feature extraction for Imaginarium.

Extracts per-tile features on a fixed-size working image for role assignment:
- Brightness/contrast metrics
- Edge/texture analysis  
- Derived hints (saliency, motion, object, bed)

All features are stable 0-1 range. Pure numpy, no OpenCV dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import math
import logging

import numpy as np

log = logging.getLogger(__name__)

EPS = 1e-6

# Role assignment constants
ROLE_LETTER = {"accent": "A", "foreground": "F", "motion": "M", "bed": "B"}

# Threshold defaults
FOREGROUND_THRESH = 0.15
MOTION_THRESH = 0.10
FOREGROUND_MAX = 2
MOTION_MAX = 2

# Phase C: Coarse weighting
WEIGHT_FLOOR = 0.15

# Phase D: Quality gating
QUALITY_THRESHOLD = 0.7
STRUCTURE_L_VAR_FLOOR = 0.01
STRUCTURE_EDGE_VAR_FLOOR = 0.005
ACCENT_TRANSIENT_FLOOR = 0.15
ROLE_CONFIDENCE_FLOOR = 0.20
ROLE_WEIGHT_FLOOR = 0.20
NONBED_TILE_CAP = 6

# Coarse cell child mapping (2×2 over 4×4 grid)
# coarse(0,0) covers rows 0-1, cols 0-1 → tiles [0,1,4,5]
# coarse(0,1) covers rows 0-1, cols 2-3 → tiles [2,3,6,7]
# coarse(1,0) covers rows 2-3, cols 0-1 → tiles [8,9,12,13]
# coarse(1,1) covers rows 2-3, cols 2-3 → tiles [10,11,14,15]
COARSE_CHILD_MAP = {
    0: [0, 1, 4, 5],      # TL
    1: [2, 3, 6, 7],      # TR
    2: [8, 9, 12, 13],    # BL
    3: [10, 11, 14, 15],  # BR
}


@dataclass
class TileFeatures:
    index: int
    row: int
    col: int

    # Bounding box (normalized 0-1)
    x0: float
    y0: float
    x1: float
    y1: float

    # Brightness (stable 0-1)
    l_mean: float
    l_std: float

    # Color (stable-ish 0-1)
    sat_mean: float
    hue_entropy: float      # / log(num_bins)
    warmth: float

    # Edges (stable 0-1)
    edge_density: float     # fixed Sobel threshold ratio
    edge_orient_entropy: float
    vertical_edge_ratio: float
    horizontal_edge_ratio: float

    # Texture (stable 0-1)
    hf_energy: float        # log1p(var) mapped to 0..1

    # Derived hints (filled by compute_hints)
    saliency: float = 0.0
    motion_hint: float = 0.0
    object_hint: float = 0.0
    bed_hint: float = 0.0


@dataclass
class CoarseCell:
    """2×2 coarse cell aggregating 4 tiles from the 4×4 grid."""
    index: int                  # 0-3 (row-major: TL=0, TR=1, BL=2, BR=3)
    row: int                    # 0-1
    col: int                    # 0-1
    child_indices: List[int]    # 4 tile indices from 4×4 grid
    
    # Aggregated hint strengths (mean of children)
    motion_strength: float
    object_strength: float      # drives foreground
    bed_strength: float
    
    # For debug
    dominant_role: str          # which strength is highest


@dataclass
class LayerStats:
    """Aggregated statistics for a musical role/layer."""
    role: str
    tile_count: int
    tile_indices: List[int]
    tile_weights: List[float]
    
    # Weighted means of tile features
    l_mean: float
    l_std: float
    sat_mean: float
    edge_density: float
    hf_energy: float
    vertical_edge_ratio: float
    
    # Coverage
    area_fraction: float        # tile_count / 16


@dataclass
class SpatialSpecToken:
    """Spec token for downstream generator selection."""
    role: str                    # accent/foreground/motion/bed
    slot_count: int              # how many generators this role gets
    
    # From LayerStats (drives parameter mapping)
    l_mean: float
    l_std: float
    sat_mean: float
    edge_density: float
    hf_energy: float
    vertical_edge_ratio: float
    
    # Weight/confidence
    confidence: float            # mean tile weight for this role
    area_fraction: float


# ----------------------------
# Public API (Phase A)
# ----------------------------

def extract_tile_features(
    img_rgb: np.ndarray,
    *,
    grid: Tuple[int, int] = (4, 4),
    resize_to: int = 512,
    hue_bins: int = 24,
    orient_bins: int = 12,
    sobel_thresh: float = 0.20,
    hf_log_max: float = 5.0,
) -> List[TileFeatures]:
    """
    Extract per-tile features on a fixed-size working image.

    img_rgb:
      - np.uint8 [H,W,3] in RGB
      - or float32 [H,W,3] in 0..1 RGB
    """
    img = _to_float01_rgb(img_rgb)
    img = _resize_square_nn(img, resize_to)  # deterministic, dependency-free

    H, W, _ = img.shape
    rows, cols = grid
    tile_h = H // rows
    tile_w = W // cols

    # Precompute global luminance + gradients on full image (cheaper and consistent)
    lum = _luminance(img)  # 0..1

    gx, gy = _sobel(lum)
    mag = np.sqrt(gx * gx + gy * gy)

    # Edge mask uses fixed threshold in "mag" units (lum is 0..1)
    edge_mask = mag > float(sobel_thresh)

    # Orientation histogram uses gradient angle (0..pi)
    ang = np.arctan2(np.abs(gy), np.abs(gx) + EPS)  # 0..pi/2, stable for entropy

    # High-frequency proxy: Laplacian variance per tile, mapped to 0..1
    lap = _laplacian(lum)

    tiles: List[TileFeatures] = []

    for r in range(rows):
        for c in range(cols):
            y0 = r * tile_h
            x0 = c * tile_w
            y1 = (r + 1) * tile_h if r < rows - 1 else H
            x1 = (c + 1) * tile_w if c < cols - 1 else W

            tile_rgb = img[y0:y1, x0:x1, :]
            tile_lum = lum[y0:y1, x0:x1]
            tile_mag = mag[y0:y1, x0:x1]
            tile_edge = edge_mask[y0:y1, x0:x1]
            tile_ang = ang[y0:y1, x0:x1]
            tile_gx = gx[y0:y1, x0:x1]
            tile_gy = gy[y0:y1, x0:x1]
            tile_lap = lap[y0:y1, x0:x1]

            l_mean = float(np.mean(tile_lum))
            l_std = float(np.std(tile_lum))

            hue, sat = _rgb_to_hs(tile_rgb)  # hue 0..1, sat 0..1
            sat_mean = float(np.mean(sat))

            hue_entropy = _entropy_norm(hue, bins=hue_bins, range_=(0.0, 1.0))
            warmth = _warmth_from_hue(hue)

            edge_density = float(np.mean(tile_edge.astype(np.float32)))

            edge_orient_entropy = _entropy_norm(tile_ang, bins=orient_bins, range_=(0.0, math.pi / 2.0))

            # "Vertical edge ratio" as gx dominance (vertical edges -> intensity changes in x)
            sum_gx = float(np.sum(np.abs(tile_gx)))
            sum_gy = float(np.sum(np.abs(tile_gy)))
            total_g = sum_gx + sum_gy + EPS
            vertical_edge_ratio = sum_gx / total_g
            horizontal_edge_ratio = sum_gy / total_g

            # HF energy: log1p(var(lap)) -> clamp -> /hf_log_max
            lap_var = float(np.var(tile_lap))
            hf_log = math.log1p(lap_var)
            hf_energy = float(np.clip(hf_log / float(hf_log_max), 0.0, 1.0))

            idx = r * cols + c
            tiles.append(
                TileFeatures(
                    index=idx,
                    row=r,
                    col=c,
                    x0=x0 / W,
                    y0=y0 / H,
                    x1=x1 / W,
                    y1=y1 / H,
                    l_mean=_clamp01(l_mean),
                    l_std=_clamp01(l_std * 3.0),  # scale contrast into 0..1-ish; stable & tunable
                    sat_mean=_clamp01(sat_mean),
                    hue_entropy=_clamp01(hue_entropy),
                    warmth=_clamp01(warmth),
                    edge_density=_clamp01(edge_density),
                    edge_orient_entropy=_clamp01(edge_orient_entropy),
                    vertical_edge_ratio=_clamp01(vertical_edge_ratio),
                    horizontal_edge_ratio=_clamp01(horizontal_edge_ratio),
                    hf_energy=_clamp01(hf_energy),
                )
            )

    return tiles


def compute_hints(
    tiles: List[TileFeatures],
    *,
    eps: float = EPS,
) -> None:
    """
    Mutates tiles in place, filling:
      saliency, motion_hint, object_hint, bed_hint
    Uses z-score only for saliency (clipped [-2, +2]).
    """
    if not tiles:
        return

    edge_arr = np.array([t.edge_density for t in tiles], dtype=np.float32)
    lstd_arr = np.array([t.l_std for t in tiles], dtype=np.float32)
    hf_arr = np.array([t.hf_energy for t in tiles], dtype=np.float32)

    def z(arr: np.ndarray, val: float) -> float:
        mu = float(arr.mean())
        sd = float(arr.std())
        return float(np.clip((val - mu) / (sd + eps), -2.0, 2.0))

    for t in tiles:
        # Saliency: sum of clipped z-scores
        t.saliency = z(edge_arr, t.edge_density) + z(lstd_arr, t.l_std) + z(hf_arr, t.hf_energy)

        # Motion: vertical structure × edges
        t.motion_hint = float(t.vertical_edge_ratio * t.edge_density)

        # Object: coherent edges × contrast bias
        t.object_hint = float(t.edge_density * (1.0 - t.edge_orient_entropy) * (0.5 + 0.5 * t.l_std))

        # Bed: smooth/flat
        t.bed_hint = float((1.0 - t.edge_density) * (1.0 - t.hf_energy))


def _mean(vals: List[float]) -> float:
    """Compute mean of list, return 0.0 if empty."""
    return float(sum(vals) / len(vals)) if vals else 0.0


def assign_roles(
    tiles: List[TileFeatures],
    *,
    foreground_thresh: float = FOREGROUND_THRESH,
    motion_thresh: float = MOTION_THRESH,
    foreground_max: int = FOREGROUND_MAX,
    motion_max: int = MOTION_MAX,
) -> Dict[str, Any]:
    """
    Assign tiles to roles based on hints. Exclusive assignment order:
      1. accent     - top 1 by saliency (always exactly 1)
      2. foreground - top N by object_hint, threshold-gated (0-2)
      3. motion     - top N by motion_hint, threshold-gated (0-2)
      4. bed        - remaining (absorbs empty slots)

    Args:
        tiles: List of TileFeatures with hints already computed
        foreground_thresh: Minimum object_hint for foreground role
        motion_thresh: Minimum motion_hint for motion role
        foreground_max: Maximum foreground tiles (default 2)
        motion_max: Maximum motion tiles (default 2)

    Returns:
        Dict with 'accent', 'foreground', 'motion', 'bed' lists, 'meta', and 'config'
    """
    if not tiles:
        return {
            "accent": [],
            "foreground": [],
            "motion": [],
            "bed": [],
            "meta": {
                "accent_saliency": None,
                "accent_transient": None,
                "foreground_confidence": 0.0,
                "motion_confidence": 0.0,
            },
            "config": {
                "FOREGROUND_THRESH": foreground_thresh,
                "MOTION_THRESH": motion_thresh,
                "FOREGROUND_MAX": foreground_max,
                "MOTION_MAX": motion_max,
            },
        }

    assigned: set = set()
    roles: Dict[str, Any] = {
        "accent": [],
        "foreground": [],
        "motion": [],
        "bed": [],
    }

    # 1. Accent: always exactly 1 (top by saliency)
    by_saliency = sorted(tiles, key=lambda t: t.saliency, reverse=True)
    accent_tile = by_saliency[0]
    roles["accent"].append(accent_tile.index)
    assigned.add(accent_tile.index)

    # 2. Foreground: top N by object_hint, threshold-gated (max 2)
    by_object = sorted(
        [t for t in tiles if t.index not in assigned],
        key=lambda t: t.object_hint,
        reverse=True,
    )
    foreground_count = 0
    for t in by_object:
        if foreground_count >= foreground_max:
            break
        if t.object_hint >= foreground_thresh:
            roles["foreground"].append(t.index)
            assigned.add(t.index)
            foreground_count += 1

    # 3. Motion: top N by motion_hint, threshold-gated (max 2)
    by_motion = sorted(
        [t for t in tiles if t.index not in assigned],
        key=lambda t: t.motion_hint,
        reverse=True,
    )
    motion_count = 0
    for t in by_motion:
        if motion_count >= motion_max:
            break
        if t.motion_hint >= motion_thresh:
            roles["motion"].append(t.index)
            assigned.add(t.index)
            motion_count += 1

    # 4. Bed: all remaining tiles (absorbs empty slots)
    for t in tiles:
        if t.index not in assigned:
            roles["bed"].append(t.index)

    # Sort all role lists for determinism
    for k in ("accent", "foreground", "motion", "bed"):
        roles[k] = sorted(roles[k])

    # Compute confidence metrics
    roles["meta"] = {
        "accent_saliency": float(accent_tile.saliency),
        "accent_transient": float(max(accent_tile.l_std, accent_tile.hf_energy)),
        "foreground_confidence": _mean([tiles[i].object_hint for i in roles["foreground"]]),
        "motion_confidence": _mean([tiles[i].motion_hint for i in roles["motion"]]),
    }

    # Record config used (for debug reproducibility)
    roles["config"] = {
        "FOREGROUND_THRESH": foreground_thresh,
        "MOTION_THRESH": motion_thresh,
        "FOREGROUND_MAX": foreground_max,
        "MOTION_MAX": motion_max,
    }

    return roles


def compute_slot_allocation(roles: Dict[str, Any]) -> Dict[str, int]:
    """
    Compute 8-slot allocation based on role counts.
    
    Base allocation: accent=1, foreground=2, motion=2, bed=3
    Empty roles redistribute to bed.
    
    Returns:
        Dict mapping role name to slot count (total = 8)
    """
    foreground_count = len(roles.get("foreground", []))
    motion_count = len(roles.get("motion", []))
    
    # Base allocation
    slots = {
        "accent": 1,
        "foreground": foreground_count,
        "motion": motion_count,
        "bed": 3,
    }
    
    # Redistribute empty slots to bed
    if motion_count == 0:
        slots["bed"] += 2
    elif motion_count == 1:
        slots["bed"] += 1
    
    if foreground_count == 0:
        slots["bed"] += 2
    elif foreground_count == 1:
        slots["bed"] += 1
    
    return slots


def build_debug_output(
    tiles: List[TileFeatures],
    roles: Dict[str, Any],
    grid: Tuple[int, int] = (4, 4),
) -> Dict[str, Any]:
    """
    Build complete debug output with grids, roles, and slot allocation.

    Returns:
        Dict with version, roles, role_grid, slot_allocation, grids, config, and meta fields
    """
    grids = debug_grids(tiles, grid=grid)
    slot_allocation = compute_slot_allocation(roles)

    # Build role grid for visualization (A/F/M/B)
    rows, cols = grid
    role_grid = [["" for _ in range(cols)] for _ in range(rows)]

    for role_name in ("accent", "foreground", "motion", "bed"):
        abbrev = ROLE_LETTER[role_name]
        for idx in roles.get(role_name, []):
            t = tiles[idx]
            role_grid[t.row][t.col] = abbrev

    # Extract meta and config from roles dict
    meta = roles.get("meta", {})
    config = roles.get("config", {})

    return {
        "version": 1,
        "roles": {
            "accent": roles.get("accent", []),
            "foreground": roles.get("foreground", []),
            "motion": roles.get("motion", []),
            "bed": roles.get("bed", []),
        },
        "role_grid": role_grid,
        "slot_allocation": slot_allocation,
        "quality_score": None,  # Phase D placeholder
        "fallback": False,      # True if global-only path used
        "meta": meta,
        "config": config,
        "grids": grids,
    }


def debug_grids(tiles: List[TileFeatures], grid: Tuple[int, int] = (4, 4)) -> Dict[str, Any]:
    """
    Returns stable 4×4 grids for manual inspection/logging.
    """
    rows, cols = grid
    if len(tiles) != rows * cols:
        raise ValueError(f"Expected {rows*cols} tiles, got {len(tiles)}")

    def grid_of(fn):
        out = [[0.0 for _ in range(cols)] for _ in range(rows)]
        for t in tiles:
            out[t.row][t.col] = float(fn(t))
        return out

    return {
        "l_mean": grid_of(lambda t: t.l_mean),
        "l_std": grid_of(lambda t: t.l_std),
        "sat_mean": grid_of(lambda t: t.sat_mean),
        "edge_density": grid_of(lambda t: t.edge_density),
        "hf_energy": grid_of(lambda t: t.hf_energy),
        "saliency": grid_of(lambda t: t.saliency),
        "motion_hint": grid_of(lambda t: t.motion_hint),
        "object_hint": grid_of(lambda t: t.object_hint),
        "bed_hint": grid_of(lambda t: t.bed_hint),
    }


# ----------------------------
# Phase C: Coarse Weighting + Layer Stats
# ----------------------------

def compute_coarse_cells(tiles: List[TileFeatures]) -> List[CoarseCell]:
    """
    Compute 2×2 coarse cells from 4×4 tiles.
    
    Each coarse cell aggregates hint strengths from its 4 child tiles.
    """
    if len(tiles) != 16:
        raise ValueError(f"Expected 16 tiles, got {len(tiles)}")
    
    cells = []
    for idx in range(4):
        row = idx // 2
        col = idx % 2
        child_indices = COARSE_CHILD_MAP[idx]
        
        # Aggregate hint strengths (mean of children)
        motion_strength = _mean([tiles[i].motion_hint for i in child_indices])
        object_strength = _mean([tiles[i].object_hint for i in child_indices])
        bed_strength = _mean([tiles[i].bed_hint for i in child_indices])
        
        # Determine dominant role
        strengths = {
            "motion": motion_strength,
            "foreground": object_strength,
            "bed": bed_strength,
        }
        dominant_role = max(strengths, key=strengths.get)
        
        cells.append(CoarseCell(
            index=idx,
            row=row,
            col=col,
            child_indices=child_indices,
            motion_strength=motion_strength,
            object_strength=object_strength,
            bed_strength=bed_strength,
            dominant_role=dominant_role,
        ))
    
    return cells


def _get_tile_coarse_parent(tile_index: int) -> int:
    """Return the coarse cell index (0-3) that contains this tile."""
    for cell_idx, children in COARSE_CHILD_MAP.items():
        if tile_index in children:
            return cell_idx
    raise ValueError(f"Tile {tile_index} not in any coarse cell")


def compute_tile_weights(
    tiles: List[TileFeatures],
    roles: Dict[str, Any],
    coarse_cells: List[CoarseCell],
    weight_floor: float = WEIGHT_FLOOR,
) -> List[float]:
    """
    Compute per-tile weights based on spatial coherence.
    
    Tiles whose assigned role matches their parent coarse cell's dominant
    tendency get higher weights. Isolated role assignments are dampened.
    
    Args:
        tiles: List of 16 TileFeatures
        roles: Role assignments dict with accent/foreground/motion/bed lists
        coarse_cells: List of 4 CoarseCell objects
        weight_floor: Minimum weight (default 0.15)
    
    Returns:
        List of 16 weights (0.15-1.0), indexed by tile index
    """
    if len(tiles) != 16:
        raise ValueError(f"Expected 16 tiles, got {len(tiles)}")
    
    # Build tile_index -> role mapping
    tile_role = {}
    for role_name in ("accent", "foreground", "motion", "bed"):
        for idx in roles.get(role_name, []):
            tile_role[idx] = role_name
    
    weights = [0.0] * 16
    
    for tile in tiles:
        idx = tile.index
        role = tile_role.get(idx, "bed")
        
        # Accent never dampened
        if role == "accent":
            weights[idx] = 1.0
            continue
        
        # Find parent coarse cell
        parent_idx = _get_tile_coarse_parent(idx)
        parent = coarse_cells[parent_idx]
        
        # Get strength for this role from parent cell
        role_to_strength = {
            "motion": parent.motion_strength,
            "foreground": parent.object_strength,
            "bed": parent.bed_strength,
        }
        
        tile_strength = role_to_strength.get(role, parent.bed_strength)
        max_strength = max(
            parent.motion_strength,
            parent.object_strength,
            parent.bed_strength
        ) + EPS
        
        # Weight = how well this role matches the coarse cell's tendency
        raw_weight = tile_strength / max_strength
        weights[idx] = float(np.clip(raw_weight, weight_floor, 1.0))
    
    return weights


def _weighted_mean(values: List[float], weights: List[float]) -> float:
    """Compute weighted mean, return 0.0 if empty or all weights zero."""
    if not values or not weights:
        return 0.0
    w = np.array(weights, dtype=np.float32)
    v = np.array(values, dtype=np.float32)
    w_sum = w.sum()
    if w_sum < EPS:
        return 0.0
    return float((v * w).sum() / w_sum)


def compute_layer_stats(
    tiles: List[TileFeatures],
    roles: Dict[str, Any],
    weights: List[float],
) -> Dict[str, LayerStats]:
    """
    Compute aggregated statistics for each role/layer.
    
    Uses weighted means of tile features for tiles assigned to each role.
    
    Args:
        tiles: List of 16 TileFeatures
        roles: Role assignments dict
        weights: Per-tile weights from compute_tile_weights
    
    Returns:
        Dict mapping role name to LayerStats
    """
    layer_stats = {}
    
    for role_name in ("accent", "foreground", "motion", "bed"):
        indices = roles.get(role_name, [])
        
        if not indices:
            # Empty role
            layer_stats[role_name] = LayerStats(
                role=role_name,
                tile_count=0,
                tile_indices=[],
                tile_weights=[],
                l_mean=0.0,
                l_std=0.0,
                sat_mean=0.0,
                edge_density=0.0,
                hf_energy=0.0,
                vertical_edge_ratio=0.0,
                area_fraction=0.0,
            )
            continue
        
        # Get tiles and weights for this role
        role_tiles = [tiles[i] for i in indices]
        role_weights = [weights[i] for i in indices]
        
        layer_stats[role_name] = LayerStats(
            role=role_name,
            tile_count=len(indices),
            tile_indices=sorted(indices),
            tile_weights=role_weights,
            l_mean=_weighted_mean([t.l_mean for t in role_tiles], role_weights),
            l_std=_weighted_mean([t.l_std for t in role_tiles], role_weights),
            sat_mean=_weighted_mean([t.sat_mean for t in role_tiles], role_weights),
            edge_density=_weighted_mean([t.edge_density for t in role_tiles], role_weights),
            hf_energy=_weighted_mean([t.hf_energy for t in role_tiles], role_weights),
            vertical_edge_ratio=_weighted_mean([t.vertical_edge_ratio for t in role_tiles], role_weights),
            area_fraction=len(indices) / 16.0,
        )
    
    return layer_stats


def build_spatial_analysis(
    tiles: List[TileFeatures],
    roles: Dict[str, Any],
    grid: Tuple[int, int] = (4, 4),
) -> Dict[str, Any]:
    """
    Build complete spatial analysis including Phase C coarse weighting.
    
    Extends build_debug_output with coarse cells, tile weights, and layer stats.
    """
    # Phase B output
    base = build_debug_output(tiles, roles, grid=grid)
    
    # Phase C additions
    coarse_cells = compute_coarse_cells(tiles)
    tile_weights = compute_tile_weights(tiles, roles, coarse_cells)
    layer_stats = compute_layer_stats(tiles, roles, tile_weights)
    
    # Build tile weight grid (4×4)
    rows, cols = grid
    tile_weight_grid = [[0.0 for _ in range(cols)] for _ in range(rows)]
    for t in tiles:
        tile_weight_grid[t.row][t.col] = tile_weights[t.index]
    
    # Add coarse data
    base["coarse"] = {
        "cells": [
            {
                "index": c.index,
                "row": c.row,
                "col": c.col,
                "child_indices": c.child_indices,
                "motion_strength": c.motion_strength,
                "object_strength": c.object_strength,
                "bed_strength": c.bed_strength,
                "dominant_role": c.dominant_role,
            }
            for c in coarse_cells
        ],
        "tile_weights": tile_weights,
        "tile_weight_grid": tile_weight_grid,
    }
    
    # Add layer stats (convert dataclass to dict)
    base["layer_stats"] = {
        role: {
            "tile_count": stats.tile_count,
            "tile_indices": stats.tile_indices,
            "tile_weights": stats.tile_weights,
            "l_mean": stats.l_mean,
            "l_std": stats.l_std,
            "sat_mean": stats.sat_mean,
            "edge_density": stats.edge_density,
            "hf_energy": stats.hf_energy,
            "vertical_edge_ratio": stats.vertical_edge_ratio,
            "area_fraction": stats.area_fraction,
        }
        for role, stats in layer_stats.items()
    }
    
    return base


# ----------------------------
# Phase D: Quality Gate + Spec Tokens
# ----------------------------

def compute_quality_score(
    tiles: List[TileFeatures],
    roles: Dict[str, Any],
    layer_stats: Dict[str, LayerStats],
    tile_weights: List[float],
) -> Tuple[float, Dict[str, bool]]:
    """
    Compute quality score and individual check results.
    
    Returns:
        Tuple of (score 0-1, dict of check name -> passed bool)
    """
    checks = {}
    
    # 1. Non-trivial image structure
    # var(l_mean) > 0.01 OR var(edge_density) > 0.005
    l_mean_var = float(np.var([t.l_mean for t in tiles]))
    edge_var = float(np.var([t.edge_density for t in tiles]))
    checks["structure"] = (
        l_mean_var > STRUCTURE_L_VAR_FLOOR or 
        edge_var > STRUCTURE_EDGE_VAR_FLOOR
    )
    
    # 2. Accent meaningful
    # accent_transient > 0.15 OR saliency > 0.0
    accent_indices = roles.get("accent", [])
    if accent_indices:
        accent_idx = accent_indices[0]
        accent_transient = float(max(tiles[accent_idx].l_std, tiles[accent_idx].hf_energy))
        accent_saliency = tiles[accent_idx].saliency
        checks["accent"] = (
            accent_transient > ACCENT_TRANSIENT_FLOOR or 
            accent_saliency > 0.0
        )
    else:
        checks["accent"] = False
    
    # 3. Role confidence (if role non-empty)
    # motion_confidence > 0.20, foreground_confidence > 0.20
    motion_indices = roles.get("motion", [])
    if motion_indices:
        motion_conf = layer_stats["motion"].edge_density if isinstance(layer_stats["motion"], LayerStats) else layer_stats["motion"]["edge_density"]
        checks["motion_conf"] = motion_conf > ROLE_CONFIDENCE_FLOOR
    else:
        checks["motion_conf"] = True  # empty is fine
    
    fg_indices = roles.get("foreground", [])
    if fg_indices:
        fg_conf = layer_stats["foreground"].edge_density if isinstance(layer_stats["foreground"], LayerStats) else layer_stats["foreground"]["edge_density"]
        checks["fg_conf"] = fg_conf > ROLE_CONFIDENCE_FLOOR
    else:
        checks["fg_conf"] = True  # empty is fine
    
    # 4. Coherence not pathological
    # If motion tiles exist: mean(weight of motion tiles) > 0.20
    if motion_indices:
        motion_weights = [tile_weights[i] for i in motion_indices]
        mean_motion_weight = float(np.mean(motion_weights))
        checks["motion_weight"] = mean_motion_weight > ROLE_WEIGHT_FLOOR
    else:
        checks["motion_weight"] = True  # empty is fine
    
    # 5. No non-bed dominance
    # accent + motion + foreground tiles <= 6
    nonbed_count = (
        len(roles.get("accent", [])) +
        len(roles.get("motion", [])) +
        len(roles.get("foreground", []))
    )
    checks["nonbed_cap"] = nonbed_count <= NONBED_TILE_CAP
    
    # Score = fraction of checks passed
    passed = sum(1 for v in checks.values() if v)
    score = passed / len(checks) if checks else 0.0
    
    return score, checks


def should_fallback(quality_score: float, threshold: float = QUALITY_THRESHOLD) -> bool:
    """Determine if spatial analysis should fall back to global-only."""
    return quality_score < threshold


def build_spec_tokens(
    roles: Dict[str, Any],
    slot_allocation: Dict[str, int],
    layer_stats: Dict[str, LayerStats],
    tile_weights: List[float],
) -> List[SpatialSpecToken]:
    """
    Generate spec tokens for downstream generator selection.
    Only includes roles with slot_count > 0.
    """
    tokens = []
    
    for role in ["accent", "foreground", "motion", "bed"]:
        slot_count = slot_allocation.get(role, 0)
        if slot_count == 0:
            continue
        
        stats = layer_stats[role]
        
        # Handle both LayerStats objects and dicts
        if isinstance(stats, LayerStats):
            l_mean = stats.l_mean
            l_std = stats.l_std
            sat_mean = stats.sat_mean
            edge_density = stats.edge_density
            hf_energy = stats.hf_energy
            vertical_edge_ratio = stats.vertical_edge_ratio
            area_fraction = stats.area_fraction
        else:
            l_mean = stats["l_mean"]
            l_std = stats["l_std"]
            sat_mean = stats["sat_mean"]
            edge_density = stats["edge_density"]
            hf_energy = stats["hf_energy"]
            vertical_edge_ratio = stats["vertical_edge_ratio"]
            area_fraction = stats["area_fraction"]
        
        # Confidence = mean weight of tiles in this role
        role_indices = roles.get(role, [])
        if role_indices:
            role_weights = [tile_weights[i] for i in role_indices]
            confidence = float(np.mean(role_weights))
        else:
            confidence = 0.0
        
        tokens.append(SpatialSpecToken(
            role=role,
            slot_count=slot_count,
            l_mean=l_mean,
            l_std=l_std,
            sat_mean=sat_mean,
            edge_density=edge_density,
            hf_energy=hf_energy,
            vertical_edge_ratio=vertical_edge_ratio,
            confidence=confidence,
            area_fraction=area_fraction,
        ))
    
    return tokens


def analyze_image_spatial(
    img_rgb: np.ndarray,
    *,
    grid: Tuple[int, int] = (4, 4),
    resize_to: int = 512,
    quality_threshold: float = QUALITY_THRESHOLD,
    # Role assignment params
    foreground_thresh: float = FOREGROUND_THRESH,
    motion_thresh: float = MOTION_THRESH,
    foreground_max: int = FOREGROUND_MAX,
    motion_max: int = MOTION_MAX,
) -> Dict[str, Any]:
    """
    Full spatial analysis pipeline (Phases A-D).
    
    Returns complete analysis dict with:
        - tiles, roles, coarse cells, weights, layer_stats
        - quality_score, quality_checks, fallback flag
        - spec_tokens (empty if fallback)
    """
    # Phase A: Extract tile features
    tiles = extract_tile_features(img_rgb, grid=grid, resize_to=resize_to)
    compute_hints(tiles)
    
    # Phase B: Assign roles
    roles = assign_roles(
        tiles,
        foreground_thresh=foreground_thresh,
        motion_thresh=motion_thresh,
        foreground_max=foreground_max,
        motion_max=motion_max,
    )
    
    # Phase C: Coarse weighting + layer stats
    coarse_cells = compute_coarse_cells(tiles)
    tile_weights = compute_tile_weights(tiles, roles, coarse_cells)
    layer_stats = compute_layer_stats(tiles, roles, tile_weights)
    slot_allocation = compute_slot_allocation(roles)
    
    # Phase D: Quality gate
    quality_score, quality_checks = compute_quality_score(
        tiles, roles, layer_stats, tile_weights
    )
    fallback = should_fallback(quality_score, quality_threshold)
    
    # Build spec tokens (empty if fallback)
    if fallback:
        spec_tokens = []
    else:
        spec_tokens = build_spec_tokens(roles, slot_allocation, layer_stats, tile_weights)
    
    # Build output
    base = build_spatial_analysis(tiles, roles, grid=grid)
    
    # Add Phase D fields
    base["quality_score"] = quality_score
    base["quality"] = {
        "score": quality_score,
        "threshold": quality_threshold,
        "fallback": fallback,
        "checks": quality_checks,
    }
    base["fallback"] = fallback
    base["spec_tokens"] = [
        {
            "role": t.role,
            "slot_count": t.slot_count,
            "l_mean": t.l_mean,
            "l_std": t.l_std,
            "sat_mean": t.sat_mean,
            "edge_density": t.edge_density,
            "hf_energy": t.hf_energy,
            "vertical_edge_ratio": t.vertical_edge_ratio,
            "confidence": t.confidence,
            "area_fraction": t.area_fraction,
        }
        for t in spec_tokens
    ]
    
    # Add config constants used for reproducibility
    base["config"].update({
        "QUALITY_THRESHOLD": quality_threshold,
        "STRUCTURE_L_VAR_FLOOR": STRUCTURE_L_VAR_FLOOR,
        "STRUCTURE_EDGE_VAR_FLOOR": STRUCTURE_EDGE_VAR_FLOOR,
        "ACCENT_TRANSIENT_FLOOR": ACCENT_TRANSIENT_FLOOR,
        "ROLE_CONFIDENCE_FLOOR": ROLE_CONFIDENCE_FLOOR,
        "ROLE_WEIGHT_FLOOR": ROLE_WEIGHT_FLOOR,
        "NONBED_TILE_CAP": NONBED_TILE_CAP,
        "WEIGHT_FLOOR": WEIGHT_FLOOR,
    })
    
    return base


# ----------------------------
# Internals (dependency-free)
# ----------------------------

def _to_float01_rgb(img: np.ndarray) -> np.ndarray:
    if img.ndim != 3 or img.shape[2] != 3:
        raise ValueError(f"Expected RGB image [H,W,3], got {img.shape}")
    if img.dtype == np.uint8:
        return img.astype(np.float32) / 255.0
    img = img.astype(np.float32)
    # Assume already 0..1-ish; clamp for safety
    return np.clip(img, 0.0, 1.0)


def _resize_square_nn(img: np.ndarray, size: int) -> np.ndarray:
    """
    Deterministic nearest-neighbour resize to size×size without external deps.
    """
    h, w, c = img.shape
    if h == size and w == size:
        return img
    ys = (np.linspace(0, h - 1, size)).astype(np.int32)
    xs = (np.linspace(0, w - 1, size)).astype(np.int32)
    return img[ys][:, xs]


def _luminance(rgb: np.ndarray) -> np.ndarray:
    # sRGB luma approximation (stable & cheap)
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    return np.clip(0.2126 * r + 0.7152 * g + 0.0722 * b, 0.0, 1.0).astype(np.float32)


def _sobel(lum: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    # 3x3 Sobel kernels
    kx = np.array([[-1, 0, 1],
                   [-2, 0, 2],
                   [-1, 0, 1]], dtype=np.float32)
    ky = np.array([[-1, -2, -1],
                   [ 0,  0,  0],
                   [ 1,  2,  1]], dtype=np.float32)
    gx = _conv2(lum, kx)
    gy = _conv2(lum, ky)
    return gx, gy


def _laplacian(lum: np.ndarray) -> np.ndarray:
    k = np.array([[0,  1, 0],
                  [1, -4, 1],
                  [0,  1, 0]], dtype=np.float32)
    return _conv2(lum, k)


def _conv2(img: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    # Simple zero-padded convolution (deterministic)
    kh, kw = kernel.shape
    pad_h = kh // 2
    pad_w = kw // 2
    padded = np.pad(img, ((pad_h, pad_h), (pad_w, pad_w)), mode="edge")
    out = np.zeros_like(img, dtype=np.float32)

    # Unrolled loops kept small (512² * 9 ops) – fine for spike
    for y in range(out.shape[0]):
        y0 = y
        y1 = y0 + kh
        for x in range(out.shape[1]):
            x0 = x
            x1 = x0 + kw
            patch = padded[y0:y1, x0:x1]
            out[y, x] = float(np.sum(patch * kernel))
    return out


def _rgb_to_hs(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Vectorized RGB->Hue,Saturation (HSV). Returns:
      hue in [0,1), sat in [0,1]
    """
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    sat = np.where(cmax < EPS, 0.0, delta / (cmax + EPS)).astype(np.float32)

    hue = np.zeros_like(cmax, dtype=np.float32)
    mask = delta > EPS

    # hue in [0,6)
    rc = (cmax - r) / (delta + EPS)
    gc = (cmax - g) / (delta + EPS)
    bc = (cmax - b) / (delta + EPS)

    # Where cmax == r
    m = mask & (cmax == r)
    hue[m] = (bc[m] - gc[m]) % 6.0

    # Where cmax == g
    m = mask & (cmax == g)
    hue[m] = (2.0 + rc[m] - bc[m])

    # Where cmax == b
    m = mask & (cmax == b)
    hue[m] = (4.0 + gc[m] - rc[m])

    hue = (hue / 6.0) % 1.0
    return hue.astype(np.float32), sat


def _entropy_norm(arr: np.ndarray, *, bins: int, range_: Tuple[float, float]) -> float:
    hist, _ = np.histogram(arr.reshape(-1), bins=bins, range=range_, density=False)
    total = float(hist.sum())
    if total <= 0:
        return 0.0
    p = hist.astype(np.float32) / (total + EPS)
    p = p[p > 0]
    ent = float(-np.sum(p * np.log(p + EPS)))
    ent_max = math.log(bins)
    if ent_max <= 0:
        return 0.0
    return float(np.clip(ent / ent_max, 0.0, 1.0))


def _warmth_from_hue(hue: np.ndarray) -> float:
    """
    Simple warmness scalar 0..1 based on proximity to warm hues.
    Warm centers: 30° and 330°. Cool center: 210°.
    Returns mean warmth over the tile.
    """
    h = (hue.reshape(-1) * 360.0).astype(np.float32)

    def circ_dist(a, b):
        d = np.abs(a - b)
        return np.minimum(d, 360.0 - d)

    d_w1 = circ_dist(h, 30.0)
    d_w2 = circ_dist(h, 330.0)
    d_w = np.minimum(d_w1, d_w2)
    d_c = circ_dist(h, 210.0)

    # Convert distance to score (triangular-ish)
    warm_score = np.clip(1.0 - (d_w / 180.0), 0.0, 1.0)
    cool_score = np.clip(1.0 - (d_c / 180.0), 0.0, 1.0)

    # Warmth as warm dominance
    w = warm_score / (warm_score + cool_score + EPS)
    return float(np.mean(w))


def _clamp01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))
