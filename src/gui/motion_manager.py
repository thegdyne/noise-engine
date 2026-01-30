"""
Motion Manager — Coordinates Arpeggiator and Sequencer per Slot

Prevents race conditions between audio clock thread and UI thread
during mode switching. Each slot has:
- An ArpEngine instance (from ArpSlotManager)
- A SeqEngine instance (created here)
- A per-slot RLock for thread-safe mode transitions
- A tick_accumulator to prevent dropped time during lock contention

Threading model:
- Clock thread: calls on_tick() with try-lock (never blocks)
- UI thread: calls set_mode() which queues pending_mode (with lock)
- Mode changes execute atomically on the clock thread

P0 CRITICAL: The clock thread never blocks waiting for UI.
If try-lock fails, time accumulates in tick_accumulator and is
processed on the next successful lock acquisition.
"""

from __future__ import annotations

import threading
from typing import Callable, List, Optional

from src.model.sequencer import MotionMode
from src.gui.arp_engine import ArpEngine
from src.gui.seq_engine import SeqEngine
from src.utils.logger import logger


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
    ):
        """
        Initialize MotionManager.

        Args:
            arp_engines: List of 8 ArpEngine instances (from ArpSlotManager)
            send_note_on: Callback (slot, note, velocity)
            send_note_off: Callback (slot, note)
        """
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

        logger.info("MotionManager: 8 slots initialized", component="MOTION")

    # =========================================================================
    # CLOCK TICK (called from audio/clock thread)
    # =========================================================================

    def on_tick(self, tick_duration_beats: float):
        """
        Called by Master Clock Thread.

        P0 CRITICAL: Never drop time. If lock fails, accumulate beats
        and apply them on the next successful tick.
        """
        for slot in self._slots:
            # Always accumulate time (even if lock fails)
            slot['tick_accumulator'] += tick_duration_beats

            # Try non-blocking acquire
            if slot['lock'].acquire(blocking=False):
                try:
                    # Process any pending mode change first
                    if slot['pending_mode'] is not None:
                        self._execute_handover(slot, slot['pending_mode'])
                        slot['pending_mode'] = None

                    # Process accumulated time
                    accumulated = slot['tick_accumulator']
                    slot['tick_accumulator'] = 0.0
                    self._process_slot(slot, accumulated)
                finally:
                    slot['lock'].release()
            # If lock fails, time accumulates — processed next tick

    def _process_slot(self, slot: dict, tick_duration_beats: float):
        """Process tick for active mode with accumulated time."""
        if slot['mode'] == MotionMode.SEQ:
            slot['seq'].tick(tick_duration_beats)
        # ARP ticks are handled by ArpEngine's own timer/clock mechanism

    # =========================================================================
    # MODE SWITCHING (called from UI thread)
    # =========================================================================

    def set_mode(self, slot_idx: int, new_mode: MotionMode):
        """
        Queue a mode change for a slot (called from UI thread).

        P0 CRITICAL: Don't block waiting for clock. Queue the mode change
        and let the clock thread execute it atomically.
        """
        if slot_idx < 0 or slot_idx >= 8:
            return

        slot = self._slots[slot_idx]
        with slot['lock']:
            if slot['mode'] == new_mode:
                return
            slot['pending_mode'] = new_mode
            logger.debug(
                f"MotionManager: slot {slot_idx} mode change queued: "
                f"{slot['mode'].name} -> {new_mode.name}",
                component="MOTION"
            )

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

    def panic_all(self):
        """Panic all slots."""
        for i in range(8):
            self.panic_slot(i)
        logger.info("MotionManager: all slots panic", component="MOTION")
