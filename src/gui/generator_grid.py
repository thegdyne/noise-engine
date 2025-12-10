"""
Generator Grid Component - Center frame
Holds multiple generator slots
Responsive grid layout
"""

from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from .generator_slot import GeneratorSlot


class GeneratorGrid(QWidget):
    """Grid of generator slots."""
    
    # Signals
    generator_selected = pyqtSignal(int)  # Emits slot ID
    
    def __init__(self, rows=2, cols=4, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.slots = {}
        
        # Responsive sizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the grid."""
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("GENERATORS")
        title_font = QFont('Helvetica', 14, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, 0, 0, 1, self.cols)
        
        # Create grid of slots
        slot_id = 1
        for row in range(self.rows):
            for col in range(self.cols):
                slot = GeneratorSlot(slot_id, "Empty")
                slot.clicked.connect(self.on_slot_clicked)
                layout.addWidget(slot, row + 1, col)
                # Equal stretch for all slots
                layout.setRowStretch(row + 1, 1)
                layout.setColumnStretch(col, 1)
                self.slots[slot_id] = slot
                slot_id += 1
                
    def on_slot_clicked(self, slot_id):
        """Handle slot click."""
        self.generator_selected.emit(slot_id)
        
    def get_slot(self, slot_id):
        """Get a specific slot."""
        return self.slots.get(slot_id)
        
    def set_generator_type(self, slot_id, gen_type):
        """Set generator type for a slot."""
        if slot_id in self.slots:
            self.slots[slot_id].set_generator_type(gen_type)
            
    def set_generator_active(self, slot_id, active):
        """Set active state for a slot."""
        if slot_id in self.slots:
            self.slots[slot_id].set_active(active)
