"""
SynthesisIcon - Animated waveform display for generator slots.

Shows animated visual based on synthesis method category.
"""

import math
import random
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath

from .theme import COLORS

# Colors per synthesis category
SYNTHESIS_COLORS = {
    'fm': '#ff8844',
    'physical': '#44dddd',
    'subtractive': '#44ff88',
    'spectral': '#aa66ff',
    'texture': '#cccccc',
    'unknown': '#666666',
    'empty': '#333333',
}


class SynthesisIcon(QWidget):
    """Animated synthesis method visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.category = 'empty'
        self.phase = 0.0
        self.particles = []  # For texture animation
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
        """)
        
        # Animation timer - 30fps
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.setInterval(33)
    
    def set_category(self, category: str):
        """Set the synthesis category to display."""
        self.category = category if category else 'empty'
        print(f"DEBUG SynthesisIcon.set_category: {category} -> {self.category}")
        self.phase = 0.0
        
        # Initialize particles for texture
        if self.category == 'texture':
            self._init_particles()
        
        # Start/stop animation
        if self.category != 'empty':
            self.timer.start()
        else:
            self.timer.stop()
        
        self.update()
    
    def _init_particles(self):
        """Initialize particle positions for texture animation."""
        random.seed(42)  # Consistent initial state
        self.particles = []
        for _ in range(30):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'vx': (random.random() - 0.5) * 0.02,
                'vy': (random.random() - 0.5) * 0.02,
                'size': random.randint(1, 3),
            })
    
    def _tick(self):
        """Animation tick - update phase and repaint."""
        self.phase += 0.05
        if self.phase > math.pi * 2:
            self.phase -= math.pi * 2
        
        # Update particles for texture
        if self.category == 'texture':
            for p in self.particles:
                p['x'] += p['vx']
                p['y'] += p['vy']
                # Wrap around
                if p['x'] < 0: p['x'] = 1.0
                if p['x'] > 1: p['x'] = 0.0
                if p['y'] < 0: p['y'] = 1.0
                if p['y'] > 1: p['y'] = 0.0
        
        self.update()
    
    def paintEvent(self, event):
        """Draw the animated synthesis visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        mid_y = h // 2
        margin = 4
        draw_w = w - margin * 2
        draw_h = h - margin * 2
        amplitude = draw_h // 2 - 2
        
        color = QColor(SYNTHESIS_COLORS.get(self.category, SYNTHESIS_COLORS['unknown']))
        pen = QPen(color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        if self.category == 'empty':
            # Flat dim line
            painter.drawLine(margin, mid_y, w - margin, mid_y)
        
        elif self.category == 'fm':
            # FM: Phasing interference pattern
            path = QPainterPath()
            for i in range(draw_w):
                t = i / draw_w
                carrier = math.sin(t * 4 * math.pi + self.phase)
                modulator = math.sin(t * 12 * math.pi + self.phase * 2.5) * 0.4
                y = mid_y - int((carrier + modulator) * amplitude * 0.6)
                if i == 0:
                    path.moveTo(margin + i, y)
                else:
                    path.lineTo(margin + i, y)
            painter.drawPath(path)
        
        elif self.category == 'physical':
            # Physical: Plucked string - decay and restart
            path = QPainterPath()
            cycle = (self.phase % (math.pi * 2)) / (math.pi * 2)
            decay = math.exp(-cycle * 4)
            for i in range(draw_w):
                t = i / draw_w
                # Standing wave pattern
                y = mid_y - int(math.sin(t * 3 * math.pi) * math.sin(self.phase * 3) * amplitude * decay)
                if i == 0:
                    path.moveTo(margin + i, y)
                else:
                    path.lineTo(margin + i, y)
            painter.drawPath(path)
        
        elif self.category == 'subtractive':
            # Subtractive: Scrolling sawtooth
            path = QPainterPath()
            teeth = 4
            tooth_w = draw_w / teeth
            offset = (self.phase / (math.pi * 2)) * tooth_w
            for i in range(draw_w):
                pos = (i + offset) % tooth_w
                progress = pos / tooth_w
                y = mid_y + int((0.5 - progress) * amplitude * 1.5)
                if i == 0:
                    path.moveTo(margin + i, y)
                else:
                    path.lineTo(margin + i, y)
            painter.drawPath(path)
        
        elif self.category == 'spectral':
            # Spectral: Pulsing harmonic bars
            num_bars = 10
            bar_spacing = draw_w / num_bars
            bar_width = max(2, int(bar_spacing * 0.6))
            for i in range(num_bars):
                x = margin + int(i * bar_spacing)
                # Harmonic amplitude with phase offset per bar
                base_height = amplitude * (1.0 / (i * 0.5 + 1))
                pulse = 0.7 + 0.3 * math.sin(self.phase + i * 0.5)
                height = int(base_height * pulse)
                painter.fillRect(x, mid_y - height, bar_width, height * 2, color)
        
        elif self.category == 'texture':
            # Texture: Drifting particles
            for p in self.particles:
                x = margin + int(p['x'] * draw_w)
                y = margin + int(p['y'] * draw_h)
                size = p['size']
                painter.setBrush(color)
                painter.drawEllipse(x, y, size, size)
        
        else:
            # Unknown: Pulsing line
            pulse = 0.5 + 0.5 * math.sin(self.phase)
            pen.setWidth(int(1 + pulse * 2))
            painter.setPen(pen)
            painter.drawLine(margin, mid_y, w - margin, mid_y)
    
    def showEvent(self, event):
        """Start animation when shown."""
        if self.category != 'empty':
            self.timer.start()
        super().showEvent(event)
    
    def hideEvent(self, event):
        """Stop animation when hidden."""
        self.timer.stop()
        super().hideEvent(event)
