"""
Mixer Panel Component - Right frame
Per-generator volume control, mute/solo, master fader
Responsive sizing with ghosting fix
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class MixerPanel(QWidget):
    """Mixer panel with per-generator controls and master fader."""
    
    # Signals
    generator_volume_changed = pyqtSignal(int, float)  # (gen_id, volume)
    generator_muted = pyqtSignal(int, bool)  # (gen_id, muted)
    generator_solo = pyqtSignal(int, bool)  # (gen_id, solo)
    master_volume_changed = pyqtSignal(float)
    
    def __init__(self, num_generators=8, parent=None):
        super().__init__(parent)
        self.num_generators = num_generators
        self.generator_faders = {}
        self.mute_buttons = {}
        self.solo_buttons = {}
        
        # Responsive sizing
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the mixer interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title
        title = QLabel("MIXER")
        title_font = QFont('Helvetica', 12, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        main_layout.addWidget(separator)
        
        # Generator channels in horizontal layout
        channels_layout = QHBoxLayout()
        channels_layout.setSpacing(5)
        
        for i in range(self.num_generators):
            channel = self.create_generator_channel(i + 1)
            channels_layout.addWidget(channel)
        
        main_layout.addLayout(channels_layout)
        
        # Spacer
        main_layout.addStretch()
        
        # Master section
        master_section = self.create_master_section()
        main_layout.addWidget(master_section)
        
        # I/O Status
        io_section = self.create_io_section()
        main_layout.addWidget(io_section)
        
    def create_generator_channel(self, gen_id):
        """Create a single generator channel strip."""
        channel = QWidget()
        layout = QVBoxLayout(channel)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)
        
        # Generator label
        label = QLabel(f"G{gen_id}")
        label.setAlignment(Qt.AlignCenter)
        label_font = QFont('Helvetica', 9, QFont.Bold)
        label.setFont(label_font)
        layout.addWidget(label)
        
        # Fader with anti-ghosting stylesheet
        fader = QSlider(Qt.Vertical)
        fader.setMinimum(0)
        fader.setMaximum(100)
        fader.setValue(75)
        fader.setMinimumHeight(80)
        fader.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Anti-ghosting stylesheet
        fader.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #999999;
                width: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 0 2px;
                border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #d4d4d4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                height: 18px;
                margin: 0 -4px;
                border-radius: 9px;
            }
            QSlider::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #f4f4f4, stop:1 #afafaf);
            }
        """)
        
        fader.valueChanged.connect(
            lambda val, gid=gen_id: self.on_generator_volume_change(gid, val)
        )
        
        # Force repaint on release - fixes ghosting
        fader.sliderReleased.connect(lambda s=fader: s.repaint())
        
        layout.addWidget(fader, alignment=Qt.AlignCenter, stretch=1)
        
        # Volume label
        vol_label = QLabel("75")
        vol_label.setAlignment(Qt.AlignCenter)
        vol_font = QFont('Courier', 8)
        vol_label.setFont(vol_font)
        layout.addWidget(vol_label)
        
        # Mute button
        mute_btn = QPushButton("M")
        mute_btn.setCheckable(True)
        mute_btn.setMinimumSize(25, 18)
        mute_btn.setMaximumSize(40, 25)
        mute_btn.setStyleSheet("""
            QPushButton { background-color: #666; color: white; }
            QPushButton:checked { background-color: #ff4444; }
        """)
        mute_btn.clicked.connect(
            lambda checked, gid=gen_id: self.on_generator_mute(gid, checked)
        )
        layout.addWidget(mute_btn)
        
        # Solo button
        solo_btn = QPushButton("S")
        solo_btn.setCheckable(True)
        solo_btn.setMinimumSize(25, 18)
        solo_btn.setMaximumSize(40, 25)
        solo_btn.setStyleSheet("""
            QPushButton { background-color: #666; color: white; }
            QPushButton:checked { background-color: #44ff44; }
        """)
        solo_btn.clicked.connect(
            lambda checked, gid=gen_id: self.on_generator_solo(gid, checked)
        )
        layout.addWidget(solo_btn)
        
        # Store references
        self.generator_faders[gen_id] = (fader, vol_label)
        self.mute_buttons[gen_id] = mute_btn
        self.solo_buttons[gen_id] = solo_btn
        
        return channel
        
    def create_master_section(self):
        """Create master fader section."""
        master = QWidget()
        layout = QVBoxLayout(master)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        
        # Master label
        label = QLabel("MASTER")
        label.setAlignment(Qt.AlignCenter)
        label_font = QFont('Helvetica', 10, QFont.Bold)
        label.setFont(label_font)
        layout.addWidget(label)
        
        # Master fader with anti-ghosting stylesheet
        fader = QSlider(Qt.Vertical)
        fader.setMinimum(0)
        fader.setMaximum(100)
        fader.setValue(80)
        fader.setMinimumHeight(60)
        fader.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Anti-ghosting stylesheet
        fader.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #999999;
                width: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 0 2px;
                border-radius: 5px;
            }
            QSlider::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #d4d4d4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                height: 20px;
                margin: 0 -5px;
                border-radius: 10px;
            }
            QSlider::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #f4f4f4, stop:1 #afafaf);
            }
        """)
        
        fader.valueChanged.connect(self.on_master_volume_change)
        
        # Force repaint on release - fixes ghosting
        fader.sliderReleased.connect(lambda s=fader: s.repaint())
        
        layout.addWidget(fader, alignment=Qt.AlignCenter, stretch=1)
        
        # Volume label
        self.master_vol_label = QLabel("80")
        self.master_vol_label.setAlignment(Qt.AlignCenter)
        vol_font = QFont('Courier', 10)
        self.master_vol_label.setFont(vol_font)
        layout.addWidget(self.master_vol_label)
        
        self.master_fader = fader
        
        return master
        
    def create_io_section(self):
        """Create I/O status section."""
        io = QWidget()
        layout = QVBoxLayout(io)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        
        # Title
        title = QLabel("I/O")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont('Helvetica', 9, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Status indicators
        self.audio_status = QLabel("Audio: ✓")
        self.audio_status.setStyleSheet("color: green;")
        self.audio_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.audio_status)
        
        self.midi_status = QLabel("MIDI: ━")
        self.midi_status.setStyleSheet("color: gray;")
        self.midi_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.midi_status)
        
        self.cv_status = QLabel("CV: ━")
        self.cv_status.setStyleSheet("color: gray;")
        self.cv_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cv_status)
        
        return io
        
    def on_generator_volume_change(self, gen_id, value):
        """Handle generator volume change."""
        volume = value / 100.0
        fader, label = self.generator_faders[gen_id]
        label.setText(str(value))
        self.generator_volume_changed.emit(gen_id, volume)
        
    def on_generator_mute(self, gen_id, muted):
        """Handle generator mute."""
        self.generator_muted.emit(gen_id, muted)
        
    def on_generator_solo(self, gen_id, solo):
        """Handle generator solo."""
        self.generator_solo.emit(gen_id, solo)
        
    def on_master_volume_change(self, value):
        """Handle master volume change."""
        volume = value / 100.0
        self.master_vol_label.setText(str(value))
        self.master_volume_changed.emit(volume)
        
    def set_io_status(self, audio=None, midi=None, cv=None):
        """Update I/O status indicators."""
        if audio is not None:
            if audio:
                self.audio_status.setText("Audio: ✓")
                self.audio_status.setStyleSheet("color: green;")
            else:
                self.audio_status.setText("Audio: ━")
                self.audio_status.setStyleSheet("color: gray;")
                
        if midi is not None:
            if midi:
                self.midi_status.setText("MIDI: ✓")
                self.midi_status.setStyleSheet("color: green;")
            else:
                self.midi_status.setText("MIDI: ━")
                self.midi_status.setStyleSheet("color: gray;")
                
        if cv is not None:
            if cv:
                self.cv_status.setText("CV: ✓")
                self.cv_status.setStyleSheet("color: green;")
            else:
                self.cv_status.setText("CV: ━")
                self.cv_status.setStyleSheet("color: gray;")
