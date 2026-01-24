"""
Boid Modulation Panel
Compact UI for boid modulation parameters and mini visualizer.

Controls:
- Enable toggle
- COUNT: Number of boids (1-24)
- Zone toggles: GEN, MOD, CHN, FX
- DISP: Flock spread (0-1)
- ENGY: Movement speed (0-1)
- FADE: Trail fade time (0-1)
- DPTH: Connection strength (0-1)
- Seed: Deterministic seed with lock toggle
"""

from typing import List, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSpinBox, QSizePolicy, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush

from .widgets import DragSlider
from .theme import COLORS, FONT_FAMILY, FONT_SIZES, MONO_FONT, button_style


class BoidMiniVisualizer(QWidget):
    """
    Mini visualizer showing boid positions on a small grid.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(80, 50)
        self.setMaximumHeight(60)

        self._positions: List[Tuple[float, float]] = []
        self._cells: dict = {}

        # Colors
        self._bg_color = QColor(COLORS['background_dark'])
        self._grid_color = QColor(COLORS['border'])
        self._boid_color = QColor('#cc66ff')
        self._trail_color = QColor('#cc66ff')

    def set_positions(self, positions: List[Tuple[float, float]]) -> None:
        """Update boid positions."""
        self._positions = positions
        self.update()

    def set_cells(self, cells: dict) -> None:
        """Update cell contributions for trail visualization."""
        self._cells = cells
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, self._bg_color)

        # Border
        painter.setPen(QPen(self._grid_color, 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        # Draw trail cells (fading contributions)
        for (row, col), value in self._cells.items():
            # Map cell to pixel position
            # Grid is 151 cols x 16 rows
            cx = (col / 151.0) * w
            cy = (row / 16.0) * h
            cell_w = w / 151.0
            cell_h = h / 16.0

            alpha = int(value * 120)
            trail_color = QColor(self._trail_color)
            trail_color.setAlpha(alpha)
            painter.fillRect(
                int(cx), int(cy),
                max(2, int(cell_w) + 1), max(2, int(cell_h) + 1),
                trail_color
            )

        # Draw boids
        for x, y in self._positions:
            px = x * w
            py = y * h

            # Boid dot
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self._boid_color))
            painter.drawEllipse(int(px) - 3, int(py) - 3, 6, 6)


class BoidPanel(QWidget):
    """
    Panel for boid modulation controls with mini visualizer.
    """

    # Signals
    enabled_changed = pyqtSignal(bool)
    count_changed = pyqtSignal(int)
    dispersion_changed = pyqtSignal(float)
    energy_changed = pyqtSignal(float)
    fade_changed = pyqtSignal(float)
    depth_changed = pyqtSignal(float)
    seed_lock_changed = pyqtSignal(bool)
    reseed_clicked = pyqtSignal()
    zone_gen_changed = pyqtSignal(bool)
    zone_mod_changed = pyqtSignal(bool)
    zone_chan_changed = pyqtSignal(bool)
    zone_fx_changed = pyqtSignal(bool)
    row_slot1_changed = pyqtSignal(bool)
    row_slot2_changed = pyqtSignal(bool)
    row_slot3_changed = pyqtSignal(bool)
    row_slot4_changed = pyqtSignal(bool)
    preset_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._enabled = False
        self._seed_locked = False

        self.setMinimumHeight(245)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self._setup_ui()

    def _setup_ui(self):
        """Build the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # === HEADER ===
        header = QHBoxLayout()
        header.setSpacing(4)

        # Enable button
        self._enable_btn = QPushButton("BOIDS")
        self._enable_btn.setCheckable(True)
        self._enable_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['label'], QFont.Bold))
        self._enable_btn.setToolTip(
            "Boid Modulation: Position-based routing.\n"
            "Boids fly over the mod matrix grid and create\n"
            "temporary connections where they land.\n\n"
            "Open mod matrix (Cmd+M) to see the visualization.")
        self._enable_btn.clicked.connect(self._on_enable_clicked)
        self._update_enable_style()
        header.addWidget(self._enable_btn)

        header.addStretch()

        # Count control in header
        count_label = QLabel("N:")
        count_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        count_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        count_label.setToolTip("Number of boids")
        header.addWidget(count_label)

        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, 24)
        self._count_spin.setValue(8)
        self._count_spin.setFixedWidth(45)
        self._count_spin.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self._count_spin.setToolTip(
            "Number of boids (1-24).\n"
            "More boids = more simultaneous connections.")
        self._count_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
                padding: 2px;
            }}
        """)
        self._count_spin.valueChanged.connect(self.count_changed.emit)
        header.addWidget(self._count_spin)

        layout.addLayout(header)

        # === MINI VISUALIZER ===
        self._visualizer = BoidMiniVisualizer()
        layout.addWidget(self._visualizer)

        # === ZONE TOGGLES ===
        zone_layout = QHBoxLayout()
        zone_layout.setSpacing(4)

        zone_label = QLabel("TARGETS:")
        zone_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        zone_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        zone_label.setToolTip("Which grid zones boids can target")
        zone_layout.addWidget(zone_label)

        self._zone_gen_btn = self._make_zone_button("GEN", "Generator params (cols 0-79)", True)
        self._zone_gen_btn.clicked.connect(lambda: self._on_zone_clicked('gen'))
        zone_layout.addWidget(self._zone_gen_btn)

        self._zone_mod_btn = self._make_zone_button("MOD", "Mod slot params (cols 80-107)\nOFF by default to prevent UI conflicts", False)
        self._zone_mod_btn.clicked.connect(lambda: self._on_zone_clicked('mod'))
        zone_layout.addWidget(self._zone_mod_btn)

        self._zone_chan_btn = self._make_zone_button("CHN", "Channel params: echo, verb, pan (cols 108-131)", True)
        self._zone_chan_btn.clicked.connect(lambda: self._on_zone_clicked('chan'))
        zone_layout.addWidget(self._zone_chan_btn)

        self._zone_fx_btn = self._make_zone_button("FX", "FX params: heat, echo, verb, feedback (cols 132-150)", True)
        self._zone_fx_btn.clicked.connect(lambda: self._on_zone_clicked('fx'))
        zone_layout.addWidget(self._zone_fx_btn)

        zone_layout.addStretch()
        layout.addLayout(zone_layout)

        # === ROW RESTRICTIONS ===
        row_layout = QHBoxLayout()
        row_layout.setSpacing(4)

        row_label = QLabel("SLOTS:")
        row_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        row_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        row_label.setToolTip("Which mod slot outputs boids can use as sources")
        row_layout.addWidget(row_label)

        self._row_slot1_btn = self._make_zone_button("1", "Slot 1 outputs (rows 0-3)", True)
        self._row_slot1_btn.clicked.connect(lambda: self._on_row_clicked(1))
        row_layout.addWidget(self._row_slot1_btn)

        self._row_slot2_btn = self._make_zone_button("2", "Slot 2 outputs (rows 4-7)", True)
        self._row_slot2_btn.clicked.connect(lambda: self._on_row_clicked(2))
        row_layout.addWidget(self._row_slot2_btn)

        self._row_slot3_btn = self._make_zone_button("3", "Slot 3 outputs (rows 8-11)", True)
        self._row_slot3_btn.clicked.connect(lambda: self._on_row_clicked(3))
        row_layout.addWidget(self._row_slot3_btn)

        self._row_slot4_btn = self._make_zone_button("4", "Slot 4 outputs (rows 12-15)", True)
        self._row_slot4_btn.clicked.connect(lambda: self._on_row_clicked(4))
        row_layout.addWidget(self._row_slot4_btn)

        row_layout.addSpacing(12)

        # Behavior preset dropdown
        preset_label = QLabel("BEHAVE:")
        preset_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        preset_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        preset_label.setToolTip("Behavior preset (sets DISP/ENGY/FADE together)")
        row_layout.addWidget(preset_label)

        self._preset_combo = QComboBox()
        self._preset_combo.addItems(['custom', 'swarm', 'scatter', 'drift', 'chaos'])
        self._preset_combo.setFixedWidth(70)
        self._preset_combo.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self._preset_combo.setToolTip(
            "Behavior presets:\n"
            "• custom: Manual control\n"
            "• swarm: Tight flock, medium speed\n"
            "• scatter: High dispersion, fast\n"
            "• drift: Slow, cohesive movement\n"
            "• chaos: Fast, erratic")
        self._preset_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
                padding: 2px 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                selection-background-color: #cc66ff;
            }}
        """)
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        row_layout.addWidget(self._preset_combo)

        row_layout.addStretch()
        layout.addLayout(row_layout)

        # === SEPARATOR ===
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # === PARAMETERS ===
        params_layout = QHBoxLayout()
        params_layout.setSpacing(8)

        # Dispersion
        disp_col = self._make_param_column("DISP",
            "Dispersion: Flock spread.\n"
            "Low = tight flock\n"
            "High = scattered boids")
        self._dispersion_slider = disp_col['slider']
        self._dispersion_slider.valueChanged.connect(self._on_dispersion_changed)
        params_layout.addLayout(disp_col['layout'])

        # Energy
        energy_col = self._make_param_column("ENGY",
            "Energy: Movement speed.\n"
            "Low = slow drift\n"
            "High = fast, chaotic")
        self._energy_slider = energy_col['slider']
        self._energy_slider.valueChanged.connect(self._on_energy_changed)
        params_layout.addLayout(energy_col['layout'])

        # Fade
        fade_col = self._make_param_column("FADE",
            "Fade: Trail decay time.\n"
            "Low = fast fade (0.1s)\n"
            "High = slow fade (2s)")
        self._fade_slider = fade_col['slider']
        self._fade_slider.valueChanged.connect(self._on_fade_changed)
        params_layout.addLayout(fade_col['layout'])

        # Depth
        depth_col = self._make_param_column("DPTH",
            "Depth: Connection strength.\n"
            "How much modulation is added\n"
            "when a boid is over a cell.")
        self._depth_slider = depth_col['slider']
        self._depth_slider.setValue(1000)  # Default 1.0
        self._depth_slider.valueChanged.connect(
            lambda v: self.depth_changed.emit(v / 1000.0)
        )
        params_layout.addLayout(depth_col['layout'])

        layout.addLayout(params_layout)

        # === SEED CONTROLS ===
        seed_layout = QHBoxLayout()
        seed_layout.setSpacing(4)

        seed_label = QLabel("SEED")
        seed_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        seed_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        seed_label.setToolTip(
            "Seed: Random number generator seed.\n"
            "Same seed = same boid movement pattern.")
        seed_layout.addWidget(seed_label)

        self._seed_display = QLabel("0")
        self._seed_display.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self._seed_display.setStyleSheet(f"color: {COLORS['text']};")
        self._seed_display.setMinimumWidth(80)
        self._seed_display.setToolTip("Current seed value")
        seed_layout.addWidget(self._seed_display)

        seed_layout.addStretch()

        self._lock_btn = QPushButton("LOCK")
        self._lock_btn.setCheckable(True)
        self._lock_btn.setFixedSize(40, 20)
        self._lock_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self._lock_btn.setToolTip(
            "Lock seed for deterministic playback.\n"
            "When locked, boids follow the exact same\n"
            "pattern every time.")
        self._lock_btn.clicked.connect(self._on_lock_clicked)
        self._update_lock_style()
        seed_layout.addWidget(self._lock_btn)

        self._reseed_btn = QPushButton("NEW")
        self._reseed_btn.setFixedSize(36, 20)
        self._reseed_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self._reseed_btn.setToolTip("Generate new random seed.")
        self._reseed_btn.setStyleSheet(button_style())
        self._reseed_btn.clicked.connect(lambda: self.reseed_clicked.emit())
        seed_layout.addWidget(self._reseed_btn)

        layout.addLayout(seed_layout)

        # Set panel style
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
            }}
        """)

    def _make_zone_button(self, label: str, tooltip: str, default_on: bool) -> QPushButton:
        """Create a zone toggle button."""
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(default_on)
        btn.setFixedSize(32, 20)
        btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        btn.setToolTip(tooltip)
        self._update_zone_button_style(btn)
        return btn

    def _update_zone_button_style(self, btn: QPushButton) -> None:
        """Update zone button style based on checked state."""
        if btn.isChecked():
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #cc66ff;
                    color: {COLORS['background']};
                    border: none;
                    border-radius: 2px;
                    font-weight: bold;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['text_dim']};
                }}
            """)

    def _on_zone_clicked(self, zone: str) -> None:
        """Handle zone button click."""
        if zone == 'gen':
            self._update_zone_button_style(self._zone_gen_btn)
            self.zone_gen_changed.emit(self._zone_gen_btn.isChecked())
        elif zone == 'mod':
            self._update_zone_button_style(self._zone_mod_btn)
            self.zone_mod_changed.emit(self._zone_mod_btn.isChecked())
        elif zone == 'chan':
            self._update_zone_button_style(self._zone_chan_btn)
            self.zone_chan_changed.emit(self._zone_chan_btn.isChecked())
        elif zone == 'fx':
            self._update_zone_button_style(self._zone_fx_btn)
            self.zone_fx_changed.emit(self._zone_fx_btn.isChecked())

    def _on_row_clicked(self, slot: int) -> None:
        """Handle row slot button click."""
        if slot == 1:
            self._update_zone_button_style(self._row_slot1_btn)
            self.row_slot1_changed.emit(self._row_slot1_btn.isChecked())
        elif slot == 2:
            self._update_zone_button_style(self._row_slot2_btn)
            self.row_slot2_changed.emit(self._row_slot2_btn.isChecked())
        elif slot == 3:
            self._update_zone_button_style(self._row_slot3_btn)
            self.row_slot3_changed.emit(self._row_slot3_btn.isChecked())
        elif slot == 4:
            self._update_zone_button_style(self._row_slot4_btn)
            self.row_slot4_changed.emit(self._row_slot4_btn.isChecked())
        # When user manually adjusts, switch to custom preset
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentText('custom')
        self._preset_combo.blockSignals(False)

    def _on_preset_changed(self, preset_name: str) -> None:
        """Handle preset selection."""
        self.preset_changed.emit(preset_name)

    def _on_dispersion_changed(self, value: int) -> None:
        """Handle dispersion slider change."""
        self._switch_to_custom_preset()
        self.dispersion_changed.emit(value / 1000.0)

    def _on_energy_changed(self, value: int) -> None:
        """Handle energy slider change."""
        self._switch_to_custom_preset()
        self.energy_changed.emit(value / 1000.0)

    def _on_fade_changed(self, value: int) -> None:
        """Handle fade slider change."""
        self._switch_to_custom_preset()
        self.fade_changed.emit(value / 1000.0)

    def _switch_to_custom_preset(self) -> None:
        """Switch to custom preset when user manually adjusts parameters."""
        if self._preset_combo.currentText() != 'custom':
            self._preset_combo.blockSignals(True)
            self._preset_combo.setCurrentText('custom')
            self._preset_combo.blockSignals(False)

    def _make_param_column(self, label: str, tooltip: str) -> dict:
        """Create a parameter column with label and slider."""
        col = QVBoxLayout()
        col.setSpacing(2)

        lbl = QLabel(label)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setToolTip(tooltip)
        col.addWidget(lbl)

        slider = DragSlider()
        slider.setRange(0, 1000)
        slider.setValue(500)
        slider.setFixedSize(20, 60)
        slider.setToolTip(tooltip)
        col.addWidget(slider, alignment=Qt.AlignCenter)

        return {'layout': col, 'slider': slider}

    def _on_enable_clicked(self):
        self._enabled = self._enable_btn.isChecked()
        self._update_enable_style()
        self.enabled_changed.emit(self._enabled)

    def _update_enable_style(self):
        if self._enabled:
            self._enable_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #cc66ff;
                    color: {COLORS['background']};
                    border: none;
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-weight: bold;
                }}
            """)
        else:
            self._enable_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: #cc66ff;
                    border: 1px solid #cc66ff;
                    border-radius: 3px;
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['background']};
                }}
            """)

    def _on_lock_clicked(self):
        self._seed_locked = self._lock_btn.isChecked()
        self._update_lock_style()
        self.seed_lock_changed.emit(self._seed_locked)

    def _update_lock_style(self):
        if self._seed_locked:
            self._lock_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #cc66ff;
                    color: {COLORS['background']};
                    border: none;
                    border-radius: 2px;
                    font-weight: bold;
                }}
            """)
        else:
            self._lock_btn.setStyleSheet(button_style())

    # === PUBLIC API ===

    def set_enabled(self, enabled: bool) -> None:
        """Set enabled state."""
        self._enabled = enabled
        self._enable_btn.blockSignals(True)
        self._enable_btn.setChecked(enabled)
        self._enable_btn.blockSignals(False)
        self._update_enable_style()

    def set_count(self, count: int) -> None:
        """Set boid count."""
        self._count_spin.blockSignals(True)
        self._count_spin.setValue(count)
        self._count_spin.blockSignals(False)

    def set_dispersion(self, value: float) -> None:
        self._dispersion_slider.blockSignals(True)
        self._dispersion_slider.setValue(int(value * 1000))
        self._dispersion_slider.blockSignals(False)

    def set_energy(self, value: float) -> None:
        self._energy_slider.blockSignals(True)
        self._energy_slider.setValue(int(value * 1000))
        self._energy_slider.blockSignals(False)

    def set_fade(self, value: float) -> None:
        self._fade_slider.blockSignals(True)
        self._fade_slider.setValue(int(value * 1000))
        self._fade_slider.blockSignals(False)

    def set_depth(self, value: float) -> None:
        self._depth_slider.blockSignals(True)
        self._depth_slider.setValue(int(value * 1000))
        self._depth_slider.blockSignals(False)

    def set_seed(self, seed: int) -> None:
        self._seed_display.setText(str(seed))

    def set_seed_locked(self, locked: bool) -> None:
        self._seed_locked = locked
        self._lock_btn.blockSignals(True)
        self._lock_btn.setChecked(locked)
        self._lock_btn.blockSignals(False)
        self._update_lock_style()

    def set_zone_gen(self, enabled: bool) -> None:
        self._zone_gen_btn.blockSignals(True)
        self._zone_gen_btn.setChecked(enabled)
        self._zone_gen_btn.blockSignals(False)
        self._update_zone_button_style(self._zone_gen_btn)

    def set_zone_mod(self, enabled: bool) -> None:
        self._zone_mod_btn.blockSignals(True)
        self._zone_mod_btn.setChecked(enabled)
        self._zone_mod_btn.blockSignals(False)
        self._update_zone_button_style(self._zone_mod_btn)

    def set_zone_chan(self, enabled: bool) -> None:
        self._zone_chan_btn.blockSignals(True)
        self._zone_chan_btn.setChecked(enabled)
        self._zone_chan_btn.blockSignals(False)
        self._update_zone_button_style(self._zone_chan_btn)

    def set_zone_fx(self, enabled: bool) -> None:
        self._zone_fx_btn.blockSignals(True)
        self._zone_fx_btn.setChecked(enabled)
        self._zone_fx_btn.blockSignals(False)
        self._update_zone_button_style(self._zone_fx_btn)

    def set_row_slot1(self, enabled: bool) -> None:
        self._row_slot1_btn.blockSignals(True)
        self._row_slot1_btn.setChecked(enabled)
        self._row_slot1_btn.blockSignals(False)
        self._update_zone_button_style(self._row_slot1_btn)

    def set_row_slot2(self, enabled: bool) -> None:
        self._row_slot2_btn.blockSignals(True)
        self._row_slot2_btn.setChecked(enabled)
        self._row_slot2_btn.blockSignals(False)
        self._update_zone_button_style(self._row_slot2_btn)

    def set_row_slot3(self, enabled: bool) -> None:
        self._row_slot3_btn.blockSignals(True)
        self._row_slot3_btn.setChecked(enabled)
        self._row_slot3_btn.blockSignals(False)
        self._update_zone_button_style(self._row_slot3_btn)

    def set_row_slot4(self, enabled: bool) -> None:
        self._row_slot4_btn.blockSignals(True)
        self._row_slot4_btn.setChecked(enabled)
        self._row_slot4_btn.blockSignals(False)
        self._update_zone_button_style(self._row_slot4_btn)

    def set_preset(self, preset_name: str) -> None:
        """Set behavior preset dropdown."""
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentText(preset_name)
        self._preset_combo.blockSignals(False)

    def set_positions(self, positions: list) -> None:
        """Update mini visualizer with boid positions."""
        self._visualizer.set_positions(positions)

    def set_cells(self, cells: dict) -> None:
        """Update mini visualizer with cell contributions."""
        self._visualizer.set_cells(cells)
