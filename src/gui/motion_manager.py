"""
Motion Manager — Coordinates Arpeggiator and Sequencer per Slot

Each slot has:
- An ArpEngine instance (from ArpSlotManager)
- A SeqEngine instance (created here)
- A per-slot RLock for thread-safe mode transitions

Clock model:
- SC fabric ticks arrive via OSC for ARP master_tick() delivery
- QTimer fires every TICK_INTERVAL_MS for SEQ sync boundary detection
  and command queue processing (note timing is SC-side)
- Timer auto-starts when any slot enters SEQ mode
- Timer auto-stops when no slots need it

Sync model:
- Global sync phase accumulates beats and wraps at SYNC_QUANTUM_BEATS (1 bar = 4 beats)
- First slot to enter SEQ activates SC immediately and resets the sync phase
- Subsequent slots entering SEQ wait for the next bar downbeat before SC activation
- This keeps all slot sequencers aligned to the same bar grid

ARP clock integration (unified with SC fabric):
- SC masterClock broadcasts fabric ticks via SendReply → OSCdef → Python OSC
- on_fabric_tick() maps fabric indices to ARP rate indices
- ARP promotes from fallback timer to master clock for grid-locked stepping
- All ARP rates including 1/12 (triplet) have fabric matches
"""

from __future__ import annotations

import time
import threading
from typing import Callable, List, Optional

from PyQt5.QtCore import QTimer

from src.model.sequencer import MotionMode, StepType
from src.gui.arp_engine import ArpEngine, euclidean_hit
from src.gui.seq_engine import SeqEngine
from src.config import FABRIC_IDX_TO_ARP_RATE, ARP_RATE_TO_FABRIC_IDX, OSC_PATHS, EUCLID_MAX_N
from src.utils.logger import logger

# Clock tick interval in milliseconds (~10ms for smooth sequencing)
TICK_INTERVAL_MS = 10

# Play mode name → SC integer (single source of truth for both push paths)
_PLAY_MODE_VAL = {'FORWARD': 0, 'REVERSE': 1, 'PINGPONG': 2, 'RANDOM': 3}

# Global sync resolution: 1 bar = 4 beats
# New SEQ slots wait for the next bar downbeat before starting playback.
SYNC_QUANTUM_BEATS = 4.0


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
        get_bpm: Optional[Callable[[], float]] = None,
        send_osc: Optional[Callable] = None,
    ):
        """
        Initialize MotionManager.

        Args:
            arp_engines: List of 8 ArpEngine instances (from ArpSlotManager)
            get_bpm: Callback returning current BPM (default 120.0)
            send_osc: Callback (path, *args) for sending OSC to SC step engine
        """
        self._get_bpm = get_bpm or (lambda: 120.0)
        self._send_osc = send_osc
        self._slots: List[dict] = []

        for i in range(8):
            seq = SeqEngine(slot_id=i)
            self._slots.append({
                'lock': threading.RLock(),
                'arp': arp_engines[i],
                'seq': seq,
                'mode': MotionMode.OFF,
                'pending_mode': None,
                'pending_seq_start': False,
                'slot_idx': i,
                'last_seq_rate': None,
                'last_seq_play_mode': None,
            })

        # QTimer-based clock for SEQ tick delivery
        self._clock_timer = QTimer()
        self._clock_timer.setTimerType(1)  # Qt.PreciseTimer
        self._clock_timer.timeout.connect(self._on_clock_tick)
        self._last_tick_time: Optional[float] = None

        # Global sync phase — accumulates beats, fires sync pulse every SYNC_QUANTUM_BEATS
        self._sync_phase: float = 0.0

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
        """Start or stop clock based on whether any slot needs ticks.

        QTimer only needed for SEQ (continuous delta-beat accumulator).
        ARP is driven by SC fabric ticks via on_fabric_tick().
        """
        any_active = any(
            s['mode'] == MotionMode.SEQ or s['pending_seq_start']
            for s in self._slots
        )
        if any_active:
            self._start_clock()
        else:
            self._stop_clock()

    def on_tick(self, tick_duration_beats: float):
        """Tick for SEQ sync boundaries and command queue processing.

        Note timing is SC-side. This only handles:
        - Sync boundary detection for deferred SEQ starts
        - Command queue draining for pending UI edits
        """
        # Check if a sync boundary is crossed this tick
        self._sync_phase += tick_duration_beats
        sync_crossed = False
        if self._sync_phase >= SYNC_QUANTUM_BEATS:
            sync_crossed = True
            self._sync_phase %= SYNC_QUANTUM_BEATS

        for slot in self._slots:
            if slot['lock'].acquire(blocking=False):
                try:
                    if slot['pending_mode'] is not None:
                        self._execute_handover(slot, slot['pending_mode'])
                        slot['pending_mode'] = None

                    # Activate pending SEQ slots on sync boundary
                    if sync_crossed and slot['pending_seq_start']:
                        slot['pending_seq_start'] = False
                        self._send_step_mode(slot['slot_idx'], MotionMode.SEQ)
                        slot['seq'].start()

                    # Drain command queue (UI edits → SC data push)
                    if slot['mode'] == MotionMode.SEQ:
                        slot['seq'].process_commands()
                finally:
                    slot['lock'].release()

    # =========================================================================
    # FABRIC TICK (from SC clock via OSC)
    # =========================================================================

    def on_fabric_tick(self, fabric_idx: int):
        """Handle clock fabric tick from SC. Route to matching ARP slots.

        Uses a short lock timeout (5ms) instead of blocking=False to
        prevent silently dropped ticks under UI stress.
        """
        arp_rate = FABRIC_IDX_TO_ARP_RATE.get(fabric_idx)
        now_ms = time.monotonic() * 1000.0

        for slot in self._slots:
            if slot['lock'].acquire(timeout=0.005):
                try:
                    # RST for ARP + SEQ (SC resetTrig is mode-agnostic)
                    if slot['mode'] in (MotionMode.ARP, MotionMode.SEQ):
                        if slot['arp'].runtime.rst_fabric_idx == fabric_idx:
                            slot['arp'].reset_on_tick(now_ms)
                            if self._send_osc is not None:
                                self._send_osc(OSC_PATHS['step_reset'], [slot['slot_idx']])

                    # ARP master tick remains ARP-only
                    if slot['mode'] == MotionMode.ARP:
                        if arp_rate is not None:
                            slot['arp'].master_tick(arp_rate, now_ms)
                finally:
                    slot['lock'].release()

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
        3. Start new mode if applicable (SEQ waits for sync boundary)
        4. Send step mode OSC to SC step engine
        """
        old_mode = slot['mode']
        slot_idx = slot['slot_idx']

        # Stop old mode
        if old_mode == MotionMode.SEQ:
            slot['seq'].on_data_changed = None
            slot['seq'].reset()
            slot['pending_seq_start'] = False
        elif old_mode == MotionMode.ARP:
            # Clear SC step engine callback
            slot['arp'].on_notes_changed = None
            # Only teardown ARP when switching TO another active mode (SEQ).
            # ARP→OFF is handled by toggle_arp(False) which preserves settings.
            if new_mode == MotionMode.SEQ:
                # Preserve RST state across teardown (RST is slot-level, not mode-level)
                saved_rst_idx = slot['arp'].runtime.rst_fabric_idx
                saved_rst_count = slot['arp'].runtime.rst_fired_count
                slot['arp'].teardown()
                slot['arp'].runtime.rst_fabric_idx = saved_rst_idx
                slot['arp'].runtime.rst_fired_count = saved_rst_count

        # Swap
        slot['mode'] = new_mode

        # Start new mode
        if new_mode == MotionMode.SEQ:
            # Install callback so SEQ data changes propagate to SC step engine
            idx = slot['slot_idx']
            slot['seq'].on_data_changed = lambda i=idx: self._on_seq_data_changed(i)
            # Push SEQ data to SC step engine (buffer, rate, play mode)
            self._push_seq_to_sc(slot, reset=1)

            # Multi-slot sync: first SEQ activates SC immediately,
            # subsequent SEQ slots defer SC activation to next bar downbeat.
            any_other_seq = any(
                s['mode'] == MotionMode.SEQ and s is not slot
                for s in self._slots
            )
            if any_other_seq:
                slot['pending_seq_start'] = True
                # Don't send step mode yet — SC stays in mode=0 until sync
            else:
                self._sync_phase = 0.0
                self._send_step_mode(slot_idx, new_mode)
                slot['seq'].start()

        elif new_mode == MotionMode.ARP:
            # Send step mode to SC (ARP activates immediately)
            self._send_step_mode(slot_idx, new_mode)
            # Install callback so ARP note changes propagate to SC step engine
            idx = slot['slot_idx']
            slot['arp'].on_notes_changed = lambda i=idx: self.push_arp_notes(i)
            # Push ARP notes to SC step engine
            self._push_arp_notes_to_sc(slot)

        else:
            # OFF — tell SC to deactivate step engine
            self._send_step_mode(slot_idx, new_mode)

        logger.debug(
            f"MotionManager: handover executed {old_mode.name} -> {new_mode.name}",
            component="MOTION"
        )

    # =========================================================================
    # SC STEP ENGINE COMMUNICATION
    # =========================================================================

    def _send_step_mode(self, slot_idx: int, mode: MotionMode):
        """Send step mode to SC step engine."""
        if self._send_osc is None:
            return
        mode_val = {MotionMode.OFF: 0, MotionMode.ARP: 1, MotionMode.SEQ: 2}.get(mode, 0)
        self._send_osc(OSC_PATHS['gen_step_mode'], [slot_idx + 1, mode_val])

    def _push_arp_notes_to_sc(self, slot: dict):
        """Push ARP expanded note list and rate to SC step engine.

        When Euclidean is enabled, sends arp_set_bulk with NOTE/REST frames
        so SC does the gating (no Python-time scheduling). Otherwise sends
        the simple arp_set_notes list.
        """
        if self._send_osc is None:
            return
        slot_idx = slot['slot_idx']
        arp: ArpEngine = slot['arp']

        # Send rate as fabric index
        rate_idx = arp.settings.rate_index
        fabric_idx = ARP_RATE_TO_FABRIC_IDX.get(rate_idx, 6)
        self._send_osc(OSC_PATHS['step_set_rate'], [slot_idx, fabric_idx])

        expanded = arp._get_expanded_list()

        if arp.settings.euclid_enabled and expanded:
            # Build Euclidean NOTE/REST buffer (N clamped to SC buffer max)
            n = max(1, min(EUCLID_MAX_N, arp.settings.euclid_n))
            k = max(0, min(n, arp.settings.euclid_k))
            rot = max(0, min(n - 1, arp.settings.euclid_rot)) if n > 1 else 0
            step_count = n

            payload = [slot_idx, step_count]
            note_idx = 0
            for i in range(step_count):
                if euclidean_hit(i, n, k, rot):
                    note = expanded[note_idx % len(expanded)]
                    payload += [0, note, 127, 1.0]  # NOTE
                    note_idx += 1
                else:
                    payload += [1, 60, 0, 0.0]  # REST
            self._send_osc(OSC_PATHS['arp_set_bulk'], payload)
        else:
            # Simple note list (empty = clear on SC side)
            self._send_osc(OSC_PATHS['arp_set_notes'], [slot_idx] + expanded)

    def _push_seq_to_sc(self, slot: dict, reset: int = 0):
        """Push SEQ step data, rate, and play mode to SC step engine.

        Args:
            slot: Slot dict with seq engine
            reset: 1 = reset playhead to step 0, 0 = preserve position.
                   Only handover (mode entry) passes reset=1.

        Note: step_set_rate fires \\resetTrig on SC side, so only call
        this on mode entry / preset load — NOT on every step edit.
        Use _push_seq_bulk_only for step data updates during playback.
        """
        if self._send_osc is None:
            return
        slot_idx = slot['slot_idx']
        seq: SeqEngine = slot['seq']

        # Send rate as fabric index (SC fires resetTrig on rate change)
        rate_idx = seq.rate_index
        fabric_idx = ARP_RATE_TO_FABRIC_IDX.get(rate_idx, 6)
        self._send_osc(OSC_PATHS['step_set_rate'], [slot_idx, fabric_idx])
        slot['last_seq_rate'] = rate_idx

        # Send play mode
        play_mode_val = _PLAY_MODE_VAL.get(seq.settings.play_mode.name, 0)
        self._send_osc(OSC_PATHS['seq_set_play_mode'], [slot_idx, play_mode_val])
        slot['last_seq_play_mode'] = seq.settings.play_mode.name

        # Send bulk step data
        self._push_seq_bulk_only(slot, reset)

    def _push_seq_bulk_only(self, slot: dict, reset: int = 0):
        """Push only SEQ step buffer data to SC (no rate/play_mode).

        Used by _on_seq_data_changed to avoid step_set_rate which
        fires \\resetTrig on SC side — step edits must not reset phase.
        """
        if self._send_osc is None:
            return
        slot_idx = slot['slot_idx']
        seq: SeqEngine = slot['seq']

        # Send bulk step data: [slot, length, reset, type1, note1, vel1, gate1, ...]
        length = seq.settings.length
        data = [slot_idx, length, reset]
        for step in seq.settings.steps[:length]:
            step_type_val = {StepType.NOTE: 0, StepType.REST: 1, StepType.TIE: 2}.get(step.step_type, 1)
            gate = float(getattr(step, 'gate', 1.0))
            data.extend([step_type_val, step.note, step.velocity, gate])
        self._send_osc(OSC_PATHS['seq_set_bulk'], data)

    def push_arp_notes(self, slot_idx: int):
        """Public API: push current ARP notes to SC (called on note change)."""
        if slot_idx < 0 or slot_idx >= 8:
            return
        slot = self._slots[slot_idx]
        if slot['mode'] == MotionMode.ARP:
            self._push_arp_notes_to_sc(slot)

    def _on_seq_data_changed(self, slot_idx: int):
        """Callback from SeqEngine when data changes during playback.

        Sends bulk buffer data every time. Only sends rate/play_mode
        when they actually change — step_set_rate fires \\resetTrig on SC
        side, so resending it on every step edit would cause phase glitches.
        """
        if self._send_osc is None:
            return
        if slot_idx < 0 or slot_idx >= 8:
            return
        slot = self._slots[slot_idx]
        if slot['mode'] != MotionMode.SEQ:
            return

        seq: SeqEngine = slot['seq']

        # Check if rate changed (step_set_rate fires resetTrig — only send when needed)
        cur_rate = seq.rate_index
        if slot['last_seq_rate'] != cur_rate:
            slot['last_seq_rate'] = cur_rate
            fabric_idx = ARP_RATE_TO_FABRIC_IDX.get(cur_rate, 6)
            self._send_osc(OSC_PATHS['step_set_rate'], [slot_idx, fabric_idx])

        # Check if play mode changed
        cur_pm = seq.settings.play_mode.name
        if slot['last_seq_play_mode'] != cur_pm:
            slot['last_seq_play_mode'] = cur_pm
            play_mode_val = {
                'FORWARD': 0, 'REVERSE': 1, 'PINGPONG': 2, 'RANDOM': 3
            }.get(cur_pm, 0)
            self._send_osc(OSC_PATHS['seq_set_play_mode'], [slot_idx, play_mode_val])

        # Always push step buffer data (no resetTrig)
        self._push_seq_bulk_only(slot)

    def push_seq_data(self, slot_idx: int):
        """Public API: push current SEQ data to SC (called on preset load/paste)."""
        if slot_idx < 0 or slot_idx >= 8:
            return
        slot = self._slots[slot_idx]
        if slot['mode'] == MotionMode.SEQ:
            self._push_seq_to_sc(slot)

    # =========================================================================
    # SC STEP EVENT FEEDBACK
    # =========================================================================

    def on_step_event(self, slot_idx: int, position: int):
        """Handle step event from SC SendReply — update SEQ playhead."""
        if slot_idx < 0 or slot_idx >= 8:
            return
        slot = self._slots[slot_idx]
        if slot['mode'] == MotionMode.SEQ:
            slot['seq'].update_playhead(position)

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
            slot['seq'].stop()
            slot['arp'].teardown()
            slot['mode'] = MotionMode.OFF
            slot['pending_mode'] = None
            slot['pending_seq_start'] = False
        self._update_clock_state()

    def panic_all(self):
        """Panic all slots."""
        for i in range(8):
            self.panic_slot(i)
        self._update_clock_state()
        logger.info("MotionManager: all slots panic", component="MOTION")
