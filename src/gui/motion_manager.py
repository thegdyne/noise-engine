"""
Motion Manager — Coordinates Arpeggiator and Sequencer per Slot

Each slot has:
- An ArpEngine instance (from ArpSlotManager)
- A SeqEngine instance (created here)
- A per-slot RLock for thread-safe mode transitions

Clock model:
- QTimer fires every TICK_INTERVAL_MS (~10ms) calling on_tick()
- Timer auto-starts when any slot enters SEQ mode
- Timer auto-stops when no slots are in SEQ mode
- BPM is tracked to convert timer intervals to beat durations
"""

from __future__ import annotations

import time
import threading
from typing import Callable, List, Optional

from PyQt5.QtCore import QTimer

from src.model.sequencer import MotionMode
from src.gui.arp_engine import ArpEngine
from src.gui.seq_engine import SeqEngine
from src.utils.logger import logger

# Clock tick interval in milliseconds (~10ms for smooth sequencing)
TICK_INTERVAL_MS = 10


class MotionManager:
    """
    Coordinates Arpeggiator and Sequencer modes per slot.
    Uses per-slot RLocks to prevent race conditions.

    Owns 8 SeqEngine instances. ArpEngine instances are provided
    externally (from ArpSlotManager via KeyboardController).
    """

    def __init__(
        self,
        arp_engines: List[ArpEngine],
        send_note_on: Callable[[int, int, int], None],
        send_note_off: Callable[[int, int], None],
        get_bpm: Optional[Callable[[], float]] = None,
    ):
        """
        Initialize MotionManager.

        Args:
            arp_engines: List of 8 ArpEngine instances (from ArpSlotManager)
            send_note_on: Callback (slot, note, velocity)
            send_note_off: Callback (slot, note)
            get_bpm: Callback returning current BPM (default 120.0)
        """
        self._get_bpm = get_bpm or (lambda: 120.0)
        self._slots: List[dict] = []

        for i in range(8):
            seq = SeqEngine(
                slot_id=i,
                send_note_on=send_note_on,
                send_note_off=send_note_off,
            )
            self._slots.append({
                'lock': threading.RLock(),
                'arp': arp_engines[i],
                'seq': seq,
                'mode': MotionMode.OFF,
                'tick_accumulator': 0.0,
                'pending_mode': None,
            })

        # QTimer-based clock for SEQ tick delivery
        self._clock_timer = QTimer()
        self._clock_timer.setTimerType(1)  # Qt.PreciseTimer
        self._clock_timer.timeout.connect(self._on_clock_tick)
        self._last_tick_time: Optional[float] = None

        logger.info("MotionManager: 8 slots initialized", component="MOTION")

    # =========================================================================
    # CLOCK (QTimer-based)
    # =========================================================================

    def _on_clock_tick(self):
        """QTimer callback — compute beat duration and tick all slots."""
        now = time.monotonic()
        if self._last_tick_time is not None:
            dt_seconds = now - self._last_tick_time
        else:
            dt_seconds = TICK_INTERVAL_MS / 1000.0
        self._last_tick_time = now

        bpm = self._get_bpm()
        if bpm <= 0:
            return
        tick_duration_beats = (bpm / 60.0) * dt_seconds
        self.on_tick(tick_duration_beats)

    def _start_clock(self):
        """Start the clock timer if not already running."""
        if not self._clock_timer.isActive():
            self._last_tick_time = time.monotonic()
            self._clock_timer.start(TICK_INTERVAL_MS)
            logger.debug("MotionManager: clock started", component="MOTION")

    def _stop_clock(self):
        """Stop the clock timer if no slots need it."""
        if self._clock_timer.isActive():
            self._clock_timer.stop()
            self._last_tick_time = None
            logger.debug("MotionManager: clock stopped", component="MOTION")

    def _update_clock_state(self):
        """Start or stop clock based on whether any slot is in SEQ mode."""
        any_seq = any(s['mode'] == MotionMode.SEQ for s in self._slots)
        if any_seq:
            self._start_clock()
        else:
            self._stop_clock()

    def on_tick(self, tick_duration_beats: float):
        """Tick all slots with the given beat duration."""
        for slot in self._slots:
            slot['tick_accumulator'] += tick_duration_beats

            if slot['lock'].acquire(blocking=False):
                try:
                    if slot['pending_mode'] is not None:
                        self._execute_handover(slot, slot['pending_mode'])
                        slot['pending_mode'] = None

                    accumulated = slot['tick_accumulator']
                    slot['tick_accumulator'] = 0.0
                    self._process_slot(slot, accumulated)
                finally:
                    slot['lock'].release()

    def _process_slot(self, slot: dict, tick_duration_beats: float):
        """Process tick for active mode with accumulated time."""
        if slot['mode'] == MotionMode.SEQ:
            slot['seq'].tick(tick_duration_beats)

    # =========================================================================
    # MODE SWITCHING (called from UI thread)
    # =========================================================================

    def set_mode(self, slot_idx: int, new_mode: MotionMode):
        """
        Set mode for a slot. Executes handover immediately since
        the clock runs on the same (UI) thread via QTimer.
        """
        if slot_idx < 0 or slot_idx >= 8:
            return

        slot = self._slots[slot_idx]
        with slot['lock']:
            if slot['mode'] == new_mode:
                return
            self._execute_handover(slot, new_mode)
            slot['pending_mode'] = None
            logger.debug(
                f"MotionManager: slot {slot_idx} mode set: "
                f"{new_mode.name}",
                component="MOTION"
            )
        self._update_clock_state()

    def get_mode(self, slot_idx: int) -> MotionMode:
        """Thread-safe mode query."""
        if slot_idx < 0 or slot_idx >= 8:
            return MotionMode.OFF
        slot = self._slots[slot_idx]
        with slot['lock']:
            return slot['mode']

    def _execute_handover(self, slot: dict, new_mode: MotionMode):
        """
        Atomic mode switch (called from clock thread with lock held):
        1. Stop old mode (panic + reset)
        2. Update mode
        3. Start new mode if applicable
        """
        old_mode = slot['mode']

        # Stop old mode
        if old_mode == MotionMode.SEQ:
            slot['seq'].panic()
            slot['seq'].reset_phase()
        elif old_mode == MotionMode.ARP:
            slot['arp'].teardown()

        # Swap
        slot['mode'] = new_mode

        # Start new mode
        if new_mode == MotionMode.SEQ:
            slot['seq'].start()

        logger.debug(
            f"MotionManager: handover executed {old_mode.name} -> {new_mode.name}",
            component="MOTION"
        )

    # =========================================================================
    # SEQ ENGINE ACCESS
    # =========================================================================

    def get_seq_engine(self, slot_idx: int) -> Optional[SeqEngine]:
        """Get sequencer engine for a slot (0-indexed)."""
        if 0 <= slot_idx < 8:
            return self._slots[slot_idx]['seq']
        return None

    def get_slot_info(self, slot_idx: int) -> Optional[dict]:
        """Get slot info snapshot for UI."""
        if slot_idx < 0 or slot_idx >= 8:
            return None
        slot = self._slots[slot_idx]
        with slot['lock']:
            return {
                'mode': slot['mode'],
                'seq_snapshot': slot['seq'].get_ui_snapshot(),
            }

    # =========================================================================
    # PANIC / RESET
    # =========================================================================

    def panic_slot(self, slot_idx: int):
        """Panic a single slot (silence both engines)."""
        if slot_idx < 0 or slot_idx >= 8:
            return
        slot = self._slots[slot_idx]
        with slot['lock']:
            slot['seq'].panic()
            slot['arp'].teardown()
            slot['mode'] = MotionMode.OFF
            slot['pending_mode'] = None
        self._update_clock_state()

    def panic_all(self):
        """Panic all slots."""
        for i in range(8):
            self.panic_slot(i)
        self._update_clock_state()
        logger.info("MotionManager: all slots panic", component="MOTION")
