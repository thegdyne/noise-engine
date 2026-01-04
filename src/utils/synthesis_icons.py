"""
Synthesis Icons - Auto-generation system for generator waveform icons.

Scans generator JSONs, identifies synthesis methods, generates missing icons.
"""

import json
import math
from pathlib import Path
from typing import Set

# Try PIL first, fall back gracefully
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Icon properties
ICON_WIDTH = 120
ICON_HEIGHT = 50
ICON_BG = (26, 26, 26, 255)  # #1a1a1a
ICON_MARGIN = 4

# Colors per synthesis category
SYNTHESIS_COLORS = {
    'fm': (255, 136, 68),        # #ff8844
    'physical': (68, 221, 221),  # #44dddd
    'subtractive': (68, 255, 136),  # #44ff88
    'spectral': (170, 102, 255),    # #aa66ff
    'texture': (204, 204, 204),     # #cccccc
    'unknown': (102, 102, 102),     # #666666
}


def get_project_root() -> Path:
    """Find project root by looking for src/ directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / 'src').is_dir():
            return current
        current = current.parent
    # Fallback to cwd
    return Path.cwd()


def get_icons_dir() -> Path:
    """Get the synthesis icons directory, create if needed."""
    icons_dir = get_project_root() / 'assets' / 'synthesis_icons'
    icons_dir.mkdir(parents=True, exist_ok=True)
    return icons_dir


def scan_generator_jsons() -> Set[str]:
    """
    Scan all generator JSON files and extract synthesis method categories.
    
    Returns set of categories (e.g. {'fm', 'physical', 'texture', ...})
    """
    root = get_project_root()
    categories = set()
    
    # Scan packs/*/generators/*.json
    packs_dir = root / 'packs'
    if packs_dir.exists():
        for json_file in packs_dir.glob('*/generators/*.json'):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    method = data.get('synthesis_method', '')
                    if '/' in method:
                        category = method.split('/')[0]
                        categories.add(category)
            except (json.JSONDecodeError, IOError):
                continue
    
    return categories


def get_missing_icons() -> Set[str]:
    """
    Check which synthesis categories are missing icons.
    
    Returns set of categories that need icons generated.
    """
    categories = scan_generator_jsons()
    icons_dir = get_icons_dir()
    
    missing = set()
    for cat in categories:
        icon_path = icons_dir / f'{cat}.png'
        if not icon_path.exists():
            missing.add(cat)
    
    # Also ensure unknown.png exists
    if not (icons_dir / 'unknown.png').exists():
        missing.add('unknown')
    
    return missing


def generate_icon(category: str, path: Path):
    """
    Generate a synthesis icon for the given category.
    
    Uses procedural drawing based on category type.
    """
    if not HAS_PIL:
        print(f"  ⚠ PIL not installed, cannot generate {category} icon")
        return
    
    # Create image
    img = Image.new('RGBA', (ICON_WIDTH, ICON_HEIGHT), ICON_BG)
    draw = ImageDraw.Draw(img)
    
    color = SYNTHESIS_COLORS.get(category, SYNTHESIS_COLORS['unknown'])
    
    # Drawing area
    x_start = ICON_MARGIN
    x_end = ICON_WIDTH - ICON_MARGIN
    y_mid = ICON_HEIGHT // 2
    draw_width = x_end - x_start
    draw_height = ICON_HEIGHT - ICON_MARGIN * 2
    amplitude = draw_height // 2 - 2
    
    if category == 'fm':
        # FM: Two interfering sine waves
        points = []
        for i in range(draw_width):
            t = i / draw_width
            # Carrier + modulator
            carrier = math.sin(t * 4 * math.pi)
            modulator = math.sin(t * 12 * math.pi) * 0.3
            y = y_mid - int((carrier + modulator) * amplitude * 0.7)
            points.append((x_start + i, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=1)
    
    elif category == 'physical':
        # Physical: Damped oscillation
        points = []
        for i in range(draw_width):
            t = i / draw_width
            decay = math.exp(-t * 3)
            y = y_mid - int(math.sin(t * 8 * math.pi) * amplitude * decay)
            points.append((x_start + i, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=1)
    
    elif category == 'subtractive':
        # Subtractive: Sawtooth with rounded edges
        teeth = 3
        tooth_width = draw_width // teeth
        points = []
        for t in range(teeth):
            x1 = x_start + t * tooth_width
            x2 = x_start + (t + 1) * tooth_width
            # Rising edge
            for i in range(tooth_width):
                progress = i / tooth_width
                y = y_mid + amplitude - int(progress * amplitude * 2)
                points.append((x1 + i, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=1)
    
    elif category == 'spectral':
        # Spectral: Harmonic bars
        import random
        random.seed(hash('spectral'))  # Consistent randomness
        num_bars = 12
        bar_width = max(2, draw_width // (num_bars * 2))
        for i in range(num_bars):
            x = x_start + i * (draw_width // num_bars)
            # Harmonic falloff with some variation
            height = int(amplitude * (1.0 / (i + 1) + random.random() * 0.3))
            draw.rectangle(
                [x, y_mid - height, x + bar_width, y_mid + height],
                fill=color
            )
    
    elif category == 'texture':
        # Texture: Scattered dots/particles
        import random
        random.seed(hash('texture'))
        for _ in range(80):
            x = random.randint(x_start, x_end)
            y = random.randint(ICON_MARGIN, ICON_HEIGHT - ICON_MARGIN)
            size = random.randint(1, 2)
            alpha = random.randint(100, 255)
            dot_color = color[:3] + (alpha,)
            draw.ellipse([x, y, x + size, y + size], fill=color)
    
    else:
        # Unknown: Flat line with question mark effect
        draw.line([(x_start, y_mid), (x_end, y_mid)], fill=color, width=1)
        # Dashed effect
        for i in range(0, draw_width, 8):
            if (i // 8) % 2 == 0:
                draw.line(
                    [(x_start + i, y_mid - 3), (x_start + i + 4, y_mid - 3)],
                    fill=color, width=1
                )
    
    # Save
    img.save(path, 'PNG')


def ensure_icons_exist():
    """
    Main entry point - check and generate any missing icons.
    
    Call this at app startup.
    """
    missing = get_missing_icons()
    
    if not missing:
        return
    
    if not HAS_PIL:
        print("  ⚠ PIL not installed - synthesis icons cannot be generated")
        print("    Install with: pip install Pillow")
        return
    
    icons_dir = get_icons_dir()
    print(f"  Generating {len(missing)} synthesis icon(s)...")
    
    for category in missing:
        path = icons_dir / f'{category}.png'
        generate_icon(category, path)
        print(f"    ✓ {category}.png")


def get_icon_path(category: str) -> Path:
    """
    Get the path to an icon for a synthesis category.
    
    Falls back to unknown.png if category icon doesn't exist.
    """
    icons_dir = get_icons_dir()
    icon_path = icons_dir / f'{category}.png'
    
    if icon_path.exists():
        return icon_path
    
    unknown_path = icons_dir / 'unknown.png'
    if unknown_path.exists():
        return unknown_path
    
    # Last resort - return the path anyway, widget will handle missing
    return icon_path


# CLI for testing
if __name__ == '__main__':
    print("Synthesis Icons Generator")
    print("=" * 40)
    
    categories = scan_generator_jsons()
    print(f"Found categories: {sorted(categories)}")
    
    missing = get_missing_icons()
    print(f"Missing icons: {sorted(missing)}")
    
    if missing:
        print("\nGenerating...")
        ensure_icons_exist()
        print("Done!")
    else:
        print("\nAll icons present.")
