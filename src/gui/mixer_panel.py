"""
Mixer Panel Component
Per-generator channel strips with volume, mute, solo, and level metering

Signal flow: Generator → Channel Strip → Master Bus
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient

from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES, pan_slider_style
from .widgets import DragSlider, MiniKnob
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
    eq_changed = pyqtSignal(int, str, float)  # channel_id, band ('lo'/'mid'/'hi'), value (0-2 linear)
    
    # Gain stages: dB value, display text, color style
    GAIN_STAGES = [
        (0, "0", 'disabled'),      # Unity - grey
        (6, "+6", 'warning'),      # +6dB - amber
        (12, "+12", 'destructive') # +12dB - red
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 5, 2, 5)
        layout.setSpacing(3)
        
        # Channel label
        self._label = QLabel(self.label_text or str(self.channel_id))
        self._label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(f"color: {COLORS['text_dim']};")  # Start dimmed
        layout.addWidget(self._label)
        
        # === EQ Section (3 mini knobs: H, M, L) ===
        eq_layout = QVBoxLayout()
        eq_layout.setSpacing(1)
        eq_layout.setContentsMargins(0, 0, 0, 2)
        
        # HI knob
        self.eq_hi = MiniKnob()
        self.eq_hi.setToolTip("HI EQ: >2.5kHz (double-click reset)")
        self.eq_hi.valueChanged.connect(lambda v: self._on_eq_changed('hi', v))
        eq_layout.addWidget(self.eq_hi, alignment=Qt.AlignCenter)
        
        # MID knob
        self.eq_mid = MiniKnob()
        self.eq_mid.setToolTip("MID EQ: 250Hz-2.5kHz (double-click reset)")
        self.eq_mid.valueChanged.connect(lambda v: self._on_eq_changed('mid', v))
        eq_layout.addWidget(self.eq_mid, alignment=Qt.AlignCenter)
        
        # LO knob
        self.eq_lo = MiniKnob()
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
        
        # Fader + Meter side by side
        fader_meter_layout = QHBoxLayout()
        fader_meter_layout.setSpacing(2)
        fader_meter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Fader - no alignment constraint so it fills vertical space
        self.fader = DragSlider()
        self.fader.setFixedWidth(SIZES['slider_width_narrow'])
        self.fader.setValue(800)
        self.fader.setMinimumHeight(SIZES['slider_height_large'])
        self.fader.valueChanged.connect(self.on_fader_changed)
        fader_meter_layout.addWidget(self.fader)  # No alignment - let it stretch
        
        # Mini meter - also stretches with fader
        self.meter = MiniMeter()
        fader_meter_layout.addWidget(self.meter)  # No alignment - let it stretch
        
        layout.addLayout(fader_meter_layout, stretch=1)  # Let faders grow
        
        # Pan slider (horizontal, compact) - double-click to center
        from PyQt5.QtWidgets import QSlider

        class PanSlider(QSlider):
            """Pan slider with double-click to center."""
            def mouseDoubleClickEvent(self, event):
                self.setValue(0)  # Center on double-click

        self.pan_slider = PanSlider(Qt.Horizontal)
        self.pan_slider.setRange(-100, 100)  # -100 = L, 0 = C, 100 = R
        self.pan_slider.setValue(0)
        self.pan_slider.setFixedWidth(40)
        self.pan_slider.setFixedHeight(16)
        self.pan_slider.setToolTip("Pan: L ← C → R (double-click to center)")
        self.pan_slider.valueChanged.connect(self.on_pan_changed)
        self.pan_slider.setStyleSheet(pan_slider_style())
        layout.addWidget(self.pan_slider, alignment=Qt.AlignCenter)
        
        # Mute/Solo/Gain buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(2)
        
        self.mute_btn = QPushButton("M")
        self.mute_btn.setFixedSize(*SIZES['button_small'])
        self.mute_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro'], QFont.Bold))
        self.mute_btn.setStyleSheet(button_style('disabled'))
        self.mute_btn.clicked.connect(self.toggle_mute)
        btn_layout.addWidget(self.mute_btn, alignment=Qt.AlignCenter)
        
        self.solo_btn = QPushButton("S")
        self.solo_btn.setFixedSize(*SIZES['button_small'])
        self.solo_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro'], QFont.Bold))
        self.solo_btn.setStyleSheet(button_style('disabled'))
        self.solo_btn.clicked.connect(self.toggle_solo)
        btn_layout.addWidget(self.solo_btn, alignment=Qt.AlignCenter)
        
        # Gain stage button (cycles 0dB -> +6dB -> +12dB)
        self.gain_btn = QPushButton("0")
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


class MixerPanel(QWidget):
    """Mixer panel with channel strips."""
    
    generator_volume_changed = pyqtSignal(int, float)
    generator_muted = pyqtSignal(int, bool)
    generator_solo = pyqtSignal(int, bool)
    generator_gain_changed = pyqtSignal(int, int)  # channel_id, gain_db
    generator_pan_changed = pyqtSignal(int, float)  # channel_id, pan (-1 to 1)
    generator_eq_changed = pyqtSignal(int, str, float)  # channel_id, band, value (0-2)
    
    def __init__(self, num_generators=8, parent=None):
        super().__init__(parent)
        self.num_generators = num_generators
        self.channels = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create mixer panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        # Channel strips frame with tooltip
        channels_frame = QFrame()
        channels_frame.setToolTip("MIXER - 8 Channel Strips")
        channels_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        channels_layout = QHBoxLayout(channels_frame)
        channels_layout.setContentsMargins(5, 5, 5, 5)
        channels_layout.setSpacing(2)
        
        for i in range(1, self.num_generators + 1):
            channel = ChannelStrip(i, str(i))
            channel.volume_changed.connect(self.on_channel_volume)
            channel.mute_toggled.connect(self.on_channel_mute)
            channel.solo_toggled.connect(self.on_channel_solo)
            channel.gain_changed.connect(self.on_channel_gain)
            channel.pan_changed.connect(self.on_channel_pan)
            channel.eq_changed.connect(self.on_channel_eq)
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
