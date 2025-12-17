"""
Mod Routing Debug Window

Shows real-time state of all mod routing connections and calculated bracket values.

Usage:
    From Python console or main_frame:
        from gui.mod_debug import ModDebugWindow
        self.mod_debug = ModDebugWindow(self.mod_routing, self)
        self.mod_debug.show()
    
    Or press F10 to toggle (if hotkey installed)
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QShortcut
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QKeySequence, QColor

from .theme import COLORS, FONT_SIZES, MONO_FONT
from .mod_routing_state import ModRoutingState, Polarity


class ModDebugWindow(QDialog):
    """Debug window showing mod routing state."""
    
    def __init__(self, routing_state: ModRoutingState, generator_grid=None, parent=None):
        super().__init__(parent)
        self.routing_state = routing_state
        self.generator_grid = generator_grid
        
        self.setWindowTitle("Mod Routing Debug")
        self.setMinimumSize(900, 400)
        self.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        # Make it a tool window
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        
        self._setup_ui()
        self._connect_signals()
        
        # Live refresh timer for CurrVal updates
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start(100)  # 100ms = 10fps
        
        # Initial refresh
        self._refresh()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Mod Routing State (Live)")
        header.setFont(QFont(MONO_FONT, FONT_SIZES['section'], QFont.Bold))
        header.setStyleSheet(f"color: {COLORS['enabled_text']};")
        layout.addWidget(header)
        
        # Connection count
        self.count_label = QLabel("Connections: 0")
        self.count_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        layout.addWidget(self.count_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "ModSrc", "ModTgt", "CurrDep", "CurrAmt", "CurrOff", 
            "Pol", "Inv", "+Rng", "-Rng", "SldrVal", "SldrMin", "SldrMax"
        ])
        self.table.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['background']};
                gridline-color: {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['border_light']};
                color: {COLORS['text']};
                padding: 4px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        btn_layout.addWidget(refresh_btn)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(copy_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _copy_to_clipboard(self):
        """Copy table contents to clipboard as markdown."""
        from PyQt5.QtWidgets import QApplication
        
        # Build markdown table
        headers = []
        for col in range(self.table.columnCount()):
            headers.append(self.table.horizontalHeaderItem(col).text())
        
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        for row in range(self.table.rowCount()):
            cells = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                cells.append(item.text() if item else "")
            lines.append("| " + " | ".join(cells) + " |")
        
        text = "\n".join(lines)
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        self.count_label.setText(f"Connections: {self.table.rowCount()} (Copied!)")
    
    def _connect_signals(self):
        """Connect to routing state signals for live updates."""
        self.routing_state.connection_added.connect(self._refresh)
        self.routing_state.connection_removed.connect(self._on_removed)
        self.routing_state.connection_changed.connect(self._refresh)
        self.routing_state.all_cleared.connect(self._refresh)
    
    def _on_removed(self, *args):
        """Handle connection removed (signal has different signature)."""
        self._refresh()
    
    def _refresh(self, *args):
        """Refresh the table with current routing state."""
        connections = self.routing_state.get_all_connections()
        
        self.count_label.setText(f"Connections: {len(connections)}")
        
        self.table.setRowCount(len(connections))
        
        for row, conn in enumerate(connections):
            # Source (e.g., "M1.A" = bus 0)
            mod_slot = conn.source_bus // 4 + 1
            output_idx = conn.source_bus % 4
            output_name = ['A', 'B', 'C', 'D'][output_idx]
            source = f"M{mod_slot}.{output_name}"
            
            # Target (e.g., "G1.cutoff")
            target = f"G{conn.target_slot}.{conn.target_param}"
            
            # Calculate bracket values
            effective = conn.depth * conn.amount
            up_range = 0.0
            down_range = 0.0
            
            if conn.polarity == Polarity.BIPOLAR:
                up_range = effective
                down_range = effective
            elif conn.polarity == Polarity.UNI_POS:
                up_range = effective
            elif conn.polarity == Polarity.UNI_NEG:
                down_range = effective
            
            # Get actual slider base value if generator_grid available
            base = 0.5  # Default fallback
            slider_min = None
            slider_max = None
            if self.generator_grid:
                slot = self.generator_grid.get_slot(conn.target_slot)
                if slot and conn.target_param in slot.sliders:
                    slider = slot.sliders[conn.target_param]
                    base = slider.value() / 1000.0
                    # Get what the slider actually has stored
                    slider_min = slider._mod_range_min
                    slider_max = slider._mod_range_max
            
            # Polarity display
            polarity_names = {
                Polarity.BIPOLAR: "Bi",
                Polarity.UNI_POS: "U+",
                Polarity.UNI_NEG: "U-"
            }
            
            # Set table items - focus on tracking actual values
            items = [
                source,
                target,
                f"{conn.depth:.2f}",
                f"{conn.amount:.2f}",
                f"{conn.offset:+.2f}",
                polarity_names.get(conn.polarity, "?"),
                "Yes" if conn.invert else "No",
                f"{up_range:.2f}",
                f"{down_range:.2f}",
                f"{base:.2f}",
                f"{slider_min:.2f}" if slider_min is not None else "?",
                f"{slider_max:.2f}" if slider_max is not None else "?"
            ]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                
                # Color coding
                if col == 5:  # Polarity
                    if conn.polarity == Polarity.UNI_POS:
                        item.setForeground(QColor('#00ff66'))
                    elif conn.polarity == Polarity.UNI_NEG:
                        item.setForeground(QColor('#ff6666'))
                    else:
                        item.setForeground(QColor('#6666ff'))
                elif col == 6 and conn.invert:  # Invert
                    item.setForeground(QColor('#ff8800'))
                # Mismatch detection: expected vs actual slider values
                elif col == 10 and slider_min is not None:  # SldrMin
                    expected_min = max(0, base + conn.offset - down_range)
                    if abs(slider_min - expected_min) > 0.01:
                        item.setForeground(QColor('#ff0000'))  # Red if mismatch
                elif col == 11 and slider_max is not None:  # SldrMax
                    expected_max = min(1, base + conn.offset + up_range)
                    if abs(slider_max - expected_max) > 0.01:
                        item.setForeground(QColor('#ff0000'))  # Red if mismatch
                
                self.table.setItem(row, col, item)


# Global reference for toggle
_mod_debug_window = None


def show_mod_debug(routing_state, generator_grid=None, parent=None):
    """Show the mod debug window."""
    global _mod_debug_window
    if _mod_debug_window is None or not _mod_debug_window.isVisible():
        _mod_debug_window = ModDebugWindow(routing_state, generator_grid, parent)
    _mod_debug_window.show()
    _mod_debug_window.raise_()
    return _mod_debug_window


def toggle_mod_debug(routing_state, generator_grid=None, parent=None):
    """Toggle mod debug window visibility."""
    global _mod_debug_window
    if _mod_debug_window is not None and _mod_debug_window.isVisible():
        _mod_debug_window.close()
        _mod_debug_window = None
        print("[Mod Debug] CLOSED")
    else:
        _mod_debug_window = show_mod_debug(routing_state, generator_grid, parent)
        print("[Mod Debug] OPENED")


def install_mod_debug_hotkey(window, routing_state, generator_grid=None):
    """Install F10 hotkey to toggle mod debug window."""
    shortcut = QShortcut(QKeySequence(Qt.Key_F10), window)
    shortcut.activated.connect(lambda: toggle_mod_debug(routing_state, generator_grid, window))
    print("[Mod Debug] Press F10 (Fn+F10 on Mac) to toggle mod debug window")
