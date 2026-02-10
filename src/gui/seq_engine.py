"""
Sequence Engine — SH-101 Style Step Sequencer (Per-Slot)

Data manager for step sequencer state. Note timing is handled entirely
by the SC step engine SynthDef (clock-locked, ±1.3ms jitter).

Python responsibilities:
- Store step data (type, note, velocity, gate)
- Thread-safe command queue for UI edits
- Push data changes to SC via on_data_changed callback
- Snapshot-based UI reads (prevents tearing)

SC responsibilities (step_engine.scd):
- Clock-locked step advancement via PulseCount + BufRd
- Freq/trigger bus writes via ReplaceOut
- Play mode (FWD/REV/PP/RAND) position computation
- SendReply for UI playhead position

Follows ArpEngine patterns:
- Callback-based data propagation (not direct osc_client)
- slot_id is 0-indexed, fixed at construction
"""

from __future__ import annotations

import queue
from typing import Callable, Optional

from src.model.sequencer import SeqSettings, SeqStep, StepType, PlayMode


# Rate presets matching ARP rate labels for UI consistency
SEQ_RATE_LABELS = ["1/32", "1/16", "1/12", "1/8", "1/4", "1/2", "1"]
SEQ_BEATS_PER_STEP = {
    0: 0.125,    # 1/32
    1: 0.25,     # 1/16
    2: 1.0 / 3,  # 1/12
    3: 0.5,      # 1/8
    4: 1.0,      # 1/4
    5: 2.0,      # 1/2
    6: 4.0,      # 1 bar
}
SEQ_DEFAULT_RATE_INDEX = 1  # 1/16 (standard SH-101 default)


class SeqEngine:
    """
    SH-101 style step sequencer data manager (per-slot).

    Note timing is handled by SC's stepEngineSlot SynthDef. This class
    manages step data, processes UI commands, and pushes changes to SC.
    """

    def __init__(self, slot_id: int):
        self._slot_id = slot_id

        # Settings
        self.settings = SeqSettings()

        # Rate (index into SEQ_BEATS_PER_STEP)
        self._rate_index: int = SEQ_DEFAULT_RATE_INDEX

        # Playhead position (updated from SC via step_event, not computed locally)
        self.current_step_index: int = 0

        # Thread-safe edit queue
        self.command_queue: queue.Queue = queue.Queue()

        # Version counter for UI snapshot diffing
        self.steps_version: int = 0

        # Playback state (for UI; actual timing is SC-side)
        self._playing: bool = False

        # Callback for data changes (set by MotionManager to push to SC)
        self.on_data_changed: Optional[Callable] = None

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def slot_id(self) -> int:
        """Target slot (0-indexed, read-only)."""
        return self._slot_id

    @property
    def rate(self) -> float:
        """Current beats per step."""
        return SEQ_BEATS_PER_STEP.get(self._rate_index, 0.25)

    @property
    def rate_index(self) -> int:
        """Current rate index."""
        return self._rate_index

    @property
    def is_playing(self) -> bool:
        """Whether the sequencer is currently playing."""
        return self._playing

    # =========================================================================
    # COMMAND PROCESSING
    # =========================================================================

    def process_commands(self):
        """Process all queued UI commands. Called from QTimer tick."""
        while not self.command_queue.empty():
            try:
                cmd = self.command_queue.get_nowait()
                self._execute_command(cmd)
            except queue.Empty:
                break

    # Commands that mutate data and must notify SC
    MUTATING_COMMANDS = {'SET_STEP', 'SET_LENGTH', 'SET_RATE', 'SET_PLAY_MODE', 'CLEAR_SEQUENCE'}

    def _execute_command(self, cmd: dict):
        """Execute a single command with bounds safety."""
        cmd_type = cmd.get('type')

        if cmd_type == 'SET_STEP':
            idx = max(0, min(cmd['index'], 15))
            self.settings.steps[idx] = SeqStep(
                step_type=cmd['step_type'],
                note=cmd.get('note', 60),
                velocity=cmd.get('velocity', 100),
            )
            self.steps_version += 1

        elif cmd_type == 'SET_LENGTH':
            new_length = max(1, min(cmd['length'], 16))
            self.settings.length = new_length
            if self.current_step_index >= new_length:
                self.current_step_index = new_length - 1
            self.steps_version += 1

        elif cmd_type == 'SET_RATE':
            new_index = max(0, min(cmd['rate_index'], len(SEQ_BEATS_PER_STEP) - 1))
            self._rate_index = new_index
            self.steps_version += 1

        elif cmd_type == 'SET_PLAY_MODE':
            self.settings.play_mode = cmd['play_mode']
            self.steps_version += 1

        elif cmd_type == 'CLEAR_SEQUENCE':
            self.settings.steps = [SeqStep() for _ in range(16)]
            self.settings.length = 16
            self.current_step_index = 0
            self.steps_version += 1

        elif cmd_type == 'TOGGLE_PLAYBACK':
            if self._playing:
                self.stop()
            else:
                self.start()

        if cmd_type in self.MUTATING_COMMANDS and self.on_data_changed is not None:
            self.on_data_changed()

    # =========================================================================
    # TRANSPORT
    # =========================================================================

    def start(self):
        """Mark sequencer as playing. Note timing is SC-side."""
        self._playing = True

    def stop(self):
        """Stop sequencer playback."""
        self._playing = False

    def reset(self):
        """Full reset for mode handover."""
        self.stop()
        self.current_step_index = 0

    # =========================================================================
    # SC PLAYHEAD FEEDBACK
    # =========================================================================

    def update_playhead(self, position: int):
        """Update playhead position from SC step_event SendReply."""
        self.current_step_index = position

    # =========================================================================
    # UI SNAPSHOT (prevents tearing)
    # =========================================================================

    def get_ui_snapshot(self) -> dict:
        """Returns snapshot for UI rendering."""
        return {
            'playhead_index': self.current_step_index,
            'steps_version': self.steps_version,
            'length': self.settings.length,
            'playing': self._playing,
            'rate_index': self._rate_index,
        }

    # =========================================================================
    # COMMAND QUEUE API (UI -> Engine)
    # =========================================================================

    def queue_command(self, command: dict):
        """Thread-safe command queue for UI edits."""
        self.command_queue.put(command)

    def set_rate(self, rate_index: int):
        """Set rate from UI (queued for thread safety)."""
        self.queue_command({'type': 'SET_RATE', 'rate_index': rate_index})

    def set_length(self, length: int):
        """Set sequence length from UI (queued for thread safety)."""
        self.queue_command({'type': 'SET_LENGTH', 'length': length})

    def set_play_mode(self, play_mode: PlayMode):
        """Set play mode from UI (queued for thread safety)."""
        self.queue_command({'type': 'SET_PLAY_MODE', 'play_mode': play_mode})

    def toggle_playback(self):
        """Toggle play/stop from UI (queued for thread safety)."""
        self.queue_command({'type': 'TOGGLE_PLAYBACK'})

    def get_settings(self) -> SeqSettings:
        """Get current sequencer settings."""
        return self.settings
