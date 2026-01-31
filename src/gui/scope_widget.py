"""
Scope Widget - Hardware-Grade Oscilloscope Display
Kassutronics aesthetic: phosphor green trace on near-black background.

Placed in the footer bar, to the left of the Heat module.
Displays real-time waveform from any generator slot's intermediate bus.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QFont

import numpy as np

from .theme import COLORS, MONO_FONT, FONT_SIZES


# =============================================================================
# SCOPE DISPLAY COLORS (Kassutronics Aesthetic)
# =============================================================================

SCOPE_BG = '#0a0c0a'           # Near-black with slight green tint
SCOPE_TRACE = '#00ff88'        # Phosphor green
SCOPE_GRID = '#0a2a15'         # Subtle green grid
SCOPE_TRIGGER = '#ff6400'      # Orange trigger line
SCOPE_CONTROLS_BG = '#141414'  # Dark panel


# =============================================================================
# SCOPE DISPLAY WIDGET (QPainter-based waveform)
# =============================================================================

class ScopeDisplay(QWidget):
    """The actual oscilloscope display area with phosphor green trace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Waveform data (normalized -1 to +1)
        self.waveform = np.zeros(1024, dtype=np.float32)
        self.threshold = 0.0

        # Colors
        self._bg = QColor(SCOPE_BG)
        self._trace = QColor(SCOPE_TRACE)
        self._grid = QColor(SCOPE_GRID)
        self._trigger = QColor(SCOPE_TRIGGER)

    def set_waveform(self, data):
        """Update waveform data (numpy array, values -1 to +1)."""
        if data is not None and len(data) > 1:
            self.waveform = data
            self.update()

    def set_threshold(self, threshold):
        """Update trigger threshold display line."""
        self.threshold = threshold
        self.update()

    def paintEvent(self, event):
        """Draw scope display."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, self._bg)

        # Grid (8x6 divisions)
        self._draw_grid(painter, w, h)

        # Trigger line
        self._draw_trigger_line(painter, w, h)

        # Waveform trace
        self._draw_trace(painter, w, h)

    def _draw_grid(self, painter, w, h):
        """Draw subtle grid lines."""
        pen = QPen(self._grid)
        pen.setWidth(1)
        painter.setPen(pen)

        # Vertical lines (8 divisions)
        for i in range(1, 8):
            x = int(w * i / 8)
            painter.drawLine(x, 0, x, h)

        # Horizontal lines (6 divisions)
        for i in range(1, 6):
            y = int(h * i / 6)
            painter.drawLine(0, y, w, y)

        # Center line (brighter)
        center_pen = QPen(QColor('#1a4a2a'))
        center_pen.setWidth(1)
        painter.setPen(center_pen)
        painter.drawLine(0, h // 2, w, h // 2)

    def _draw_trigger_line(self, painter, w, h):
        """Draw trigger threshold as a dashed orange line."""
        # Map threshold (-1..+1) to y position
        y = int(h * (1.0 - (self.threshold + 1.0) / 2.0))
        y = max(0, min(h - 1, y))

        pen = QPen(self._trigger)
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(0, y, w, y)

    def _draw_trace(self, painter, w, h):
        """Draw phosphor green waveform trace."""
        data = self.waveform
        if len(data) < 2:
            return

        pen = QPen(self._trace)
        pen.setWidth(2)
        painter.setPen(pen)

        path = QPainterPath()
        num_points = len(data)

        for i in range(num_points):
            x = w * i / (num_points - 1)
            # Map -1..+1 to bottom..top
            val = float(data[i])
            y = h * (1.0 - (val + 1.0) / 2.0)
            y = max(0.0, min(float(h - 1), y))

            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.drawPath(path)


# =============================================================================
# SCOPE WIDGET (display + controls)
# =============================================================================

class ScopeWidget(QFrame):
    """Complete scope module for the footer bar.

    Contains:
    - Waveform display (top)
    - Controls: slot buttons (1-8), trigger drag, freeze button (bottom)
    """

    # Signals
    slot_changed = pyqtSignal(int)         # 0-indexed slot
    threshold_changed = pyqtSignal(float)  # -1.0 to 1.0
    freeze_changed = pyqtSignal(bool)      # True = frozen

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scopeModule")
        self.setFixedWidth(280)
        self.setFixedHeight(150)

        self._frozen = False
        self._active_slot = 0  # 0-indexed
        self._threshold = 0.0

        self._build_ui()

    def _build_ui(self):
        """Build scope UI layout."""
        self.setStyleSheet(f"""
            QFrame#scopeModule {{
                background-color: {SCOPE_CONTROLS_BG};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(4)

        title = QLabel("SCOPE")
        title.setFont(QFont(MONO_FONT, FONT_SIZES['tiny'], QFont.Bold))
        title.setStyleSheet(f"color: {SCOPE_TRACE}; background: transparent; border: none;")
        title_row.addWidget(title)
        title_row.addStretch(1)

        # Freeze button
        self._freeze_btn = QPushButton("FRZ")
        self._freeze_btn.setFixedSize(32, 16)
        self._freeze_btn.setFont(QFont(MONO_FONT, 8, QFont.Bold))
        self._freeze_btn.setCheckable(True)
        self._freeze_btn.setStyleSheet(self._freeze_style(False))
        self._freeze_btn.clicked.connect(self._on_freeze_clicked)
        title_row.addWidget(self._freeze_btn)

        layout.addLayout(title_row)

        # Waveform display
        self._display = ScopeDisplay()
        self._display.setStyleSheet(f"""
            border: 1px solid {COLORS['border']};
            border-radius: 2px;
        """)
        layout.addWidget(self._display, stretch=1)

        # Controls row
        controls = QHBoxLayout()
        controls.setSpacing(2)
        controls.setContentsMargins(0, 0, 0, 0)

        # Slot buttons (1-8)
        self._slot_btns = []
        for i in range(8):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(22, 16)
            btn.setFont(QFont(MONO_FONT, 8, QFont.Bold))
            btn.setStyleSheet(self._slot_btn_style(i == 0))
            btn.clicked.connect(lambda checked, idx=i: self._on_slot_clicked(idx))
            self._slot_btns.append(btn)
            controls.addWidget(btn)

        controls.addSpacing(4)

        # Trigger threshold label (drag to adjust)
        trig_label = QLabel("TRIG")
        trig_label.setFont(QFont(MONO_FONT, 7))
        trig_label.setStyleSheet(f"color: {SCOPE_TRIGGER}; background: transparent; border: none;")
        controls.addWidget(trig_label)

        # Threshold value display (drag to adjust)
        self._trig_value = TrigDragLabel("0.00")
        self._trig_value.value_changed.connect(self._on_threshold_changed)
        controls.addWidget(self._trig_value)

        controls.addStretch(1)

        layout.addLayout(controls)

    def _on_slot_clicked(self, slot_idx):
        """Handle slot button click."""
        self._active_slot = slot_idx
        for i, btn in enumerate(self._slot_btns):
            btn.setStyleSheet(self._slot_btn_style(i == slot_idx))
        self.slot_changed.emit(slot_idx)

    def _on_freeze_clicked(self):
        """Handle freeze button toggle."""
        self._frozen = self._freeze_btn.isChecked()
        self._freeze_btn.setStyleSheet(self._freeze_style(self._frozen))
        self.freeze_changed.emit(self._frozen)

    def _on_threshold_changed(self, value):
        """Handle threshold drag change."""
        self._threshold = value
        self._display.set_threshold(value)
        self.threshold_changed.emit(value)

    def set_waveform(self, data):
        """Update the scope display with new waveform data."""
        self._display.set_waveform(data)

    def set_active_slot(self, slot_idx):
        """Programmatically set the active slot (0-indexed)."""
        if 0 <= slot_idx < 8:
            self._active_slot = slot_idx
            for i, btn in enumerate(self._slot_btns):
                btn.setStyleSheet(self._slot_btn_style(i == slot_idx))

    # ── Style helpers ──

    def _slot_btn_style(self, active):
        """Slot button style - inverted green when active."""
        if active:
            return f"""
                QPushButton {{
                    background-color: #000000;
                    color: {SCOPE_TRACE};
                    border: 1px solid {SCOPE_TRACE};
                    border-radius: 2px;
                    padding: 0px;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    color: {COLORS['text']};
                    border-color: {COLORS['text_dim']};
                }}
            """

    def _freeze_style(self, frozen):
        """Freeze button style."""
        if frozen:
            return f"""
                QPushButton {{
                    background-color: {SCOPE_TRIGGER};
                    color: #000000;
                    border: 1px solid {SCOPE_TRIGGER};
                    border-radius: 2px;
                    padding: 0px;
                    font-weight: bold;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    color: {COLORS['text']};
                    border-color: {COLORS['text_dim']};
                }}
            """


# =============================================================================
# TRIGGER DRAG LABEL (drag up/down to adjust threshold)
# =============================================================================

class TrigDragLabel(QLabel):
    """Small label that supports drag-to-adjust for trigger threshold.

    Drag up to increase, drag down to decrease. Range: -1.0 to 1.0.
    """

    value_changed = pyqtSignal(float)

    def __init__(self, text="0.00", parent=None):
        super().__init__(text, parent)
        self._value = 0.0
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_value = 0.0

        self.setFixedSize(36, 16)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont(MONO_FONT, 8))
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['background_dark']};
                color: {SCOPE_TRIGGER};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
            }}
        """)
        self.setCursor(Qt.SizeVerCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_y = event.globalY()
            self._drag_start_value = self._value

    def mouseMoveEvent(self, event):
        if self._dragging:
            dy = self._drag_start_y - event.globalY()
            sensitivity = 0.005
            if event.modifiers() & Qt.ShiftModifier:
                sensitivity = 0.001
            new_val = self._drag_start_value + dy * sensitivity
            new_val = max(-1.0, min(1.0, new_val))
            if new_val != self._value:
                self._value = new_val
                self.setText(f"{new_val:.2f}")
                self.value_changed.emit(new_val)

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def mouseDoubleClickEvent(self, event):
        """Double-click resets to 0.0."""
        self._value = 0.0
        self.setText("0.00")
        self.value_changed.emit(0.0)
