"""
Layout Debug Utility for Noise Engine

Enables visual debugging of Qt layouts by overlaying size/geometry info
on widgets and drawing colored backgrounds to reveal container bounds.

Usage:
    from gui.layout_debug import enable_layout_debug, disable_layout_debug
    
    # Enable on specific widget and children
    enable_layout_debug(widget)
    
    # Or enable globally via environment variable:
    # DEBUG_LAYOUT=1 python src/main.py

Configuration:
    Set DEBUG_LAYOUT=1 environment variable before launching, or call
    enable_layout_debug() on specific widgets at runtime.
"""

import os
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
from PyQt5.QtCore import Qt, QRect

# Global flag
DEBUG_LAYOUT = os.environ.get('DEBUG_LAYOUT', '0') == '1'

# Colors for different widget types (semi-transparent)
DEBUG_COLORS = {
    'QFrame': QColor(255, 0, 0, 30),      # Red
    'QWidget': QColor(0, 255, 0, 30),     # Green
    'QLabel': QColor(0, 0, 255, 30),      # Blue
    'QPushButton': QColor(255, 255, 0, 30),  # Yellow
    'QSlider': QColor(255, 0, 255, 30),   # Magenta
    'QVBoxLayout': QColor(0, 255, 255, 30),  # Cyan
    'QHBoxLayout': QColor(255, 128, 0, 30),  # Orange
    'default': QColor(128, 128, 128, 30),    # Gray
}

# Store original paintEvent methods
_original_paint_events = {}


def get_debug_color(widget):
    """Get debug color based on widget class name."""
    class_name = widget.__class__.__name__
    return DEBUG_COLORS.get(class_name, DEBUG_COLORS['default'])


def debug_paint_event(widget, original_paint, event):
    """Replacement paintEvent that draws debug overlay."""
    # Call original paint first
    original_paint(event)
    
    # Draw debug overlay
    painter = QPainter(widget)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Semi-transparent background
    color = get_debug_color(widget)
    painter.fillRect(widget.rect(), color)
    
    # Border
    border_color = QColor(color)
    border_color.setAlpha(150)
    painter.setPen(QPen(border_color, 1))
    painter.drawRect(widget.rect().adjusted(0, 0, -1, -1))
    
    # Size info text
    geo = widget.geometry()
    hint = widget.sizeHint()
    policy = widget.sizePolicy()
    
    name = widget.objectName() or widget.__class__.__name__
    info = f"{name}\n{geo.width()}x{geo.height()}"
    if hint.isValid():
        info += f"\nhint:{hint.width()}x{hint.height()}"
    
    # Draw text background
    painter.setFont(QFont('Monaco', 8))
    text_rect = painter.fontMetrics().boundingRect(
        QRect(0, 0, 200, 100), 
        Qt.AlignLeft | Qt.TextWordWrap, 
        info
    )
    text_rect.moveTo(2, 2)
    text_rect.adjust(-1, -1, 3, 3)
    
    painter.fillRect(text_rect, QColor(0, 0, 0, 180))
    painter.setPen(Qt.white)
    painter.drawText(text_rect.adjusted(2, 2, 0, 0), Qt.AlignLeft, info)
    
    painter.end()


def enable_layout_debug(widget=None, recursive=True):
    """
    Enable layout debugging on a widget (and optionally its children).
    
    Args:
        widget: QWidget to debug. If None, applies to all top-level windows.
        recursive: If True, also debug all child widgets.
    """
    global DEBUG_LAYOUT
    DEBUG_LAYOUT = True
    
    if widget is None:
        app = QApplication.instance()
        if app:
            for w in app.topLevelWidgets():
                enable_layout_debug(w, recursive)
        return
    
    # Store and replace paintEvent
    widget_id = id(widget)
    if widget_id not in _original_paint_events:
        original = widget.paintEvent
        _original_paint_events[widget_id] = original
        widget.paintEvent = lambda e, w=widget, o=original: debug_paint_event(w, o, e)
    
    if recursive:
        for child in widget.findChildren(QWidget):
            enable_layout_debug(child, recursive=False)


def disable_layout_debug(widget=None, recursive=True):
    """
    Disable layout debugging and restore original paintEvent.
    
    Args:
        widget: QWidget to restore. If None, applies to all.
        recursive: If True, also restore all child widgets.
    """
    global DEBUG_LAYOUT
    DEBUG_LAYOUT = False
    
    if widget is None:
        # Restore all
        for widget_id, original in list(_original_paint_events.items()):
            # Can't easily get widget from id, so just clear
            pass
        _original_paint_events.clear()
        return
    
    widget_id = id(widget)
    if widget_id in _original_paint_events:
        widget.paintEvent = _original_paint_events.pop(widget_id)
    
    if recursive:
        for child in widget.findChildren(QWidget):
            disable_layout_debug(child, recursive=False)


def print_widget_info(widget, indent=0):
    """
    Print detailed size/policy info for a widget tree.
    
    Usage:
        print_widget_info(my_widget)
    """
    prefix = "  " * indent
    name = widget.objectName() or widget.__class__.__name__
    geo = widget.geometry()
    hint = widget.sizeHint()
    min_hint = widget.minimumSizeHint()
    policy = widget.sizePolicy()
    
    print(f"{prefix}{name}:")
    print(f"{prefix}  geometry: {geo.width()}x{geo.height()} at ({geo.x()},{geo.y()})")
    print(f"{prefix}  sizeHint: {hint.width()}x{hint.height()}")
    print(f"{prefix}  minSizeHint: {min_hint.width()}x{min_hint.height()}")
    print(f"{prefix}  policy: H={policy.horizontalPolicy()} V={policy.verticalPolicy()}")
    print(f"{prefix}  min: {widget.minimumWidth()}x{widget.minimumHeight()}")
    print(f"{prefix}  max: {widget.maximumWidth()}x{widget.maximumHeight()}")
    
    layout = widget.layout()
    if layout:
        margins = layout.contentsMargins()
        print(f"{prefix}  layout: {layout.__class__.__name__}")
        print(f"{prefix}  margins: L={margins.left()} T={margins.top()} R={margins.right()} B={margins.bottom()}")
        print(f"{prefix}  spacing: {layout.spacing()}")
    
    for child in widget.children():
        if isinstance(child, QWidget):
            print_widget_info(child, indent + 1)


def log_size_constraints(widget, label=""):
    """
    Quick one-liner to log a widget's size constraints.
    
    Usage:
        log_size_constraints(self.type_btn, "type_btn")
    """
    hint = widget.sizeHint()
    geo = widget.geometry()
    policy = widget.sizePolicy()
    
    h_policies = {0: 'Fixed', 1: 'Min', 4: 'Max', 5: 'Preferred', 7: 'Expanding', 13: 'MinExp', 3: 'Ignored'}
    h_str = h_policies.get(policy.horizontalPolicy(), str(policy.horizontalPolicy()))
    v_str = h_policies.get(policy.verticalPolicy(), str(policy.verticalPolicy()))
    
    print(f"[{label}] geo={geo.width()}x{geo.height()} hint={hint.width()}x{hint.height()} policy=({h_str},{v_str}) min={widget.minimumWidth()}x{widget.minimumHeight()} max={widget.maximumWidth()}x{widget.maximumHeight()}")
