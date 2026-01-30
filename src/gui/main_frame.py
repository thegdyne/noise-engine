"""
Main Frame - Combines all components
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QShortcut, QApplication,
                             QSizePolicy)
from PyQt5.QtCore import Qt, QEvent, QTimer, QSettings
from PyQt5.QtGui import QFont, QKeySequence, QColor

from src.gui.generator_grid import GeneratorGrid
from src.gui.mixer_panel import MixerPanel
# Phase 2: MasterChain replaces MasterSection (adds Heat + Filter inserts)
from src.gui.master_chain import MasterChain
# from src.gui.master_section import MasterSection  # Now embedded in MasterChain
# from src.gui.inline_fx_strip import InlineFXStrip  # Deprecated
from src.gui.fx_grid import FXGrid
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
from src.gui.theme import COLORS, button_style, FONT_FAMILY, MONO_FONT, FONT_SIZES
from src.audio.osc_bridge import OSCBridge
from src.config import (
    CLOCK_RATE_INDEX, FILTER_TYPE_INDEX, GENERATORS, GENERATOR_CYCLE,
    BPM_DEFAULT, OSC_PATHS, unmap_value, get_param_config
)
from src.utils.logger import logger
from src.presets import PresetState, SlotState, MixerState, ChannelState, MasterState, ModSourcesState, FXState, FXSlotsState
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
from src.boids.boid_pulse_manager import BoidPulseManager
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
        state = settings.value("window/state")
        if geometry:
            self.restoreGeometry(geometry)
            if state is not None:
                self.setWindowState(Qt.WindowState(int(state)))
        else:
            # First run defaults
            self.setGeometry(100, 50, 1400, 800)

    def _save_window_geometry(self):
        """Save window geometry and state to settings."""
        settings = QSettings("NoiseEngine", "NoiseEngine")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", int(self.windowState()))
        settings.sync()  # Force write to disk

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
        content_container.setObjectName("contentContainer")
        content_container.setAutoFillBackground(True)
        content_outer = QHBoxLayout(content_container)
        content_outer.setContentsMargins(0, 0, 0, 0)
        content_outer.setSpacing(0)
        
        # Main content (left side)
        content_widget = QWidget()
        content_widget.setObjectName("contentArea")
        content_widget.setAutoFillBackground(True)
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Left column - MODULATOR GRID + BOID PANEL
        left_column = QWidget()
        left_column.setObjectName("leftColumn")
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
        
        # Right column - MIXER + BOIDS stacked (fixed width)
        right_column = QWidget()
        right_column.setObjectName("rightColumn")
        right_column.setFixedWidth(400)  # Fixed width for 8 channel strips
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        # Mixer panel (top)
        self.mixer_panel = MixerPanel(num_generators=8)
        self.mixer_panel.generator_volume_changed.connect(self.mixer.on_generator_volume_changed)
        self.mixer_panel.generator_muted.connect(self.mixer.on_generator_muted)
        self.mixer_panel.generator_solo.connect(self.mixer.on_generator_solo)
        self.mixer_panel.generator_gain_changed.connect(self.mixer.on_generator_gain_changed)
        self.mixer_panel.generator_pan_changed.connect(self.mixer.on_generator_pan_changed)
        self.mixer_panel.generator_eq_changed.connect(self.mixer.on_generator_eq_changed)
        self.mixer_panel.generator_fx1_send_changed.connect(self.mixer.on_generator_fx1_send)
        self.mixer_panel.generator_fx2_send_changed.connect(self.mixer.on_generator_fx2_send)
        self.mixer_panel.generator_fx3_send_changed.connect(self.mixer.on_generator_fx3_send)
        self.mixer_panel.generator_fx4_send_changed.connect(self.mixer.on_generator_fx4_send)
        right_layout.addWidget(self.mixer_panel, stretch=1)

        # Boid panel (bottom) - equal stretch for balanced layout
        self.boid_panel = BoidPanel()
        self._connect_boid_signals()
        right_layout.addWidget(self.boid_panel, stretch=1)

        content_layout.addWidget(right_column, stretch=1)
        
        content_outer.addWidget(content_widget, stretch=1)
        
        # Console panel (right edge overlay)
        self.console_panel = ConsolePanel()
        content_outer.addWidget(self.console_panel)
        
        main_layout.addWidget(content_container, stretch=1)
        
        # Bottom section - FX Chain + Master side by side
        bottom_container = QWidget()
        bottom_container.setObjectName("bottomSection")
        bottom_container.setAutoFillBackground(True)
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(5, 5, 5, 5)
        bottom_layout.setSpacing(10)
        
        # FX Grid (4 send slots) - align left
        self.fx_grid = FXGrid()
        bottom_layout.addWidget(self.fx_grid)

        # Spacer pushes master chain to the right
        bottom_layout.addStretch(1)

        # Master chain (right side) - Heat → Filter → EQ → Comp → Limiter → Output
        self.master_section = MasterChain()
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
        bottom_layout.addWidget(self.master_section)
        
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
        self._keyboard_shortcut.activated.connect(lambda: print("CMD+K fired!") or self.keyboard._toggle_keyboard_mode())

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
        """Create top bar with grid cell layout (HF-12)."""
        from src.gui.audio_device_selector import AudioDeviceSelector

        # --- Skin values ---
        bg_base = '#141414'
        bg_mid = '#1a1a1a'
        bg_highlight = '#2e2e2e'
        border_dark = '#2a2a2a'
        border_mid = '#3a3a3a'
        text_dim = '#606060'
        text_mid = '#909090'
        text_bright = '#d0d0d0'
        text_white = '#f0f0f0'
        accent_green = '#00ff66'
        accent_green_dim = '#00aa44'
        accent_cyan = '#00ccff'
        accent_orange = '#ff8800'
        accent_red = '#ff4444'
        accent_gold = '#ccaa44'
        enabled_bg = '#0a2a15'
        warning_bg = '#2a0a0a'
        submenu_bg = '#251a0a'

        # --- Helper: cell label style ---
        label_ss = f"color: {text_dim}; font-size: 9px; font-weight: bold; letter-spacing: 1px; background: transparent; border: none;"

        # --- Helper: make a header cell ---
        def _cell(contents, padding=(12, 4, 12, 4), border_right=True, min_width=None):
            """Wrap widget(s) in a styled QFrame cell."""
            cell = QFrame()
            cell.setObjectName("header_cell")
            br = f"border-right: 1px solid {border_dark};" if border_right else ""
            cell.setStyleSheet(f"""
                QFrame#header_cell {{
                    background-color: {bg_base};
                    {br}
                }}
                QLabel {{ background: transparent; border: none; }}
            """)
            lay = QVBoxLayout(cell)
            lay.setContentsMargins(*padding)
            lay.setSpacing(1)
            lay.setAlignment(Qt.AlignCenter)
            if isinstance(contents, (list, tuple)):
                for w in contents:
                    lay.addWidget(w)
            else:
                lay.addWidget(contents)
            if min_width:
                cell.setMinimumWidth(min_width)
            return cell

        def _label(text):
            """9px uppercase dim label."""
            lbl = QLabel(text.upper())
            lbl.setStyleSheet(label_ss)
            lbl.setFont(QFont(MONO_FONT, 9))
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        def _divider():
            """2px vertical divider between logical groups."""
            d = QFrame()
            d.setFixedWidth(2)
            d.setStyleSheet(f"background-color: {border_mid};")
            return d

        # === Outer bar ===
        bar = QFrame()
        bar.setObjectName("header")
        bar.setFixedHeight(60)
        bar.setStyleSheet(f"""
            QFrame#header {{
                background-color: {bg_mid};
                border-radius: 6px;
                border: 1px solid {border_dark};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 1. Logo cell ──
        title = QLabel("NOISE ENGINE")
        title.setObjectName("header_logo")
        title.setFont(QFont(MONO_FONT, 14, QFont.Bold))
        title.setStyleSheet(f"color: {text_white}; letter-spacing: 2px; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        logo_cell = QFrame()
        logo_cell.setObjectName("header_cell_logo")
        logo_cell.setStyleSheet(f"""
            QFrame#header_cell_logo {{
                background-color: {bg_base};
                border-right: 2px solid {accent_gold};
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        logo_lay = QVBoxLayout(logo_cell)
        logo_lay.setContentsMargins(16, 4, 16, 4)
        logo_lay.setAlignment(Qt.AlignCenter)
        logo_lay.addWidget(title)
        layout.addWidget(logo_cell)

        # ── 2. BPM cell ──
        self.bpm_display = BPMDisplay(initial_bpm=BPM_DEFAULT)
        self.bpm_display.setObjectName("header_bpm")
        self.bpm_display.bpm_changed.connect(self.on_bpm_changed)
        layout.addWidget(_cell([_label("BPM"), self.bpm_display], padding=(10, 2, 10, 2)))

        # ── divider ──
        layout.addWidget(_divider())

        # ── 3. Preset cell ──
        preset_label = QLabel("Preset:")
        preset_label.setObjectName("header_preset_label")
        preset_label.setStyleSheet(label_ss)
        preset_label.setFont(QFont(MONO_FONT, 9))
        preset_label.setAlignment(Qt.AlignCenter)
        self.preset_name = QLabel("Init")
        self.preset_name.setObjectName("header_preset_name")
        self.preset_name.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        self.preset_name.setStyleSheet(f"color: {text_bright}; background: transparent; border: none;")
        self.preset_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(_cell([preset_label, self.preset_name], padding=(10, 2, 10, 2)))

        # ── 4. Save / As / Load cells ──
        btn_ss_submenu = f"""
            QPushButton {{
                background-color: {submenu_bg};
                color: {accent_orange};
                border: 1px solid {accent_orange};
                border-radius: 3px;
                font-family: {MONO_FONT};
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: #352a1a;
            }}
            QPushButton:disabled {{
                background-color: {bg_base};
                color: {text_dim};
                border-color: {border_dark};
            }}
        """
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("header_btn_save")
        self.save_btn.setToolTip("Save preset (Ctrl+S)")
        self.save_btn.setStyleSheet(btn_ss_submenu)
        self.save_btn.clicked.connect(self.preset._save_preset)
        layout.addWidget(_cell(self.save_btn, padding=(4, 8, 4, 8)))

        self.save_as_btn = QPushButton("As")
        self.save_as_btn.setObjectName("header_btn_save_as")
        self.save_as_btn.setToolTip("Save preset as new file (Ctrl+Shift+S)")
        self.save_as_btn.setStyleSheet(btn_ss_submenu)
        self.save_as_btn.clicked.connect(self.preset._save_preset_as)
        layout.addWidget(_cell(self.save_as_btn, padding=(4, 8, 4, 8)))

        self.load_btn = QPushButton("Load")
        self.load_btn.setObjectName("header_btn_load")
        self.load_btn.setToolTip("Load preset (Ctrl+O)")
        self.load_btn.setStyleSheet(btn_ss_submenu)
        self.load_btn.clicked.connect(self.preset._load_preset)
        layout.addWidget(_cell(self.load_btn, padding=(4, 8, 4, 8)))

        # ── divider ──
        layout.addWidget(_divider())

        # ── 5. Pack selector cell ──
        self.pack_selector = PackSelector()
        self.pack_selector.setObjectName("header_pack")
        self.pack_selector.pack_changed.connect(self.on_pack_changed)
        layout.addWidget(_cell([_label("PACK"), self.pack_selector], padding=(8, 2, 8, 2)))

        # ── 6. Audio device cell ──
        self.audio_selector = AudioDeviceSelector()
        self.audio_selector.setObjectName("header_audio")
        self.audio_selector.device_changed.connect(self.master.on_audio_device_changed)
        layout.addWidget(_cell([_label("AUDIO"), self.audio_selector], padding=(8, 2, 8, 2)))

        # ── 7. MIDI device cell ──
        self.midi_selector = MIDISelector()
        self.midi_selector.setObjectName("header_midi_device")
        self.midi_selector.device_changed.connect(self.generator.on_midi_device_changed)
        layout.addWidget(_cell([_label("MIDI"), self.midi_selector], padding=(8, 2, 8, 2)))

        # ── divider ──
        layout.addWidget(_divider())

        # ── 8. Matrix button ──
        self.matrix_btn = QPushButton("MATRIX")
        self.matrix_btn.setObjectName("header_btn_matrix")
        self.matrix_btn.setToolTip("Mod Matrix (Ctrl+M)")
        self.matrix_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {enabled_bg};
                color: {accent_green};
                border: 1px solid {accent_green_dim};
                border-radius: 3px;
                font-family: {MONO_FONT};
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: #0d3a1d;
            }}
            QPushButton:disabled {{
                background-color: {bg_base};
                color: {text_dim};
                border-color: {border_dark};
            }}
        """)
        self.matrix_btn.clicked.connect(self.modulation._open_mod_matrix)
        layout.addWidget(_cell(self.matrix_btn, padding=(4, 8, 4, 8)))

        # ── 9. Clear button ──
        self.clear_mod_btn = QPushButton("CLEAR")
        self.clear_mod_btn.setObjectName("header_btn_clear")
        self.clear_mod_btn.setToolTip("Clear all modulation routes")
        self.clear_mod_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {warning_bg};
                color: {accent_red};
                border: 1px solid #aa2222;
                border-radius: 3px;
                font-family: {MONO_FONT};
                font-size: {FONT_SIZES['small']}px;
                font-weight: bold;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: #3a1515;
            }}
            QPushButton:disabled {{
                background-color: {bg_base};
                color: {text_dim};
                border-color: {border_dark};
            }}
        """)
        self.clear_mod_btn.clicked.connect(self.modulation._clear_all_mod_routes)
        layout.addWidget(_cell(self.clear_mod_btn, padding=(4, 8, 4, 8)))

        # ── 10. MIDI mode toggle ──
        self.midi_mode_btn = QPushButton("MIDI")
        self.midi_mode_btn.setObjectName("header_btn_midi_mode")
        self.midi_mode_btn.setToolTip("Set all generators to MIDI mode (toggle)")
        self.midi_mode_btn.setCheckable(True)
        self.midi_mode_btn.setStyleSheet(self.midi_mode._midi_mode_btn_style(False))
        self.midi_mode_btn.clicked.connect(self.midi_mode._toggle_midi_mode)
        layout.addWidget(_cell(self.midi_mode_btn, padding=(4, 8, 4, 8)))

        # ── spacer ──
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setStyleSheet(f"background-color: {bg_mid};")
        layout.addWidget(spacer)

        # ── 11. SC status cell (LED + button) ──
        self.connect_btn = QPushButton("Connect SC")
        self.connect_btn.setObjectName("header_btn_connect")
        self.connect_btn.setStyleSheet(self.connection._connect_btn_style())
        self.connect_btn.clicked.connect(self.connection.toggle_connection)
        self.status_label = QLabel("Disconnected")
        self.status_label.setObjectName("header_status")
        self.status_label.setStyleSheet(f"color: {accent_red}; font-size: 10px; background: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(_cell([self.connect_btn, self.status_label], padding=(8, 4, 8, 4), min_width=130))

        # ── 12. MIDI status cell ──
        self.midi_status_label = QLabel("MIDI: Ready")
        self.midi_status_label.setObjectName("header_midi_status")
        self.midi_status_label.setStyleSheet(f"color: {text_dim}; font-size: 10px; background: transparent; border: none;")
        self.midi_status_label.setAlignment(Qt.AlignCenter)
        self.midi_status_label.setToolTip("MIDI CC control active")
        layout.addWidget(_cell(self.midi_status_label, padding=(8, 4, 8, 4)))

        # ── divider ──
        layout.addWidget(_divider())

        # ── 13. Console button ──
        self.console_btn = QPushButton(">_")
        self.console_btn.setObjectName("header_btn_console")
        self.console_btn.setToolTip("Toggle Console (Ctrl+`)")
        self.console_btn.setFixedSize(36, 36)
        self.console_btn.setCheckable(True)
        self.console_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_base};
                color: {text_mid};
                border: 1px solid {border_dark};
                border-radius: 3px;
                font-family: {MONO_FONT};
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: {text_bright};
                border-color: {border_mid};
            }}
            QPushButton:checked {{
                background-color: {enabled_bg};
                color: {accent_green};
                border-color: {accent_green_dim};
            }}
        """)
        self.console_btn.clicked.connect(self.toggle_console)
        layout.addWidget(_cell(self.console_btn, padding=(6, 6, 6, 6)))

        # ── 14. Restart button ──
        self.restart_btn = QPushButton("↻")
        self.restart_btn.setObjectName("header_btn_restart")
        self.restart_btn.setToolTip("Restart Noise Engine")
        self.restart_btn.setFixedSize(36, 36)
        self.restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_base};
                color: {text_mid};
                border: 1px solid {border_dark};
                border-radius: 3px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                color: {text_bright};
                border-color: {border_mid};
            }}
        """)
        self.restart_btn.clicked.connect(self.restart_app)
        layout.addWidget(_cell(self.restart_btn, padding=(6, 6, 6, 6), border_right=False))

        return bar
        
    def on_bpm_changed(self, bpm):
        """Handle BPM change."""
        self.master_bpm = bpm
        if self.osc_connected:
            self.osc.client.send_message(OSC_PATHS['clock_bpm'], [bpm])
        self._mark_dirty()

    def on_pack_changed(self, pack_id):
        """Load pack generators directly into slots 1-8."""
        if getattr(self, '_applying_pack', False):
            return
        self._applying_pack = True
        try:
            self._do_pack_changed(pack_id)
        finally:
            self._applying_pack = False

    def _do_pack_changed(self, pack_id):
        from src.config import get_generators_for_pack, get_all_pack_generators
        from src.presets.preset_schema import (
            PresetState, SlotState, MixerState, ChannelState,
            FXSlotsState, FXSlotState,
        )

        if pack_id == "__all__":
            # All packs — lock cycle to all pack generators, don't load into slots
            cycle_list = get_all_pack_generators()
            self._update_slot_cycles(cycle_list)
            return

        if pack_id:
            # Specific pack — get its generators
            generators = get_generators_for_pack(pack_id)

            # Lock cycle buttons to this pack's generators
            self._update_slot_cycles(generators)

            # Strip "Empty" for slot assignment
            gen_names = [g for g in generators if g != "Empty"]

            # Build slot states: map generators 1:1 to slots
            slots = []
            for i in range(8):
                if i < len(gen_names):
                    slots.append(SlotState(generator=gen_names[i]))
                else:
                    slots.append(SlotState())  # Empty slot

            # Ch1 at -1dB unmuted, channels 2-8 muted with faders at minimum
            channels = [ChannelState(volume=0.891, mute=False)]
            channels.extend(ChannelState(volume=0.0, mute=True) for _ in range(7))
            mixer = MixerState(channels=channels)

            # FX3 (Chorus) and FX4 (LoFi) bypassed by default
            fx_slots = FXSlotsState(slots=[
                FXSlotState(fx_type='Echo', p1=0.3, p2=0.3, p3=0.7, p4=0.1),
                FXSlotState(fx_type='Reverb', p1=0.75, p2=0.65, p3=0.7, p4=0.5),
                FXSlotState(fx_type='Chorus', bypassed=True),
                FXSlotState(fx_type='LoFi', bypassed=True),
            ])

            state = PresetState(pack=pack_id, slots=slots, mixer=mixer, fx_slots=fx_slots)
            self.preset._apply_preset(state)
            self.preset_name.setText("Init")
            logger.info(f"Loaded pack '{pack_id}': {len(gen_names)} generators into slots (all muted)", component="PACK")
        else:
            # Core — lock cycle to core generators, clear all slots
            core_generators = get_generators_for_pack(None)
            self._update_slot_cycles(core_generators)
            self.preset._apply_preset(PresetState())
            self.preset_name.setText("Init")

    def _update_slot_cycles(self, generator_list):
        """Update all slot cycle buttons to only show given generators."""
        for slot in self.generator_grid.slots.values():
            current = slot.type_btn.get_value()
            slot.type_btn.set_values(generator_list)
            # Preserve current selection if it exists in new list
            if current in generator_list:
                slot.type_btn.set_value(current)
            else:
                slot.type_btn.set_value(generator_list[0])

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

        # Boid pulse visualization (glow on targeted widgets)
        self._boid_pulse_manager = BoidPulseManager(self)
        # Defer build_registry until after window shown (widgets need to be in hierarchy)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._boid_pulse_manager.build_registry)
        self.boid.cells_updated.connect(self._boid_pulse_manager.on_cells_updated)

    def _on_boid_enabled_changed(self, enabled: bool):
        """Handle boid enable/disable from panel."""
        if getattr(self, '_boid_toggle_guard', False):
            return
        self._boid_toggle_guard = True
        try:
            if enabled:
                self.boid.start()
                # If start failed (e.g. no OSC), sync panel back to actual state
                if not self.boid._state.enabled:
                    self.boid_panel.set_enabled(False)
                    return
            else:
                self.boid.stop()
            self._mark_dirty()
        finally:
            self._boid_toggle_guard = False

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

