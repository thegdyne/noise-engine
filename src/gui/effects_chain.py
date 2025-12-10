"""
Effects Chain Component - Bottom section
Master effects processing with 4 slots
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from .effect_slot import EffectSlot


class EffectsChain(QWidget):
    """Master effects chain with 4 slots."""
    
    effect_selected = pyqtSignal(int)
    effect_amount_changed = pyqtSignal(int, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slots = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create the effects chain."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # Title
        title = QLabel("MASTER EFFECTS")
        title_font = QFont('Helvetica', 12, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        main_layout.addWidget(separator)
        
        # Slots in horizontal layout
        slots_layout = QHBoxLayout()
        slots_layout.setSpacing(10)
        
        slots_layout.addStretch()
        
        for i in range(1, 5):
            slot = EffectSlot(i, "Empty")
            slot.clicked.connect(self.on_slot_clicked)
            slot.amount_changed.connect(self.on_amount_changed)
            slots_layout.addWidget(slot)
            self.slots[i] = slot
            
        slots_layout.addStretch()
        
        main_layout.addLayout(slots_layout)
        
    def on_slot_clicked(self, slot_id):
        """Handle slot click."""
        self.effect_selected.emit(slot_id)
        
    def on_amount_changed(self, slot_id, amount):
        """Handle amount change."""
        self.effect_amount_changed.emit(slot_id, amount)
        
    def get_slot(self, slot_id):
        """Get a specific slot."""
        return self.slots.get(slot_id)
        
    def set_effect_type(self, slot_id, effect_type):
        """Set effect type for a slot."""
        if slot_id in self.slots:
            self.slots[slot_id].set_effect_type(effect_type)
