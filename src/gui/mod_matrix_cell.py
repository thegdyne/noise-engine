"""
Mod Matrix Cell
Individual clickable cell in the mod routing matrix.

Visual states:
- Empty: no connection
- Filled circle: active connection
- Ring: disabled connection
- Size/intensity: depth magnitude
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush


class ModMatrixCell(QWidget):
    """A single cell in the mod routing matrix."""
    
    # Signals
    clicked = pyqtSignal()           # Left click
    right_clicked = pyqtSignal()     # Right click (for depth popup)
    
    # Colours by mod source type
    SOURCE_COLORS = {
        'LFO': '#00ff66',      # Green
        'Sloth': '#ff8800',    # Orange  
        'Empty': '#666666',    # Grey
    }
    
    # Alternating background tints for generator grouping
    GEN_TINTS = {
        'odd': '#1a1a1a',    # Slightly lighter for odd generators (1,3,5,7)
        'even': '#141414',   # Darker for even generators (2,4,6,8)
    }
    
    def __init__(self, source_bus: int, target_slot: int, target_param: str, parent=None):
        super().__init__(parent)
        
        self.source_bus = source_bus
        self.target_slot = target_slot
        self.target_param = target_param
        
        # State
        self.connected = False
        self.amount = 0.0  # Controls dot size (0-1)
        self.source_type = 'LFO'  # Updated by matrix window
        
        # Selection state
        self._selected = False
        
        # Generator group tint (odd/even)
        self._gen_tint = 'odd' if target_slot % 2 == 1 else 'even'
        
        # Sizing
        self.setFixedSize(28, 24)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)  # Don't steal focus from matrix window
        
        # Hover state
        self._hovered = False
        
    def set_connection(self, connected: bool, amount: float = 0.5):
        """Update cell state."""
        self.connected = connected
        self.amount = amount
        self.update()
        
    def set_source_type(self, source_type: str):
        """Update source type for colouring."""
        self.source_type = source_type
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
        
        # Get colour for source type
        color = QColor(self.SOURCE_COLORS.get(self.source_type, '#666666'))
        
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
            self.clicked.emit()
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit()
