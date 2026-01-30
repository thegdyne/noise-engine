"""
ArpSlotManager — Per-Slot ARP Engine Manager (PER_SLOT_ARP_SPEC v1.2.1)

Owns 8 ArpEngine instances (one per generator slot).
Engines are created eagerly at startup and never removed.
reset_slot() resets in-place; engines[n] is never None.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from .arp_engine import ArpEngine
from src.utils.logger import logger


class ArpSlotManager:
    """
    Manages per-slot ARP engines.

    Slot numbering: 0-indexed internally (matches OSC), 1-indexed in UI.
    All public methods use 0-indexed slot IDs.
    """

    def __init__(
        self,
        send_note_on: Callable[[int, int, int], None],
        send_note_off: Callable[[int, int], None],
        send_all_notes_off: Callable[[int], None],
        get_velocity: Callable[[], int],
        get_bpm: Callable[[], float],
    ):
        self._send_note_on = send_note_on
        self._send_note_off = send_note_off
        self._send_all_notes_off = send_all_notes_off
        self._get_velocity = get_velocity
        self._get_bpm = get_bpm

        # Eagerly create all 8 engines (invariant: never None, never removed)
        self.engines: List[ArpEngine] = []
        for slot_id in range(8):
            engine = ArpEngine(
                slot_id=slot_id,
                send_note_on=send_note_on,
                send_note_off=send_note_off,
                get_velocity=get_velocity,
                get_bpm=get_bpm,
            )
            self.engines.append(engine)

        logger.info("ArpSlotManager: 8 engines created", component="ARP")

    def get_engine(self, slot: int) -> ArpEngine:
        """Get engine for slot (0-indexed). Always returns a valid engine."""
        return self.engines[slot]

    def reset_slot(self, slot: int):
        """Reset a single slot's engine in-place. Engine object remains."""
        engine = self.engines[slot]
        engine.teardown()
        logger.debug(f"ArpSlotManager: reset slot {slot}", component="ARP")

    def reset_all(self):
        """Reset all 8 engines in-place."""
        for slot in range(8):
            self.engines[slot].teardown()
        logger.info("ArpSlotManager: all engines reset", component="ARP")

    def all_notes_off(self):
        """Panic: reset all engines and send all-notes-off to all slots."""
        self.reset_all()
        for slot in range(8):
            self._send_all_notes_off(slot)
        logger.info("ArpSlotManager: all-notes-off (panic)", component="ARP")

    def get_active_holds(self) -> List[int]:
        """Get list of slot IDs (0-indexed) with ARP+HOLD active."""
        return [slot for slot, engine in enumerate(self.engines) if engine.has_hold]

    def on_bpm_changed(self, bpm: float):
        """Forward BPM change to all engines (no-op on IDLE engines)."""
        for engine in self.engines:
            engine.notify_bpm_changed(bpm)
