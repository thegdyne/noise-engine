"""
Mixer Panel Component
Volume faders and master output
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, MONO_FONT
from .widgets import DragSlider


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
        label = QLabel(self.label_text or str(self.channel_id))
        label.setFont(QFont('Helvetica', 8))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(label)
        
        # Fader - DragSlider with fixed width
        self.fader = DragSlider()
        self.fader.setFixedWidth(20)
        self.fader.setValue(800)
        self.fader.setMinimumHeight(80)
        self.fader.valueChanged.connect(self.on_fader_changed)
        layout.addWidget(self.fader, alignment=Qt.AlignCenter)
        
        # Mute/Solo buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(2)
        
        self.mute_btn = QPushButton("M")
        self.mute_btn.setFixedSize(20, 18)
        self.mute_btn.setFont(QFont('Helvetica', 7, QFont.Bold))
        self.mute_btn.setStyleSheet(button_style('disabled'))
        self.mute_btn.clicked.connect(self.toggle_mute)
        btn_layout.addWidget(self.mute_btn, alignment=Qt.AlignCenter)
        
        self.solo_btn = QPushButton("S")
        self.solo_btn.setFixedSize(20, 18)
        self.solo_btn.setFont(QFont('Helvetica', 7, QFont.Bold))
        self.solo_btn.setStyleSheet(button_style('disabled'))
        self.solo_btn.clicked.connect(self.toggle_solo)
        btn_layout.addWidget(self.solo_btn, alignment=Qt.AlignCenter)
        
        layout.addLayout(btn_layout)
        
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
    master_volume_changed = pyqtSignal(float)
    
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
        
        title = QLabel("MIXER")
        title_font = QFont('Helvetica', 12, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(title)
        
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
            channels_layout.addWidget(channel)
            self.channels[i] = channel
            
        layout.addWidget(channels_frame)
        
        # Master section with vertical fader
        master_frame = QFrame()
        master_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        master_layout = QVBoxLayout(master_frame)
        master_layout.setContentsMargins(10, 5, 10, 5)
        
        master_label = QLabel("MASTER")
        master_label.setFont(QFont('Helvetica', 9, QFont.Bold))
        master_label.setAlignment(Qt.AlignCenter)
        master_label.setStyleSheet(f"color: {COLORS['text_bright']}; border: none;")
        master_layout.addWidget(master_label)
        
        # Vertical master fader - DragSlider with fixed width
        self.master_fader = DragSlider()
        self.master_fader.setFixedWidth(25)
        self.master_fader.setValue(800)
        self.master_fader.setMinimumHeight(60)
        self.master_fader.valueChanged.connect(self.on_master_volume)
        master_layout.addWidget(self.master_fader, alignment=Qt.AlignCenter)
        
        layout.addWidget(master_frame)
        
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
        self.audio_status.setFont(QFont('Helvetica', 9))
        self.audio_status.setStyleSheet(f"color: {COLORS['audio_off']}; border: none;")
        io_layout.addWidget(self.audio_status)
        
        self.midi_status = QLabel("🎹 MIDI")
        self.midi_status.setFont(QFont('Helvetica', 9))
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
        
    def on_master_volume(self, value):
        """Handle master volume change."""
        self.master_volume_changed.emit(value / 1000.0)
        
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
