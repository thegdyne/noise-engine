"""
Crossmod Matrix Window
Visual matrix for creating generator-to-generator cross-modulation routing.

Layout:
- Rows: 8 source generators (with enable checkbox)
- Columns: 80 target params (8 slots × 10 params)
- Click cell to toggle connection
- Shift+click for inverted connection
- Right-click for connection popup

Keyboard:
- Arrow keys: Navigate cells
- Space: Toggle connection
- Shift+Space: Toggle with invert
- Delete/Backspace: Remove connection
- D: Open connection popup
- I: Toggle invert on existing connection
- 1-9: Quick amount (10%-90%)
- 0: Set amount 100%
- Escape: Deselect
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QPushButton, QCheckBox, QShortcut,
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QFont, QColor, QKeySequence

from .crossmod_matrix_cell import CrossmodMatrixCell
from .crossmod_routing_state import CrossmodRoutingState, CrossmodConnection
from .crossmod_connection_popup import CrossmodConnectionPopup

# Import theme if available, otherwise use defaults
try:
    from .theme import COLORS, FONT_FAMILY, FONT_SIZES, MONO_FONT
except ImportError:
    COLORS = {
        'background': '#1a1a1a',
        'background_light': '#2a2a2a',
        'text': '#cccccc',
        'text_bright': '#ffffff',
        'text_dim': '#888888',
        'border': '#444444',
    }
    FONT_FAMILY = 'Arial'
    FONT_SIZES = {'small': 10, 'normal': 11, 'section': 12, 'micro': 8}
    MONO_FONT = 'Courier New'


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

# Number of generators
NUM_GENS = 8

# Total rows and columns for navigation
TOTAL_ROWS = NUM_GENS                           # 8
TOTAL_COLS = NUM_GENS * len(GEN_PARAMS)         # 80 (8 slots × 10 params)


class CrossmodMatrixWindow(QMainWindow):
    """Matrix window for crossmod routing."""
    
    def __init__(self, routing_state: CrossmodRoutingState, parent=None):
        super().__init__(parent)
        
        self.routing_state = routing_state
        self.cells = {}  # (source, target, param) -> CrossmodMatrixCell
        self.cell_grid = []  # [row][col] -> (source, target, param) for navigation
        self.row_checkboxes = {}  # source_gen -> QCheckBox
        
        # Selection state
        self.selected_row = 0
        self.selected_col = 0
        
        # Navigation timer for continuous movement
        self._nav_timer = QTimer(self)
        self._nav_timer.timeout.connect(self._on_nav_timer)
        self._nav_direction = (0, 0)
        self._held_arrow = None
        
        # Open popup reference
        self._open_popup = None
        
        self.setWindowTitle("CROSSMOD MATRIX")
        self.setMinimumSize(800, 400)
        
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
        
        # Ctrl+X to toggle (close) when this window has focus
        close_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        close_shortcut.activated.connect(self.hide)
        
        # Ctrl+M also returns to engine
        engine_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        engine_shortcut.activated.connect(self.hide)
    
    def _setup_ui(self):
        """Build the matrix UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        # Header row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        
        title = QLabel("CROSSMOD MATRIX")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_bright']}; padding: 5px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # ENGINE button
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
        
        # CLEAR button
        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setToolTip("Clear all crossmod routes")
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
        scroll.setFocusPolicy(Qt.NoFocus)
        
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
        
        # Alternating tints for generator grouping
        gen_tints = {
            'odd': '#1a1a1a',
            'even': '#141414',
        }
        
        for gen_slot in range(1, NUM_GENS + 1):
            tint = gen_tints['odd'] if gen_slot % 2 == 1 else gen_tints['even']
            
            for param_key, param_label in GEN_PARAMS:
                # Two-line header: "G1" / "CUT"
                header = QLabel(f"G{gen_slot}\n{param_label}")
                header.setFont(QFont(MONO_FONT, FONT_SIZES.get('micro', 8)))
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
            if gen_slot < NUM_GENS:
                sep = QFrame()
                sep.setFixedWidth(3)
                sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
                layout.addWidget(sep, 0, col)
                col += 1
    
    def _build_rows(self, layout: QGridLayout):
        """Build row headers (with checkboxes) and cell grid."""
        row = 1  # Start after column headers
        
        for source_gen in range(1, NUM_GENS + 1):
            # Row header container with checkbox
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(2, 0, 4, 0)
            header_layout.setSpacing(2)
            
            # Enable checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox.setToolTip(f"Enable follower for Gen {source_gen}")
            checkbox.stateChanged.connect(
                lambda state, sg=source_gen: self._on_follower_checkbox_changed(sg, state)
            )
            self.row_checkboxes[source_gen] = checkbox
            header_layout.addWidget(checkbox)
            
            # Label
            label = QLabel(f"GEN {source_gen}")
            label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            color = CrossmodMatrixCell.SOURCE_COLORS.get(source_gen, '#666666')
            label.setStyleSheet(f"color: {color};")
            header_layout.addWidget(label)
            
            header_widget.setFixedSize(75, 24)
            layout.addWidget(header_widget, row, 0)
            
            # Cells for this row
            col = 1
            row_cells = []
            
            for target_gen in range(1, NUM_GENS + 1):
                for param_key, param_label in GEN_PARAMS:
                    cell = CrossmodMatrixCell(source_gen, target_gen, param_key)
                    cell.clicked.connect(
                        lambda sg=source_gen, tg=target_gen, p=param_key: self._on_cell_clicked(sg, tg, p)
                    )
                    cell.shift_clicked.connect(
                        lambda sg=source_gen, tg=target_gen, p=param_key: self._on_cell_shift_clicked(sg, tg, p)
                    )
                    cell.right_clicked.connect(
                        lambda sg=source_gen, tg=target_gen, p=param_key: self._on_cell_right_clicked(sg, tg, p)
                    )
                    layout.addWidget(cell, row, col)
                    self.cells[(source_gen, target_gen, param_key)] = cell
                    row_cells.append((source_gen, target_gen, param_key))
                    col += 1
                
                # Add vertical separator between target generators
                if target_gen < NUM_GENS:
                    sep = QFrame()
                    sep.setFixedWidth(3)
                    sep.setStyleSheet(f"background-color: {COLORS['background']}; border: none;")
                    layout.addWidget(sep, row, col)
                    col += 1
            
            self.cell_grid.append(row_cells)
            row += 1
            
            # Add separator row between source generators
            if source_gen < NUM_GENS:
                sep_col = 0
                total_cols = 1 + NUM_GENS * len(GEN_PARAMS) + (NUM_GENS - 1)
                for c in range(total_cols):
                    sep = QFrame()
                    sep.setFixedHeight(2)
                    sep.setStyleSheet(f"background-color: {COLORS['border']};")
                    layout.addWidget(sep, row, c)
                row += 1
    
    def _build_legend(self) -> QWidget:
        """Build legend showing source generator colors."""
        legend = QWidget()
        layout = QHBoxLayout(legend)
        layout.setContentsMargins(5, 5, 5, 5)
        
        layout.addStretch()
        
        label = QLabel("Source:")
        label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(label)
        
        for gen in range(1, NUM_GENS + 1):
            color = CrossmodMatrixCell.SOURCE_COLORS.get(gen, '#666666')
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            layout.addWidget(dot)
            gen_label = QLabel(f"G{gen}")
            gen_label.setStyleSheet(f"color: {COLORS['text']}; margin-right: 8px;")
            layout.addWidget(gen_label)
        
        # Invert indicator
        layout.addWidget(QLabel("  |  "))
        invert_dot = QLabel("◐")  # Half-moon for invert
        invert_dot.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        layout.addWidget(invert_dot)
        invert_label = QLabel("= inverted")
        invert_label.setStyleSheet(f"color: {COLORS['text_dim']}; margin-right: 15px;")
        layout.addWidget(invert_label)
        
        layout.addStretch()
        
        return legend
    
    def _on_follower_checkbox_changed(self, source_gen: int, state: int):
        """Handle row enable checkbox change."""
        enabled = (state == Qt.Checked)
        self.routing_state.set_follower_enabled(source_gen, enabled)
    
    def _connect_signals(self):
        """Connect to routing state signals."""
        self.routing_state.connection_added.connect(self._on_connection_added)
        self.routing_state.connection_removed.connect(self._on_connection_removed)
        self.routing_state.connection_changed.connect(self._on_connection_changed)
        self.routing_state.all_cleared.connect(self._on_all_cleared)
        self.routing_state.follower_changed.connect(self._on_follower_state_changed)
    
    def sync_from_state(self):
        """Sync cell states from routing state."""
        for conn in self.routing_state.get_all_connections():
            cell = self.cells.get((conn.source_gen, conn.target_gen, conn.target_param))
            if cell:
                cell.set_connection(True, conn.amount, conn.invert)
        
        # Sync follower checkboxes
        for source_gen in range(1, NUM_GENS + 1):
            enabled = self.routing_state.is_follower_enabled(source_gen)
            if source_gen in self.row_checkboxes:
                self.row_checkboxes[source_gen].blockSignals(True)
                self.row_checkboxes[source_gen].setChecked(enabled)
                self.row_checkboxes[source_gen].blockSignals(False)
    
    def _on_cell_clicked(self, source: int, target: int, param: str):
        """Handle cell left-click: toggle connection."""
        self._select_cell(source, target, param)
        
        conn = self.routing_state.get_connection(source, target, param)
        
        if conn:
            # Remove existing connection
            self.routing_state.remove_connection(source, target, param)
        else:
            # Check for prior state to restore
            prior = self.routing_state.get_prior_state(source, target, param)
            if prior:
                # Restore prior state
                new_conn = CrossmodConnection(
                    source_gen=source,
                    target_gen=target,
                    target_param=param,
                    amount=prior.amount,
                    offset=prior.offset,
                    invert=prior.invert
                )
            else:
                # New connection with defaults
                new_conn = CrossmodConnection(
                    source_gen=source,
                    target_gen=target,
                    target_param=param,
                    amount=0.5,
                    offset=0.0,
                    invert=False
                )
            self.routing_state.add_connection(new_conn)
    
    def _on_cell_shift_clicked(self, source: int, target: int, param: str):
        """Handle shift+click: toggle with invert flipped."""
        self._select_cell(source, target, param)
        
        conn = self.routing_state.get_connection(source, target, param)
        
        if conn:
            # Already connected - just toggle invert
            self.routing_state.toggle_invert(source, target, param)
        else:
            # Create new connection with invert=True
            prior = self.routing_state.get_prior_state(source, target, param)
            if prior:
                new_conn = CrossmodConnection(
                    source_gen=source,
                    target_gen=target,
                    target_param=param,
                    amount=prior.amount,
                    offset=prior.offset,
                    invert=not prior.invert  # Flip from prior
                )
            else:
                new_conn = CrossmodConnection(
                    source_gen=source,
                    target_gen=target,
                    target_param=param,
                    amount=0.5,
                    offset=0.0,
                    invert=True  # Default to inverted
                )
            self.routing_state.add_connection(new_conn)
    
    def _select_cell(self, source: int, target: int, param: str):
        """Update selection to specific cell."""
        self._update_selection_visual(False)
        
        for row_idx, row_cells in enumerate(self.cell_grid):
            for col_idx, key in enumerate(row_cells):
                if key == (source, target, param):
                    self.selected_row = row_idx
                    self.selected_col = col_idx
                    self._update_selection_visual(True)
                    return
    
    def _on_cell_right_clicked(self, source: int, target: int, param: str):
        """Handle cell right-click: show connection popup."""
        self._select_cell(source, target, param)
        
        conn = self.routing_state.get_connection(source, target, param)
        
        if not conn:
            # Create connection first
            conn = CrossmodConnection(
                source_gen=source,
                target_gen=target,
                target_param=param,
                amount=0.5,
                offset=0.0,
                invert=False
            )
            self.routing_state.add_connection(conn)
        
        # Build labels
        source_label = f"GEN {source}"
        param_label = param.upper()[:3]
        for key, label in GEN_PARAMS:
            if key == param:
                param_label = label
                break
        target_label = f"G{target} {param_label}"
        
        # Close existing popup
        if self._open_popup:
            self._open_popup.close()
        
        # Show popup
        popup = CrossmodConnectionPopup(conn, source_label, target_label, parent=self)
        popup.connection_changed.connect(
            lambda c, s=source, t=target, p=param: self._on_popup_connection_changed(s, t, p, c)
        )
        popup.remove_requested.connect(
            lambda s=source, t=target, p=param: self._on_popup_remove(s, t, p)
        )
        popup.finished.connect(self._on_popup_closed)
        
        self._open_popup = popup
        
        # Position near cell
        cell = self.cells.get((source, target, param))
        if cell:
            global_pos = cell.mapToGlobal(cell.rect().center())
            popup.move(global_pos.x() + 20, global_pos.y() - 50)
        
        popup.show()
    
    def _on_popup_closed(self):
        """Clear popup reference."""
        self._open_popup = None
    
    def _on_popup_connection_changed(self, source: int, target: int, param: str, conn: CrossmodConnection):
        """Handle popup changes."""
        self.routing_state.update_connection(
            source, target, param,
            amount=conn.amount,
            offset=conn.offset,
            invert=conn.invert
        )
    
    def _on_popup_remove(self, source: int, target: int, param: str):
        """Handle remove from popup."""
        self.routing_state.remove_connection(source, target, param)
    
    def _on_connection_added(self, conn: CrossmodConnection):
        """Update cell when connection added."""
        cell = self.cells.get((conn.source_gen, conn.target_gen, conn.target_param))
        if cell:
            cell.set_connection(True, conn.amount, conn.invert)
    
    def _on_connection_removed(self, source: int, target: int, param: str):
        """Update cell when connection removed."""
        cell = self.cells.get((source, target, param))
        if cell:
            cell.set_connection(False)
        if self._open_popup:
            self._open_popup.close()
    
    def _on_connection_changed(self, conn: CrossmodConnection):
        """Update cell when connection changed."""
        cell = self.cells.get((conn.source_gen, conn.target_gen, conn.target_param))
        if cell:
            cell.set_connection(True, conn.amount, conn.invert)
        if self._open_popup:
            self._open_popup.sync_from_state(conn)
    
    def _on_all_cleared(self):
        """Clear all cells."""
        for cell in self.cells.values():
            cell.set_connection(False)
        if self._open_popup:
            self._open_popup.close()
    
    def _on_follower_state_changed(self, source_gen: int):
        """Sync checkbox when follower state changes externally."""
        enabled = self.routing_state.is_follower_enabled(source_gen)
        if source_gen in self.row_checkboxes:
            self.row_checkboxes[source_gen].blockSignals(True)
            self.row_checkboxes[source_gen].setChecked(enabled)
            self.row_checkboxes[source_gen].blockSignals(False)
    
    def _clear_all_routes(self):
        """Clear all crossmod routes."""
        self.routing_state.clear()
    
    # ========================================
    # KEYBOARD NAVIGATION
    # ========================================
    
    def keyPressEvent(self, event):
        """Handle keyboard input."""
        key = event.key()
        modifiers = event.modifiers()
        
        ctrl_held = modifiers & (Qt.ControlModifier | Qt.MetaModifier)
        shift_held = modifiers & Qt.ShiftModifier
        
        # Arrow keys
        if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            if key == Qt.Key_Up:
                step = 4 if ctrl_held else (1 if not shift_held else 5)
                self._nav_direction = (-step, 0)
            elif key == Qt.Key_Down:
                step = 4 if ctrl_held else (1 if not shift_held else 5)
                self._nav_direction = (step, 0)
            elif key == Qt.Key_Left:
                step = 10 if ctrl_held else (1 if not shift_held else 5)
                self._nav_direction = (0, -step)
            elif key == Qt.Key_Right:
                step = 10 if ctrl_held else (1 if not shift_held else 5)
                self._nav_direction = (0, step)
            
            self._held_arrow = key
            self._move_selection(*self._nav_direction)
            self._nav_timer.start(100)
        
        # Space: toggle connection
        elif key == Qt.Key_Space:
            if shift_held:
                self._toggle_selected_with_invert()
            else:
                self._toggle_selected()
        
        # Delete/Backspace: remove connection
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self._remove_selected()
        
        # D: open popup
        elif key == Qt.Key_D:
            self._open_popup_for_selected()
        
        # I: toggle invert
        elif key == Qt.Key_I:
            self._toggle_selected_invert()
        
        # 1-9: set amount
        elif Qt.Key_1 <= key <= Qt.Key_9:
            value = (key - Qt.Key_0) / 10.0
            self._set_selected_amount(value)
        
        # 0: set amount 100%
        elif key == Qt.Key_0:
            self._set_selected_amount(1.0)
        
        # Escape: deselect
        elif key == Qt.Key_Escape:
            self._update_selection_visual(False)
        
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Stop navigation timer."""
        if event.key() == self._held_arrow:
            self._nav_timer.stop()
            self._held_arrow = None
        super().keyReleaseEvent(event)
    
    def _on_nav_timer(self):
        """Continue movement while arrow held."""
        if self._held_arrow:
            self._move_selection(*self._nav_direction)
    
    def _move_selection(self, row_delta: int, col_delta: int):
        """Move selection by delta."""
        self._update_selection_visual(False)
        
        new_row = (self.selected_row + row_delta) % TOTAL_ROWS
        new_col = (self.selected_col + col_delta) % TOTAL_COLS
        
        self.selected_row = new_row
        self.selected_col = new_col
        
        self._update_selection_visual(True)
        self._scroll_to_selected()
    
    def _update_selection_visual(self, selected: bool):
        """Update selection visual."""
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
        """Scroll to selected cell."""
        if not self.cell_grid:
            return
        if self.selected_row >= len(self.cell_grid):
            return
        if self.selected_col >= len(self.cell_grid[self.selected_row]):
            return
        
        key = self.cell_grid[self.selected_row][self.selected_col]
        cell = self.cells.get(key)
        if cell:
            scroll = self.findChild(QScrollArea)
            if scroll:
                scroll.ensureWidgetVisible(cell)
    
    def _get_selected_key(self):
        """Get selected cell key."""
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
    
    def _toggle_selected_with_invert(self):
        """Toggle connection with invert at selected cell."""
        key = self._get_selected_key()
        if key:
            self._on_cell_shift_clicked(*key)
    
    def _toggle_selected_invert(self):
        """Toggle invert on existing connection."""
        key = self._get_selected_key()
        if key:
            source, target, param = key
            conn = self.routing_state.get_connection(source, target, param)
            if conn:
                self.routing_state.toggle_invert(source, target, param)
    
    def _remove_selected(self):
        """Remove connection at selected cell."""
        key = self._get_selected_key()
        if key:
            self.routing_state.remove_connection(*key)
    
    def _open_popup_for_selected(self):
        """Open popup for selected cell."""
        key = self._get_selected_key()
        if key:
            self._on_cell_right_clicked(*key)
    
    def _set_selected_amount(self, amount: float):
        """Set amount for selected cell."""
        key = self._get_selected_key()
        if not key:
            return
        
        source, target, param = key
        conn = self.routing_state.get_connection(source, target, param)
        
        if conn:
            self.routing_state.set_amount(source, target, param, amount)
        else:
            new_conn = CrossmodConnection(
                source_gen=source,
                target_gen=target,
                target_param=param,
                amount=amount
            )
            self.routing_state.add_connection(new_conn)
    
    # ========================================
    # SETTINGS PERSISTENCE
    # ========================================
    
    def _load_settings(self):
        """Load window geometry."""
        settings = QSettings("NoiseEngine", "CrossmodMatrix")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 400)
    
    def _save_settings(self):
        """Save window geometry."""
        settings = QSettings("NoiseEngine", "CrossmodMatrix")
        settings.setValue("geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Save settings on close."""
        self._save_settings()
        super().closeEvent(event)
    
    def showEvent(self, event):
        """Set initial selection when shown."""
        super().showEvent(event)
        self._update_selection_visual(True)
        self.setFocus(Qt.OtherFocusReason)
