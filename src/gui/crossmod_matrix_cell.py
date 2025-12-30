"""
Crossmod Matrix Cell
Individual clickable cell in the crossmod routing matrix.

Visual states:
- Empty: no connection (background tint only)
- Filled circle: active connection (size = amount)
- Filled circle + notch: inverted connection
- Hover highlight
- Selection border
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush


class CrossmodMatrixCell(QWidget):
    """A single cell in the crossmod routing matrix."""
    
    # Signals
    clicked = pyqtSignal()           # Left click
    right_clicked = pyqtSignal()     # Right click (for popup)
    shift_clicked = pyqtSignal()     # Shift + left click (for invert toggle)
    
    # 8 source colors (one per generator)
    SOURCE_COLORS = {
        1: '#ff4444',  # Red
        2: '#ff8800',  # Orange
        3: '#ffcc00',  # Yellow
        4: '#44ff44',  # Green
        5: '#44ffff',  # Cyan
        6: '#4488ff',  # Blue
        7: '#aa44ff',  # Purple
        8: '#ff44aa',  # Pink
    }
    
    # Alternating background tints for generator grouping
    GEN_TINTS = {
        'odd': '#1a1a1a',    # Slightly lighter for odd generators (1,3,5,7)
        'even': '#141414',   # Darker for even generators (2,4,6,8)
    }
    
    def __init__(self, source_gen: int, target_gen: int, target_param: str, parent=None):
        super().__init__(parent)
        
        self.source_gen = source_gen      # 1-8
        self.target_gen = target_gen      # 1-8
        self.target_param = target_param  # 'cutoff', etc.
        
        # State
        self.connected = False
        self.amount = 0.0      # Controls dot size (0-1)
        self.invert = False    # Inverted connection (for ducking)
        
        # Selection state
        self._selected = False
        
        # Generator group tint (odd/even) based on target
        self._gen_tint = 'odd' if target_gen % 2 == 1 else 'even'
        
        # Sizing
        self.setFixedSize(28, 24)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)  # Don't steal focus from matrix window
        
        # Hover state
        self._hovered = False
    
    def set_connection(self, connected: bool, amount: float = 0.5, invert: bool = False):
        """Update cell state."""
        self.connected = connected
        self.amount = amount
        self.invert = invert
        self.update()
    
    def set_source_gen(self, source_gen: int):
        """Update source generator for coloring."""
        self.source_gen = source_gen
        self.update()
    
    def set_selected(self, selected: bool):
        """Update selection state."""
        self._selected = selected
        self.update()
    
    def paintEvent(self, event):
        """Draw the cell."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        # Generator group background tint (always draw first)
        tint_color = self.GEN_TINTS.get(self._gen_tint, self.GEN_TINTS['odd'])
        painter.fillRect(0, 0, w, h, QColor(tint_color))
        
        # Selection highlight
        if self._selected:
            painter.fillRect(0, 0, w, h, QColor('#444466'))
            # Draw focus border
            pen = QPen(QColor('#8888ff'))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(1, 1, w - 2, h - 2)
        # Background on hover (only if not selected)
        elif self._hovered:
            painter.fillRect(0, 0, w, h, QColor('#333333'))
        
        # Get color for source generator
        color = QColor(self.SOURCE_COLORS.get(self.source_gen, '#666666'))
        
        if self.connected:
            # Circle size based on amount (3-10 radius)
            min_radius = 3
            max_radius = 10
            radius = min_radius + self.amount * (max_radius - min_radius)
            radius = min(radius, min(w, h) // 2 - 2)
            
            # Filled circle for connection
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
            
            # Invert indicator: notch/half-moon on right side
            if self.invert:
                # Draw a dark notch to indicate inversion
                painter.setBrush(QBrush(QColor(tint_color)))
                painter.setPen(Qt.NoPen)
                notch_width = radius * 0.5
                painter.drawEllipse(QRectF(
                    cx + radius * 0.3 - notch_width/2,
                    cy - notch_width/2,
                    notch_width,
                    notch_width
                ))
        else:
            # Empty cell - draw subtle dot on hover or when selected
            if self._hovered or self._selected:
                painter.setBrush(QBrush(QColor('#555555')))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QRectF(cx - 3, cy - 3, 6, 6))
    
    def enterEvent(self, event):
        """Mouse entered cell."""
        self._hovered = True
        self.update()
    
    def leaveEvent(self, event):
        """Mouse left cell."""
        self._hovered = False
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse click."""
        # Give focus to the matrix window for keyboard navigation
        top_window = self.window()
        if top_window:
            top_window.setFocus(Qt.MouseFocusReason)
        
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ShiftModifier:
                self.shift_clicked.emit()
            else:
                self.clicked.emit()
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit()
