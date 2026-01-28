"""
Mixer Panel Component
Per-generator channel strips with volume, mute, solo, and level metering

Signal flow: Generator → Channel Strip → Master Bus
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient

from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES, pan_slider_style
from .widgets import DragSlider, MiniKnob, MidiButton
from src.config import SIZES


class MiniMeter(QWidget):
    """Compact stereo level meter for channel strips."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level_l = 0.0
        self.level_r = 0.0
        self.setFixedWidth(20)  # Fixed width
        self.setMinimumHeight(40)  # Can grow taller
        
    def set_levels(self, left, right):
        """Update meter levels (0.0 to 1.0)."""
        # Convert to dB-scaled display
        self.level_l = self._amp_to_meter(left)
        self.level_r = self._amp_to_meter(right)
        self.update()
    
    def _amp_to_meter(self, amp):
        """Convert linear amplitude to meter display value."""
        import math
        if amp < 0.001:
            return 0.0
        db = 20 * math.log10(amp)
        meter = (db + 60) / 60  # -60dB = 0, 0dB = 1
        return max(0.0, min(1.0, meter))
        
    def paintEvent(self, event):
        """Draw the mini meter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        bar_width = 7
        gap = 2
        margin = 2
        
        left_x = margin
        right_x = margin + bar_width + gap
        
        # Background
        bg_color = QColor(COLORS['background_dark'])
        painter.fillRect(left_x, margin, bar_width, h - margin * 2, bg_color)
        painter.fillRect(right_x, margin, bar_width, h - margin * 2, bg_color)
        
        # Level bars
        meter_h = h - margin * 2
        self._draw_bar(painter, left_x, margin, bar_width, meter_h, self.level_l)
        self._draw_bar(painter, right_x, margin, bar_width, meter_h, self.level_r)
        
        # Borders
        border_color = QColor(COLORS['border'])
        painter.setPen(border_color)
        painter.drawRect(left_x, margin, bar_width - 1, meter_h - 1)
        painter.drawRect(right_x, margin, bar_width - 1, meter_h - 1)
        
    def _draw_bar(self, painter, x, y, width, height, level):
        """Draw a single meter bar with gradient."""
        if level < 0.001:
            return
            
        bar_h = int(level * height)
        bar_y = y + height - bar_h
        
        # Green -> Yellow -> Red gradient
        gradient = QLinearGradient(x, y + height, x, y)
        gradient.setColorAt(0.0, QColor('#22aa22'))
        gradient.setColorAt(0.6, QColor('#22aa22'))
        gradient.setColorAt(0.75, QColor('#aaaa22'))
        gradient.setColorAt(0.9, QColor('#aa2222'))
        gradient.setColorAt(1.0, QColor('#ff2222'))
        
        painter.fillRect(x, bar_y, width, bar_h, gradient)


class ChannelStrip(QWidget):
    """Individual channel strip with fader, meter, and EQ."""

    volume_changed = pyqtSignal(int, float)
    mute_toggled = pyqtSignal(int, bool)
    solo_toggled = pyqtSignal(int, bool)
    gain_changed = pyqtSignal(int, int)  # channel_id, gain_db (0, 6, or 12)
    pan_changed = pyqtSignal(int, float)  # channel_id, pan (-1 to 1)
    eq_changed = pyqtSignal(int, str, float)  # channel_id, band
    fx1_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    fx2_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    fx3_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    fx4_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    # Legacy signal aliases
    echo_send_changed = fx1_send_changed
    verb_send_changed = fx2_send_changed
    
    # Gain stages: dB value, display text, color style
    GAIN_STAGES = [
        (0, "0", 'disabled'),  # Unity - grey
        (6, "+6", 'submenu'),  # +6dB - orange
        (12, "+12", 'warning'),  # +12dB - amber
    ]
    
    def __init__(self, channel_id, label="", parent=None):
        super().__init__(parent)
        self.channel_id = channel_id
        self.label_text = label
        self.muted = False
        self.soloed = False
        self.gain_index = 0  # Index into GAIN_STAGES
        self.pan_value = 0.0  # -1 (L) to 1 (R), 0 = center
        # Cut button state
        self.lo_cut_active = False
        self.hi_cut_active = False
        self.lo_cut_saved = 100  # Saved knob value when cut is engaged
        self.hi_cut_saved = 100
        self.setup_ui()
        
    def setup_ui(self):
        """Create channel strip."""
        self.setMaximumWidth(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 5, 2, 5)
        layout.setSpacing(3)
        
        # Channel label
        self._label = QLabel(self.label_text or str(self.channel_id))
        self._label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(f"color: {COLORS['text_bright']}; font-weight: bold;")
        layout.addWidget(self._label)
        
        # === EQ Section (3 mini knobs: HI, MID, LO) ===
        eq_layout = QVBoxLayout()
        eq_layout.setSpacing(1)
        eq_layout.setContentsMargins(0, 0, 0, 2)
        
        # EQ label style
        eq_label_style = f"color: {COLORS['text_bright']}; font-size: {FONT_SIZES['tiny']}px; font-weight: bold;" 

        # HI knob with label
        hi_label = QLabel("HI")
        hi_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        hi_label.setStyleSheet(eq_label_style)
        hi_label.setAlignment(Qt.AlignCenter)
        eq_layout.addWidget(hi_label)
        self.eq_hi = MiniKnob()
        self.eq_hi.setObjectName(f"mixer{self.channel_id}_eq_hi")
        self.eq_hi.setToolTip("HI EQ: >2.5kHz (double-click reset)")
        self.eq_hi.valueChanged.connect(lambda v: self._on_eq_changed('hi', v))
        eq_layout.addWidget(self.eq_hi, alignment=Qt.AlignCenter)
        
        # MID knob with label
        mid_label = QLabel("MID")
        mid_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        mid_label.setStyleSheet(eq_label_style)
        mid_label.setAlignment(Qt.AlignCenter)
        eq_layout.addWidget(mid_label)
        self.eq_mid = MiniKnob()
        self.eq_mid.setObjectName(f"mixer{self.channel_id}_eq_mid")
        self.eq_mid.setToolTip("MID EQ: 250Hz-2.5kHz (double-click reset)")
        self.eq_mid.valueChanged.connect(lambda v: self._on_eq_changed('mid', v))
        eq_layout.addWidget(self.eq_mid, alignment=Qt.AlignCenter)
        
        # LO knob with label
        lo_label = QLabel("LO")
        lo_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        lo_label.setStyleSheet(eq_label_style)
        lo_label.setAlignment(Qt.AlignCenter)
        eq_layout.addWidget(lo_label)
        self.eq_lo = MiniKnob()
        self.eq_lo.setObjectName(f"mixer{self.channel_id}_eq_lo")
        self.eq_lo.setToolTip("LO EQ: <250Hz (double-click reset)")
        self.eq_lo.valueChanged.connect(lambda v: self._on_eq_changed('lo', v))
        eq_layout.addWidget(self.eq_lo, alignment=Qt.AlignCenter)
        
        # Lo Cut / Hi Cut buttons row
        cut_layout = QHBoxLayout()
        cut_layout.setSpacing(2)
        cut_layout.setContentsMargins(0, 2, 0, 0)
        
        self.lo_cut_btn = QPushButton("LC")
        self.lo_cut_btn.setFixedSize(20, 14)
        self.lo_cut_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.lo_cut_btn.setToolTip("Lo Cut: kill frequencies below 250Hz")
        self.lo_cut_btn.clicked.connect(self.toggle_lo_cut)
        self._update_lo_cut_style()
        cut_layout.addWidget(self.lo_cut_btn)
        
        self.hi_cut_btn = QPushButton("HC")
        self.hi_cut_btn.setFixedSize(20, 14)
        self.hi_cut_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.hi_cut_btn.setToolTip("Hi Cut: kill frequencies above 2.5kHz")
        self.hi_cut_btn.clicked.connect(self.toggle_hi_cut)
        self._update_hi_cut_style()
        cut_layout.addWidget(self.hi_cut_btn)
        
        eq_layout.addLayout(cut_layout)
        
        layout.addLayout(eq_layout)
        
        # === FX Sends (4 slots in 2x2 grid) ===
        sends_layout = QVBoxLayout()
        sends_layout.setSpacing(1)
        sends_layout.setContentsMargins(0, 2, 0, 2)

        # Row 1: FX1, FX2
        sends_row1 = QHBoxLayout()
        sends_row1.setSpacing(1)

        self.fx1_send = MiniKnob()
        self.fx1_send.setObjectName(f"chan_{self.channel_id}_fx1")
        self.fx1_send.setToolTip("FX1 Send")
        self.fx1_send.setValue(0)
        self.fx1_send.valueChanged.connect(self._on_fx1_send_changed)
        sends_row1.addWidget(self.fx1_send)

        self.fx2_send = MiniKnob()
        self.fx2_send.setObjectName(f"chan_{self.channel_id}_fx2")
        self.fx2_send.setToolTip("FX2 Send")
        self.fx2_send.setValue(0)
        self.fx2_send.valueChanged.connect(self._on_fx2_send_changed)
        sends_row1.addWidget(self.fx2_send)

        sends_layout.addLayout(sends_row1)

        # Row 2: FX3, FX4
        sends_row2 = QHBoxLayout()
        sends_row2.setSpacing(1)

        self.fx3_send = MiniKnob()
        self.fx3_send.setObjectName(f"chan_{self.channel_id}_fx3")
        self.fx3_send.setToolTip("FX3 Send")
        self.fx3_send.setValue(0)
        self.fx3_send.valueChanged.connect(self._on_fx3_send_changed)
        sends_row2.addWidget(self.fx3_send)

        self.fx4_send = MiniKnob()
        self.fx4_send.setObjectName(f"chan_{self.channel_id}_fx4")
        self.fx4_send.setToolTip("FX4 Send")
        self.fx4_send.setValue(0)
        self.fx4_send.valueChanged.connect(self._on_fx4_send_changed)
        sends_row2.addWidget(self.fx4_send)

        sends_layout.addLayout(sends_row2)

        # Legacy aliases
        self.echo_send = self.fx1_send
        self.verb_send = self.fx2_send

        layout.addLayout(sends_layout)
        
        # Fader + Meter side by side
        fader_meter_layout = QHBoxLayout()
        fader_meter_layout.setSpacing(2)
        fader_meter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Fader - no alignment constraint so it fills vertical space
        self.fader = DragSlider()
        self.fader.setObjectName(f"mixer{self.channel_id}_fader")
        self.fader.setFixedWidth(SIZES['slider_width_narrow'])
        self.fader.setValue(800)
        self.fader.setMinimumHeight(60)  # Reduced from 80 to accommodate 2x2 FX sends
        self.fader.valueChanged.connect(self.on_fader_changed)
        fader_meter_layout.addWidget(self.fader)  # No alignment - let it stretch
        
        # Mini meter - also stretches with fader
        self.meter = MiniMeter()
        fader_meter_layout.addWidget(self.meter)  # No alignment - let it stretch
        
        layout.addLayout(fader_meter_layout, stretch=1)  # Let faders grow
        
        # Pan slider (horizontal, compact) - double-click to center
        from PyQt5.QtWidgets import QSlider

        class PanSlider(QSlider):
            """Pan slider with double-click to center and MIDI support."""

            def __init__(self, orientation, parent=None):
                super().__init__(orientation, parent)
                self._midi_armed = False
                self._midi_mapped = False
                # Modulation visualization state
                self._mod_range_min = None
                self._mod_range_max = None
                self._mod_current = None
                self._mod_color = QColor('#00ff66')
                # Boid glow state
                self._boid_glow_intensity = 0.0
                self._boid_glow_muted = False

            def mouseDoubleClickEvent(self, event):
                self.setValue(0)  # Center on double-click

            def set_midi_armed(self, armed):
                self._midi_armed = armed
                self.update()

            def set_midi_mapped(self, mapped):
                self._midi_mapped = mapped
                self.update()

            def set_modulation_range(self, min_norm: float, max_norm: float,
                                     inner_min: float = None, inner_max: float = None,
                                     color: 'QColor' = None):
                """Set modulation range for visualization (normalized 0-1 values)."""
                self._mod_range_min = min_norm
                self._mod_range_max = max_norm
                if color:
                    self._mod_color = color
                self.update()

            def set_modulated_value(self, norm_value: float):
                """Set current modulated value for animated indicator (normalized 0-1)."""
                self._mod_current = norm_value
                self.update()

            def clear_modulation(self):
                """Clear modulation visualization."""
                self._mod_range_min = None
                self._mod_range_max = None
                self._mod_current = None
                self.update()

            def has_modulation(self) -> bool:
                """Return True if modulation range is set."""
                return self._mod_range_min is not None

            def set_boid_glow(self, intensity: float, muted: bool = False):
                """Set boid glow intensity (0.0-1.0) and muted state."""
                self._boid_glow_intensity = intensity
                self._boid_glow_muted = muted
                self.update()

            def _get_main_frame(self):
                widget = self.window()
                while widget:
                    if hasattr(widget, 'cc_mapping_manager'):
                        return widget
                    widget = widget.parent()
                return None

            def _start_midi_learn(self):
                main_frame = self._get_main_frame()
                if main_frame:
                    main_frame.cc_learn_manager.start_learn(self)

            def _clear_midi_mapping(self):
                main_frame = self._get_main_frame()
                if main_frame:
                    main_frame.cc_mapping_manager.remove_mapping(self)
                    self.set_midi_mapped(False)

            def contextMenuEvent(self, event):
                from PyQt5.QtWidgets import QMenu
                menu = QMenu(self)
                main_frame = self._get_main_frame()
                if not main_frame:
                    return
                if self._midi_mapped:
                    menu.addAction("Clear MIDI Mapping", self._clear_midi_mapping)
                menu.addAction("MIDI Learn", self._start_midi_learn)
                menu.exec_(event.globalPos())

            def paintEvent(self, event):
                super().paintEvent(event)
                from PyQt5.QtGui import QPainter, QColor, QPen
                from PyQt5.QtCore import Qt

                painter = QPainter(self)

                # Draw modulation range (horizontal bar at top)
                if self._mod_range_min is not None and self._mod_range_max is not None:
                    mod_color = QColor(self._mod_color)
                    mod_color.setAlpha(100)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(mod_color)
                    # _mod_range_min/max are 0-1, map to widget width
                    x_min = int(self._mod_range_min * self.width())
                    x_max = int(self._mod_range_max * self.width())
                    painter.drawRect(x_min, 0, x_max - x_min, 4)

                # Draw current modulated value (vertical line)
                if self._mod_current is not None:
                    painter.setPen(QPen(self._mod_color, 2))
                    x_pos = int(self._mod_current * self.width())
                    painter.drawLine(x_pos, 0, x_pos, self.height())

                # Draw MIDI mapped badge
                if self._midi_mapped:
                    painter.setBrush(QColor('#FF00FF'))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(self.width() - 6, 0, 4, 4)

                # Draw boid glow
                if self._boid_glow_intensity > 0:
                    # Gray for muted, purple for active
                    glow_color = QColor('#666666') if self._boid_glow_muted else QColor(COLORS['boid'])
                    if self._boid_glow_intensity > 0.8:
                        glow_color.setAlpha(255 if not self._boid_glow_muted else 180)
                        pen_width = 3
                    else:
                        alpha = int(self._boid_glow_intensity * (150 if self._boid_glow_muted else 200))
                        glow_color.setAlpha(alpha)
                        pen_width = 2
                    painter.setPen(QPen(glow_color, pen_width))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)

                painter.end()

        self.pan_slider = PanSlider(Qt.Horizontal)
        self.pan_slider.setObjectName(f"chan_{self.channel_id}_pan")
        self.pan_slider.setRange(-100, 100)  # -100 = L, 0 = C, 100 = R
        self.pan_slider.setValue(0)
        self.pan_slider.setFixedWidth(38)
        self.pan_slider.setFixedHeight(16)
        self.pan_slider.setToolTip("Pan: L ← C → R (double-click to center)")
        self.pan_slider.valueChanged.connect(self.on_pan_changed)
        self.pan_slider.setStyleSheet(pan_slider_style())
        layout.addWidget(self.pan_slider, alignment=Qt.AlignCenter)
        
        # Mute/Solo/Gain buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(2)

        self.mute_btn = MidiButton("M")
        self.mute_btn.setObjectName(f"mixer{self.channel_id}_mute")
        self.mute_btn.setFixedSize(*SIZES['button_small'])
        self.mute_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro'], QFont.Bold))
        self.mute_btn.setStyleSheet(button_style('disabled'))
        self.mute_btn.clicked.connect(self.toggle_mute)
        btn_layout.addWidget(self.mute_btn, alignment=Qt.AlignCenter)

        self.solo_btn = MidiButton("S")
        self.solo_btn.setObjectName(f"mixer{self.channel_id}_solo")
        self.solo_btn.setFixedSize(*SIZES['button_small'])
        self.solo_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro'], QFont.Bold))
        self.solo_btn.setStyleSheet(button_style('disabled'))
        self.solo_btn.clicked.connect(self.toggle_solo)
        btn_layout.addWidget(self.solo_btn, alignment=Qt.AlignCenter)
        
        # Gain stage button (cycles 0dB -> +6dB -> +12dB)
        self.gain_btn = MidiButton("0")
        self.gain_btn.setObjectName(f"mixer{self.channel_id}_gain")
        self.gain_btn.setFixedSize(*SIZES['button_small'])
        self.gain_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro'], QFont.Bold))
        self.gain_btn.setStyleSheet(button_style('disabled'))
        self.gain_btn.clicked.connect(self.cycle_gain)
        self.gain_btn.setToolTip("Gain stage: click to cycle 0dB → +6dB → +12dB")
        btn_layout.addWidget(self.gain_btn, alignment=Qt.AlignCenter)
        
        layout.addLayout(btn_layout)
    
    def _on_eq_changed(self, band, value):
        """Handle EQ knob change. Convert 0-200 to 0-2 linear."""
        linear = value / 100.0
        self.eq_changed.emit(self.channel_id, band, linear)
    
    def _on_fx1_send_changed(self, value):
        """Handle FX1 send knob change. Convert 0-200 to 0-1."""
        send_level = value / 200.0
        self.fx1_send_changed.emit(self.channel_id, send_level)

    def _on_fx2_send_changed(self, value):
        """Handle FX2 send knob change. Convert 0-200 to 0-1."""
        send_level = value / 200.0
        self.fx2_send_changed.emit(self.channel_id, send_level)

    def _on_fx3_send_changed(self, value):
        """Handle FX3 send knob change. Convert 0-200 to 0-1."""
        send_level = value / 200.0
        self.fx3_send_changed.emit(self.channel_id, send_level)

    def _on_fx4_send_changed(self, value):
        """Handle FX4 send knob change. Convert 0-200 to 0-1."""
        send_level = value / 200.0
        self.fx4_send_changed.emit(self.channel_id, send_level)

    # Legacy handler aliases
    _on_echo_send_changed = _on_fx1_send_changed
    _on_verb_send_changed = _on_fx2_send_changed
    
    def set_levels(self, left, right):
        """Update the channel meter levels."""
        self.meter.set_levels(left, right)
        
    def set_active(self, active):
        """Update visual state based on whether generator is active."""
        if active:
            self._label.setStyleSheet(f"color: {COLORS['text']};")
            # Keep mute/solo/gain state - just update label brightness
            # Re-apply button styles based on current state
            if self.muted:
                self.mute_btn.setStyleSheet(button_style('warning'))
            else:
                self.mute_btn.setStyleSheet(button_style('disabled'))
            if self.soloed:
                self.solo_btn.setStyleSheet(button_style('submenu'))
            else:
                self.solo_btn.setStyleSheet(button_style('disabled'))
            # Re-apply gain button style
            _, _, style = self.GAIN_STAGES[self.gain_index]
            self.gain_btn.setStyleSheet(button_style(style))
            # Re-apply cut button styles
            self._update_lo_cut_style()
            self._update_hi_cut_style()
        else:
            self._label.setStyleSheet(f"color: {COLORS['text_dim']};")
            # Dim the buttons when inactive but keep state
            dim_btn = f"""
                QPushButton {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                }}
            """
            self.mute_btn.setStyleSheet(dim_btn)
            self.solo_btn.setStyleSheet(dim_btn)
            self.gain_btn.setStyleSheet(dim_btn)
            self.lo_cut_btn.setStyleSheet(dim_btn)
            self.hi_cut_btn.setStyleSheet(dim_btn)
            # Clear meter when inactive
            self.meter.set_levels(0, 0)
    
    def reset_state(self):
        """Reset mute/solo/gain/pan/EQ to default state."""
        self.muted = False
        self.soloed = False
        self.gain_index = 0
        self.pan_value = 0.0
        self.lo_cut_active = False
        self.hi_cut_active = False
        self.lo_cut_saved = 100
        self.hi_cut_saved = 100
        self.mute_btn.setStyleSheet(button_style('disabled'))
        self.solo_btn.setStyleSheet(button_style('disabled'))
        self.gain_btn.setText("0")
        self.gain_btn.setStyleSheet(button_style('disabled'))
        self.pan_slider.setValue(0)
        # Reset EQ to unity
        self.eq_hi.setValue(100)
        self.eq_mid.setValue(100)
        self.eq_lo.setValue(100)
        self._update_lo_cut_style()
        self._update_hi_cut_style()
        
    def toggle_lo_cut(self):
        """Toggle lo cut - kills LO band, restores on second click."""
        if self.lo_cut_active:
            # Restore previous value
            self.eq_lo.setValue(self.lo_cut_saved)
        else:
            # Save current and kill
            self.lo_cut_saved = self.eq_lo.value()
            self.eq_lo.setValue(0)
        self.lo_cut_active = not self.lo_cut_active
        self._update_lo_cut_style()
    
    def toggle_hi_cut(self):
        """Toggle hi cut - kills HI band, restores on second click."""
        if self.hi_cut_active:
            # Restore previous value
            self.eq_hi.setValue(self.hi_cut_saved)
        else:
            # Save current and kill
            self.hi_cut_saved = self.eq_hi.value()
            self.eq_hi.setValue(0)
        self.hi_cut_active = not self.hi_cut_active
        self._update_hi_cut_style()
    
    def _update_lo_cut_style(self):
        """Update Lo Cut button appearance."""
        if self.lo_cut_active:
            self.lo_cut_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['warning']};
                    border-radius: 2px;
                }}
            """)
        else:
            self.lo_cut_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                }}
            """)
    
    def _update_hi_cut_style(self):
        """Update Hi Cut button appearance."""
        if self.hi_cut_active:
            self.hi_cut_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['warning']};
                    border-radius: 2px;
                }}
            """)
        else:
            self.hi_cut_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                }}
            """)
        
    def on_fader_changed(self, value):
        """Handle fader movement."""
        normalized = value / 1000.0
        # Calculate dB for popup
        if normalized < 0.001:
            db_text = "-∞"
        else:
            import math
            db = 20 * math.log10(normalized)
            db_text = f"{db:.1f}dB"
        self.fader.show_drag_value(db_text)
        self.volume_changed.emit(self.channel_id, normalized)
    
    def on_pan_changed(self, value):
        """Handle pan slider movement."""
        self.pan_value = value / 100.0  # Convert to -1 to 1 range
        
        # Show drag tooltip
        if value < -5:
            pan_text = f"L{abs(value)}"
        elif value > 5:
            pan_text = f"R{value}"
        else:
            pan_text = "C"
        
        from PyQt5.QtWidgets import QToolTip
        from PyQt5.QtCore import QPoint
        pos = self.pan_slider.mapToGlobal(QPoint(self.pan_slider.width() // 2, -20))
        QToolTip.showText(pos, pan_text, self.pan_slider)
        
        self.pan_changed.emit(self.channel_id, self.pan_value)
        
    def toggle_mute(self):
        """Toggle mute state."""
        self.muted = not self.muted
        if self.muted:
            self.mute_btn.setStyleSheet(button_style('warning'))
        else:
            self.mute_btn.setStyleSheet(button_style('disabled'))
        self.mute_toggled.emit(self.channel_id, self.muted)
        
    def toggle_solo(self):
        """Toggle solo state."""
        self.soloed = not self.soloed
        if self.soloed:
            self.solo_btn.setStyleSheet(button_style('submenu'))
        else:
            self.solo_btn.setStyleSheet(button_style('disabled'))
        self.solo_toggled.emit(self.channel_id, self.soloed)
    
    def cycle_gain(self):
        """Cycle through gain stages: 0dB -> +6dB -> +12dB -> 0dB."""
        self.gain_index = (self.gain_index + 1) % len(self.GAIN_STAGES)
        db, text, style = self.GAIN_STAGES[self.gain_index]
        self.gain_btn.setText(text)
        self.gain_btn.setStyleSheet(button_style(style))
        self.gain_changed.emit(self.channel_id, db)
    
    def get_strip_state(self):
        """Return current strip state for syncing to SC after generator change."""
        return {
            'volume': self.fader.value() / 1000.0,
            'pan': self.pan_value,
            'muted': self.muted,
            'soloed': self.soloed,
            'gain_db': self.GAIN_STAGES[self.gain_index][0],
            'eq_lo': self.eq_lo.value() / 100.0,  # 0-2 linear
            'eq_mid': self.eq_mid.value() / 100.0,
            'eq_hi': self.eq_hi.value() / 100.0,
        }

    def get_state(self) -> dict:
        """
        Get current channel state for preset save.
        Returns dict with all channel strip settings (Phase 1 expanded).
        """
        return {
            # Original fields
            "volume": self.fader.value() / 1000.0,
            "pan": (self.pan_slider.value() + 100) / 200.0,  # Convert -100..100 to 0..1
            "mute": self.muted,
            "solo": self.soloed,
            # Phase 1 additions
            "eq_hi": self.eq_hi.value(),
            "eq_mid": self.eq_mid.value(),
            "eq_lo": self.eq_lo.value(),
            "gain": self.gain_index,
            "fx1_send": self.fx1_send.value(),
            "fx2_send": self.fx2_send.value(),
            "fx3_send": self.fx3_send.value(),
            "fx4_send": self.fx4_send.value(),
            # Legacy keys for backward compatibility
            "echo_send": self.fx1_send.value(),
            "verb_send": self.fx2_send.value(),
            "lo_cut": self.lo_cut_active,
            "hi_cut": self.hi_cut_active,
        }

    def set_state(self, state: dict):
        """
        Apply state from preset load.
        Args:
            state: dict from get_state() or preset file
        """
        # Volume
        vol = state.get("volume", 0.8)
        self.fader.blockSignals(True)
        self.fader.setValue(int(vol * 1000))
        self.fader.blockSignals(False)
        self.volume_changed.emit(self.channel_id, vol)

        # Pan (convert 0..1 back to -100..100)
        pan = state.get("pan", 0.5)
        pan_value = int((pan * 200) - 100)
        self.pan_slider.blockSignals(True)
        self.pan_slider.setValue(pan_value)
        self.pan_slider.blockSignals(False)
        self.pan_value = pan_value / 100.0
        self.pan_changed.emit(self.channel_id, self.pan_value)

        # Mute
        mute = state.get("mute", False)
        if mute != self.muted:
            self.toggle_mute()

        # Solo
        solo = state.get("solo", False)
        if solo != self.soloed:
            self.toggle_solo()

        # === Phase 1 additions ===

        # EQ Hi
        eq_hi = state.get("eq_hi", 100)
        self.eq_hi.blockSignals(True)
        self.eq_hi.setValue(eq_hi)
        self.eq_hi.blockSignals(False)
        self._on_eq_changed('hi', eq_hi)

        # EQ Mid
        eq_mid = state.get("eq_mid", 100)
        self.eq_mid.blockSignals(True)
        self.eq_mid.setValue(eq_mid)
        self.eq_mid.blockSignals(False)
        self._on_eq_changed('mid', eq_mid)

        # EQ Lo
        eq_lo = state.get("eq_lo", 100)
        self.eq_lo.blockSignals(True)
        self.eq_lo.setValue(eq_lo)
        self.eq_lo.blockSignals(False)
        self._on_eq_changed('lo', eq_lo)

        # Gain
        gain = state.get("gain", 0)
        if 0 <= gain < len(self.GAIN_STAGES):
            self.gain_index = gain
            db, text, style = self.GAIN_STAGES[self.gain_index]
            self.gain_btn.setText(text)
            self.gain_btn.setStyleSheet(button_style(style))
            self.gain_changed.emit(self.channel_id, db)

        # FX1 Send (with legacy echo_send fallback)
        fx1_send = state.get("fx1_send", state.get("echo_send", 0))
        self.fx1_send.blockSignals(True)
        self.fx1_send.setValue(fx1_send)
        self.fx1_send.blockSignals(False)
        self._on_fx1_send_changed(fx1_send)

        # FX2 Send (with legacy verb_send fallback)
        fx2_send = state.get("fx2_send", state.get("verb_send", 0))
        self.fx2_send.blockSignals(True)
        self.fx2_send.setValue(fx2_send)
        self.fx2_send.blockSignals(False)
        self._on_fx2_send_changed(fx2_send)

        # FX3 Send
        fx3_send = state.get("fx3_send", 0)
        self.fx3_send.blockSignals(True)
        self.fx3_send.setValue(fx3_send)
        self.fx3_send.blockSignals(False)
        self._on_fx3_send_changed(fx3_send)

        # FX4 Send
        fx4_send = state.get("fx4_send", 0)
        self.fx4_send.blockSignals(True)
        self.fx4_send.setValue(fx4_send)
        self.fx4_send.blockSignals(False)
        self._on_fx4_send_changed(fx4_send)

        # Lo Cut
        lo_cut = state.get("lo_cut", False)
        if lo_cut != self.lo_cut_active:
            self.toggle_lo_cut()

        # Hi Cut
        hi_cut = state.get("hi_cut", False)
        if hi_cut != self.hi_cut_active:
            self.toggle_hi_cut()

    def get_param_widget(self, param: str):
        """
        Return widget for param (for boid pulse visualization).

        Args:
            param: 'fx1', 'fx2', 'fx3', 'fx4', 'pan', or legacy 'echo'/'verb'

        Returns:
            Widget with set_boid_glow() method, or None
        """
        if param == 'fx1' or param == 'echo':
            return self.fx1_send
        elif param == 'fx2' or param == 'verb':
            return self.fx2_send
        elif param == 'fx3':
            return self.fx3_send
        elif param == 'fx4':
            return self.fx4_send
        elif param == 'pan':
            return self.pan_slider
        return None


class MixerPanel(QWidget):
    """Mixer panel with channel strips."""

    generator_volume_changed = pyqtSignal(int, float)
    generator_muted = pyqtSignal(int, bool)
    generator_solo = pyqtSignal(int, bool)
    generator_gain_changed = pyqtSignal(int, int)  # channel_id, gain_db
    generator_pan_changed = pyqtSignal(int, float)  # channel_id, pan (-1 to 1)
    generator_eq_changed = pyqtSignal(int, str, float)  # channel_id, band
    generator_fx1_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    generator_fx2_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    generator_fx3_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    generator_fx4_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    fx1_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    fx2_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    fx3_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    fx4_send_changed = pyqtSignal(int, float)  # channel_id, send level 0-1
    # Legacy signal aliases
    generator_echo_send_changed = generator_fx1_send_changed
    generator_verb_send_changed = generator_fx2_send_changed
    echo_send_changed = fx1_send_changed
    verb_send_changed = fx2_send_changed
    
    def __init__(self, num_generators=8, parent=None):
        super().__init__(parent)
        self.num_generators = num_generators
        self.channels = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create mixer panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SIZES['margin_none'], SIZES['margin_none'],
                                   SIZES['margin_none'], SIZES['margin_none'])
        layout.setSpacing(SIZES['margin_none'])
        
        # Channel strips frame with tooltip and accent border
        channels_frame = QFrame()
        channels_frame.setToolTip("MIXER - 8 Channel Strips")
        # Teal/cyan accent for mixer (complements green EQ knobs)
        mixer_border = '#339999'  # Teal accent
        channels_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {mixer_border};
                border-radius: 4px;
            }}
        """)
        channels_layout = QHBoxLayout(channels_frame)
        channels_layout.setContentsMargins(SIZES['margin_tight'], SIZES['margin_tight'],
                                            SIZES['margin_tight'], SIZES['margin_tight'])
        channels_layout.setSpacing(SIZES['spacing_tight'])
        
        for i in range(1, self.num_generators + 1):
            channel = ChannelStrip(i, str(i))
            channel.volume_changed.connect(self.on_channel_volume)
            channel.mute_toggled.connect(self.on_channel_mute)
            channel.solo_toggled.connect(self.on_channel_solo)
            channel.gain_changed.connect(self.on_channel_gain)
            channel.pan_changed.connect(self.on_channel_pan)
            channel.eq_changed.connect(self.on_channel_eq)
            channel.fx1_send_changed.connect(self.on_channel_fx1_send)
            channel.fx2_send_changed.connect(self.on_channel_fx2_send)
            channel.fx3_send_changed.connect(self.on_channel_fx3_send)
            channel.fx4_send_changed.connect(self.on_channel_fx4_send)
            channel.set_active(False)  # Start inactive (no generator loaded)
            channels_layout.addWidget(channel)
            self.channels[i] = channel
            
        layout.addWidget(channels_frame, stretch=1)  # Let it fill available space
        
    def on_channel_volume(self, channel_id, volume):
        """Handle channel volume change."""
        self.generator_volume_changed.emit(channel_id, volume)
        
    def on_channel_mute(self, channel_id, muted):
        """Handle channel mute."""
        self.generator_muted.emit(channel_id, muted)
        
    def on_channel_solo(self, channel_id, soloed):
        """Handle channel solo."""
        self.generator_solo.emit(channel_id, soloed)
    
    def on_channel_gain(self, channel_id, gain_db):
        """Handle channel gain change."""
        self.generator_gain_changed.emit(channel_id, gain_db)
    
    def on_channel_pan(self, channel_id, pan):
        """Handle channel pan change."""
        self.generator_pan_changed.emit(channel_id, pan)
    
    def on_channel_eq(self, channel_id, band, value):
        """Handle channel EQ change."""
        self.generator_eq_changed.emit(channel_id, band, value)

    def on_channel_fx1_send(self, channel_id, value):
        """Handle channel FX1 send change."""
        self.generator_fx1_send_changed.emit(channel_id, value)

    def on_channel_fx2_send(self, channel_id, value):
        """Handle channel FX2 send change."""
        self.generator_fx2_send_changed.emit(channel_id, value)

    def on_channel_fx3_send(self, channel_id, value):
        """Handle channel FX3 send change."""
        self.generator_fx3_send_changed.emit(channel_id, value)

    def on_channel_fx4_send(self, channel_id, value):
        """Handle channel FX4 send change."""
        self.generator_fx4_send_changed.emit(channel_id, value)

    # Legacy handler aliases
    on_channel_echo_send = on_channel_fx1_send
    on_channel_verb_send = on_channel_fx2_send
        
    def set_channel_active(self, channel_id, active):
        """Set active state for a channel (called when generator starts/stops)."""
        if channel_id in self.channels:
            self.channels[channel_id].set_active(active)
    
    def set_channel_levels(self, channel_id, left, right):
        """Update level meter for a channel."""
        if channel_id in self.channels:
            self.channels[channel_id].set_levels(left, right)
    
    def get_channel_strip_state(self, channel_id):
        """Get strip state for a channel (for syncing to SC)."""
        if channel_id in self.channels:
            return self.channels[channel_id].get_strip_state()
        return None

    def get_all_channel_states(self) -> list:
        """Get state of all channels for preset save."""
        return [self.channels[i].get_state() for i in range(1, self.num_generators + 1)]

    def set_all_channel_states(self, states: list):
        """Apply states to all channels from preset load."""
        for i, state in enumerate(states):
            channel_id = i + 1
            if channel_id in self.channels:
                self.channels[channel_id].set_state(state)

    def get_channel(self, channel_id: int):
        """Return channel strip by ID (1-indexed) for boid pulse visualization."""
        return self.channels.get(channel_id)
