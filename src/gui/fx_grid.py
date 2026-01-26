"""
FX Grid Component - UI Refresh Phase 2
4-slot FX grid for bottom bar

Contains 4 FXSlot widgets in a horizontal row.
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .fx_slot import FXSlot
from .theme import COLORS, FONT_FAMILY, FONT_SIZES

from src.utils.logger import logger


class FXGrid(QWidget):
    """4-slot FX grid for the send effects section."""

    # Forward signals from slots
    type_changed = pyqtSignal(int, str)  # slot_id, fx_type
    param_changed = pyqtSignal(int, str, float)  # slot_id, param, value
    bypass_changed = pyqtSignal(int, bool)  # slot_id, bypassed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fx_grid")

        self.osc_bridge = None
        self.slots = []

        self._build_ui()

    def _build_ui(self):
        """Build the 4-slot grid."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Title
        title_frame = QFrame()
        title_frame.setFixedWidth(50)
        title_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """)

        title_label = QLabel("SEND\nFX", title_frame)
        title_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        title_label.setStyleSheet(f"color: {COLORS['accent_effect']};")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setGeometry(0, 40, 50, 40)

        layout.addWidget(title_frame)

        # Create 4 FX slots
        for i in range(1, 5):
            slot = FXSlot(i, parent=self)
            slot.type_changed.connect(self._forward_type_changed)
            slot.param_changed.connect(self._forward_param_changed)
            slot.bypass_changed.connect(self._forward_bypass_changed)
            self.slots.append(slot)
            layout.addWidget(slot)

        layout.addStretch()

    def _forward_type_changed(self, slot_id, fx_type):
        """Forward type changed signal."""
        self.type_changed.emit(slot_id, fx_type)

    def _forward_param_changed(self, slot_id, param, value):
        """Forward param changed signal."""
        self.param_changed.emit(slot_id, param, value)

    def _forward_bypass_changed(self, slot_id, bypassed):
        """Forward bypass changed signal."""
        self.bypass_changed.emit(slot_id, bypassed)

    def set_osc_bridge(self, bridge):
        """Set OSC bridge on all slots."""
        self.osc_bridge = bridge
        for slot in self.slots:
            slot.set_osc_bridge(bridge)

    def get_slot(self, slot_id):
        """Get a specific slot by ID (1-4)."""
        if 1 <= slot_id <= 4:
            return self.slots[slot_id - 1]
        return None

    def get_state(self):
        """Get state of all slots for preset saving."""
        return {
            'slot1': self.slots[0].get_state(),
            'slot2': self.slots[1].get_state(),
            'slot3': self.slots[2].get_state(),
            'slot4': self.slots[3].get_state(),
        }

    def load_state(self, state):
        """Load state of all slots from preset."""
        for i, key in enumerate(['slot1', 'slot2', 'slot3', 'slot4']):
            if key in state:
                self.slots[i].load_state(state[key])

    def sync_to_sc(self):
        """Send current state to SuperCollider."""
        if not self.osc_bridge:
            return

        for slot in self.slots:
            state = slot.get_state()
            slot_id = slot.slot_id

            # Send type (use SSOT key format: fx_slotN_param)
            self.osc_bridge.send(f'fx_slot{slot_id}_type', state['type'].lower())

            # Send params
            for param in ['p1', 'p2', 'p3', 'p4', 'return']:
                self.osc_bridge.send(f'fx_slot{slot_id}_{param}', state[param])

            # Send bypass
            self.osc_bridge.send(f'fx_slot{slot_id}_bypass', 1.0 if state['bypassed'] else 0.0)

        logger.debug("FX Grid: synced to SC", component="FX")
