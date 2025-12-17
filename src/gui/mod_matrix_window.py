"""
Mod Matrix Window
Visual matrix for creating modulation routing connections.

Layout:
- Rows: 16 mod buses (4 slots × 4 outputs)
- Columns: Generator parameters (8 slots × key params)
- Click cell to toggle connection
- Right-click for depth popup

Keyboard:
- Arrow keys: Navigate cells
- Space: Toggle connection
- Delete/Backspace: Remove connection
- D: Open depth popup
- 1-9: Quick depth (10%-90%)
- 0: Set depth to 0%
- -: Invert depth sign
- Escape: Deselect

Row labels update dynamically based on mod slot types (LFO/Sloth).
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QColor, QKeySequence

from .mod_matrix_cell import ModMatrixCell
from .mod_routing_state import ModRoutingState, ModConnection
from .mod_connection_popup import ModConnectionPopup
from .theme import COLORS, FONT_FAMILY, FONT_SIZES, MONO_FONT


# Modulatable parameters per generator (key, short label)
GEN_PARAMS = [
    ('cutoff', 'CUT'),
    ('resonance', 'RES'),
    ('frequency', 'FRQ'),
    ('attack', 'ATK'),
    ('decay', 'DEC'),
]

# Number of generator slots
NUM_GEN_SLOTS = 8

# Number of mod slots and outputs per slot
NUM_MOD_SLOTS = 4
OUTPUTS_PER_MOD_SLOT = 4

# Total rows and columns for navigation
TOTAL_ROWS = NUM_MOD_SLOTS * OUTPUTS_PER_MOD_SLOT  # 16
TOTAL_COLS = NUM_GEN_SLOTS * len(GEN_PARAMS)        # 40


class ModMatrixWindow(QMainWindow):
    """Matrix window for mod routing."""
    
    def __init__(self, routing_state: ModRoutingState, parent=None):
        super().__init__(parent)
        
        self.routing_state = routing_state
        self.cells = {}  # (bus, slot, param) -> ModMatrixCell
        self.cell_grid = []  # [row][col] -> (bus, slot, param) for navigation
        self.mod_slot_types = ['LFO', 'Sloth', 'LFO', 'Sloth']  # Default types
        
        # Selection state
        self.selected_row = 0
        self.selected_col = 0
        
        # Drag state
        self._dragging = False
        self._drag_start = None
        
        self.setWindowTitle("Mod Matrix")
        self.setMinimumSize(800, 500)
        
        # Restore window geometry from settings
        self._load_settings()
        
        # Accept keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Dark theme
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {COLORS['background']}; }}
            QLabel {{ color: {COLORS['text']}; }}
        """)
        
        self._setup_ui()
        self._connect_signals()
        self._sync_from_state()
        
    def _setup_ui(self):
        """Build the matrix UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        # Title
        title = QLabel("MOD ROUTING MATRIX")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_bright']}; padding: 5px;")
        layout.addWidget(title)
        
        # Scroll area for the matrix
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background-color: {COLORS['background']}; }}
            QScrollBar:vertical {{ width: 12px; background: {COLORS['background_light']}; }}
            QScrollBar:horizontal {{ height: 12px; background: {COLORS['background_light']}; }}
        """)
        scroll.setFocusPolicy(Qt.NoFocus)  # Don't steal focus from main window
        
        # Matrix container
        matrix_widget = QWidget()
        matrix_widget.setFocusPolicy(Qt.NoFocus)
        matrix_layout = QGridLayout(matrix_widget)
        matrix_layout.setSpacing(1)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        
        # Build column headers (row 0)
        self._build_column_headers(matrix_layout)
        
        # Build row headers and cells
        self._build_rows(matrix_layout)
        
        scroll.setWidget(matrix_widget)
        layout.addWidget(scroll)
        
        # Legend
        legend = self._build_legend()
        layout.addWidget(legend)
        
    def _build_column_headers(self, layout: QGridLayout):
        """Build column headers: G1 CUT, G1 RES, G2 CUT, etc."""
        col = 1  # Start after row header column
        
        for gen_slot in range(1, NUM_GEN_SLOTS + 1):
            for param_key, param_label in GEN_PARAMS:
                # Two-line header: "G1" / "CUT"
                header = QLabel(f"G{gen_slot}\n{param_label}")
                header.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
                header.setAlignment(Qt.AlignCenter)
                header.setFixedSize(28, 36)
                header.setStyleSheet(f"""
                    color: {COLORS['text']};
                    background-color: {COLORS['background_light']};
                    border-bottom: 1px solid {COLORS['border']};
                """)
                layout.addWidget(header, 0, col)
                col += 1
            
            # Add separator after each generator's params
            if gen_slot < NUM_GEN_SLOTS:
                sep = QFrame()
                sep.setFixedWidth(2)
                sep.setStyleSheet(f"background-color: {COLORS['border']};")
                layout.addWidget(sep, 0, col)
                col += 1
                
    def _build_rows(self, layout: QGridLayout):
        """Build row headers and cell grid."""
        row = 1  # Start after column headers
        nav_row = 0  # Navigation row index (0-15)
        
        for mod_slot in range(NUM_MOD_SLOTS):
            slot_type = self.mod_slot_types[mod_slot]
            output_labels = self._get_output_labels(slot_type)
            
            for output_idx in range(OUTPUTS_PER_MOD_SLOT):
                bus_idx = mod_slot * OUTPUTS_PER_MOD_SLOT + output_idx
                
                # Row header: "M1.A" or "M2.X"
                label_text = f"M{mod_slot + 1}.{output_labels[output_idx]}"
                row_header = QLabel(label_text)
                row_header.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
                row_header.setFixedSize(50, 24)
                row_header.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row_header.setStyleSheet(f"""
                    color: {self._get_slot_color(slot_type)};
                    padding-right: 6px;
                """)
                row_header.setObjectName(f"row_header_{bus_idx}")
                layout.addWidget(row_header, row, 0)
                
                # Cells for this row
                col = 1
                nav_col = 0  # Navigation column index (0-39)
                row_cells = []
                
                for gen_slot in range(1, NUM_GEN_SLOTS + 1):
                    for param_key, param_label in GEN_PARAMS:
                        cell = ModMatrixCell(bus_idx, gen_slot, param_key)
                        cell.set_source_type(slot_type)
                        cell.clicked.connect(
                            lambda b=bus_idx, s=gen_slot, p=param_key: self._on_cell_clicked(b, s, p)
                        )
                        cell.right_clicked.connect(
                            lambda b=bus_idx, s=gen_slot, p=param_key: self._on_cell_right_clicked(b, s, p)
                        )
                        layout.addWidget(cell, row, col)
                        self.cells[(bus_idx, gen_slot, param_key)] = cell
                        row_cells.append((bus_idx, gen_slot, param_key))
                        col += 1
                        nav_col += 1
                    
                    # Skip separator column
                    if gen_slot < NUM_GEN_SLOTS:
                        col += 1
                
                self.cell_grid.append(row_cells)
                row += 1
                nav_row += 1
            
            # Add separator row between mod slots
            if mod_slot < NUM_MOD_SLOTS - 1:
                sep_col = 0
                total_cols = 1 + NUM_GEN_SLOTS * len(GEN_PARAMS) + (NUM_GEN_SLOTS - 1)
                for c in range(total_cols):
                    sep = QFrame()
                    sep.setFixedHeight(2)
                    sep.setStyleSheet(f"background-color: {COLORS['border']};")
                    layout.addWidget(sep, row, c)
                row += 1
                
    def _build_legend(self) -> QWidget:
        """Build legend showing source type colours."""
        legend = QWidget()
        layout = QHBoxLayout(legend)
        layout.setContentsMargins(5, 5, 5, 5)
        
        layout.addStretch()
        
        for source_type, color in ModMatrixCell.SOURCE_COLORS.items():
            if source_type == 'Empty':
                continue
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            layout.addWidget(dot)
            label = QLabel(source_type)
            label.setStyleSheet(f"color: {COLORS['text']}; margin-right: 15px;")
            layout.addWidget(label)
        
        # Instructions
        layout.addWidget(QLabel("  |  "))
        instructions = QLabel("Click/Space: toggle  •  Right-click/D: depth  •  1-9: quick depth  •  -: invert  •  Del: remove")
        instructions.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(instructions)
        
        layout.addStretch()
        
        return legend
    
    def _get_output_labels(self, slot_type: str) -> list:
        """Get output labels for a mod slot type."""
        if slot_type == 'Sloth':
            return ['X', 'Y', 'Z', 'R']
        else:  # LFO or Empty
            return ['A', 'B', 'C', 'D']
    
    def _get_slot_color(self, slot_type: str) -> str:
        """Get colour for a mod slot type."""
        return ModMatrixCell.SOURCE_COLORS.get(slot_type, '#666666')
    
    def _connect_signals(self):
        """Connect to routing state signals."""
        self.routing_state.connection_added.connect(self._on_connection_added)
        self.routing_state.connection_removed.connect(self._on_connection_removed)
        self.routing_state.connection_changed.connect(self._on_connection_changed)
        self.routing_state.all_cleared.connect(self._on_all_cleared)
    
    def _sync_from_state(self):
        """Sync cell states from routing state."""
        for conn in self.routing_state.get_all_connections():
            cell = self.cells.get((conn.source_bus, conn.target_slot, conn.target_param))
            if cell:
                cell.set_connection(True, conn.depth, conn.polarity.value)
    
    def _on_cell_clicked(self, bus: int, slot: int, param: str):
        """Handle cell left-click: toggle connection."""
        # Update selection to clicked cell
        self._select_cell(bus, slot, param)
        
        conn = self.routing_state.get_connection(bus, slot, param)
        
        if conn:
            # Remove existing connection
            self.routing_state.remove_connection(bus, slot, param)
        else:
            # Add new connection with default depth
            new_conn = ModConnection(
                source_bus=bus,
                target_slot=slot,
                target_param=param,
                depth=0.5
            )
            self.routing_state.add_connection(new_conn)
    
    def _select_cell(self, bus: int, slot: int, param: str):
        """Update selection to specific cell."""
        # Clear old selection
        self._update_selection_visual(False)
        
        # Find row/col for this cell
        for row_idx, row_cells in enumerate(self.cell_grid):
            for col_idx, key in enumerate(row_cells):
                if key == (bus, slot, param):
                    self.selected_row = row_idx
                    self.selected_col = col_idx
                    self._update_selection_visual(True)
                    return
    
    def _on_cell_right_clicked(self, bus: int, slot: int, param: str):
        """Handle cell right-click: show depth popup for existing connection, or create new."""
        # Update selection to clicked cell
        self._select_cell(bus, slot, param)
        
        conn = self.routing_state.get_connection(bus, slot, param)
        
        if not conn:
            # No connection - create one first, then open popup
            conn = ModConnection(
                source_bus=bus,
                target_slot=slot,
                target_param=param,
                depth=0.5
            )
            self.routing_state.add_connection(conn)
        
        # Get labels for popup header
        mod_slot = bus // OUTPUTS_PER_MOD_SLOT
        output_idx = bus % OUTPUTS_PER_MOD_SLOT
        slot_type = self.mod_slot_types[mod_slot]
        output_labels = self._get_output_labels(slot_type)
        source_label = f"M{mod_slot + 1}.{output_labels[output_idx]}"
        
        # Find param label
        param_label = param.upper()[:3]
        for key, label in GEN_PARAMS:
            if key == param:
                param_label = label
                break
        target_label = f"G{slot} {param_label}"
        
        # Show popup
        popup = ModConnectionPopup(conn, source_label, target_label, self)
        popup.connection_changed.connect(
            lambda c, b=bus, s=slot, p=param: self._on_popup_connection_changed(b, s, p, c)
        )
        popup.remove_requested.connect(
            lambda b=bus, s=slot, p=param: self._on_popup_remove(b, s, p)
        )
        
        # Position popup near the cell
        cell = self.cells.get((bus, slot, param))
        if cell:
            global_pos = cell.mapToGlobal(cell.rect().center())
            popup.move(global_pos.x() + 20, global_pos.y() - 50)
        
        popup.show()
    
    def _on_popup_connection_changed(self, bus: int, slot: int, param: str, conn: ModConnection):
        """Handle connection change from popup (depth, amount, polarity, invert)."""
        self.routing_state.update_connection(
            bus, slot, param,
            depth=conn.depth,
            amount=conn.amount,
            polarity=conn.polarity,
            invert=conn.invert
        )
    
    def _on_popup_remove(self, bus: int, slot: int, param: str):
        """Handle remove from popup."""
        self.routing_state.remove_connection(bus, slot, param)
    
    def _on_connection_added(self, conn: ModConnection):
        """Update cell when connection added."""
        cell = self.cells.get((conn.source_bus, conn.target_slot, conn.target_param))
        if cell:
            cell.set_connection(True, conn.depth, conn.polarity.value)
    
    def _on_connection_removed(self, source_bus: int, target_slot: int, target_param: str):
        """Update cell when connection removed."""
        cell = self.cells.get((source_bus, target_slot, target_param))
        if cell:
            cell.set_connection(False)
    
    def _on_connection_changed(self, conn: ModConnection):
        """Update cell when connection parameters change."""
        cell = self.cells.get((conn.source_bus, conn.target_slot, conn.target_param))
        if cell:
            cell.set_connection(True, conn.depth, conn.polarity.value)
    
    def _on_all_cleared(self):
        """Clear all cells when routing cleared."""
        for cell in self.cells.values():
            cell.set_connection(False)
    
    def update_mod_slot_type(self, slot: int, slot_type: str):
        """
        Update a mod slot's type (affects row labels and cell colours).
        
        Args:
            slot: 1-4 (mod slot number)
            slot_type: 'LFO', 'Sloth', or 'Empty'
        """
        if 1 <= slot <= NUM_MOD_SLOTS:
            self.mod_slot_types[slot - 1] = slot_type
            
            # Update row headers and cell colours for this slot
            output_labels = self._get_output_labels(slot_type)
            base_bus = (slot - 1) * OUTPUTS_PER_MOD_SLOT
            
            for output_idx in range(OUTPUTS_PER_MOD_SLOT):
                bus_idx = base_bus + output_idx
                
                # Update row header
                header = self.findChild(QLabel, f"row_header_{bus_idx}")
                if header:
                    header.setText(f"M{slot}.{output_labels[output_idx]}")
                    header.setStyleSheet(f"""
                        color: {self._get_slot_color(slot_type)};
                        padding-right: 6px;
                    """)
                
                # Update cell colours
                for gen_slot in range(1, NUM_GEN_SLOTS + 1):
                    for param_key, _ in GEN_PARAMS:
                        cell = self.cells.get((bus_idx, gen_slot, param_key))
                        if cell:
                            cell.set_source_type(slot_type)
    
    # ========================================
    # KEYBOARD NAVIGATION
    # ========================================
    
    def keyPressEvent(self, event):
        """Handle keyboard input for navigation and actions."""
        key = event.key()
        modifiers = event.modifiers()
        
        # Arrow keys: navigate
        if key == Qt.Key_Up:
            self._move_selection(-1, 0)
        elif key == Qt.Key_Down:
            self._move_selection(1, 0)
        elif key == Qt.Key_Left:
            self._move_selection(0, -1)
        elif key == Qt.Key_Right:
            self._move_selection(0, 1)
        
        # Space: toggle connection
        elif key == Qt.Key_Space:
            self._toggle_selected()
        
        # Delete/Backspace: remove connection
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self._remove_selected()
        
        # D: open depth popup
        elif key == Qt.Key_D:
            self._open_depth_popup_for_selected()
        
        # 1-9: quick depth (10%-90%)
        elif Qt.Key_1 <= key <= Qt.Key_9:
            depth = (key - Qt.Key_0) / 10.0
            self._set_selected_depth(depth)
        
        # 0: set depth to 0% (effectively disable)
        elif key == Qt.Key_0:
            self._set_selected_depth(0.0)
        
        # Minus: invert depth
        elif key == Qt.Key_Minus:
            self._invert_selected_depth()
        
        # Escape: deselect
        elif key == Qt.Key_Escape:
            self._clear_selection()
        
        else:
            super().keyPressEvent(event)
    
    def _move_selection(self, row_delta: int, col_delta: int):
        """Move selection by given delta."""
        # Clear old selection visual
        self._update_selection_visual(False)
        
        # Calculate new position with wrapping
        new_row = (self.selected_row + row_delta) % TOTAL_ROWS
        new_col = (self.selected_col + col_delta) % TOTAL_COLS
        
        self.selected_row = new_row
        self.selected_col = new_col
        
        # Update new selection visual
        self._update_selection_visual(True)
        
        # Scroll to make selected cell visible
        self._scroll_to_selected()
    
    def _update_selection_visual(self, selected: bool):
        """Update the visual state of the selected cell."""
        if not self.cell_grid:
            return
        if self.selected_row >= len(self.cell_grid):
            return
        if self.selected_col >= len(self.cell_grid[self.selected_row]):
            return
            
        key = self.cell_grid[self.selected_row][self.selected_col]
        cell = self.cells.get(key)
        if cell:
            cell.set_selected(selected)
    
    def _scroll_to_selected(self):
        """Scroll to make selected cell visible."""
        if not self.cell_grid:
            return
        if self.selected_row >= len(self.cell_grid):
            return
        if self.selected_col >= len(self.cell_grid[self.selected_row]):
            return
            
        key = self.cell_grid[self.selected_row][self.selected_col]
        cell = self.cells.get(key)
        if cell:
            cell.ensurePolished()
            # Find scroll area and ensure visible
            scroll = self.findChild(QScrollArea)
            if scroll:
                scroll.ensureWidgetVisible(cell)
    
    def _get_selected_key(self):
        """Get (bus, slot, param) tuple for selected cell."""
        if not self.cell_grid:
            return None
        if self.selected_row >= len(self.cell_grid):
            return None
        if self.selected_col >= len(self.cell_grid[self.selected_row]):
            return None
        return self.cell_grid[self.selected_row][self.selected_col]
    
    def _toggle_selected(self):
        """Toggle connection at selected cell."""
        key = self._get_selected_key()
        if key:
            self._on_cell_clicked(*key)
    
    def _remove_selected(self):
        """Remove connection at selected cell."""
        key = self._get_selected_key()
        if key:
            bus, slot, param = key
            self.routing_state.remove_connection(bus, slot, param)
    
    def _open_depth_popup_for_selected(self):
        """Open depth popup for selected cell."""
        key = self._get_selected_key()
        if key:
            self._on_cell_right_clicked(*key)
    
    def _set_selected_depth(self, depth: float):
        """Set depth for selected cell (creates connection if needed)."""
        key = self._get_selected_key()
        if not key:
            return
        
        bus, slot, param = key
        conn = self.routing_state.get_connection(bus, slot, param)
        
        if conn:
            self.routing_state.set_depth(bus, slot, param, depth)
        else:
            # Create new connection with this depth
            new_conn = ModConnection(
                source_bus=bus,
                target_slot=slot,
                target_param=param,
                depth=depth
            )
            self.routing_state.add_connection(new_conn)
    
    def _invert_selected_depth(self):
        """Toggle invert flag for selected cell."""
        key = self._get_selected_key()
        if not key:
            return
        
        bus, slot, param = key
        conn = self.routing_state.get_connection(bus, slot, param)
        
        if conn:
            self.routing_state.set_invert(bus, slot, param, not conn.invert)
    
    def _clear_selection(self):
        """Clear selection visual."""
        self._update_selection_visual(False)
    
    # ========================================
    # WINDOW SETTINGS PERSISTENCE
    # ========================================
    
    def _load_settings(self):
        """Load window geometry from settings."""
        settings = QSettings("NoiseEngine", "ModMatrix")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 550)
    
    def _save_settings(self):
        """Save window geometry to settings."""
        settings = QSettings("NoiseEngine", "ModMatrix")
        settings.setValue("geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Save settings when window closes."""
        self._save_settings()
        super().closeEvent(event)
    
    def showEvent(self, event):
        """Set initial selection when window is shown."""
        super().showEvent(event)
        # Set initial selection visual
        self._update_selection_visual(True)
        # Grab keyboard focus
        self.setFocus(Qt.OtherFocusReason)

