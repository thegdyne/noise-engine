"""
Mixer Panel Component
Per-generator channel strips with volume, mute, solo

Signal flow: Generator → Channel Strip → Master Bus
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES
from .widgets import DragSlider
from src.config import SIZES


class ChannelStrip(QWidget):
    """Individual channel strip with fader."""
    
    volume_changed = pyqtSignal(int, float)
    mute_toggled = pyqtSignal(int, bool)
    solo_toggled = pyqtSignal(int, bool)
    
    def __init__(self, channel_id, label="", parent=None):
        super().__init__(parent)
        self.channel_id = channel_id
        self.label_text = label
        self.muted = False
        self.soloed = False
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
        
        # Fader
        self.fader = DragSlider()
        self.fader.setFixedWidth(SIZES['slider_width_narrow'])
        self.fader.setValue(800)
        self.fader.setMinimumHeight(SIZES['slider_height_large'])
        self.fader.valueChanged.connect(self.on_fader_changed)
        layout.addWidget(self.fader, alignment=Qt.AlignCenter)
        
        # Mute/Solo buttons
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
        
        layout.addLayout(btn_layout)
        
    def set_active(self, active):
        """Update visual state based on whether generator is active."""
        if active:
            self._label.setStyleSheet(f"color: {COLORS['text']};")
            self.mute_btn.setStyleSheet(button_style('disabled'))
            self.solo_btn.setStyleSheet(button_style('disabled'))
        else:
            self._label.setStyleSheet(f"color: {COLORS['text_dim']};")
            # Dim the buttons when inactive
            dim_btn = f"""
                QPushButton {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                }}
            """
            self.mute_btn.setStyleSheet(dim_btn)
            self.solo_btn.setStyleSheet(dim_btn)
        
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


class MixerPanel(QWidget):
    """Mixer panel with channel strips."""
    
    generator_volume_changed = pyqtSignal(int, float)
    generator_muted = pyqtSignal(int, bool)
    generator_solo = pyqtSignal(int, bool)
    
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
