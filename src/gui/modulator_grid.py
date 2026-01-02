"""
Modulator Grid
Container for MOD_SLOT_COUNT modulator slots in the left panel

Layout: 2 rows × 2 columns to align with generator grid rows.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .modulator_slot import ModulatorSlot
from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from src.config import MOD_SLOT_COUNT, SIZES


class ModulatorGrid(QWidget):
    """Container for modulator slots - 2x2 grid layout."""
    
    # Forwarded signals from slots
    generator_changed = pyqtSignal(int, str)
    parameter_changed = pyqtSignal(int, str, float)
    output_wave_changed = pyqtSignal(int, int, int)
    output_phase_changed = pyqtSignal(int, int, int)
    output_polarity_changed = pyqtSignal(int, int, int)

    # ARSEq+ envelope signals
    env_attack_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_release_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_curve_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_sync_mode_changed = pyqtSignal(int, int, int)  # slot_id, env_idx, mode
    env_loop_rate_changed = pyqtSignal(int, int, int)  # slot_id, env_idx, rate_idx

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slots = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Build the grid with 2x2 slot layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SIZES['margin_none'], SIZES['margin_none'], 
                                   SIZES['margin_none'], SIZES['margin_none'])
        layout.setSpacing(SIZES['margin_none'])
        
        # 2x2 grid for slots (aligns with 2 generator rows)
        grid = QGridLayout()
        grid.setContentsMargins(SIZES['margin_none'], SIZES['margin_none'],
                                 SIZES['margin_none'], SIZES['margin_none'])
        grid.setSpacing(SIZES['spacing_normal'])
        
        # Create slots in 2x2 layout with default generators
        # Slot 1 (LFO) | Slot 2 (Sloth)  (top row)
        # Slot 3 (LFO) | Slot 4 (Sloth)  (bottom row)
        slot_defaults = ["LFO", "Sloth", "LFO", "Sloth"]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for i in range(1, MOD_SLOT_COUNT + 1):
            default_gen = slot_defaults[i - 1]
            slot = ModulatorSlot(i, default_generator=default_gen)
            self._connect_slot_signals(slot)
            row, col = positions[i - 1]
            grid.addWidget(slot, row, col)
            self.slots[i] = slot
            
        # Make rows stretch equally
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        
        layout.addLayout(grid, stretch=1)
        
    def _connect_slot_signals(self, slot):
        """Connect slot signals to grid signals."""
        slot.generator_changed.connect(self.generator_changed.emit)
        slot.parameter_changed.connect(self.parameter_changed.emit)
        slot.output_wave_changed.connect(self.output_wave_changed.emit)
        slot.output_phase_changed.connect(self.output_phase_changed.emit)
        slot.output_polarity_changed.connect(self.output_polarity_changed.emit)

        # ARSEq+ envelope signals
        slot.env_attack_changed.connect(self.env_attack_changed.emit)
        slot.env_release_changed.connect(self.env_release_changed.emit)
        slot.env_curve_changed.connect(self.env_curve_changed.emit)
        slot.env_sync_mode_changed.connect(self.env_sync_mode_changed.emit)
        slot.env_loop_rate_changed.connect(self.env_loop_rate_changed.emit)

    def get_slot(self, slot_id):
        """Get a slot by ID."""
        return self.slots.get(slot_id)

    def get_state(self) -> dict:
        """Get all modulator slots state for preset save (Phase 3)."""
        return {
            "slots": [slot.get_state() for slot in self.slots.values()]
        }

    def set_state(self, state: dict):
        """Apply modulator slots state from preset load (Phase 3)."""
        slots_data = state.get("slots", [])
        for i, slot in enumerate(self.slots.values()):
            if i < len(slots_data):
                slot.set_state(slots_data[i])
