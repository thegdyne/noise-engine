"""
Mod Source Panel
Container for MOD_SLOT_COUNT mod source slots in the left panel

Replaces the old WIP ModulationSources widget.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .mod_source_slot import ModSourceSlot
from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from src.config import MOD_SLOT_COUNT


class ModSourcePanel(QWidget):
    """Container for mod source slots - vertical stack."""
    
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
        """Build the panel with scrollable slot container."""
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
        
        # Scroll area for slots
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['background']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Container widget for slots
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # Create slots
        for i in range(1, MOD_SLOT_COUNT + 1):
            slot = ModSourceSlot(i)
            self._connect_slot_signals(slot)
            container_layout.addWidget(slot)
            self.slots[i] = slot
            
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
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
