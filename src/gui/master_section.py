"""
Master Section Component
Master output with fader, level meters, and clip detection

Phase 1 of master out system - see docs/MASTER_OUT.md
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient

from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from .widgets import DragSlider
from src.config import SIZES


class LevelMeter(QWidget):
    """Stereo level meter with peak hold and clip detection."""
    
    # Constants
    METER_WIDTH = 12  # Per channel
    METER_GAP = 4     # Gap between L/R
    PEAK_HOLD_MS = 1500  # Peak hold time
    CLIP_HOLD_MS = 2000  # Clip indicator hold time
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Current levels (0.0 to 1.0)
        self.level_l = 0.0
        self.level_r = 0.0
        
        # Peak hold values
        self.peak_l = 0.0
        self.peak_r = 0.0
        
        # Clip state
        self.clip_l = False
        self.clip_r = False
        
        # Timers for peak decay and clip reset
        self.peak_timer = QTimer(self)
        self.peak_timer.timeout.connect(self._decay_peaks)
        self.peak_timer.start(50)  # 20fps decay check
        
        self.clip_timer_l = QTimer(self)
        self.clip_timer_l.setSingleShot(True)
        self.clip_timer_l.timeout.connect(lambda: self._reset_clip('l'))
        
        self.clip_timer_r = QTimer(self)
        self.clip_timer_r.setSingleShot(True)
        self.clip_timer_r.timeout.connect(lambda: self._reset_clip('r'))
        
        # Track when peaks were set (for hold time)
        self.peak_l_time = 0
        self.peak_r_time = 0
        self._tick = 0  # Simple counter for timing
        
        # Fixed size
        total_width = (self.METER_WIDTH * 2) + self.METER_GAP + 4  # +4 for margins
        self.setFixedWidth(total_width)
        self.setMinimumHeight(80)
        
    def set_levels(self, left, right, peak_left=None, peak_right=None):
        """Update meter levels.
        
        Args:
            left: Left channel level (0.0 to 1.0+)
            right: Right channel level (0.0 to 1.0+)
            peak_left: Optional peak level from SC
            peak_right: Optional peak level from SC
        """
        self.level_l = max(0.0, min(1.0, left))
        self.level_r = max(0.0, min(1.0, right))
        
        # Update peaks
        if peak_left is not None and peak_left > self.peak_l:
            self.peak_l = min(1.0, peak_left)
            self.peak_l_time = self._tick
        elif left > self.peak_l:
            self.peak_l = min(1.0, left)
            self.peak_l_time = self._tick
            
        if peak_right is not None and peak_right > self.peak_r:
            self.peak_r = min(1.0, peak_right)
            self.peak_r_time = self._tick
        elif right > self.peak_r:
            self.peak_r = min(1.0, right)
            self.peak_r_time = self._tick
        
        # Clip detection (level > 0.99)
        if left > 0.99:
            self.clip_l = True
            self.clip_timer_l.start(self.CLIP_HOLD_MS)
        if right > 0.99:
            self.clip_r = True
            self.clip_timer_r.start(self.CLIP_HOLD_MS)
        
        self.update()
        
    def _decay_peaks(self):
        """Called periodically to decay peak hold."""
        self._tick += 1
        hold_ticks = self.PEAK_HOLD_MS // 50  # Convert ms to ticks
        
        # Decay peaks after hold time
        if self._tick - self.peak_l_time > hold_ticks:
            self.peak_l = max(self.level_l, self.peak_l * 0.95)
        if self._tick - self.peak_r_time > hold_ticks:
            self.peak_r = max(self.level_r, self.peak_r * 0.95)
        
        self.update()
        
    def _reset_clip(self, channel):
        """Reset clip indicator after timeout."""
        if channel == 'l':
            self.clip_l = False
        else:
            self.clip_r = False
        self.update()
        
    def paintEvent(self, event):
        """Draw the level meters."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Calculate meter positions
        margin = 2
        meter_height = h - (margin * 2) - 16  # Leave room for clip indicators
        clip_height = 12
        
        left_x = margin
        right_x = margin + self.METER_WIDTH + self.METER_GAP
        meter_y = margin + clip_height + 2
        
        # Draw backgrounds
        bg_color = QColor(COLORS['background_dark'])
        painter.fillRect(left_x, meter_y, self.METER_WIDTH, meter_height, bg_color)
        painter.fillRect(right_x, meter_y, self.METER_WIDTH, meter_height, bg_color)
        
        # Draw level bars with gradient
        self._draw_meter_bar(painter, left_x, meter_y, self.METER_WIDTH, 
                            meter_height, self.level_l)
        self._draw_meter_bar(painter, right_x, meter_y, self.METER_WIDTH, 
                            meter_height, self.level_r)
        
        # Draw peak indicators
        peak_color = QColor(COLORS['text_bright'])
        peak_h = 2
        
        if self.peak_l > 0.01:
            peak_y = meter_y + meter_height - int(self.peak_l * meter_height)
            painter.fillRect(left_x, peak_y, self.METER_WIDTH, peak_h, peak_color)
            
        if self.peak_r > 0.01:
            peak_y = meter_y + meter_height - int(self.peak_r * meter_height)
            painter.fillRect(right_x, peak_y, self.METER_WIDTH, peak_h, peak_color)
        
        # Draw clip indicators
        clip_y = margin
        
        clip_off_color = QColor(COLORS['border'])
        clip_on_color = QColor('#ff2222')
        
        painter.fillRect(left_x, clip_y, self.METER_WIDTH, clip_height, 
                        clip_on_color if self.clip_l else clip_off_color)
        painter.fillRect(right_x, clip_y, self.METER_WIDTH, clip_height, 
                        clip_on_color if self.clip_r else clip_off_color)
        
        # Draw borders
        border_color = QColor(COLORS['border'])
        painter.setPen(border_color)
        painter.drawRect(left_x, meter_y, self.METER_WIDTH - 1, meter_height - 1)
        painter.drawRect(right_x, meter_y, self.METER_WIDTH - 1, meter_height - 1)
        painter.drawRect(left_x, clip_y, self.METER_WIDTH - 1, clip_height - 1)
        painter.drawRect(right_x, clip_y, self.METER_WIDTH - 1, clip_height - 1)
        
    def _draw_meter_bar(self, painter, x, y, width, height, level):
        """Draw a single meter bar with gradient coloring."""
        if level < 0.001:
            return
            
        bar_height = int(level * height)
        bar_y = y + height - bar_height
        
        # Create gradient: green -> yellow -> red
        gradient = QLinearGradient(x, y + height, x, y)
        gradient.setColorAt(0.0, QColor('#22aa22'))   # Green at bottom
        gradient.setColorAt(0.6, QColor('#22aa22'))   # Green up to 60%
        gradient.setColorAt(0.75, QColor('#aaaa22'))  # Yellow at 75%
        gradient.setColorAt(0.9, QColor('#aa2222'))   # Red at 90%
        gradient.setColorAt(1.0, QColor('#ff2222'))   # Bright red at top
        
        painter.fillRect(x, bar_y, width, bar_height, gradient)


class MasterSection(QWidget):
    """Master output section with fader and meters.
    
    Phase 1: Fader + Meter
    - Master volume fader
    - Stereo level meters with peak hold
    - Clip indicators
    
    Phase 1.5: PRE/POST meter toggle
    - Toggle button to switch between PRE and POST fader metering
    
    Phase 4: Limiter
    - Brickwall limiter (on by default)
    - Ceiling control (-6 to 0 dB)
    - Bypass button
    """
    
    master_volume_changed = pyqtSignal(float)
    meter_mode_changed = pyqtSignal(int)  # 0=PRE, 1=POST
    limiter_ceiling_changed = pyqtSignal(float)  # dB value (-6 to 0)
    limiter_bypass_changed = pyqtSignal(int)  # 0=on, 1=bypassed
    # EQ signals
    eq_lo_changed = pyqtSignal(float)  # dB value (-12 to +12)
    eq_mid_changed = pyqtSignal(float)
    eq_hi_changed = pyqtSignal(float)
    eq_locut_changed = pyqtSignal(int)  # 0=off, 1=on
    eq_bypass_changed = pyqtSignal(int)  # 0=on, 1=bypassed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.meter_mode = 0  # 0=PRE, 1=POST
        self.limiter_bypass = 0  # 0=on, 1=bypassed
        self.limiter_ceiling_db = -0.1  # Default ceiling
        # EQ state
        self.eq_bypass = 0  # 0=on, 1=bypassed
        self.eq_locut = 0  # 0=off, 1=on
        self.setup_ui()
        
    def setup_ui(self):
        """Create master section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header
        header = QLabel("MASTER")
        header.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(header)
        
        # Main content frame
        content_frame = QFrame()
        content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        
        # Fader section
        fader_widget = QWidget()
        fader_layout = QVBoxLayout(fader_widget)
        fader_layout.setContentsMargins(0, 0, 0, 0)
        fader_layout.setSpacing(3)
        
        fader_label = QLabel("VOL")
        fader_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        fader_label.setAlignment(Qt.AlignCenter)
        fader_label.setStyleSheet(f"color: {COLORS['text']}; border: none;")
        fader_layout.addWidget(fader_label)
        
        self.master_fader = DragSlider()
        self.master_fader.setFixedWidth(SIZES['slider_width'])
        self.master_fader.setValue(800)  # 80% default
        self.master_fader.setMinimumHeight(SIZES['slider_height_medium'])
        self.master_fader.valueChanged.connect(self._on_fader_changed)
        fader_layout.addWidget(self.master_fader, alignment=Qt.AlignCenter)
        
        # dB display
        self.db_label = QLabel("-2.0")
        self.db_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.db_label.setAlignment(Qt.AlignCenter)
        self.db_label.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        fader_layout.addWidget(self.db_label)
        
        content_layout.addWidget(fader_widget)
        
        # Meter section (next to fader for visual feedback while mixing)
        meter_widget = QWidget()
        meter_layout = QVBoxLayout(meter_widget)
        meter_layout.setContentsMargins(0, 0, 0, 0)
        meter_layout.setSpacing(3)
        
        # PRE/POST toggle button
        self.meter_mode_btn = QPushButton("PRE")
        self.meter_mode_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.meter_mode_btn.setFixedSize(32, 18)
        self.meter_mode_btn.setToolTip("Toggle PRE/POST fader metering")
        self.meter_mode_btn.clicked.connect(self._on_meter_mode_clicked)
        self._update_meter_mode_style()
        meter_layout.addWidget(self.meter_mode_btn, alignment=Qt.AlignCenter)
        
        self.level_meter = LevelMeter()
        meter_layout.addWidget(self.level_meter, alignment=Qt.AlignCenter)
        
        # Peak dB display
        self.peak_label = QLabel("---")
        self.peak_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.peak_label.setAlignment(Qt.AlignCenter)
        self.peak_label.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        meter_layout.addWidget(self.peak_label)
        
        content_layout.addWidget(meter_widget)
        
        # Divider line
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.VLine)
        divider1.setStyleSheet(f"color: {COLORS['border']};")
        content_layout.addWidget(divider1)
        
        # EQ section (3-band + lo cut)
        eq_widget = QWidget()
        eq_layout = QVBoxLayout(eq_widget)
        eq_layout.setContentsMargins(0, 0, 0, 0)
        eq_layout.setSpacing(2)
        
        # EQ header with bypass button
        eq_header = QHBoxLayout()
        eq_header.setSpacing(3)
        
        eq_label = QLabel("EQ")
        eq_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        eq_label.setStyleSheet(f"color: {COLORS['text']}; border: none;")
        eq_header.addWidget(eq_label)
        
        self.eq_bypass_btn = QPushButton("ON")
        self.eq_bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.eq_bypass_btn.setFixedSize(24, 16)
        self.eq_bypass_btn.setToolTip("EQ bypass")
        self.eq_bypass_btn.clicked.connect(self._on_eq_bypass_clicked)
        self._update_eq_bypass_style()
        eq_header.addWidget(self.eq_bypass_btn)
        
        eq_layout.addLayout(eq_header)
        
        # EQ knobs row
        eq_knobs = QHBoxLayout()
        eq_knobs.setSpacing(4)
        
        # LO knob
        lo_container = QVBoxLayout()
        lo_container.setSpacing(1)
        self.eq_lo_slider = DragSlider()
        self.eq_lo_slider.setFixedWidth(SIZES['slider_width_narrow'])
        self.eq_lo_slider.setRange(0, 240)  # 0=-12dB, 120=0dB, 240=+12dB
        self.eq_lo_slider.setValue(120)  # 0dB default
        self.eq_lo_slider.setMinimumHeight(SIZES['slider_height_small'])
        self.eq_lo_slider.valueChanged.connect(self._on_eq_lo_changed)
        lo_container.addWidget(self.eq_lo_slider, alignment=Qt.AlignCenter)
        lo_label = QLabel("LO")
        lo_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        lo_label.setAlignment(Qt.AlignCenter)
        lo_label.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        lo_container.addWidget(lo_label)
        eq_knobs.addLayout(lo_container)
        
        # MID knob
        mid_container = QVBoxLayout()
        mid_container.setSpacing(1)
        self.eq_mid_slider = DragSlider()
        self.eq_mid_slider.setFixedWidth(SIZES['slider_width_narrow'])
        self.eq_mid_slider.setRange(0, 240)
        self.eq_mid_slider.setValue(120)
        self.eq_mid_slider.setMinimumHeight(SIZES['slider_height_small'])
        self.eq_mid_slider.valueChanged.connect(self._on_eq_mid_changed)
        mid_container.addWidget(self.eq_mid_slider, alignment=Qt.AlignCenter)
        mid_label = QLabel("MID")
        mid_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        mid_label.setAlignment(Qt.AlignCenter)
        mid_label.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        mid_container.addWidget(mid_label)
        eq_knobs.addLayout(mid_container)
        
        # HI knob
        hi_container = QVBoxLayout()
        hi_container.setSpacing(1)
        self.eq_hi_slider = DragSlider()
        self.eq_hi_slider.setFixedWidth(SIZES['slider_width_narrow'])
        self.eq_hi_slider.setRange(0, 240)
        self.eq_hi_slider.setValue(120)
        self.eq_hi_slider.setMinimumHeight(SIZES['slider_height_small'])
        self.eq_hi_slider.valueChanged.connect(self._on_eq_hi_changed)
        hi_container.addWidget(self.eq_hi_slider, alignment=Qt.AlignCenter)
        hi_label = QLabel("HI")
        hi_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        hi_label.setAlignment(Qt.AlignCenter)
        hi_label.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        hi_container.addWidget(hi_label)
        eq_knobs.addLayout(hi_container)
        
        eq_layout.addLayout(eq_knobs)
        
        # Lo Cut button
        self.eq_locut_btn = QPushButton("CUT")
        self.eq_locut_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.eq_locut_btn.setFixedSize(32, 16)
        self.eq_locut_btn.setToolTip("Low cut filter (75Hz)")
        self.eq_locut_btn.clicked.connect(self._on_eq_locut_clicked)
        self._update_eq_locut_style()
        eq_layout.addWidget(self.eq_locut_btn, alignment=Qt.AlignCenter)
        
        content_layout.addWidget(eq_widget)
        
        # Divider line
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.VLine)
        divider2.setStyleSheet(f"color: {COLORS['border']};")
        content_layout.addWidget(divider2)
        
        # Limiter section (separate - safety/protection)
        limiter_widget = QWidget()
        limiter_layout = QVBoxLayout(limiter_widget)
        limiter_layout.setContentsMargins(0, 0, 0, 0)
        limiter_layout.setSpacing(3)
        
        limiter_label = QLabel("LIM")
        limiter_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        limiter_label.setAlignment(Qt.AlignCenter)
        limiter_label.setStyleSheet(f"color: {COLORS['text']}; border: none;")
        limiter_layout.addWidget(limiter_label)
        
        # Bypass button
        self.limiter_bypass_btn = QPushButton("ON")
        self.limiter_bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.limiter_bypass_btn.setFixedSize(28, 18)
        self.limiter_bypass_btn.setToolTip("Limiter bypass")
        self.limiter_bypass_btn.clicked.connect(self._on_limiter_bypass_clicked)
        self._update_limiter_bypass_style()
        limiter_layout.addWidget(self.limiter_bypass_btn, alignment=Qt.AlignCenter)
        
        # Ceiling control (small fader)
        self.ceiling_fader = DragSlider()
        self.ceiling_fader.setFixedWidth(SIZES['slider_width_narrow'])
        self.ceiling_fader.setRange(0, 600)  # 0 = -6dB, 600 = 0dB
        self.ceiling_fader.setValue(590)  # -0.1dB default
        self.ceiling_fader.setMinimumHeight(SIZES['slider_height_small'])
        self.ceiling_fader.valueChanged.connect(self._on_ceiling_changed)
        limiter_layout.addWidget(self.ceiling_fader, alignment=Qt.AlignCenter)
        
        # Ceiling dB display
        self.ceiling_label = QLabel("-0.1")
        self.ceiling_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.ceiling_label.setAlignment(Qt.AlignCenter)
        self.ceiling_label.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        limiter_layout.addWidget(self.ceiling_label)
        
        content_layout.addWidget(limiter_widget)
        
        layout.addWidget(content_frame)
        
    def _on_fader_changed(self, value):
        """Handle fader movement."""
        # Convert 0-1000 to 0.0-1.0
        normalized = value / 1000.0
        
        # Debug - this should appear in console
        from src.utils.logger import logger
        logger.debug(f"Master fader: {value} -> {normalized:.3f}", component="UI")
        
        # Update dB display
        if normalized < 0.001:
            db_text = "-∞"
        else:
            # Simple dB conversion: 0dB at 1.0, -∞ at 0
            import math
            db = 20 * math.log10(normalized)
            db_text = f"{db:.1f}"
        self.db_label.setText(db_text)
        
        self.master_volume_changed.emit(normalized)
    
    def _on_meter_mode_clicked(self):
        """Toggle between PRE and POST metering."""
        self.meter_mode = 1 - self.meter_mode  # Toggle 0<->1
        self._update_meter_mode_style()
        
        from src.utils.logger import logger
        mode_name = "POST" if self.meter_mode == 1 else "PRE"
        logger.info(f"Master meter mode: {mode_name}", component="UI")
        
        # Reset peaks when switching modes for clearer comparison
        self.level_meter.peak_l = 0.0
        self.level_meter.peak_r = 0.0
        
        self.meter_mode_changed.emit(self.meter_mode)
    
    def _update_meter_mode_style(self):
        """Update button appearance based on current mode."""
        if self.meter_mode == 0:
            # PRE mode - default styling
            self.meter_mode_btn.setText("PRE")
            self.meter_mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['background_light']};
                }}
            """)
        else:
            # POST mode - highlighted styling (green to match active state)
            self.meter_mode_btn.setText("POST")
            self.meter_mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
    
    def _on_limiter_bypass_clicked(self):
        """Toggle limiter bypass."""
        self.limiter_bypass = 1 - self.limiter_bypass  # Toggle 0<->1
        self._update_limiter_bypass_style()
        
        from src.utils.logger import logger
        state = "BYPASSED" if self.limiter_bypass == 1 else "ON"
        logger.info(f"Limiter: {state}", component="UI")
        
        self.limiter_bypass_changed.emit(self.limiter_bypass)
    
    def _update_limiter_bypass_style(self):
        """Update bypass button appearance."""
        if self.limiter_bypass == 0:
            # Limiter ON - green/active
            self.limiter_bypass_btn.setText("ON")
            self.limiter_bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
        else:
            # Limiter BYPASSED - dim/warning
            self.limiter_bypass_btn.setText("BYP")
            self.limiter_bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['warning_hover']};
                }}
            """)
    
    def _on_ceiling_changed(self, value):
        """Handle ceiling fader change."""
        # Convert 0-600 to -6 to 0 dB
        db = (value / 100.0) - 6.0
        self.limiter_ceiling_db = db
        
        # Update display
        self.ceiling_label.setText(f"{db:.1f}")
        
        from src.utils.logger import logger
        logger.debug(f"Limiter ceiling: {db:.1f}dB", component="UI")
        
        self.limiter_ceiling_changed.emit(db)
    
    # === EQ Handlers ===
    
    def _on_eq_lo_changed(self, value):
        """Handle EQ LO slider change."""
        # Convert 0-240 to -12 to +12 dB
        db = (value / 10.0) - 12.0
        self.eq_lo_changed.emit(db)
    
    def _on_eq_mid_changed(self, value):
        """Handle EQ MID slider change."""
        db = (value / 10.0) - 12.0
        self.eq_mid_changed.emit(db)
    
    def _on_eq_hi_changed(self, value):
        """Handle EQ HI slider change."""
        db = (value / 10.0) - 12.0
        self.eq_hi_changed.emit(db)
    
    def _on_eq_locut_clicked(self):
        """Toggle EQ low cut filter."""
        self.eq_locut = 1 - self.eq_locut
        self._update_eq_locut_style()
        
        from src.utils.logger import logger
        state = "ON" if self.eq_locut == 1 else "OFF"
        logger.info(f"EQ Lo Cut: {state}", component="UI")
        
        self.eq_locut_changed.emit(self.eq_locut)
    
    def _update_eq_locut_style(self):
        """Update lo cut button appearance."""
        if self.eq_locut == 0:
            # Lo cut OFF
            self.eq_locut_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['background_light']};
                }}
            """)
        else:
            # Lo cut ON - highlighted
            self.eq_locut_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
    
    def _on_eq_bypass_clicked(self):
        """Toggle EQ bypass."""
        self.eq_bypass = 1 - self.eq_bypass
        self._update_eq_bypass_style()
        
        from src.utils.logger import logger
        state = "BYPASSED" if self.eq_bypass == 1 else "ON"
        logger.info(f"EQ: {state}", component="UI")
        
        self.eq_bypass_changed.emit(self.eq_bypass)
    
    def _update_eq_bypass_style(self):
        """Update EQ bypass button appearance."""
        if self.eq_bypass == 0:
            # EQ ON - green/active
            self.eq_bypass_btn.setText("ON")
            self.eq_bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
        else:
            # EQ BYPASSED - dim/warning
            self.eq_bypass_btn.setText("BYP")
            self.eq_bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 1px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['warning_hover']};
                }}
            """)
        
    def set_levels(self, left, right, peak_left=None, peak_right=None):
        """Update level meters from OSC data.
        
        Args:
            left: Left RMS level (0.0 to 1.0+)
            right: Right RMS level (0.0 to 1.0+)
            peak_left: Optional peak level
            peak_right: Optional peak level
        """
        self.level_meter.set_levels(left, right, peak_left, peak_right)
        
        # Update peak display
        peak = max(peak_left or left, peak_right or right)
        if peak > 0.001:
            import math
            db = 20 * math.log10(peak)
            self.peak_label.setText(f"{db:.1f}")
        else:
            self.peak_label.setText("---")
            
    def get_volume(self):
        """Get current master volume (0.0 to 1.0)."""
        return self.master_fader.value() / 1000.0
