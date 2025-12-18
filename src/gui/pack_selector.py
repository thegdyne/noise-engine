"""
Pack Selector Widget
Dropdown to select active generator pack
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from src.config import get_enabled_packs, get_current_pack, set_current_pack


class PackSelector(QWidget):
    """Dropdown to select the active generator pack."""
    
    pack_changed = pyqtSignal(str)  # Emits pack_id (or empty string for Core)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._populate()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        
        # Label
        label = QLabel("PACK")
        label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        label.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(label)
        
        # Dropdown
        self.combo = QComboBox()
        self.combo.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.combo.setMinimumWidth(120)
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 2px 6px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['border_light']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['enabled']};
            }}
        """)
        self.combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.combo)
    
    def _populate(self):
        """Populate dropdown with Core + enabled packs."""
        self.combo.blockSignals(True)
        self.combo.clear()
        
        # Core is always first
        self.combo.addItem("Core", None)
        
        # Add enabled packs
        for pack in get_enabled_packs():
            self.combo.addItem(pack['display_name'], pack['id'])
        
        # Set current selection
        current = get_current_pack()
        if current is None:
            self.combo.setCurrentIndex(0)
        else:
            for i in range(self.combo.count()):
                if self.combo.itemData(i) == current:
                    self.combo.setCurrentIndex(i)
                    break
        
        self.combo.blockSignals(False)
    
    def _on_selection_changed(self, index):
        """Handle dropdown selection change."""
        pack_id = self.combo.itemData(index)
        set_current_pack(pack_id)
        self.pack_changed.emit(pack_id or "")
    
    def refresh(self):
        """Refresh pack list (call after packs change)."""
        self._populate()
