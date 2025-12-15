"""
Reusable UI Widgets
Atomic components with no business logic - just behavior
"""

from PyQt5.QtWidgets import QSlider, QPushButton, QLabel, QApplication, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QFont

from .theme import slider_style, DRAG_SENSITIVITY, COLORS, MONO_FONT, FONT_SIZES


class ValuePopup(QLabel):
    """
    Floating popup that displays a value near a slider handle.
    Shows during drag, hides on release.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['background_highlight']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 3px;
                padding: 2px 5px;
            }}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.hide()
        self.setWindowFlags(Qt.ToolTip)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
    def show_value(self, text, global_pos):
        """Show popup with text at position."""
        self.setText(text)
        self.adjustSize()
        # Position to the right of the handle
        self.move(global_pos.x() + 15, global_pos.y() - self.height() // 2)
        self.show()
        self.raise_()
        
    def hide_value(self):
        """Hide the popup."""
        self.hide()


class DragSlider(QSlider):
    """
    Vertical slider with click+drag anywhere behavior.
    Click and drag up = increase, drag down = decrease.
    Hold Shift for fine control.
    
    Supports optional ValuePopup for displaying mapped values during drag.
    
    Base class - use MiniSlider for generator params, or customize size.
    """
    
    # Signal emits normalized 0-1 value
    normalizedValueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setMinimum(0)
        self.setMaximum(1000)
        self.setValue(500)
        self.setStyleSheet(slider_style())
        
        # Drag tracking
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_value = 0
        
        # Value popup (optional)
        self._popup = None
        self._param_config = None
        self._format_func = None
        
        # Double-click reset (optional)
        self._double_click_value = None
        
    def set_param_config(self, param_config, format_func=None):
        """
        Set parameter config for value mapping and popup display.
        param_config: dict with min, max, curve, unit, invert, default
        format_func: function(value, param) -> str for display
        """
        self._param_config = param_config
        self._format_func = format_func
        if param_config is not None:
            if self._popup is None:
                self._popup = ValuePopup()
            # Set slider to default value
            default = param_config.get('default', 0.5)
            self.setValue(int(default * 1000))
            
    def get_mapped_value(self):
        """Get the real mapped value based on param config."""
        if self._param_config is None:
            return self.value() / 1000.0
        
        from src.config import map_value
        normalized = self.value() / 1000.0
        return map_value(normalized, self._param_config)
        
    def _update_popup(self):
        """Update popup position and value during drag."""
        if self._popup is None or self._param_config is None:
            return
            
        mapped_value = self.get_mapped_value()
        
        if self._format_func:
            text = self._format_func(mapped_value, self._param_config)
        else:
            text = f"{mapped_value:.2f}"
        
        # Get handle position in global coords
        handle_pos = self._get_handle_global_pos()
        self._popup.show_value(text, handle_pos)
        
    def _get_handle_global_pos(self):
        """Calculate global position of slider handle."""
        # Slider geometry
        groove_margin = 5
        available_height = self.height() - 2 * groove_margin
        
        # Value position (inverted because 0 is at bottom for vertical)
        value_ratio = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        handle_y = groove_margin + (1.0 - value_ratio) * available_height
        
        local_pos = QPoint(self.width(), int(handle_y))
        return self.mapToGlobal(local_pos)
    
    def show_drag_value(self, text):
        """Display a value in popup during drag. Called by handler.
        
        This allows any fader to show a popup without needing param_config.
        The handler calculates the display value and passes it here.
        """
        if not self.dragging:
            return
        # Create popup lazily if needed
        if self._popup is None:
            self._popup = ValuePopup()
        handle_pos = self._get_handle_global_pos()
        self._popup.show_value(text, handle_pos)
        
    def mousePressEvent(self, event):
        """Start drag from current value."""
        if not self.isEnabled():
            return
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_y = event.globalPos().y()
            self.drag_start_value = self.value()
            self._update_popup()
            
    def mouseMoveEvent(self, event):
        """Drag up = increase, drag down = decrease. Shift = fine control."""
        if not self.isEnabled():
            return
        if self.dragging:
            modifiers = QApplication.keyboardModifiers()
            
            # Height-ratio sensitivity: drag distance relative to fader height
            # Normal: 1:1 ratio (drag full height = full range)
            # Fine: 3:1 ratio (drag 3x height = full range)
            fader_height = self.height()
            if modifiers & Qt.ShiftModifier:
                travel = fader_height * 3.0  # Fine control
            else:
                travel = fader_height * 1.0  # Normal 1:1 tracking
            
            delta_y = self.drag_start_y - event.globalPos().y()
            value_range = self.maximum() - self.minimum()
            delta_value = int((delta_y / travel) * value_range)
            
            new_value = self.drag_start_value + delta_value
            new_value = max(self.minimum(), min(self.maximum(), new_value))
            
            if new_value != self.value():
                self.setValue(new_value)
                self.normalizedValueChanged.emit(new_value / 1000.0)
                self._update_popup()
                
    def mouseReleaseEvent(self, event):
        """End drag."""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            if self._popup:
                self._popup.hide_value()
    
    def setDoubleClickValue(self, value):
        """Enable double-click to reset slider to specified value."""
        self._double_click_value = value
    
    def mouseDoubleClickEvent(self, event):
        """Reset to configured value on double-click."""
        if self._double_click_value is not None:
            self.setValue(self._double_click_value)
            # Emit signal for value change
            if self.maximum() == 1000:
                self.normalizedValueChanged.emit(self._double_click_value / 1000.0)
            else:
                self.valueChanged.emit(self._double_click_value)
        super().mouseDoubleClickEvent(event)


class MiniSlider(DragSlider):
    """Compact vertical slider for generator params with value popup support."""
    
    def __init__(self, param_config=None, parent=None):
        super().__init__(parent)
        self.setFixedWidth(25)
        self.setMinimumHeight(50)
        
        if param_config:
            from src.config import format_value
            self.set_param_config(param_config, format_value)


class DragValue(QLabel):
    """
    Label that supports click+drag to change integer value.
    Drag up = increase, drag down = decrease.
    Shift = fine control.
    
    Uses value_normal/value_fine sensitivity (pixels per unit).
    """
    
    value_changed = pyqtSignal(int)
    
    def __init__(self, initial_value=0, min_val=0, max_val=100, parent=None):
        super().__init__(parent)
        self._value = initial_value
        self.min_val = min_val
        self.max_val = max_val
        
        # Drag tracking
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_value = 0
        self.accumulated_delta = 0.0
        
        self.setCursor(Qt.SizeVerCursor)
        self._update_display()
        
    def _update_display(self):
        """Update label text."""
        self.setText(f"{self._value:03d}")
        
    def value(self):
        """Get current value."""
        return self._value
        
    def set_value(self, value):
        """Set value programmatically."""
        self._value = max(self.min_val, min(self.max_val, value))
        self._update_display()
        
    def mousePressEvent(self, event):
        """Start drag."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_y = event.globalPos().y()
            self.drag_start_value = self._value
            self.accumulated_delta = 0.0
            
    def mouseMoveEvent(self, event):
        """Handle drag - up = increase, down = decrease."""
        if self.dragging:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ShiftModifier:
                pixels_per_unit = DRAG_SENSITIVITY['bpm_value_fine']
            else:
                pixels_per_unit = DRAG_SENSITIVITY['bpm_value_normal']
            
            delta_y = self.drag_start_y - event.globalPos().y()
            delta_value = delta_y / pixels_per_unit
            
            new_value = int(self.drag_start_value + delta_value)
            new_value = max(self.min_val, min(self.max_val, new_value))
            
            if new_value != self._value:
                self._value = new_value
                self._update_display()
                self.value_changed.emit(self._value)
                
    def mouseReleaseEvent(self, event):
        """End drag."""
        if event.button() == Qt.LeftButton:
            self.dragging = False


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
        self.wrap = True  # Default: cycle wraps around at ends
        self.wrap_at_start = False  # Only wrap when going up from index 0
        self.sensitivity_key = 'cycle'  # Key prefix for DRAG_SENSITIVITY lookup
        self._update_display()
        
        # Drag tracking
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_index = 0
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
            self.drag_start_y = event.globalPos().y()
            self.drag_start_index = self.index
            self.moved_during_press = False
        
    def mouseMoveEvent(self, event):
        """Handle drag - up = higher index (faster), down = lower index (slower). Shift = fine."""
        if self.dragging:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ShiftModifier:
                threshold = DRAG_SENSITIVITY[f'{self.sensitivity_key}_fine']
            else:
                threshold = DRAG_SENSITIVITY[f'{self.sensitivity_key}_normal']
                
            delta_y = self.drag_start_y - event.globalPos().y()
            steps = int(delta_y / threshold)
            
            # Up = higher index (toward x2, x4 = faster triggers)
            new_index = self.drag_start_index + steps
            
            if self.wrap:
                new_index = new_index % len(self.values)
            elif self.wrap_at_start and new_index < 0:
                # Only wrap when going below 0 (up from Empty)
                new_index = len(self.values) + (new_index % len(self.values))
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


class MiniKnob(QWidget):
    """
    Tiny circular knob for channel strip EQ.
    Drag up/down to change value. Double-click to reset.
    
    Value range: 0-200 (maps to 0-2 linear gain: 0=kill, 100=unity, 200=+6dB)
    """
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 100  # Unity default
        self._min = 0
        self._max = 200
        self._default = 100
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_value = 0
        self._popup = None
        
        # Fixed size for compact channel strips
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("EQ: drag to adjust, double-click to reset")
        
    def value(self):
        return self._value
        
    def setValue(self, val):
        val = max(self._min, min(self._max, val))
        if val != self._value:
            self._value = val
            self.update()
            self.valueChanged.emit(val)
            
    def setRange(self, min_val, max_val):
        self._min = min_val
        self._max = max_val
        
    def setDoubleClickValue(self, val):
        self._default = val
        
    def setToolTip(self, tip):
        super().setToolTip(tip)
        
    def paintEvent(self, event):
        """Draw the knob as a filled arc."""
        from PyQt5.QtGui import QPainter, QColor, QPen
        from PyQt5.QtCore import QRectF
        import math
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Knob area (slightly inset)
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        
        # Background circle
        painter.setPen(QPen(QColor(COLORS['border']), 1))
        painter.setBrush(QColor(COLORS['background_dark']))
        painter.drawEllipse(rect)
        
        # Value indicator - arc from 7 o'clock to 5 o'clock (240 degrees)
        # 0 = 7 o'clock (225°), max = 5 o'clock (-45° = 315°)
        value_ratio = (self._value - self._min) / (self._max - self._min)
        
        # Draw arc showing current value
        start_angle = 225 * 16  # Qt uses 1/16th degrees, 7 o'clock
        span_angle = -int(270 * value_ratio) * 16  # Clockwise
        
        # Determine color based on value
        if self._value < 10:
            # Near kill - red
            arc_color = QColor(COLORS['warning_text'])
        elif self._value > 110:
            # Boosting - amber
            arc_color = QColor(COLORS['submenu_text'])
        else:
            # Normal range - green
            arc_color = QColor(COLORS['enabled_text'])
        
        painter.setPen(QPen(arc_color, 2))
        painter.drawArc(rect, start_angle, span_angle)
        
        # Center dot
        center_rect = QRectF(rect.center().x() - 2, rect.center().y() - 2, 4, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLORS['text_dim']))
        painter.drawEllipse(center_rect)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_y = event.globalPos().y()
            self._drag_start_value = self._value
            self._show_popup()
            
    def mouseMoveEvent(self, event):
        if self._dragging:
            # Sensitivity: full range over ~100 pixels
            delta_y = self._drag_start_y - event.globalPos().y()
            
            # Shift for fine control
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ShiftModifier:
                sensitivity = 0.5  # Fine
            else:
                sensitivity = 2.0  # Normal
                
            delta_value = int(delta_y * sensitivity)
            new_value = self._drag_start_value + delta_value
            new_value = max(self._min, min(self._max, new_value))
            
            if new_value != self._value:
                self.setValue(new_value)
                self._show_popup()
                
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._hide_popup()
            
    def mouseDoubleClickEvent(self, event):
        """Reset to default on double-click."""
        self.setValue(self._default)
        self.valueChanged.emit(self._value)
        
    def _show_popup(self):
        """Show value popup during drag."""
        if self._popup is None:
            self._popup = ValuePopup()
        
        # Convert value to dB display
        linear = self._value / 100.0  # 0-2 range
        if linear < 0.01:
            text = "-∞"
        else:
            import math
            db = 20 * math.log10(linear)
            text = f"{db:+.1f}dB"
            
        # Position popup to the right
        global_pos = self.mapToGlobal(QPoint(self.width(), self.height() // 2))
        self._popup.show_value(text, global_pos)
        
    def _hide_popup(self):
        if self._popup:
            self._popup.hide_value()
