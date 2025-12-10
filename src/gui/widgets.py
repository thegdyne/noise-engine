"""
Reusable UI Widgets
Atomic components with no business logic - just behavior
"""

from PyQt5.QtWidgets import QSlider, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

from .theme import slider_style


class MiniSlider(QSlider):
    """Compact vertical slider."""
    
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setMinimum(0)
        self.setMaximum(1000)
        self.setValue(500)
        self.setFixedWidth(25)
        self.setMinimumHeight(50)
        self.setStyleSheet(slider_style())


class CycleButton(QPushButton):
    """
    Button that cycles through a list of values.
    - Click = cycle forward
    - Click + drag up/down = change value
    
    Signals:
        value_changed(str): Emitted when value changes
        index_changed(int): Emitted when index changes
    """
    
    value_changed = pyqtSignal(str)
    index_changed = pyqtSignal(int)
    
    def __init__(self, values, initial_index=0, parent=None):
        super().__init__(parent)
        self.values = values
        self.index = initial_index
        self.wrap = False  # Set True to wrap at ends
        self._update_display()
        
        # Drag tracking
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_index = 0
        self.drag_threshold = 15  # Pixels per step
        self.moved_during_press = False
        
    def _update_display(self):
        """Update button text."""
        self.setText(self.values[self.index])
        
    def _emit_signals(self):
        """Emit both signals."""
        self.value_changed.emit(self.values[self.index])
        self.index_changed.emit(self.index)
        
    def set_index(self, index):
        """Set value by index."""
        if 0 <= index < len(self.values):
            self.index = index
            self._update_display()
            
    def set_value(self, value):
        """Set value by string."""
        if value in self.values:
            self.index = self.values.index(value)
            self._update_display()
            
    def get_value(self):
        """Get current value."""
        return self.values[self.index]
        
    def get_index(self):
        """Get current index."""
        return self.index
        
    def cycle_forward(self):
        """Move to next value (higher index)."""
        if self.wrap:
            self.index = (self.index + 1) % len(self.values)
        else:
            self.index = min(self.index + 1, len(self.values) - 1)
        self._update_display()
        self._emit_signals()
        
    def cycle_backward(self):
        """Move to previous value (lower index)."""
        if self.wrap:
            self.index = (self.index - 1) % len(self.values)
        else:
            self.index = max(self.index - 1, 0)
        self._update_display()
        self._emit_signals()
        
    def mousePressEvent(self, event):
        """Start drag tracking."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_y = event.pos().y()
            self.drag_start_index = self.index
            self.moved_during_press = False
        
    def mouseMoveEvent(self, event):
        """Handle drag - up = faster (lower index), down = slower (higher index)."""
        if self.dragging:
            delta_y = self.drag_start_y - event.pos().y()  # Positive = moved up
            steps = delta_y // self.drag_threshold
            
            new_index = self.drag_start_index - steps  # Up = lower index = faster
            
            # Clamp or wrap
            if self.wrap:
                new_index = new_index % len(self.values)
            else:
                new_index = max(0, min(len(self.values) - 1, new_index))
            
            if new_index != self.index:
                self.moved_during_press = True
                self.index = new_index
                self._update_display()
                self._emit_signals()
                
    def mouseReleaseEvent(self, event):
        """End drag. If no movement, cycle forward."""
        if event.button() == Qt.LeftButton:
            if not self.moved_during_press:
                self.cycle_forward()
            self.dragging = False
            self.moved_during_press = False
