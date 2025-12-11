"""
Effects Chain Component
Horizontal chain of effect slots
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, MONO_FONT, FONT_FAMILY, FONT_SIZES
from .widgets import DragSlider


class EffectSlot(QFrame):
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
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(3)
        
        # Effect name at top
        self.type_label = QLabel(self.effect_type)
        self.type_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        self.type_label.setAlignment(Qt.AlignCenter)
        self.type_label.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.type_label)
        
        # Slider in center
        self.amount_slider = DragSlider()
        self.amount_slider.setFixedHeight(50)
        self.amount_slider.valueChanged.connect(self.on_amount_changed)
        self.amount_slider.setEnabled(False)
        layout.addWidget(self.amount_slider, alignment=Qt.AlignCenter)
        
        # Value label at bottom
        self.amount_label = QLabel("---")
        self.amount_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self.amount_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.amount_label)
        
        self.setFixedWidth(70)
        
    def update_style(self):
        """Update appearance based on state."""
        if self.effect_type == "Empty":
            border_color = COLORS['border']
            bg_color = COLORS['background']
            text_color = COLORS['text_dim']
            self.amount_label.setText("---")
        else:
            border_color = COLORS['border_active']
            bg_color = COLORS['active_bg']
            text_color = COLORS['enabled_text']
            
        self.setStyleSheet(f"""
            EffectSlot {{
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: {bg_color};
            }}
        """)
        self.type_label.setStyleSheet(f"color: {text_color};")
        self.amount_label.setStyleSheet(f"color: {COLORS['text']};")
        
    def set_effect_type(self, effect_type):
        """Change effect type."""
        self.effect_type = effect_type
        self.type_label.setText(effect_type)
        self.amount_slider.setEnabled(effect_type != "Empty")
        self.update_style()
        
    def set_amount(self, amount):
        """Set effect amount (0-1)."""
        self.amount_slider.setValue(int(amount * 1000))
        self.amount_label.setText(f"{int(amount * 100)}%")
        
    def on_amount_changed(self, value):
        """Handle amount slider change."""
        amount = value / 1000.0
        self.amount_label.setText(f"{int(amount * 100)}%")
        self.amount_changed.emit(self.slot_id, amount)
        
    def mousePressEvent(self, event):
        """Handle click to change effect type."""
        if event.button() == Qt.LeftButton:
            # Only trigger if clicking on label area
            if event.pos().y() < 25:
                self.clicked.emit(self.slot_id)
            else:
                super().mousePressEvent(event)


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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("FX")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        title.setFixedWidth(25)
        layout.addWidget(title)
        
        # Effect slots with arrows
        for i in range(1, self.num_slots + 1):
            slot = EffectSlot(i, "Empty")
            slot.clicked.connect(self.on_slot_clicked)
            slot.amount_changed.connect(self.on_amount_changed)
            layout.addWidget(slot)
            self.slots[i] = slot
            
            if i < self.num_slots:
                arrow = QLabel("→")
                arrow.setFont(QFont(FONT_FAMILY, FONT_SIZES['section']))
                arrow.setStyleSheet(f"color: {COLORS['text_dim']};")
                arrow.setFixedWidth(15)
                arrow.setAlignment(Qt.AlignCenter)
                layout.addWidget(arrow)
        
        layout.addStretch()
                
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
