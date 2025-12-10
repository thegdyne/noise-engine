"""
Generator Grid Component
2x4 grid of generator slots
"""

from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from .generator_slot import GeneratorSlot


class GeneratorGrid(QWidget):
    """Grid of generator slots."""
    
    generator_selected = pyqtSignal(int)
    generator_parameter_changed = pyqtSignal(int, str, float)
    generator_filter_changed = pyqtSignal(int, str)
    generator_clock_changed = pyqtSignal(int, str)
    
    def __init__(self, rows=2, cols=4, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.slots = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the grid."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        title = QLabel("GENERATORS")
        title_font = QFont('Helvetica', 12, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        slot_id = 1
        for row in range(self.rows):
            for col in range(self.cols):
                slot = GeneratorSlot(slot_id, "Empty")
                slot.clicked.connect(self.on_slot_clicked)
                slot.parameter_changed.connect(self.on_parameter_changed)
                slot.filter_type_changed.connect(self.on_filter_changed)
                slot.vca_clock_changed.connect(self.on_clock_changed)
                grid.addWidget(slot, row, col)
                self.slots[slot_id] = slot
                slot_id += 1
                
        main_layout.addLayout(grid)
        
    def on_slot_clicked(self, slot_id):
        """Handle slot click."""
        self.generator_selected.emit(slot_id)
        
    def on_parameter_changed(self, slot_id, param_name, value):
        """Handle parameter change."""
        self.generator_parameter_changed.emit(slot_id, param_name, value)
        
    def on_filter_changed(self, slot_id, filter_type):
        """Handle filter type change."""
        self.generator_filter_changed.emit(slot_id, filter_type)
        
    def on_clock_changed(self, slot_id, clock_div):
        """Handle clock routing change."""
        self.generator_clock_changed.emit(slot_id, clock_div)
        
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
