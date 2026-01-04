"""
Generator Grid Component
2x4 grid of generator slots
"""

from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .generator_slot_new import GeneratorSlot
from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from src.config import SIZES


class GeneratorGrid(QWidget):
    """Grid of generator slots."""
    
    generator_selected = pyqtSignal(int)  # Legacy
    generator_changed = pyqtSignal(int, str)  # slot_id, generator_type
    generator_parameter_changed = pyqtSignal(int, str, float)
    generator_custom_parameter_changed = pyqtSignal(int, int, float)  # slot_id, param_index, value
    generator_filter_changed = pyqtSignal(int, str)
    generator_clock_enabled_changed = pyqtSignal(int, bool)  # Legacy
    generator_env_source_changed = pyqtSignal(int, int)  # slot_id, source (0=OFF, 1=CLK, 2=MIDI)
    generator_clock_rate_changed = pyqtSignal(int, str)
    generator_midi_channel_changed = pyqtSignal(int, int)  # slot_id, channel
    generator_transpose_changed = pyqtSignal(int, int)  # slot_id, semitones
    generator_portamento_changed = pyqtSignal(int, float)  # ADD THIS - slot_id, value
    generator_mute_changed = pyqtSignal(int, bool)  # slot_id, muted

    def __init__(self, rows=2, cols=4, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.slots = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the grid."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SIZES['margin_none'], SIZES['margin_none'],
                                        SIZES['margin_none'], SIZES['margin_none'])
        main_layout.setSpacing(SIZES['margin_none'])
        
        # Set tooltip on the whole widget
        self.setToolTip("GENERATORS - 8 Synth Slots")
        
        grid = QGridLayout()
        grid.setSpacing(8)  # Tighter grid
        
        slot_id = 1
        for row in range(self.rows):
            for col in range(self.cols):
                slot = GeneratorSlot(slot_id, "Empty")
                slot.clicked.connect(self.on_slot_clicked)  # Legacy
                slot.generator_changed.connect(self.on_generator_changed)
                slot.parameter_changed.connect(self.on_parameter_changed)
                slot.custom_parameter_changed.connect(self.on_custom_parameter_changed)
                slot.filter_type_changed.connect(self.on_filter_changed)
                slot.clock_enabled_changed.connect(self.on_clock_enabled_changed)
                slot.env_source_changed.connect(self.on_env_source_changed)
                slot.clock_rate_changed.connect(self.on_clock_rate_changed)
                slot.transpose_changed.connect(self.on_transpose_changed)
                slot.portamento_changed.connect(self.on_portamento_changed)
                slot.mute_changed.connect(self.on_mute_changed)
                slot.midi_channel_changed.connect(self.on_midi_channel_changed)
                grid.addWidget(slot, row, col)
                self.slots[slot_id] = slot
                slot_id += 1
                
        main_layout.addLayout(grid)
        
    def on_slot_clicked(self, slot_id):
        """Handle slot click (legacy)."""
        self.generator_selected.emit(slot_id)
    
    def on_generator_changed(self, slot_id, gen_type):
        """Handle generator type change."""
        self.generator_changed.emit(slot_id, gen_type)
        
    def on_parameter_changed(self, slot_id, param_name, value):
        """Handle parameter change."""
        self.generator_parameter_changed.emit(slot_id, param_name, value)
    
    def on_custom_parameter_changed(self, slot_id, param_index, value):
        """Handle custom parameter change."""
        self.generator_custom_parameter_changed.emit(slot_id, param_index, value)
        
    def on_filter_changed(self, slot_id, filter_type):
        """Handle filter type change."""
        self.generator_filter_changed.emit(slot_id, filter_type)
        
    def on_clock_enabled_changed(self, slot_id, enabled):
        """Handle clock enable toggle (legacy)."""
        self.generator_clock_enabled_changed.emit(slot_id, enabled)
    
    def on_env_source_changed(self, slot_id, source):
        """Handle ENV source change."""
        self.generator_env_source_changed.emit(slot_id, source)
        
    def on_clock_rate_changed(self, slot_id, rate):
        """Handle clock rate change."""
        self.generator_clock_rate_changed.emit(slot_id, rate)

    def on_transpose_changed(self, slot_id, semitones):
        """Re-emit transpose change from slot."""
        self.generator_transpose_changed.emit(slot_id, semitones)

    def on_portamento_changed(self, slot_id, value):  # ADD FROM HERE
        """Forward portamento change from slot to main frame."""
        self.generator_portamento_changed.emit(slot_id, value)  # TO HERE

    def on_mute_changed(self, slot_id, muted):
        """Handle mute toggle."""
        self.generator_mute_changed.emit(slot_id, muted)
    
    def on_midi_channel_changed(self, slot_id, channel):
        """Handle MIDI channel change."""
        self.generator_midi_channel_changed.emit(slot_id, channel)
        
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

    def set_available_generators(self, generators):
        """Update available generators in all slots."""
        for slot in self.slots.values():
            slot.type_btn.set_values(generators)

