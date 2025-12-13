"""
Mixer Panel Component
Per-generator channel strips with volume, mute, solo, and level metering

Signal flow: Generator → Channel Strip → Master Bus
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient

from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES
from .widgets import DragSlider
from src.config import SIZES


class MiniMeter(QWidget):
    """Compact stereo level meter for channel strips."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level_l = 0.0
        self.level_r = 0.0
        self.setFixedSize(20, 40)  # Compact size
        
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
    """Individual channel strip with fader and meter."""
    
    volume_changed = pyqtSignal(int, float)
    mute_toggled = pyqtSignal(int, bool)
    solo_toggled = pyqtSignal(int, bool)
    gain_changed = pyqtSignal(int, int)  # channel_id, gain_db (0, 6, or 12)
    
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
        
        # Fader + Meter side by side
        fader_meter_layout = QHBoxLayout()
        fader_meter_layout.setSpacing(2)
        
        # Fader
        self.fader = DragSlider()
        self.fader.setFixedWidth(SIZES['slider_width_narrow'])
        self.fader.setValue(800)
        self.fader.setMinimumHeight(SIZES['slider_height_large'])
        self.fader.valueChanged.connect(self.on_fader_changed)
        fader_meter_layout.addWidget(self.fader, alignment=Qt.AlignCenter)
        
        # Mini meter
        self.meter = MiniMeter()
        fader_meter_layout.addWidget(self.meter, alignment=Qt.AlignCenter)
        
        layout.addLayout(fader_meter_layout)
        
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
            # Clear meter when inactive
            self.meter.set_levels(0, 0)
    
    def reset_state(self):
        """Reset mute/solo/gain to default (off) state."""
        self.muted = False
        self.soloed = False
        self.gain_index = 0
        self.mute_btn.setStyleSheet(button_style('disabled'))
        self.solo_btn.setStyleSheet(button_style('disabled'))
        self.gain_btn.setText("0")
        self.gain_btn.setStyleSheet(button_style('disabled'))
        
    def on_fader_changed(self, value):
        """Handle fader movement."""
        self.volume_changed.emit(self.channel_id, value / 1000.0)
        
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


class MixerPanel(QWidget):
    """Mixer panel with channel strips."""
    
    generator_volume_changed = pyqtSignal(int, float)
    generator_muted = pyqtSignal(int, bool)
    generator_solo = pyqtSignal(int, bool)
    generator_gain_changed = pyqtSignal(int, int)  # channel_id, gain_db
    
    def __init__(self, num_generators=8, parent=None):
        super().__init__(parent)
        self.num_generators = num_generators
        self.channels = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create mixer panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(5)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("MIXER")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_dim']};")
        header.addWidget(title)
        
        header.addStretch()
        
        layout.addLayout(header)
        
        # Channel strips
        channels_frame = QFrame()
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
            channel.set_active(False)  # Start inactive (no generator loaded)
            channels_layout.addWidget(channel)
            self.channels[i] = channel
            
        layout.addWidget(channels_frame)
        
        # I/O Status
        io_frame = QFrame()
        io_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        io_layout = QHBoxLayout(io_frame)
        io_layout.setContentsMargins(10, 5, 10, 5)
        
        self.audio_status = QLabel("🔇 Audio")
        self.audio_status.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.audio_status.setStyleSheet(f"color: {COLORS['audio_off']}; border: none;")
        io_layout.addWidget(self.audio_status)
        
        self.midi_status = QLabel("🎹 MIDI")
        self.midi_status.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.midi_status.setStyleSheet(f"color: {COLORS['midi_off']}; border: none;")
        io_layout.addWidget(self.midi_status)
        
        layout.addWidget(io_frame)
        
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
        
    def set_io_status(self, audio=False, midi=False):
        """Update I/O status indicators."""
        if audio:
            self.audio_status.setText("🔊 Audio")
            self.audio_status.setStyleSheet(f"color: {COLORS['audio_on']}; border: none;")
        else:
            self.audio_status.setText("🔇 Audio")
            self.audio_status.setStyleSheet(f"color: {COLORS['audio_off']}; border: none;")
            
        if midi:
            self.midi_status.setText("🎹 MIDI")
            self.midi_status.setStyleSheet(f"color: {COLORS['midi_on']}; border: none;")
        else:
            self.midi_status.setText("🎹 MIDI")
            self.midi_status.setStyleSheet(f"color: {COLORS['midi_off']}; border: none;")
    
    def set_channel_active(self, channel_id, active):
        """Set active state for a channel (called when generator starts/stops)."""
        if channel_id in self.channels:
            self.channels[channel_id].set_active(active)
    
    def set_channel_levels(self, channel_id, left, right):
        """Update level meter for a channel."""
        if channel_id in self.channels:
            self.channels[channel_id].set_levels(left, right)
