"""
Sequence Engine — SH-101 Style Step Sequencer (Per-Slot)

Implements a monophonic step sequencer with:
- Accumulator-based timing (never drops clock time)
- State machine: NOTE / REST / TIE transitions
- Thread-safe command queue for UI edits
- Snapshot-based UI reads (prevents tearing)
- Slot-scoped OSC panic (only silences own slot)

Key invariant: current_sounding_note is the SINGLE SOURCE OF TRUTH
for whether a note is playing. Never look back at the step list.

Follows ArpEngine patterns:
- Callback-based OSC emission (not direct osc_client)
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
    SH-101 style step sequencer engine (per-slot).

    Each engine targets exactly one slot. UI edits are queued via
    command_queue and processed on the clock thread to avoid races.
    """

    def __init__(
        self,
        slot_id: int,
        send_note_on: Callable[[int, int, int], None],
        send_note_off: Callable[[int, int], None],
    ):
        """
        Initialize sequencer engine for a single slot.

        Args:
            slot_id: Target slot (0-indexed, fixed for lifetime)
            send_note_on: Callback (slot, note, velocity)
            send_note_off: Callback (slot, note)
        """
        self._slot_id = slot_id
        self._send_note_on = send_note_on
        self._send_note_off = send_note_off

        # Timing state
        self.phase: float = 0.0
        self.current_step_index: int = 0

        # Audio state — SINGLE SOURCE OF TRUTH
        self.current_sounding_note: Optional[int] = None

        # Settings
        self.settings = SeqSettings()

        # Rate (index into SEQ_BEATS_PER_STEP)
        self._rate_index: int = SEQ_DEFAULT_RATE_INDEX

        # Thread-safe edit queue
        self.command_queue: queue.Queue = queue.Queue()

        # Version counter for UI snapshot diffing
        self.steps_version: int = 0

        # Playback state
        self._playing: bool = False

        # Ping-pong direction: True = forward, False = reverse
        self._pingpong_forward: bool = True

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
    # TICK (called by MotionManager from clock thread)
    # =========================================================================

    def tick(self, tick_duration_beats: float):
        """
        Advance sequencer by tick_duration_beats.

        Accumulator pattern: handles variable tick rates and
        multiple steps per tick if rate is very fast.
        """
        if not self._playing:
            return

        # Process any pending UI commands first
        self._process_commands()

        # Accumulate time
        self.phase += tick_duration_beats

        # Advance through steps
        rate = self.rate
        while self.phase >= rate:
            self.phase -= rate
            self._advance_step()

    # =========================================================================
    # STEP ADVANCEMENT
    # =========================================================================

    def _advance_step(self):
        """Move to next step based on play mode and trigger appropriate action."""
        length = self.settings.length

        if self.settings.play_mode == PlayMode.FORWARD:
            self.current_step_index = (self.current_step_index + 1) % length

        elif self.settings.play_mode == PlayMode.REVERSE:
            self.current_step_index = (self.current_step_index - 1) % length

        elif self.settings.play_mode == PlayMode.PINGPONG:
            if length <= 1:
                self.current_step_index = 0
            else:
                if self._pingpong_forward:
                    self.current_step_index += 1
                    if self.current_step_index >= length - 1:
                        self.current_step_index = length - 1
                        self._pingpong_forward = False
                else:
                    self.current_step_index -= 1
                    if self.current_step_index <= 0:
                        self.current_step_index = 0
                        self._pingpong_forward = True

        elif self.settings.play_mode == PlayMode.RANDOM:
            import random
            self.current_step_index = random.randint(0, length - 1)

        # Execute the step at current index
        step = self.settings.steps[self.current_step_index]
        self._execute_step(step)

    def _execute_step(self, step: SeqStep):
        """
        State machine transition based on step type.

        Transition table:
          Any       + NOTE(P)  -> panic, note_on(P), sounding=P
          Any       + REST     -> panic, sounding=None
          None      + TIE      -> no-op (silence continues)
          Pitch(P)  + TIE      -> no-op (sustain continues)
        """
        if step.step_type == StepType.NOTE:
            self.panic()
            self._note_on(step.note, step.velocity)
            self.current_sounding_note = step.note

        elif step.step_type == StepType.REST:
            self.panic()

        elif step.step_type == StepType.TIE:
            # Sustain if playing, silence if not — no action needed.
            # current_sounding_note unchanged (handles wrap case).
            pass

    # =========================================================================
    # OSC EMISSION (slot-scoped)
    # =========================================================================

    def _note_on(self, note: int, velocity: int):
        """Emit note-on to this engine's slot."""
        self._send_note_on(self._slot_id, note, velocity)

    def _note_off(self, note: int):
        """Emit note-off to this engine's slot."""
        self._send_note_off(self._slot_id, note)

    def panic(self):
        """
        Slot-scoped note off. Only silences THIS slot.

        Clears current_sounding_note after sending note-off.
        """
        if self.current_sounding_note is not None:
            self._note_off(self.current_sounding_note)
            self.current_sounding_note = None

    # =========================================================================
    # TRANSPORT
    # =========================================================================

    def start(self):
        """Start sequencer playback."""
        self._playing = True
        # Execute first step immediately
        if self.settings.length > 0:
            step = self.settings.steps[self.current_step_index]
            self._execute_step(step)

    def stop(self):
        """Stop sequencer playback and silence."""
        self._playing = False
        self.panic()

    def reset_phase(self):
        """Reset timing state for mode handover."""
        self.phase = 0.0
        self.current_step_index = 0
        self._pingpong_forward = True

    def reset(self):
        """Full reset including audio state."""
        self.stop()
        self.reset_phase()

    # =========================================================================
    # UI SNAPSHOT (prevents tearing)
    # =========================================================================

    def get_ui_snapshot(self) -> dict:
        """
        Returns snapshot for UI rendering.
        Prevents tearing from concurrent access.
        """
        return {
            'playhead_index': self.current_step_index,
            'active_note': self.current_sounding_note,
            'steps_version': self.steps_version,
            'length': self.settings.length,
            'playing': self._playing,
            'rate_index': self._rate_index,
        }

    # =========================================================================
    # THREAD-SAFE COMMAND QUEUE (UI -> Engine)
    # =========================================================================

    def queue_command(self, command: dict):
        """Thread-safe command queue for UI edits."""
        self.command_queue.put(command)

    def _process_commands(self):
        """Process all queued commands (called from clock thread before tick)."""
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
            self._pingpong_forward = True
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
    # SETTINGS ACCESS
    # =========================================================================

    def get_settings(self) -> SeqSettings:
        """Get current sequencer settings."""
        return self.settings

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
