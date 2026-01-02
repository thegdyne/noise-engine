"""
Main Frame - Combines all components
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QShortcut, QApplication)
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QFont, QKeySequence

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
from src.presets import PresetManager, PresetState, SlotState, MixerState, ChannelState, MasterState, ModSourcesState, FXState
from src.midi import MidiCCMappingManager, MidiCCLearnManager


class MainFrame(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Noise Engine")
        self.setMinimumSize(1200, 700)
        self.setGeometry(100, 50, 1400, 800)
        
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        
        self.osc = OSCBridge()

        # MIDI CC mapping (Phase 1+2)
        self.cc_mapping_manager = MidiCCMappingManager()
        self.cc_learn_manager = MidiCCLearnManager(self.cc_mapping_manager)

        # MIDI CC flood control (~60Hz update rate)
        self._pending_cc = {}  # (channel, cc) -> value
        self._cc_timer = QTimer(self)
        self._cc_timer.timeout.connect(self._process_pending_cc)
        self._cc_timer.start(16)  # ~60Hz

        # MIDI menu
        self._setup_midi_menu()

        # Connect MIDI CC signal from OSC
        self.osc.midi_cc_received.connect(self._on_midi_cc)

        # Connect learn manager signals for visual feedback
        self.cc_learn_manager.learn_started.connect(self._on_learn_started)
        self.cc_learn_manager.learn_completed.connect(self._on_learn_completed)
        self.cc_learn_manager.learn_cancelled.connect(self._on_learn_cancelled)

        self.osc_connected = False
        
        self.active_generators = {}
        self.active_effects = {}

        self.master_bpm = BPM_DEFAULT

        # Preset manager
        self.preset_manager = PresetManager()

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

    def _clear_dirty(self, preset_name: str = None):
        """Clear dirty flag after save/load."""
        self._dirty = False
        self._current_preset_name = preset_name
        self._update_window_title()

    def _update_window_title(self):
        """Update window title with preset name and dirty indicator."""
        base = "Noise Engine"
        if self._current_preset_name:
            base = f"Noise Engine - {self._current_preset_name}"
        if self._dirty:
            base = f"• {base}"
        self.setWindowTitle(base)

    def setup_ui(self):
        """Create the main interface layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # Content area with console overlay
        content_container = QWidget()
        content_outer = QHBoxLayout(content_container)
        content_outer.setContentsMargins(0, 0, 0, 0)
        content_outer.setSpacing(0)
        
        # Main content (left side)
        content_widget = QWidget()
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
        self.save_btn.setStyleSheet(button_style('submenu'))
        self.save_btn.clicked.connect(self._save_preset)
        layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("Load")
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

    def toggle_connection(self):
        """Connect/disconnect to SuperCollider."""
        if not self.osc_connected:
            # Connect signals before connecting
            self.osc.gate_triggered.connect(self.on_gate_trigger)
            self.osc.levels_received.connect(self.on_levels_received)
            self.osc.channel_levels_received.connect(self.on_channel_levels_received)
            self.osc.connection_lost.connect(self.on_connection_lost)
            self.osc.connection_restored.connect(self.on_connection_restored)
            self.osc.audio_devices_received.connect(self.on_audio_devices_received)
            self.osc.audio_device_changing.connect(self.on_audio_device_changing)
            self.osc.audio_device_ready.connect(self.on_audio_device_ready)
            self.osc.comp_gr_received.connect(self.on_comp_gr_received)
            self.osc.mod_bus_value_received.connect(self.on_mod_bus_value)
            self.osc.mod_values_received.connect(self.on_mod_values_received)
            
            if self.osc.connect():
                self.osc_connected = True
                # Initialize crossmod OSC bridge
                if self.crossmod_osc is None:
                    self.crossmod_osc = CrossmodOSCBridge(self.crossmod_state, self.osc.client)
                self._set_header_buttons_enabled(True)
                self.master_section.set_osc_bridge(self.osc)
                self.inline_fx.set_osc_bridge(self.osc)
                self.inline_fx.sync_state()
                if self.fx_window:
                    self.fx_window.set_osc_bridge(self.osc)
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("Connected")
                self.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
                
                self.osc.client.send_message(OSC_PATHS['clock_bpm'], [self.master_bpm])
                
                # Send initial master volume
                self.osc.client.send_message(OSC_PATHS['master_volume'], [self.master_section.get_volume()])
                
                # Query audio devices
                self.osc.query_audio_devices()
                
                # Send current MIDI device if one is selected
                current_midi = self.midi_selector.get_current_device()
                if current_midi:
                    port_index = self.midi_selector.get_port_index(current_midi)
                    if port_index >= 0:
                        self.osc.client.send_message(OSC_PATHS['midi_device'], [port_index])
                
                # Send initial mod source state
                self._sync_mod_sources()
            else:
                self.status_label.setText("Connection Failed")
                self.status_label.setStyleSheet(f"color: {COLORS['warning_text']};")
        else:
            try:
                # Disconnect all signals connected in toggle_connection
                self.osc.gate_triggered.disconnect(self.on_gate_trigger)
                self.osc.levels_received.disconnect(self.on_levels_received)
                self.osc.channel_levels_received.disconnect(self.on_channel_levels_received)
                self.osc.connection_lost.disconnect(self.on_connection_lost)
                self.osc.connection_restored.disconnect(self.on_connection_restored)
                self.osc.audio_devices_received.disconnect(self.on_audio_devices_received)
                self.osc.audio_device_changing.disconnect(self.on_audio_device_changing)
                self.osc.audio_device_ready.disconnect(self.on_audio_device_ready)
                self.osc.comp_gr_received.disconnect(self.on_comp_gr_received)
                self.osc.mod_bus_value_received.disconnect(self.on_mod_bus_value)
                self.osc.mod_values_received.disconnect(self.on_mod_values_received)
            except TypeError:
                pass  # Signals weren't connected
            self.osc.disconnect()
            self.osc_connected = False
            self._set_header_buttons_enabled(False)
            self.connect_btn.setText("Connect SuperCollider")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet(f"color: {COLORS['submenu_text']};")
    
    def on_connection_lost(self):
        """Handle connection lost - show prominent warning."""
        self.osc_connected = False
        self._set_header_buttons_enabled(False)
        self.connect_btn.setText("RECONNECT")
        self.connect_btn.setStyleSheet(f"background-color: {COLORS['warning_text']}; color: black; font-weight: bold;")
        self.status_label.setText("CONNECTION LOST")
        self.status_label.setStyleSheet(f"color: {COLORS['warning_text']}; font-weight: bold;")
    
    def on_connection_restored(self):
        """Handle connection restored after reconnect."""
        self.osc_connected = True
        self._set_header_buttons_enabled(True)
        self.master_section.set_osc_bridge(self.osc)
        self.inline_fx.set_osc_bridge(self.osc)
        self.inline_fx.sync_state()
        if self.fx_window:
            self.fx_window.set_osc_bridge(self.osc)
        self.connect_btn.setText("Disconnect")
        self.connect_btn.setStyleSheet(self._connect_btn_style())  # Restore original style
        self.status_label.setText("Connected")
        self.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
        
        # Resend current state
        self.osc.client.send_message(OSC_PATHS['clock_bpm'], [self.master_bpm])
        
        # Clear mod routing (SC has fresh state after restart)
        self.mod_routing.clear()
    
    def _connect_btn_style(self):
        """Return the standard connect button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {COLORS['border_light']};
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['text']};
            }}
        """
    
    def on_gate_trigger(self, slot_id):
        """Handle gate trigger from SC - flash LED."""
        slot = self.generator_grid.get_slot(slot_id)
        if slot:
            slot.flash_gate()
    
    def on_midi_device_changed(self, device_name):
        """Handle MIDI device selection change."""
        if self.osc_connected:
            if device_name:
                port_index = self.midi_selector.get_port_index(device_name)
                if port_index >= 0:
                    self.osc.client.send_message(OSC_PATHS['midi_device'], [port_index])
                    logger.info(f"MIDI device: {device_name} (port {port_index})", component="MIDI")
            else:
                self.osc.client.send_message(OSC_PATHS['midi_device'], [-1])  # -1 = disconnect
                logger.info("MIDI device: None", component="MIDI")
        
    def on_generator_param_changed(self, slot_id, param_name, value):
        """Handle per-generator parameter change."""
        if self.osc_connected:
            path = OSC_PATHS.get(f'gen_{param_name}', f'/noise/gen/{param_name}')
            self.osc.client.send_message(path, [slot_id, value])
        self._mark_dirty()
    
    def on_generator_custom_param_changed(self, slot_id, param_index, value):
        """Handle per-generator custom parameter change."""
        if self.osc_connected:
            # Safety clamp to prevent OSC float overflow
            value = max(-1e30, min(1e30, float(value)))
            path = f"{OSC_PATHS['gen_custom']}/{slot_id}/{param_index}"
            self.osc.client.send_message(path, [value])
        self._mark_dirty()

    def on_generator_filter_changed(self, slot_id, filter_type):
        """Handle generator filter type change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_filter_type'], [slot_id, FILTER_TYPE_INDEX[filter_type]])
        self._mark_dirty()

    def on_generator_clock_enabled(self, slot_id, enabled):
        """Handle generator envelope ON/OFF (legacy)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_env_enabled'], [slot_id, 1 if enabled else 0])

    def on_generator_transpose(self, slot_id, semitones):
        """Send transpose to SuperCollider."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_transpose'], [slot_id, semitones])
        self._mark_dirty()

    def on_generator_env_source(self, slot_id, source):
        """Handle generator ENV source change (0=OFF, 1=CLK, 2=MIDI)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_env_source'], [slot_id, source])
        logger.gen(slot_id, f"env source: {['OFF', 'CLK', 'MIDI'][source]}")
        
        # Detect manual change while MIDI mode is active
        if self._midi_mode_active and not self._midi_mode_changing:
            self._deactivate_midi_mode()
        self._mark_dirty()

    def on_generator_clock_rate(self, slot_id, rate):
        """Handle generator clock rate change - send index."""
        rate_index = CLOCK_RATE_INDEX.get(rate, 3)  # Default to CLK
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_clock_rate'], [slot_id, rate_index])
        logger.gen(slot_id, f"rate: {rate} (index {rate_index})")
        self._mark_dirty()

    def on_generator_mute(self, slot_id, muted):
        """Handle generator mute from slot button."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1 if muted else 0])
        logger.gen(slot_id, f"mute: {muted}")
    
    def on_generator_midi_channel(self, slot_id, channel):
        """Handle generator MIDI channel change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_midi_channel'], [slot_id, channel])
        logger.gen(slot_id, f"MIDI channel: {channel}")

    def on_generator_portamento(self, slot_id, value):  # ADD FROM HERE
        """Handle portamento knob change - send normalized value via OSC."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_portamento'], [slot_id, value])
        logger.gen(slot_id, f"portamento: {value:.3f}")
        self._mark_dirty()

    def on_generator_selected(self, slot_id):
        """Handle generator slot selection (legacy click handler)."""
        # Legacy - cycles through generators on click
        # New behavior uses on_generator_changed from CycleButton
        pass
    
    def on_generator_changed(self, slot_id, new_type):
        """Handle generator type change from CycleButton."""
        from src.config import get_generator_midi_retrig, get_generator_output_trim_db
        
        synth_name = GENERATORS.get(new_type)
        
        # Update the slot (custom params, etc)
        self.generator_grid.set_generator_type(slot_id, new_type)
        
        if synth_name:
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['start_generator'], [slot_id, synth_name])
                # Tell SC if this generator needs MIDI retriggering
                midi_retrig = 1 if get_generator_midi_retrig(new_type) else 0
                self.osc.client.send_message(OSC_PATHS['midi_retrig'], [slot_id, midi_retrig])
                # Send output trim for loudness normalization (from generator JSON config)
                trim_db = get_generator_output_trim_db(new_type)
                self.osc.client.send_message(OSC_PATHS['gen_trim'], [slot_id, trim_db])
                # Re-sync strip state (pan/EQ/mute/solo/gain) so UI values persist
                self._sync_strip_state_to_sc(slot_id)
                # Re-sync generator slot state (mute/env/rate/midi/filter persist across type changes)
                self._sync_generator_slot_state_to_sc(slot_id)
            
            self.generator_grid.set_generator_active(slot_id, True)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(True)
            self.active_generators[slot_id] = synth_name
            
            # Update mixer channel active state
            self.mixer_panel.set_channel_active(slot_id, True)
        else:
            if self.osc_connected:
                self.osc.client.send_message(OSC_PATHS['stop_generator'], [slot_id])
                # Clear midi_retrig flag
                self.osc.client.send_message(OSC_PATHS['midi_retrig'], [slot_id, 0])
            
            self.generator_grid.set_generator_active(slot_id, False)
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slot.set_audio_status(False)
            if slot_id in self.active_generators:
                del self.active_generators[slot_id]
            
            # Update mixer channel active state
            self.mixer_panel.set_channel_active(slot_id, False)
        self._mark_dirty()

    # -------------------------------------------------------------------------
    # Mod Source Handlers
    # -------------------------------------------------------------------------
    
    def _sync_mod_slot_state(self, slot_id, send_generator=True):
        """Push full UI state for one mod slot to SC (SSOT)."""
        if not self.osc_connected:
            return
        from src.config import get_mod_generator_custom_params, map_value
        
        slot = self.modulator_grid.get_slot(slot_id)
        if not slot:
            return
        
        gen_name = slot.generator_name
        
        if send_generator:
            self.osc.client.send_message(OSC_PATHS['mod_generator'], [slot_id, gen_name])
        
        # Enable/disable scope
        enabled = 1 if gen_name != "Empty" else 0
        self.osc.client.send_message(OSC_PATHS['mod_scope_enable'], [slot_id, enabled])
        
        if gen_name == "Empty":
            return
        
        # Sync outputs (wave/phase/polarity) from UI
        for out_idx, row in enumerate(slot.output_rows):
            if 'wave' in row:
                self.osc.client.send_message(OSC_PATHS['mod_output_wave'], [slot_id, out_idx, row['wave'].get_index()])
            if 'phase' in row:
                self.osc.client.send_message(OSC_PATHS['mod_output_phase'], [slot_id, out_idx, row['phase'].get_index()])
            if 'polarity' in row:
                self.osc.client.send_message(OSC_PATHS['mod_output_polarity'], [slot_id, out_idx, row['polarity'].get_index()])
        
        # Sync custom params from UI sliders/buttons
        for param in get_mod_generator_custom_params(gen_name):
            key = param['key']
            control = slot.param_sliders.get(key)
            if control:
                # CycleButton (mode) vs DragSlider (rate, shape, etc)
                if hasattr(control, 'get_index'):
                    # CycleButton - index is the value (0=CLK, 1=FREE)
                    real_value = float(control.get_index())
                else:
                    # DragSlider - normalize and map
                    normalized = control.value() / 1000.0
                    real_value = map_value(normalized, param)
                self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, key, real_value])
    
    def _sync_mod_sources(self):
        """Send current mod source state to SC on connect."""
        from src.config import MOD_SLOT_COUNT
        
        for slot_id in range(1, MOD_SLOT_COUNT + 1):
            self._sync_mod_slot_state(slot_id, send_generator=True)
            slot = self.modulator_grid.get_slot(slot_id)
            if slot:
                logger.debug(f"Synced mod {slot_id}: {slot.generator_name}", component="OSC")
    
    def on_mod_generator_changed(self, slot_id, gen_name):
        """Handle mod source generator change - full sync to SC."""
        if self.osc_connected:
            # Full push to SC so UI is SSOT after rebuild
            self._sync_mod_slot_state(slot_id, send_generator=True)
        logger.debug(f"Mod {slot_id} generator: {gen_name}", component="OSC")
        self._mark_dirty()

    def on_mod_param_changed(self, slot_id, key, value):
        """Handle mod source parameter change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, key, value])
        logger.debug(f"Mod {slot_id} {key}: {value:.3f}", component="OSC")
        
    def on_mod_output_wave(self, slot_id, output_idx, wave_index):
        """Handle mod output waveform change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_output_wave'], [slot_id, output_idx, wave_index])
        logger.debug(f"Mod {slot_id} out {output_idx} wave: {wave_index}", component="OSC")
        
    def on_mod_output_phase(self, slot_id, output_idx, phase_index):
        """Handle mod output phase change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_output_phase'], [slot_id, output_idx, phase_index])
        logger.debug(f"Mod {slot_id} out {output_idx} phase: {phase_index}", component="OSC")

    def on_mod_output_polarity(self, slot_id, output_idx, polarity):
        """Handle mod output polarity change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_output_polarity'], [slot_id, output_idx, polarity])
        logger.debug(f"Mod {slot_id} out {output_idx} polarity: {polarity}", component="OSC")

    # ARSEq+ envelope handlers
    def on_mod_env_attack(self, slot_id, env_idx, value):
        """Handle ARSEq+ envelope attack change."""
        param_name = ["atkA", "atkB", "atkC", "atkD"][env_idx]
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, value])
        logger.debug(f"Mod {slot_id} env {env_idx} attack: {value:.3f}", component="OSC")

    def on_mod_env_release(self, slot_id, env_idx, value):
        """Handle ARSEq+ envelope release change."""
        param_name = ["relA", "relB", "relC", "relD"][env_idx]
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, value])
        logger.debug(f"Mod {slot_id} env {env_idx} release: {value:.3f}", component="OSC")

    def on_mod_env_curve(self, slot_id, env_idx, value):
        """Handle ARSEq+ envelope curve change."""
        param_name = ["curveA", "curveB", "curveC", "curveD"][env_idx]
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, value])
        logger.debug(f"Mod {slot_id} env {env_idx} curve: {value:.3f}", component="OSC")

    def on_mod_env_sync_mode(self, slot_id, env_idx, mode):
        """Handle ARSEq+ envelope sync mode change."""
        param_name = ["syncModeA", "syncModeB", "syncModeC", "syncModeD"][env_idx]
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, float(mode)])
        logger.debug(f"Mod {slot_id} env {env_idx} sync_mode: {mode}", component="OSC")

    def on_mod_env_loop_rate(self, slot_id, env_idx, rate_idx):
        """Handle ARSEq+ envelope loop rate change."""
        param_name = ["loopRateA", "loopRateB", "loopRateC", "loopRateD"][env_idx]
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, float(rate_idx)])
        logger.debug(f"Mod {slot_id} env {env_idx} loop_rate: {rate_idx}", component="OSC")

    def on_mod_tension(self, slot_id, output_idx, normalized):
        """Handle SauceOfGrav tension change."""
        print(f"DEBUG: on_mod_tension - osc_connected={self.osc_connected}")
        param_name = f"tension{output_idx + 1}"
        if self.osc_connected:
            print(f"DEBUG: sending OSC /noise/mod/param [{slot_id}, {param_name}, {normalized}]")
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, normalized])
        else:
            print("DEBUG: OSC not connected, message not sent")
        logger.debug(f"Mod {slot_id} tension{output_idx + 1}: {normalized:.3f}", component="OSC")

    def on_mod_mass(self, slot_id, output_idx, normalized):
        """Handle SauceOfGrav mass change."""
        param_name = f"mass{output_idx + 1}"
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_param'], [slot_id, param_name, normalized])
        logger.debug(f"Mod {slot_id} mass{output_idx + 1}: {normalized:.3f}", component="OSC")

    def on_mod_bus_value(self, bus_idx, value):
        """Handle mod bus value from SC - route to appropriate scope."""
        # Calculate slot from bus index: bus 0-3 slot 1, bus 4-7 slot 2, etc.
        slot_id = (bus_idx // 4) + 1
        output_idx = bus_idx % 4
        
        slot = self.modulator_grid.get_slot(slot_id)
        if slot and hasattr(slot, 'scope') and slot.scope.isEnabled():
            slot.scope.push_value(output_idx, value)
            self._mod_scope_dirty.add(slot_id)  # Mark for repaint
    
    def on_mod_values_received(self, values):
        """Handle batched modulated parameter values from SC - update sliders.
        
        Args:
            values: List of (slot, param, raw_value) tuples where raw_value is
                    the actual mapped parameter value (Hz, seconds, etc.)
        """
        for slot_id, param, raw_value in values:
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                slider = self._get_slot_slider(slot, param)
                if slider:
                    # Convert raw mapped value to normalized 0-1 for slider display
                    param_config = get_param_config(param)
                    norm_value = unmap_value(raw_value, param_config)
                    slider.set_modulated_value(norm_value)
        
    def _flush_mod_scopes(self):
        """Repaint dirty scopes at throttled rate (~30fps)."""
        for slot_id in list(self._mod_scope_dirty):
            slot = self.modulator_grid.get_slot(slot_id)
            if slot and hasattr(slot, 'scope') and slot.scope.isEnabled():
                slot.scope.update()
        self._mod_scope_dirty.clear()
    
    def _connect_mod_routing_signals(self):
        """Connect mod routing state signals to OSC."""
        self.mod_routing.connection_added.connect(self._on_mod_route_added)
        self.mod_routing.connection_removed.connect(self._on_mod_route_removed)
        self.mod_routing.connection_changed.connect(self._on_mod_route_changed)
        self.mod_routing.all_cleared.connect(self._on_mod_routes_cleared)
    
    def _on_mod_route_added(self, conn):
        """Send new mod route to SC and update slider visualization."""
        if self.osc_connected:
            self.osc.client.send_message(
                OSC_PATHS['mod_route_add'],
                [conn.source_bus, conn.target_slot, conn.target_param,
                 conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
            )
            logger.debug(f"Mod route added: bus {conn.source_bus} → slot {conn.target_slot}.{conn.target_param} "
                        f"(d={conn.depth}, a={conn.amount}, o={conn.offset}, p={conn.polarity.name}, i={conn.invert})", component="MOD")
        
        # Update slider visualization
        self._update_slider_mod_range(conn.target_slot, conn.target_param)
        self._mark_dirty()

    def _on_mod_route_removed(self, source_bus, target_slot, target_param):
        """Send mod route removal to SC and update slider visualization."""
        if self.osc_connected:
            self.osc.client.send_message(
                OSC_PATHS['mod_route_remove'],
                [source_bus, target_slot, target_param]
            )
            logger.debug(f"Mod route removed: bus {source_bus} → slot {target_slot}.{target_param}", component="MOD")
        
        # Update slider visualization (may clear if no more routes)
        self._update_slider_mod_range(target_slot, target_param)
        self._mark_dirty()

    def _on_mod_route_changed(self, conn):
        """Send mod route parameter change to SC."""
        if self.osc_connected:
            # Send all params via set message
            self.osc.client.send_message(
                OSC_PATHS['mod_route_set'],
                [conn.source_bus, conn.target_slot, conn.target_param,
                 conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
            )
        
        # Update slider visualization (deferred to ensure state is fully updated)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._update_slider_mod_range(conn.target_slot, conn.target_param))
    
    def _get_slot_slider(self, slot, param):
        """Get slider for a param, handling both standard and custom (P1-P5) params.
        
        Args:
            slot: Generator slot widget
            param: Parameter name ('cutoff', 'p1', etc.)
            
        Returns:
            FaderSlider or None if not found
        """
        # Check for custom params (p1-p5)
        if param.startswith('p') and len(param) == 2 and param[1].isdigit():
            idx = int(param[1]) - 1  # p1 -> 0, p2 -> 1, etc.
            if hasattr(slot, 'custom_sliders') and 0 <= idx < len(slot.custom_sliders):
                return slot.custom_sliders[idx]
            return None
        
        # Standard params
        if hasattr(slot, 'sliders') and param in slot.sliders:
            return slot.sliders[param]
        return None
    
    def _update_slider_mod_range(self, slot_id, param):
        """Update slider modulation range visualization based on active connections.
        
        Computes modulation range in real parameter units using the same math as SC,
        then unmaps back to 0-1 slider space for display.
        """
        from PyQt5.QtGui import QColor
        from src.config import map_value
        import math
        
        slot = self.generator_grid.get_slot(slot_id)
        if not slot:
            return
        
        slider = self._get_slot_slider(slot, param)
        if not slider:
            return
        
        # Get all connections to this param
        connections = self.mod_routing.get_connections_for_target(slot_id, param)
        
        if not connections:
            # No modulation - clear visualization
            slider.clear_modulation()
            return
        
        # Get param config for this parameter
        param_config = get_param_config(param)
        min_val = param_config.get('min', 0.0)
        max_val = param_config.get('max', 1.0)
        curve = param_config.get('curve', 'lin')
        oct_range = param_config.get('oct_range', 0)
        
        # Get current slider position and convert to real value
        slider_norm = slider.value() / 1000.0  # Normalized 0-1
        base_real = map_value(slider_norm, param_config)
        
        # Sum up total amount and offset from all connections
        # Sum per-connection extrema respecting polarity mode
        from src.gui.mod_routing_state import Polarity
        
        delta_min = 0.0
        delta_max = 0.0
        
        for c in connections:
            r = c.effective_range  # depth * amount
            
            if c.polarity == Polarity.BIPOLAR:
                mn, mx = -r, +r
            elif c.polarity == Polarity.UNI_POS:
                mn, mx = 0.0, +r
            else:  # Polarity.UNI_NEG
                mn, mx = -r, 0.0
            
            mn += c.offset
            mx += c.offset
            
            delta_min += mn
            delta_max += mx
        
        # Apply modulation curve to get real value range
        if curve == 'exp' and oct_range > 0:
            # Exponential: out = base * 2^(delta * octRange)
            # Protect against invalid base values
            if base_real <= 0:
                base_real = min_val if min_val > 0 else 0.001
            mod_max_real = base_real * math.pow(2, delta_max * oct_range)
            mod_min_real = base_real * math.pow(2, delta_min * oct_range)
        else:
            # Linear: out = base + delta * range
            param_range = max_val - min_val
            mod_max_real = base_real + delta_max * param_range
            mod_min_real = base_real + delta_min * param_range
        
        # Clamp to param limits
        mod_max_real = max(min_val, min(max_val, mod_max_real))
        mod_min_real = max(min_val, min(max_val, mod_min_real))
        
        # Ensure min <= max
        if mod_min_real > mod_max_real:
            mod_min_real, mod_max_real = mod_max_real, mod_min_real
        
        # Unmap back to 0-1 slider space for display
        range_min = unmap_value(mod_min_real, param_config)
        range_max = unmap_value(mod_max_real, param_config)
        
        # Get color: mixed if multiple sources, else based on first source type
        if len(connections) > 1:
            # Multiple sources - use cyan to indicate mixed
            color = QColor('#00cccc')
        else:
            # Single source - color by type
            conn = connections[0]
            mod_slot = conn.source_bus // 4 + 1
            source_slot = self.modulator_grid.get_slot(mod_slot)
            if source_slot and source_slot.generator_name == 'Sloth':
                color = QColor('#ff8800')  # Orange
            else:
                color = QColor('#00ff66')  # Green
        
        # Pass same values for outer and inner (single bracket pair now)
        slider.set_modulation_range(range_min, range_max, range_min, range_max, color)

    def _on_mod_routes_cleared(self):
        """Handle all routes cleared - send OSC and clear all slider brackets."""
        # Send OSC to SuperCollider
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['mod_route_clear_all'], [])

        logger.debug("All mod routes cleared", component="MOD")

        # Clear all slider modulation visualizations
        for slot_id in range(1, 9):
            slot = self.generator_grid.get_slot(slot_id)
            if slot:
                # Standard params
                for param, slider in slot.sliders.items():
                    slider.clear_modulation()
                # Custom params (P1-P5)
                if hasattr(slot, 'custom_sliders'):
                    for slider in slot.custom_sliders:
                        slider.clear_modulation()
    
    def _sync_mod_routing_to_sc(self):
        """Sync all mod routing state to SC (called on reconnect)."""
        if not self.osc_connected:
            return
        for conn in self.mod_routing.get_all_connections():
            self.osc.client.send_message(
                OSC_PATHS['mod_route_add'],
                [conn.source_bus, conn.target_slot, conn.target_param,
                 conn.depth, conn.amount, conn.offset, conn.polarity.value, int(conn.invert)]
            )
        logger.debug(f"Synced {len(self.mod_routing)} mod routes to SC", component="MOD")
    
    def _open_mod_matrix(self):
        """Toggle the mod routing matrix window (Cmd+M)."""
        if self.mod_matrix_window is None:
            self.mod_matrix_window = ModMatrixWindow(
                self.mod_routing, 
                get_target_value_callback=self._get_target_slider_value,
                parent=self
            )
            # Connect mod slot type changes to update matrix
            self.modulator_grid.generator_changed.connect(self._on_mod_slot_type_changed_for_matrix)
        
        # Toggle visibility
        if self.mod_matrix_window.isVisible():
            self.mod_matrix_window.hide()
            logger.info("Mod matrix window closed", component="MOD")
        else:
            self.mod_matrix_window.show()
            # Center on main window
            main_geo = self.geometry()
            window_geo = self.mod_matrix_window.geometry()
            x = main_geo.x() + (main_geo.width() - window_geo.width()) // 2
            y = main_geo.y() + (main_geo.height() - window_geo.height()) // 2
            self.mod_matrix_window.move(x, y)
            self.mod_matrix_window.raise_()
            self.mod_matrix_window.activateWindow()
            logger.info("Mod matrix window opened", component="MOD")

    def _open_crossmod_matrix(self):
        """Toggle the crossmod routing matrix window (Cmd+X)."""
        # Create OSC bridge on first use (needs osc.client)
        if self.crossmod_osc is None and self.osc_connected:
            self.crossmod_osc = CrossmodOSCBridge(self.crossmod_state, self.osc.client)

        if self.crossmod_window is None:
            self.crossmod_window = CrossmodMatrixWindow(self.crossmod_state, parent=self)

        # Toggle visibility
        if self.crossmod_window.isVisible():
            self.crossmod_window.hide()
            logger.info("Crossmod matrix window closed", component="CROSSMOD")
        else:
            self.crossmod_window.show()
            # Center on main window
            main_geo = self.geometry()
            window_geo = self.crossmod_window.geometry()
            x = main_geo.x() + (main_geo.width() - window_geo.width()) // 2
            y = main_geo.y() + (main_geo.height() - window_geo.height()) // 2
            self.crossmod_window.move(x, y)
            self.crossmod_window.raise_()
            self.crossmod_window.activateWindow()
            logger.info("Crossmod matrix window opened", component="CROSSMOD")

    def _open_fx_window(self):
        """Toggle the FX controls window (Cmd+F)."""
        if self.fx_window is None:
            self.fx_window = FXWindow(self.osc if self.osc_connected else None, parent=self)
        
        # Toggle visibility
        if self.fx_window.isVisible():
            self.fx_window.hide()
            logger.info("FX window closed", component="FX")
        else:
            self.fx_window.show()
            self.fx_window.raise_()
            self.fx_window.activateWindow()
            logger.info("FX window opened", component="FX")

    def _clear_all_mod_routes(self):
        """Clear all modulation routes."""
        self.mod_routing.clear()
        logger.info("Cleared all mod routes", component="MOD")

    def _get_target_slider_value(self, slot_id: int, param: str) -> float:
        """Get normalized 0-1 value of a generator parameter slider.
        
        Used by mod popup to calculate depth limits.
        """
        slot = self.generator_grid.get_slot(slot_id)
        if slot:
            slider = self._get_slot_slider(slot, param)
            if slider:
                return slider.value() / 1000.0
        return 0.5  # Default to center if not found
    
    def _on_mod_slot_type_changed_for_matrix(self, slot_id: int, gen_name: str):
        """Update matrix window when mod slot type changes."""
        if self.mod_matrix_window:
            self.mod_matrix_window.update_mod_slot_type(slot_id, gen_name)
        
    def on_generator_volume_changed(self, gen_id, volume):
        """Handle generator volume change from mixer."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_volume'], [gen_id, volume])
        logger.debug(f"Gen {gen_id} volume: {volume:.2f}", component="OSC")
        self._mark_dirty()

    def on_generator_muted(self, gen_id, muted):
        """Handle generator mute from mixer."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_mute'], [gen_id, 1 if muted else 0])
        logger.debug(f"Gen {gen_id} mute: {muted}", component="OSC")
        
    def on_generator_solo(self, gen_id, solo):
        """Handle generator solo from mixer."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_strip_solo'], [gen_id, 1 if solo else 0])
        logger.debug(f"Gen {gen_id} solo: {solo}", component="OSC")
    
    def on_generator_gain_changed(self, gen_id, gain_db):
        """Handle generator gain stage change from mixer."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_gain'], [gen_id, gain_db])
        logger.debug(f"Gen {gen_id} gain: +{gain_db}dB", component="OSC")
    
    def on_generator_pan_changed(self, gen_id, pan):
        """Handle generator pan change from mixer."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['gen_pan'], [gen_id, pan])
        logger.debug(f"Gen {gen_id} pan: {pan:.2f}", component="OSC")
        self._mark_dirty()

    def on_generator_eq_changed(self, gen_id, band, value):
        """Handle generator EQ change from mixer. band: 'lo'/'mid'/'hi', value: 0-2 linear."""
        if self.osc_connected:
            osc_path = f"{OSC_PATHS['gen_strip_eq_base']}/{band}"
            self.osc.client.send_message(osc_path, [gen_id, value])
        logger.debug(f"Gen {gen_id} EQ {band}: {value:.2f}", component="OSC")
        self._mark_dirty()

    def on_generator_echo_send(self, gen_id, value):
        """Handle generator echo send change from mixer. value: 0-1."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['strip_echo_send'], [gen_id, value])
        logger.debug(f"Gen {gen_id} echo send: {value:.2f}", component="OSC")
    
    def on_generator_verb_send(self, gen_id, value):
        """Handle generator verb send change from mixer. value: 0-1."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['strip_verb_send'], [gen_id, value])
        logger.debug(f"Gen {gen_id} verb send: {value:.2f}", component="OSC")
    
    def _sync_strip_state_to_sc(self, slot_id):
        """Re-sync mixer strip state to SC after generator change.
        
        This ensures pan/EQ/mute/solo/gain persist when switching generators,
        since SC creates a fresh synth with default values.
        """
        if not self.osc_connected:
            return
        
        state = self.mixer_panel.get_channel_strip_state(slot_id)
        if not state:
            return
        
        # Re-send all strip parameters to SC
        self.osc.client.send_message(OSC_PATHS['gen_pan'], [slot_id, state['pan']])
        self.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1 if state['muted'] else 0])
        self.osc.client.send_message(OSC_PATHS['gen_strip_solo'], [slot_id, 1 if state['soloed'] else 0])
        self.osc.client.send_message(OSC_PATHS['gen_gain'], [slot_id, state['gain_db']])
        
        # EQ bands
        for band in ['lo', 'mid', 'hi']:
            osc_path = f"{OSC_PATHS['gen_strip_eq_base']}/{band}"
            self.osc.client.send_message(osc_path, [slot_id, state[f'eq_{band}']])
        
        logger.debug(f"Gen {slot_id} strip state synced (pan={state['pan']:.2f})", component="OSC")
    
    def _sync_generator_slot_state_to_sc(self, slot_id):
        """Re-sync generator slot control state to SC after type change.
        
        This ensures mute/env/rate/midi/filter persist when switching generators,
        since SC creates a fresh synth with default values.
        
        Note: The slot's mute button state is separate from mixer strip mute.
        If slot is muted, we send mute=1 regardless of mixer strip state.
        """
        if not self.osc_connected:
            return
        
        slot = self.generator_grid.get_slot(slot_id)
        if not slot:
            return
        
        # Generator slot mute (overrides strip mute if set)
        if slot.muted:
            self.osc.client.send_message(OSC_PATHS['gen_mute'], [slot_id, 1])
        
        # Envelope source (0=OFF, 1=CLK, 2=MIDI)
        self.osc.client.send_message(OSC_PATHS['gen_env_source'], [slot_id, slot.env_source])
        
        # Clock rate (only relevant when env_source=CLK)
        if slot.env_source == 1 and hasattr(slot, 'rate_btn'):
            rate = slot.rate_btn.get_value()
            rate_index = CLOCK_RATE_INDEX.get(rate, 3)
            self.osc.client.send_message(OSC_PATHS['gen_clock_rate'], [slot_id, rate_index])
        
        # MIDI channel (only relevant when env_source=MIDI)
        if slot.env_source == 2:
            self.osc.client.send_message(OSC_PATHS['gen_midi_channel'], [slot_id, slot.midi_channel])
        
        # Filter type
        if hasattr(slot, 'filter_btn'):
            filter_type = slot.filter_btn.get_value()
            self.osc.client.send_message(OSC_PATHS['gen_filter_type'], [slot_id, FILTER_TYPE_INDEX[filter_type]])
        
        logger.debug(f"Gen {slot_id} slot state synced (mute={slot.muted}, env={slot.env_source})", component="OSC")
        
        
    def on_master_volume_from_master(self, volume):
        """Handle master volume change from master section."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_volume'], [volume])
        logger.info(f"Master volume: {volume:.2f}", component="OSC")
        self._mark_dirty()

    def on_meter_mode_changed(self, mode):
        """Handle meter mode toggle (PRE=0, POST=1)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_meter_toggle'], [mode])
        mode_name = "POST" if mode == 1 else "PRE"
        logger.info(f"Master meter: {mode_name}", component="OSC")
    
    def on_limiter_ceiling_changed(self, db):
        """Handle limiter ceiling change (dB value)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_limiter_ceiling'], [db])
        logger.debug(f"Limiter ceiling: {db:.1f}dB", component="OSC")
    
    def on_limiter_bypass_changed(self, bypass):
        """Handle limiter bypass toggle (0=on, 1=bypassed)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_limiter_bypass'], [bypass])
        state = "BYPASSED" if bypass == 1 else "ON"
        logger.info(f"Limiter: {state}", component="OSC")
    
    # === EQ Handlers ===
    
    def on_eq_lo_changed(self, db):
        """Handle EQ LO change (dB value)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_lo'], [db])
    
    def on_eq_mid_changed(self, db):
        """Handle EQ MID change (dB value)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_mid'], [db])
    
    def on_eq_hi_changed(self, db):
        """Handle EQ HI change (dB value)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_hi'], [db])
    
    def on_eq_lo_kill_changed(self, kill):
        """Handle EQ LO kill toggle."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_lo_kill'], [kill])
        state = "KILLED" if kill == 1 else "OFF"
        logger.info(f"EQ LO Kill: {state}", component="OSC")
    
    def on_eq_mid_kill_changed(self, kill):
        """Handle EQ MID kill toggle."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_mid_kill'], [kill])
        state = "KILLED" if kill == 1 else "OFF"
        logger.info(f"EQ MID Kill: {state}", component="OSC")
    
    def on_eq_hi_kill_changed(self, kill):
        """Handle EQ HI kill toggle."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_hi_kill'], [kill])
        state = "KILLED" if kill == 1 else "OFF"
        logger.info(f"EQ HI Kill: {state}", component="OSC")
    
    def on_eq_locut_changed(self, enabled):
        """Handle EQ lo cut toggle (0=off, 1=on)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_locut'], [enabled])
        state = "ON" if enabled == 1 else "OFF"
        logger.info(f"EQ Lo Cut: {state}", component="OSC")
    
    def on_eq_bypass_changed(self, bypass):
        """Handle EQ bypass toggle (0=on, 1=bypassed)."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_eq_bypass'], [bypass])
        state = "BYPASSED" if bypass == 1 else "ON"
        logger.info(f"EQ: {state}", component="OSC")
    
    # === Compressor Handlers ===
    
    def on_comp_threshold_changed(self, db):
        """Handle compressor threshold change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_comp_threshold'], [db])
    
    def on_comp_ratio_changed(self, idx):
        """Handle compressor ratio change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_comp_ratio'], [idx])
    
    def on_comp_attack_changed(self, idx):
        """Handle compressor attack change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_comp_attack'], [idx])
    
    def on_comp_release_changed(self, idx):
        """Handle compressor release change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_comp_release'], [idx])
    
    def on_comp_makeup_changed(self, db):
        """Handle compressor makeup change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_comp_makeup'], [db])
    
    def on_comp_sc_hpf_changed(self, idx):
        """Handle compressor SC HPF change."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_comp_sc_hpf'], [idx])
    
    def on_comp_bypass_changed(self, bypass):
        """Handle compressor bypass toggle."""
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['master_comp_bypass'], [bypass])
        state = "BYPASSED" if bypass == 1 else "ON"
        logger.info(f"Compressor: {state}", component="OSC")
    
    def on_comp_gr_received(self, gr_db):
        """Handle compressor GR meter update."""
        self.master_section.set_comp_gr(gr_db)
    
    def on_audio_device_changed(self, device_name):
        """Handle audio device selection from dropdown - disabled for now."""
        # Device switching disabled - SC reboot is too fragile
        # Dropdown is display-only to show available devices
        pass
    
    def on_audio_devices_received(self, devices, current):
        """Handle audio device list from SC."""
        logger.info(f"Audio devices: {len(devices)} available, current: {current}", component="OSC")
        self.audio_selector.set_devices(devices, current)
    
    def on_audio_device_changing(self, device_name):
        """Handle notification that SC is changing audio device."""
        logger.info(f"Audio device changing to: {device_name}...", component="OSC")
        self.status_label.setText("Switching...")
        self.status_label.setStyleSheet(f"color: {COLORS['submenu_text']};")
    
    def on_audio_device_ready(self, device_name):
        """Handle notification that SC finished changing device."""
        logger.info(f"Audio device ready: {device_name}", component="OSC")
        self.status_label.setText("Connected")
        self.status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
        self.audio_selector.set_enabled(True)
        # Re-query to confirm
        self.osc.query_audio_devices()
        
    def on_levels_received(self, amp_l, amp_r, peak_l, peak_r):
        """Handle level meter data from SuperCollider."""
        self.master_section.set_levels(amp_l, amp_r, peak_l, peak_r)
    
    def on_channel_levels_received(self, slot_id, amp_l, amp_r):
        """Handle per-channel level meter data from SuperCollider."""
        self.mixer_panel.set_channel_levels(slot_id, amp_l, amp_r)
    
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

    def _midi_mode_btn_style(self, active):
        """Return style for MIDI mode button."""
        if active:
            return f"""
                QPushButton {{
                    background-color: #660066;
                    color: #ff00ff;
                    border: 1px solid #ff00ff;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: {FONT_SIZES['small']}px;
                    font-weight: bold;
                }}
                QPushButton:disabled {{
                    background-color: #220022;
                    color: #440044;
                    border-color: #330033;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: {FONT_SIZES['small']}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #330033;
                    color: #ff00ff;
                    border-color: #aa00aa;
                }}
                QPushButton:disabled {{
                    background-color: {COLORS['background']};
                    color: {COLORS['border']};
                    border-color: {COLORS['border']};
                }}
            """
    def _toggle_midi_mode(self):
        """Toggle all generators to/from MIDI mode."""
        if not self._midi_mode_active:
            # Activate: save states, set all to MIDI
            self._midi_mode_changing = True
            for i, slot in enumerate(self.generator_grid.slots.values()):
                self._midi_mode_saved_states[i] = slot.env_source
                if slot.env_source != 2:  # Not already MIDI
                    slot.env_btn.set_index(2)  # Update visual
                    slot.on_env_source_changed("MIDI")   # Trigger full state update
            self._midi_mode_changing = False
            self._midi_mode_active = True
            logger.info("MIDI mode activated", component="APP")
        else:
            # Deactivate: restore saved states
            self._restore_midi_mode_states()
        
        self.midi_mode_btn.setChecked(self._midi_mode_active)
        self.midi_mode_btn.setStyleSheet(self._midi_mode_btn_style(self._midi_mode_active))

    def _restore_midi_mode_states(self):
        """Restore saved env_source states."""
        from src.config import ENV_SOURCES
        self._midi_mode_changing = True
        for i, slot in enumerate(self.generator_grid.slots.values()):
            saved = self._midi_mode_saved_states[i]
            slot.env_btn.set_index(saved)  # Update visual
            slot.on_env_source_changed(ENV_SOURCES[saved])  # Trigger full state update
        self._midi_mode_changing = False
        self._midi_mode_active = False
        logger.info("MIDI mode deactivated", component="APP")

    def _deactivate_midi_mode(self):
        """Deactivate MIDI mode without restoring (user made manual change)."""
        self._midi_mode_active = False
        self.midi_mode_btn.setChecked(False)
        self.midi_mode_btn.setStyleSheet(self._midi_mode_btn_style(False))
        logger.info("MIDI mode cancelled (manual change)", component="APP")

    # === Preset Save/Load ===

    def _save_preset(self):
        """Save current state to preset file."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        from src.config import get_current_pack

        # Collect generator slot states
        slots = []
        for slot_id in range(1, 9):
            slot_widget = self.generator_grid.slots[slot_id]
            slots.append(SlotState.from_dict(slot_widget.get_state()))

        # Collect mixer channel states
        channels = []
        for ch_id in range(1, 9):
            ch_widget = self.mixer_panel.channels[ch_id]
            channels.append(ChannelState.from_dict(ch_widget.get_state()))

        mixer = MixerState(
            channels=channels,
            master_volume=self.master_section.get_volume(),
        )

        # Phase 2: BPM and master section
        bpm = self.bpm_display.get_bpm()
        master = MasterState.from_dict(self.master_section.get_state())
        
        # Phase 3: Mod sources
        mod_sources = ModSourcesState.from_dict(self.modulator_grid.get_state())
        
        # Phase 4: Mod routing
        mod_routing = self.mod_routing.to_dict()
        
        # Phase 5: FX state
        fx = self.fx_window.get_state() if self.fx_window else FXState()

        # Phase 6: MIDI mappings
        midi_mappings = self.cc_mapping_manager.to_dict()
        
        # Get current pack
        current_pack = get_current_pack()

        state = PresetState(
            pack=current_pack,
            slots=slots,
            mixer=mixer,
            bpm=bpm,
            master=master,
            mod_sources=mod_sources,
            mod_routing=mod_routing,
            fx=fx,
            midi_mappings=midi_mappings,
        )

        # Get filename from user
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Preset",
            str(self.preset_manager.presets_dir),
            "Preset Files (*.json)",
        )

        if filepath:
            try:
                # Ensure .json extension
                if not filepath.endswith('.json'):
                    filepath += '.json'
                name = Path(filepath).stem
                state.name = name
                saved_path = self.preset_manager.save(state, name)
                self.preset_name.setText(name)
                logger.info(f"Preset saved: {saved_path}", component="PRESET")
                self._clear_dirty(name)
            except Exception as e:
                logger.error(f"Failed to save preset: {e}", component="PRESET")
                QMessageBox.warning(self, "Error", f"Failed to save preset:\n{e}")

    def _load_preset(self):
        """Load preset from file."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Preset",
            str(self.preset_manager.presets_dir),
            "Preset Files (*.json)",
        )

        if filepath:
            try:
                state = self.preset_manager.load(Path(filepath))
                self._apply_preset(state)
                # Safety: reset master to 0 so presets don't blast audio
                self.master_section.set_volume(0.0)
                self.preset_name.setText(state.name)
                logger.info(f"Preset loaded: {state.name}", component="PRESET")
                self._clear_dirty(state.name)
            except Exception as e:
                logger.error(f"Failed to load preset: {e}", component="PRESET")
                QMessageBox.warning(self, "Error", f"Failed to load preset:\n{e}")

    def _apply_preset(self, state: PresetState):
        """Apply preset state to all components."""
        # Handle pack switching FIRST (before loading slots)
        if state.pack is not None:
            # Preset specifies a pack - switch to it
            if not self.pack_selector.set_pack(state.pack):
                logger.warning(f"Pack '{state.pack}' not found, using Core", component="PRESET")
        else:
            # Preset is for Core (or old preset without pack field)
            # Don't auto-switch to Core - leave current pack as is for backward compat
            pass
        
        # Apply to generator slots
        for i, slot_state in enumerate(state.slots):
            slot_id = i + 1
            if slot_id <= 8:
                slot_widget = self.generator_grid.slots[slot_id]
                slot_widget.set_state(slot_state.to_dict())

        # Apply to mixer channels
        for i, channel_state in enumerate(state.mixer.channels):
            ch_id = i + 1
            if ch_id in self.mixer_panel.channels:
                self.mixer_panel.channels[ch_id].set_state(channel_state.to_dict())

        # Apply master volume (legacy field)
        self.master_section.set_volume(state.mixer.master_volume)
        
        # Phase 2: BPM (only if preset had bpm saved)
        if state.bpm != 120:  # Non-default means it was explicitly saved
            self.bpm_display.set_bpm(state.bpm)
            self.on_bpm_changed(state.bpm)  # Send to SC
        
        # Phase 2: Master section (only if preset version >= 2)
        if state.version >= 2 and hasattr(state, 'master'):
            self.master_section.set_state(state.master.to_dict())
        
        # Phase 3: Mod sources
        if state.version >= 2:
            self.modulator_grid.set_state(state.mod_sources.to_dict())

        # Phase 4: Mod routing (only if has connections)
        if state.mod_routing.get("connections"):
            self.mod_routing.from_dict(state.mod_routing)
            # Update mod matrix window if open
            if self.mod_matrix_window:
                self.mod_matrix_window.sync_from_state()
        
        # Phase 5: FX state
        if self.fx_window:
            self.fx_window.set_state(state.fx)

        # Phase 6: MIDI mappings (if preset contains them)
        if state.midi_mappings:
            # Clear existing visual badges
            for controls in self.cc_mapping_manager.get_all_mappings().values():
                for control in controls:
                    if hasattr(control, 'set_midi_mapped'):
                        control.set_midi_mapped(False)
            # Load new mappings
            self.cc_mapping_manager.from_dict(state.midi_mappings, self._find_control_by_name)
            self._update_midi_status()
            self._show_toast("MIDI mappings loaded from preset")

    def _init_preset(self):
        """Reset to default empty state (Cmd+N / Ctrl+N)."""
        # Create fresh default state
        state = PresetState()

        # Apply to all components
        self._apply_preset(state)

        # Clear mod routing
        self.mod_routing.clear()

        # Update mod matrix window if open
        if self.mod_matrix_window:
            self.mod_matrix_window.sync_from_state()

        # Reset FX to defaults
        if self.fx_window:
            self.fx_window.set_state(FXState())

        # Reset pack selector to Core (empty string = Core)
        self.pack_selector.set_pack("")

        # Update preset name display
        self.preset_name.setText("Init")

        # Clear dirty flag
        self._clear_dirty("Init")

        logger.info("Preset initialized to defaults", component="PRESET")

    # Keyboard Mode

    def eventFilter(self, obj, event):
        """Forward key events to keyboard overlay when visible."""
        # Cancel MIDI Learn on Escape
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                if hasattr(self, 'cc_learn_manager') and self.cc_learn_manager.is_learning():
                    self.cc_learn_manager.cancel_learn()
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
        """Toggle the keyboard overlay for QWERTY-to-MIDI input."""
        # If overlay exists and is visible, just toggle it off
        if self._keyboard_overlay is not None and self._keyboard_overlay.isVisible():
            self._keyboard_overlay._dismiss()
            return
        
        focus_widget = QApplication.focusWidget()
        if focus_widget is not None:
            from PyQt5.QtWidgets import QLineEdit, QTextEdit, QSpinBox
            if isinstance(focus_widget, (QLineEdit, QTextEdit, QSpinBox)):
                return
        
        # Create overlay on first use
        if self._keyboard_overlay is None:
            self._keyboard_overlay = KeyboardOverlay(
                parent=self,
                send_note_on_fn=self._send_midi_note_on,
                send_note_off_fn=self._send_midi_note_off,
                send_all_notes_off_fn=self._send_all_notes_off,
                get_focused_slot_fn=self._get_focused_slot,
                is_slot_midi_mode_fn=self._is_slot_midi_mode,
            )
        
        # Position at bottom-center of main window
        overlay_width = self._keyboard_overlay.width()
        x = self.x() + (self.width() - overlay_width) // 2
        y = self.y() + self.height() - self._keyboard_overlay.height() - 24
        self._keyboard_overlay.move(x, y)
        self._keyboard_overlay.show()
        self._keyboard_overlay.raise_()
        self._keyboard_overlay.activateWindow()

    def _send_midi_note_on(self, slot: int, note: int, velocity: int):
        """Send MIDI note-on via OSC. Slot is 0-indexed."""
        if self.osc is not None and self.osc.client is not None:
            self.osc.client.send_message(f"/noise/slot/{slot}/midi/note_on", [note, velocity])

    def _send_midi_note_off(self, slot: int, note: int):
        """Send MIDI note-off via OSC. Slot is 0-indexed."""
        if self.osc is not None and self.osc.client is not None:
            self.osc.client.send_message(f"/noise/slot/{slot}/midi/note_off", [note])

    def _send_all_notes_off(self, slot: int):
        if self.osc is not None and self.osc.client is not None:
            self.osc.client.send_message(f"/noise/slot/{slot}/midi/all_notes_off", [])

    def _get_focused_slot(self) -> int:
        """Return currently focused slot (1-indexed for UI)."""
        # TODO: Track actual focused slot when we add slot focus tracking
        return 1

    def _is_slot_midi_mode(self, slot_id: int) -> bool:
        """Check if slot is in MIDI envelope mode. Slot is 1-indexed (UI)."""
        if slot_id < 1 or slot_id > 8:
            return False
        slot = self.generator_grid.slots[slot_id]
        return slot.env_source == 2 or slot.env_source == "MIDI"

    def _set_header_buttons_enabled(self, enabled: bool) -> None:
        """Enable/disable header buttons that require SC connection.

        On startup, only CONNECT, CONSOLE, RESTART are enabled.
        After SC connection confirmed, all buttons become enabled.
        """
        # Buttons/widgets that require SC connection
        sc_dependent = [
            self.save_btn,  # Preset save
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
        # Stop OSC bridge first to prevent signals on deleted objects
        if hasattr(self, 'osc') and self.osc:
            self.osc.shutdown()

        # Accept the close event
        event.accept()

    # ─────────────────────────────────────────────────────────────
    # MIDI CC Handling (Phase 2)
    # ─────────────────────────────────────────────────────────────

    def _on_midi_cc(self, channel, cc, value):
        """Handle MIDI CC from OSC bridge."""
        # If learning, handle immediately (don't buffer)
        if self.cc_learn_manager.is_learning():
            self.cc_learn_manager.on_cc_received(channel, cc, value)
        else:
            # Buffer all CCs - process in timer
            self._pending_cc[(channel, cc)] = value

    def _process_pending_cc(self):
        """Process buffered CC updates (~60Hz)."""
        if not self._pending_cc:
            return

        pending = dict(self._pending_cc)
        self._pending_cc.clear()

        for (channel, cc), value in pending.items():
            controls = self.cc_mapping_manager.get_controls(channel, cc)
            for control in controls:
                self._apply_cc_to_control(control, channel, cc, value)

    def _apply_cc_to_control(self, control, channel, cc, value):
        """Apply CC value to a control with pickup mode."""
        # Handle buttons
        if hasattr(control, 'handle_cc'):
            should_activate = control.handle_cc(value)
            if should_activate:
                if hasattr(control, 'cycle_forward'):
                    control.cycle_forward()
                else:
                    control.click()
            return

        # Handle sliders/knobs
        if not hasattr(control, 'minimum') or not hasattr(control, 'maximum'):
            return

        min_val = control.minimum()
        max_val = control.maximum()
        param_range = max_val - min_val

        # Scale CC 0-127 to control range
        cc_scaled = min_val + (value / 127.0) * param_range

        # Pickup threshold: 3 CC steps for easier catching
        eps = (param_range / 127.0) * 3

        # Get current caught state
        is_caught = self.cc_mapping_manager.is_caught(channel, cc, control)

        if not is_caught:
            # Check if CC catches current value
            current_val = control.value()
            if abs(cc_scaled - current_val) <= eps:
                # Caught! Start controlling
                self.cc_mapping_manager.set_caught(channel, cc, control, True)
                control.setValue(int(cc_scaled))
                # Clear ghost
                if hasattr(control, 'set_cc_ghost'):
                    control.set_cc_ghost(None)
            else:
                # Not caught - show ghost indicator
                if hasattr(control, 'set_cc_ghost'):
                    ghost_norm = value / 127.0
                    control.set_cc_ghost(ghost_norm)
        else:
            # Already caught - apply value directly
            control.setValue(int(cc_scaled))

    def _on_learn_started(self, control):
        """Visual feedback when MIDI Learn starts."""
        if hasattr(control, 'set_midi_armed'):
            control.set_midi_armed(True)
        logger.info(f"MIDI Learn armed: {control.objectName()}", component="MIDI")

    def _on_learn_completed(self, channel, cc, control):
        """Visual feedback when MIDI Learn completes."""
        if hasattr(control, 'set_midi_armed'):
            control.set_midi_armed(False)
        if hasattr(control, 'set_midi_mapped'):
            control.set_midi_mapped(True)

        # Check for duplicate mappings
        existing = self.cc_mapping_manager.get_controls(channel, cc)
        other_controls = [c for c in existing if c != control]
        if other_controls:
            names = [c.objectName() for c in other_controls if c.objectName()]
            if names:
                self._show_toast(f"CC{cc} also mapped to: {', '.join(names)}")

        logger.info(f"MIDI mapped: Ch{channel} CC{cc} -> {control.objectName()}", component="MIDI")
        self._update_midi_status()

    def _on_learn_cancelled(self, control):
        """Visual feedback when MIDI Learn cancelled."""
        if control and hasattr(control, 'set_midi_armed'):
            control.set_midi_armed(False)
        logger.info("MIDI Learn cancelled", component="MIDI")

    def _find_control_by_name(self, name):
        """Find a control widget by objectName."""
        return self.findChild(QWidget, name)

    def save_midi_mappings(self):
        """Save MIDI mappings to file."""
        from PyQt5.QtWidgets import QFileDialog
        import json
        import os

        data = self.cc_mapping_manager.to_dict()
        if not data:
            logger.info("No MIDI mappings to save", component="MIDI")
            return

        # Default to midi_mappings folder
        midi_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'midi_mappings')
        os.makedirs(midi_dir, exist_ok=True)

        path, _ = QFileDialog.getSaveFileName(
            self, "Save MIDI Mappings", midi_dir, "JSON Files (*.json)"
        )
        if path:
            if not path.endswith('.json'):
                path += '.json'
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved MIDI mappings to {path}", component="MIDI")

    def load_midi_mappings(self):
        """Load MIDI mappings from file."""
        from PyQt5.QtWidgets import QFileDialog
        import json
        import os

        # Default to midi_mappings folder
        midi_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'midi_mappings')
        os.makedirs(midi_dir, exist_ok=True)

        path, _ = QFileDialog.getOpenFileName(
            self, "Load MIDI Mappings", midi_dir, "JSON Files (*.json)"
        )
        if path:
            with open(path, 'r') as f:
                data = json.load(f)
            self.cc_mapping_manager.from_dict(data, self._find_control_by_name)
            logger.info(f"Loaded MIDI mappings from {path}", component="MIDI")
        self._update_midi_status()

    def clear_all_midi_mappings(self):
        """Clear all MIDI mappings."""
        # Clear visual badges first
        for controls in self.cc_mapping_manager.get_all_mappings().values():
            for control in controls:
                if hasattr(control, 'set_midi_mapped'):
                    control.set_midi_mapped(False)
        self.cc_mapping_manager.clear_all()
        logger.info("Cleared all MIDI mappings", component="MIDI")
        self._update_midi_status()

    def _setup_midi_menu(self):
        """Create MIDI menu in menu bar."""
        menu_bar = self.menuBar()
        midi_menu = menu_bar.addMenu("MIDI")

        midi_menu.addAction("Save Mappings...", self.save_midi_mappings)
        midi_menu.addAction("Load Mappings...", self.load_midi_mappings)
        midi_menu.addSeparator()
        midi_menu.addAction("Clear All Mappings", self.clear_all_midi_mappings)

    def _update_midi_status(self):
        """Update MIDI status label with mapping count."""
        count = len(self.cc_mapping_manager.to_dict())
        if count == 0:
            self.midi_status_label.setText("MIDI: Ready")
            self.midi_status_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        else:
            self.midi_status_label.setText(f"MIDI: {count} mapped")
            self.midi_status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")

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