"""
Mod Scope Widget
Real-time waveform display for mod source outputs

Shows 4 traces (A/B/C/D or X/Y/Z/R) with circular buffer history.
Receives values from SC via OSC at ~30fps.
"""

from collections import deque
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath

from .theme import COLORS


def _hex_to_qcolor(hex_str):
    """Convert hex color string to QColor."""
    hex_str = hex_str.lstrip('#')
    return QColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


class ModScope(QWidget):
    """
    Oscilloscope-style display for mod source outputs.
    
    Features:
    - 4 traces with history buffer
    - Bipolar (-1 to +1) or unipolar (0 to 1) display
    - Grid with center line
    - Configurable history length
    """
    
    def __init__(self, parent=None, history_length=128):
        super().__init__(parent)
        self.history_length = history_length
        
        # Circular buffers for each output (0, 1, 2, 3)
        self.buffers = [
            deque([0.0] * history_length, maxlen=history_length),
            deque([0.0] * history_length, maxlen=history_length),
            deque([0.0] * history_length, maxlen=history_length),
            deque([0.0] * history_length, maxlen=history_length),
        ]
        
        # Display mode: 'bipolar' (-1 to +1) or 'unipolar' (0 to 1)
        self.display_mode = 'bipolar'
        
        # Which traces are visible
        self.trace_visible = [True, True, True, True]
        
        # Trace colors from skin (with fallback for 4th)
        self.trace_colors = [
            _hex_to_qcolor(COLORS.get('scope_trace_a', '#00ff00')),
            _hex_to_qcolor(COLORS.get('scope_trace_b', '#ff6600')),
            _hex_to_qcolor(COLORS.get('scope_trace_c', '#00ffff')),
            _hex_to_qcolor(COLORS.get('scope_trace_d', '#ff00ff')),
        ]
        self.grid_color = _hex_to_qcolor(COLORS['scope_grid'])
        self.center_color = _hex_to_qcolor(COLORS['scope_center'])
        
        # Styling
        self.setMinimumHeight(50)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
    def push_value(self, output_idx, value):
        """
        Add a new value to the specified output buffer.
        
        Args:
            output_idx: 0, 1, 2, or 3 (A/X, B/Y, C/Z, D/R)
            value: float, typically -1 to +1 or 0 to 1
        """
        if 0 <= output_idx < 4:
            self.buffers[output_idx].append(value)
            
    def push_values(self, values):
        """
        Add values for all 4 outputs at once.
        
        Args:
            values: list of 4 floats [A, B, C, D]
        """
        for i, val in enumerate(values[:4]):
            self.buffers[i].append(val)
            
    def clear(self):
        """Clear all buffers to zero."""
        for buf in self.buffers:
            buf.clear()
            buf.extend([0.0] * self.history_length)
            
    def set_display_mode(self, mode):
        """Set display mode: 'bipolar' or 'unipolar'."""
        self.display_mode = mode
        self.update()
        
    def set_trace_visible(self, output_idx, visible):
        """Show or hide a specific trace."""
        if 0 <= output_idx < 4:
            self.trace_visible[output_idx] = visible
            self.update()
            
    def paintEvent(self, event):
        """Draw the scope display."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, QColor(COLORS['background']))
        
        # Draw grid
        self._draw_grid(painter, w, h)
        
        # Draw traces
        for i in range(4):
            if self.trace_visible[i]:
                self._draw_trace(painter, w, h, i)
                
    def _draw_grid(self, painter, w, h):
        """Draw background grid."""
        pen = QPen(self.grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Vertical grid lines (time divisions)
        num_v_lines = 8
        for i in range(1, num_v_lines):
            x = int(w * i / num_v_lines)
            painter.drawLine(x, 0, x, h)
            
        # Horizontal grid lines
        if self.display_mode == 'bipolar':
            # Center line (0) - brighter
            center_y = h // 2
            pen.setColor(self.center_color)
            painter.setPen(pen)
            painter.drawLine(0, center_y, w, center_y)
            
            # Quarter lines (+0.5, -0.5)
            pen.setColor(self.grid_color)
            painter.setPen(pen)
            quarter_h = h // 4
            painter.drawLine(0, quarter_h, w, quarter_h)
            painter.drawLine(0, h - quarter_h, w, h - quarter_h)
        else:
            # Unipolar: lines at 0.25, 0.5, 0.75
            pen.setColor(self.grid_color)
            painter.setPen(pen)
            for frac in [0.25, 0.5, 0.75]:
                y = int(h * (1 - frac))
                if frac == 0.5:
                    pen.setColor(self.center_color)
                else:
                    pen.setColor(self.grid_color)
                painter.setPen(pen)
                painter.drawLine(0, y, w, y)
                
    def _draw_trace(self, painter, w, h, output_idx):
        """Draw a single trace."""
        buf = self.buffers[output_idx]
        if len(buf) < 2:
            return
            
        pen = QPen(self.trace_colors[output_idx])
        pen.setWidth(2)
        painter.setPen(pen)
        
        path = QPainterPath()
        
        for i, val in enumerate(buf):
            x = int(w * i / (len(buf) - 1))
            
            # Map value to y coordinate
            if self.display_mode == 'bipolar':
                # -1 → bottom, +1 → top
                y = int(h * (1 - (val + 1) / 2))
            else:
                # 0 → bottom, 1 → top
                y = int(h * (1 - val))
                
            # Clamp y to widget bounds
            y = max(0, min(h - 1, y))
            
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
                
        painter.drawPath(path)


class ModScopeController:
    """
    Manages scope updates from OSC messages.
    
    Connects to OSC bridge and routes bus values to the correct scope.
    """
    
    def __init__(self):
        self.scopes = {}  # slot_id -> ModScope widget
        self.enabled_slots = set()
        
    def register_scope(self, slot_id, scope_widget):
        """Register a scope widget for a slot."""
        self.scopes[slot_id] = scope_widget
        
    def unregister_scope(self, slot_id):
        """Remove a scope widget."""
        self.scopes.pop(slot_id, None)
        
    def enable_slot(self, slot_id, enabled=True):
        """Enable or disable scope updates for a slot."""
        if enabled:
            self.enabled_slots.add(slot_id)
        else:
            self.enabled_slots.discard(slot_id)
            
    def on_bus_value(self, bus_idx, value):
        """
        Handle incoming bus value from OSC.
        
        Args:
            bus_idx: 0-15 (4 slots × 4 outputs)
            value: float
        """
        # Calculate slot and output from bus index
        slot_id = (bus_idx // 4) + 1  # 1-4
        output_idx = bus_idx % 4       # 0-3
        
        if slot_id in self.enabled_slots and slot_id in self.scopes:
            self.scopes[slot_id].push_value(output_idx, value)
            
    def update_displays(self):
        """Trigger repaint on all enabled scopes."""
        for slot_id in self.enabled_slots:
            if slot_id in self.scopes:
                self.scopes[slot_id].update()
