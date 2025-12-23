#!/usr/bin/env python3
"""
imaginarium/tools/gen_test_image.py
Generate test images covering formal art elements and design principles

Elements of Art: Line, Shape, Form, Space, Value, Colour, Texture, Mark-making
Principles of Design: Composition, Contrast, Balance, Emphasis, Hierarchy,
                      Movement, Rhythm, Unity, Variety, Proportion

Usage:
    python3 -m imaginarium.tools.gen_test_image --preset chiaroscuro
    python3 -m imaginarium.tools.gen_test_image --style line_gesture -b 0.5 -n 0.6
    python3 -m imaginarium.tools.gen_test_image --list-styles
    python3 -m imaginarium.tools.gen_test_image --sweep
"""

import argparse
import math
from pathlib import Path
from typing import Tuple, List
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


# =============================================================================
# Color Utilities
# =============================================================================

def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """Convert HSV (0-1 range) to RGB (0-255 range)."""
    if s == 0:
        r = g = b = int(v * 255)
        return (r, g, b)
    
    i = int(h * 6)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    
    i %= 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else: r, g, b = v, p, q
    
    return (int(r * 255), int(g * 255), int(b * 255))


def generate_palette(brightness: float, rng: np.random.Generator, num_colors: int = 5) -> List[Tuple[int, int, int]]:
    """Generate a vivid, varied color palette."""
    base_hue = rng.random()
    
    colors = []
    for i in range(num_colors):
        # Spread hues widely
        h = (base_hue + (i * 0.22) + rng.random() * 0.1) % 1.0
        
        # HIGH saturation for vivid colors (0.6-1.0)
        s = 0.6 + rng.random() * 0.4
        
        # HIGH value for bright colors, adjusted slightly by brightness param
        # Don't let brightness make colors muddy - keep V high
        v = 0.7 + rng.random() * 0.25 + brightness * 0.05
        v = min(1.0, v)
        
        colors.append(hsv_to_rgb(h, s, v))
    
    return colors


def generate_dark_palette(brightness: float, rng: np.random.Generator, num_colors: int = 5) -> List[Tuple[int, int, int]]:
    """Generate darker colors for low-key images."""
    base_hue = rng.random()
    
    colors = []
    for i in range(num_colors):
        h = (base_hue + (i * 0.2) + rng.random() * 0.1) % 1.0
        s = 0.3 + rng.random() * 0.4
        v = 0.15 + rng.random() * 0.35  # Dark values
        colors.append(hsv_to_rgb(h, s, v))
    
    return colors


def fill_background(img: Image.Image, brightness: float, rng: np.random.Generator, 
                    style: str = 'neutral') -> Tuple[int, int, int]:
    """Fill image background based on style. Returns the background color."""
    w, h = img.size
    
    if style == 'neutral':
        # Pure gray based on brightness
        v = int(brightness * 255)
        bg = (v, v, v)
    elif style == 'warm':
        # Obvious warm - orange/red/yellow tones, NOT muddy
        hue = rng.choice([0.0, 0.03, 0.06, 0.08, 0.12])  # reds, oranges, yellows
        bg = hsv_to_rgb(hue, 0.4 + rng.random() * 0.3, 0.7 + brightness * 0.25)
    elif style == 'cool':
        # Obvious cool - blue/cyan/purple tones
        hue = rng.choice([0.55, 0.58, 0.62, 0.68, 0.75])  # blues, cyans, purples
        bg = hsv_to_rgb(hue, 0.4 + rng.random() * 0.3, 0.6 + brightness * 0.3)
    elif style == 'tinted':
        # Colorful tinted - NOT gray-green
        hue = rng.random()
        bg = hsv_to_rgb(hue, 0.35 + rng.random() * 0.3, 0.65 + brightness * 0.3)
    elif style == 'white':
        bg = (255, 255, 255)
    elif style == 'black':
        bg = (0, 0, 0)
    elif style == 'dark':
        v = int(15 + brightness * 30)
        bg = (v, v, v)
    elif style == 'light':
        v = int(220 + brightness * 35)
        bg = (min(255, v), min(255, v), min(255, v))
    elif style == 'paper':
        # Cream/ivory paper - warm whites, not gray
        paper_type = rng.choice(['cream', 'ivory', 'white', 'tan'])
        if paper_type == 'cream':
            bg = (255, 253, 240)
        elif paper_type == 'ivory':
            bg = (255, 255, 245)
        elif paper_type == 'tan':
            bg = (240, 225, 200)
        else:
            bg = (255, 255, 255)
    elif style == 'contrast':
        # Bold, saturated background color
        hue = rng.random()
        bg = hsv_to_rgb(hue, 0.5 + rng.random() * 0.4, 0.5 + brightness * 0.4)
    else:
        v = int(brightness * 255)
        bg = (v, v, v)
    
    img.paste(bg, [0, 0, w, h])
    return bg


def complementary_palette(base_hue: float, brightness: float) -> List[Tuple[int, int, int]]:
    """Generate complementary color palette - VIVID."""
    v = 0.75 + brightness * 0.2  # High value
    return [
        hsv_to_rgb(base_hue, 0.8, v),
        hsv_to_rgb((base_hue + 0.5) % 1.0, 0.8, v),
        hsv_to_rgb(base_hue, 0.5, min(1.0, v + 0.1)),
        hsv_to_rgb((base_hue + 0.5) % 1.0, 0.5, v),
    ]


def analogous_palette(base_hue: float, brightness: float) -> List[Tuple[int, int, int]]:
    """Generate analogous color palette (adjacent hues) - VIVID."""
    v = 0.75 + brightness * 0.2
    return [
        hsv_to_rgb((base_hue - 0.08) % 1.0, 0.75, v),
        hsv_to_rgb(base_hue, 0.85, v),
        hsv_to_rgb((base_hue + 0.08) % 1.0, 0.75, v),
        hsv_to_rgb(base_hue, 0.6, min(1.0, v + 0.1)),
    ]


def triadic_palette(base_hue: float, brightness: float) -> List[Tuple[int, int, int]]:
    """Generate triadic color palette (120 degrees apart) - VIVID."""
    v = 0.8 + brightness * 0.15
    return [
        hsv_to_rgb(base_hue, 0.85, v),
        hsv_to_rgb((base_hue + 0.333) % 1.0, 0.85, v),
        hsv_to_rgb((base_hue + 0.666) % 1.0, 0.85, v),
    ]


def split_complementary_palette(base_hue: float, brightness: float) -> List[Tuple[int, int, int]]:
    """Generate split-complementary palette - VIVID."""
    v = 0.75 + brightness * 0.2
    return [
        hsv_to_rgb(base_hue, 0.85, v),
        hsv_to_rgb((base_hue + 0.42) % 1.0, 0.8, v),
        hsv_to_rgb((base_hue + 0.58) % 1.0, 0.8, v),
    ]


def warm_palette(brightness: float, rng: np.random.Generator) -> List[Tuple[int, int, int]]:
    """Generate warm color palette (reds, oranges, yellows) - VIVID."""
    colors = []
    for _ in range(5):
        h = rng.random() * 0.12  # 0-0.12 = red to yellow
        s = 0.7 + rng.random() * 0.3  # High saturation
        v = 0.75 + rng.random() * 0.25  # High value - don't use brightness here
        colors.append(hsv_to_rgb(h, s, v))
    return colors


def cool_palette(brightness: float, rng: np.random.Generator) -> List[Tuple[int, int, int]]:
    """Generate cool color palette (blues, greens, purples) - VIVID."""
    colors = []
    for _ in range(5):
        h = 0.5 + rng.random() * 0.3  # 0.5-0.8 = cyan to purple
        s = 0.7 + rng.random() * 0.3  # High saturation
        v = 0.7 + rng.random() * 0.3  # High value
        colors.append(hsv_to_rgb(h, s, v))
    return colors


# =============================================================================
# ELEMENTS OF ART
# =============================================================================

# --- LINE ---

def draw_line_straight(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Straight lines - horizontal, vertical, diagonal."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_lines = int(10 + noisiness * 30)
    
    for _ in range(num_lines):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        stroke = max(1, int(1 + rng.random() * 8))
        
        line_type = rng.choice(['horizontal', 'vertical', 'diagonal'])
        
        if line_type == 'horizontal':
            y = rng.integers(0, h)
            draw.line([(0, y), (w, y)], fill=(*color, alpha), width=stroke)
        elif line_type == 'vertical':
            x = rng.integers(0, w)
            draw.line([(x, 0), (x, h)], fill=(*color, alpha), width=stroke)
        else:
            # Diagonal - corner to corner or parallel
            if rng.random() > 0.5:
                draw.line([(0, rng.integers(0, h)), (w, rng.integers(0, h))], 
                         fill=(*color, alpha), width=stroke)
            else:
                draw.line([(rng.integers(0, w), 0), (rng.integers(0, w), h)], 
                         fill=(*color, alpha), width=stroke)


def draw_line_stripes_h(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Horizontal stripes - clean parallel lines."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(8 + (1 - noisiness) * 40)
    stroke = max(2, int(spacing * 0.4))
    
    y = 0
    i = 0
    while y < h:
        color = palette[i % len(palette)]
        draw.line([(0, y), (w, y)], fill=color, width=stroke)
        y += spacing
        i += 1


def draw_line_stripes_v(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Vertical stripes - clean parallel lines."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(8 + (1 - noisiness) * 40)
    stroke = max(2, int(spacing * 0.4))
    
    x = 0
    i = 0
    while x < w:
        color = palette[i % len(palette)]
        draw.line([(x, 0), (x, h)], fill=color, width=stroke)
        x += spacing
        i += 1


def draw_line_grid(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Grid pattern - perpendicular straight lines."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(15 + (1 - noisiness) * 50)
    stroke = max(1, int(1 + noisiness * 3))
    
    color = palette[0]
    alpha = int(150 + rng.random() * 105)
    
    # Vertical lines
    for x in range(0, w, spacing):
        draw.line([(x, 0), (x, h)], fill=(*color, alpha), width=stroke)
    
    # Horizontal lines
    for y in range(0, h, spacing):
        draw.line([(0, y), (w, y)], fill=(*color, alpha), width=stroke)


def draw_line_mondrian(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Mondrian-style - rectangular divisions with primary colors."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # White background
    bg_val = int(brightness * 255)
    img.paste((bg_val, bg_val, bg_val), [0, 0, w, h])
    
    # Primary colors + white
    colors = [
        (255, 255, 255),  # white
        (255, 0, 0),      # red
        (0, 0, 255),      # blue
        (255, 255, 0),    # yellow
        (255, 255, 255),  # more white (weighted)
        (255, 255, 255),
    ]
    
    # Recursive subdivision
    def subdivide(x1, y1, x2, y2, depth=0):
        if depth > 4 or (x2 - x1) < 40 or (y2 - y1) < 40:
            # Fill with color
            color = colors[rng.integers(len(colors))]
            draw.rectangle([x1 + 2, y1 + 2, x2 - 2, y2 - 2], fill=color)
            return
        
        if rng.random() > 0.3 + depth * 0.15:
            # Subdivide
            if (x2 - x1) > (y2 - y1):
                # Vertical split
                split = rng.integers(x1 + 40, x2 - 40) if x2 - x1 > 80 else (x1 + x2) // 2
                subdivide(x1, y1, split, y2, depth + 1)
                subdivide(split, y1, x2, y2, depth + 1)
            else:
                # Horizontal split
                split = rng.integers(y1 + 40, y2 - 40) if y2 - y1 > 80 else (y1 + y2) // 2
                subdivide(x1, y1, x2, split, depth + 1)
                subdivide(x1, split, x2, y2, depth + 1)
        else:
            color = colors[rng.integers(len(colors))]
            draw.rectangle([x1 + 2, y1 + 2, x2 - 2, y2 - 2], fill=color)
    
    subdivide(0, 0, w, h)
    
    # Black grid lines
    line_width = int(3 + noisiness * 5)
    
    # Draw lines at subdivision boundaries (simplified - just grid)
    num_v = int(2 + noisiness * 4)
    num_h = int(2 + noisiness * 4)
    
    for i in range(num_v):
        x = int(w * (i + 1) / (num_v + 1))
        x += rng.integers(-30, 31)
        draw.line([(x, 0), (x, h)], fill=(0, 0, 0), width=line_width)
    
    for i in range(num_h):
        y = int(h * (i + 1) / (num_h + 1))
        y += rng.integers(-30, 31)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0), width=line_width)
    
    # Border
    draw.rectangle([0, 0, w-1, h-1], outline=(0, 0, 0), width=line_width)


def draw_line_diagonal(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Diagonal lines - 45 degree patterns."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(10 + (1 - noisiness) * 30)
    stroke = max(1, int(1 + noisiness * 4))
    
    color = palette[0]
    alpha = int(150 + rng.random() * 105)
    
    # Diagonal lines going one way
    for i in range(-h, w + h, spacing):
        draw.line([(i, 0), (i + h, h)], fill=(*color, alpha), width=stroke)
    
    # Cross-hatch if noisy enough
    if noisiness > 0.4:
        color2 = palette[1] if len(palette) > 1 else palette[0]
        for i in range(-h, w + h, spacing):
            draw.line([(i + h, 0), (i, h)], fill=(*color2, alpha), width=stroke)


def draw_line_rays(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Rays - straight lines radiating from a point."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    # Center point (can be off-center for variety)
    cx = w // 2 + rng.integers(-w//4, w//4)
    cy = h // 2 + rng.integers(-h//4, h//4)
    
    num_rays = int(12 + noisiness * 36)
    stroke = max(1, int(1 + noisiness * 4))
    
    for i in range(num_rays):
        angle = 2 * math.pi * i / num_rays
        color = palette[i % len(palette)]
        alpha = int(150 + rng.random() * 105)
        
        # Extend to edge of image
        length = max(w, h)
        end_x = cx + length * math.cos(angle)
        end_y = cy + length * math.sin(angle)
        
        draw.line([(cx, cy), (end_x, end_y)], fill=(*color, alpha), width=stroke)


def draw_line_checker(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Checkerboard pattern - alternating squares."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    spacing = int(16 + (1 - noisiness) * 48)
    
    # Two colors based on brightness
    if brightness > 0.5:
        c1 = (255, 255, 255)
        c2 = (0, 0, 0)
    else:
        c1 = (0, 0, 0)
        c2 = (255, 255, 255)
    
    for x in range(0, w, spacing):
        for y in range(0, h, spacing):
            if ((x // spacing) + (y // spacing)) % 2 == 0:
                draw.rectangle([x, y, x + spacing, y + spacing], fill=c1)
            else:
                draw.rectangle([x, y, x + spacing, y + spacing], fill=c2)


def draw_line_blocks(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Rectangular blocks - hard-edged rectangular divisions."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_blocks = int(5 + noisiness * 15)
    
    for _ in range(num_blocks):
        color = palette[rng.integers(len(palette))]
        
        # Random rectangle with straight edges
        x1 = rng.integers(0, w - 30)
        y1 = rng.integers(0, h - 30)
        x2 = x1 + rng.integers(30, min(200, w - x1))
        y2 = y1 + rng.integers(30, min(200, h - y1))
        
        draw.rectangle([x1, y1, x2, y2], fill=color)


def draw_line_contour(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Contour lines - outlines defining edges of forms."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(5 + noisiness * 15)
    stroke = max(2, int(2 + noisiness * 4))
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        size = int(40 + rng.random() * 150)
        
        shape = rng.choice(['ellipse', 'rect', 'polygon'])
        if shape == 'ellipse':
            draw.ellipse([cx - size//2, cy - size//2, cx + size//2, cy + size//2], 
                        outline=color, width=stroke)
        elif shape == 'rect':
            draw.rectangle([cx - size//2, cy - size//2, cx + size//2, cy + size//2],
                          outline=color, width=stroke)
        else:
            n = rng.integers(3, 8)
            points = [(cx + size//2 * math.cos(2*math.pi*i/n + rng.random()*0.3),
                      cy + size//2 * math.sin(2*math.pi*i/n + rng.random()*0.3)) for i in range(n)]
            draw.polygon(points, outline=color, width=stroke)


def draw_line_gesture(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Gesture lines - quick, expressive strokes suggesting movement."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_strokes = int(10 + noisiness * 30)
    
    for _ in range(num_strokes):
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 155)
        stroke = max(1, int(1 + rng.random() * 6))
        
        points = []
        x, y = rng.integers(0, w), rng.integers(0, h)
        angle = rng.random() * 2 * math.pi
        length = int(50 + rng.random() * 200)
        
        for i in range(20):
            points.append((x, y))
            angle += rng.normal(0, 0.3)
            step = length / 20
            x += step * math.cos(angle)
            y += step * math.sin(angle)
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=stroke)


def draw_line_implied(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Implied lines - dots/elements suggesting line without continuous stroke."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_lines = int(5 + noisiness * 10)
    
    for _ in range(num_lines):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        
        x1, y1 = rng.integers(0, w), rng.integers(0, h)
        x2, y2 = rng.integers(0, w), rng.integers(0, h)
        
        steps = int(10 + rng.random() * 20)
        dot_size = int(3 + noisiness * 5)
        
        for i in range(steps):
            t = i / steps
            x = int(x1 + t * (x2 - x1) + rng.normal(0, 3))
            y = int(y1 + t * (y2 - y1) + rng.normal(0, 3))
            draw.ellipse([x - dot_size, y - dot_size, x + dot_size, y + dot_size],
                        fill=(*color, alpha))


def draw_line_quality(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Edge quality - varying line weights and character."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_lines = int(8 + noisiness * 20)
    
    for _ in range(num_lines):
        color = palette[rng.integers(len(palette))]
        
        points = []
        widths = []
        x, y = rng.integers(50, w - 50), rng.integers(50, h - 50)
        
        for i in range(30):
            points.append((x, y))
            w_var = 1 + 8 * (0.5 + 0.5 * math.sin(i * 0.3 + rng.random()))
            widths.append(int(w_var))
            
            x += rng.integers(-20, 21)
            y += rng.integers(-20, 21)
            x = max(10, min(w - 10, x))
            y = max(10, min(h - 10, y))
        
        for i in range(len(points) - 1):
            alpha = int(150 + rng.random() * 100)
            draw.line([points[i], points[i+1]], fill=(*color, alpha), width=widths[i])


# --- SHAPE ---

def draw_shape_geometric(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Geometric shapes - precise, mathematical forms."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(8 + noisiness * 20)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        
        shape = rng.choice(['rect', 'circle', 'triangle', 'hexagon'])
        size = int(30 + rng.random() * min(w, h) * 0.3)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        if shape == 'rect':
            draw.rectangle([cx - size//2, cy - size//2, cx + size//2, cy + size//2],
                          fill=(*color, alpha))
        elif shape == 'circle':
            draw.ellipse([cx - size//2, cy - size//2, cx + size//2, cy + size//2],
                        fill=(*color, alpha))
        elif shape == 'triangle':
            points = [(cx, cy - size//2), (cx - size//2, cy + size//2), (cx + size//2, cy + size//2)]
            draw.polygon(points, fill=(*color, alpha))
        elif shape == 'hexagon':
            points = [(cx + size//2 * math.cos(math.pi/3 * i),
                      cy + size//2 * math.sin(math.pi/3 * i)) for i in range(6)]
            draw.polygon(points, fill=(*color, alpha))


def draw_shape_organic(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Organic shapes - natural, irregular forms."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(6 + noisiness * 15)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 120)
        
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        base_radius = int(30 + rng.random() * 100)
        
        points = []
        for angle in np.linspace(0, 2 * math.pi, 20):
            r = base_radius * (0.7 + 0.6 * rng.random())
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        
        draw.polygon(points, fill=(*color, alpha))


def draw_shape_triangles(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Triangular shapes - angular geometric forms."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(10 + noisiness * 25)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        
        # Random triangle
        points = [
            (rng.integers(0, w), rng.integers(0, h)),
            (rng.integers(0, w), rng.integers(0, h)),
            (rng.integers(0, w), rng.integers(0, h)),
        ]
        draw.polygon(points, fill=(*color, alpha))


def draw_shape_circles(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Circle shapes - overlapping circular forms."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(10 + noisiness * 30)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(80 + rng.random() * 120)
        
        cx = rng.integers(0, w)
        cy = rng.integers(0, h)
        size = int(20 + rng.random() * min(w, h) * 0.3)
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


def draw_shape_rectangles(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Rectangle shapes - overlapping rectangular forms."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(8 + noisiness * 20)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 155)
        
        x1 = rng.integers(0, w)
        y1 = rng.integers(0, h)
        width = int(30 + rng.random() * 150)
        height = int(30 + rng.random() * 150)
        
        draw.rectangle([x1, y1, x1 + width, y1 + height], fill=(*color, alpha))


def draw_shape_polygons(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Polygon shapes - various sided regular polygons."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(8 + noisiness * 20)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        size = int(30 + rng.random() * 80)
        sides = rng.integers(5, 10)
        rotation = rng.random() * 2 * math.pi
        
        points = [(cx + size * math.cos(2 * math.pi * i / sides + rotation),
                  cy + size * math.sin(2 * math.pi * i / sides + rotation)) 
                 for i in range(sides)]
        draw.polygon(points, fill=(*color, alpha))


def draw_shape_stars(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Star shapes - pointed star forms."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(5 + noisiness * 15)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        outer_r = int(30 + rng.random() * 80)
        inner_r = outer_r * (0.3 + rng.random() * 0.3)
        points_count = rng.integers(5, 9)
        rotation = rng.random() * 2 * math.pi
        
        points = []
        for i in range(points_count * 2):
            angle = math.pi * i / points_count + rotation
            r = outer_r if i % 2 == 0 else inner_r
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        
        draw.polygon(points, fill=(*color, alpha))


def draw_shape_diamonds(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Diamond shapes - rotated squares."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(8 + noisiness * 20)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        size = int(30 + rng.random() * 100)
        
        # Diamond = rotated square
        points = [
            (cx, cy - size),  # top
            (cx + size, cy),  # right
            (cx, cy + size),  # bottom
            (cx - size, cy),  # left
        ]
        draw.polygon(points, fill=(*color, alpha))


# --- FORM (3D illusion) ---

def draw_form_shaded(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """3D forms with shading to suggest volume."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    num_forms = int(3 + noisiness * 8)
    
    for _ in range(num_forms):
        cx = rng.integers(80, w - 80)
        cy = rng.integers(80, h - 80)
        radius = int(40 + rng.random() * 80)
        base_hue = rng.random()
        
        for r in range(radius, 0, -2):
            t = r / radius
            light_factor = 0.3 + 0.7 * (1 - t)
            v = brightness * light_factor
            color = hsv_to_rgb(base_hue, 0.3, v)
            alpha = int(200 + 55 * (1 - t))
            
            offset_x = int((1 - t) * radius * 0.3)
            offset_y = int((1 - t) * radius * 0.3)
            
            draw.ellipse([cx - r + offset_x, cy - r + offset_y,
                         cx + r + offset_x, cy + r + offset_y],
                        fill=(*color, alpha))


def draw_form_perspective(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Forms with perspective - converging lines suggesting depth."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    vp_x = w // 2 + rng.integers(-100, 101)
    vp_y = h // 3
    
    num_boxes = int(4 + noisiness * 8)
    
    for _ in range(num_boxes):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 100)
        
        bx = rng.integers(50, w - 50)
        by = rng.integers(h // 2, h - 50)
        bw = int(40 + rng.random() * 100)
        bh = int(40 + rng.random() * 80)
        
        front = [(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh)]
        draw.polygon(front, fill=(*color, alpha), outline=color)
        
        scale = 0.3
        top_back_l = (bx + (vp_x - bx) * scale, by + (vp_y - by) * scale)
        top_back_r = (bx + bw + (vp_x - bx - bw) * scale, by + (vp_y - by) * scale)
        
        top_face = [front[0], front[1], top_back_r, top_back_l]
        lighter = tuple(min(255, c + 40) for c in color)
        draw.polygon(top_face, fill=(*lighter, alpha - 30))


def draw_form_cubes(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Isometric cubes - 3D cube forms."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_cubes = int(5 + noisiness * 15)
    
    for _ in range(num_cubes):
        base_color = palette[rng.integers(len(palette))]
        cx = rng.integers(60, w - 60)
        cy = rng.integers(60, h - 60)
        size = int(30 + rng.random() * 60)
        
        # Isometric cube vertices - top face
        top = [
            (cx, cy - size * 0.5),
            (cx + size, cy),
            (cx, cy + size * 0.5),
            (cx - size, cy),
        ]
        
        # Left face
        left = [
            (cx - size, cy),
            (cx, cy + size * 0.5),
            (cx, cy + size * 1.5),
            (cx - size, cy + size),
        ]
        
        # Right face
        right = [
            (cx + size, cy),
            (cx + size, cy + size),
            (cx, cy + size * 1.5),
            (cx, cy + size * 0.5),
        ]
        
        # Draw faces with different values
        dark = tuple(max(0, c - 50) for c in base_color)
        mid = base_color
        light = tuple(min(255, c + 30) for c in base_color)
        
        draw.polygon(left, fill=(*dark, 200))
        draw.polygon(right, fill=(*mid, 200))
        draw.polygon(top, fill=(*light, 200))


def draw_form_cylinders(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Cylindrical forms with shading."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_cylinders = int(3 + noisiness * 8)
    
    for _ in range(num_cylinders):
        base_color = palette[rng.integers(len(palette))]
        cx = rng.integers(60, w - 60)
        cy = rng.integers(60, h - 60)
        width = int(40 + rng.random() * 80)
        height = int(60 + rng.random() * 120)
        
        # Draw vertical strips with gradient shading
        for i in range(20):
            t = i / 19
            x = cx - width//2 + int(t * width)
            
            # Shading based on position (light from left)
            shade = math.sin(t * math.pi)
            v = brightness * (0.4 + 0.6 * shade)
            color = hsv_to_rgb(rng.random() * 0.1, 0.3, v)
            
            draw.rectangle([x, cy - height//2, x + width//20 + 1, cy + height//2],
                          fill=(*color, 200))
        
        # Top ellipse
        draw.ellipse([cx - width//2, cy - height//2 - 10, cx + width//2, cy - height//2 + 10],
                    fill=(*base_color, 220))


# --- PATTERN ---

def draw_pattern_dots(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Dot pattern - regular grid of circles."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(15 + (1 - noisiness) * 35)
    size = max(2, spacing // 4)
    
    for x in range(spacing // 2, w, spacing):
        for y in range(spacing // 2, h, spacing):
            color = palette[rng.integers(len(palette))]
            alpha = int(180 + rng.random() * 75)
            draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))


def draw_pattern_waves(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Wave pattern - sinusoidal lines."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(10 + (1 - noisiness) * 30)
    amplitude = int(10 + noisiness * 30)
    stroke = max(1, int(1 + noisiness * 3))
    
    for y_base in range(0, h + amplitude, spacing):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        freq = 0.02 + rng.random() * 0.03
        phase = rng.random() * 2 * math.pi
        
        points = []
        for x in range(0, w, 4):
            y = y_base + amplitude * math.sin(x * freq + phase)
            points.append((x, y))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=stroke)


def draw_pattern_spirals(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Spiral pattern - radiating spirals."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_spirals = int(2 + noisiness * 5)
    
    for _ in range(num_spirals):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        stroke = max(1, int(1 + noisiness * 3))
        
        cx = rng.integers(w // 4, 3 * w // 4)
        cy = rng.integers(h // 4, 3 * h // 4)
        
        points = []
        for t in np.linspace(0, 6 * math.pi, 200):
            r = 5 + t * (5 + noisiness * 10)
            x = cx + r * math.cos(t)
            y = cy + r * math.sin(t)
            points.append((x, y))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=stroke)


def draw_pattern_concentric(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Concentric pattern - nested circles or squares."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    cx = w // 2 + rng.integers(-50, 51)
    cy = h // 2 + rng.integers(-50, 51)
    
    spacing = int(10 + (1 - noisiness) * 20)
    stroke = max(1, int(1 + noisiness * 3))
    max_r = int(max(w, h) * 0.7)
    
    shape = rng.choice(['circle', 'square'])
    
    for r in range(spacing, max_r, spacing):
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 100)
        
        if shape == 'circle':
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], 
                        outline=(*color, alpha), width=stroke)
        else:
            draw.rectangle([cx - r, cy - r, cx + r, cy + r],
                          outline=(*color, alpha), width=stroke)


def draw_pattern_hexagonal(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Hexagonal pattern - honeycomb grid."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    size = int(20 + (1 - noisiness) * 30)
    stroke = max(1, int(1 + noisiness * 2))
    
    # Hexagon dimensions
    hex_w = size * 2
    hex_h = size * math.sqrt(3)
    
    row = 0
    y = 0
    while y < h + hex_h:
        x_offset = (row % 2) * (hex_w * 0.75)
        x = x_offset
        while x < w + hex_w:
            color = palette[rng.integers(len(palette))]
            alpha = int(150 + rng.random() * 105)
            
            # Hexagon vertices
            points = []
            for i in range(6):
                angle = math.pi / 3 * i
                px = x + size * math.cos(angle)
                py = y + size * math.sin(angle)
                points.append((px, py))
            
            draw.polygon(points, outline=(*color, alpha), width=stroke)
            x += hex_w * 1.5
        
        y += hex_h / 2
        row += 1


def draw_pattern_zigzag(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Zigzag pattern - sharp angular waves."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(15 + (1 - noisiness) * 30)
    amplitude = int(10 + noisiness * 25)
    stroke = max(1, int(1 + noisiness * 3))
    
    for y_base in range(0, h + amplitude, spacing):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        
        points = []
        for x in range(0, w + spacing, spacing // 2):
            y_offset = amplitude if (x // (spacing // 2)) % 2 == 0 else -amplitude
            points.append((x, y_base + y_offset))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=stroke)


def draw_pattern_chevron(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Chevron pattern - V-shaped stripes."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(20 + (1 - noisiness) * 40)
    stroke = max(2, int(spacing * 0.4))
    
    for y in range(0, h + spacing * 2, spacing):
        color = palette[(y // spacing) % len(palette)]
        alpha = int(180 + rng.random() * 75)
        
        # V pointing right
        points = []
        for x in range(0, w + spacing, spacing):
            # Alternate up/down
            if (x // spacing) % 2 == 0:
                points.append((x, y))
            else:
                points.append((x, y + spacing // 2))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=stroke)


# --- SPACE ---

def draw_space_positive_negative(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Positive and negative space - figure/ground relationship."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    bg = int(brightness * 255)
    fg = 255 - bg
    draw.rectangle([0, 0, w, h], fill=(bg, bg, bg))
    
    num_shapes = int(3 + noisiness * 8)
    
    for _ in range(num_shapes):
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        size = int(60 + rng.random() * 150)
        
        points = []
        for angle in np.linspace(0, 2 * math.pi, 16):
            r = size * (0.6 + 0.4 * rng.random())
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        
        draw.polygon(points, fill=(fg, fg, fg))


def draw_space_depth(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Depth through overlapping and size variation."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    num_layers = int(4 + noisiness * 6)
    
    for layer in range(num_layers):
        depth = layer / num_layers
        size_mult = 0.4 + depth * 0.8
        value = brightness * (0.5 + depth * 0.5)
        sat = 0.2 + depth * 0.5
        
        color = hsv_to_rgb(rng.random(), sat, value)
        alpha = int(100 + depth * 155)
        
        num_shapes = int(2 + rng.random() * 4)
        for _ in range(num_shapes):
            size = int((30 + rng.random() * 80) * size_mult)
            cx = rng.integers(size, max(size + 1, w - size))
            cy = rng.integers(size, max(size + 1, h - size))
            
            draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                        fill=(*color, alpha))


# --- VALUE (tonal value) ---

def draw_value_gradient(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Value gradients - smooth tonal transitions."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    for y in range(h):
        t = y / h
        v = int((brightness * (1 - t) + (1 - brightness) * t) * 255)
        draw.line([(0, y), (w, y)], fill=(v, v, v))
    
    if noisiness > 0.2:
        draw2 = ImageDraw.Draw(img, 'RGBA')
        num_shapes = int(noisiness * 15)
        for _ in range(num_shapes):
            v = int(rng.random() * 255)
            alpha = int(50 + rng.random() * 100)
            size = int(20 + rng.random() * 100)
            cx = rng.integers(0, w)
            cy = rng.integers(0, h)
            draw2.ellipse([cx - size, cy - size, cx + size, cy + size],
                         fill=(v, v, v, alpha))


def draw_value_high_key(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """High-key - predominantly light values."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    bg = int(220 + brightness * 35)
    img.paste((bg, bg, bg), [0, 0, w, h])
    
    num_shapes = int(8 + noisiness * 15)
    for _ in range(num_shapes):
        v = int(180 + rng.random() * 75)
        alpha = int(80 + rng.random() * 120)
        size = int(30 + rng.random() * 120)
        cx = rng.integers(0, w)
        cy = rng.integers(0, h)
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(v, v, v, alpha))


def draw_value_low_key(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Low-key - predominantly dark values with dramatic lighting."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # Very dark background
    img.paste((10, 8, 12), [0, 0, w, h])
    
    # A few shapes emerging from darkness
    num_shapes = int(4 + noisiness * 8)
    for _ in range(num_shapes):
        # Dark to mid-dark values only
        v = int(20 + rng.random() * 60)
        # Slight color tint
        r = v + rng.integers(-10, 11)
        g = v + rng.integers(-10, 11)
        b = v + rng.integers(-10, 11)
        alpha = int(150 + rng.random() * 105)
        size = int(40 + rng.random() * 150)
        cx = rng.integers(0, w)
        cy = rng.integers(0, h)
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(max(0, r), max(0, g), max(0, b), alpha))
    
    # One or two brighter accents
    for _ in range(1 + int(noisiness * 2)):
        v = int(80 + rng.random() * 80)  # Mid-value highlight
        size = int(20 + rng.random() * 40)
        cx = rng.integers(w // 4, 3 * w // 4)
        cy = rng.integers(h // 4, 3 * h // 4)
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(v, v - 5, v - 10, 200))


def draw_chiaroscuro(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Chiaroscuro - dramatic light/dark contrast."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    img.paste((15, 12, 10), [0, 0, w, h])
    
    light_x = rng.integers(w // 4, 3 * w // 4)
    light_y = rng.integers(h // 4, h // 2)
    
    max_radius = int(min(w, h) * 0.8)
    for r in range(max_radius, 0, -3):
        t = 1 - (r / max_radius)
        v = int(brightness * 255 * t * t)
        alpha = int(20 + t * 100)
        draw.ellipse([light_x - r, light_y - r, light_x + r, light_y + r],
                    fill=(v, v - 5, v - 10, alpha))
    
    num_forms = int(2 + noisiness * 5)
    for _ in range(num_forms):
        cx = rng.integers(50, w - 50)
        cy = rng.integers(h // 3, h - 50)
        size = int(40 + rng.random() * 80)
        
        dist = math.sqrt((cx - light_x)**2 + (cy - light_y)**2)
        light_amount = max(0, 1 - dist / max_radius)
        
        for r in range(size, 0, -2):
            t = r / size
            v = int(brightness * 255 * light_amount * (1 - t * 0.5))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(v, v - 3, v - 5))


# --- COLOUR ---

def draw_colour_complementary(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Complementary colors - opposite on color wheel."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    base_hue = rng.random()
    palette = complementary_palette(base_hue, brightness)
    
    num_shapes = int(8 + noisiness * 20)
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        size = int(30 + rng.random() * min(w, h) * 0.35)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


def draw_colour_analogous(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Analogous colors - adjacent on color wheel."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    base_hue = rng.random()
    palette = analogous_palette(base_hue, brightness)
    
    num_shapes = int(10 + noisiness * 20)
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 155)
        size = int(30 + rng.random() * min(w, h) * 0.35)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


def draw_colour_triadic(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Triadic colors - three colors equally spaced."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    base_hue = rng.random()
    palette = triadic_palette(base_hue, brightness)
    
    num_shapes = int(9 + noisiness * 18)
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        size = int(30 + rng.random() * min(w, h) * 0.3)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        shape = rng.choice(['rect', 'ellipse', 'tri'])
        if shape == 'rect':
            draw.rectangle([cx - size, cy - size, cx + size, cy + size],
                          fill=(*color, alpha))
        elif shape == 'ellipse':
            draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                        fill=(*color, alpha))
        else:
            points = [(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)]
            draw.polygon(points, fill=(*color, alpha))


def draw_colour_split_complementary(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Split-complementary colors."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    base_hue = rng.random()
    palette = split_complementary_palette(base_hue, brightness)
    
    num_shapes = int(9 + noisiness * 18)
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        size = int(30 + rng.random() * min(w, h) * 0.3)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


def draw_colour_warm(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Warm color temperature - reds, oranges, yellows."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    palette = warm_palette(brightness, rng)
    
    # Strong warm background
    bg = hsv_to_rgb(0.06 + rng.random() * 0.06, 0.35 + rng.random() * 0.2, brightness)
    img.paste(bg, [0, 0, w, h])
    
    num_shapes = int(10 + noisiness * 20)
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        size = int(25 + rng.random() * min(w, h) * 0.35)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


def draw_colour_cool(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Cool color temperature - blues, greens, purples."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    palette = cool_palette(brightness, rng)
    
    # Strong cool background
    bg = hsv_to_rgb(0.55 + rng.random() * 0.1, 0.3 + rng.random() * 0.2, brightness)
    img.paste(bg, [0, 0, w, h])
    
    num_shapes = int(10 + noisiness * 20)
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        size = int(25 + rng.random() * min(w, h) * 0.35)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


def draw_colour_saturated(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """High saturation - vivid colors."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # Dark or neutral background to make colors pop
    bg_v = max(0.1, brightness - 0.3)
    bg = hsv_to_rgb(rng.random(), 0.1, bg_v)
    img.paste(bg, [0, 0, w, h])
    
    # Fully saturated colors
    colors = [hsv_to_rgb(i/8, 0.95, max(0.5, brightness)) for i in range(8)]
    
    num_shapes = int(10 + noisiness * 25)
    for _ in range(num_shapes):
        color = colors[rng.integers(len(colors))]
        alpha = int(200 + rng.random() * 55)
        size = int(30 + rng.random() * min(w, h) * 0.35)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


def draw_colour_muted(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Low saturation - muted, desaturated colors."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # Muted background
    base_hue = rng.random()
    bg = hsv_to_rgb(base_hue, 0.15, brightness)
    img.paste(bg, [0, 0, w, h])
    
    # Low saturation colors in similar hue range
    colors = [hsv_to_rgb((base_hue + rng.random() * 0.3) % 1.0, 0.15 + rng.random() * 0.2, 
                         brightness + (rng.random() - 0.5) * 0.3) for _ in range(6)]
    
    num_shapes = int(10 + noisiness * 20)
    for _ in range(num_shapes):
        color = colors[rng.integers(len(colors))]
        alpha = int(150 + rng.random() * 105)
        size = int(35 + rng.random() * min(w, h) * 0.35)
        cx = rng.integers(size//2, max(size//2 + 1, w - size//2))
        cy = rng.integers(size//2, max(size//2 + 1, h - size//2))
        
        draw.ellipse([cx - size, cy - size, cx + size, cy + size],
                    fill=(*color, alpha))


# --- TEXTURE ---

def draw_texture_stipple(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Stipple texture - dots of varying density."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    base_color = palette[0]
    spacing = int(3 + (1 - noisiness) * 6)
    
    for x in range(0, w, spacing):
        for y in range(0, h, spacing):
            size = int(1 + rng.random() * 3 * noisiness)
            alpha = int(50 + rng.random() * 150)
            ox = int(rng.normal(0, 2))
            oy = int(rng.normal(0, 2))
            draw.ellipse([x + ox - size, y + oy - size, x + ox + size, y + oy + size],
                        fill=(*base_color, alpha))


def draw_texture_crosshatch(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Crosshatch texture - overlapping diagonal lines, like pen drawing."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # Paper-like background
    paper_color = (255, 252, 245) if brightness > 0.5 else (240, 235, 225)
    img.paste(paper_color, [0, 0, w, h])
    
    # Dark ink color for crosshatch
    ink_colors = [(30, 25, 20), (50, 40, 35), (20, 30, 40)]  # Dark browns/blues
    ink = ink_colors[rng.integers(len(ink_colors))]
    
    spacing = int(6 + (1 - noisiness) * 10)
    stroke = max(1, int(1 + noisiness * 2))
    
    # First direction - clear visible lines
    for i in range(-h, w + h, spacing):
        alpha = int(120 + rng.random() * 80)
        draw.line([(i, 0), (i + h, h)], fill=(*ink, alpha), width=stroke)
    
    # Second direction - crosshatch
    for i in range(-h, w + h, spacing):
        alpha = int(100 + rng.random() * 80)
        draw.line([(i + h, 0), (i, h)], fill=(*ink, alpha), width=stroke)


def draw_texture_grain(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Film grain texture - colored noise like vintage film."""
    w, h = img.size
    
    # Choose a film stock color cast
    film_types = [
        {'base': (245, 235, 220), 'tint': (10, -5, -15)},   # Warm sepia
        {'base': (230, 240, 245), 'tint': (-10, 0, 15)},    # Cool blue
        {'base': (240, 245, 230), 'tint': (-5, 10, -10)},   # Green tint
        {'base': (245, 230, 235), 'tint': (10, -10, 5)},    # Magenta
    ]
    film = film_types[rng.integers(len(film_types))]
    
    # Create base with film color
    arr = np.zeros((h, w, 3), dtype=np.float32)
    for c in range(3):
        arr[:, :, c] = film['base'][c] * brightness + 50 * (1 - brightness)
    
    # Add colored grain noise
    noise_intensity = 20 + noisiness * 40
    for c in range(3):
        noise = rng.normal(film['tint'][c], noise_intensity, (h, w))
        arr[:, :, c] = np.clip(arr[:, :, c] + noise, 0, 255)
    
    img.paste(Image.fromarray(arr.astype(np.uint8)))


def draw_texture_weave(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Woven texture - interlocking horizontal and vertical threads."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(6 + (1 - noisiness) * 10)
    
    c1 = palette[0]
    c2 = palette[1] if len(palette) > 1 else palette[0]
    
    # Vertical threads
    for x in range(0, w, spacing):
        alpha = int(80 + rng.random() * 80)
        draw.line([(x, 0), (x, h)], fill=(*c1, alpha), width=2)
    
    # Horizontal threads (weaving over/under)
    for y in range(0, h, spacing):
        for x in range(0, w, spacing * 2):
            alpha = int(80 + rng.random() * 80)
            draw.line([(x, y), (x + spacing, y)], fill=(*c2, alpha), width=2)


def draw_texture_noise(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Random noise texture - TV static style."""
    w, h = img.size
    
    base = brightness * 255
    spread = noisiness * 200
    
    arr = rng.normal(base, spread, (h, w, 3))
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    
    img.paste(Image.fromarray(arr))


def draw_texture_wood(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Wood grain texture - parallel wavy lines."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # Wood tones
    base_hue = 0.08  # Orange-brown
    
    # Background
    bg = hsv_to_rgb(base_hue, 0.4, brightness)
    img.paste(bg, [0, 0, w, h])
    
    spacing = int(4 + (1 - noisiness) * 8)
    
    for y in range(0, h, spacing):
        color = hsv_to_rgb(base_hue + rng.random() * 0.02, 0.5 + rng.random() * 0.2, 
                          brightness * (0.7 + rng.random() * 0.3))
        alpha = int(60 + rng.random() * 100)
        
        # Wavy line
        points = []
        for x in range(0, w, 8):
            wave = math.sin(x * 0.02 + rng.random()) * (3 + noisiness * 5)
            points.append((x, y + wave))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=1)


def draw_texture_marble(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Marble texture - white stone with visible dark veins."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # White/cream marble background
    marble_types = [
        (250, 248, 245),  # White Carrara
        (245, 240, 230),  # Cream
        (240, 235, 240),  # Slight pink
        (235, 240, 245),  # Slight blue-gray
    ]
    bg = marble_types[rng.integers(len(marble_types))]
    img.paste(bg, [0, 0, w, h])
    
    # Vein colors - dark and visible
    vein_colors = [
        (60, 55, 50),    # Dark gray
        (80, 70, 60),    # Brown-gray
        (50, 60, 70),    # Blue-gray
        (90, 80, 70),    # Warm gray
    ]
    
    num_veins = int(8 + noisiness * 15)
    
    for _ in range(num_veins):
        vein_color = vein_colors[rng.integers(len(vein_colors))]
        alpha = int(100 + rng.random() * 100)  # Much more visible
        stroke = max(1, int(1 + rng.random() * 3))
        
        # Wandering vein path
        points = []
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        angle = rng.random() * 2 * math.pi
        
        for _ in range(60 + int(noisiness * 40)):
            points.append((x, y))
            angle += rng.normal(0, 0.35)
            x += 6 * math.cos(angle)
            y += 6 * math.sin(angle)
        
        if len(points) > 1:
            draw.line(points, fill=(*vein_color, alpha), width=stroke)
    
    # Add some subtle secondary veins
    for _ in range(num_veins * 2):
        vein_color = vein_colors[rng.integers(len(vein_colors))]
        alpha = int(40 + rng.random() * 60)
        
        points = []
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        angle = rng.random() * 2 * math.pi
        
        for _ in range(20 + int(noisiness * 20)):
            points.append((x, y))
            angle += rng.normal(0, 0.5)
            x += 5 * math.cos(angle)
            y += 5 * math.sin(angle)
        
        if len(points) > 1:
            draw.line(points, fill=(*vein_color, alpha), width=1)


def draw_texture_concrete(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Concrete texture - rough surface with aggregate and pits."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # Concrete base color with slight warm or cool tint
    tint = rng.choice(['warm', 'cool', 'neutral'])
    if tint == 'warm':
        base_color = (180, 175, 165)
    elif tint == 'cool':
        base_color = (170, 175, 180)
    else:
        base_color = (175, 175, 175)
    
    # Adjust for brightness
    base_color = tuple(int(c * (0.5 + brightness * 0.5)) for c in base_color)
    img.paste(base_color, [0, 0, w, h])
    
    # Add subtle color variation patches
    num_patches = int(10 + noisiness * 20)
    for _ in range(num_patches):
        px = rng.integers(0, w)
        py = rng.integers(0, h)
        size = int(30 + rng.random() * 80)
        variation = rng.integers(-20, 21)
        patch_color = tuple(max(0, min(255, c + variation)) for c in base_color)
        alpha = int(30 + rng.random() * 50)
        draw.ellipse([px - size, py - size, px + size, py + size], 
                    fill=(*patch_color, alpha))
    
    # Add visible aggregate (small stones)
    num_aggregate = int(50 + noisiness * 150)
    for _ in range(num_aggregate):
        ax = rng.integers(0, w)
        ay = rng.integers(0, h)
        size = int(2 + rng.random() * 6)
        # Aggregate colors - various grays and browns
        agg_v = rng.integers(100, 200)
        agg_color = (agg_v + rng.integers(-20, 21), 
                    agg_v + rng.integers(-20, 21), 
                    agg_v + rng.integers(-30, 11))
        alpha = int(150 + rng.random() * 105)
        draw.ellipse([ax - size, ay - size, ax + size, ay + size],
                    fill=(*agg_color, alpha))
    
    # Add pits/holes (darker spots)
    num_pits = int(20 + noisiness * 60)
    for _ in range(num_pits):
        px = rng.integers(0, w)
        py = rng.integers(0, h)
        size = int(1 + rng.random() * 4)
        pit_color = tuple(max(0, c - 40 - rng.integers(0, 30)) for c in base_color)
        draw.ellipse([px - size, py - size, px + size, py + size],
                    fill=(*pit_color, 200))


def draw_texture_fabric(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Fabric/canvas texture - fine grid with variation."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    # Base fabric color
    bg = palette[0]
    img.paste(bg, [0, 0, w, h])
    
    spacing = int(2 + (1 - noisiness) * 3)
    
    # Fine threads
    for x in range(0, w, spacing):
        alpha = int(20 + rng.random() * 40)
        v = int(brightness * 255 * 0.8)
        draw.line([(x, 0), (x, h)], fill=(v, v, v, alpha), width=1)
    
    for y in range(0, h, spacing):
        alpha = int(20 + rng.random() * 40)
        v = int(brightness * 255 * 0.85)
        draw.line([(0, y), (w, y)], fill=(v, v, v, alpha), width=1)


# --- MARK-MAKING ---

def draw_marks_brush(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Brush stroke marks - painterly strokes."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_strokes = int(15 + noisiness * 40)
    
    for _ in range(num_strokes):
        color = palette[rng.integers(len(palette))]
        alpha = int(80 + rng.random() * 120)
        
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        length = int(30 + rng.random() * 150)
        width = int(5 + rng.random() * 25)
        angle = rng.random() * 2 * math.pi
        
        points = []
        for i in range(15):
            t = i / 14
            curve = math.sin(t * math.pi) * 20
            px = x + t * length * math.cos(angle) + curve * math.sin(angle)
            py = y + t * length * math.sin(angle) - curve * math.cos(angle)
            points.append((px, py))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=width)


def draw_marks_stipple(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Stippling marks - dots creating tone."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_dots = int(500 + noisiness * 2000)
    
    for _ in range(num_dots):
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        
        density_factor = 1 - (y / h) * 0.5
        if rng.random() > density_factor:
            continue
        
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 155)
        size = int(1 + rng.random() * 3)
        
        draw.ellipse([x - size, y - size, x + size, y + size],
                    fill=(*color, alpha))


def draw_marks_hatching(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Hatching marks - parallel lines for shading."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    base_color = palette[0]
    spacing = int(4 + (1 - noisiness) * 10)
    stroke = max(1, int(1 + noisiness * 2))
    
    angle = rng.random() * math.pi
    
    for i in range(-max(w, h), max(w, h) * 2, spacing):
        alpha = int(60 + rng.random() * 100)
        
        x1 = i
        y1 = 0
        x2 = i + h * math.tan(angle) if abs(math.tan(angle)) < 10 else i
        y2 = h
        
        draw.line([(x1, y1), (x2, y2)], fill=(*base_color, alpha), width=stroke)
    
    if noisiness > 0.4:
        angle2 = angle + math.pi / 4
        for i in range(-max(w, h), max(w, h) * 2, spacing * 2):
            alpha = int(40 + rng.random() * 60)
            x1 = i
            y1 = 0
            x2 = i + h * math.tan(angle2) if abs(math.tan(angle2)) < 10 else i
            y2 = h
            draw.line([(x1, y1), (x2, y2)], fill=(*base_color, alpha), width=stroke)


def draw_marks_splatter(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Splatter marks - chaotic paint splashes like Jackson Pollock."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_splatters = int(8 + noisiness * 25)
    
    for _ in range(num_splatters):
        color = palette[rng.integers(len(palette))]
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        
        # Main impact blob - irregular shape
        size = int(15 + rng.random() * 50)
        alpha = int(180 + rng.random() * 75)
        
        # Draw irregular blob
        blob_points = []
        for i in range(12):
            angle = 2 * math.pi * i / 12
            r = size * (0.6 + rng.random() * 0.8)
            blob_points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(blob_points, fill=(*color, alpha))
        
        # Many tiny droplets radiating outward - the splatter effect
        num_drops = int(20 + noisiness * 60)
        for _ in range(num_drops):
            angle = rng.random() * 2 * math.pi
            # Drops spray outward with varying distances
            dist = size * (0.5 + rng.random() * 4)
            dx = cx + dist * math.cos(angle)
            dy = cy + dist * math.sin(angle)
            
            # Drops get smaller further from center
            drop_size = max(1, int((1 + rng.random() * 4) * (1 - dist / (size * 5))))
            drop_alpha = int(alpha * (0.5 + rng.random() * 0.5))
            
            draw.ellipse([dx - drop_size, dy - drop_size, dx + drop_size, dy + drop_size],
                        fill=(*color, drop_alpha))
        
        # Some linear drip trails
        num_trails = int(2 + noisiness * 5)
        for _ in range(num_trails):
            angle = rng.random() * 2 * math.pi
            trail_len = int(size * (1 + rng.random() * 3))
            end_x = cx + trail_len * math.cos(angle)
            end_y = cy + trail_len * math.sin(angle)
            draw.line([(cx, cy), (end_x, end_y)], fill=(*color, alpha // 2), width=int(1 + rng.random() * 3))


def draw_marks_scribble(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Scribble marks - chaotic overlapping pencil/pen scribbles."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_scribbles = int(8 + noisiness * 25)
    
    for _ in range(num_scribbles):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        stroke = int(2 + rng.random() * 4)
        
        # Starting point
        x = rng.integers(30, w - 30)
        y = rng.integers(30, h - 30)
        
        # Scribble as tight back-and-forth motion
        points = [(x, y)]
        direction = rng.random() * 2 * math.pi
        
        for _ in range(40 + int(noisiness * 80)):
            # Small movements with frequent direction changes
            step = 5 + rng.random() * 15
            direction += rng.normal(0, 0.8)  # Wandering direction
            
            # Occasionally reverse direction (scribbling back)
            if rng.random() < 0.2:
                direction += math.pi + rng.normal(0, 0.3)
            
            x += step * math.cos(direction)
            y += step * math.sin(direction)
            
            # Keep in bounds loosely
            x = max(10, min(w - 10, x))
            y = max(10, min(h - 10, y))
            
            points.append((x, y))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=stroke)
    
    # Add some circular scribble clusters
    num_clusters = int(2 + noisiness * 5)
    for _ in range(num_clusters):
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 100)
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        radius = int(20 + rng.random() * 60)
        
        # Circular scribble
        points = []
        for i in range(100):
            angle = i * 0.3 + rng.random() * 0.5
            r = radius * (0.3 + 0.7 * rng.random())
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=2)


def draw_marks_drip(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Drip marks - vertical dripping paint."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_drips = int(10 + noisiness * 30)
    
    for _ in range(num_drips):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        
        x = rng.integers(0, w)
        y_start = rng.integers(0, h // 2)
        length = int(50 + rng.random() * (h - y_start))
        width = int(2 + rng.random() * 8)
        
        # Drip with slight wobble
        points = []
        for y in range(y_start, min(h, y_start + length), 3):
            wobble = rng.normal(0, 1)
            points.append((x + wobble, y))
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=width)
        
        # Blob at bottom
        if y_start + length < h:
            blob_size = int(width * 1.5)
            draw.ellipse([x - blob_size, y_start + length - blob_size,
                         x + blob_size, y_start + length + blob_size],
                        fill=(*color, alpha))


def draw_marks_knife(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Palette knife marks - thick, textured strokes."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_strokes = int(8 + noisiness * 20)
    
    for _ in range(num_strokes):
        color = palette[rng.integers(len(palette))]
        alpha = int(180 + rng.random() * 75)
        
        # Wide, angular stroke
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        length = int(40 + rng.random() * 150)
        width = int(15 + rng.random() * 40)
        angle = rng.random() * 2 * math.pi
        
        # Parallelogram shape
        dx = length * math.cos(angle)
        dy = length * math.sin(angle)
        wx = width * math.cos(angle + math.pi/2)
        wy = width * math.sin(angle + math.pi/2)
        
        points = [
            (x, y),
            (x + dx, y + dy),
            (x + dx + wx, y + dy + wy),
            (x + wx, y + wy),
        ]
        draw.polygon(points, fill=(*color, alpha))


def draw_marks_dots(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Dot pattern marks - regular or irregular dot grid."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    spacing = int(10 + (1 - noisiness) * 25)
    
    for x in range(spacing // 2, w, spacing):
        for y in range(spacing // 2, h, spacing):
            color = palette[rng.integers(len(palette))]
            alpha = int(150 + rng.random() * 105)
            size = int(2 + rng.random() * (spacing * 0.3))
            
            # Random offset for noisiness
            ox = int(rng.normal(0, noisiness * 5))
            oy = int(rng.normal(0, noisiness * 5))
            
            draw.ellipse([x + ox - size, y + oy - size, x + ox + size, y + oy + size],
                        fill=(*color, alpha))


# =============================================================================
# PRINCIPLES OF DESIGN
# =============================================================================

def draw_balance_symmetrical(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Symmetrical balance - mirror image composition."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(4 + noisiness * 10)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(120 + rng.random() * 135)
        
        size = int(20 + rng.random() * 80)
        x = rng.integers(size, w // 2 - size // 2)
        y = rng.integers(size, h - size)
        
        draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))
        mirror_x = w - x
        draw.ellipse([mirror_x - size, y - size, mirror_x + size, y + size], fill=(*color, alpha))


def draw_balance_asymmetrical(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Asymmetrical balance - visual weight without mirror."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    big_side = rng.choice(['left', 'right'])
    big_x = w // 4 if big_side == 'left' else 3 * w // 4
    big_size = int(80 + rng.random() * 100)
    big_color = palette[0]
    draw.ellipse([big_x - big_size, h // 2 - big_size, big_x + big_size, h // 2 + big_size],
                fill=(*big_color, 200))
    
    small_x_base = 3 * w // 4 if big_side == 'left' else w // 4
    num_small = int(3 + noisiness * 5)
    
    for i in range(num_small):
        color = palette[rng.integers(len(palette))]
        alpha = int(150 + rng.random() * 105)
        size = int(20 + rng.random() * 40)
        x = small_x_base + rng.integers(-80, 81)
        y = rng.integers(50, h - 50)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))


def draw_balance_radial(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Radial balance - elements radiating from center."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    cx, cy = w // 2, h // 2
    num_rays = int(6 + noisiness * 12)
    
    for i in range(num_rays):
        angle = 2 * math.pi * i / num_rays
        color = palette[i % len(palette)]
        alpha = int(100 + rng.random() * 100)
        
        length = int(min(w, h) * 0.35 + rng.random() * min(w, h) * 0.1)
        width = int(15 + rng.random() * 30)
        
        end_x = cx + length * math.cos(angle)
        end_y = cy + length * math.sin(angle)
        
        points = [
            (cx + width * math.cos(angle + math.pi/2) * 0.3, 
             cy + width * math.sin(angle + math.pi/2) * 0.3),
            (cx + width * math.cos(angle - math.pi/2) * 0.3,
             cy + width * math.sin(angle - math.pi/2) * 0.3),
            (end_x + width * math.cos(angle - math.pi/2),
             end_y + width * math.sin(angle - math.pi/2)),
            (end_x + width * math.cos(angle + math.pi/2),
             end_y + width * math.sin(angle + math.pi/2)),
        ]
        draw.polygon(points, fill=(*color, alpha))


def draw_emphasis_focal(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Focal point emphasis - clear center of attention."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    for _ in range(int(10 + noisiness * 15)):
        color = palette[rng.integers(1, len(palette))]
        alpha = int(40 + rng.random() * 60)
        size = int(20 + rng.random() * 60)
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))
    
    focal_x = w // 2 + rng.integers(-w//6, w//6)
    focal_y = h // 2 + rng.integers(-h//6, h//6)
    focal_size = int(60 + rng.random() * 80)
    focal_color = hsv_to_rgb(rng.random(), 0.9, min(1.0, brightness + 0.3))
    
    draw.ellipse([focal_x - focal_size, focal_y - focal_size,
                  focal_x + focal_size, focal_y + focal_size],
                fill=(*focal_color, 255))


def draw_hierarchy(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Hierarchy - ordered importance of elements."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    # Primary element - largest, most prominent
    primary_size = int(min(w, h) * 0.25)
    primary_x = w // 2
    primary_y = h // 3
    draw.ellipse([primary_x - primary_size, primary_y - primary_size,
                  primary_x + primary_size, primary_y + primary_size],
                fill=(*palette[0], 255))
    
    # Secondary elements - medium size
    for i in range(3):
        size = int(primary_size * 0.5)
        x = w // 4 + (i * w // 4)
        y = h * 2 // 3
        draw.ellipse([x - size, y - size, x + size, y + size],
                    fill=(*palette[1], 200))
    
    # Tertiary elements - small
    num_small = int(5 + noisiness * 10)
    for _ in range(num_small):
        size = int(primary_size * 0.2)
        x = rng.integers(size, w - size)
        y = rng.integers(size, h - size)
        draw.ellipse([x - size, y - size, x + size, y + size],
                    fill=(*palette[2], 120))


def draw_movement_flow(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Movement - flowing lines guiding the eye."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_flows = int(5 + noisiness * 10)
    
    for _ in range(num_flows):
        color = palette[rng.integers(len(palette))]
        alpha = int(80 + rng.random() * 120)
        width = int(3 + rng.random() * 15)
        
        points = []
        x = rng.integers(0, w)
        y = rng.integers(0, h)
        angle = rng.random() * 2 * math.pi
        
        for _ in range(30):
            points.append((x, y))
            angle += rng.normal(0, 0.2)
            x += 15 * math.cos(angle)
            y += 15 * math.sin(angle)
        
        if len(points) > 1:
            draw.line(points, fill=(*color, alpha), width=width)


def draw_rhythm_pattern(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Rhythm through repetition with variation."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    base_spacing = int(30 + (1 - noisiness) * 40)
    
    for x in range(base_spacing, w - base_spacing, base_spacing):
        for y in range(base_spacing, h - base_spacing, base_spacing):
            size = int(base_spacing * 0.3 * (0.5 + rng.random()))
            color = palette[rng.integers(len(palette))]
            alpha = int(100 + rng.random() * 155)
            
            ox = int(rng.normal(0, noisiness * 10))
            oy = int(rng.normal(0, noisiness * 10))
            
            draw.ellipse([x + ox - size, y + oy - size, x + ox + size, y + oy + size],
                        fill=(*color, alpha))


def draw_unity_harmony(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Unity - cohesive, harmonious composition."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    base_hue = rng.random()
    palette = [hsv_to_rgb((base_hue + i * 0.05) % 1.0, 0.5, brightness) for i in range(4)]
    
    shape_type = rng.choice(['circles', 'squares', 'organic'])
    
    num_shapes = int(12 + noisiness * 20)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        alpha = int(100 + rng.random() * 100)
        size = int(25 + rng.random() * 60)
        x = rng.integers(size, max(size + 1, w - size))
        y = rng.integers(size, max(size + 1, h - size))
        
        if shape_type == 'circles':
            draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))
        elif shape_type == 'squares':
            draw.rectangle([x - size, y - size, x + size, y + size], fill=(*color, alpha))
        else:
            points = []
            for angle in np.linspace(0, 2 * math.pi, 8):
                r = size * (0.7 + 0.3 * rng.random())
                points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
            draw.polygon(points, fill=(*color, alpha))


def draw_variety_contrast(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Variety - diverse elements creating interest."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    colors = [hsv_to_rgb(i / 6, 0.6 + rng.random() * 0.3, brightness) for i in range(6)]
    shapes = ['circle', 'rect', 'triangle', 'line', 'blob']
    
    num_elements = int(10 + noisiness * 20)
    
    for _ in range(num_elements):
        color = colors[rng.integers(len(colors))]
        shape = rng.choice(shapes)
        alpha = int(100 + rng.random() * 155)
        size = int(15 + rng.random() * 100)
        x = rng.integers(size, max(size + 1, w - size))
        y = rng.integers(size, max(size + 1, h - size))
        
        if shape == 'circle':
            draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))
        elif shape == 'rect':
            draw.rectangle([x - size, y - size//2, x + size, y + size//2], fill=(*color, alpha))
        elif shape == 'triangle':
            points = [(x, y - size), (x - size, y + size), (x + size, y + size)]
            draw.polygon(points, fill=(*color, alpha))
        elif shape == 'line':
            draw.line([x - size, y, x + size, y + rng.integers(-size, size)],
                     fill=(*color, alpha), width=int(3 + rng.random() * 10))
        elif shape == 'blob':
            points = [(x + size * (0.5 + 0.5 * rng.random()) * math.cos(a),
                      y + size * (0.5 + 0.5 * rng.random()) * math.sin(a))
                     for a in np.linspace(0, 2 * math.pi, 8)]
            draw.polygon(points, fill=(*color, alpha))


def draw_proportion_scale(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Proportion and scale relationships."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    sizes = [100, 62, 38, 24, 15, 9]
    
    for i, size in enumerate(sizes):
        color = palette[i % len(palette)]
        alpha = int(120 + rng.random() * 80)
        
        for _ in range(int(1 + i * noisiness * 2)):
            x = rng.integers(size, max(size + 1, w - size))
            y = rng.integers(size, max(size + 1, h - size))
            draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))


def draw_contrast_value(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Contrast - strong light/dark differences."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # Black background
    img.paste((20, 20, 20), [0, 0, w, h])
    
    # White/light shapes
    num_shapes = int(5 + noisiness * 15)
    for _ in range(num_shapes):
        v = int(200 + rng.random() * 55)
        size = int(30 + rng.random() * 120)
        x = rng.integers(size, max(size + 1, w - size))
        y = rng.integers(size, max(size + 1, h - size))
        
        if rng.random() > 0.5:
            draw.ellipse([x - size, y - size, x + size, y + size], fill=(v, v, v))
        else:
            draw.rectangle([x - size, y - size, x + size, y + size], fill=(v, v, v))


# --- EDGE CONTROL ---

def draw_edge_soft(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Soft edges - sfumato-like blurred transitions."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(5 + noisiness * 12)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        cx = rng.integers(50, w - 50)
        cy = rng.integers(50, h - 50)
        size = int(40 + rng.random() * 100)
        
        for r in range(size, 0, -3):
            t = r / size
            alpha = int(150 * (1 - t))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    
    blurred = img.filter(ImageFilter.GaussianBlur(radius=3))
    img.paste(blurred)


def draw_edge_hard(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Hard edges - crisp, defined boundaries."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    palette = generate_palette(brightness, rng)
    
    num_shapes = int(6 + noisiness * 15)
    
    for _ in range(num_shapes):
        color = palette[rng.integers(len(palette))]
        size = int(30 + rng.random() * 120)
        x = rng.integers(size, max(size + 1, w - size))
        y = rng.integers(size, max(size + 1, h - size))
        
        shape = rng.choice(['rect', 'circle', 'tri'])
        if shape == 'rect':
            draw.rectangle([x - size, y - size, x + size, y + size], fill=color)
        elif shape == 'circle':
            draw.ellipse([x - size, y - size, x + size, y + size], fill=color)
        else:
            points = [(x, y - size), (x - size, y + size), (x + size, y + size)]
            draw.polygon(points, fill=color)


def draw_edge_lost(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Lost edges - edges that disappear into similar values."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    base_v = brightness
    colors = [hsv_to_rgb(rng.random(), 0.3, base_v + (rng.random() - 0.5) * 0.15) for _ in range(5)]
    
    num_shapes = int(8 + noisiness * 15)
    
    for _ in range(num_shapes):
        color = colors[rng.integers(len(colors))]
        alpha = int(80 + rng.random() * 80)
        size = int(40 + rng.random() * 120)
        x = rng.integers(size, max(size + 1, w - size))
        y = rng.integers(size, max(size + 1, h - size))
        
        draw.ellipse([x - size, y - size, x + size, y + size], fill=(*color, alpha))
    
    img.paste(img.filter(ImageFilter.GaussianBlur(radius=2)))


def draw_sfumato(img: Image.Image, brightness: float, noisiness: float, rng: np.random.Generator):
    """Sfumato - soft, smoky transitions (Leonardo da Vinci technique)."""
    draw = ImageDraw.Draw(img, 'RGBA')
    w, h = img.size
    
    # Rich Renaissance-style background - warm golden or cool blue-gray
    bg_style = rng.choice(['golden', 'earth', 'dusk'])
    if bg_style == 'golden':
        bg_top = (180, 160, 120)
        bg_bottom = (140, 120, 90)
    elif bg_style == 'earth':
        bg_top = (160, 140, 120)
        bg_bottom = (120, 100, 80)
    else:  # dusk
        bg_top = (140, 130, 150)
        bg_bottom = (100, 90, 110)
    
    # Gradient background
    for y in range(h):
        t = y / h
        r = int(bg_top[0] * (1 - t) + bg_bottom[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bottom[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bottom[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    # Soft overlapping forms - visible but with soft edges
    num_forms = int(5 + noisiness * 8)
    for _ in range(num_forms):
        cx = rng.integers(80, w - 80)
        cy = rng.integers(80, h - 80)
        size = int(50 + rng.random() * 100)
        
        # Skin-like or earth tones
        base_hue = rng.choice([0.05, 0.08, 0.1, 0.95])  # Warm flesh/earth tones
        
        # Build up form with many subtle layers (the sfumato technique)
        for r in range(size, 0, -3):
            t = r / size
            sat = 0.25 + 0.15 * (1 - t)
            val = 0.5 + 0.35 * (1 - t)  # Lighter toward center
            color = hsv_to_rgb(base_hue, sat, val)
            alpha = int(80 * (1 - t * t))  # More visible
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    
    # Multiple blur passes for true sfumato softness
    blurred = img.filter(ImageFilter.GaussianBlur(radius=3))
    blurred = blurred.filter(ImageFilter.GaussianBlur(radius=2))
    img.paste(blurred)


# =============================================================================
# STYLE REGISTRY
# =============================================================================

STYLES = {
    # Elements of Art - Line
    'line_straight': draw_line_straight,
    'line_stripes_h': draw_line_stripes_h,
    'line_stripes_v': draw_line_stripes_v,
    'line_grid': draw_line_grid,
    'line_mondrian': draw_line_mondrian,
    'line_diagonal': draw_line_diagonal,
    'line_rays': draw_line_rays,
    'line_checker': draw_line_checker,
    'line_blocks': draw_line_blocks,
    'line_contour': draw_line_contour,
    'line_gesture': draw_line_gesture,
    'line_implied': draw_line_implied,
    'line_quality': draw_line_quality,
    
    # Elements of Art - Shape
    'shape_geometric': draw_shape_geometric,
    'shape_organic': draw_shape_organic,
    'shape_triangles': draw_shape_triangles,
    'shape_circles': draw_shape_circles,
    'shape_rectangles': draw_shape_rectangles,
    'shape_polygons': draw_shape_polygons,
    'shape_stars': draw_shape_stars,
    'shape_diamonds': draw_shape_diamonds,
    
    # Elements of Art - Form
    'form_shaded': draw_form_shaded,
    'form_perspective': draw_form_perspective,
    'form_cubes': draw_form_cubes,
    'form_cylinders': draw_form_cylinders,
    
    # Elements of Art - Space
    'space_positive_negative': draw_space_positive_negative,
    'space_depth': draw_space_depth,
    
    # Elements of Art - Value
    'value_gradient': draw_value_gradient,
    'value_high_key': draw_value_high_key,
    'value_low_key': draw_value_low_key,
    'chiaroscuro': draw_chiaroscuro,
    
    # Elements of Art - Colour
    'colour_complementary': draw_colour_complementary,
    'colour_analogous': draw_colour_analogous,
    'colour_triadic': draw_colour_triadic,
    'colour_split_complementary': draw_colour_split_complementary,
    'colour_warm': draw_colour_warm,
    'colour_cool': draw_colour_cool,
    'colour_saturated': draw_colour_saturated,
    'colour_muted': draw_colour_muted,
    
    # Elements of Art - Texture
    'texture_stipple': draw_texture_stipple,
    'texture_crosshatch': draw_texture_crosshatch,
    'texture_grain': draw_texture_grain,
    'texture_weave': draw_texture_weave,
    'texture_noise': draw_texture_noise,
    'texture_wood': draw_texture_wood,
    'texture_marble': draw_texture_marble,
    'texture_concrete': draw_texture_concrete,
    'texture_fabric': draw_texture_fabric,
    
    # Elements of Art - Mark-making
    'marks_brush': draw_marks_brush,
    'marks_stipple': draw_marks_stipple,
    'marks_hatching': draw_marks_hatching,
    'marks_splatter': draw_marks_splatter,
    'marks_scribble': draw_marks_scribble,
    'marks_drip': draw_marks_drip,
    'marks_knife': draw_marks_knife,
    'marks_dots': draw_marks_dots,
    
    # Pattern
    'pattern_dots': draw_pattern_dots,
    'pattern_waves': draw_pattern_waves,
    'pattern_spirals': draw_pattern_spirals,
    'pattern_concentric': draw_pattern_concentric,
    'pattern_hexagonal': draw_pattern_hexagonal,
    'pattern_zigzag': draw_pattern_zigzag,
    'pattern_chevron': draw_pattern_chevron,
    
    # Principles of Design - Balance
    'balance_symmetrical': draw_balance_symmetrical,
    'balance_asymmetrical': draw_balance_asymmetrical,
    'balance_radial': draw_balance_radial,
    
    # Principles of Design - Others
    'emphasis_focal': draw_emphasis_focal,
    'hierarchy': draw_hierarchy,
    'movement_flow': draw_movement_flow,
    'rhythm_pattern': draw_rhythm_pattern,
    'unity_harmony': draw_unity_harmony,
    'variety_contrast': draw_variety_contrast,
    'proportion_scale': draw_proportion_scale,
    'contrast_value': draw_contrast_value,
    
    # Edge control
    'edge_soft': draw_edge_soft,
    'edge_hard': draw_edge_hard,
    'edge_lost': draw_edge_lost,
    'sfumato': draw_sfumato,
}

# =============================================================================
# PRESETS
# =============================================================================

PRESETS = {
    # Basic
    "white": {"brightness": 0.95, "noisiness": 0.0, "style": "value_gradient"},
    "black": {"brightness": 0.1, "noisiness": 0.0, "style": "value_gradient"},
    "gray": {"brightness": 0.5, "noisiness": 0.1, "style": "value_gradient"},
    
    # Line - straight
    "straight_lines": {"brightness": 0.5, "noisiness": 0.5, "style": "line_straight"},
    "stripes_h": {"brightness": 0.5, "noisiness": 0.5, "style": "line_stripes_h"},
    "stripes_v": {"brightness": 0.5, "noisiness": 0.5, "style": "line_stripes_v"},
    "grid": {"brightness": 0.5, "noisiness": 0.5, "style": "line_grid"},
    "mondrian": {"brightness": 0.7, "noisiness": 0.5, "style": "line_mondrian"},
    "diagonal": {"brightness": 0.5, "noisiness": 0.5, "style": "line_diagonal"},
    "rays": {"brightness": 0.5, "noisiness": 0.5, "style": "line_rays"},
    "checker": {"brightness": 0.5, "noisiness": 0.5, "style": "line_checker"},
    "blocks": {"brightness": 0.5, "noisiness": 0.5, "style": "line_blocks"},
    # Line - expressive
    "contour": {"brightness": 0.6, "noisiness": 0.5, "style": "line_contour"},
    "gesture": {"brightness": 0.5, "noisiness": 0.7, "style": "line_gesture"},
    "implied_line": {"brightness": 0.55, "noisiness": 0.4, "style": "line_implied"},
    "line_weight": {"brightness": 0.5, "noisiness": 0.6, "style": "line_quality"},
    
    # Shape
    "geometric": {"brightness": 0.5, "noisiness": 0.5, "style": "shape_geometric"},
    "organic": {"brightness": 0.6, "noisiness": 0.4, "style": "shape_organic"},
    "triangles": {"brightness": 0.5, "noisiness": 0.6, "style": "shape_triangles"},
    "circles": {"brightness": 0.55, "noisiness": 0.5, "style": "shape_circles"},
    "rectangles": {"brightness": 0.5, "noisiness": 0.5, "style": "shape_rectangles"},
    "polygons": {"brightness": 0.55, "noisiness": 0.5, "style": "shape_polygons"},
    "stars": {"brightness": 0.55, "noisiness": 0.5, "style": "shape_stars"},
    "diamonds": {"brightness": 0.5, "noisiness": 0.5, "style": "shape_diamonds"},
    
    # Form
    "shaded_forms": {"brightness": 0.6, "noisiness": 0.3, "style": "form_shaded"},
    "perspective": {"brightness": 0.55, "noisiness": 0.4, "style": "form_perspective"},
    "cubes": {"brightness": 0.55, "noisiness": 0.5, "style": "form_cubes"},
    "cylinders": {"brightness": 0.55, "noisiness": 0.4, "style": "form_cylinders"},
    
    # Space
    "positive_negative": {"brightness": 0.5, "noisiness": 0.4, "style": "space_positive_negative"},
    "depth": {"brightness": 0.55, "noisiness": 0.5, "style": "space_depth"},
    
    # Value / Tonality
    "high_key": {"brightness": 0.85, "noisiness": 0.3, "style": "value_high_key"},
    "low_key": {"brightness": 0.2, "noisiness": 0.4, "style": "value_low_key"},
    "chiaroscuro": {"brightness": 0.4, "noisiness": 0.5, "style": "chiaroscuro"},
    "value_contrast": {"brightness": 0.5, "noisiness": 0.5, "style": "contrast_value"},
    
    # Colour harmony
    "complementary": {"brightness": 0.55, "noisiness": 0.5, "style": "colour_complementary"},
    "analogous": {"brightness": 0.55, "noisiness": 0.5, "style": "colour_analogous"},
    "triadic": {"brightness": 0.55, "noisiness": 0.5, "style": "colour_triadic"},
    "split_complementary": {"brightness": 0.55, "noisiness": 0.5, "style": "colour_split_complementary"},
    
    # Colour temperature
    "warm": {"brightness": 0.6, "noisiness": 0.5, "style": "colour_warm"},
    "cool": {"brightness": 0.5, "noisiness": 0.5, "style": "colour_cool"},
    
    # Saturation
    "saturated": {"brightness": 0.6, "noisiness": 0.5, "style": "colour_saturated"},
    "muted": {"brightness": 0.5, "noisiness": 0.4, "style": "colour_muted"},
    
    # Texture
    "stipple": {"brightness": 0.5, "noisiness": 0.6, "style": "texture_stipple"},
    "crosshatch": {"brightness": 0.5, "noisiness": 0.5, "style": "texture_crosshatch"},
    "grain": {"brightness": 0.5, "noisiness": 0.6, "style": "texture_grain"},
    "weave": {"brightness": 0.5, "noisiness": 0.5, "style": "texture_weave"},
    "noise": {"brightness": 0.5, "noisiness": 0.8, "style": "texture_noise"},
    "wood": {"brightness": 0.5, "noisiness": 0.5, "style": "texture_wood"},
    "marble": {"brightness": 0.7, "noisiness": 0.4, "style": "texture_marble"},
    "concrete": {"brightness": 0.5, "noisiness": 0.5, "style": "texture_concrete"},
    "fabric": {"brightness": 0.55, "noisiness": 0.4, "style": "texture_fabric"},
    
    # Mark-making
    "brush_strokes": {"brightness": 0.55, "noisiness": 0.6, "style": "marks_brush"},
    "stippled": {"brightness": 0.5, "noisiness": 0.6, "style": "marks_stipple"},
    "hatched": {"brightness": 0.5, "noisiness": 0.5, "style": "marks_hatching"},
    "splatter": {"brightness": 0.5, "noisiness": 0.7, "style": "marks_splatter"},
    "scribble": {"brightness": 0.5, "noisiness": 0.7, "style": "marks_scribble"},
    "drip": {"brightness": 0.5, "noisiness": 0.6, "style": "marks_drip"},
    "knife": {"brightness": 0.55, "noisiness": 0.5, "style": "marks_knife"},
    "dot_marks": {"brightness": 0.5, "noisiness": 0.5, "style": "marks_dots"},
    
    # Pattern
    "dots": {"brightness": 0.5, "noisiness": 0.5, "style": "pattern_dots"},
    "waves": {"brightness": 0.5, "noisiness": 0.5, "style": "pattern_waves"},
    "spirals": {"brightness": 0.5, "noisiness": 0.5, "style": "pattern_spirals"},
    "concentric": {"brightness": 0.5, "noisiness": 0.5, "style": "pattern_concentric"},
    "hexagonal": {"brightness": 0.5, "noisiness": 0.5, "style": "pattern_hexagonal"},
    "zigzag": {"brightness": 0.5, "noisiness": 0.6, "style": "pattern_zigzag"},
    "chevron": {"brightness": 0.5, "noisiness": 0.5, "style": "pattern_chevron"},
    
    # Balance
    "symmetrical": {"brightness": 0.55, "noisiness": 0.4, "style": "balance_symmetrical"},
    "asymmetrical": {"brightness": 0.55, "noisiness": 0.5, "style": "balance_asymmetrical"},
    "radial": {"brightness": 0.5, "noisiness": 0.5, "style": "balance_radial"},
    
    # Other principles
    "focal_point": {"brightness": 0.5, "noisiness": 0.5, "style": "emphasis_focal"},
    "hierarchy": {"brightness": 0.55, "noisiness": 0.4, "style": "hierarchy"},
    "flowing": {"brightness": 0.55, "noisiness": 0.6, "style": "movement_flow"},
    "rhythmic": {"brightness": 0.5, "noisiness": 0.5, "style": "rhythm_pattern"},
    "harmonious": {"brightness": 0.55, "noisiness": 0.4, "style": "unity_harmony"},
    "varied": {"brightness": 0.55, "noisiness": 0.6, "style": "variety_contrast"},
    "proportioned": {"brightness": 0.5, "noisiness": 0.5, "style": "proportion_scale"},
    
    # Edge control
    "soft_edges": {"brightness": 0.55, "noisiness": 0.4, "style": "edge_soft"},
    "hard_edges": {"brightness": 0.5, "noisiness": 0.5, "style": "edge_hard"},
    "lost_edges": {"brightness": 0.5, "noisiness": 0.4, "style": "edge_lost"},
    "sfumato": {"brightness": 0.5, "noisiness": 0.3, "style": "sfumato"},
}

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def generate_test_image(
    brightness: float = 0.5,
    noisiness: float = 0.5,
    size: Tuple[int, int] = (512, 512),
    style: str = 'auto',
    seed: int = 42,
) -> Image.Image:
    """Generate a test image with target brightness and noisiness."""
    rng = np.random.default_rng(seed)
    w, h = size
    
    if style == 'auto':
        style = rng.choice(list(STYLES.keys()))
    
    # Set appropriate background based on style
    img = Image.new('RGB', size, (255, 255, 255))
    
    # Styles that handle their own backgrounds completely
    self_bg_styles = {
        'chiaroscuro', 'sfumato', 'value_gradient', 'value_high_key', 'value_low_key',
        'contrast_value', 'space_positive_negative', 'line_checker', 'line_mondrian',
        'texture_grain', 'texture_noise', 'texture_concrete', 'texture_wood', 
        'texture_marble', 'colour_warm', 'colour_cool', 'colour_saturated', 'colour_muted',
    }
    
    if style not in self_bg_styles:
        # Set a contrasting/appropriate background
        if 'warm' in style:
            fill_background(img, brightness, rng, 'warm')
        elif 'cool' in style:
            fill_background(img, brightness, rng, 'cool')
        elif 'high_key' in style:
            fill_background(img, brightness, rng, 'light')
        elif 'low_key' in style:
            fill_background(img, brightness, rng, 'dark')
        elif style.startswith('line_'):
            # Lines need clean backgrounds - paper or white
            bg_choice = rng.choice(['paper', 'white', 'light'])
            fill_background(img, brightness, rng, bg_choice)
        elif style.startswith('pattern_'):
            # Patterns - variety
            bg_choice = rng.choice(['paper', 'tinted', 'contrast'])
            fill_background(img, brightness, rng, bg_choice)
        elif style.startswith('shape_'):
            # Shapes - contrasting colored backgrounds
            fill_background(img, brightness, rng, 'contrast')
        elif style.startswith('form_'):
            # 3D forms - neutral to show shading
            fill_background(img, brightness, rng, 'paper')
        elif style.startswith('marks_'):
            # Mark-making on paper
            fill_background(img, brightness, rng, 'paper')
        elif style.startswith('texture_'):
            # Textures handle themselves mostly
            fill_background(img, brightness, rng, 'neutral')
        elif style.startswith('balance_') or style.startswith('emphasis_'):
            fill_background(img, brightness, rng, 'contrast')
        elif style.startswith('colour_'):
            fill_background(img, brightness, rng, 'tinted')
        else:
            # Default: varied
            bg_choice = rng.choice(['tinted', 'paper', 'contrast'])
            fill_background(img, brightness, rng, bg_choice)
    
    if style in STYLES:
        result = STYLES[style](img, brightness, noisiness, rng)
        if result is not None:
            img = result
    
    return img


def generate_sweep(
    output_dir: Path,
    steps: int = 5,
    size: Tuple[int, int] = (256, 256),
    seed: int = 42,
):
    """Generate a grid of test images."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    styles = list(STYLES.keys())
    
    for bi, b in enumerate(np.linspace(0.15, 0.85, steps)):
        for ni, n in enumerate(np.linspace(0.1, 0.9, steps)):
            style = styles[(bi * steps + ni) % len(styles)]
            img = generate_test_image(
                brightness=b,
                noisiness=n,
                size=size,
                style=style,
                seed=seed + bi * steps + ni,
            )
            filename = f"b{b:.2f}_n{n:.2f}_{style}.png"
            img.save(output_dir / filename)
            print(f"  {filename}")
    
    print(f"\nGenerated {steps * steps} images in {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test images covering art elements and design principles"
    )
    parser.add_argument("--brightness", "-b", type=float, default=0.5,
                        help="Target brightness 0-1 (default: 0.5)")
    parser.add_argument("--noisiness", "-n", type=float, default=0.5,
                        help="Target noisiness 0-1 (default: 0.5)")
    parser.add_argument("--style", type=str, default="auto",
                        choices=["auto"] + list(STYLES.keys()),
                        help="Visual style (default: auto)")
    parser.add_argument("--size", "-s", type=int, default=512,
                        help="Image size in pixels (default: 512)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output path (default: imaginarium/test_images/<n>.png)")
    parser.add_argument("--preset", "-p", type=str, choices=list(PRESETS.keys()),
                        help="Use a preset")
    parser.add_argument("--sweep", action="store_true",
                        help="Generate grid of images")
    parser.add_argument("--sweep-steps", type=int, default=5,
                        help="Steps per axis for sweep (default: 5)")
    parser.add_argument("--list-presets", action="store_true",
                        help="List available presets")
    parser.add_argument("--list-styles", action="store_true",
                        help="List available styles")
    
    args = parser.parse_args()
    
    if args.list_presets:
        print("Available presets:")
        print()
        categories = {}
        for name, params in PRESETS.items():
            style = params['style']
            cat = style.split('_')[0] if '_' in style else style
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((name, params))
        
        for cat in sorted(categories.keys()):
            print(f"[{cat}]")
            for name, params in categories[cat]:
                print(f"  {name:20s} b={params['brightness']:.2f} n={params['noisiness']:.2f}")
            print()
        return 0
    
    if args.list_styles:
        print("Available styles:")
        print()
        categories = {}
        for name in STYLES.keys():
            cat = name.split('_')[0]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(name)
        
        for cat in sorted(categories.keys()):
            print(f"[{cat}]")
            for name in categories[cat]:
                print(f"  {name}")
            print()
        return 0
    
    if args.sweep:
        output_dir = Path(args.output) if args.output else Path("imaginarium/test_images/sweep")
        print(f"Generating {args.sweep_steps}x{args.sweep_steps} sweep...")
        generate_sweep(
            output_dir=output_dir,
            steps=args.sweep_steps,
            size=(args.size, args.size),
            seed=args.seed,
        )
        return 0
    
    if args.preset:
        params = PRESETS[args.preset]
        brightness = params["brightness"]
        noisiness = params["noisiness"]
        style = params.get("style", "auto")
        print(f"Using preset '{args.preset}': b={brightness:.2f} n={noisiness:.2f} style={style}")
    else:
        brightness = args.brightness
        noisiness = args.noisiness
        style = args.style
    
    if args.output:
        output_path = Path(args.output)
    else:
        test_images_dir = Path("imaginarium/test_images")
        test_images_dir.mkdir(parents=True, exist_ok=True)
        
        if args.preset:
            filename = f"{args.preset}.png"
        else:
            filename = f"b{brightness:.2f}_n{noisiness:.2f}_{style}_s{args.seed}.png"
        output_path = test_images_dir / filename
    
    img = generate_test_image(
        brightness=brightness,
        noisiness=noisiness,
        size=(args.size, args.size),
        style=style,
        seed=args.seed,
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    
    print(f"Generated: {output_path}")
    print(f"  brightness: {brightness:.2f}")
    print(f"  noisiness:  {noisiness:.2f}")
    print(f"  style:      {style}")
    print(f"  size:       {args.size}x{args.size}")
    
    print()
    print("Verifying with extractor...")
    try:
        from imaginarium.extract import extract_from_image
        result = extract_from_image(output_path)
        print(f"  Extracted brightness: {result.spec.brightness:.3f} (target: {brightness:.2f})")
        print(f"  Extracted noisiness:  {result.spec.noisiness:.3f} (target: {noisiness:.2f})")
    except ImportError:
        print("  (extractor not available)")
    
    return 0


if __name__ == "__main__":
    exit(main())
