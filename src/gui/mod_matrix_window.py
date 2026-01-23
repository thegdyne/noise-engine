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

from PyQt5.QtWidgets import (QPushButton, 
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy, QApplication, QShortcut
, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QFont, QColor, QKeySequence

from .mod_matrix_cell import ModMatrixCell
from .mod_routing_state import ModRoutingState, ModConnection, Polarity
from .mod_connection_popup import ModConnectionPopup
from .theme import COLORS, FONT_FAMILY, FONT_SIZES, MONO_FONT


# Modulatable parameters per generator (key, short label)
GEN_PARAMS = [
    ('cutoff', 'CUT'),
    ('resonance', 'RES'),
    ('frequency', 'FRQ'),
    ('attack', 'ATK'),
    ('decay', 'DEC'),
    ('p1', 'P1'),
    ('p2', 'P2'),
    ('p3', 'P3'),
    ('p4', 'P4'),
    ('p5', 'P5'),
]

# Number of generator slots
NUM_GEN_SLOTS = 8

# Number of mod slots and outputs per slot
NUM_MOD_SLOTS = 4
OUTPUTS_PER_MOD_SLOT = 4

# Modulator P1-P4 params for cross-modulation
MOD_PARAMS = [
    ('p1', 'P1'),  # rate (all types)
    ('p2', 'P2'),  # globalWave/globalAtk/globalTension
    ('p3', 'P3'),  # pattern/globalRel/calm
    ('p4', 'P4'),  # globalPolarity (all types)
]

# Channel strip params  
CHAN_PARAMS = [
    ('ec', 'EC'),   # Echo send
    ('vb', 'VB'),   # Verb send
    ('pan', 'PAN'), # Pan
]

NUM_CHAN_SLOTS = 8

# Column counts
GEN_COLS = NUM_GEN_SLOTS * len(GEN_PARAMS)          # 80
MOD_COLS = NUM_MOD_SLOTS * len(MOD_PARAMS)          # 16  
CHAN_COLS = NUM_CHAN_SLOTS * len(CHAN_PARAMS)       # 24

# Total rows and columns for navigation
TOTAL_ROWS = NUM_MOD_SLOTS * OUTPUTS_PER_MOD_SLOT  # 16
TOTAL_COLS = GEN_COLS + MOD_COLS + CHAN_COLS        # 120

# Section background colors for alternating slots
SECTION_COLORS = {
    'gen': {'odd': '#1a1a1a', 'even': '#141414'},
    'mod': {'odd': '#1a1a22', 'even': '#14141a'},    # Blue tint
    'chan': {'odd': '#1a221a', 'even': '#141a14'},   # Green tint
}


class ModMatrixWindow(QMainWindow):
    """Matrix window for mod routing."""
    
    def __init__(self, routing_state: ModRoutingState, get_target_value_callback=None, parent=None):
        super().__init__(parent)
        
        self.routing_state = routing_state
        self.get_target_value = get_target_value_callback  # (slot_id, param) -> float 0-1
        self.cells = {}  # (bus, slot, param) -> ModMatrixCell
        self.cell_grid = []  # [row][col] -> (bus, slot, param) for navigation
        self.mod_slot_types = ['LFO', 'Sloth', 'LFO', 'Sloth']  # Default types
        
        # Selection state
        self.selected_row = 0
        self.selected_col = 0
        
        # Drag state
        self._dragging = False
        self._drag_start = None

        # Navigation timer for continuous movement
        self._nav_timer = QTimer(self)
        self._nav_timer.timeout.connect(self._on_nav_timer)
        self._nav_direction = (0, 0)  # (row_delta, col_delta)
        self._nav_step = 1  # Step size (modified by Shift/Ctrl)
        self._held_arrow = None
 
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
        self.sync_from_state()
        
        # Cmd+M to close (toggle) when this window has focus
        close_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        close_shortcut.activated.connect(self.hide)
        
    def _setup_ui(self):
        """Build the matrix UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        # Header row with title and ENGINE button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        
        title = QLabel("MOD ROUTING MATRIX")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_bright']}; padding: 5px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # ENGINE button - returns to main window (centered)
        engine_btn = QPushButton("ENGINE")
        engine_btn.setToolTip("Return to Engine (Ctrl+M)")
        engine_btn.setFixedSize(70, 27)
        engine_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: #ff6600;
                border: 1px solid #cc5500;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #331100;
                color: #ff6600;
                border-color: #ff6600;
            }}
        """)
        engine_btn.clicked.connect(self.hide)
        header_layout.addWidget(engine_btn)

        # CLEAR button - clears all mod routes (ADD HERE)
        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setToolTip("Clear all modulation routes")
        self.clear_btn.setFixedSize(55, 27)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: #ff4444;
                border: 1px solid #aa2222;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #330000;
                color: #ff6666;
                border-color: #ff4444;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['background']};
                color: #441111;
                border-color: #331111;
            }}
        """)
        self.clear_btn.clicked.connect(self._clear_all_routes)
        header_layout.addWidget(self.clear_btn)

        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
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

        # Extended Routes Section (new)
        # ext_section = self._build_extended_routes_section()
        # layout.addWidget(ext_section)
        
        # Legend
        legend = self._build_legend()
        layout.addWidget(legend)

    def _build_column_headers(self, layout: QGridLayout):
        """Build column headers: G1 CUT, G1 RES, G2 CUT, etc."""
        col = 1  # Start after row header column
        
        # Alternating tints for generator grouping
        gen_tints = {
            'odd': '#1a1a1a',    # Slightly lighter for odd generators (1,3,5,7)
            'even': '#141414',   # Darker for even generators (2,4,6,8)
        }
        
        for gen_slot in range(1, NUM_GEN_SLOTS + 1):
            tint = gen_tints['odd'] if gen_slot % 2 == 1 else gen_tints['even']
            
            for param_key, param_label in GEN_PARAMS:
                # Two-line header: "G1" / "CUT"
                header = QLabel(f"G{gen_slot}\n{param_label}")
                header.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
                header.setAlignment(Qt.AlignCenter)
                header.setFixedSize(28, 36)
                header.setStyleSheet(f"""
                    color: {COLORS['text']};
                    background-color: {tint};
                    border-bottom: 1px solid {COLORS['border']};
                """)
                layout.addWidget(header, 0, col)
                col += 1
            
            # Add separator after each generator's params
            if gen_slot < NUM_GEN_SLOTS:
                sep = QFrame()
                sep.setFixedWidth(3)
                sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
                layout.addWidget(sep, 0, col)
                col += 1
        
        # === SECTION SEPARATOR: Gen → Mod ===
        sep = QFrame()
        sep.setFixedWidth(6)
        sep.setStyleSheet(f"background-color: #333366; border: none;")
        layout.addWidget(sep, 0, col)
        col += 1
        
        # === MODULATOR COLUMNS (P1-P4) ===
        for mod_slot in range(1, NUM_MOD_SLOTS + 1):
            tint = SECTION_COLORS['mod']['odd'] if mod_slot % 2 == 1 else SECTION_COLORS['mod']['even']
            
            for param_key, param_label in MOD_PARAMS:
                header = QLabel(f"M{mod_slot}\n{param_label}")
                header.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
                header.setAlignment(Qt.AlignCenter)
                header.setFixedSize(28, 36)
                header.setStyleSheet(f"""
                    color: #8888cc;
                    background-color: {tint};
                    border-bottom: 1px solid {COLORS['border']};
                """)
                layout.addWidget(header, 0, col)
                col += 1
            
            if mod_slot < NUM_MOD_SLOTS:
                sep = QFrame()
                sep.setFixedWidth(3)
                sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
                layout.addWidget(sep, 0, col)
                col += 1
        
        # === SECTION SEPARATOR: Mod → Chan ===
        sep = QFrame()
        sep.setFixedWidth(6)
        sep.setStyleSheet(f"background-color: #336633; border: none;")
        layout.addWidget(sep, 0, col)
        col += 1
        
        # === CHANNEL STRIP COLUMNS ===
        for chan_slot in range(1, NUM_CHAN_SLOTS + 1):
            tint = SECTION_COLORS['chan']['odd'] if chan_slot % 2 == 1 else SECTION_COLORS['chan']['even']
            
            for param_key, param_label in CHAN_PARAMS:
                header = QLabel(f"C{chan_slot}\n{param_label}")
                header.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
                header.setAlignment(Qt.AlignCenter)
                header.setFixedSize(28, 36)
                header.setStyleSheet(f"""
                    color: #88cc88;
                    background-color: {tint};
                    border-bottom: 1px solid {COLORS['border']};
                """)
                layout.addWidget(header, 0, col)
                col += 1
            
            if chan_slot < NUM_CHAN_SLOTS:
                sep = QFrame()
                sep.setFixedWidth(3)
                sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
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
                        # R1.1: Shift+Click cycles polarity
                        cell.shift_clicked.connect(
                            lambda b=bus_idx, s=gen_slot, p=param_key: self._on_cell_shift_clicked(b, s, p)
                        )
                        layout.addWidget(cell, row, col)
                        self.cells[(bus_idx, gen_slot, param_key)] = cell
                        row_cells.append((bus_idx, gen_slot, param_key))
                        col += 1
                        nav_col += 1
                    
                    # Add vertical separator between generators
                    if gen_slot < NUM_GEN_SLOTS:
                        sep = QFrame()
                        sep.setFixedWidth(3)
                        sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
                        layout.addWidget(sep, row, col)
                        col += 1
                
                # === SECTION SEPARATOR: Gen → Mod ===
                sep = QFrame()
                sep.setFixedWidth(6)
                sep.setStyleSheet(f"background-color: #333366; border: none;")
                layout.addWidget(sep, row, col)
                col += 1
                
                # === MODULATOR CELLS (P1-P4) ===
                for target_mod_slot in range(1, NUM_MOD_SLOTS + 1):
                    for param_key, param_label in MOD_PARAMS:
                        target_str = f"mod:{target_mod_slot}:{param_key}"

                        cell = ModMatrixCell(bus_idx, target_mod_slot, param_key)
                        cell.set_source_type(slot_type)
                        cell._gen_tint = 'odd' if target_mod_slot % 2 == 1 else 'even'
                        cell.clicked.connect(
                            lambda b=bus_idx, ts=target_str: self._on_ext_cell_clicked(b, ts)
                        )
                        cell.right_clicked.connect(
                            lambda b=bus_idx, ts=target_str: self._on_ext_cell_right_clicked(b, ts)
                        )
                        # R1.1: Shift+Click cycles polarity
                        cell.shift_clicked.connect(
                            lambda b=bus_idx, ts=target_str: self._on_ext_cell_shift_clicked(b, ts)
                        )
                        layout.addWidget(cell, row, col)

                        key = (bus_idx, target_str)
                        self.cells[key] = cell
                        row_cells.append(key)
                        col += 1
                    
                    if target_mod_slot < NUM_MOD_SLOTS:
                        sep = QFrame()
                        sep.setFixedWidth(3)
                        sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
                        layout.addWidget(sep, row, col)
                        col += 1
                
                # === SECTION SEPARATOR: Mod → Chan ===
                sep = QFrame()
                sep.setFixedWidth(6)
                sep.setStyleSheet(f"background-color: #336633; border: none;")
                layout.addWidget(sep, row, col)
                col += 1
                
                # === CHANNEL STRIP CELLS ===
                for chan_slot in range(1, NUM_CHAN_SLOTS + 1):
                    for param_key, param_label in CHAN_PARAMS:
                        if param_key in ('ec', 'vb'):
                            target_str = f"send:{chan_slot}:{param_key}"
                        else:  # pan
                            target_str = f"chan:{chan_slot}:{param_key}"

                        cell = ModMatrixCell(bus_idx, chan_slot, param_key)
                        cell.set_source_type(slot_type)
                        cell._gen_tint = 'odd' if chan_slot % 2 == 1 else 'even'
                        cell.clicked.connect(
                            lambda b=bus_idx, ts=target_str: self._on_ext_cell_clicked(b, ts)
                        )
                        cell.right_clicked.connect(
                            lambda b=bus_idx, ts=target_str: self._on_ext_cell_right_clicked(b, ts)
                        )
                        # R1.1: Shift+Click cycles polarity
                        cell.shift_clicked.connect(
                            lambda b=bus_idx, ts=target_str: self._on_ext_cell_shift_clicked(b, ts)
                        )
                        layout.addWidget(cell, row, col)

                        key = (bus_idx, target_str)
                        self.cells[key] = cell
                        row_cells.append(key)
                        col += 1
                    
                    if chan_slot < NUM_CHAN_SLOTS:
                        sep = QFrame()
                        sep.setFixedWidth(3)
                        sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
                        layout.addWidget(sep, row, col)
                        col += 1
                
                self.cell_grid.append(row_cells)
                row += 1
                nav_row += 1
            
            # Add separator row between mod slots
            if mod_slot < NUM_MOD_SLOTS - 1:
                # col already has correct count after building all cells
                for c in range(col):
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
    
    def sync_from_state(self):
        """Sync cell states from routing state."""
        for conn in self.routing_state.get_all_connections():
            if conn.is_extended:
                key = (conn.source_bus, conn.target_str)
            else:
                key = (conn.source_bus, conn.target_slot, conn.target_param)
            
            cell = self.cells.get(key)
            if cell:
                cell.set_connection(True, conn.amount)

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

    def _on_cell_shift_clicked(self, bus: int, slot: int, param: str):
        """
        R1.1: Handle Shift+Click on generator cell - cycle polarity.

        Per spec: BI → UNI → INV → BI
        Mapping: BIPOLAR (0) → UNI_POS (1) → UNI_NEG (2) → BIPOLAR (0)

        Only affects existing connections; no-op if cell has no routing.
        """
        conn = self.routing_state.get_connection(bus, slot, param)
        if not conn:
            return  # No routing, no-op

        # Cycle polarity: BIPOLAR → UNI_POS → UNI_NEG → BIPOLAR
        current = conn.polarity
        if current == Polarity.BIPOLAR:
            new_polarity = Polarity.UNI_POS
        elif current == Polarity.UNI_POS:
            new_polarity = Polarity.UNI_NEG
        else:  # UNI_NEG
            new_polarity = Polarity.BIPOLAR

        self.routing_state.set_polarity(bus, slot, param, new_polarity)

    def _on_ext_cell_shift_clicked(self, bus: int, target_str: str):
        """
        R1.1: Handle Shift+Click on extended cell - cycle polarity.

        Per spec: BI → UNI → INV → BI
        Only affects existing connections; no-op if cell has no routing.
        """
        conn = self.routing_state.get_connection(bus, target_str=target_str)
        if not conn:
            return  # No routing, no-op

        # Cycle polarity: BIPOLAR → UNI_POS → UNI_NEG → BIPOLAR
        current = conn.polarity
        if current == Polarity.BIPOLAR:
            new_polarity = Polarity.UNI_POS
        elif current == Polarity.UNI_POS:
            new_polarity = Polarity.UNI_NEG
        else:  # UNI_NEG
            new_polarity = Polarity.BIPOLAR

        self.routing_state.update_connection(bus, target_str=target_str, polarity=new_polarity)

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
        
        # Close any existing popup
        if hasattr(self, '_open_popup') and self._open_popup:
            self._open_popup.close()
        
        # Show popup with target value callback
        popup = ModConnectionPopup(
            conn, source_label, target_label, 
            get_target_value=lambda: self.get_target_value(slot, param) if self.get_target_value else 0.5,
            parent=self
        )
        popup.connection_changed.connect(
            lambda c, b=bus, s=slot, p=param: self._on_popup_connection_changed(b, s, p, c)
        )
        popup.remove_requested.connect(
            lambda b=bus, s=slot, p=param: self._on_popup_remove(b, s, p)
        )
        popup.finished.connect(self._on_popup_closed)
        
        # Store reference so keyboard changes can update it
        self._open_popup = popup
        
        # Position popup near the cell
        cell = self.cells.get((bus, slot, param))
        if cell:
            global_pos = cell.mapToGlobal(cell.rect().center())
            popup.move(global_pos.x() + 20, global_pos.y() - 50)
        
        popup.show()
    
    def _on_popup_closed(self):
        """Clear popup reference when closed."""
        self._open_popup = None
    
    def _on_popup_connection_changed(self, bus: int, slot: int, param: str, conn: ModConnection):
        """Handle connection change from popup (depth, amount, offset, polarity, invert)."""
        self.routing_state.update_connection(
            bus, slot, param,
            depth=conn.depth,
            amount=conn.amount,
            offset=conn.offset,
            polarity=conn.polarity,
            invert=conn.invert
        )
    
    def _on_popup_remove(self, bus: int, slot: int, param: str):
        """Handle remove from popup."""
        self.routing_state.remove_connection(bus, slot, param)
    
    def _on_ext_cell_clicked(self, bus: int, target_str: str):
        """Handle extended cell left-click: toggle connection."""
        key = (bus, target_str)
        self._select_cell_by_key(key)
        
        conn = self.routing_state.get_connection(bus, target_str=target_str)
        
        if conn:
            self.routing_state.remove_connection(bus, target_str=target_str)
        else:
            new_conn = ModConnection(
                source_bus=bus,
                target_str=target_str,
                depth=1.0,
                amount=0.5
            )
            self.routing_state.add_connection(new_conn)
    
    def _on_ext_cell_right_clicked(self, bus: int, target_str: str):
        """Handle extended cell right-click: show depth popup."""
        key = (bus, target_str)
        self._select_cell_by_key(key)
        
        conn = self.routing_state.get_connection(bus, target_str=target_str)
        
        if not conn:
            conn = ModConnection(
                source_bus=bus,
                target_str=target_str,
                depth=1.0,
                amount=0.5
            )
            self.routing_state.add_connection(conn)
        
        # Get source label
        mod_slot = bus // OUTPUTS_PER_MOD_SLOT
        output_idx = bus % OUTPUTS_PER_MOD_SLOT
        slot_type = self.mod_slot_types[mod_slot]
        output_labels = self._get_output_labels(slot_type)
        source_label = f"M{mod_slot + 1}.{output_labels[output_idx]}"
        
        # Get target label
        target_label = self._get_ext_target_label(target_str)
        
        # Close existing popup
        if hasattr(self, '_open_popup') and self._open_popup:
            self._open_popup.close()
        
        popup = ModConnectionPopup(
            conn, source_label, target_label,
            get_target_value=None,
            parent=self
        )
        popup.connection_changed.connect(
            lambda c, ts=target_str: self._on_ext_popup_connection_changed(bus, ts, c)
        )
        popup.remove_requested.connect(
            lambda ts=target_str: self._on_ext_popup_remove(bus, ts)
        )
        popup.finished.connect(self._on_popup_closed)
        
        self._open_popup = popup
        
        cell = self.cells.get(key)
        if cell:
            global_pos = cell.mapToGlobal(cell.rect().center())
            popup.move(global_pos.x() + 20, global_pos.y() - 50)
        
        popup.show()
    
    def _on_ext_popup_connection_changed(self, bus: int, target_str: str, conn: ModConnection):
        """Handle extended connection change from popup."""
        self.routing_state.update_connection(
            bus, target_str=target_str,
            depth=conn.depth,
            amount=conn.amount,
            offset=conn.offset,
            polarity=conn.polarity,
            invert=conn.invert
        )
    
    def _on_ext_popup_remove(self, bus: int, target_str: str):
        """Handle extended remove from popup."""
        self.routing_state.remove_connection(bus, target_str=target_str)
    
    def _select_cell_by_key(self, key):
        """Update selection to cell by key (tuple or extended)."""
        self._update_selection_visual(False)
        
        for row_idx, row_cells in enumerate(self.cell_grid):
            for col_idx, cell_key in enumerate(row_cells):
                if cell_key == key:
                    self.selected_row = row_idx
                    self.selected_col = col_idx
                    self._update_selection_visual(True)
                    return

    def _on_connection_added(self, conn: ModConnection):
        """Update cell when connection added."""
        if conn.is_extended:
            key = (conn.source_bus, conn.target_str)
            print(f"[DEBUG] Extended connection added: key={key}")
        else:
            key = (conn.source_bus, conn.target_slot, conn.target_param)

        cell = self.cells.get(key)
        print(f"[DEBUG] Cell lookup: key={key}, found={cell is not None}")
        if cell:
            cell.set_connection(True, conn.amount)

        # Update ext routes list if extended
        if conn.is_extended:
            self._update_ext_routes_list()

    def _on_connection_removed(self, conn):
        """Update cell when connection removed."""
        if conn.is_extended:
            key = (conn.source_bus, conn.target_str)
        else:
            key = (conn.source_bus, conn.target_slot, conn.target_param)
        
        cell = self.cells.get(key)
        if cell:
            cell.set_connection(False)
        
        # Close popup if it was showing this connection
        if hasattr(self, '_open_popup') and self._open_popup:
            self._open_popup.close()
        
        # Update ext routes list if extended
        if conn.is_extended:
            self._update_ext_routes_list()
    
    def _on_connection_changed(self, conn: ModConnection):
        """Update cell and popup when connection parameters change."""
        if conn.is_extended:
            key = (conn.source_bus, conn.target_str)
        else:
            key = (conn.source_bus, conn.target_slot, conn.target_param)
        
        cell = self.cells.get(key)
        if cell:
            cell.set_connection(True, conn.amount)
        
        # Sync popup if open
        if hasattr(self, '_open_popup') and self._open_popup:
            self._open_popup.sync_from_state(conn)
    
    def _on_all_cleared(self):
        """Clear all cells when routing cleared."""
        for cell in self.cells.values():
            cell.set_connection(False)
        # Close popup if open
        if hasattr(self, '_open_popup') and self._open_popup:
            self._open_popup.close()

    def _clear_all_routes(self):
        """Clear all modulation routes."""
        self.routing_state.clear()

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
                
                # Update ALL cell colours for this row (gen, mod, chan)
                for key, cell in self.cells.items():
                    if key[0] == bus_idx:
                        cell.set_source_type(slot_type)
    
    # ========================================
    # KEYBOARD NAVIGATION
    # ========================================
    
    def keyPressEvent(self, event):
        """Handle keyboard input for navigation and actions."""
        key = event.key()
        modifiers = event.modifiers()
        
        # Navigation step size:
        # - Normal: 1 cell
        # - Shift: 5 cells (half a generator)
        # - Ctrl/Cmd: 10 cols (full generator) or 4 rows (full mod slot)
        ctrl_held = modifiers & (Qt.ControlModifier | Qt.MetaModifier)  # Ctrl or Cmd
        shift_held = modifiers & Qt.ShiftModifier
        
        # Arrow keys: start/continue navigation
        if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            if key == Qt.Key_Up:
                step = 4 if ctrl_held else (5 if shift_held else 1)
                self._nav_direction = (-step, 0)
            elif key == Qt.Key_Down:
                step = 4 if ctrl_held else (5 if shift_held else 1)
                self._nav_direction = (step, 0)
            elif key == Qt.Key_Left:
                step = 10 if ctrl_held else (5 if shift_held else 1)
                self._nav_direction = (0, -step)
            elif key == Qt.Key_Right:
                step = 10 if ctrl_held else (5 if shift_held else 1)
                self._nav_direction = (0, step)
            
            self._held_arrow = key
            self._move_selection(*self._nav_direction)
            self._nav_timer.start(100)
 
        # Space: toggle connection
        elif key == Qt.Key_Space:
            self._toggle_selected()
        
        # Delete/Backspace: remove connection
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self._remove_selected()
        
        # D: open connection popup
        elif key == Qt.Key_D:
            self._open_depth_popup_for_selected()
        
        # 1-9: set amount (10%-90%)
        elif Qt.Key_1 <= key <= Qt.Key_9:
            value = (key - Qt.Key_0) / 10.0  # 0.1 to 0.9
            self._set_selected_amount(value)
        
        # 0: set amount to 100%
        elif key == Qt.Key_0:
            self._set_selected_amount(1.0)

        # Shifted number keys (Shift held for fine navigation)
        elif key == Qt.Key_Exclam:      self._set_selected_amount(0.1)  # Shift+1
        elif key == Qt.Key_At:          self._set_selected_amount(0.2)  # Shift+2
        elif key == Qt.Key_NumberSign:  self._set_selected_amount(0.3)  # Shift+3
        elif key == Qt.Key_Dollar:      self._set_selected_amount(0.4)  # Shift+4
        elif key == Qt.Key_Percent:     self._set_selected_amount(0.5)  # Shift+5
        elif key == Qt.Key_AsciiCircum: self._set_selected_amount(0.6)  # Shift+6
        elif key == Qt.Key_Ampersand:   self._set_selected_amount(0.7)  # Shift+7
        elif key == Qt.Key_Asterisk:    self._set_selected_amount(0.8)  # Shift+8
        elif key == Qt.Key_ParenLeft:   self._set_selected_amount(0.9)  # Shift+9
        elif key == Qt.Key_ParenRight:  self._set_selected_amount(1.0)  # Shift+0 

        # Shift + -/+ : adjust offset
        elif key == Qt.Key_Underscore:  # Shift + minus
            self._adjust_selected_offset(-10)
        elif key == Qt.Key_Plus:        # Shift + equals
            self._adjust_selected_offset(10)        

        # Escape: deselect
        elif key == Qt.Key_Escape:
            self._clear_selection()
        
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Stop navigation timer when arrow released."""
        if event.key() == self._held_arrow:
            self._nav_timer.stop()
            self._held_arrow = None
        super().keyReleaseEvent(event)

    def _on_nav_timer(self):
        """Continue movement while arrow held."""
        if self._held_arrow:
            self._move_selection(*self._nav_direction)
 
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

    def _set_selected_amount(self, amount: float):
        """Set amount for selected cell (creates connection if needed)."""
        key = self._get_selected_key()
        if not key:
            return

        if len(key) == 3:
            # Generator route: (bus, slot, param)
            bus, slot, param = key
            conn = self.routing_state.get_connection(bus, slot, param)

            if conn:
                self.routing_state.set_amount(bus, slot, param, amount)
            else:
                new_conn = ModConnection(
                    source_bus=bus,
                    target_slot=slot,
                    target_param=param,
                    amount=amount
                )
                self.routing_state.add_connection(new_conn)
        else:
            # Extended route: (bus, target_str)
            bus, target_str = key
            conn = self.routing_state.get_connection(bus, target_str=target_str)

            if conn:
                self.routing_state.update_connection(bus, target_str=target_str, amount=amount)
            else:
                new_conn = ModConnection(
                    source_bus=bus,
                    target_str=target_str,
                    amount=amount
                )
                self.routing_state.add_connection(new_conn)

    def _adjust_selected_offset(self, delta: int):
        """Adjust offset for selected cell by delta (-10 or +10)."""
        key = self._get_selected_key()
        if not key:
            return

        if len(key) == 3:
            # Generator route: (bus, slot, param)
            bus, slot, param = key
            conn = self.routing_state.get_connection(bus, slot, param)

            if conn:
                current = int(conn.offset * 100)
                new_offset = max(-100, min(100, current + delta))
                self.routing_state.set_offset(bus, slot, param, new_offset / 100.0)
        else:
            # Extended route: (bus, target_str)
            bus, target_str = key
            conn = self.routing_state.get_connection(bus, target_str=target_str)

            if conn:
                current = int(conn.offset * 100)
                new_offset = max(-100, min(100, current + delta))
                self.routing_state.update_connection(bus, target_str=target_str, offset=new_offset / 100.0)

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
    
    def _build_extended_routes_section(self):
        """Build the extended routes management section."""
        from PyQt5.QtWidgets import QGroupBox, QListWidget, QListWidgetItem
        
        group = QGroupBox("Extended Routes (FX / Modulators / Sends)")
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
                font-family: '{MONO_FONT}';
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Top row: Add button + counter
        top_layout = QHBoxLayout()
        
        self.add_ext_route_btn = QPushButton("+ Add Extended Route")
        self.add_ext_route_btn.setFixedHeight(28)
        self.add_ext_route_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['enabled']};
                color: {COLORS['background']};
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-family: '{MONO_FONT}';
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['enabled_hover']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['background_light']};
            }}
        """)
        self.add_ext_route_btn.clicked.connect(self._on_add_extended_route_clicked)
        top_layout.addWidget(self.add_ext_route_btn)
        
        top_layout.addStretch()
        
        self.ext_route_counter = QLabel("0 extended routes")
        self.ext_route_counter.setStyleSheet(f"color: {COLORS['text']}; font-size: {FONT_SIZES['small']}px;")
        top_layout.addWidget(self.ext_route_counter)
        
        layout.addLayout(top_layout)
        
        # List of extended routes
        self.ext_routes_list = QListWidget()
        self.ext_routes_list.setFixedHeight(120)
        self.ext_routes_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['background_light']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                font-family: '{MONO_FONT}';
                font-size: {FONT_SIZES['small']}px;
                padding: 2px;
            }}
            QListWidget::item {{
                padding: 4px;
                border-radius: 2px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['background_highlight']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['background_light']};
                color: {COLORS['text_bright']};
            }}
        """)
        self.ext_routes_list.itemDoubleClicked.connect(self._on_ext_route_double_clicked)
        layout.addWidget(self.ext_routes_list)
        
        return group
    
    def _on_add_extended_route_clicked(self):
        """Open popup to create a new extended route."""
        from .mod_connection_popup_ext import ExtModConnectionPopup
        
        # Close any existing popup
        if hasattr(self, '_open_ext_popup') and self._open_ext_popup:
            self._open_ext_popup.close()
        
        # Show source selection popup (for now, just use mod slot 1, bus A = 0)
        # TODO: Add source selection dialog
        source_bus = 0  # M1.A for testing
        source_label = "M1.A"
        
        popup = ExtModConnectionPopup(
            source_bus=source_bus,
            source_label=source_label,
            connection=None,  # Create mode
            parent=self
        )
        popup.connection_created.connect(self._on_ext_route_created)
        popup.show()
        
        self._open_ext_popup = popup
    
    def _on_ext_route_created(self, conn):
        """Handle new extended route creation."""
        # Add to routing state (will trigger OSC via modulation_controller)
        self.routing_state.add_connection(conn)
        
        # Update the list
        self._update_ext_routes_list()
    
    def _on_ext_route_double_clicked(self, item):
        """Open edit popup for an extended route."""
        from .mod_connection_popup_ext import ExtModConnectionPopup
        
        # Extract connection from item data
        conn = item.data(Qt.UserRole)
        if not conn:
            return
        
        # Get source label
        mod_slot = conn.source_bus // 4
        output_idx = conn.source_bus % 4
        output_labels = ['A', 'B', 'C', 'D']
        source_label = f"M{mod_slot + 1}.{output_labels[output_idx]}"
        
        # Close any existing popup
        if hasattr(self, '_open_ext_popup') and self._open_ext_popup:
            self._open_ext_popup.close()
        
        popup = ExtModConnectionPopup(
            source_bus=conn.source_bus,
            source_label=source_label,
            connection=conn,  # Edit mode
            parent=self
        )
        popup.connection_changed.connect(lambda c: self._update_ext_routes_list())
        popup.remove_requested.connect(lambda: self._on_ext_route_remove_requested(conn))
        popup.show()
        
        self._open_ext_popup = popup
    
    def _on_ext_route_remove_requested(self, conn):
        """Remove an extended route."""
        self.routing_state.remove_connection(
            conn.source_bus,
            target_str=conn.target_str
        )
        self._update_ext_routes_list()

    def _update_ext_routes_list(self):
        """Refresh the extended routes list widget."""
        if not hasattr(self, 'ext_routes_list'):
            return  # Section hidden - using grid columns instead
        self.ext_routes_list.clear()

        ext_conns = self.routing_state.get_extended_connections()
        
        # Update counter
        self.ext_route_counter.setText(f"{len(ext_conns)} extended route{'s' if len(ext_conns) != 1 else ''}")
        
        # Populate list
        for conn in ext_conns:
            # Get source label
            mod_slot = conn.source_bus // 4
            output_idx = conn.source_bus % 4
            output_labels = ['A', 'B', 'C', 'D']
            source_label = f"M{mod_slot + 1}.{output_labels[output_idx]}"
            
            # Get target label
            target_label = self._get_ext_target_label(conn.target_str)
            
            # Format: "M1.A → HEAT Drive [50%]"
            text = f"{source_label} → {target_label} [{int(conn.amount * 100)}%]"
            
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, conn)  # Store connection for later
            self.ext_routes_list.addItem(item)
    
    def _get_ext_target_label(self, target_str: str) -> str:
        """Convert target string to human-readable label."""
        parts = target_str.split(':')
        if len(parts) < 3:
            return target_str
        
        target_type, identifier, param = parts[0], parts[1], parts[2]
        
        if target_type == 'fx':
            fx_labels = {'heat': 'HEAT', 'echo': 'ECHO', 'reverb': 'REVERB', 'dual_filter': 'DUAL_FILTER'}
            fx_name = fx_labels.get(identifier, identifier.upper())
            param_label = param.replace('_', ' ').title()
            return f"{fx_name} {param_label}"
        
        elif target_type == 'mod':
            param_labels = {'p1': 'P1', 'p2': 'P2', 'p3': 'P3', 'p4': 'P4'}
            param_label = param_labels.get(param, param.upper())
            return f"M{identifier} {param_label}"
        
        elif target_type == 'send':
            send_labels = {'ec': 'Echo', 'vb': 'Verb'}
            send_name = send_labels.get(param, param.upper())
            return f"C{identifier} {send_name}"
        
        elif target_type == 'chan':
            param_labels = {'pan': 'Pan'}
            param_label = param_labels.get(param, param.upper())
            return f"C{identifier} {param_label}"
        
        return target_str

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

