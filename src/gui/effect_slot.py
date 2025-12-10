"""
Effect Slot Component - Compact version
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class EffectSlot(QWidget):
    """A single effect slot in the chain - compact."""
    
    clicked = pyqtSignal(int)
    amount_changed = pyqtSignal(int, float)
    
    def __init__(self, slot_id, effect_type="Empty", parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.effect_type = effect_type
        self.active = False
        
        self.setMinimumSize(60, 80)
        self.setMaximumWidth(80)
        self.setup_ui()
        
    def setup_ui(self):
        """Create slot interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        
        self.type_label = QLabel(self.effect_type)
        self.type_label.setFont(QFont('Helvetica', 8, QFont.Bold))
        self.type_label.setAlignment(Qt.AlignCenter)
        self.type_label.setWordWrap(True)
        self.type_label.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.type_label)
        
        self.amount_slider = QSlider(Qt.Vertical)
        self.amount_slider.setMinimum(0)
        self.amount_slider.setMaximum(100)
        self.amount_slider.setValue(75)
        self.amount_slider.setEnabled(False)
        self.amount_slider.setFixedHeight(40)
        
        self.amount_slider.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #666;
                width: 6px;
                background: #333;
                border-radius: 3px;
            }
            QSlider::handle:vertical {
                background: #888;
                border: 1px solid #555;
                height: 10px;
                margin: 0 -2px;
                border-radius: 5px;
            }
        """)
        
        self.amount_slider.valueChanged.connect(
            lambda val: self.amount_changed.emit(self.slot_id, val / 100.0)
        )
        self.amount_slider.sliderReleased.connect(lambda: self.amount_slider.repaint())
        
        layout.addWidget(self.amount_slider, alignment=Qt.AlignCenter)
        
        self.amount_label = QLabel("75%")
        self.amount_label.setAlignment(Qt.AlignCenter)
        self.amount_label.setFont(QFont('Menlo', 7))
        layout.addWidget(self.amount_label)
        
        self.update_style()
        
    def update_style(self):
        """Update appearance based on state."""
        if self.effect_type == "Empty":
            border_color = "#333"
            bg_color = "#1a1a1a"
        elif self.active:
            border_color = "#4488ff"
            bg_color = "#1a2a3a"
        else:
            border_color = "#555"
            bg_color = "#252525"
            
        self.setStyleSheet(f"""
            EffectSlot {{
                border: 1px solid {border_color};
                border-radius: 3px;
                background-color: {bg_color};
            }}
        """)
        
    def set_effect_type(self, effect_type):
        """Change effect type."""
        self.effect_type = effect_type
        self.type_label.setText(effect_type)
        
        if effect_type == "Empty":
            self.amount_slider.setEnabled(False)
            self.active = False
        else:
            self.amount_slider.setEnabled(True)
            self.active = True
            
        self.update_style()
        
    def set_amount(self, amount):
        """Set amount (0.0-1.0)."""
        self.amount_slider.setValue(int(amount * 100))
        self.amount_label.setText(f"{int(amount * 100)}%")
        
    def mousePressEvent(self, event):
        """Handle click on type label area."""
        if event.button() == Qt.LeftButton:
            if event.pos().y() < 25:
                self.clicked.emit(self.slot_id)
