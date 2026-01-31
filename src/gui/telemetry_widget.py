"""
Telemetry Widget — Development-only DSP monitor for generators.

Opens as a separate window (Ctrl+Shift+T). Displays:
- Real-time parameter values (FRQ, P0-P4)
- Per-stage RMS meters (Stage 1/2/3)
- Peak indicator with color grading
- Core Lock warning (NaN/inf detection)
- Waveform display with ideal overlay

All colors from theme.py. All fonts from FONT_SIZES/FONT_FAMILY.
"""

import time

import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QPen, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QFrame,
    QFileDialog,
)

from src.gui.theme import COLORS, FONT_FAMILY, MONO_FONT, FONT_SIZES


# =============================================================================
# VERTICAL METER (themed)
# =============================================================================

class VerticalMeter(QWidget):
    """Vertical LED-style meter for RMS levels."""

    def __init__(self, label_text="", parent=None):
        super().__init__(parent)
        self.setFixedWidth(28)
        self.setMinimumHeight(120)
        self._value = 0.0  # 0-1 linear amplitude
        self._peak = 0.0
        self._label_text = label_text

    def set_value(self, value):
        self._value = max(0.0, min(1.0, value))
        self.update()

    def set_peak(self, peak):
        self._peak = max(0.0, min(1.0, peak))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        label_h = 14
        meter_y = 0
        meter_h = h - label_h - 4

        # Background
        p.fillRect(0, meter_y, w, meter_h, QColor(COLORS['meter_bg']))

        # Filled region (bottom-up)
        fill_h = int(self._value * meter_h)
        if fill_h > 0:
            for y in range(fill_h):
                ratio = y / meter_h
                if ratio > 0.85:
                    color = QColor(COLORS['meter_clip'])
                elif ratio > 0.65:
                    color = QColor(COLORS['meter_warn'])
                else:
                    color = QColor(COLORS['meter_normal'])
                p.fillRect(2, meter_y + meter_h - y - 1, w - 4, 1, color)

        # Peak indicator line
        if self._peak > 0.01:
            peak_y = meter_y + meter_h - int(self._peak * meter_h)
            p.setPen(QPen(QColor(COLORS['text_bright']), 1))
            p.drawLine(1, peak_y, w - 2, peak_y)

        # Border
        p.setPen(QPen(QColor(COLORS['border']), 1))
        p.drawRect(0, meter_y, w - 1, meter_h - 1)

        # Label
        p.setPen(QColor(COLORS['text_dim']))
        p.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        p.drawText(0, meter_y + meter_h + 2, w, label_h, Qt.AlignCenter, self._label_text)

        p.end()


# =============================================================================
# WAVEFORM DISPLAY (QPainter, following ScopeDisplay pattern)
# =============================================================================

class WaveformDisplay(QWidget):
    """Oscilloscope-style waveform display with ideal overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 140)
        self._actual = None     # np.ndarray
        self._ideal = None      # np.ndarray
        self._show_ideal = True

    def set_waveform(self, actual, ideal=None):
        self._actual = actual
        self._ideal = ideal
        self.update()

    def set_show_ideal(self, show):
        self._show_ideal = show
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        p.fillRect(0, 0, w, h, QColor(COLORS['background_dark']))

        # Grid
        p.setPen(QPen(QColor(COLORS['scope_grid']), 1, Qt.DotLine))
        mid_y = h // 2
        p.drawLine(0, mid_y, w, mid_y)
        p.drawLine(w // 2, 0, w // 2, h)

        # Center line (brighter)
        p.setPen(QPen(QColor(COLORS['scope_center']), 1))
        p.drawLine(0, mid_y, w, mid_y)

        # Draw ideal trace (dimmer, behind actual)
        if self._show_ideal and self._ideal is not None and len(self._ideal) > 1:
            self._draw_trace(p, self._ideal, COLORS['scope_trace_b'], 1.0)

        # Draw actual trace
        if self._actual is not None and len(self._actual) > 1:
            self._draw_trace(p, self._actual, COLORS['scope_trace_a'], 1.5)

        # Border
        p.setPen(QPen(QColor(COLORS['border']), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        # Label if no data
        if self._actual is None:
            p.setPen(QColor(COLORS['text_dim']))
            p.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
            p.drawText(0, 0, w, h, Qt.AlignCenter, "No waveform data")

        p.end()

    def _draw_trace(self, painter, data, color, width):
        w, h = self.width(), self.height()
        n = len(data)
        mid_y = h / 2
        scale = mid_y * 0.9  # Leave margin

        painter.setPen(QPen(QColor(color), width))

        prev_x = 0
        prev_y = mid_y - float(data[0]) * scale
        for i in range(1, n):
            x = int(i * w / n)
            y = mid_y - float(data[i]) * scale
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
            prev_x, prev_y = x, y


# =============================================================================
# TELEMETRY WIDGET (main window)
# =============================================================================

class TelemetryWidget(QWidget):
    """Development-only DSP telemetry monitor window."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("DEV: Telemetry Monitor")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(480, 400)
        self.resize(520, 480)

        self._setup_ui()
        self._setup_refresh_timer()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                font-family: {MONO_FONT};
            }}
            QLabel {{
                font-size: {FONT_SIZES['small']}px;
            }}
            QPushButton {{
                background-color: {COLORS['background_highlight']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 4px 10px;
                font-size: {FONT_SIZES['small']}px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['enabled']};
                color: {COLORS['enabled_text']};
                border-color: {COLORS['border_active']};
            }}
            QComboBox {{
                background-color: {COLORS['background_highlight']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 2px 6px;
                font-size: {FONT_SIZES['small']}px;
            }}
        """)

        # ── Top row: Slot selector + Enable + Core Lock ──
        top_row = QHBoxLayout()

        slot_label = QLabel("SLOT")
        slot_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        top_row.addWidget(slot_label)

        self.slot_combo = QComboBox()
        for i in range(8):
            self.slot_combo.addItem(f"Slot {i + 1}")
        self.slot_combo.currentIndexChanged.connect(self._on_slot_changed)
        top_row.addWidget(self.slot_combo)

        self.enable_btn = QPushButton("Enable")
        self.enable_btn.setCheckable(True)
        self.enable_btn.clicked.connect(self._on_enable_toggled)
        top_row.addWidget(self.enable_btn)

        top_row.addStretch()

        # Core Lock warning
        self.core_lock_label = QLabel("")
        self.core_lock_label.setStyleSheet(
            f"color: {COLORS['warning_text']}; font-weight: bold; "
            f"font-size: {FONT_SIZES['label']}px; background: transparent;"
        )
        top_row.addWidget(self.core_lock_label)

        layout.addLayout(top_row)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        layout.addWidget(sep)

        # ── Parameter values ──
        param_grid = QGridLayout()
        param_grid.setSpacing(4)

        param_labels = ["FRQ", "P0", "P1", "P2", "P3", "P4"]
        self.param_values = {}

        for col, name in enumerate(param_labels):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
            param_grid.addWidget(lbl, 0, col)

            val = QLabel("---")
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};")
            param_grid.addWidget(val, 1, col)
            self.param_values[name] = val

        layout.addLayout(param_grid)

        # ── Meters + Peak ──
        meters_row = QHBoxLayout()
        meters_row.setSpacing(8)

        # Three stage meters
        self.meter_stage1 = VerticalMeter("S1")
        self.meter_stage2 = VerticalMeter("S2")
        self.meter_stage3 = VerticalMeter("S3")
        meters_row.addWidget(self.meter_stage1)
        meters_row.addWidget(self.meter_stage2)
        meters_row.addWidget(self.meter_stage3)

        meters_row.addSpacing(12)

        # Peak display
        peak_frame = QVBoxLayout()
        peak_label = QLabel("PEAK")
        peak_label.setAlignment(Qt.AlignCenter)
        peak_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        peak_frame.addWidget(peak_label)

        self.peak_value = QLabel("---")
        self.peak_value.setAlignment(Qt.AlignCenter)
        self.peak_value.setStyleSheet(f"color: {COLORS['meter_normal']}; font-size: {FONT_SIZES['title']}px; font-family: {MONO_FONT}; font-weight: bold;")
        peak_frame.addWidget(self.peak_value)
        peak_frame.addStretch()

        meters_row.addLayout(peak_frame)
        meters_row.addStretch()

        layout.addLayout(meters_row)

        # ── Waveform display ──
        wave_row = QHBoxLayout()
        wave_label = QLabel("WAVEFORM")
        wave_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        wave_row.addWidget(wave_label)

        self.wave_enable_cb = QCheckBox("Capture")
        self.wave_enable_cb.setStyleSheet(f"color: {COLORS['text']}; font-size: {FONT_SIZES['small']}px;")
        self.wave_enable_cb.toggled.connect(self._on_wave_enable_toggled)
        wave_row.addWidget(self.wave_enable_cb)

        self.ideal_cb = QCheckBox("Ideal Overlay")
        self.ideal_cb.setChecked(True)
        self.ideal_cb.setStyleSheet(f"color: {COLORS['text']}; font-size: {FONT_SIZES['small']}px;")
        self.ideal_cb.toggled.connect(self._on_ideal_toggled)
        wave_row.addWidget(self.ideal_cb)

        wave_row.addStretch()
        layout.addLayout(wave_row)

        self.waveform_display = WaveformDisplay()
        layout.addWidget(self.waveform_display, stretch=1)

        # ── Bottom row: Snapshot + Export ──
        bottom_row = QHBoxLayout()

        snapshot_btn = QPushButton("Snapshot")
        snapshot_btn.clicked.connect(self._on_snapshot)
        bottom_row.addWidget(snapshot_btn)

        export_btn = QPushButton("Export History")
        export_btn.clicked.connect(self._on_export)
        bottom_row.addWidget(export_btn)

        bottom_row.addStretch()

        # Frame count
        self.frame_count_label = QLabel("Frames: 0")
        self.frame_count_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px;")
        bottom_row.addWidget(self.frame_count_label)

        layout.addLayout(bottom_row)

    def _setup_refresh_timer(self):
        """Refresh UI at 15fps (matches default telemetry rate)."""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(66)  # ~15fps

    # ── Event Handlers ──

    def _on_slot_changed(self, index):
        self.controller.set_slot(index)
        self.core_lock_label.setText("")

    def _on_enable_toggled(self, checked):
        if checked:
            self.controller.enable(self.slot_combo.currentIndex())
            self.enable_btn.setText("Disable")
        else:
            self.controller.disable()
            self.enable_btn.setText("Enable")

    def _on_wave_enable_toggled(self, checked):
        slot = self.slot_combo.currentIndex()
        if checked:
            self.controller.enable_waveform(slot)
        else:
            self.controller.disable_waveform(slot)

    def _on_ideal_toggled(self, checked):
        self.waveform_display.set_show_ideal(checked)

    def _on_snapshot(self):
        snap = self.controller.snapshot()
        if snap:
            import json
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Telemetry Snapshot", "", "JSON (*.json)"
            )
            if path:
                with open(path, 'w') as f:
                    json.dump(snap, f, indent=2)

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Telemetry History", "", "JSON (*.json)"
        )
        if path:
            self.controller.export_history(path)

    # ── Refresh ──

    def _refresh(self):
        """Update display from latest telemetry data."""
        data = self.controller.get_latest()
        if data is None:
            return

        # Parameters
        self.param_values["FRQ"].setText(f"{data.get('freq', 0):.1f}")
        self.param_values["P0"].setText(f"{data.get('p0', 0):.3f}")
        self.param_values["P1"].setText(f"{data.get('p1', 0):.3f}")
        self.param_values["P2"].setText(f"{data.get('p2', 0):.3f}")
        self.param_values["P3"].setText(f"{data.get('p3', 0):.3f}")
        self.param_values["P4"].setText(f"{data.get('p4', 0):.3f}")

        # Stage meters
        self.meter_stage1.set_value(data.get('rms_stage1', 0))
        self.meter_stage2.set_value(data.get('rms_stage2', 0))
        self.meter_stage3.set_value(data.get('rms_stage3', 0))

        # Peak
        peak = data.get('peak', 0)
        if peak > 0.95:
            color = COLORS['meter_clip']
        elif peak > 0.7:
            color = COLORS['meter_warn']
        else:
            color = COLORS['meter_normal']
        self.peak_value.setText(f"{peak:.3f}")
        self.peak_value.setStyleSheet(
            f"color: {color}; font-size: {FONT_SIZES['title']}px; "
            f"font-family: {MONO_FONT}; font-weight: bold;"
        )

        # Core Lock
        bad = data.get('bad_value', 0)
        if bad > 0:
            err = "NaN" if bad == 1 else "∞"
            self.core_lock_label.setText(f"⚠ CORE LOCK: {err}")
        else:
            if self.core_lock_label.text():
                self.core_lock_label.setText("")

        # Waveform
        actual = self.controller.current_waveform
        ideal = self.controller.get_ideal_waveform(data) if self.ideal_cb.isChecked() else None
        self.waveform_display.set_waveform(actual, ideal)

        # Frame count
        self.frame_count_label.setText(f"Frames: {len(self.controller.history)}")

    def closeEvent(self, event):
        """Disable telemetry when window closes."""
        self.controller.disable()
        slot = self.slot_combo.currentIndex()
        if self.wave_enable_cb.isChecked():
            self.controller.disable_waveform(slot)
        self._timer.stop()
        event.accept()
