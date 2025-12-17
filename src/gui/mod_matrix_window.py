"""
Mod Matrix Window
Visual matrix for creating modulation routing connections.

Layout:
- Rows: 16 mod buses (4 slots × 4 outputs)
- Columns: Generator parameters (8 slots × key params)
- Click cell to toggle connection
- Right-click for depth popup (Phase 5)

Row labels update dynamically based on mod slot types (LFO/Sloth).
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from .mod_matrix_cell import ModMatrixCell
from .mod_routing_state import ModRoutingState, ModConnection
from .mod_depth_popup import ModDepthPopup
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


class ModMatrixWindow(QMainWindow):
    """Matrix window for mod routing."""
    
    def __init__(self, routing_state: ModRoutingState, parent=None):
        super().__init__(parent)
        
        self.routing_state = routing_state
        self.cells = {}  # (bus, slot, param) -> ModMatrixCell
        self.mod_slot_types = ['LFO', 'Sloth', 'LFO', 'Sloth']  # Default types
        
        self.setWindowTitle("Mod Matrix")
        self.setMinimumSize(800, 500)
        self.resize(1000, 550)
        
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
        
        # Matrix container
        matrix_widget = QWidget()
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
                        col += 1
                    
                    # Skip separator column
                    if gen_slot < NUM_GEN_SLOTS:
                        col += 1
                
                row += 1
            
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
        instructions = QLabel("Click: toggle  •  Right-click: adjust depth")
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
                cell.set_connection(True, conn.depth, conn.enabled)
    
    def _on_cell_clicked(self, bus: int, slot: int, param: str):
        """Handle cell left-click: toggle connection."""
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
                depth=0.5,
                enabled=True
            )
            self.routing_state.add_connection(new_conn)
    
    def _on_cell_right_clicked(self, bus: int, slot: int, param: str):
        """Handle cell right-click: show depth popup for existing connection, or create new."""
        conn = self.routing_state.get_connection(bus, slot, param)
        
        if not conn:
            # No connection - create one first, then open popup
            conn = ModConnection(
                source_bus=bus,
                target_slot=slot,
                target_param=param,
                depth=0.5,
                enabled=True
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
        popup = ModDepthPopup(conn, source_label, target_label, self)
        popup.depth_changed.connect(
            lambda d, b=bus, s=slot, p=param: self._on_popup_depth_changed(b, s, p, d)
        )
        popup.enable_toggled.connect(
            lambda e, b=bus, s=slot, p=param: self._on_popup_enable_toggled(b, s, p, e)
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
    
    def _on_popup_depth_changed(self, bus: int, slot: int, param: str, depth: float):
        """Handle depth change from popup."""
        self.routing_state.set_depth(bus, slot, param, depth)
    
    def _on_popup_enable_toggled(self, bus: int, slot: int, param: str, enabled: bool):
        """Handle enable toggle from popup."""
        self.routing_state.set_enabled(bus, slot, param, enabled)
    
    def _on_popup_remove(self, bus: int, slot: int, param: str):
        """Handle remove from popup."""
        self.routing_state.remove_connection(bus, slot, param)
    
    def _on_connection_added(self, conn: ModConnection):
        """Update cell when connection added."""
        cell = self.cells.get((conn.source_bus, conn.target_slot, conn.target_param))
        if cell:
            cell.set_connection(True, conn.depth, conn.enabled)
    
    def _on_connection_removed(self, source_bus: int, target_slot: int, target_param: str):
        """Update cell when connection removed."""
        cell = self.cells.get((source_bus, target_slot, target_param))
        if cell:
            cell.set_connection(False)
    
    def _on_connection_changed(self, conn: ModConnection):
        """Update cell when connection depth/enabled changes."""
        cell = self.cells.get((conn.source_bus, conn.target_slot, conn.target_param))
        if cell:
            cell.set_connection(True, conn.depth, conn.enabled)
    
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
