"""
imaginarium/extract.py
Extract SoundSpec from input stimuli

Phase 1: Image → brightness + noisiness

Brightness: Derived from mean luminance
Noisiness: Derived from edge density (texture complexity)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Union
import numpy as np

from .models import SoundSpec
from .seeds import input_fingerprint


@dataclass
class ExtractionResult:
    """Result of spec extraction from input."""
    spec: SoundSpec
    fingerprint: str
    debug: dict  # Raw values for diagnostics


def _load_image_as_array(source: Union[str, Path, bytes]) -> np.ndarray:
    """
    Load image from path or bytes into numpy array.
    
    Returns:
        RGB array of shape (H, W, 3) with values 0-255
    """
    from PIL import Image
    import io
    
    if isinstance(source, bytes):
        img = Image.open(io.BytesIO(source))
    else:
        img = Image.open(source)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    return np.array(img)


def _rgb_to_luminance(rgb: np.ndarray) -> np.ndarray:
    """
    Convert RGB image to luminance using standard coefficients.
    
    Uses Rec. 709 coefficients: Y = 0.2126*R + 0.7152*G + 0.0722*B
    
    Returns:
        Grayscale array of shape (H, W) with values 0-255
    """
    return (
        0.2126 * rgb[:, :, 0] +
        0.7152 * rgb[:, :, 1] +
        0.0722 * rgb[:, :, 2]
    )


def _compute_edge_density(gray: np.ndarray) -> float:
    """
    Compute edge density using Sobel-like gradient magnitude.
    
    Higher values = more texture/edges = more "noisy" character.
    
    Returns:
        Normalized edge density (0-1)
    """
    # Simple Sobel approximation using numpy
    # Horizontal gradient
    gx = np.abs(np.diff(gray.astype(np.float32), axis=1))
    # Vertical gradient  
    gy = np.abs(np.diff(gray.astype(np.float32), axis=0))
    
    # Mean gradient magnitude (approximate)
    # Pad to same size and combine
    gx_padded = np.pad(gx, ((0, 0), (0, 1)), mode='edge')
    gy_padded = np.pad(gy, ((0, 1), (0, 0)), mode='edge')
    
    gradient_mag = np.sqrt(gx_padded**2 + gy_padded**2)
    
    # Normalize: max theoretical gradient is ~360 (255 * sqrt(2))
    # But typical images have much lower average
    # Empirical scaling: divide by 50 and clip
    density = np.mean(gradient_mag) / 50.0
    return float(np.clip(density, 0.0, 1.0))


def _compute_color_variance(rgb: np.ndarray) -> float:
    """
    Compute color variance as secondary noisiness signal.
    
    High color variance suggests complexity/chaos.
    
    Returns:
        Normalized variance (0-1)
    """
    # Variance across color channels per pixel, then mean
    channel_var = np.var(rgb.astype(np.float32), axis=2)
    mean_var = np.mean(channel_var)
    
    # Normalize: max variance for RGB is ~10833 ((255/2)^2 * 2/3)
    # Empirical scaling for typical images
    normalized = mean_var / 5000.0
    return float(np.clip(normalized, 0.0, 1.0))


def _compute_contrast(gray: np.ndarray) -> float:
    """
    Compute contrast as standard deviation of luminance.
    
    Returns:
        Normalized contrast (0-1)
    """
    std = np.std(gray)
    # Max std for 0-255 range is ~127.5
    return float(np.clip(std / 80.0, 0.0, 1.0))


def _compute_warmth(rgb: np.ndarray) -> float:
    """
    Compute color temperature from R/B ratio.
    
    0 = cool (blue dominant)
    0.5 = neutral
    1 = warm (red/orange dominant)
    
    Returns:
        Normalized warmth (0-1)
    """
    r_mean = np.mean(rgb[:, :, 0])
    b_mean = np.mean(rgb[:, :, 2])
    
    # Avoid division by zero
    if b_mean < 1:
        b_mean = 1
    
    # R/B ratio: <1 = cool, >1 = warm
    ratio = r_mean / b_mean
    
    # Map ratio to 0-1: ratio of 0.5 → 0, ratio of 1 → 0.5, ratio of 2 → 1
    # Using sigmoid-like mapping
    warmth = ratio / (ratio + 1)  # Maps 0→0, 1→0.5, inf→1
    
    return float(np.clip(warmth, 0.0, 1.0))


def _compute_saturation(rgb: np.ndarray) -> float:
    """
    Compute mean color saturation.
    
    Uses simplified HSV saturation: (max - min) / max per pixel
    
    Returns:
        Normalized saturation (0-1)
    """
    # Per-pixel max and min across channels
    rgb_float = rgb.astype(np.float32)
    max_rgb = np.max(rgb_float, axis=2)
    min_rgb = np.min(rgb_float, axis=2)
    
    # Saturation = (max - min) / max, avoiding div by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        sat = np.where(max_rgb > 0, (max_rgb - min_rgb) / max_rgb, 0)
    
    mean_sat = np.mean(sat)
    return float(np.clip(mean_sat, 0.0, 1.0))


def _compute_density(gray: np.ndarray, edge_density: float) -> float:
    """
    Compute visual density - how "full" or "busy" the image is.
    
    Combines edge density with non-empty space ratio.
    
    Returns:
        Normalized density (0-1)
    """
    # Fill ratio: proportion of non-dark pixels
    # Consider pixels above 20% brightness as "content"
    fill_ratio = np.mean(gray > 51) # 51 = 20% of 255
    
    # Combine edge density and fill ratio
    density = 0.6 * edge_density + 0.4 * fill_ratio
    
    return float(np.clip(density, 0.0, 1.0))


def _compute_method_affinity(
    brightness: float,
    noisiness: float,
    warmth: float,
    saturation: float,
    contrast: float,
    density: float,
) -> Dict[str, float]:
    """
    Compute affinity scores for each synthesis method based on image features.
    
    Higher affinity = method is more appropriate for this image.
    Scores are multipliers (1.0 = neutral, >1 = favored, <1 = disfavored).
    
    Returns:
        Dict mapping method_id to affinity score
    """
    affinity = {}
    
    # === SUBTRACTIVE METHODS ===
    
    # bright_saw: Favored by bright, high saturation images
    affinity["subtractive/bright_saw"] = (
        0.7 + 
        0.4 * brightness +
        0.3 * saturation -
        0.2 * (1 - warmth)  # Penalty for cool images
    )
    
    # dark_pulse: Favored by dark, low saturation, high contrast
    affinity["subtractive/dark_pulse"] = (
        0.7 +
        0.4 * (1 - brightness) +
        0.3 * contrast -
        0.2 * saturation
    )
    
    # noise_filtered: Favored by textured, noisy, low saturation
    affinity["subtractive/noise_filtered"] = (
        0.6 +
        0.5 * noisiness +
        0.2 * (1 - saturation) +
        0.1 * density
    )
    
    # supersaw: Favored by saturated, dense, warm images
    affinity["subtractive/supersaw"] = (
        0.6 +
        0.3 * saturation +
        0.3 * density +
        0.2 * warmth
    )
    
    # === FM METHODS ===
    
    # simple_fm: Neutral, slightly favors clean/bright images
    affinity["fm/simple_fm"] = (
        0.8 +
        0.2 * brightness +
        0.2 * (1 - noisiness)
    )
    
    # feedback_fm: Favored by high contrast, noisy, tense images
    affinity["fm/feedback_fm"] = (
        0.6 +
        0.4 * contrast +
        0.3 * noisiness +
        0.2 * (1 - warmth)  # Cool = tense
    )
    
    # ratio_stack: Favored by complex, medium density
    affinity["fm/ratio_stack"] = (
        0.7 +
        0.3 * density +
        0.2 * saturation
    )
    
    # ring_mod: Favored by dark, high contrast, cool images (sci-fi, metallic)
    affinity["fm/ring_mod"] = (
        0.5 +
        0.4 * (1 - brightness) +
        0.3 * contrast +
        0.3 * (1 - warmth)
    )
    
    # === PHYSICAL METHODS ===
    
    # karplus: Favored by clean, bright, low density (plucked strings)
    affinity["physical/karplus"] = (
        0.7 +
        0.3 * (1 - noisiness) +
        0.2 * (1 - density) +
        0.2 * brightness
    )
    
    # modal: Favored by warm, medium saturation (bells, metals)
    affinity["physical/modal"] = (
        0.7 +
        0.3 * warmth +
        0.2 * contrast
    )
    
    # bowed: Favored by dark, warm, low-medium density (sustained strings)
    affinity["physical/bowed"] = (
        0.5 +
        0.4 * (1 - brightness) +
        0.3 * warmth +
        0.2 * (1 - noisiness)
    )
    
    # formant: Favored by warm, medium-high saturation (vocal, organic)
    affinity["physical/formant"] = (
        0.6 +
        0.4 * warmth +
        0.3 * saturation +
        0.1 * (1 - contrast)
    )
    
    # Normalize to 0.5-1.5 range
    for method_id in affinity:
        affinity[method_id] = float(np.clip(affinity[method_id], 0.5, 1.5))
    
    return affinity


def extract_from_image(
    source: Union[str, Path, bytes],
    brightness_weight: float = 1.0,
    noisiness_weight: float = 1.0,
) -> ExtractionResult:
    """
    Extract SoundSpec from an image.
    
    Phase 2a extraction:
    - brightness: Mean luminance (light images → bright sounds)
    - noisiness: Edge density + color variance (textured images → noisy sounds)
    - warmth: Color temperature (warm colors → warm timbres)
    - saturation: Color vividness (saturated → harmonically rich)
    - contrast: Luminance range (high contrast → dynamic sounds)
    - density: Visual fullness (dense → complex sounds)
    
    Args:
        source: Image path or bytes
        brightness_weight: Weight for brightness in scoring (default 1.0)
        noisiness_weight: Weight for noisiness in scoring (default 1.0)
    
    Returns:
        ExtractionResult with SoundSpec and diagnostics
    """
    # Load image
    rgb = _load_image_as_array(source)
    gray = _rgb_to_luminance(rgb)
    
    # Compute fingerprint for reproducibility tracking
    if isinstance(source, bytes):
        fp = input_fingerprint(source)
    else:
        fp = input_fingerprint(Path(source).read_bytes())
    
    # === BRIGHTNESS ===
    # Mean luminance, normalized to 0-1
    mean_lum = np.mean(gray) / 255.0
    brightness = float(mean_lum)
    
    # === INTERMEDIATE VALUES ===
    edge_density = _compute_edge_density(gray)
    color_var = _compute_color_variance(rgb)
    contrast = _compute_contrast(gray)
    
    # === NOISINESS ===
    # Combine edge density and color variance
    noisiness = (
        0.5 * edge_density +
        0.3 * color_var +
        0.2 * contrast
    )
    noisiness = float(np.clip(noisiness, 0.0, 1.0))
    
    # === PHASE 2a FEATURES ===
    warmth = _compute_warmth(rgb)
    saturation = _compute_saturation(rgb)
    density = _compute_density(gray, edge_density)
    
    # === METHOD AFFINITY ===
    # Compute biases toward different synthesis methods
    method_affinity = _compute_method_affinity(
        brightness=brightness,
        noisiness=noisiness,
        warmth=warmth,
        saturation=saturation,
        contrast=contrast,
        density=density,
    )
    
    # Build SoundSpec
    spec = SoundSpec(
        brightness=brightness,
        noisiness=noisiness,
        warmth=warmth,
        saturation=saturation,
        contrast=contrast,
        density=density,
        weights={
            "brightness": brightness_weight,
            "noisiness": noisiness_weight,
            "warmth": 0.7,
            "saturation": 0.7,
            "contrast": 0.7,
            "density": 0.7,
        },
        method_affinity=method_affinity,
    )
    
    # Debug info
    debug = {
        "image_size": (rgb.shape[1], rgb.shape[0]),
        "mean_luminance": float(mean_lum),
        "edge_density": edge_density,
        "color_variance": color_var,
        "contrast": contrast,
        "warmth": warmth,
        "saturation": saturation,
        "density": density,
        "brightness_raw": brightness,
        "noisiness_raw": noisiness,
        "method_affinity": method_affinity,
    }
    
    return ExtractionResult(
        spec=spec,
        fingerprint=fp,
        debug=debug,
    )


def extract_from_image_region(
    source: Union[str, Path, bytes],
    region: Tuple[int, int, int, int],  # (x, y, width, height)
) -> ExtractionResult:
    """
    Extract SoundSpec from a specific region of an image.
    
    Useful for analyzing different parts of an image separately.
    """
    from PIL import Image
    import io
    
    if isinstance(source, bytes):
        img = Image.open(io.BytesIO(source))
        fp = input_fingerprint(source)
    else:
        path = Path(source)
        img = Image.open(path)
        fp = input_fingerprint(path.read_bytes())
    
    x, y, w, h = region
    cropped = img.crop((x, y, x + w, y + h))
    
    if cropped.mode != 'RGB':
        cropped = cropped.convert('RGB')
    
    rgb = np.array(cropped)
    gray = _rgb_to_luminance(rgb)
    
    # Same extraction logic as full image
    brightness = float(np.mean(gray) / 255.0)
    
    edge_density = _compute_edge_density(gray)
    color_var = _compute_color_variance(rgb)
    contrast = _compute_contrast(gray)
    
    noisiness = float(np.clip(
        0.5 * edge_density + 0.3 * color_var + 0.2 * contrast,
        0.0, 1.0
    ))
    
    spec = SoundSpec(brightness=brightness, noisiness=noisiness)
    
    debug = {
        "region": region,
        "region_size": (w, h),
        "mean_luminance": brightness,
        "edge_density": edge_density,
        "color_variance": color_var,
        "contrast": contrast,
    }
    
    return ExtractionResult(spec=spec, fingerprint=fp, debug=debug)


# =============================================================================
# Phase 2+ placeholders
# =============================================================================

def extract_from_text(text: str) -> ExtractionResult:
    """Extract SoundSpec from text description. (Phase 2)"""
    raise NotImplementedError("Text extraction is Phase 2+")


def extract_from_audio(source: Union[str, Path, bytes]) -> ExtractionResult:
    """Extract SoundSpec from audio sample. (Phase 2)"""
    raise NotImplementedError("Audio extraction is Phase 2+")
