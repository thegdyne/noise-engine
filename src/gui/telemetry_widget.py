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
from PyQt5.QtWidgets import (  # noqa: E501
    QSlider, QMenu,
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QFrame,
    QFileDialog, QDoubleSpinBox,
)

from src.audio.telemetry_controller import TelemetryController
from src.config import get_generator_synthdef, TELEM_SOURCES
from src.gui.theme import COLORS, FONT_FAMILY, MONO_FONT, FONT_SIZES
from src.gui.widgets import MidiButton


# =============================================================================
# VERTICAL METER (themed)
# =============================================================================

class VerticalMeter(QWidget):
    """Vertical LED-style meter for RMS levels."""

    def __init__(self, label_text="", target=None, parent=None):
        super().__init__(parent)
        self.setFixedWidth(28)
        self.setMinimumHeight(120)
        self._value = 0.0  # 0-1 linear amplitude
        self._peak = 0.0
        self._target = target  # Optional target line (0-1)
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

        # Target line (dashed white)
        if self._target is not None:
            target_y = meter_y + meter_h - int(self._target * meter_h)
            p.setPen(QPen(QColor(COLORS['text_bright']), 1, Qt.DashLine))
            p.drawLine(1, target_y, w - 2, target_y)

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
        self._delta = None      # np.ndarray — |actual - ideal|
        self._show_ideal = True
        self._show_delta = False
        self._capture_enabled = False
        self._show_safety = False   # ±0.85 corridor lines
        self._peak_clipping = False  # stage1 peak > 0.90

    def set_waveform(self, actual, ideal=None, delta=None):
        self._actual = actual
        self._ideal = ideal
        self._delta = delta
        self.update()

    def set_capture_enabled(self, enabled):
        self._capture_enabled = enabled
        self.update()

    def set_show_ideal(self, show):
        self._show_ideal = show
        self.update()

    def set_show_delta(self, show):
        self._show_delta = show
        self.update()

    def set_show_safety(self, show):
        self._show_safety = show
        self.update()

    def set_peak_clipping(self, clipping):
        self._peak_clipping = clipping
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

        # Safety corridor: ±0.85 threshold lines (PA calibration guide)
        if self._show_safety:
            scale = (h / 2) * 0.9
            safety_pen = QPen(QColor(COLORS['meter_clip']), 1, Qt.DashLine)
            p.setPen(safety_pen)
            hi_y = int(mid_y - 0.85 * scale)
            lo_y = int(mid_y + 0.85 * scale)
            p.drawLine(0, hi_y, w, hi_y)
            p.drawLine(0, lo_y, w, lo_y)

        # Draw ideal trace (dimmer, behind actual)
        if self._show_ideal and self._ideal is not None and len(self._ideal) > 1:
            self._draw_trace(p, self._ideal, COLORS['scope_trace_b'], 1.0)

        # Draw actual trace
        if self._actual is not None and len(self._actual) > 1:
            self._draw_trace(p, self._actual, COLORS['scope_trace_a'], 1.5)

        # Draw delta trace (|actual - ideal|, rendered from center line up)
        if self._show_delta and self._delta is not None and len(self._delta) > 1:
            self._draw_trace(p, self._delta, COLORS['scope_trace_c'], 1.0)

        # Border (flashes red when peak > 0.90)
        if self._peak_clipping:
            p.setPen(QPen(QColor(COLORS['meter_clip']), 2))
        else:
            p.setPen(QPen(QColor(COLORS['border']), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        # Label if no data
        if self._actual is None:
            p.setPen(QColor(COLORS['text_dim']))
            p.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
            if not self._capture_enabled:
                p.drawText(0, 0, w, h, Qt.AlignCenter, "Capture OFF")
            else:
                p.drawText(0, 0, w, h, Qt.AlignCenter, "Waiting for waveform...")

        p.end()

    def _draw_trace(self, painter, data, color, width):
        w, h = self.width(), self.height()
        n = len(data)
        mid_y = h / 2
        scale = mid_y * 0.9  # Leave margin
        clamp = h * 2  # Pixel clamp to prevent int32 overflow

        painter.setPen(QPen(QColor(color), width))

        prev_x = 0
        val = float(data[0])
        if not np.isfinite(val):
            val = 0.0
        prev_y = max(-clamp, min(clamp, mid_y - val * scale))
        for i in range(1, n):
            x = int(i * w / n)
            val = float(data[i])
            if not np.isfinite(val):
                val = 0.0
            y = max(-clamp, min(clamp, mid_y - val * scale))
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
            prev_x, prev_y = x, y


# =============================================================================
# MIDI-LEARNABLE HORIZONTAL SLIDER (for telemetry controls)
# =============================================================================

class MidiHSlider(QSlider):
    """Horizontal slider with MIDI CC learn support for telemetry window.

    Hold Shift for 10x finer steps (singleStep=1 becomes effectively 0.1x
    by requiring 10 scroll events per step).

    FINE mode: when enabled, MIDI CC 0-127 maps to a ±64 window around
    the current value instead of the full ±640 range. Gives ~1 slider unit
    per CC step for sub-sample precision.
    """

    def __init__(self, main_frame_ref=None, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setFocusPolicy(Qt.StrongFocus)  # Ensure wheel events arrive
        self._main_frame_ref = main_frame_ref
        self._midi_armed = False
        self._midi_mapped = False
        self._cc_ghost = None
        self._shift_accum = 0  # Accumulator for shift-key fine steps
        self._fine_mode = False
        self._fine_center = 0  # Captured when FINE toggled on

    def set_fine_mode(self, enabled):
        """Toggle fine CC mode. Captures current value as center."""
        self._fine_mode = enabled
        if enabled:
            self._fine_center = self.value()
        # Reset pickup so CC re-catches at the new range
        mf = self._get_main_frame()
        if mf:
            mapping = mf.cc_mapping_manager.get_mapping_for_control(self)
            if mapping:
                mf.cc_mapping_manager.reset_pickup(*mapping)

    def cc_range(self):
        """Return effective (min, max) for CC mapping.

        Normal: full slider range. FINE: ±64 around captured center,
        clamped to slider bounds.
        """
        if self._fine_mode:
            lo = max(self.minimum(), self._fine_center - 64)
            hi = min(self.maximum(), self._fine_center + 64)
            return (lo, hi)
        return (self.minimum(), self.maximum())

    def wheelEvent(self, event):
        from PyQt5.QtWidgets import QApplication
        if QApplication.keyboardModifiers() & Qt.ShiftModifier:
            # Accumulate scroll delta; step once per 10 standard ticks.
            # Threshold of 1200 (120/tick * 10) for sub-sample precision.
            delta = event.angleDelta().y()
            self._shift_accum += delta
            if abs(self._shift_accum) >= 1200:
                step = 1 if self._shift_accum > 0 else -1
                self.setValue(self.value() + step)
                self._shift_accum = 0
            event.accept()
        else:
            self._shift_accum = 0
            super().wheelEvent(event)

    def set_midi_armed(self, armed):
        self._midi_armed = armed
        self.update()

    def set_midi_mapped(self, mapped):
        self._midi_mapped = mapped
        self.update()

    def set_cc_ghost(self, norm_value):
        self._cc_ghost = norm_value
        self.update()

    def _get_main_frame(self):
        return self._main_frame_ref

    def _start_midi_learn(self):
        mf = self._get_main_frame()
        if mf:
            mf.cc_learn_manager.start_learn(self)

    def _clear_midi_mapping(self):
        mf = self._get_main_frame()
        if mf:
            mf.cc_mapping_manager.remove_mapping(self)
            self.set_midi_mapped(False)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        mf = self._get_main_frame()
        if not mf:
            return
        if self._midi_mapped:
            menu.addAction("Clear MIDI Mapping", self._clear_midi_mapping)
        menu.addAction("MIDI Learn", self._start_midi_learn)
        menu.exec_(event.globalPos())

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._midi_mapped:
            painter = QPainter(self)
            painter.setBrush(QColor('#FF00FF'))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.width() - 6, 1, 4, 4)
            painter.end()


# =============================================================================
# TELEMETRY WIDGET (main window)
# =============================================================================

class TelemetryWidget(QWidget):
    """Development-only DSP telemetry monitor window."""

    def __init__(self, controller, main_frame=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.main_frame = main_frame
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

        top_row.addSpacing(8)

        source_label = QLabel("TAP")
        source_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        top_row.addWidget(source_label)

        self.source_combo = QComboBox()
        for name in TELEM_SOURCES:
            self.source_combo.addItem(name)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        top_row.addWidget(self.source_combo)

        top_row.addStretch()

        # Core Lock warning
        self.core_lock_label = QLabel("")
        self.core_lock_label.setStyleSheet(
            f"color: {COLORS['warning_text']}; font-weight: bold; "
            f"font-size: {FONT_SIZES['label']}px; background: transparent;"
        )
        top_row.addWidget(self.core_lock_label)

        layout.addLayout(top_row)

        # ── Signal indicator row ──
        signal_row = QHBoxLayout()
        signal_row.setSpacing(6)

        self.signal_dot = QLabel("\u25CF")  # filled circle
        self.signal_dot.setFixedWidth(16)
        self.signal_dot.setAlignment(Qt.AlignCenter)
        self.signal_dot.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['label']}px; background: transparent;"
        )
        signal_row.addWidget(self.signal_dot)

        self.source_label = QLabel("---")
        self.source_label.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['small']}px; "
            f"font-family: {MONO_FONT}; font-weight: bold; background: transparent;"
        )
        signal_row.addWidget(self.source_label)

        signal_row.addStretch()
        layout.addLayout(signal_row)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        layout.addWidget(sep)

        # ── Parameter values ──
        param_grid = QGridLayout()
        param_grid.setSpacing(4)

        self._param_header_labels = []  # QLabel refs for dynamic relabeling
        self.param_values = {}
        self._param_keys = ["FRQ", "P0", "P1", "P2", "P3", "P4", "ERR"]

        for col, name in enumerate(self._param_keys):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
            param_grid.addWidget(lbl, 0, col)
            self._param_header_labels.append(lbl)

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
        self.meter_stage2 = VerticalMeter("S2", target=0.7027)  # RMS target for calibration
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

        meters_row.addSpacing(12)

        # Cal gain (internal tap calibration)
        cal_frame = QVBoxLayout()
        cal_label = QLabel("CAL")
        cal_label.setAlignment(Qt.AlignCenter)
        cal_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        cal_frame.addWidget(cal_label)

        self.cal_spin = QDoubleSpinBox()
        self.cal_spin.setRange(0.0, 4.0)
        self.cal_spin.setSingleStep(0.01)
        self.cal_spin.setDecimals(3)
        self.cal_spin.setValue(1.0)
        self.cal_spin.setFixedWidth(70)
        self.cal_spin.setStyleSheet(
            f"background-color: {COLORS['background_highlight']}; "
            f"color: {COLORS['text_bright']}; border: 1px solid {COLORS['border']}; "
            f"font-size: {FONT_SIZES['small']}px; font-family: {MONO_FONT};"
        )
        self.cal_spin.valueChanged.connect(self._on_cal_changed)
        cal_frame.addWidget(self.cal_spin)
        cal_frame.addStretch()

        self.cal_frame_widget = QWidget()
        self.cal_frame_widget.setLayout(cal_frame)
        meters_row.addWidget(self.cal_frame_widget)

        meters_row.addStretch()

        layout.addLayout(meters_row)

        # ── Living Proof metrics (Analog Life v1.2) ──
        life_row = QHBoxLayout()
        life_row.setSpacing(16)

        life_header = QLabel("LIFE")
        life_header.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        life_row.addWidget(life_header)

        # Crest Factor: Peak / RMS
        cf_label = QLabel("CF")
        cf_label.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        cf_label.setToolTip("Crest Factor (Peak ÷ RMS)")
        life_row.addWidget(cf_label)
        self.crest_value = QLabel("---")
        self.crest_value.setStyleSheet(
            f"color: {COLORS['text']}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};")
        life_row.addWidget(self.crest_value)

        life_row.addSpacing(8)

        # HF Energy: first-difference RMS proxy
        hf_label = QLabel("HF")
        hf_label.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        hf_label.setToolTip("HF Energy (slew breathing proxy)")
        life_row.addWidget(hf_label)
        self.hf_value = QLabel("---")
        self.hf_value.setStyleSheet(
            f"color: {COLORS['text']}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};")
        life_row.addWidget(self.hf_value)

        life_row.addSpacing(8)

        # DC Shift: waveform mean (TAPE sag indicator)
        dc_label = QLabel("DC")
        dc_label.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        dc_label.setToolTip("DC Shift (TAPE sag micro-fluctuation)")
        life_row.addWidget(dc_label)
        self.dc_value = QLabel("---")
        self.dc_value.setStyleSheet(
            f"color: {COLORS['text']}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};")
        life_row.addWidget(self.dc_value)

        life_row.addStretch()
        layout.addLayout(life_row)

        # ── Waveform display ──
        wave_row = QHBoxLayout()
        wave_label = QLabel("WAVEFORM")
        wave_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        wave_row.addWidget(wave_label)

        self.wave_enable_cb = QCheckBox("Capture")
        self.wave_enable_cb.setChecked(False)
        self.wave_enable_cb.setStyleSheet(f"color: {COLORS['text']}; font-size: {FONT_SIZES['small']}px;")
        self.wave_enable_cb.toggled.connect(self._on_wave_enable_toggled)
        wave_row.addWidget(self.wave_enable_cb)

        self.ideal_cb = QCheckBox("Ideal Overlay")
        self.ideal_cb.setChecked(True)
        self.ideal_cb.setStyleSheet(f"color: {COLORS['text']}; font-size: {FONT_SIZES['small']}px;")
        self.ideal_cb.toggled.connect(self._on_ideal_toggled)
        wave_row.addWidget(self.ideal_cb)

        self.delta_cb = QCheckBox("Delta")
        self.delta_cb.setStyleSheet(f"color: {COLORS['text']}; font-size: {FONT_SIZES['small']}px;")
        self.delta_cb.toggled.connect(self._on_delta_toggled)
        wave_row.addWidget(self.delta_cb)

        self.inv_btn = MidiButton("INV")
        self.inv_btn.setCheckable(True)
        self.inv_btn.setFixedWidth(40)
        self.inv_btn.setObjectName("telemetry_inv")
        self.inv_btn.setStyleSheet(f"font-size: {FONT_SIZES['tiny']}px;")
        self.inv_btn.toggled.connect(self._on_inv_toggled)
        self.inv_btn._get_main_frame = lambda: self.main_frame
        wave_row.addWidget(self.inv_btn)

        os_label = QLabel("OS")
        os_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        wave_row.addWidget(os_label)

        self.os_slider = MidiHSlider(main_frame_ref=self.main_frame)
        self.os_slider.setMinimum(-640)
        self.os_slider.setMaximum(640)
        self.os_slider.setValue(0)
        self.os_slider.setSingleStep(1)
        self.os_slider.setPageStep(64)
        self.os_slider.setFixedWidth(80)
        self.os_slider.setObjectName("telemetry_os")
        self.os_slider.valueChanged.connect(self._on_os_changed)
        wave_row.addWidget(self.os_slider)

        self.fine_btn = QPushButton("FINE")
        self.fine_btn.setCheckable(True)
        self.fine_btn.setFixedWidth(40)
        self.fine_btn.setStyleSheet(f"font-size: {FONT_SIZES['tiny']}px;")
        self.fine_btn.toggled.connect(self._on_fine_toggled)
        wave_row.addWidget(self.fine_btn)

        wave_row.addStretch()
        layout.addLayout(wave_row)

        # ── Square-mode precision row: BODY + OFS ──
        self.square_row = QHBoxLayout()

        body_label = QLabel("BODY")
        body_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        self.square_row.addWidget(body_label)
        self._body_label = body_label

        self.body_slider = MidiHSlider(main_frame_ref=self.main_frame)
        self.body_slider.setMinimum(250)   # 0.25x
        self.body_slider.setMaximum(1000)  # 1.0x
        self.body_slider.setValue(1000)     # Default: 1.0x (full peak)
        self.body_slider.setSingleStep(1)
        self.body_slider.setPageStep(50)
        self.body_slider.setFixedWidth(100)
        self.body_slider.setObjectName("telemetry_body")
        self.body_slider.valueChanged.connect(self._on_body_changed)
        self.square_row.addWidget(self.body_slider)

        ofs_label = QLabel("OFS")
        ofs_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;")
        self.square_row.addWidget(ofs_label)
        self._ofs_label = ofs_label

        self.ofs_slider = MidiHSlider(main_frame_ref=self.main_frame)
        self.ofs_slider.setMinimum(-200)   # -0.2
        self.ofs_slider.setMaximum(200)    # +0.2
        self.ofs_slider.setValue(0)         # Default: no offset
        self.ofs_slider.setSingleStep(1)
        self.ofs_slider.setPageStep(20)
        self.ofs_slider.setFixedWidth(100)
        self.ofs_slider.setObjectName("telemetry_v_offset")
        self.ofs_slider.valueChanged.connect(self._on_ofs_changed)
        self.square_row.addWidget(self.ofs_slider)

        self.square_row.addStretch()

        self.square_row_widget = QWidget()
        self.square_row_widget.setLayout(self.square_row)
        self.square_row_widget.setVisible(False)  # Hidden until Square mode
        layout.addWidget(self.square_row_widget)

        self.waveform_display = WaveformDisplay()
        layout.addWidget(self.waveform_display, stretch=1)

        # ── Bottom row: Snapshot + Export ──
        bottom_row = QHBoxLayout()

        self.auto_lock_btn = QPushButton("AUTO LOCK")
        self.auto_lock_btn.setStyleSheet(
            f"font-size: {FONT_SIZES['small']}px; font-weight: bold; "
            f"padding: 4px 14px;"
        )
        self.auto_lock_btn.clicked.connect(self._on_auto_lock)
        bottom_row.addWidget(self.auto_lock_btn)

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
        """Refresh UI — rate adapts to telemetry mode.

        Monitor mode (5Hz data): refresh at ~8fps (125ms) — lightweight.
        Capture mode (30Hz data): refresh at ~15fps (66ms) — smooth waveform.
        """
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(125)  # Start at monitor rate (~8fps)

    # ── Event Handlers ──

    def _on_slot_changed(self, index):
        self.controller.set_slot(index)
        self.core_lock_label.setText("")
        self._update_generator_context()

    def _on_source_changed(self, index):
        """Handle telemetry source tap point change."""
        self.controller.set_source(index)

    def _on_enable_toggled(self, checked):
        if checked:
            self._update_generator_context()
            # enable() starts the internal tap for meters/data — waveform is separate
            self.controller.enable(self.slot_combo.currentIndex())
            self.enable_btn.setText("Disable")
            # Monitor-only rate: meters update at ~8fps
            self._timer.setInterval(125)
        else:
            self.controller.disable()
            self.enable_btn.setText("Enable")
            # Sync UI: uncheck Capture
            self.wave_enable_cb.blockSignals(True)
            self.wave_enable_cb.setChecked(False)
            self.wave_enable_cb.blockSignals(False)
            self.waveform_display.set_capture_enabled(False)
            self.controller.current_waveform = None
            self.waveform_display.set_waveform(None)
            self._timer.setInterval(125)

    def _on_wave_enable_toggled(self, checked):
        slot = self.slot_combo.currentIndex()
        self.waveform_display.set_capture_enabled(checked)
        if checked:
            # Bump to capture rate for waveform data
            self.controller.set_rate(TelemetryController.CAPTURE_RATE)
            # Only create internal capture synth — external (HW) handles itself
            if not self.controller.waveform_active:
                if self.controller._capture_type == TelemetryController.CAPTURE_INTERNAL:
                    self.controller.enable_waveform(slot)
                self.controller.waveform_active = True
            self._timer.setInterval(66)  # ~15fps for smooth waveform
        else:
            if self.controller.waveform_active:
                if self.controller._capture_type == TelemetryController.CAPTURE_INTERNAL:
                    self.controller.disable_waveform(slot)
                self.controller.waveform_active = False
            self.controller.current_waveform = None  # Clear stale buffer
            self.waveform_display.set_waveform(None)
            # Drop back to monitor rate
            self.controller.set_rate(TelemetryController.MONITOR_RATE)
            self._timer.setInterval(125)  # ~8fps for info-only

    def _on_ideal_toggled(self, checked):
        self.waveform_display.set_show_ideal(checked)

    def _on_delta_toggled(self, checked):
        self.waveform_display.set_show_delta(checked)

    def _on_inv_toggled(self, checked):
        self.controller.phase_inverted = checked
        self.controller._err_history.clear()  # Reset rolling average on flip

    def _on_os_changed(self, value):
        self.controller.phase_offset = value / 1280.0  # -640..+640 maps to -0.5..+0.5
        self.controller._err_history.clear()

    def _on_fine_toggled(self, checked):
        self.os_slider.set_fine_mode(checked)

    def _on_cal_changed(self, value):
        self.controller.set_cal_gain(value)

    def _on_body_changed(self, value):
        self.controller.body_gain = value / 1000.0  # 250..1000 maps to 0.25..1.0
        self.controller._err_history.clear()

    def _on_ofs_changed(self, value):
        self.controller.v_offset = value / 1000.0  # -200..200 maps to -0.2..0.2
        self.controller._err_history.clear()

    def _on_auto_lock(self):
        """Run Nelder-Mead optimizer and sync sliders to result."""
        if not self.controller.enabled or self.controller.current_waveform is None:
            return

        self.auto_lock_btn.setText("LOCKING...")
        self.auto_lock_btn.setEnabled(False)
        self.auto_lock_btn.repaint()  # Force immediate visual update

        result = self.controller.optimize_twin()

        self.auto_lock_btn.setEnabled(True)

        if result is None:
            self.auto_lock_btn.setText("AUTO LOCK")
            return

        # Sync OS slider to optimized phase
        os_val = int(result['phase'] * 1280.0)
        self.os_slider.blockSignals(True)
        self.os_slider.setValue(max(-640, min(640, os_val)))
        self.os_slider.blockSignals(False)

        # Sync BODY/OFS sliders (Square mode)
        if result['shape'] == 'SQUARE':
            body_val = int(result['body_gain'] * 1000)
            self.body_slider.blockSignals(True)
            self.body_slider.setValue(max(250, min(1000, body_val)))
            self.body_slider.blockSignals(False)

            ofs_val = int(result['v_offset'] * 1000)
            self.ofs_slider.blockSignals(True)
            self.ofs_slider.setValue(max(-200, min(200, ofs_val)))
            self.ofs_slider.blockSignals(False)

        # Sync-back: push optimized SYM/SAT to the generator slot's P3/P4 sliders.
        # setValue triggers the full signal chain (UI → GeneratorSlot → OSC to SC).
        if self.main_frame is not None:
            slot_id = self.controller.target_slot + 1  # generator_grid uses 1-based
            slot_widget = self.main_frame.generator_grid.get_slot(slot_id)
            if slot_widget and len(slot_widget.custom_sliders) >= 4:
                sym_int = int(np.clip(result['sym'], 0.0, 1.0) * 1000)
                slot_widget.custom_sliders[2].setValue(sym_int)   # P3 = SYM
                sat_int = int(np.clip(result['sat'], 0.0, 1.0) * 1000)
                slot_widget.custom_sliders[3].setValue(sat_int)   # P4 = SAT

        # Update button text with final ERR
        self.auto_lock_btn.setText(f"LOCKED {result['error']:.3f}")
        # Reset button text after 3 seconds
        QTimer.singleShot(3000, lambda: self.auto_lock_btn.setText("AUTO LOCK"))

    def _on_snapshot(self):
        snap = self.controller.snapshot()
        if snap:
            import json
            from pathlib import Path
            home = str(Path.home())
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Telemetry Snapshot", home, "JSON (*.json)"
            )
            if path:
                with open(path, 'w') as f:
                    json.dump(snap, f, indent=2)

    def _on_export(self):
        from pathlib import Path
        home = str(Path.home())
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Telemetry History", home, "JSON (*.json)"
        )
        if path:
            self.controller.export_history(path)

    # ── Generator context ──

    def _update_generator_context(self):
        """Query main_frame for the generator on the current slot and update controller."""
        slot_id = self.slot_combo.currentIndex() + 1  # main_frame uses 1-based
        gen_name = ""
        synthdef = ""

        if self.main_frame is not None:
            synthdef_name = self.main_frame.active_generators.get(slot_id, "")
            if synthdef_name:
                synthdef = synthdef_name
                # Reverse-lookup display name from generator grid
                slot_widget = self.main_frame.generator_grid.get_slot(slot_id)
                if slot_widget:
                    gen_name = slot_widget.generator_type or ""

        self.controller.set_generator_context(gen_name, synthdef)
        self._update_param_labels()
        self._update_source_label(gen_name)

        # Cal gain only applies to internal capture
        is_internal = self.controller._capture_type == TelemetryController.CAPTURE_INTERNAL
        self.cal_frame_widget.setEnabled(is_internal)

    def _update_param_labels(self):
        """Update param header labels based on current generator."""
        labels = ["FRQ"] + self.controller.param_labels + ["ERR"]
        for i, lbl_widget in enumerate(self._param_header_labels):
            lbl_widget.setText(labels[i])

    def _update_source_label(self, gen_name: str):
        """Update the source label text."""
        if not gen_name:
            self.source_label.setText("---")
            self.source_label.setStyleSheet(
                f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['small']}px; "
                f"font-family: {MONO_FONT}; font-weight: bold; background: transparent;"
            )
        elif self.controller.is_hw_mode:
            self.source_label.setText(f"EXT INPUT  \u2022  {gen_name}")
            self.source_label.setStyleSheet(
                f"color: {COLORS['meter_warn']}; font-size: {FONT_SIZES['small']}px; "
                f"font-family: {MONO_FONT}; font-weight: bold; background: transparent;"
            )
        else:
            self.source_label.setText(f"INTERNAL  \u2022  {gen_name}")
            self.source_label.setStyleSheet(
                f"color: {COLORS['text']}; font-size: {FONT_SIZES['small']}px; "
                f"font-family: {MONO_FONT}; font-weight: bold; background: transparent;"
            )

    def _update_signal_dot(self, rms_stage1: float):
        """Update signal presence dot color based on stage 1 RMS."""
        if rms_stage1 > 0.005:
            # Signal present — green
            self.signal_dot.setStyleSheet(
                f"color: {COLORS['meter_normal']}; font-size: {FONT_SIZES['label']}px; background: transparent;"
            )
        else:
            # No signal — dim
            self.signal_dot.setStyleSheet(
                f"color: {COLORS['text_dim']}; font-size: {FONT_SIZES['label']}px; background: transparent;"
            )

    # ── Refresh ──

    def _refresh(self):
        """Update display from latest telemetry data."""
        data = self.controller.get_latest()
        if data is None:
            return

        # Parameters
        freq = data.get('freq', 0)
        self.param_values["FRQ"].setText(f"{freq:.1f}")

        # FRQ phase-lock indicator: green when locked, red when stuck at boundary
        phase_locked = not self.controller.has_phase_lock_warning(data)
        if phase_locked and freq > 10:
            frq_color = COLORS['meter_normal']
        elif freq < 1:
            frq_color = COLORS['text_dim']
        else:
            frq_color = COLORS['meter_clip']
        self.param_values["FRQ"].setStyleSheet(
            f"color: {frq_color}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};"
        )

        self.param_values["P0"].setText(f"{data.get('p0', 0):.3f}")
        self.param_values["P1"].setText(f"{data.get('p1', 0):.3f}")
        self.param_values["P2"].setText(f"{data.get('p2', 0):.3f}")
        self.param_values["P3"].setText(f"{data.get('p3', 0):.3f}")
        self.param_values["P4"].setText(f"{data.get('p4', 0):.3f}")

        # Dynamic REF shape label — high-contrast "Master Mode" indicator
        ref_name = getattr(self.controller, 'active_ref_name', '---')
        self._param_header_labels[3].setText(f"REF:{ref_name}")
        self._param_header_labels[3].setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;"
        )

        # Show BODY/OFS row only in Square mode
        self.square_row_widget.setVisible(ref_name == "SQUARE")

        # Live RMS error (Digital Twin match quality)
        err = self.controller.current_rms_error
        self.param_values["ERR"].setText(f"{err:.3f}")
        if err > 0 and err < 0.10:
            err_color = COLORS['meter_normal']
        elif err > 0 and err < 0.25:
            err_color = COLORS['meter_warn']
        else:
            err_color = COLORS['text_dim']
        self.param_values["ERR"].setStyleSheet(
            f"color: {err_color}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};"
        )

        # Stage meters
        rms1 = data.get('rms_stage1', 0)
        self.meter_stage1.set_value(rms1)
        self.meter_stage2.set_value(data.get('rms_stage2', 0))
        self.meter_stage3.set_value(data.get('rms_stage3', 0))

        # Signal presence dot
        self._update_signal_dot(rms1)

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

        # Living Proof metrics
        cf = self.controller.current_crest_factor
        if cf > 0.01:
            self.crest_value.setText(f"{cf:.2f}")
            # Color: green < 1.4 (compressed), yellow 1.4-1.7, white > 1.7 (peaky)
            if cf < 1.4:
                cf_color = COLORS['meter_warn']
            elif cf > 1.7:
                cf_color = COLORS['meter_normal']
            else:
                cf_color = COLORS['text']
            self.crest_value.setStyleSheet(
                f"color: {cf_color}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};")
        else:
            self.crest_value.setText("---")

        hf = self.controller.current_hf_energy
        if hf > 0.0001:
            self.hf_value.setText(f"{hf:.4f}")
        else:
            self.hf_value.setText("---")

        dc = self.controller.current_dc_shift
        if abs(dc) > 0.0001:
            self.dc_value.setText(f"{dc:+.4f}")
            dc_color = COLORS['meter_warn'] if abs(dc) > 0.01 else COLORS['text']
            self.dc_value.setStyleSheet(
                f"color: {dc_color}; font-size: {FONT_SIZES['label']}px; font-family: {MONO_FONT};")
        else:
            self.dc_value.setText("---")

        # Scope clipping flash (border goes red when peak > 0.90)
        self.waveform_display.set_peak_clipping(peak > 0.90)

        # Safety corridor: auto-enable in hw mode for PA calibration
        self.waveform_display.set_show_safety(self.controller.is_hw_mode)

        # Core Lock / Phase Inversion Warning
        bad = data.get('bad_value', 0)
        rms_err = self.controller.current_rms_error
        phase_locked = not self.controller.has_phase_lock_warning(data)
        if bad > 0:
            err_txt = "NaN" if bad == 1 else "∞"
            self.core_lock_label.setText(f"⚠ CORE LOCK: {err_txt}")
        elif rms_err > 0.40 and phase_locked and not self.controller.phase_inverted:
            self.core_lock_label.setText("⚠ PHASE INVERTED? Try INV")
        else:
            if self.core_lock_label.text():
                self.core_lock_label.setText("")

        # Waveform — inject actual waveform into data for forensic body measurement
        actual = self.controller.current_waveform
        if actual is not None:
            data['waveform'] = actual
        ideal = self.controller.get_ideal_waveform(data) if self.ideal_cb.isChecked() else None
        delta = self.controller.get_delta_waveform() if self.delta_cb.isChecked() else None
        self.waveform_display.set_waveform(actual, ideal, delta)

        # Frame count
        self.frame_count_label.setText(f"Frames: {len(self.controller.history)}")

    def closeEvent(self, event):
        """Disable telemetry when window closes."""
        self.controller.disable()  # Also stops waveform capture
        self._timer.stop()
        event.accept()
