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
        self.osc.midi_cc_received.connect(self._on_midi_cc)

        # Connection controller
        self.connection = ConnectionController(self)

        # MIDI mode controller
        self.midi_mode = MidiModeController(self)
        # Keyboard controller
        self.keyboard = KeyboardController(self)

        # Modulation controller
        self.modulation = ModulationController(self)

        # Mixer controller
        self.mixer = MixerController(self)
        # Master controller
        self.master = MasterController(self)

        # Connect learn manager signals for visual feedback (wrappers forward to controller)
        self.midi_cc.cc_learn_manager.learn_started.connect(self._on_learn_started)
        self.midi_cc.cc_learn_manager.learn_completed.connect(self._on_learn_completed)
        self.midi_cc.cc_learn_manager.learn_cancelled.connect(self._on_learn_cancelled)

        self.osc_connected = False
        self._auto_connect_tried = False
        self._auto_connect_attempts = 0

        self.active_generators = {}
        self.active_effects = {}

        self.master_bpm = BPM_DEFAULT

        # Mod routing state
        self.mod_routing = ModRoutingState()
        self._connect_mod_routing_signals()
        
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
        
        # Left - MODULATOR GRID
        self.modulator_grid = ModulatorGrid()
        self.modulator_grid.setFixedWidth(320)  # 2 columns
        self.modulator_grid.generator_changed.connect(self.on_mod_generator_changed)
        self.modulator_grid.parameter_changed.connect(self.on_mod_param_changed)
        self.modulator_grid.output_wave_changed.connect(self.on_mod_output_wave)
        self.modulator_grid.output_phase_changed.connect(self.on_mod_output_phase)
        self.modulator_grid.output_polarity_changed.connect(self.on_mod_output_polarity)

        # ARSEq+ envelope signals
        self.modulator_grid.env_attack_changed.connect(self.on_mod_env_attack)
        self.modulator_grid.env_release_changed.connect(self.on_mod_env_release)
        self.modulator_grid.env_curve_changed.connect(self.on_mod_env_curve)
        self.modulator_grid.env_sync_mode_changed.connect(self.on_mod_env_sync_mode)
        self.modulator_grid.env_loop_rate_changed.connect(self.on_mod_env_loop_rate)

        # SauceOfGrav output signals
        self.modulator_grid.tension_changed.connect(self.on_mod_tension)
        self.modulator_grid.mass_changed.connect(self.on_mod_mass)
        content_layout.addWidget(self.modulator_grid)
        
        # Scope repaint timer (~30fps)
        from PyQt5.QtCore import QTimer
        self._mod_scope_timer = QTimer(self)
        self._mod_scope_timer.timeout.connect(self._flush_mod_scopes)
        self._mod_scope_timer.start(33)  # ~30fps
        
        # Center - GENERATORS
        self.generator_grid = GeneratorGrid(rows=2, cols=4)
        self.generator_grid.generator_selected.connect(self.on_generator_selected)  # Legacy
        self.generator_grid.generator_changed.connect(self.on_generator_changed)
        self.generator_grid.generator_parameter_changed.connect(self.on_generator_param_changed)
        self.generator_grid.generator_custom_parameter_changed.connect(self.on_generator_custom_param_changed)
        self.generator_grid.generator_filter_changed.connect(self.on_generator_filter_changed)
        self.generator_grid.generator_clock_enabled_changed.connect(self.on_generator_clock_enabled)
        self.generator_grid.generator_env_source_changed.connect(self.on_generator_env_source)
        self.generator_grid.generator_clock_rate_changed.connect(self.on_generator_clock_rate)
        self.generator_grid.generator_transpose_changed.connect(self.on_generator_transpose)
        self.generator_grid.generator_portamento_changed.connect(self.on_generator_portamento)  # ADD THIS
        self.generator_grid.generator_mute_changed.connect(self.on_generator_mute)
        self.generator_grid.generator_midi_channel_changed.connect(self.on_generator_midi_channel)
        content_layout.addWidget(self.generator_grid, stretch=5)
        
        # Right - MIXER only (full height now)
        self.mixer_panel = MixerPanel(num_generators=8)
        self.mixer_panel.generator_volume_changed.connect(self.on_generator_volume_changed)
        self.mixer_panel.generator_muted.connect(self.on_generator_muted)
        self.mixer_panel.generator_solo.connect(self.on_generator_solo)
        self.mixer_panel.generator_gain_changed.connect(self.on_generator_gain_changed)
        self.mixer_panel.generator_pan_changed.connect(self.on_generator_pan_changed)
        self.mixer_panel.generator_eq_changed.connect(self.on_generator_eq_changed)
        self.mixer_panel.generator_echo_send_changed.connect(self.on_generator_echo_send)
        self.mixer_panel.generator_verb_send_changed.connect(self.on_generator_verb_send)
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
        self.master_section.master_volume_changed.connect(self.on_master_volume_from_master)
        self.master_section.meter_mode_changed.connect(self.on_meter_mode_changed)
        self.master_section.limiter_ceiling_changed.connect(self.on_limiter_ceiling_changed)
        self.master_section.limiter_bypass_changed.connect(self.on_limiter_bypass_changed)
        self.master_section.eq_lo_changed.connect(self.on_eq_lo_changed)
        self.master_section.eq_mid_changed.connect(self.on_eq_mid_changed)
        self.master_section.eq_hi_changed.connect(self.on_eq_hi_changed)
        self.master_section.eq_lo_kill_changed.connect(self.on_eq_lo_kill_changed)
        self.master_section.eq_mid_kill_changed.connect(self.on_eq_mid_kill_changed)
        self.master_section.eq_hi_kill_changed.connect(self.on_eq_hi_kill_changed)
        self.master_section.eq_locut_changed.connect(self.on_eq_locut_changed)
        self.master_section.eq_bypass_changed.connect(self.on_eq_bypass_changed)
        # Compressor signals
        self.master_section.comp_threshold_changed.connect(self.on_comp_threshold_changed)
        self.master_section.comp_ratio_changed.connect(self.on_comp_ratio_changed)
        self.master_section.comp_attack_changed.connect(self.on_comp_attack_changed)
        self.master_section.comp_release_changed.connect(self.on_comp_release_changed)
        self.master_section.comp_makeup_changed.connect(self.on_comp_makeup_changed)
        self.master_section.comp_sc_hpf_changed.connect(self.on_comp_sc_hpf_changed)
        self.master_section.comp_bypass_changed.connect(self.on_comp_bypass_changed)
        bottom_layout.addWidget(self.master_section, stretch=3)
        
        main_layout.addWidget(bottom_container)
        
        # Keyboard shortcut for console (Cmd+` or Ctrl+`)
        console_shortcut = QShortcut(QKeySequence("Ctrl+`"), self)
        console_shortcut.activated.connect(self.toggle_console)
        
        # Shortcut: open mod matrix window (Ctrl+M / Cmd+M)
        mod_matrix_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        mod_matrix_shortcut.activated.connect(self._open_mod_matrix)

        # Shortcut: save preset (Ctrl+S / Cmd+S)
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self._save_preset)

        # Shortcut: save preset as (Ctrl+Shift+S / Cmd+Shift+S)
        save_as_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        save_as_shortcut.activated.connect(self._save_preset_as)

        # Shortcut: load preset (Ctrl+O / Cmd+O)
        load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        load_shortcut.activated.connect(self._load_preset)

        # Shortcut: init preset (Ctrl+N / Cmd+N)
        init_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        init_shortcut.activated.connect(self._init_preset)

        # Shortcut: keyboard mode (Ctrl+K / Cmd+K)
        keyboard_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        keyboard_shortcut.activated.connect(self._toggle_keyboard_mode)

        # Shortcut: FX window (Ctrl+F / Cmd+F)
        fx_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        fx_shortcut.activated.connect(self._open_fx_window)

        # Shortcut: crossmod matrix (Ctrl+X / Cmd+X)
        crossmod_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        crossmod_shortcut.activated.connect(self._open_crossmod_matrix)

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
        self.audio_selector.device_changed.connect(self.on_audio_device_changed)
        layout.addWidget(self.audio_selector)
        
        layout.addSpacing(10)
        
        # MIDI device selector
        self.midi_selector = MIDISelector()
        self.midi_selector.device_changed.connect(self.on_midi_device_changed)
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
        self.save_btn.clicked.connect(self._save_preset)
        layout.addWidget(self.save_btn)

        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.setToolTip("Save preset as new file (Ctrl+Shift+S)")
        self.save_as_btn.setStyleSheet(button_style('submenu'))
        self.save_as_btn.clicked.connect(self._save_preset_as)
        layout.addWidget(self.save_as_btn)

        self.load_btn = QPushButton("Load")
        self.load_btn.setToolTip("Load preset (Ctrl+O)")
        self.load_btn.setStyleSheet(button_style('submenu'))
        self.load_btn.clicked.connect(self._load_preset)
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
        self.matrix_btn.clicked.connect(self._open_mod_matrix)
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
        self.clear_mod_btn.clicked.connect(self._clear_all_mod_routes)
        layout.addWidget(self.clear_mod_btn)

        # MIDI mode button - sets all generators to MIDI trigger mode
        self.midi_mode_btn = QPushButton("MIDI")
        self.midi_mode_btn.setToolTip("Set all generators to MIDI mode (toggle)")
        self.midi_mode_btn.setFixedSize(50, 27)
        self.midi_mode_btn.setCheckable(True)
        self.midi_mode_btn.setStyleSheet(self._midi_mode_btn_style(False))
        self.midi_mode_btn.clicked.connect(self._toggle_midi_mode)
        layout.addWidget(self.midi_mode_btn)
        
        layout.addStretch()
        
        self.connect_btn = QPushButton("Connect SuperCollider")
        self.connect_btn.setFixedWidth(180)  # FIXED: fits "Connect SuperCollider"
        self.connect_btn.setStyleSheet(self._connect_btn_style())
        self.connect_btn.clicked.connect(self.toggle_connection)
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
                    self._apply_preset(state)
                    self.preset_name.setText(state.name)
                    logger.info(f"Auto-loaded preset for pack '{pack_id}'", component="PACK")
                except Exception as e:
                    logger.warning(f"Failed to load pack preset: {e}", component="PACK")
                    self._apply_preset(PresetState(pack=pack_id))
                    self.preset_name.setText("Init")
            else:
                self._apply_preset(PresetState(pack=pack_id))
                self.preset_name.setText("Init")
        else:
            # Core - clean state
            from src.presets.preset_schema import PresetState
            self._apply_preset(PresetState())
            self.preset_name.setText("Init")

    def showEvent(self, event):
        """Auto-connect if SC is ready (launched via ne-run)."""
        super().showEvent(event)
        if not self._auto_connect_tried and not self.osc_connected and self._sc_is_ready():
            self._auto_connect_tried = True
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("Connecting...")
            QTimer.singleShot(3000, self._try_auto_connect)

    # ── Connection Controller Wrappers ──────────────────────────────────
    # Method bodies moved to ConnectionController (Phase 5 refactor)

    def _try_auto_connect(self):
        return self.connection._try_auto_connect()

    def _sc_is_ready(self):
        return self.connection._sc_is_ready()

    def toggle_connection(self):
        return self.connection.toggle_connection()

    def on_connection_lost(self):
        return self.connection.on_connection_lost()

    def on_connection_restored(self):
        return self.connection.on_connection_restored()

    def _connect_btn_style(self):
        return self.connection._connect_btn_style()

    # ── Generator Controller Wrappers ───────────────────────────────────
    # Method bodies moved to GeneratorController (Phase 3 refactor)

    def on_gate_trigger(self, slot_id):
        return self.generator.on_gate_trigger(slot_id)

    def on_midi_device_changed(self, device_name):
        return self.generator.on_midi_device_changed(device_name)

    def on_generator_param_changed(self, slot_id, param_name, value):
        return self.generator.on_generator_param_changed(slot_id, param_name, value)

    def on_generator_custom_param_changed(self, slot_id, param_index, value):
        return self.generator.on_generator_custom_param_changed(slot_id, param_index, value)

    def on_generator_filter_changed(self, slot_id, filter_type):
        return self.generator.on_generator_filter_changed(slot_id, filter_type)

    def on_generator_clock_enabled(self, slot_id, enabled):
        return self.generator.on_generator_clock_enabled(slot_id, enabled)

    def on_generator_transpose(self, slot_id, semitones):
        return self.generator.on_generator_transpose(slot_id, semitones)

    def on_generator_env_source(self, slot_id, source):
        return self.generator.on_generator_env_source(slot_id, source)

    def on_generator_clock_rate(self, slot_id, rate):
        return self.generator.on_generator_clock_rate(slot_id, rate)

    def on_generator_mute(self, slot_id, muted):
        return self.generator.on_generator_mute(slot_id, muted)

    def on_generator_midi_channel(self, slot_id, channel):
        return self.generator.on_generator_midi_channel(slot_id, channel)

    def on_generator_portamento(self, slot_id, value):
        return self.generator.on_generator_portamento(slot_id, value)

    def on_generator_selected(self, slot_id):
        return self.generator.on_generator_selected(slot_id)

    def on_generator_changed(self, slot_id, new_type):
        return self.generator.on_generator_changed(slot_id, new_type)

    # ── Modulation Controller Wrappers ──────────────────────────────────
    # Method bodies moved to ModulationController (Phase 6 refactor)

    def _sync_mod_slot_state(self, slot_id, send_generator=True):
        return self.modulation._sync_mod_slot_state(slot_id, send_generator)

    def _sync_mod_sources(self):
        return self.modulation._sync_mod_sources()

    def on_mod_generator_changed(self, slot_id, gen_name):
        return self.modulation.on_mod_generator_changed(slot_id, gen_name)

    def on_mod_param_changed(self, slot_id, key, value):
        return self.modulation.on_mod_param_changed(slot_id, key, value)

    def on_mod_output_wave(self, slot_id, output_idx, wave_index):
        return self.modulation.on_mod_output_wave(slot_id, output_idx, wave_index)

    def on_mod_output_phase(self, slot_id, output_idx, phase_index):
        return self.modulation.on_mod_output_phase(slot_id, output_idx, phase_index)

    def on_mod_output_polarity(self, slot_id, output_idx, polarity):
        return self.modulation.on_mod_output_polarity(slot_id, output_idx, polarity)

    def on_mod_env_attack(self, slot_id, env_idx, value):
        return self.modulation.on_mod_env_attack(slot_id, env_idx, value)

    def on_mod_env_release(self, slot_id, env_idx, value):
        return self.modulation.on_mod_env_release(slot_id, env_idx, value)

    def on_mod_env_curve(self, slot_id, env_idx, value):
        return self.modulation.on_mod_env_curve(slot_id, env_idx, value)

    def on_mod_env_sync_mode(self, slot_id, env_idx, mode):
        return self.modulation.on_mod_env_sync_mode(slot_id, env_idx, mode)

    def on_mod_env_loop_rate(self, slot_id, env_idx, rate_idx):
        return self.modulation.on_mod_env_loop_rate(slot_id, env_idx, rate_idx)

    def on_mod_tension(self, slot_id, output_idx, normalized):
        return self.modulation.on_mod_tension(slot_id, output_idx, normalized)

    def on_mod_mass(self, slot_id, output_idx, normalized):
        return self.modulation.on_mod_mass(slot_id, output_idx, normalized)

    def on_mod_bus_value(self, bus_idx, value):
        return self.modulation.on_mod_bus_value(bus_idx, value)

    def on_mod_values_received(self, values):
        return self.modulation.on_mod_values_received(values)

    def _flush_mod_scopes(self):
        return self.modulation._flush_mod_scopes()

    def _connect_mod_routing_signals(self):
        return self.modulation._connect_mod_routing_signals()

    def _on_mod_route_added(self, conn):
        return self.modulation._on_mod_route_added(conn)

    def _on_mod_route_removed(self, source_bus, target_slot, target_param):
        return self.modulation._on_mod_route_removed(source_bus, target_slot, target_param)

    def _on_mod_route_changed(self, conn):
        return self.modulation._on_mod_route_changed(conn)

    def _get_slot_slider(self, slot, param):
        return self.modulation._get_slot_slider(slot, param)

    def _update_slider_mod_range(self, slot_id, param):
        return self.modulation._update_slider_mod_range(slot_id, param)

    def _on_mod_routes_cleared(self):
        return self.modulation._on_mod_routes_cleared()

    def _sync_mod_routing_to_sc(self):
        return self.modulation._sync_mod_routing_to_sc()

    def _open_mod_matrix(self):
        return self.modulation._open_mod_matrix()

    def _open_crossmod_matrix(self):
        return self.modulation._open_crossmod_matrix()

    def _open_fx_window(self):
        return self.modulation._open_fx_window()

    def _clear_all_mod_routes(self):
        return self.modulation._clear_all_mod_routes()

    def _get_target_slider_value(self, slot_id, param):
        return self.modulation._get_target_slider_value(slot_id, param)

    def _on_mod_slot_type_changed_for_matrix(self, slot_id, gen_name):
        return self.modulation._on_mod_slot_type_changed_for_matrix(slot_id, gen_name)

    # ── Mixer Controller Wrappers ───────────────────────────────────────
    # Method bodies moved to MixerController (Phase 4 refactor)

    def on_generator_volume_changed(self, gen_id, volume):
        return self.mixer.on_generator_volume_changed(gen_id, volume)

    def on_generator_muted(self, gen_id, muted):
        return self.mixer.on_generator_muted(gen_id, muted)

    def on_generator_solo(self, gen_id, solo):
        return self.mixer.on_generator_solo(gen_id, solo)

    def on_generator_gain_changed(self, gen_id, gain_db):
        return self.mixer.on_generator_gain_changed(gen_id, gain_db)

    def on_generator_pan_changed(self, gen_id, pan):
        return self.mixer.on_generator_pan_changed(gen_id, pan)

    def on_generator_eq_changed(self, gen_id, band, value):
        return self.mixer.on_generator_eq_changed(gen_id, band, value)

    def on_generator_echo_send(self, gen_id, value):
        return self.mixer.on_generator_echo_send(gen_id, value)

    def on_generator_verb_send(self, gen_id, value):
        return self.mixer.on_generator_verb_send(gen_id, value)

    def _sync_strip_state_to_sc(self, slot_id):
        return self.generator._sync_strip_state_to_sc(slot_id)

    def _sync_generator_slot_state_to_sc(self, slot_id):
        return self.generator._sync_generator_slot_state_to_sc(slot_id)

    # ── Master Controller Wrappers ──────────────────────────────────────
    # Method bodies moved to MasterController (Phase 4 refactor)

    def on_master_volume_from_master(self, volume):
        return self.master.on_master_volume_from_master(volume)

    def on_meter_mode_changed(self, mode):
        return self.master.on_meter_mode_changed(mode)

    def on_limiter_ceiling_changed(self, db):
        return self.master.on_limiter_ceiling_changed(db)

    def on_limiter_bypass_changed(self, bypass):
        return self.master.on_limiter_bypass_changed(bypass)

    def on_eq_lo_changed(self, db):
        return self.master.on_eq_lo_changed(db)

    def on_eq_mid_changed(self, db):
        return self.master.on_eq_mid_changed(db)

    def on_eq_hi_changed(self, db):
        return self.master.on_eq_hi_changed(db)

    def on_eq_lo_kill_changed(self, kill):
        return self.master.on_eq_lo_kill_changed(kill)

    def on_eq_mid_kill_changed(self, kill):
        return self.master.on_eq_mid_kill_changed(kill)

    def on_eq_hi_kill_changed(self, kill):
        return self.master.on_eq_hi_kill_changed(kill)

    def on_eq_locut_changed(self, enabled):
        return self.master.on_eq_locut_changed(enabled)

    def on_eq_bypass_changed(self, bypass):
        return self.master.on_eq_bypass_changed(bypass)

    def on_comp_threshold_changed(self, db):
        return self.master.on_comp_threshold_changed(db)

    def on_comp_ratio_changed(self, idx):
        return self.master.on_comp_ratio_changed(idx)

    def on_comp_attack_changed(self, idx):
        return self.master.on_comp_attack_changed(idx)

    def on_comp_release_changed(self, idx):
        return self.master.on_comp_release_changed(idx)

    def on_comp_makeup_changed(self, db):
        return self.master.on_comp_makeup_changed(db)

    def on_comp_sc_hpf_changed(self, idx):
        return self.master.on_comp_sc_hpf_changed(idx)

    def on_comp_bypass_changed(self, bypass):
        return self.master.on_comp_bypass_changed(bypass)

    def on_comp_gr_received(self, gr_db):
        return self.master.on_comp_gr_received(gr_db)

    def on_audio_device_changed(self, device_name):
        return self.master.on_audio_device_changed(device_name)

    def on_audio_devices_received(self, devices, current):
        return self.master.on_audio_devices_received(devices, current)

    def on_audio_device_changing(self, device_name):
        return self.master.on_audio_device_changing(device_name)

    def on_audio_device_ready(self, device_name):
        return self.master.on_audio_device_ready(device_name)

    def on_levels_received(self, amp_l, amp_r, peak_l, peak_r):
        return self.master.on_levels_received(amp_l, amp_r, peak_l, peak_r)

    def on_channel_levels_received(self, slot_id, amp_l, amp_r):
        return self.master.on_channel_levels_received(slot_id, amp_l, amp_r)
    
    def toggle_console(self):
        """Toggle console panel visibility."""
        self.console_panel.toggle_panel()
        self.console_btn.setChecked(self.console_panel.is_open)
    
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

    # === MIDI Mode Toggle ===

    # ── MIDI Mode Controller Wrappers ───────────────────────────────────
    # Method bodies moved to MidiModeController (Phase 7 refactor)

    def _midi_mode_btn_style(self, active):
        return self.midi_mode._midi_mode_btn_style(active)

    def _toggle_midi_mode(self):
        return self.midi_mode._toggle_midi_mode()

    def _restore_midi_mode_states(self):
        return self.midi_mode._restore_midi_mode_states()

    def _deactivate_midi_mode(self):
        return self.midi_mode._deactivate_midi_mode()

    # ── Preset Controller Wrappers ──────────────────────────────────────
    # Method bodies moved to PresetController (Phase 1 refactor)

    def _save_preset(self):
        return self.preset._save_preset()

    def _save_preset_as(self):
        return self.preset._save_preset_as()

    def _do_save_preset(self, name: str, filepath):
        return self.preset._do_save_preset(name, filepath)

    def _load_preset(self):
        return self.preset._load_preset()

    def _apply_preset(self, state):
        return self.preset._apply_preset(state)

    def _init_preset(self):
        return self.preset._init_preset()

    # Keyboard Mode

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

    def _toggle_keyboard_mode(self):
        return self.keyboard._toggle_keyboard_mode()

    def _send_midi_note_on(self, slot, note, velocity):
        return self.keyboard._send_midi_note_on(slot, note, velocity)

    def _send_midi_note_off(self, slot, note):
        return self.keyboard._send_midi_note_off(slot, note)

    def _send_all_notes_off(self, slot):
        return self.keyboard._send_all_notes_off(slot)

    def _get_focused_slot(self):
        return self.keyboard._get_focused_slot()

    def _is_slot_midi_mode(self, slot_id):
        return self.keyboard._is_slot_midi_mode(slot_id)

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

    # ── MIDI CC Controller Wrappers ─────────────────────────────────────
    # Method bodies moved to MidiCCController (Phase 2 refactor)

    def _on_midi_cc(self, channel, cc, value):
        return self.midi_cc._on_midi_cc(channel, cc, value)

    def _process_pending_cc(self):
        return self.midi_cc._process_pending_cc()

    def _apply_cc_to_control(self, control, channel, cc, value):
        return self.midi_cc._apply_cc_to_control(control, channel, cc, value)

    def _on_learn_started(self, control):
        return self.midi_cc._on_learn_started(control)

    def _on_learn_completed(self, channel, cc, control):
        return self.midi_cc._on_learn_completed(channel, cc, control)

    def _on_learn_cancelled(self, control):
        return self.midi_cc._on_learn_cancelled(control)

    def _find_control_by_name(self, name):
        return self.midi_cc._find_control_by_name(name)

    def save_midi_mappings(self):
        return self.midi_cc.save_midi_mappings()

    def save_midi_mappings_as(self):
        return self.midi_cc.save_midi_mappings_as()

    def load_midi_mappings(self):
        return self.midi_cc.load_midi_mappings()

    def clear_all_midi_mappings(self):
        return self.midi_cc.clear_all_midi_mappings()

    def _setup_midi_menu(self):
        return self.midi_cc._setup_midi_menu()

    def _update_midi_status(self):
        return self.midi_cc._update_midi_status()

    @property
    def cc_mapping_manager(self):
        """Compatibility property - cc_mapping_manager now lives in MidiCCController."""
        return self.midi_cc.cc_mapping_manager

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

