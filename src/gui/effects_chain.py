"""
Effects Chain Component
Horizontal chain of effect slots
"""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QSlider, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS


class EffectSlot(QWidget):
    """Individual effect slot."""
    
    clicked = pyqtSignal(int)
    amount_changed = pyqtSignal(int, float)
    
    def __init__(self, slot_id, effect_type="Empty", parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.effect_type = effect_type
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """Create effect slot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        self.type_label = QLabel(self.effect_type)
        self.type_label.setFont(QFont('Helvetica', 9, QFont.Bold))
        self.type_label.setAlignment(Qt.AlignCenter)
        self.type_label.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.type_label)
        
        self.amount_slider = QSlider(Qt.Horizontal)
        self.amount_slider.setMinimum(0)
        self.amount_slider.setMaximum(1000)
        self.amount_slider.setValue(500)
        self.amount_slider.setFixedWidth(60)
        self.amount_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {COLORS['border_light']};
                height: 6px;
                background: {COLORS['slider_groove']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['slider_handle']};
                border: 1px solid {COLORS['border_light']};
                width: 12px;
                margin: -3px 0;
                border-radius: 6px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLORS['slider_handle_hover']};
            }}
        """)
        self.amount_slider.valueChanged.connect(self.on_amount_changed)
        self.amount_slider.setEnabled(False)
        layout.addWidget(self.amount_slider, alignment=Qt.AlignCenter)
        
        self.setFixedSize(80, 60)
        
    def update_style(self):
        """Update appearance based on state."""
        if self.effect_type == "Empty":
            border_color = COLORS['border']
            bg_color = COLORS['background']
            text_color = COLORS['text_dim']
        else:
            border_color = COLORS['border_active']
            bg_color = '#1a2a1a'
            text_color = COLORS['enabled_text']
            
        self.setStyleSheet(f"""
            EffectSlot {{
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: {bg_color};
            }}
        """)
        self.type_label.setStyleSheet(f"color: {text_color};")
        
    def set_effect_type(self, effect_type):
        """Change effect type."""
        self.effect_type = effect_type
        self.type_label.setText(effect_type)
        self.amount_slider.setEnabled(effect_type != "Empty")
        self.update_style()
        
    def set_amount(self, amount):
        """Set effect amount (0-1)."""
        self.amount_slider.setValue(int(amount * 1000))
        
    def on_amount_changed(self, value):
        """Handle amount slider change."""
        self.amount_changed.emit(self.slot_id, value / 1000.0)
        
    def mousePressEvent(self, event):
        """Handle click to change effect type."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot_id)


class EffectsChain(QWidget):
    """Horizontal chain of effects."""
    
    effect_selected = pyqtSignal(int)
    effect_amount_changed = pyqtSignal(int, float)
    
    def __init__(self, num_slots=4, parent=None):
        super().__init__(parent)
        self.num_slots = num_slots
        self.slots = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create effects chain."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        title = QLabel("EFFECTS")
        title.setFont(QFont('Helvetica', 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(title)
        
        chain_layout = QHBoxLayout()
        chain_layout.setSpacing(5)
        
        for i in range(1, self.num_slots + 1):
            slot = EffectSlot(i, "Empty")
            slot.clicked.connect(self.on_slot_clicked)
            slot.amount_changed.connect(self.on_amount_changed)
            chain_layout.addWidget(slot)
            self.slots[i] = slot
            
            if i < self.num_slots:
                arrow = QLabel("→")
                arrow.setStyleSheet(f"color: {COLORS['text_dim']};")
                chain_layout.addWidget(arrow)
                
        layout.addLayout(chain_layout)
        
    def on_slot_clicked(self, slot_id):
        """Handle slot click."""
        self.effect_selected.emit(slot_id)
        
    def on_amount_changed(self, slot_id, amount):
        """Handle amount change."""
        self.effect_amount_changed.emit(slot_id, amount)
        
    def get_slot(self, slot_id):
        """Get effect slot by ID."""
        return self.slots.get(slot_id)
        
    def set_effect_type(self, slot_id, effect_type):
        """Set effect type for a slot."""
        if slot_id in self.slots:
            self.slots[slot_id].set_effect_type(effect_type)
