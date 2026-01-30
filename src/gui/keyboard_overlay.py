"""
Keyboard Mode Overlay - QWERTY keyboard as MIDI input (Per-Slot ARP v2.0).

CMD+K (macOS) / Ctrl+K (Win/Linux) toggles overlay.
Keys map to piano notes (Logic-style layout).
Z/X for octave shift. ESC dismisses.

v2.0: Overlay is a pure view — no engine ownership.
      ArpEngine is bound/unbound via set_arp_engine().
      Physical keys are overlay state, not engine state.
      Target selector is single-select (one slot at a time).
"""

from PyQt5.QtCore import Qt, QPoint, QEvent, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QFrame, QApplication
)
from PyQt5.QtGui import QFont
from typing import Optional, Callable, Set

from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from .widgets import CycleButton
from .arp_engine import (
    ArpEngine, ArpPattern, ArpSettings,
    ARP_RATE_LABELS, ARP_DEFAULT_RATE_INDEX
)
from .seq_engine import SeqEngine, SEQ_RATE_LABELS, SEQ_DEFAULT_RATE_INDEX
from src.model.sequencer import StepType, SeqStep, MotionMode

# Key -> semitone offset from C (within current octave span)
KEY_TO_SEMITONE = {
    # White keys (bottom row) - C D E F G A B C D E
    Qt.Key_A: 0,
    Qt.Key_S: 2,
    Qt.Key_D: 4,
    Qt.Key_F: 5,
    Qt.Key_G: 7,
    Qt.Key_H: 9,
    Qt.Key_J: 11,
    Qt.Key_K: 12,
    Qt.Key_L: 14,
    Qt.Key_Semicolon: 16,
    # Black keys (top row) - C# D# F# G# A# C# D#
    Qt.Key_W: 1,
    Qt.Key_E: 3,
    Qt.Key_T: 6,
    Qt.Key_Y: 8,
    Qt.Key_U: 10,
    Qt.Key_O: 13,
    Qt.Key_P: 15,
}

OCTAVE_KEYS = {
    Qt.Key_Z: -1,
    Qt.Key_X: +1,
}

# Display labels for keys
WHITE_KEYS = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';']
BLACK_KEYS = ['W', 'E', '', 'T', 'Y', 'U', '', 'O', 'P']
NOTE_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C', 'D', 'E']

# ARP pattern labels
ARP_PATTERN_LABELS = {
    ArpPattern.UP: "UP",
    ArpPattern.DOWN: "DN",
    ArpPattern.UPDOWN: "UD",
    ArpPattern.RANDOM: "RND",
    ArpPattern.ORDER: "ORD",
}
ARP_PATTERN_ORDER = [ArpPattern.UP, ArpPattern.DOWN, ArpPattern.UPDOWN,
                     ArpPattern.RANDOM, ArpPattern.ORDER]


class KeyboardOverlay(QWidget):
    """
    QWERTY keyboard overlay for MIDI note input with per-slot arpeggiator.

    v2.0: Pure view — does not own ArpEngine instances.
    Engine is bound via set_arp_engine() and unbound via set_arp_engine(None).
    Physical keys held are overlay state (not engine state).

    Slot indices:
    - UI uses 1-8 (matches generator slot labels)
    - OSC uses 0-7 (internal indexing)
    - Conversion happens in send methods
    """

    def __init__(self, parent, send_note_on_fn, send_note_off_fn,
                 send_all_notes_off_fn, get_focused_slot_fn, is_slot_midi_mode_fn,
                 on_slot_focus_changed_fn: Optional[Callable[[int], None]] = None,
                 on_seq_mode_changed_fn: Optional[Callable[[bool, int], None]] = None):
        super().__init__(parent)

        # Callbacks - these expect 0-indexed slot IDs
        self._send_note_on = send_note_on_fn
        self._send_note_off = send_note_off_fn
        self._send_all_notes_off = send_all_notes_off_fn
        # These return/accept 1-indexed slot IDs
        self._get_focused_slot = get_focused_slot_fn
        self._is_slot_midi_mode = is_slot_midi_mode_fn
        # Callback when user clicks a different slot button
        self._on_slot_focus_changed = on_slot_focus_changed_fn
        # Callback when SEQ mode toggled (enabled: bool, slot_0idx: int)
        self._on_seq_mode_changed = on_seq_mode_changed_fn

        # State - internally uses 1-indexed slot IDs (like UI)
        self._octave = 4
        self._velocity = 100
        self._physical_keys_held: dict[int, int] = {}  # qt_key -> midi_note
        self._target_slot: int = 1  # Single-select (1-indexed)

        # Bound ARP engine (None when no engine bound)
        self._arp_engine: Optional[ArpEngine] = None

        # Bound SEQ engine (None when no engine bound)
        self._seq_engine: Optional[SeqEngine] = None
        self._seq_recording: bool = False
        self._seq_input_cursor: int = 0

        # Dragging state
        self._drag_pos = None

        # UI elements
        self._key_buttons: dict[int, QPushButton] = {}
        self._slot_buttons: list[QPushButton] = []
        self._slot_button_group: Optional[QButtonGroup] = None
        self._octave_label: QLabel = None
        self._velocity_buttons: list[QPushButton] = []

        # ARP UI elements
        self._arp_toggle_btn: QPushButton = None
        self._arp_controls_frame: QFrame = None
        self._arp_rate_btn: QPushButton = None
        self._arp_pattern_btn: QPushButton = None
        self._arp_octaves_btn: QPushButton = None
        self._arp_hold_btn: QPushButton = None

        # SEQ UI elements
        self._seq_toggle_btn: QPushButton = None
        self._seq_controls_frame: QFrame = None
        self._seq_rate_btn = None
        self._seq_length_btn = None
        self._seq_play_btn: QPushButton = None
        self._seq_rec_btn: QPushButton = None
        self._seq_rest_btn: QPushButton = None
        self._seq_tie_btn: QPushButton = None

        # Step grid UI
        self._seq_grid_frame: QFrame = None
        self._step_cells: list[QPushButton] = []
        self._last_steps_version: int = -1
        self._last_playhead: int = -1
        self._grid_refresh_timer: QTimer = None

        self._setup_ui()
        self._apply_style()

        # Start hidden
        self.hide()

    # =========================================================================
    # ENGINE BINDING (per spec v1.2.1)
    # =========================================================================

    def set_arp_engine(self, engine: Optional[ArpEngine]):
        """
        Bind or unbind an ARP engine.

        When bound: UI controls reflect engine state.
        When unbound (None): ARP controls disabled, keys do nothing.
        """
        self._arp_engine = engine
        if engine is not None:
            self.sync_ui_from_engine()

    def set_seq_engine(self, engine: Optional[SeqEngine]):
        """
        Bind or unbind a SEQ engine for step recording.

        When bound: overlay can enter step-recording mode.
        When unbound (None): step recording disabled.
        """
        self._seq_engine = engine
        if engine is None:
            self._seq_recording = False
            self._seq_input_cursor = 0

    def sync_seq_ui_state(self, seq_active: bool):
        """
        Sync SEQ UI controls to match the slot's current MotionMode.

        Called by controller after binding engines on slot focus switch
        or overlay open. Updates toggle, controls visibility, and control values.
        """
        self._seq_toggle_btn.setChecked(seq_active)

        if seq_active:
            self._seq_controls_frame.show()
            self._seq_grid_frame.show()
            # Sync control values from engine
            if self._seq_engine is not None:
                self._seq_rate_btn.set_index(self._seq_engine.rate_index)
                self._seq_length_btn.set_index(self._seq_engine.settings.length - 1)
                self._seq_play_btn.setChecked(self._seq_engine.is_playing)
            self._refresh_step_grid()
            self._grid_refresh_timer.start()
        else:
            self._seq_controls_frame.hide()
            self._seq_grid_frame.hide()
            self._grid_refresh_timer.stop()
            self._seq_recording = False
            if self._seq_rec_btn is not None:
                self._seq_rec_btn.setChecked(False)
            if self._seq_play_btn is not None:
                self._seq_play_btn.setChecked(False)

        self._update_overlay_size()

    def set_seq_recording(self, enabled: bool):
        """Toggle step recording mode."""
        if self._seq_engine is None:
            self._seq_recording = False
            return
        self._seq_recording = enabled
        if enabled:
            self._seq_input_cursor = 0

    def _is_seq_recording_mode(self) -> bool:
        """Check if currently in SEQ step-recording mode."""
        return self._seq_recording and self._seq_engine is not None

    def _advance_input_cursor(self):
        """Advance step-recording cursor with wrap."""
        if self._seq_engine is None:
            return
        length = self._seq_engine.settings.length
        self._seq_input_cursor = (self._seq_input_cursor + 1) % length

    def _move_input_cursor(self, delta: int):
        """Move step-recording cursor by delta with wrap."""
        if self._seq_engine is None:
            return
        length = self._seq_engine.settings.length
        self._seq_input_cursor = (self._seq_input_cursor + delta) % length

    def sync_ui_from_engine(self):
        """Exhaustive UI sync from bound engine's state (ARP only).

        SEQ state is synced separately via sync_seq_ui_state() which
        is called by the controller after binding both engines.
        """
        engine = self._arp_engine
        if engine is None:
            # Reset UI to defaults
            self._arp_toggle_btn.setChecked(False)
            self._arp_controls_frame.hide()
            self._update_overlay_size()
            return

        settings = engine.get_settings()

        # ARP toggle
        self._arp_toggle_btn.setChecked(settings.enabled)
        if settings.enabled:
            self._arp_controls_frame.show()
        else:
            self._arp_controls_frame.hide()

        # ARP controls
        self._arp_rate_btn.set_index(settings.rate_index)
        pattern_idx = ARP_PATTERN_ORDER.index(settings.pattern)
        self._arp_pattern_btn.set_index(pattern_idx)
        self._arp_octaves_btn.set_index(settings.octaves - 1)
        self._arp_hold_btn.setChecked(settings.hold)

        # Target slot button — highlight the engine's slot
        target_ui_slot = engine.slot_id + 1  # 0-indexed -> 1-indexed
        self._target_slot = target_ui_slot
        for i, btn in enumerate(self._slot_buttons):
            slot_id = i + 1
            btn.setChecked(slot_id == target_ui_slot)

        self._update_overlay_size()

    # =========================================================================
    # UI SETUP
    # =========================================================================

    def _setup_ui(self):
        """Build the overlay UI."""
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.setFixedSize(560, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header (draggable)
        header = self._create_header()
        layout.addWidget(header)

        # ARP controls row (hidden when ARP off)
        self._arp_controls_frame = self._create_arp_controls()
        layout.addWidget(self._arp_controls_frame)

        # SEQ controls row (hidden when SEQ off)
        self._seq_controls_frame = self._create_seq_controls()
        layout.addWidget(self._seq_controls_frame)

        # SEQ step grid (hidden when SEQ off)
        self._seq_grid_frame = self._create_step_grid()
        layout.addWidget(self._seq_grid_frame)

        # Keyboard area
        keyboard = self._create_keyboard()
        layout.addWidget(keyboard)

        # Octave controls
        octave_row = self._create_octave_controls()
        layout.addWidget(octave_row)

        # Target slots
        targets = self._create_target_slots()
        layout.addWidget(targets)

    def _create_header(self) -> QFrame:
        """Create draggable header with title, ARP toggle, velocity selector, octave display."""
        header = QFrame()
        header.setObjectName("keyboard_header")
        header.setFixedHeight(36)
        header.setCursor(Qt.OpenHandCursor)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 0, 12, 0)

        # Drag handle + title
        title = QLabel("KEYBOARD")
        title.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        layout.addWidget(title)

        layout.addSpacing(8)

        # ARP toggle button
        self._arp_toggle_btn = QPushButton("ARP")
        self._arp_toggle_btn.setCheckable(True)
        self._arp_toggle_btn.setFixedSize(40, 24)
        self._arp_toggle_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._arp_toggle_btn.setToolTip("Toggle Arpeggiator")
        self._arp_toggle_btn.clicked.connect(self._on_arp_toggle)
        layout.addWidget(self._arp_toggle_btn)

        layout.addSpacing(4)

        # SEQ toggle button
        self._seq_toggle_btn = QPushButton("SEQ")
        self._seq_toggle_btn.setCheckable(True)
        self._seq_toggle_btn.setFixedSize(40, 24)
        self._seq_toggle_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._seq_toggle_btn.setToolTip("Toggle Step Sequencer")
        self._seq_toggle_btn.clicked.connect(self._on_seq_toggle)
        layout.addWidget(self._seq_toggle_btn)

        layout.addStretch()

        # Velocity selector
        vel_label = QLabel("Vel:")
        vel_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(vel_label)

        vel_group = QButtonGroup(self)
        for vel in [64, 100, 127]:
            btn = QPushButton(str(vel))
            btn.setCheckable(True)
            btn.setFixedSize(36, 24)
            btn.setFont(QFont(FONT_FAMILY, 9))
            btn.clicked.connect(lambda checked, v=vel: self._set_velocity(v))
            vel_group.addButton(btn)
            self._velocity_buttons.append(btn)
            layout.addWidget(btn)
            if vel == 100:
                btn.setChecked(True)

        layout.addSpacing(16)

        # Close button
        close_btn = QPushButton("CLOSE")
        close_btn.setFixedSize(50, 24)
        close_btn.setFont(QFont(FONT_FAMILY, 10))
        close_btn.setObjectName("keyboard_close")
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn)

        # Octave display
        oct_title = QLabel("Oct:")
        oct_title.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(oct_title)

        self._octave_label = QLabel(str(self._octave))
        self._octave_label.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        self._octave_label.setFixedWidth(24)
        layout.addWidget(self._octave_label)

        # Make header draggable
        header.mousePressEvent = self._header_mouse_press
        header.mouseMoveEvent = self._header_mouse_move
        header.mouseReleaseEvent = self._header_mouse_release

        return header

    def _create_arp_controls(self) -> QFrame:
        """Create ARP controls row (visible only when ARP enabled)."""
        frame = QFrame()
        frame.setObjectName("keyboard_arp_controls")
        frame.setFixedHeight(36)
        frame.hide()  # Hidden by default

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Rate button (CycleButton with drag support)
        rate_label = QLabel("Rate:")
        rate_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(rate_label)

        self._arp_rate_btn = CycleButton(list(ARP_RATE_LABELS), ARP_DEFAULT_RATE_INDEX)
        self._arp_rate_btn.setFixedSize(50, 24)
        self._arp_rate_btn.setFont(QFont(FONT_FAMILY, 9))
        self._arp_rate_btn.setToolTip("ARP rate (click or drag)")
        self._arp_rate_btn.invert_drag = True  # Drag up = faster (higher index)
        self._arp_rate_btn.index_changed.connect(self._on_rate_changed)
        layout.addWidget(self._arp_rate_btn)

        layout.addSpacing(8)

        # Pattern button (CycleButton with drag support)
        pattern_label = QLabel("Pattern:")
        pattern_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(pattern_label)

        pattern_labels = [ARP_PATTERN_LABELS[p] for p in ARP_PATTERN_ORDER]
        self._arp_pattern_btn = CycleButton(pattern_labels, 0)
        self._arp_pattern_btn.setFixedSize(44, 24)
        self._arp_pattern_btn.setFont(QFont(FONT_FAMILY, 9))
        self._arp_pattern_btn.setToolTip("Pattern (click or drag)")
        self._arp_pattern_btn.index_changed.connect(self._on_pattern_changed)
        layout.addWidget(self._arp_pattern_btn)

        layout.addSpacing(8)

        # Octaves button (CycleButton with drag support)
        oct_label = QLabel("Oct:")
        oct_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(oct_label)

        self._arp_octaves_btn = CycleButton(["1", "2", "3", "4"], 0)
        self._arp_octaves_btn.setFixedSize(32, 24)
        self._arp_octaves_btn.setFont(QFont(FONT_FAMILY, 9))
        self._arp_octaves_btn.setToolTip("Octave range (click or drag)")
        self._arp_octaves_btn.index_changed.connect(self._on_octaves_changed)
        layout.addWidget(self._arp_octaves_btn)

        layout.addSpacing(8)

        # Hold button
        self._arp_hold_btn = QPushButton("HOLD")
        self._arp_hold_btn.setCheckable(True)
        self._arp_hold_btn.setFixedSize(50, 24)
        self._arp_hold_btn.setFont(QFont(FONT_FAMILY, 9))
        self._arp_hold_btn.setToolTip("Latch notes (toggle on key press)")
        self._arp_hold_btn.clicked.connect(self._on_hold_toggle)
        layout.addWidget(self._arp_hold_btn)

        layout.addStretch()

        return frame

    def _create_seq_controls(self) -> QFrame:
        """Create SEQ controls row (visible only when SEQ enabled)."""
        frame = QFrame()
        frame.setObjectName("keyboard_seq_controls")
        frame.setFixedHeight(36)
        frame.hide()  # Hidden by default

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Rate button
        rate_label = QLabel("Rate:")
        rate_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(rate_label)

        self._seq_rate_btn = CycleButton(list(SEQ_RATE_LABELS), SEQ_DEFAULT_RATE_INDEX)
        self._seq_rate_btn.setFixedSize(50, 24)
        self._seq_rate_btn.setFont(QFont(FONT_FAMILY, 9))
        self._seq_rate_btn.setToolTip("SEQ rate (click or drag)")
        self._seq_rate_btn.invert_drag = True
        self._seq_rate_btn.index_changed.connect(self._on_seq_rate_changed)
        layout.addWidget(self._seq_rate_btn)

        layout.addSpacing(8)

        # Length button
        len_label = QLabel("Len:")
        len_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(len_label)

        length_labels = [str(i) for i in range(1, 17)]
        self._seq_length_btn = CycleButton(length_labels, 15)  # Default 16
        self._seq_length_btn.setFixedSize(36, 24)
        self._seq_length_btn.setFont(QFont(FONT_FAMILY, 9))
        self._seq_length_btn.setToolTip("Sequence length (click or drag)")
        self._seq_length_btn.index_changed.connect(self._on_seq_length_changed)
        layout.addWidget(self._seq_length_btn)

        layout.addSpacing(12)

        # PLAY button (toggle playback)
        self._seq_play_btn = QPushButton("PLAY")
        self._seq_play_btn.setCheckable(True)
        self._seq_play_btn.setFixedSize(46, 24)
        self._seq_play_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._seq_play_btn.setToolTip("Start/stop sequence playback")
        self._seq_play_btn.clicked.connect(self._on_seq_play_toggle)
        layout.addWidget(self._seq_play_btn)

        layout.addSpacing(4)

        # REC button (toggle step recording)
        self._seq_rec_btn = QPushButton("REC")
        self._seq_rec_btn.setCheckable(True)
        self._seq_rec_btn.setFixedSize(40, 24)
        self._seq_rec_btn.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self._seq_rec_btn.setToolTip("Step record mode (keys enter notes)")
        self._seq_rec_btn.clicked.connect(self._on_seq_rec_toggle)
        layout.addWidget(self._seq_rec_btn)

        layout.addSpacing(4)

        # REST button (insert rest step)
        self._seq_rest_btn = QPushButton("REST")
        self._seq_rest_btn.setFixedSize(44, 24)
        self._seq_rest_btn.setFont(QFont(FONT_FAMILY, 9))
        self._seq_rest_btn.setToolTip("Insert rest step (or press Space)")
        self._seq_rest_btn.clicked.connect(self._on_seq_rest_clicked)
        layout.addWidget(self._seq_rest_btn)

        layout.addSpacing(4)

        # TIE button (insert tie step)
        self._seq_tie_btn = QPushButton("TIE")
        self._seq_tie_btn.setFixedSize(36, 24)
        self._seq_tie_btn.setFont(QFont(FONT_FAMILY, 9))
        self._seq_tie_btn.setToolTip("Insert tie/sustain step (or press Tab)")
        self._seq_tie_btn.clicked.connect(self._on_seq_tie_clicked)
        layout.addWidget(self._seq_tie_btn)

        layout.addStretch()

        return frame

    def _create_step_grid(self) -> QFrame:
        """Create 16-cell step grid visualization (hidden when SEQ off)."""
        frame = QFrame()
        frame.setObjectName("keyboard_step_grid")
        frame.setFixedHeight(40)
        frame.hide()

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        self._step_cells = []
        for i in range(16):
            cell = QPushButton("")
            cell.setFixedSize(32, 28)
            cell.setFont(QFont(FONT_FAMILY, 8))
            cell.setObjectName("step_cell")
            cell.setProperty("step_state", "empty")
            cell.setProperty("cursor_here", "false")
            cell.setProperty("playhead", "false")
            cell.clicked.connect(lambda checked, idx=i: self._on_step_cell_clicked(idx))
            layout.addWidget(cell)
            self._step_cells.append(cell)

        layout.addStretch()

        # Timer for playhead refresh during playback
        self._grid_refresh_timer = QTimer(self)
        self._grid_refresh_timer.setInterval(50)
        self._grid_refresh_timer.timeout.connect(self._refresh_step_grid)

        return frame

    def _create_keyboard(self) -> QFrame:
        """Create the piano keyboard visualization."""
        keyboard = QFrame()
        keyboard.setObjectName("keyboard_keys")

        layout = QVBoxLayout(keyboard)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(4)

        # Black keys row
        black_row = QHBoxLayout()
        black_row.setSpacing(4)
        black_row.addSpacing(20)  # Offset for piano layout

        for i, label in enumerate(BLACK_KEYS):
            if label:
                btn = QPushButton(label)
                btn.setFixedSize(36, 40)
                btn.setObjectName("black_key")
                btn.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
                # Map label to Qt key
                qt_key = getattr(Qt, f"Key_{label}", None)
                if qt_key:
                    self._key_buttons[qt_key] = btn
            else:
                btn = QWidget()
                btn.setFixedSize(36, 40)
            black_row.addWidget(btn)

        black_row.addStretch()
        layout.addLayout(black_row)

        # White keys row
        white_row = QHBoxLayout()
        white_row.setSpacing(4)

        for i, label in enumerate(WHITE_KEYS):
            btn = QPushButton(f"{label}\n{NOTE_NAMES[i]}")
            btn.setFixedSize(44, 56)
            btn.setObjectName("white_key")
            btn.setFont(QFont(FONT_FAMILY, 9))
            # Map label to Qt key
            if label == ';':
                qt_key = Qt.Key_Semicolon
            else:
                qt_key = getattr(Qt, f"Key_{label}", None)
            if qt_key:
                self._key_buttons[qt_key] = btn
            white_row.addWidget(btn)

        white_row.addStretch()
        layout.addLayout(white_row)

        return keyboard

    def _create_octave_controls(self) -> QFrame:
        """Create octave up/down display."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 4, 16, 4)

        z_label = QLabel("[Z] Oct-")
        z_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(z_label)

        layout.addSpacing(24)

        x_label = QLabel("[X] Oct+")
        x_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(x_label)

        layout.addStretch()

        return frame

    def _create_target_slots(self) -> QFrame:
        """Create target slot selection row (single-select radio group)."""
        frame = QFrame()
        frame.setObjectName("keyboard_targets")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 8, 16, 12)

        label = QLabel("Target:")
        label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(label)

        layout.addSpacing(8)

        # Single-select group (exclusive)
        self._slot_button_group = QButtonGroup(self)
        self._slot_button_group.setExclusive(True)

        # Slots 1-8 (UI uses 1-indexed)
        for i in range(1, 9):
            btn = QPushButton(str(i))
            btn.setCheckable(True)
            btn.setFixedSize(32, 28)
            btn.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
            btn.clicked.connect(lambda checked, slot=i: self._on_target_slot_clicked(slot))
            self._slot_button_group.addButton(btn, i)
            self._slot_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        return frame

    def _apply_style(self):
        """Apply modern themed styling with accent colors."""
        # Keyboard accent color - magenta/pink for performance energy
        accent = '#ff00ff'
        accent_dim = '#aa00aa'
        accent_bg = '#1a0a1a'

        self.setStyleSheet(f"""
            KeyboardOverlay {{
                background: {COLORS['background_dark']};
                border: 2px solid {accent_dim};
                border-radius: 8px;
            }}

            #keyboard_header {{
                background: {accent_bg};
                border-bottom: 1px solid {accent_dim};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}

            #keyboard_header QLabel {{
                color: {accent};
            }}

            #keyboard_header QPushButton {{
                background: {COLORS['background']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 4px;
                color: {COLORS['text']};
            }}

            #keyboard_header QPushButton:hover {{
                border-color: {accent_dim};
            }}

            #keyboard_header QPushButton:checked {{
                background: {accent_bg};
                border: 1px solid {accent};
                color: {accent};
            }}

            #keyboard_arp_controls {{
                background: {COLORS['background']};
                border-bottom: 1px solid {COLORS['border']};
            }}

            #keyboard_arp_controls QLabel {{
                color: {COLORS['text_bright']};
            }}

            #keyboard_arp_controls QPushButton {{
                background: {COLORS['background_highlight']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 4px;
                color: {accent};
            }}

            #keyboard_arp_controls QPushButton:hover {{
                border-color: {accent_dim};
                background: {accent_bg};
            }}

            #keyboard_arp_controls QPushButton:checked {{
                background: {accent_bg};
                border: 1px solid {accent};
                color: {accent};
            }}

            #keyboard_seq_controls {{
                background: {COLORS['background']};
                border-bottom: 1px solid {COLORS['border']};
            }}

            #keyboard_seq_controls QLabel {{
                color: {COLORS['text_bright']};
            }}

            #keyboard_seq_controls QPushButton {{
                background: {COLORS['background_highlight']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 4px;
                color: {accent};
            }}

            #keyboard_seq_controls QPushButton:hover {{
                border-color: {accent_dim};
                background: {accent_bg};
            }}

            #keyboard_seq_controls QPushButton:checked {{
                background: {accent_bg};
                border: 1px solid {accent};
                color: {accent};
            }}

            #keyboard_step_grid {{
                background: {COLORS['background_dark']};
                border-bottom: 1px solid {COLORS['border']};
            }}

            #step_cell {{
                background: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                color: {COLORS['text_dim']};
                font-size: {FONT_SIZES['small']}px;
            }}

            #step_cell:hover {{
                border-color: {accent_dim};
            }}

            #step_cell[step_state="note"] {{
                background: {accent_bg};
                color: {accent};
                border-color: {accent_dim};
            }}

            #step_cell[step_state="rest"] {{
                background: {COLORS['background_dark']};
                color: {COLORS['text_dim']};
            }}

            #step_cell[step_state="tie"] {{
                background: #1a1a0a;
                color: #aaaa00;
                border-color: #555500;
            }}

            #step_cell[step_state="inactive"] {{
                background: {COLORS['background_dark']};
                border-color: transparent;
                color: transparent;
            }}

            #step_cell[cursor_here="true"] {{
                border: 2px solid #00ccff;
            }}

            #step_cell[playhead="true"] {{
                border: 2px solid {accent};
            }}

            #keyboard_keys {{
                background: {COLORS['background_dark']};
            }}

            #white_key {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f5f5, stop:0.1 #e8e8e8, stop:0.9 #d8d8d8, stop:1 #c8c8c8);
                border: 1px solid #888;
                border-radius: 4px;
                color: #333;
            }}

            #white_key:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:0.1 #f0f0f0, stop:0.9 #e0e0e0, stop:1 #d0d0d0);
                border-color: {accent_dim};
            }}

            #white_key:pressed, #white_key[pressed="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {accent}, stop:0.2 #dd00dd, stop:0.8 #bb00bb, stop:1 #990099);
                border: 2px solid {accent};
                color: #fff;
            }}

            #black_key {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #404040, stop:0.1 #333333, stop:0.9 #222222, stop:1 #1a1a1a);
                border: 1px solid #555;
                border-radius: 4px;
                color: #999;
            }}

            #black_key:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #505050, stop:0.1 #404040, stop:0.9 #303030, stop:1 #252525);
                border-color: {accent_dim};
            }}

            #black_key:pressed, #black_key[pressed="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {accent}, stop:0.2 #dd00dd, stop:0.8 #990099, stop:1 #770077);
                border: 2px solid {accent};
                color: #fff;
            }}

            #keyboard_targets {{
                background: {COLORS['background_dark']};
                border-top: 1px solid {COLORS['border']};
            }}

            #keyboard_targets QLabel {{
                color: {COLORS['text_bright']};
            }}

            #keyboard_targets QPushButton {{
                background: {COLORS['background']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 4px;
                color: {COLORS['text_dim']};
            }}

            #keyboard_targets QPushButton:hover {{
                border-color: {accent_dim};
            }}

            #keyboard_targets QPushButton:checked {{
                background: {accent_bg};
                border: 1px solid {accent};
                color: {accent};
            }}

            #keyboard_targets QPushButton:disabled {{
                background: {COLORS['background_dark']};
                border-color: {COLORS['border']};
                color: {COLORS['border']};
            }}

            QLabel {{
                color: {COLORS['text']};
            }}
        """)

    # -------------------------------------------------------------------------
    # ARP Control Handlers
    # -------------------------------------------------------------------------

    def _on_arp_toggle(self):
        """Handle ARP toggle button click."""
        if self._arp_engine is None:
            self._arp_toggle_btn.setChecked(False)
            return

        enabled = self._arp_toggle_btn.isChecked()
        self._arp_engine.toggle_arp(enabled)

        if enabled:
            self._arp_controls_frame.show()

            # Disable SEQ when enabling ARP (mutually exclusive)
            if self._seq_toggle_btn.isChecked():
                self._seq_toggle_btn.setChecked(False)
                self._seq_controls_frame.hide()
                self._seq_grid_frame.hide()
                self._grid_refresh_timer.stop()
                self._seq_recording = False
                if self._seq_rec_btn is not None:
                    self._seq_rec_btn.setChecked(False)
                if self._seq_play_btn is not None:
                    self._seq_play_btn.setChecked(False)
                # Notify controller to switch MotionMode OFF for SEQ
                if self._on_seq_mode_changed is not None and self._seq_engine is not None:
                    self._on_seq_mode_changed(False, self._seq_engine.slot_id)
        else:
            self._arp_controls_frame.hide()

        self._update_overlay_size()

    def _on_rate_changed(self, index: int):
        """Handle ARP rate change from CycleButton."""
        if self._arp_engine is not None:
            self._arp_engine.set_rate(index)

    def _on_pattern_changed(self, index: int):
        """Handle ARP pattern change from CycleButton."""
        if self._arp_engine is not None:
            new_pattern = ARP_PATTERN_ORDER[index]
            self._arp_engine.set_pattern(new_pattern)

    def _on_octaves_changed(self, index: int):
        """Handle ARP octaves change from CycleButton."""
        if self._arp_engine is not None:
            new_octaves = index + 1  # Index 0 = 1 octave, etc.
            self._arp_engine.set_octaves(new_octaves)

    def _on_hold_toggle(self):
        """Toggle ARP hold/latch mode."""
        if self._arp_engine is None:
            self._arp_hold_btn.setChecked(False)
            return

        enabled = self._arp_hold_btn.isChecked()
        self._arp_engine.toggle_hold(enabled)

    # -------------------------------------------------------------------------
    # SEQ Control Handlers
    # -------------------------------------------------------------------------

    def _on_seq_toggle(self):
        """Handle SEQ toggle button click — shows/hides SEQ UI controls."""
        enabled = self._seq_toggle_btn.isChecked()

        if enabled:
            if self._seq_engine is None:
                self._seq_toggle_btn.setChecked(False)
                return

            # Disable ARP when enabling SEQ (mutually exclusive)
            if self._arp_engine is not None and self._arp_engine.is_enabled():
                self._arp_engine.toggle_arp(False)
            self._arp_toggle_btn.setChecked(False)
            self._arp_controls_frame.hide()

            self._seq_controls_frame.show()
            self._seq_grid_frame.show()
            self._refresh_step_grid()
            self._grid_refresh_timer.start()
        else:
            # Turning SEQ off — also stop playback
            if self._seq_play_btn.isChecked():
                self._seq_play_btn.setChecked(False)
                if self._on_seq_mode_changed is not None and self._seq_engine is not None:
                    self._on_seq_mode_changed(False, self._seq_engine.slot_id)

            self._seq_controls_frame.hide()
            self._seq_grid_frame.hide()
            self._grid_refresh_timer.stop()
            self._seq_recording = False
            if self._seq_rec_btn is not None:
                self._seq_rec_btn.setChecked(False)

        self._update_overlay_size()

    def _on_seq_rate_changed(self, index: int):
        """Handle SEQ rate change from CycleButton."""
        if self._seq_engine is not None:
            self._seq_engine.set_rate(index)

    def _on_seq_length_changed(self, index: int):
        """Handle SEQ length change from CycleButton."""
        if self._seq_engine is not None:
            new_length = index + 1  # Index 0 = length 1, etc.
            self._seq_engine.set_length(new_length)

    def _on_seq_play_toggle(self):
        """Toggle sequence playback — sets MotionMode via controller."""
        if self._seq_engine is None:
            self._seq_play_btn.setChecked(False)
            return

        playing = self._seq_play_btn.isChecked()

        # Notify controller to set MotionMode (which starts/stops the engine)
        if self._on_seq_mode_changed is not None:
            self._on_seq_mode_changed(playing, self._seq_engine.slot_id)

    def _on_seq_rec_toggle(self):
        """Toggle step recording mode."""
        enabled = self._seq_rec_btn.isChecked()
        self.set_seq_recording(enabled)

    def _on_seq_rest_clicked(self):
        """Insert a REST step at the current cursor position."""
        if self._seq_engine is None:
            return
        if not self._seq_recording:
            self.set_seq_recording(True)
            self._seq_rec_btn.setChecked(True)

        self._seq_engine.settings.steps[self._seq_input_cursor] = SeqStep(
            step_type=StepType.REST,
        )
        self._seq_engine.steps_version += 1
        self._advance_input_cursor()
        self._refresh_step_grid()

    def _on_seq_tie_clicked(self):
        """Insert a TIE step at the current cursor position."""
        if self._seq_engine is None:
            return
        if not self._seq_recording:
            self.set_seq_recording(True)
            self._seq_rec_btn.setChecked(True)

        self._seq_engine.settings.steps[self._seq_input_cursor] = SeqStep(
            step_type=StepType.TIE,
        )
        self._seq_engine.steps_version += 1
        self._advance_input_cursor()
        self._refresh_step_grid()

    # -------------------------------------------------------------------------
    # Overlay Sizing
    # -------------------------------------------------------------------------

    def _update_overlay_size(self):
        """Update overlay height based on which control rows are visible."""
        base = 320
        if self._arp_controls_frame.isVisible():
            base += 36
        if self._seq_controls_frame.isVisible():
            base += 36
        if self._seq_grid_frame.isVisible():
            base += 40
        self.setFixedSize(560, base)

    # -------------------------------------------------------------------------
    # Header Dragging
    # -------------------------------------------------------------------------

    def _header_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def _header_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _header_mouse_release(self, event):
        self._drag_pos = None
        event.accept()

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def _set_velocity(self, vel: int):
        self._velocity = vel

    def get_velocity(self) -> int:
        """Get current velocity (used by ArpEngine via callback)."""
        return self._velocity

    def _on_target_slot_clicked(self, slot: int):
        """Handle single-select target slot click. slot is 1-indexed (UI)."""
        if slot == self._target_slot:
            # Already selected — keep it checked (don't allow deselect in exclusive mode)
            self._slot_buttons[slot - 1].setChecked(True)
            return

        # Notify controller of focus change (controller handles engine swap)
        if self._on_slot_focus_changed is not None:
            self._on_slot_focus_changed(slot)

    def _update_slot_buttons(self):
        """
        Update slot button states.

        All 8 buttons are always enabled — clicking any slot auto-switches
        it to MIDI mode (handled by controller). Only the target slot is checked.
        """
        for i, btn in enumerate(self._slot_buttons):
            slot_id = i + 1  # 1-indexed
            btn.setEnabled(True)
            btn.setChecked(slot_id == self._target_slot)

    # -------------------------------------------------------------------------
    # Toggle / Show / Hide
    # -------------------------------------------------------------------------

    def toggle(self):
        """Toggle overlay visibility."""
        if self.isVisible():
            self._dismiss()
        else:
            self._show_overlay()

    def _show_overlay(self):
        """Show and activate the overlay."""
        # Update slot buttons based on current MIDI mode states
        self._update_slot_buttons()

        # Position at bottom-center of parent, 24px margin
        if self.parent():
            parent = self.parent()
            x = (parent.width() - self.width()) // 2
            y = parent.height() - self.height() - 24
            self.move(parent.mapToGlobal(QPoint(x, y)))

        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)

    def _dismiss(self):
        """
        Hide overlay and release physical keys.

        Per spec v1.2.1:
        1. Release all physical keys from focused engine
        2. Clear _physical_keys_held
        3. Controller handles teardown/preservation (not overlay)
        4. Hide overlay
        """
        # Release physical keys from bound engine
        self._release_all_physical_keys()

        # Clear physical key state
        self._physical_keys_held.clear()

        # Reset key visuals
        for qt_key in self._key_buttons:
            self._update_key_visual(qt_key, False)

        # Stop grid refresh timer
        if self._grid_refresh_timer is not None:
            self._grid_refresh_timer.stop()

        # Hide overlay
        self.hide()

    def release_physical_keys_from_engine(self):
        """
        Release all physical keys from the currently bound engine.
        Called by controller before switching engines on focus change.
        """
        self._release_all_physical_keys()
        self._physical_keys_held.clear()
        for qt_key in self._key_buttons:
            self._update_key_visual(qt_key, False)

    def _release_all_physical_keys(self):
        """Release all currently held physical keys from the bound engine."""
        if self._arp_engine is None:
            return

        for qt_key, midi_note in list(self._physical_keys_held.items()):
            if self._arp_engine.is_enabled():
                self._arp_engine.key_release(midi_note)
            else:
                # Legacy: note-off to target slot
                osc_slot = self._target_slot - 1
                self._send_note_off(osc_slot, midi_note)

    # -------------------------------------------------------------------------
    # Key Event Handling
    # -------------------------------------------------------------------------

    def keyPressEvent(self, event):
        """Handle key press - trigger notes."""
        # ESC dismisses
        if event.key() == Qt.Key_Escape:
            self._dismiss()
            event.accept()
            return

        # Cmd/Ctrl+K dismisses (toggle)
        if event.key() == Qt.Key_K and event.modifiers() & Qt.ControlModifier:
            self._dismiss()
            event.accept()
            return

        # Number keys 1-8 switch target slot (single-select)
        if Qt.Key_1 <= event.key() <= Qt.Key_8:
            slot_index = event.key() - Qt.Key_1  # 0-7
            self._slot_buttons[slot_index].click()
            event.accept()
            return

        # Ignore auto-repeat
        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()

        # SEQ step recording mode — intercept keys for step input
        if self._is_seq_recording_mode():
            self._handle_seq_recording_key(key)
            event.accept()
            return

        # Octave change
        if key in OCTAVE_KEYS:
            self._handle_octave_change(OCTAVE_KEYS[key])
            event.accept()
            return

        # Note key
        if key in KEY_TO_SEMITONE and key not in self._physical_keys_held:
            if self._arp_engine is None:
                event.accept()
                return

            semitone = KEY_TO_SEMITONE[key]
            midi_note = self._compute_midi_note(semitone)

            if 0 <= midi_note <= 127:
                self._physical_keys_held[key] = midi_note

                if self._arp_engine.is_enabled():
                    self._arp_engine.key_press(midi_note)
                else:
                    # Legacy: direct note-on to target slot
                    osc_slot = self._target_slot - 1
                    self._send_note_on(osc_slot, midi_note, self._velocity)

                self._update_key_visual(key, True)

        event.accept()

    def keyReleaseEvent(self, event):
        """Handle key release - stop notes."""
        # Ignore auto-repeat
        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()

        # Release note
        if key in self._physical_keys_held:
            midi_note = self._physical_keys_held.pop(key)

            if self._arp_engine is not None:
                if self._arp_engine.is_enabled():
                    self._arp_engine.key_release(midi_note)
                else:
                    # Legacy: note-off to target slot
                    osc_slot = self._target_slot - 1
                    self._send_note_off(osc_slot, midi_note)

            self._update_key_visual(key, False)

        event.accept()

    def _compute_midi_note(self, semitone: int) -> int:
        """Compute MIDI note from semitone offset and current octave."""
        return (self._octave + 1) * 12 + semitone

    def _handle_octave_change(self, delta: int):
        """Handle octave up/down with held note re-triggering."""
        new_octave = max(0, min(7, self._octave + delta))

        if new_octave == self._octave:
            return

        if self._arp_engine is None:
            self._octave = new_octave
            self._octave_label.setText(str(self._octave))
            return

        if self._arp_engine.is_enabled():
            # For ARP mode: release old notes, press new notes
            for key, old_note in list(self._physical_keys_held.items()):
                self._arp_engine.key_release(old_note)

                semitone = KEY_TO_SEMITONE[key]
                new_note = (new_octave + 1) * 12 + semitone

                if 0 <= new_note <= 127:
                    self._physical_keys_held[key] = new_note
                    self._arp_engine.key_press(new_note)
                else:
                    del self._physical_keys_held[key]
                    self._update_key_visual(key, False)
        else:
            # Legacy re-pitch all held notes
            osc_slot = self._target_slot - 1
            for key, old_note in list(self._physical_keys_held.items()):
                self._send_note_off(osc_slot, old_note)

                semitone = KEY_TO_SEMITONE[key]
                new_note = (new_octave + 1) * 12 + semitone

                if 0 <= new_note <= 127:
                    self._physical_keys_held[key] = new_note
                    self._send_note_on(osc_slot, new_note, self._velocity)
                else:
                    del self._physical_keys_held[key]
                    self._update_key_visual(key, False)

        self._octave = new_octave
        self._octave_label.setText(str(self._octave))

    def _update_key_visual(self, qt_key: int, pressed: bool):
        """Update visual state of a key button."""
        if qt_key in self._key_buttons:
            btn = self._key_buttons[qt_key]
            btn.setProperty("pressed", "true" if pressed else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # -------------------------------------------------------------------------
    # Step Grid
    # -------------------------------------------------------------------------

    @staticmethod
    def _note_name(midi_note: int) -> str:
        """Convert MIDI note number to display name (e.g. 60 -> C4)."""
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        name = names[midi_note % 12]
        return f"{name}{octave}"

    def _refresh_step_grid(self):
        """Update step grid cells from engine state."""
        if self._seq_engine is None:
            return

        settings = self._seq_engine.settings
        length = settings.length
        playhead = self._seq_engine.current_step_index
        is_playing = self._seq_engine.is_playing

        for i, cell in enumerate(self._step_cells):
            needs_restyle = False

            if i >= length:
                # Beyond active length — inactive
                new_state = "inactive"
                new_text = ""
            else:
                step = settings.steps[i]
                if step.step_type == StepType.NOTE:
                    new_state = "note"
                    new_text = self._note_name(step.note)
                elif step.step_type == StepType.TIE:
                    new_state = "tie"
                    new_text = "~"
                else:
                    new_state = "rest"
                    new_text = "-"

            # Update step state property
            if cell.property("step_state") != new_state:
                cell.setProperty("step_state", new_state)
                needs_restyle = True

            # Update cursor indicator (recording cursor)
            cursor_val = "true" if (self._seq_recording and i == self._seq_input_cursor and i < length) else "false"
            if cell.property("cursor_here") != cursor_val:
                cell.setProperty("cursor_here", cursor_val)
                needs_restyle = True

            # Update playhead indicator
            playhead_val = "true" if (is_playing and i == playhead and i < length) else "false"
            if cell.property("playhead") != playhead_val:
                cell.setProperty("playhead", playhead_val)
                needs_restyle = True

            cell.setText(new_text)

            if needs_restyle:
                cell.style().unpolish(cell)
                cell.style().polish(cell)

    def _on_step_cell_clicked(self, index: int):
        """Handle click on a step grid cell — move recording cursor there."""
        if self._seq_engine is None:
            return
        if index >= self._seq_engine.settings.length:
            return

        # Enter recording mode if not already
        if not self._seq_recording:
            self.set_seq_recording(True)
            self._seq_rec_btn.setChecked(True)

        self._seq_input_cursor = index
        self._refresh_step_grid()

    # -------------------------------------------------------------------------
    # SEQ Step Recording
    # -------------------------------------------------------------------------

    def _handle_seq_recording_key(self, key: int):
        """
        Handle key press in SEQ recording mode (SH-101 style).

        Key mapping:
            Note keys (A-K row) -> NOTE step with MIDI pitch, advance cursor
            Space               -> REST step, advance cursor
            Tab                 -> TIE step, advance cursor
            Backspace           -> Move cursor back 1 step
            Z/X                 -> Octave shift (still works in recording)
        """
        if self._seq_engine is None:
            return

        # Octave change works in recording mode too
        if key in OCTAVE_KEYS:
            self._handle_octave_change(OCTAVE_KEYS[key])
            return

        # Note key -> NOTE step + audition
        if key in KEY_TO_SEMITONE:
            semitone = KEY_TO_SEMITONE[key]
            midi_note = self._compute_midi_note(semitone)
            if 0 <= midi_note <= 127:
                # Write step directly for immediate grid display
        
                self._seq_engine.settings.steps[self._seq_input_cursor] = SeqStep(
                    step_type=StepType.NOTE, note=midi_note, velocity=self._velocity,
                )
                self._seq_engine.steps_version += 1
                self._advance_input_cursor()
                self._refresh_step_grid()

                # Audition: play note briefly so user hears what was entered
                osc_slot = self._target_slot - 1
                self._send_note_on(osc_slot, midi_note, self._velocity)
                QTimer.singleShot(200, lambda n=midi_note, s=osc_slot: self._send_note_off(s, n))
            return

        # Space -> REST step
        if key == Qt.Key_Space:
    
            self._seq_engine.settings.steps[self._seq_input_cursor] = SeqStep(
                step_type=StepType.REST,
            )
            self._seq_engine.steps_version += 1
            self._advance_input_cursor()
            self._refresh_step_grid()
            return

        # Tab -> TIE step
        if key == Qt.Key_Tab:
    
            self._seq_engine.settings.steps[self._seq_input_cursor] = SeqStep(
                step_type=StepType.TIE,
            )
            self._seq_engine.steps_version += 1
            self._advance_input_cursor()
            self._refresh_step_grid()
            return

        # Backspace -> move cursor back
        if key == Qt.Key_Backspace:
            self._move_input_cursor(-1)
            self._refresh_step_grid()
            return

    # -------------------------------------------------------------------------
    # Show / Hide
    # -------------------------------------------------------------------------

    def showEvent(self, event):
        """Update slot buttons when overlay becomes visible."""
        super().showEvent(event)
        self._update_slot_buttons()

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def closeEvent(self, event):
        """Ensure cleanup on close."""
        self._dismiss()
        super().closeEvent(event)
