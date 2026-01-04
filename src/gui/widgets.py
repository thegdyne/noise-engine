"""
Reusable UI Widgets
Atomic components with no business logic - just behavior
"""

from PyQt5.QtWidgets import QSlider, QPushButton, QLabel, QApplication, QWidget, QMenu
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QFont, QPainter, QPen, QColor, QPolygon

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
    Supports modulation visualization (range brackets + animated value).
    
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
        self.drag_start_x = 0
        self.drag_start_value = 0
        
        # Value popup (optional)
        self._popup = None
        self._param_config = None
        self._format_func = None
        
        # Double-click reset (optional)
        self._double_click_value = None
        
        # Modulation visualization
        self._mod_range_min = None   # Normalized 0-1 (outer/depth)
        self._mod_range_max = None   # Normalized 0-1 (outer/depth)
        self._mod_inner_min = None   # Normalized 0-1 (inner/amount)
        self._mod_inner_max = None   # Normalized 0-1 (inner/amount)
        self._mod_current = None     # Normalized 0-1 (animated value)
        self._mod_color = QColor('#00ff66')  # Default green

        # MIDI CC ghost indicator (pickup mode)
        self._cc_ghost = None  # Normalized 0-1, or None if not showing
        self._cc_ghost_color = QColor('#FF6600')  # Orange

        # MIDI mapping visual state
        self._midi_armed = False
        self._midi_mapped = False

    def set_modulation_range(self, min_norm: float, max_norm: float, 
                             inner_min: float = None, inner_max: float = None,
                             color: QColor = None):
        """
        Set modulation range to display on slider.
        
        Args:
            min_norm: Minimum normalized value (0-1) - outer/depth range
            max_norm: Maximum normalized value (0-1) - outer/depth range
            inner_min: Inner minimum (0-1) - amount range (optional)
            inner_max: Inner maximum (0-1) - amount range (optional)
            color: Optional color for the mod indicator
        """
        self._mod_range_min = min_norm
        self._mod_range_max = max_norm
        self._mod_inner_min = inner_min
        self._mod_inner_max = inner_max
        if color:
            self._mod_color = color
        self.update()
        self.repaint()  # Force immediate repaint
        # Also update parent in case of composite widgets
        if self.parent():
            self.parent().update()
    
    def set_modulated_value(self, norm_value: float):
        """
        Set the current modulated value (animated indicator).
        
        Args:
            norm_value: Normalized value (0-1)
        """
        self._mod_current = norm_value
        self.update()
        self.repaint()  # Force immediate repaint
    
    def clear_modulation(self):
        """Clear modulation visualization."""
        self._mod_range_min = None
        self._mod_range_max = None
        self._mod_inner_min = None
        self._mod_inner_max = None
        self._mod_current = None
        self.update()

    def set_cc_ghost(self, norm_value):
        """Set CC ghost indicator position (pickup mode).
        Args:
            norm_value: Normalized value (0-1), or None to hide ghost
        """
        self._cc_ghost = norm_value
        self.update()

    def clear_cc_ghost(self):
        """Clear CC ghost indicator."""
        self._cc_ghost = None
        self.update()

    def set_midi_armed(self, armed):
        """Set MIDI Learn armed state (shows highlight)."""
        self._midi_armed = armed
        self.update()

    def set_midi_mapped(self, mapped):
        """Set MIDI mapped state (shows badge)."""
        self._midi_mapped = mapped
        self.update()

    def has_modulation(self) -> bool:
        """Check if modulation is active on this slider."""
        return self._mod_range_min is not None

    def paintEvent(self, event):
        """Draw slider with modulation overlay."""
        # Let Qt draw the standard slider first
        super().paintEvent(event)

        # Skip modulation overlay if disabled
        if not self.isEnabled():
            return

        # Draw modulation overlay if active
        if self._mod_range_min is not None:
            # Store values at paint time for debug comparison
            self._last_paint_min = self._mod_range_min
            self._last_paint_max = self._mod_range_max

            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Get the actual groove rect from Qt style
            from PyQt5.QtWidgets import QStyleOptionSlider, QStyle
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            groove_rect = self.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self
            )

            groove_x = groove_rect.x()
            groove_width = groove_rect.width()
            groove_top = groove_rect.top()
            groove_bottom = groove_rect.bottom()
            available_height = groove_bottom - groove_top

            # Convert normalized values to Y positions (inverted - 0 at bottom)
            def norm_to_y(norm):
                return groove_top + (1.0 - norm) * available_height

            # Outer range (depth) - Y positions
            outer_min_y = norm_to_y(self._mod_range_min)
            outer_max_y = norm_to_y(self._mod_range_max)

            # Inner range (amount) - Y positions if available
            has_inner = (self._mod_inner_min is not None and
                         self._mod_inner_max is not None)
            if has_inner:
                inner_min_y = norm_to_y(self._mod_inner_min)
                inner_max_y = norm_to_y(self._mod_inner_max)

            # Handle collapsed outer range
            if abs(self._mod_range_max - self._mod_range_min) < 0.001:
                bracket_color = QColor(self._mod_color)
                bracket_color.setAlpha(200)
                painter.setPen(QPen(bracket_color, 2))
                cap_y = int(outer_min_y)
                painter.drawLine(groove_x - 2, cap_y, groove_x + groove_width + 2, cap_y)
            else:
                # Draw OUTER range (depth) as dim overlay
                outer_color = QColor(self._mod_color)
                outer_color.setAlpha(40)  # Dimmer than inner
                painter.fillRect(
                    int(groove_x), int(outer_max_y),
                    groove_width, int(outer_min_y - outer_max_y),
                    outer_color
                )

                # Draw outer brackets (dim)
                outer_bracket = QColor(self._mod_color)
                outer_bracket.setAlpha(100)
                painter.setPen(QPen(outer_bracket, 1))
                painter.drawLine(groove_x - 2, int(outer_max_y), groove_x + groove_width + 2, int(outer_max_y))
                painter.drawLine(groove_x - 2, int(outer_min_y), groove_x + groove_width + 2, int(outer_min_y))

                # Draw INNER range (amount) if available
                if has_inner and abs(self._mod_inner_max - self._mod_inner_min) >= 0.001:
                    # Inner fill (brighter)
                    inner_color = QColor(self._mod_color)
                    inner_color.setAlpha(100)
                    painter.fillRect(
                        int(groove_x), int(inner_max_y),
                        groove_width, int(inner_min_y - inner_max_y),
                        inner_color
                    )

                    # Inner brackets (bright)
                    inner_bracket = QColor(self._mod_color)
                    inner_bracket.setAlpha(255)
                    painter.setPen(QPen(inner_bracket, 2))
                    painter.drawLine(groove_x - 2, int(inner_max_y), groove_x + groove_width + 2, int(inner_max_y))
                    painter.drawLine(groove_x - 2, int(inner_min_y), groove_x + groove_width + 2, int(inner_min_y))

            # Draw current modulated value indicator (animated line)
            if self._mod_current is not None:
                current_y = norm_to_y(self._mod_current)
                # Bright white indicator for visibility
                painter.setPen(QPen(QColor('#ffffff'), 4))
                painter.drawLine(
                    groove_x - 6, int(current_y),
                    groove_x + groove_width + 6, int(current_y)
                )

            painter.end()

        # Draw CC ghost indicator (pickup mode) - separate from modulation
        if self._cc_ghost is not None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            rect = self.rect()
            available_height = rect.height() - 10

            # Ghost position (inverted for vertical slider)
            ghost_y = rect.top() + 5 + available_height * (1.0 - self._cc_ghost)

            # Draw ghost line
            painter.setPen(QPen(self._cc_ghost_color, 2))
            painter.drawLine(rect.left() + 2, int(ghost_y),
                             rect.right() - 2, int(ghost_y))

            painter.end()

        # Draw MIDI armed highlight (yellow border during learn)
        if self._midi_armed:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor('#FFA500'), 3))  # Orange
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
            painter.end()

        # Draw MIDI mapped badge (small dot)
        if self._midi_mapped:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor('#FF00FF'))  # Bright pink dot
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.width() - 4, 2, 4, 4)  # Top-right corner
            painter.end()

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
            self.drag_start_x = event.globalPos().x()
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

            # Use X-axis for horizontal, Y-axis for vertical
            if self.orientation() == Qt.Horizontal:
                delta = event.globalPos().x() - self.drag_start_x
                travel = self.width() * (3.0 if modifiers & Qt.ShiftModifier else 1.0)
            else:
                delta = self.drag_start_y - event.globalPos().y()
                travel = fader_height * (3.0 if modifiers & Qt.ShiftModifier else 1.0)
            value_range = self.maximum() - self.minimum()
            delta_value = int((delta / travel) * value_range)
            
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

    def contextMenuEvent(self, event):
        """Right-click menu for MIDI Learn."""
        menu = QMenu(self)

        # Find MainFrame by walking up parent chain
        main_frame = self._get_main_frame()
        if not main_frame:
            return

        is_mapped = self._midi_mapped

        if is_mapped:
            menu.addAction("Clear MIDI Mapping", self._clear_midi_mapping)

        menu.addAction("MIDI Learn", self._start_midi_learn)
        menu.exec_(event.globalPos())

    def _get_main_frame(self):
        """Find MainFrame by walking up parent chain."""
        widget = self.window()
        print(f"DEBUG window: {widget}, has cc_mapping_manager: {hasattr(widget, 'cc_mapping_manager')}")
        while widget:
            if hasattr(widget, 'cc_mapping_manager'):
                return widget
            print(f"DEBUG checking parent: {widget.parent()}")
            widget = widget.parent()
        return None

    def _start_midi_learn(self):
        """Start MIDI Learn for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_learn_manager.start_learn(self)

    def _clear_midi_mapping(self):
        """Clear MIDI mapping for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_mapping_manager.remove_mapping(self)
            self.set_midi_mapped(False)

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
        self.invert_drag = False  # If True, drag up = lower index, drag down = higher index
        self.sensitivity_key = 'cycle'  # Key prefix for DRAG_SENSITIVITY lookup
        self.skip_prefix = None  # Skip values starting with this prefix (e.g., "────" for separators)
        # Text alignment for custom paint (stylesheet text-align is ignored)
        self.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        self.text_padding_lr = 3  # default padding for custom draw
        self._update_display()
        
        # Drag tracking
        self.dragging = False
        self.drag_start_y = 0
        self.drag_start_index = 0
        self.moved_during_press = False

        # MIDI mapping support
        self._midi_armed = False
        self._midi_mapped = False
        self._last_cc_high = False  # Edge detection for cycling

    def _should_skip(self, index):
        """Check if value at index should be skipped."""
        if self.skip_prefix is None:
            return False
        return self.values[index].startswith(self.skip_prefix)
        
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
        
    def set_values(self, values):
        """Update the list of values and reset to first."""
        self.values = values
        self.index = 0
        self._update_display()

    def cycle_forward(self):
        """Move to next value (higher index), skipping skip_prefix entries."""
        start_index = self.index
        attempts = 0
        max_attempts = len(self.values)
        
        while attempts < max_attempts:
            if self.wrap:
                self.index = (self.index + 1) % len(self.values)
            else:
                self.index = min(self.index + 1, len(self.values) - 1)
            
            if not self._should_skip(self.index):
                break
            
            # Prevent infinite loop if all values are skippable
            attempts += 1
            if self.index == start_index:
                break
        
        self._update_display()
        self._emit_signals()
        
    def cycle_backward(self):
        """Move to previous value (lower index), skipping skip_prefix entries."""
        start_index = self.index
        attempts = 0
        max_attempts = len(self.values)
        
        while attempts < max_attempts:
            if self.wrap:
                self.index = (self.index - 1) % len(self.values)
            else:
                self.index = max(self.index - 1, 0)
            
            if not self._should_skip(self.index):
                break
            
            # Prevent infinite loop
            attempts += 1
            if self.index == start_index:
                break
        
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
            
            # Invert if requested (for filter sync: up = x multipliers, down = / divisions)
            if self.invert_drag:
                steps = -steps
            
            # Up = higher index (toward x2, x4 = faster triggers)
            new_index = self.drag_start_index + steps
            
            if self.wrap:
                new_index = new_index % len(self.values)
            elif self.wrap_at_start and new_index < 0:
                # Only wrap when going below 0 (up from Empty)
                new_index = len(self.values) + (new_index % len(self.values))
            else:
                new_index = max(0, min(len(self.values) - 1, new_index))
            
            # Skip over separator entries
            if self._should_skip(new_index):
                direction = 1 if steps >= 0 else -1
                attempts = 0
                while self._should_skip(new_index) and attempts < len(self.values):
                    new_index = (new_index + direction) % len(self.values)
                    attempts += 1
            
            if new_index != self.index:
                self.moved_during_press = True
                self.index = new_index
                self._update_display()
                self._emit_signals()

    def mouseReleaseEvent(self, event):
        """End drag. If no movement, cycle forward. Shift+click calls special handler if set."""
        if event.button() == Qt.LeftButton:
            if not self.moved_during_press:
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.ShiftModifier and hasattr(self, 'shift_click_callback') and self.shift_click_callback:
                    self.shift_click_callback()
                else:
                    self.cycle_forward()
            self.dragging = False
            self.moved_during_press = False

    def paintEvent(self, event):
        """Custom paint with clipping and text elision to prevent overflow."""
        from PyQt5.QtGui import QPainter, QFontMetrics
        from PyQt5.QtWidgets import QStylePainter, QStyleOptionButton, QStyle

        p = QStylePainter(self)
        p.setClipRect(self.rect())  # CRITICAL: stop spill outside widget

        # Draw button background/frame using style
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.text = ""  # We'll draw text ourselves
        p.drawControl(QStyle.CE_PushButton, opt)

        # Draw elided text with per-instance padding
        r = self.contentsRect()
        fm = QFontMetrics(self.font())
        text = self.text()
        pad = self.text_padding_lr
        elided = fm.elidedText(text, Qt.ElideRight, max(0, r.width() - pad * 2))

        # Dim text color when disabled
        if not self.isEnabled():
            p.setPen(QColor(COLORS['border']))

        p.drawText(r.adjusted(pad, 0, -pad, 0), self.text_alignment, elided)

        # Set tooltip to full text if elided
        if elided != text:
            self.setToolTip(text)

    def set_midi_armed(self, armed):
        """Set MIDI Learn armed state."""
        self._midi_armed = armed
        self.update()

    def set_midi_mapped(self, mapped):
        """Set MIDI mapped state."""
        self._midi_mapped = mapped
        self.update()

    def minimum(self):
        """Return minimum index (for MIDI CC compatibility)."""
        return 0

    def maximum(self):
        """Return maximum index (for MIDI CC compatibility)."""
        return len(self.values) - 1

    def value(self):
        """Return current index (for MIDI CC compatibility)."""
        return self.index

    def setValue(self, index):
        """Set index (for MIDI CC compatibility)."""
        index = max(0, min(index, len(self.values) - 1))
        if index != self.index:
            self.index = index
            self._update_display()
            self._emit_signals()

    def handle_cc(self, value):
        """Handle CC - button cycles with wrap, knob sweeps through options."""
        # Detect if this is a button (0 or 127) or knob (values in between)
        if value == 0 or value == 127:
            # Button-style: cycle on rising edge
            cc_high = value >= 64
            if cc_high and not self._last_cc_high:
                self._last_cc_high = cc_high
                return True  # Will trigger cycle_forward
            self._last_cc_high = cc_high
            return False
        else:
            # Knob-style: set index directly based on CC position
            num_options = len(self.values)
            new_index = int((value / 127.0) * (num_options - 1) + 0.5)
            new_index = max(0, min(new_index, num_options - 1))
            if new_index != self.index:
                self.index = new_index
                self._update_display()
                self._emit_signals()
            return False  # Don't trigger cycle_forward

    def _get_main_frame(self):
        """Find MainFrame by walking up parent chain."""
        widget = self.window()
        while widget:
            if hasattr(widget, 'cc_mapping_manager'):
                return widget
            widget = widget.parent()
        return None

    def _start_midi_learn(self):
        """Start MIDI Learn for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_learn_manager.start_learn(self)

    def _clear_midi_mapping(self):
        """Clear MIDI mapping for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_mapping_manager.remove_mapping(self)
            self.set_midi_mapped(False)

    def contextMenuEvent(self, event):
        """Right-click menu for MIDI Learn."""
        menu = QMenu(self)

        main_frame = self._get_main_frame()
        if not main_frame:
            return

        if self._midi_mapped:
            menu.addAction("Clear MIDI Mapping", self._clear_midi_mapping)

        menu.addAction("MIDI Learn", self._start_midi_learn)
        menu.exec_(event.globalPos())

    def paintEvent(self, event):
        """Draw button with MIDI badge."""
        super().paintEvent(event)

        if self._midi_mapped:
            from PyQt5.QtGui import QPainter
            painter = QPainter(self)
            painter.setBrush(QColor('#FF00FF'))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.width() - 6, 1, 4, 4)
            painter.end()

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
        # MIDI mapping visual state
        self._midi_armed = False
        self._midi_mapped = False
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

        # Use dimmer colors when disabled
        if self.isEnabled():
            border_color = QColor(COLORS['border'])
            bg_color = QColor(COLORS['background_dark'])
            dot_color = QColor(COLORS['text_dim'])
        else:
            border_color = QColor(COLORS['border']).darker(150)
            bg_color = QColor(COLORS['background'])
            dot_color = QColor(COLORS['border'])

        # Background circle
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(bg_color)
        painter.drawEllipse(rect)

        # Value indicator - arc from 7 o'clock to 5 o'clock (240 degrees)
        # 0 = 7 o'clock (225°), max = 5 o'clock (-45° = 315°)
        value_ratio = (self._value - self._min) / (self._max - self._min)

        # Draw arc showing current value
        start_angle = 225 * 16  # Qt uses 1/16th degrees, 7 o'clock
        span_angle = -int(270 * value_ratio) * 16  # Clockwise

        # Determine color based on value (dimmed when disabled)
        if not self.isEnabled():
            arc_color = QColor(COLORS['border'])
        elif self._value < 10:
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
        painter.setBrush(dot_color)
        painter.drawEllipse(center_rect)

        # Draw MIDI mapped badge (small dot)
        if self._midi_mapped:
            painter.setBrush(QColor('#FF00FF'))  # Bright pink
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.width() - 6, 0, 5, 5)

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

    def set_midi_armed(self, armed):
        """Set MIDI Learn armed state."""
        self._midi_armed = armed
        self.update()

    def set_midi_mapped(self, mapped):
        """Set MIDI mapped state."""
        self._midi_mapped = mapped
        self.update()

    def _get_main_frame(self):
        """Find MainFrame by walking up parent chain."""
        widget = self.window()
        while widget:
            if hasattr(widget, 'cc_mapping_manager'):
                return widget
            widget = widget.parent()
        return None

    def _start_midi_learn(self):
        """Start MIDI Learn for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_learn_manager.start_learn(self)

    def _clear_midi_mapping(self):
        """Clear MIDI mapping for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_mapping_manager.remove_mapping(self)
            self.set_midi_mapped(False)

    def contextMenuEvent(self, event):
        """Right-click menu for MIDI Learn."""
        menu = QMenu(self)

        main_frame = self._get_main_frame()
        if not main_frame:
            return

        if self._midi_mapped:
            menu.addAction("Clear MIDI Mapping", self._clear_midi_mapping)

        menu.addAction("MIDI Learn", self._start_midi_learn)
        menu.exec_(event.globalPos())

    def minimum(self):
        """Return minimum value (for MIDI CC compatibility)."""
        return self._min

    def maximum(self):
        """Return maximum value (for MIDI CC compatibility)."""
        return self._max

class MidiButton(QPushButton):
    """Button with MIDI CC mapping support."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._midi_armed = False
        self._midi_mapped = False
        self._midi_mode = 'toggle'  # 'toggle' or 'momentary'
        self._midi_state = False  # Current on/off state for MIDI
        self._last_cc_high = False  # Track CC state for edge detection

    def set_midi_armed(self, armed):
        """Set MIDI Learn armed state."""
        self._midi_armed = armed
        self.update()

    def set_midi_mapped(self, mapped):
        """Set MIDI mapped state."""
        self._midi_mapped = mapped
        self.update()

    def set_midi_mode(self, mode):
        """Set MIDI mode: 'toggle' or 'momentary'."""
        self._midi_mode = mode

    def handle_cc(self, value):
        """Handle incoming CC value. Returns True if button should activate."""
        cc_high = value >= 64

        if self._midi_mode == 'toggle':
            # Toggle only on rising edge (low → high transition)
            if cc_high and not self._last_cc_high:
                self._last_cc_high = cc_high
                return True
            self._last_cc_high = cc_high
            return False
        else:
            # Momentary: click on any edge change (press and release)
            if cc_high != self._last_cc_high:
                self._last_cc_high = cc_high
                return True
            return False

    def _get_main_frame(self):
        """Find MainFrame by walking up parent chain."""
        widget = self.window()
        while widget:
            if hasattr(widget, 'cc_mapping_manager'):
                return widget
            widget = widget.parent()
        return None

    def _start_midi_learn(self):
        """Start MIDI Learn for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_learn_manager.start_learn(self)

    def _clear_midi_mapping(self):
        """Clear MIDI mapping for this control."""
        main_frame = self._get_main_frame()
        if main_frame:
            main_frame.cc_mapping_manager.remove_mapping(self)
            self.set_midi_mapped(False)

    def _set_toggle_mode(self):
        """Set to toggle mode."""
        self._midi_mode = 'toggle'

    def _set_momentary_mode(self):
        """Set to momentary mode."""
        self._midi_mode = 'momentary'

    def contextMenuEvent(self, event):
        """Right-click menu for MIDI Learn."""
        menu = QMenu(self)

        main_frame = self._get_main_frame()
        if not main_frame:
            return

        if self._midi_mapped:
            menu.addAction("Clear MIDI Mapping", self._clear_midi_mapping)
            menu.addSeparator()
            toggle_action = menu.addAction("Toggle Mode", self._set_toggle_mode)
            toggle_action.setCheckable(True)
            toggle_action.setChecked(self._midi_mode == 'toggle')
            momentary_action = menu.addAction("Momentary Mode", self._set_momentary_mode)
            momentary_action.setCheckable(True)
            momentary_action.setChecked(self._midi_mode == 'momentary')
            menu.addSeparator()

        menu.addAction("MIDI Learn", self._start_midi_learn)
        menu.exec_(event.globalPos())

    def paintEvent(self, event):
        """Draw button with MIDI badge."""
        super().paintEvent(event)

        if self._midi_mapped:
            from PyQt5.QtGui import QPainter
            painter = QPainter(self)
            painter.setBrush(QColor('#FF00FF'))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.width() - 6, 1, 4, 4)
            painter.end()