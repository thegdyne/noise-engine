"""
Mod Source Panel
Container for MOD_SLOT_COUNT mod source slots in the left panel

Layout: 2 rows × 2 columns to align with generator grid rows.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .mod_source_slot import ModSourceSlot
from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from src.config import MOD_SLOT_COUNT


class ModSourcePanel(QWidget):
    """Container for mod source slots - 2x2 grid layout."""
    
    # Forwarded signals from slots
    generator_changed = pyqtSignal(int, str)
    parameter_changed = pyqtSignal(int, str, float)
    output_wave_changed = pyqtSignal(int, int, int)
    output_phase_changed = pyqtSignal(int, int, int)
    output_polarity_changed = pyqtSignal(int, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slots = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Build the panel with 2x2 slot grid."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("MOD SOURCES")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # 2x2 grid for slots (aligns with 2 generator rows)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        
        # Create slots in 2x2 layout with default generators
        # Slot 1 (LFO) | Slot 2 (Sloth)  (top row)
        # Slot 3 (LFO) | Slot 4 (Sloth)  (bottom row)
        slot_defaults = ["LFO", "Sloth", "LFO", "Sloth"]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for i in range(1, MOD_SLOT_COUNT + 1):
            default_gen = slot_defaults[i - 1]
            slot = ModSourceSlot(i, default_generator=default_gen)
            self._connect_slot_signals(slot)
            row, col = positions[i - 1]
            grid.addWidget(slot, row, col)
            self.slots[i] = slot
            
        # Make rows stretch equally
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        
        layout.addLayout(grid, stretch=1)
        
    def _connect_slot_signals(self, slot):
        """Connect slot signals to panel signals."""
        slot.generator_changed.connect(self.generator_changed.emit)
        slot.parameter_changed.connect(self.parameter_changed.emit)
        slot.output_wave_changed.connect(self.output_wave_changed.emit)
        slot.output_phase_changed.connect(self.output_phase_changed.emit)
        slot.output_polarity_changed.connect(self.output_polarity_changed.emit)
        
    def get_slot(self, slot_id):
        """Get a slot by ID."""
        return self.slots.get(slot_id)
