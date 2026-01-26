"""
Main Frame - Combines all components
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QShortcut, QApplication)
from PyQt5.QtCore import Qt, QEvent, QTimer, QSettings
from PyQt5.QtGui import QFont, QKeySequence, QColor

from src.gui.generator_grid import GeneratorGrid
from src.gui.mixer_panel import MixerPanel
from src.gui.master_section import MasterSection
from src.gui.inline_fx_strip import InlineFXStrip
from src.gui.fx_window import FXWindow
from src.gui.modulator_grid import ModulatorGrid
from src.gui.bpm_display import BPMDisplay
from src.gui.pack_selector import PackSelector
from src.gui.midi_selector import MIDISelector
from src.gui.console_panel import ConsolePanel
from src.gui.mod_routing_state import ModRoutingState, ModConnection, Polarity
from src.gui.mod_matrix_window import ModMatrixWindow
from src.gui.crossmod_routing_state import CrossmodRoutingState
from src.gui.crossmod_osc_bridge import CrossmodOSCBridge
from src.gui.crossmod_matrix_window import CrossmodMatrixWindow
from src.gui.keyboard_overlay import KeyboardOverlay
from src.gui.preset_browser import PresetBrowser
from src.gui.mod_debug import install_mod_debug_hotkey
from src.gui.theme import COLORS, button_style, FONT_FAMILY, FONT_SIZES
from src.audio.osc_bridge import OSCBridge
from src.config import (
    CLOCK_RATE_INDEX, FILTER_TYPE_INDEX, GENERATORS, GENERATOR_CYCLE,
    BPM_DEFAULT, OSC_PATHS, unmap_value, get_param_config
)
from src.utils.logger import logger
from src.presets import PresetState, SlotState, MixerState, ChannelState, MasterState, ModSourcesState, FXState
from src.gui.controllers.preset_controller import PresetController
from src.gui.controllers.midi_cc_controller import MidiCCController
from src.gui.controllers.generator_controller import GeneratorController
from src.gui.controllers.mixer_controller import MixerController
from src.gui.controllers.master_controller import MasterController
from src.gui.controllers.connection_controller import ConnectionController
from src.gui.controllers.modulation_controller import ModulationController
from src.gui.controllers.midi_mode_controller import MidiModeController
from src.gui.controllers.keyboard_controller import KeyboardController
from src.gui.boid_panel import BoidPanel
from src.boids import BoidController
from src.utils.boid_gen_router import BoidGenRouter

class MainFrame(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Noise Engine")
        self.setMinimumSize(1200, 700)
        self._restore_window_geometry()
        
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        
        self.osc = OSCBridge()

        # Preset controller (pre-UI - handles menu setup)
        self.preset = PresetController(self)
        self.preset._setup_preset_menu()

        # MIDI CC controller (pre-UI - handles menu setup)
        self.midi_cc = MidiCCController(self)
        # Generator controller
        self.generator = GeneratorController(self)
        self.midi_cc._setup_midi_menu()

        # Connect MIDI CC signal from OSC (wrapper forwards to controller)
        self.osc.midi_cc_received.connect(self.midi_cc._on_midi_cc)

        # Connection controller
        self.connection = ConnectionController(self)

        # MIDI mode controller
        self.midi_mode = MidiModeController(self)
        # Keyboard controller
        self.keyboard = KeyboardController(self)

        # Modulation controller
        self.modulation = ModulationController(self)

        # Boid controller (pass main frame - gets osc client when connected)
        self.boid = BoidController(self)

        # Mixer controller
        self.mixer = MixerController(self)
        # Master controller
        self.master = MasterController(self)

        # Connect learn manager signals for visual feedback (wrappers forward to controller)
        self.midi_cc.cc_learn_manager.learn_started.connect(self.midi_cc._on_learn_started)
        self.midi_cc.cc_learn_manager.learn_completed.connect(self.midi_cc._on_learn_completed)
        self.midi_cc.cc_learn_manager.learn_cancelled.connect(self.midi_cc._on_learn_cancelled)

        self.osc_connected = False
        self._auto_connect_tried = False
        self._auto_connect_attempts = 0

        self.active_generators = {}
        self.active_effects = {}

        self.master_bpm = BPM_DEFAULT

        # Mod routing state
        self.mod_routing = ModRoutingState()
        self.modulation._connect_mod_routing_signals()
        
        # Mod matrix window (created on first open)
        self.mod_matrix_window = None

        # Crossmod routing state (slot-to-slot)
        self.crossmod_state = CrossmodRoutingState()
        self.crossmod_osc = None
        self.crossmod_window = None

        # FX window (created on first open)
        self.fx_window = None
        
        # Keyboard overlay (created on first open)
        self._keyboard_overlay = None

        # Preset browser (R1.1, created on first open)
        self._preset_browser = None
        
        # MIDI mode toggle state
        self._midi_mode_active = False
        self._midi_mode_saved_states = [0] * 8  # env_source per slot
        self._midi_mode_changing = False  # Guard flag for bulk changes

        # Dirty state tracking (unsaved changes indicator)
        self._dirty = False
        self._current_preset_name = None
        self._current_preset_path = None  # Full path to loaded/saved preset
        
        # Scope repaint throttling (~30fps instead of per-message)
        self._mod_scope_dirty = set()
        
        self.setup_ui()
        self._set_header_buttons_enabled(False)  # Disable until SC connects

        # Install event filter for keyboard overlay
        self.installEventFilter(self)

        # Debug hotkey
        from .debug_dump import install_dump_hotkey
        install_dump_hotkey(self)

    # Dirty State Tracking

    def _mark_dirty(self):
        """Mark session as having unsaved changes."""
        if not self._dirty:
            self._dirty = True
            self._update_window_title()

    def _clear_dirty(self, preset_name: str = None, preset_path = None):
        """Clear dirty flag after save/load."""
        self._dirty = False
        self._current_preset_name = preset_name
        self._current_preset_path = preset_path
        self._update_window_title()

    def _update_window_title(self):
        """Update window title with preset name and dirty indicator."""
        base = "Noise Engine"
        if self._current_preset_name:
            base = f"Noise Engine - {self._current_preset_name}"
        if self._dirty:
            base = f"• {base}"
        self.setWindowTitle(base)

    # ── Window Geometry Persistence ──────────────────────────────────

    def _restore_window_geometry(self):
        """Restore window geometry from settings, or use defaults."""
        settings = QSettings("NoiseEngine", "NoiseEngine")
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # First run defaults
            self.setGeometry(100, 50, 1400, 800)

    def _save_window_geometry(self):
        """Save window geometry to settings."""
        settings = QSettings("NoiseEngine", "NoiseEngine")
        settings.setValue("window/geometry", self.saveGeometry())

    def setup_ui(self):
        """Create the main interface layout."""
        central = QWidget()
        central.setObjectName("centralBackground")
        central.setAutoFillBackground(True)
        central.setStyleSheet(f"""
                    #centralBackground {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {COLORS['background_light']}, 
                            stop:0.08 {COLORS['background']}, 
                            stop:1 {COLORS['background_dark']});
                    }}
                """)
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # Content area with console overlay
        content_container = QWidget()
        content_container.setAutoFillBackground(True)
        content_outer = QHBoxLayout(content_container)
        content_outer.setContentsMargins(0, 0, 0, 0)
        content_outer.setSpacing(0)
        
        # Main content (left side)
        content_widget = QWidget()
        content_widget.setAutoFillBackground(True)
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Left column - MODULATOR GRID + BOID PANEL
        left_column = QWidget()
        left_column.setFixedWidth(320)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        # Modulator grid
        self.modulator_grid = ModulatorGrid()
        self.modulator_grid.generator_changed.connect(self.modulation.on_mod_generator_changed)
        self.modulator_grid.parameter_changed.connect(self.modulation.on_mod_param_changed)
        self.modulator_grid.output_wave_changed.connect(self.modulation.on_mod_output_wave)
        self.modulator_grid.output_phase_changed.connect(self.modulation.on_mod_output_phase)
        self.modulator_grid.output_polarity_changed.connect(self.modulation.on_mod_output_polarity)

        # ARSEq+ envelope signals
        self.modulator_grid.env_attack_changed.connect(self.modulation.on_mod_env_attack)
        self.modulator_grid.env_release_changed.connect(self.modulation.on_mod_env_release)
        self.modulator_grid.env_curve_changed.connect(self.modulation.on_mod_env_curve)
        self.modulator_grid.env_sync_mode_changed.connect(self.modulation.on_mod_env_sync_mode)
        self.modulator_grid.env_loop_rate_changed.connect(self.modulation.on_mod_env_loop_rate)

        # SauceOfGrav output signals
        self.modulator_grid.tension_changed.connect(self.modulation.on_mod_tension)
        self.modulator_grid.mass_changed.connect(self.modulation.on_mod_mass)
        left_layout.addWidget(self.modulator_grid, stretch=1)

        # Boid panel
        self.boid_panel = BoidPanel()
        self._connect_boid_signals()
        left_layout.addWidget(self.boid_panel)

        content_layout.addWidget(left_column)
        
        # Scope repaint timer (~30fps)
        from PyQt5.QtCore import QTimer
        self._mod_scope_timer = QTimer(self)
        self._mod_scope_timer.timeout.connect(self.modulation._flush_mod_scopes)
        self._mod_scope_timer.start(33)  # ~30fps
        
        # Center - GENERATORS
        self.generator_grid = GeneratorGrid(rows=2, cols=4)
        self.generator_grid.generator_selected.connect(self.generator.on_generator_selected)  # Legacy
        self.generator_grid.generator_changed.connect(self.generator.on_generator_changed)
        self.generator_grid.generator_parameter_changed.connect(self.generator.on_generator_param_changed)
        self.generator_grid.generator_custom_parameter_changed.connect(self.generator.on_generator_custom_param_changed)
        self.generator_grid.generator_filter_changed.connect(self.generator.on_generator_filter_changed)
        self.generator_grid.generator_clock_enabled_changed.connect(self.generator.on_generator_clock_enabled)
        self.generator_grid.generator_env_source_changed.connect(self.generator.on_generator_env_source)
        self.generator_grid.generator_clock_rate_changed.connect(self.generator.on_generator_clock_rate)
        self.generator_grid.generator_transpose_changed.connect(self.generator.on_generator_transpose)
        self.generator_grid.generator_portamento_changed.connect(self.generator.on_generator_portamento)  # ADD THIS
        self.generator_grid.generator_mute_changed.connect(self.generator.on_generator_mute)
        self.generator_grid.generator_midi_channel_changed.connect(self.generator.on_generator_midi_channel)
        content_layout.addWidget(self.generator_grid, stretch=5)
        
        # Right - MIXER only (full height now)
        self.mixer_panel = MixerPanel(num_generators=8)
        self.mixer_panel.generator_volume_changed.connect(self.mixer.on_generator_volume_changed)
        self.mixer_panel.generator_muted.connect(self.mixer.on_generator_muted)
        self.mixer_panel.generator_solo.connect(self.mixer.on_generator_solo)
        self.mixer_panel.generator_gain_changed.connect(self.mixer.on_generator_gain_changed)
        self.mixer_panel.generator_pan_changed.connect(self.mixer.on_generator_pan_changed)
        self.mixer_panel.generator_eq_changed.connect(self.mixer.on_generator_eq_changed)
        self.mixer_panel.generator_echo_send_changed.connect(self.mixer.on_generator_echo_send)
        self.mixer_panel.generator_verb_send_changed.connect(self.mixer.on_generator_verb_send)
        content_layout.addWidget(self.mixer_panel, stretch=1)
        
        content_outer.addWidget(content_widget, stretch=1)
        
        # Console panel (right edge overlay)
        self.console_panel = ConsolePanel()
        content_outer.addWidget(self.console_panel)
        
        main_layout.addWidget(content_container, stretch=1)
        
        # Bottom section - FX Chain + Master side by side
        bottom_container = QWidget()
        bottom_container.setAutoFillBackground(True)
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(5, 5, 5, 5)
        bottom_layout.setSpacing(10)
        
        # FX Chain (left side)
        bottom_section = self.create_bottom_section()
        bottom_layout.addWidget(bottom_section, stretch=2)
        
        # Master section (right side)
        self.master_section = MasterSection()
        self.master_section.master_volume_changed.connect(self.master.on_master_volume_from_master)
        self.master_section.meter_mode_changed.connect(self.master.on_meter_mode_changed)
        self.master_section.limiter_ceiling_changed.connect(self.master.on_limiter_ceiling_changed)
        self.master_section.limiter_bypass_changed.connect(self.master.on_limiter_bypass_changed)
        self.master_section.eq_lo_changed.connect(self.master.on_eq_lo_changed)
        self.master_section.eq_mid_changed.connect(self.master.on_eq_mid_changed)
        self.master_section.eq_hi_changed.connect(self.master.on_eq_hi_changed)
        self.master_section.eq_lo_kill_changed.connect(self.master.on_eq_lo_kill_changed)
        self.master_section.eq_mid_kill_changed.connect(self.master.on_eq_mid_kill_changed)
        self.master_section.eq_hi_kill_changed.connect(self.master.on_eq_hi_kill_changed)
        self.master_section.eq_locut_changed.connect(self.master.on_eq_locut_changed)
        self.master_section.eq_bypass_changed.connect(self.master.on_eq_bypass_changed)
        # Compressor signals
        self.master_section.comp_threshold_changed.connect(self.master.on_comp_threshold_changed)
        self.master_section.comp_ratio_changed.connect(self.master.on_comp_ratio_changed)
        self.master_section.comp_attack_changed.connect(self.master.on_comp_attack_changed)
        self.master_section.comp_release_changed.connect(self.master.on_comp_release_changed)
        self.master_section.comp_makeup_changed.connect(self.master.on_comp_makeup_changed)
        self.master_section.comp_sc_hpf_changed.connect(self.master.on_comp_sc_hpf_changed)
        self.master_section.comp_bypass_changed.connect(self.master.on_comp_bypass_changed)
        bottom_layout.addWidget(self.master_section, stretch=3)
        
        main_layout.addWidget(bottom_container)
        
        # Keyboard shortcut for console (Cmd+` or Ctrl+`)
        console_shortcut = QShortcut(QKeySequence("Ctrl+`"), self)
        console_shortcut.activated.connect(self.toggle_console)
        
        # Shortcut: open mod matrix window (Ctrl+M / Cmd+M)
        mod_matrix_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        mod_matrix_shortcut.activated.connect(self.modulation._open_mod_matrix)

        # Shortcut: save preset (Ctrl+S / Cmd+S)
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.preset._save_preset)

        # Shortcut: save preset as (Ctrl+Shift+S / Cmd+Shift+S)
        save_as_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        save_as_shortcut.activated.connect(self.preset._save_preset_as)

        # Shortcut: load preset (Ctrl+O / Cmd+O)
        load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        load_shortcut.activated.connect(self.preset._load_preset)

        # Shortcut: init preset (Ctrl+N / Cmd+N)
        init_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        init_shortcut.activated.connect(self.preset._init_preset)

        # Shortcut: keyboard mode (Ctrl+K / Cmd+K)
        self._keyboard_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self._keyboard_shortcut.activated.connect(self.keyboard._toggle_keyboard_mode)

        # Shortcut: FX window (Ctrl+F / Cmd+F)
        fx_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        fx_shortcut.activated.connect(self.modulation._open_fx_window)

        # Shortcut: crossmod matrix (Ctrl+X / Cmd+X)
        crossmod_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        crossmod_shortcut.activated.connect(self.modulation._open_crossmod_matrix)

        # Shortcut: preset browser (Ctrl+P / Cmd+P) - R1.1
        preset_browser_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        preset_browser_shortcut.activated.connect(self._toggle_preset_browser)

        # Shortcut: mod debug window (F10)
        install_mod_debug_hotkey(self, self.mod_routing, self.generator_grid)
        
        # Log startup
        logger.info("Noise Engine started", component="APP")
        
    def create_top_bar(self):
        """Create top bar."""
        bar = QFrame()
        bar.setFrameShape(QFrame.StyledPanel)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background_highlight']};
                border-bottom: 1px solid {COLORS['border_light']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['background']};
                color: {COLORS['border']};
                border-color: {COLORS['border']};
            }}
            QComboBox:disabled {{
                background-color: {COLORS['background']};
                color: {COLORS['border']};
                border-color: {COLORS['border']};
            }}
        """)
        bar.setFixedHeight(60)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        
        title = QLabel("NOISE ENGINE")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['title'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(title)
        
        layout.addStretch()
        
        self.bpm_display = BPMDisplay(initial_bpm=BPM_DEFAULT)
        self.bpm_display.bpm_changed.connect(self.on_bpm_changed)
        layout.addWidget(self.bpm_display)
        
        layout.addSpacing(20)
        
        # Pack selector
        self.pack_selector = PackSelector()
        self.pack_selector.pack_changed.connect(self.on_pack_changed)
        layout.addWidget(self.pack_selector)
        
        layout.addSpacing(20)
        
        # Audio device selector
        from src.gui.audio_device_selector import AudioDeviceSelector
        self.audio_selector = AudioDeviceSelector()
        self.audio_selector.device_changed.connect(self.master.on_audio_device_changed)
        layout.addWidget(self.audio_selector)
        
        layout.addSpacing(10)
        
        # MIDI device selector
        self.midi_selector = MIDISelector()
        self.midi_selector.device_changed.connect(self.generator.on_midi_device_changed)
        layout.addWidget(self.midi_selector)
        
        layout.addStretch()
        
        preset_label = QLabel("Preset:")
        preset_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(preset_label)
        
        self.preset_name = QLabel("Init")
        self.preset_name.setFont(QFont(FONT_FAMILY, FONT_SIZES['section']))
        self.preset_name.setStyleSheet(f"color: {COLORS['selected_text']};")
        layout.addWidget(self.preset_name)

        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save preset (Ctrl+S)")
        self.save_btn.setStyleSheet(button_style('submenu'))
        self.save_btn.clicked.connect(self.preset._save_preset)
        layout.addWidget(self.save_btn)

        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.setToolTip("Save preset as new file (Ctrl+Shift+S)")
        self.save_as_btn.setStyleSheet(button_style('submenu'))
        self.save_as_btn.clicked.connect(self.preset._save_preset_as)
        layout.addWidget(self.save_as_btn)

        self.load_btn = QPushButton("Load")
        self.load_btn.setToolTip("Load preset (Ctrl+O)")
        self.load_btn.setStyleSheet(button_style('submenu'))
        self.load_btn.clicked.connect(self.preset._load_preset)
        layout.addWidget(self.load_btn)
        
        # Matrix button - opens mod matrix window
        self.matrix_btn = QPushButton("MATRIX")
        self.matrix_btn.setToolTip("Mod Matrix (Ctrl+M)")
        self.matrix_btn.setFixedSize(70, 27)
        self.matrix_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: #00ff00;
                border: 1px solid #00aa00;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #003300;
                color: #00ff00;
                border-color: #00ff00;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['background']};
                color: #004400;
                border-color: #002200;
            }}
        """)
        self.matrix_btn.clicked.connect(self.modulation._open_mod_matrix)
        layout.addWidget(self.matrix_btn)

        # Clear mod button - clears all modulation routes
        self.clear_mod_btn = QPushButton("CLEAR")
        self.clear_mod_btn.setToolTip("Clear all modulation routes")
        self.clear_mod_btn.setFixedSize(55, 27)
        self.clear_mod_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: #ff4444;
                border: 1px solid #aa2222;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #330000;
                color: #ff6666;
                border-color: #ff4444;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['background']};
                color: #441111;
                border-color: #331111;
            }}
        """)
        self.clear_mod_btn.clicked.connect(self.modulation._clear_all_mod_routes)
        layout.addWidget(self.clear_mod_btn)

        # MIDI mode button - sets all generators to MIDI trigger mode
        self.midi_mode_btn = QPushButton("MIDI")
        self.midi_mode_btn.setToolTip("Set all generators to MIDI mode (toggle)")
        self.midi_mode_btn.setFixedSize(50, 27)
        self.midi_mode_btn.setCheckable(True)
        self.midi_mode_btn.setStyleSheet(self.midi_mode._midi_mode_btn_style(False))
        self.midi_mode_btn.clicked.connect(self.midi_mode._toggle_midi_mode)
        layout.addWidget(self.midi_mode_btn)
        
        layout.addStretch()
        
        self.connect_btn = QPushButton("Connect SuperCollider")
        self.connect_btn.setFixedWidth(180)  # FIXED: fits "Connect SuperCollider"
        self.connect_btn.setStyleSheet(self.connection._connect_btn_style())
        self.connect_btn.clicked.connect(self.connection.toggle_connection)
        layout.addWidget(self.connect_btn)

        self.status_label = QLabel("Disconnected")
        self.status_label.setFixedWidth(130)  # FIXED: fits "CONNECTION LOST"
        self.status_label.setStyleSheet(f"color: {COLORS['warning_text']};")
        layout.addWidget(self.status_label)

        # MIDI status
        self.midi_status_label = QLabel("MIDI: Ready")
        self.midi_status_label.setFixedWidth(100)
        self.midi_status_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        self.midi_status_label.setToolTip("MIDI CC control active")
        layout.addWidget(self.midi_status_label)

        layout.addSpacing(10)
        
        # Console toggle button
        self.console_btn = QPushButton(">_")
        self.console_btn.setToolTip("Toggle Console (Ctrl+`)")
        self.console_btn.setFixedSize(30, 30)
        self.console_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                font-family: {FONT_FAMILY};
                font-size: {FONT_SIZES['small']}px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_highlight']};
                color: {COLORS['text_bright']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['enabled']};
                color: {COLORS['enabled_text']};
                border-color: {COLORS['enabled']};
            }}
        """)
        self.console_btn.setCheckable(True)
        self.console_btn.clicked.connect(self.toggle_console)
        layout.addWidget(self.console_btn)
        
        # Restart button
        self.restart_btn = QPushButton("↻")
        self.restart_btn.setToolTip("Restart Noise Engine")
        self.restart_btn.setFixedSize(30, 30)
        self.restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                font-size: {FONT_SIZES['section']}px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['submenu']};
                color: {COLORS['submenu_text']};
                border-color: {COLORS['submenu']};
            }}
        """)
        self.restart_btn.clicked.connect(self.restart_app)
        layout.addWidget(self.restart_btn)
        
        return bar
        
    def create_bottom_section(self):
        """Create bottom section - effects only."""
        from PyQt5.QtWidgets import QSizePolicy
        container = QFrame()
        container.setObjectName("fxContainer")
        container.setFrameShape(QFrame.StyledPanel)
        container.setStyleSheet(f"background-color: {COLORS['background_highlight']}; border-top: 1px solid {COLORS['border_light']};")
        container.setFixedHeight(180)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        container.setMinimumWidth(600)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        self.inline_fx = InlineFXStrip()
        layout.addWidget(self.inline_fx, stretch=1)
        
        return container
        
    def on_bpm_changed(self, bpm):
        """Handle BPM change."""
        self.master_bpm = bpm
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['clock_bpm'], [bpm])
        self._mark_dirty()

    def on_pack_changed(self, pack_id):
        # Auto-load pack preset if exists
        if pack_id:
            from src.presets.preset_manager import PresetManager
            from src.presets.preset_schema import PresetState
            sanitized = pack_id.replace("-", "_").replace(" ", "_").lower()
            preset_path = PresetManager.DEFAULT_DIR / f"{sanitized}_preset.json"
            if preset_path.exists():
                try:
                    manager = PresetManager()
                    state = manager.load(preset_path)
                    self.preset._apply_preset(state)
                    self.preset_name.setText(state.name)
                    logger.info(f"Auto-loaded preset for pack '{pack_id}'", component="PACK")
                except Exception as e:
                    logger.warning(f"Failed to load pack preset: {e}", component="PACK")
                    self.preset._apply_preset(PresetState(pack=pack_id))
                    self.preset_name.setText("Init")
            else:
                self.preset._apply_preset(PresetState(pack=pack_id))
                self.preset_name.setText("Init")
        else:
            # Core - clean state
            from src.presets.preset_schema import PresetState
            self.preset._apply_preset(PresetState())
            self.preset_name.setText("Init")

    def showEvent(self, event):
        """Auto-connect if SC is ready (launched via ne-run)."""
        super().showEvent(event)
        if not self._auto_connect_tried and not self.osc_connected and self.connection._sc_is_ready():
            self._auto_connect_tried = True
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("Connecting...")
            QTimer.singleShot(3000, self.connection._try_auto_connect)

    def toggle_console(self):
        """Toggle console panel visibility."""
        self.console_panel.toggle_panel()
        self.console_btn.setChecked(self.console_panel.is_open)

    def _toggle_preset_browser(self):
        """Toggle preset browser panel visibility (R1.1)."""
        if self._preset_browser is None:
            # Create browser on first open
            from src.presets.preset_manager import PresetManager
            manager = PresetManager()
            self._preset_browser = PresetBrowser(manager, self)
            self._preset_browser.preset_load_requested.connect(self._on_browser_load_requested)
            self._preset_browser.preset_save_requested.connect(self._on_browser_save_requested)
            # Position as a floating panel on the right side
            self._preset_browser.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            self._preset_browser.setWindowTitle("Preset Browser")
            self._preset_browser.resize(320, 600)
            # Position relative to main window
            main_geo = self.geometry()
            self._preset_browser.move(main_geo.right() + 10, main_geo.top())

        if self._preset_browser.isVisible():
            self._preset_browser.hide()
        else:
            self._preset_browser.show()
            self._preset_browser.raise_()
            self._preset_browser.activateWindow()

    def _on_browser_load_requested(self, file_path: str):
        """Handle load request from preset browser."""
        from pathlib import Path
        self.preset._apply_preset_from_path(Path(file_path))

    def _on_browser_save_requested(self, file_path: str, name: str):
        """Handle save request from preset browser."""
        from pathlib import Path
        self.preset._save_preset_to_path(Path(file_path), name)

    def _connect_boid_signals(self):
        """Wire boid panel signals to boid controller."""
        # Panel -> Controller
        self.boid_panel.enabled_changed.connect(self._on_boid_enabled_changed)
        self.boid_panel.count_changed.connect(self.boid.set_boid_count)
        self.boid_panel.dispersion_changed.connect(self.boid.set_dispersion)
        self.boid_panel.energy_changed.connect(self.boid.set_energy)
        self.boid_panel.fade_changed.connect(self.boid.set_fade)
        self.boid_panel.depth_changed.connect(self.boid.set_depth)
        self.boid_panel.seed_lock_changed.connect(self.boid.set_seed_locked)
        self.boid_panel.reseed_clicked.connect(self.boid.reseed)
        self.boid_panel.zone_gen_changed.connect(self.boid.set_zone_gen)
        self.boid_panel.zone_mod_changed.connect(self.boid.set_zone_mod)
        self.boid_panel.zone_chan_changed.connect(self.boid.set_zone_chan)
        self.boid_panel.zone_fx_changed.connect(self.boid.set_zone_fx)
        self.boid_panel.row_slot1_changed.connect(self.boid.set_row_slot1)
        self.boid_panel.row_slot2_changed.connect(self.boid.set_row_slot2)
        self.boid_panel.row_slot3_changed.connect(self.boid.set_row_slot3)
        self.boid_panel.row_slot4_changed.connect(self.boid.set_row_slot4)
        self.boid_panel.preset_changed.connect(self.boid.apply_preset)

        # Controller -> Panel (visualization updates)
        self.boid.positions_updated.connect(self.boid_panel.set_positions)
        self.boid.cells_updated.connect(self.boid_panel.set_cells)
        self.boid.seed_changed.connect(self.boid_panel.set_seed)
        self.boid.enabled_changed.connect(self.boid_panel.set_enabled)

    def _on_boid_enabled_changed(self, enabled: bool):
        """Handle boid enable/disable from panel."""
        if enabled:
            self.boid.start()
        else:
            self.boid.stop()
        self._mark_dirty()

    def restart_app(self):
        """Restart the application with confirmation."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt5.QtCore import Qt
        import sys
        import os
        
        # Custom styled dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Restart")
        dialog.setFixedSize(280, 120)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border_light']};
            }}
            QLabel {{
                color: {COLORS['text_bright']};
                font-size: {FONT_SIZES['section']}px;
            }}
            QPushButton {{
                background-color: {COLORS['background_highlight']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px 20px;
                font-size: {FONT_SIZES['small']}px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
                color: {COLORS['text_bright']};
            }}
            QPushButton#confirm {{
                background-color: {COLORS['submenu']};
                color: {COLORS['submenu_text']};
                border-color: {COLORS['submenu']};
            }}
            QPushButton#confirm:hover {{
                background-color: {COLORS['warning_text']};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(20)
        
        label = QLabel("Restart Noise Engine?")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        no_btn = QPushButton("Cancel")
        no_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(no_btn)
        
        yes_btn = QPushButton("Restart")
        yes_btn.setObjectName("confirm")
        yes_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(yes_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # Save window position before restart
        self._save_window_geometry()
        
        logger.info("Restarting Noise Engine...", component="APP")
        
        # Disconnect OSC cleanly
        if self.osc_connected:
            try:
                self.osc.disconnect()
            except Exception as e:
                logger.warning(f"OSC disconnect failed during restart: {e}", component="APP")
        
        # Get the command to restart
        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        
        # Restart the process
        os.execv(python, [python, script])

    def eventFilter(self, obj, event):
        """Forward key events to keyboard overlay when visible."""
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                if self.midi_cc.cc_learn_manager.is_learning():
                    self.midi_cc.cc_learn_manager.cancel_learn()
                    return True

        if self._keyboard_overlay is not None and self._keyboard_overlay.isVisible():
            if event.type() == QEvent.KeyPress:
                self._keyboard_overlay.keyPressEvent(event)
                return True
            elif event.type() == QEvent.KeyRelease:
                self._keyboard_overlay.keyReleaseEvent(event)
                return True
        return super().eventFilter(obj, event)

    def _set_header_buttons_enabled(self, enabled: bool) -> None:
        """Enable/disable header buttons that require SC connection.

        On startup, only CONNECT, CONSOLE, RESTART are enabled.
        After SC connection confirmed, all buttons become enabled.
        """
        # Buttons/widgets that require SC connection
        sc_dependent = [
            self.save_btn,  # Preset save
            self.save_as_btn,  # Preset save as
            self.load_btn,  # Preset load
            self.pack_selector,  # Pack selector
            self.matrix_btn,  # Mod matrix
            self.midi_mode_btn,  # MIDI mode toggle
            self.audio_selector,  # Audio device selector
            self.midi_selector,  # MIDI device selector
            self.bpm_display,  # BPM control
            self.clear_mod_btn # CLear matrix button
        ]

        for widget in sc_dependent:
            if widget is not None:
                widget.setEnabled(enabled)

    def closeEvent(self, event):
        """Handle window close - cleanup OSC to prevent signal spam."""
        # Save window position for next launch
        self._save_window_geometry()
        
        # Stop OSC bridge first to prevent signals on deleted objects
        if hasattr(self, 'osc') and self.osc:
            self.osc.shutdown()

        # Accept the close event
        event.accept()

    @property
    def cc_mapping_manager(self):
        """Compatibility property - cc_mapping_manager now lives in MidiCCController."""
        return self.midi_cc.cc_mapping_manager

    @property
    def cc_learn_manager(self):
        """Compatibility property - cc_learn_manager now lives in MidiCCController."""
        return self.midi_cc.cc_learn_manager

    def _show_toast(self, message, duration=3000):
        """Show brief toast notification."""
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import QTimer

        toast = QLabel(message, self)
        toast.setStyleSheet(f"""
            background-color: {COLORS['background_light']};
            color: {COLORS['text']};
            padding: 8px 16px;
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
        """)
        toast.adjustSize()
        toast.move(self.width() // 2 - toast.width() // 2, 50)
        toast.show()

        QTimer.singleShot(duration, toast.deleteLater)

