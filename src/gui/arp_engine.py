"""
Arpeggiator Engine for Keyboard Overlay

Implements the ARP specification v1.7 with:
- Serialized event queue for thread-safe operation
- Master clock integration with fallback timer
- Pattern generation (UP, DOWN, UPDOWN, RANDOM, ORDER)
- Hold/latch functionality
- Velocity tracking per note

Key invariants:
- Monophonic per target: at most one ARP note on per target at any time
- No stuck notes: all notes turned off on disable/dismiss/empty set
- Deterministic: PRNG uses xorshift32, order tracking for ORDER pattern
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QTimer


# =============================================================================
# ENUMERATIONS
# =============================================================================

class ArpPattern(Enum):
    """Arpeggiator pattern types."""
    UP = auto()
    DOWN = auto()
    UPDOWN = auto()
    RANDOM = auto()
    ORDER = auto()


class ClockMode(Enum):
    """ARP clock source mode."""
    STOPPED = auto()  # ARP disabled, no stepping
    AUTO = auto()     # Fallback timer, promotes to MASTER on valid ticks
    MASTER = auto()   # Master clock ticks only


class ArpState(Enum):
    """ARP state machine states."""
    DISABLED = auto()
    ENABLED_IDLE = auto()
    ENABLED_PLAYING = auto()


# =============================================================================
# RATE CONFIGURATION
# =============================================================================

# Rate labels for UI display (index matches rateIndex)
ARP_RATE_LABELS = ["1/32", "1/16", "1/12", "1/8", "1/4", "1/2", "1"]

# Beats per step for each rate index
ARP_BEATS_PER_STEP = {
    0: 0.125,    # 1/32
    1: 0.25,     # 1/16
    2: 1.0 / 3,  # 1/12
    3: 0.5,      # 1/8
    4: 1.0,      # 1/4
    5: 2.0,      # 1/2
    6: 4.0,      # 1 bar (4 beats)
}

# Default ARP settings
ARP_DEFAULT_RATE_INDEX = 3  # 1/8
ARP_DEFAULT_PATTERN = ArpPattern.UP
ARP_DEFAULT_OCTAVES = 1
ARP_DEFAULT_VELOCITY = 64

# Timing constants
PROMOTION_SUPPRESS_WINDOW_MS = 5.0
LIVENESS_TIMEOUT_MULTIPLIER = 2.5
LIVENESS_POST_INTERVAL_MIN_MS = 25.0
LIVENESS_POST_INTERVAL_MAX_MS = 100.0
LIVENESS_POST_INTERVAL_FACTOR = 0.4


# =============================================================================
# PRNG - XORSHIFT32
# =============================================================================

class XorShift32:
    """
    xorshift32 PRNG as specified.
    State must never be 0; if 0 then use 0x6D2B79F5.
    """
    DEFAULT_SEED = 0x6D2B79F5

    def __init__(self, seed: int = 0):
        if seed == 0:
            seed = self.DEFAULT_SEED
        self.state = seed & 0xFFFFFFFF

    def next_uint32(self) -> int:
        """Generate next random uint32."""
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17)
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x
        return x

    def choice(self, n: int) -> int:
        """
        Uniform choice over [0, n) using rejection sampling.
        Requires n >= 1.
        """
        if n <= 0:
            raise ValueError("n must be >= 1")
        if n == 1:
            return 0

        # Compute limit for unbiased sampling
        # limit = floor(2^32 / n) * n
        limit = (0x100000000 // n) * n

        while True:
            r = self.next_uint32()
            if r < limit:
                return r % n


# =============================================================================
# EVENT TYPES
# =============================================================================

class ArpEventType(Enum):
    """Types of events processed by the ARP event queue."""
    KEY_PRESS = auto()
    KEY_RELEASE = auto()
    ARP_TOGGLE = auto()
    HOLD_TOGGLE = auto()
    RATE_CHANGE = auto()
    PATTERN_CHANGE = auto()
    OCTAVES_CHANGE = auto()
    TARGET_CHANGE = auto()
    BPM_CHANGE = auto()
    MASTER_TICK = auto()
    FALLBACK_FIRE = auto()
    LIVENESS_CHECK = auto()
    TEARDOWN = auto()


@dataclass
class ArpEvent:
    """Event to be processed by the ARP engine."""
    event_type: ArpEventType
    data: dict = field(default_factory=dict)
    timestamp_ms: float = 0.0


# =============================================================================
# ARP SETTINGS
# =============================================================================

@dataclass
class ArpSettings:
    """User-configurable ARP settings (session-only, reset on overlay open)."""
    enabled: bool = False
    rate_index: int = ARP_DEFAULT_RATE_INDEX
    pattern: ArpPattern = ARP_DEFAULT_PATTERN
    octaves: int = ARP_DEFAULT_OCTAVES
    hold: bool = False


# =============================================================================
# ARP RUNTIME STATE
# =============================================================================

@dataclass
class ArpRuntime:
    """Runtime state for ARP playback."""
    # Physical held notes
    physical_held: Set[int] = field(default_factory=set)
    physical_order: List[int] = field(default_factory=list)

    # Latched notes (hold mode)
    latched: Set[int] = field(default_factory=set)
    latched_order: List[int] = field(default_factory=list)

    # Velocity tracking
    note_velocity: Dict[int, int] = field(default_factory=dict)

    # PRNG state
    rng_seed: int = 0
    prng: Optional[XorShift32] = None

    # Playback state
    current_step_index: int = 0
    last_played_note: Optional[int] = None
    last_played_targets: Set[int] = field(default_factory=set)

    # Clock/timing
    clock_mode: ClockMode = ClockMode.STOPPED
    last_master_tick_time_by_rate: Dict[int, float] = field(default_factory=dict)
    last_eligible_master_tick_time: Optional[float] = None
    last_arp_step_time: Optional[float] = None
    fallback_timer_running: bool = False
    last_scheduled_fallback_fire_time: Optional[float] = None
    fallback_generation: int = 0


# =============================================================================
# ARP ENGINE
# =============================================================================

class ArpEngine:
    """
    Arpeggiator engine implementing the ARP specification.

    All external inputs (UI events, clock ticks, timer callbacks) are posted
    to the event queue and processed serialized.
    """

    def __init__(
        self,
        send_note_on: Callable[[int, int, int], None],
        send_note_off: Callable[[int, int], None],
        get_velocity: Callable[[], int],
        get_targets: Callable[[], Set[int]],
        get_bpm: Callable[[], float],
        rng_seed_override: Optional[int] = None,
    ):
        """
        Initialize ARP engine.

        Args:
            send_note_on: Callback to send note on (slot, note, velocity)
            send_note_off: Callback to send note off (slot, note)
            get_velocity: Callback to get current overlay velocity
            get_targets: Callback to get current target slots
            get_bpm: Callback to get current BPM
            rng_seed_override: Optional seed for deterministic testing
        """
        self._send_note_on = send_note_on
        self._send_note_off = send_note_off
        self._get_velocity = get_velocity
        self._get_targets = get_targets
        self._get_bpm = get_bpm
        self._rng_seed_override = rng_seed_override

        # State
        self.settings = ArpSettings()
        self.runtime = ArpRuntime()
        self._state = ArpState.DISABLED

        # Event queue
        self._event_queue: deque[ArpEvent] = deque()
        self._processing = False

        # Timers
        self._fallback_timer = QTimer()
        self._fallback_timer.setSingleShot(True)
        self._fallback_timer.timeout.connect(self._on_fallback_timer)

        self._liveness_timer = QTimer()
        self._liveness_timer.timeout.connect(self._on_liveness_timer)

        # Legacy note tracking (for notes sent in legacy mode)
        self._legacy_notes_on: Dict[int, Set[int]] = {}  # note -> set of slots

        # Initialize PRNG
        self._init_prng()

    def _init_prng(self):
        """Initialize PRNG with seed."""
        if self._rng_seed_override is not None:
            seed = self._rng_seed_override & 0xFFFFFFFF
            if seed == 0:
                seed = XorShift32.DEFAULT_SEED
        else:
            # Generate random seed
            import random
            seed = random.randint(1, 0xFFFFFFFF)

        self.runtime.rng_seed = seed
        self.runtime.prng = XorShift32(seed)

    def _now_ms(self) -> float:
        """Get monotonic time in milliseconds."""
        return time.monotonic() * 1000.0

    # =========================================================================
    # EVENT QUEUE
    # =========================================================================

    def post_event(self, event: ArpEvent):
        """Post an event to the queue for serialized processing."""
        if event.timestamp_ms == 0.0:
            event.timestamp_ms = self._now_ms()
        self._event_queue.append(event)
        self._process_queue()

    def _process_queue(self):
        """Process events from the queue one at a time."""
        if self._processing:
            return

        self._processing = True
        try:
            while self._event_queue:
                event = self._event_queue.popleft()

                # TEARDOWN clears remaining events
                if event.event_type == ArpEventType.TEARDOWN:
                    self._handle_teardown(event)
                    self._event_queue.clear()
                    break

                self._dispatch_event(event)
        finally:
            self._processing = False

    def _dispatch_event(self, event: ArpEvent):
        """Dispatch event to appropriate handler."""
        handlers = {
            ArpEventType.KEY_PRESS: self._handle_key_press,
            ArpEventType.KEY_RELEASE: self._handle_key_release,
            ArpEventType.ARP_TOGGLE: self._handle_arp_toggle,
            ArpEventType.HOLD_TOGGLE: self._handle_hold_toggle,
            ArpEventType.RATE_CHANGE: self._handle_rate_change,
            ArpEventType.PATTERN_CHANGE: self._handle_pattern_change,
            ArpEventType.OCTAVES_CHANGE: self._handle_octaves_change,
            ArpEventType.TARGET_CHANGE: self._handle_target_change,
            ArpEventType.BPM_CHANGE: self._handle_bpm_change,
            ArpEventType.MASTER_TICK: self._handle_master_tick,
            ArpEventType.FALLBACK_FIRE: self._handle_fallback_fire,
            ArpEventType.LIVENESS_CHECK: self._handle_liveness_check,
        }
        handler = handlers.get(event.event_type)
        if handler:
            handler(event)

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def key_press(self, note: int):
        """Handle key press from keyboard overlay."""
        self.post_event(ArpEvent(ArpEventType.KEY_PRESS, {"note": note}))

    def key_release(self, note: int):
        """Handle key release from keyboard overlay."""
        self.post_event(ArpEvent(ArpEventType.KEY_RELEASE, {"note": note}))

    def toggle_arp(self, enabled: bool):
        """Toggle ARP on/off."""
        self.post_event(ArpEvent(ArpEventType.ARP_TOGGLE, {"enabled": enabled}))

    def toggle_hold(self, enabled: bool):
        """Toggle hold/latch mode."""
        self.post_event(ArpEvent(ArpEventType.HOLD_TOGGLE, {"enabled": enabled}))

    def set_rate(self, rate_index: int):
        """Set ARP rate."""
        self.post_event(ArpEvent(ArpEventType.RATE_CHANGE, {"rate_index": rate_index}))

    def set_pattern(self, pattern: ArpPattern):
        """Set ARP pattern."""
        self.post_event(ArpEvent(ArpEventType.PATTERN_CHANGE, {"pattern": pattern}))

    def set_octaves(self, octaves: int):
        """Set octave range."""
        self.post_event(ArpEvent(ArpEventType.OCTAVES_CHANGE, {"octaves": octaves}))

    def notify_targets_changed(self):
        """Notify that target slots have changed."""
        self.post_event(ArpEvent(ArpEventType.TARGET_CHANGE, {}))

    def notify_bpm_changed(self, bpm: float):
        """Notify BPM change."""
        self.post_event(ArpEvent(ArpEventType.BPM_CHANGE, {"bpm": bpm}))

    def master_tick(self, rate_index: int, tick_time_ms: float):
        """Handle master clock tick."""
        self.post_event(ArpEvent(
            ArpEventType.MASTER_TICK,
            {"rate_index": rate_index, "tick_time_ms": tick_time_ms}
        ))

    def teardown(self):
        """Tear down ARP engine (overlay dismiss)."""
        self.post_event(ArpEvent(ArpEventType.TEARDOWN, {}))

    def is_enabled(self) -> bool:
        """Check if ARP is enabled."""
        return self.settings.enabled

    def get_settings(self) -> ArpSettings:
        """Get current ARP settings."""
        return self.settings

    # =========================================================================
    # ACTIVE SET DERIVATION
    # =========================================================================

    def _get_active_set(self) -> Set[int]:
        """Get active note set based on hold mode."""
        if self.settings.hold:
            return self.runtime.latched.copy()
        return self.runtime.physical_held.copy()

    def _get_active_order(self) -> List[int]:
        """Get active order list based on hold mode."""
        if self.settings.hold:
            return self.runtime.latched_order.copy()
        return self.runtime.physical_order.copy()

    def _get_expanded_list(self) -> List[int]:
        """
        Compute expanded note list from active set.

        Returns notes in pattern-appropriate order, expanded across octaves.
        """
        active_set = self._get_active_set()
        if not active_set:
            return []

        # Base list ordering
        if self.settings.pattern == ArpPattern.ORDER:
            # Use insertion order
            base_list = [n for n in self._get_active_order() if n in active_set]
        else:
            # Sorted ascending
            base_list = sorted(active_set)

        # Expand across octaves
        expanded = []
        for octave_offset in range(self.settings.octaves):
            for note in base_list:
                expanded_note = note + (12 * octave_offset)
                if 0 <= expanded_note <= 127:
                    expanded.append(expanded_note)

        return expanded

    # =========================================================================
    # PATTERN STEPPING
    # =========================================================================

    def _select_next_note(self, expanded_list: List[int]) -> int:
        """
        Select next note from expanded list based on pattern.
        Updates current_step_index.
        """
        n = len(expanded_list)
        if n == 0:
            raise ValueError("Cannot select from empty list")

        pattern = self.settings.pattern
        idx = self.runtime.current_step_index

        if pattern == ArpPattern.UP or pattern == ArpPattern.ORDER:
            note = expanded_list[idx % n]
            self.runtime.current_step_index += 1
            return note

        elif pattern == ArpPattern.DOWN:
            reversed_list = list(reversed(expanded_list))
            note = reversed_list[idx % n]
            self.runtime.current_step_index += 1
            return note

        elif pattern == ArpPattern.UPDOWN:
            if n == 1:
                note = expanded_list[0]
            elif n == 2:
                note = expanded_list[idx % 2]
            else:
                # n >= 3: ping-pong without repeating endpoints
                seq_len = 2 * n - 2
                pos = idx % seq_len
                if pos < n:
                    note = expanded_list[pos]
                else:
                    note = expanded_list[seq_len - pos]
            self.runtime.current_step_index += 1
            return note

        elif pattern == ArpPattern.RANDOM:
            choice_idx = self.runtime.prng.choice(n)
            note = expanded_list[choice_idx]
            self.runtime.current_step_index += 1
            return note

        # Fallback
        return expanded_list[0]

    # =========================================================================
    # VELOCITY HELPERS
    # =========================================================================

    def _get_arp_velocity(self, note: int, vel_snapshot: int) -> int:
        """Get velocity for ARP note using ARP Note On velocity rules."""
        if note in self.runtime.note_velocity:
            return self.runtime.note_velocity[note]
        return vel_snapshot

    def _get_legacy_velocity(self, note: int, vel_snapshot: int) -> int:
        """Get velocity for legacy note using Legacy Note On velocity rules."""
        if note in self.runtime.note_velocity:
            return self.runtime.note_velocity[note]
        return vel_snapshot

    # =========================================================================
    # MIDI EMISSION HELPERS
    # =========================================================================

    def _emit_note_on(self, slot: int, note: int, velocity: int):
        """Emit a note on message."""
        self._send_note_on(slot, note, velocity)

    def _emit_note_off(self, slot: int, note: int):
        """Emit a note off message."""
        self._send_note_off(slot, note)

    def _note_off_last_played(self):
        """Turn off last played ARP note on all last played targets."""
        if self.runtime.last_played_note is not None:
            for slot in self.runtime.last_played_targets:
                self._emit_note_off(slot, self.runtime.last_played_note)
            self.runtime.last_played_note = None
            self.runtime.last_played_targets = set()

    def _note_off_legacy(self, note: int):
        """Turn off a legacy note on all slots it's playing on."""
        if note in self._legacy_notes_on:
            for slot in self._legacy_notes_on[note]:
                self._emit_note_off(slot, note)
            del self._legacy_notes_on[note]

    def _note_off_all_legacy(self):
        """Turn off all legacy notes."""
        for note, slots in list(self._legacy_notes_on.items()):
            for slot in slots:
                self._emit_note_off(slot, note)
        self._legacy_notes_on.clear()

    def _note_on_legacy(self, note: int, velocity: int, targets: Set[int]):
        """Turn on a legacy note on all target slots."""
        self._legacy_notes_on[note] = targets.copy()
        for slot in targets:
            self._emit_note_on(slot, note, velocity)

    # =========================================================================
    # TIMING HELPERS
    # =========================================================================

    def _compute_interval_ms(self, bpm: float) -> Optional[float]:
        """Compute step interval in ms for current rate and BPM."""
        if bpm <= 0:
            return None
        beat_ms = 60000.0 / bpm
        beats_per_step = ARP_BEATS_PER_STEP.get(self.settings.rate_index, 0.5)
        return beat_ms * beats_per_step

    def _start_or_restart_fallback(self, reason: str = ""):
        """
        Start or restart fallback timer following the spec procedure.
        """
        # Stop existing timer
        self._fallback_timer.stop()
        self.runtime.fallback_generation += 1

        bpm = self._get_bpm()
        interval_ms = self._compute_interval_ms(bpm)

        if interval_ms is None or interval_ms <= 0:
            self.runtime.fallback_timer_running = False
            return

        # First-fire computation
        now = self._now_ms()

        # Choose anchor in priority order
        t_anchor = now
        if self.runtime.last_arp_step_time is not None:
            t_anchor = self.runtime.last_arp_step_time
        elif self.settings.rate_index in self.runtime.last_master_tick_time_by_rate:
            t_anchor = self.runtime.last_master_tick_time_by_rate[self.settings.rate_index]
        elif self.runtime.last_scheduled_fallback_fire_time is not None:
            t_anchor = self.runtime.last_scheduled_fallback_fire_time

        # Clamp anchor
        t_anchor_effective = min(t_anchor, now)

        # Compute first fire time
        k = max(1, int((now + 1.0 - t_anchor_effective) / interval_ms) + 1)
        t_first = t_anchor_effective + k * interval_ms

        # Schedule timer
        delay_ms = max(1, int(t_first - now))
        self._fallback_timer.start(delay_ms)

        self.runtime.fallback_timer_running = True
        self.runtime.last_scheduled_fallback_fire_time = t_first

    def _stop_fallback(self):
        """Stop fallback timer."""
        self._fallback_timer.stop()
        self.runtime.fallback_generation += 1
        self.runtime.fallback_timer_running = False

    def _start_liveness_timer(self):
        """Start liveness timer for MASTER mode."""
        bpm = self._get_bpm()
        beat_ms = 60000.0 / bpm if bpm > 0 else 500.0

        interval_ms = 0.4 * beat_ms
        interval_ms = max(LIVENESS_POST_INTERVAL_MIN_MS,
                          min(LIVENESS_POST_INTERVAL_MAX_MS, interval_ms))

        self._liveness_timer.start(int(interval_ms))

    def _stop_liveness_timer(self):
        """Stop liveness timer."""
        self._liveness_timer.stop()

    def _get_liveness_timeout_ms(self) -> float:
        """Compute liveness timeout threshold."""
        interval_ms = self._compute_interval_ms(self._get_bpm())
        if interval_ms is None:
            interval_ms = 250.0
        return max(50.0, LIVENESS_TIMEOUT_MULTIPLIER * interval_ms)

    # =========================================================================
    # TIMER CALLBACKS
    # =========================================================================

    def _on_fallback_timer(self):
        """Fallback timer fired - post event to queue."""
        generation = self.runtime.fallback_generation
        t_scheduled = self.runtime.last_scheduled_fallback_fire_time
        t_fired = self._now_ms()

        self.post_event(ArpEvent(
            ArpEventType.FALLBACK_FIRE,
            {
                "generation": generation,
                "t_scheduled_ms": t_scheduled,
                "t_fired_ms": t_fired,
            }
        ))

    def _on_liveness_timer(self):
        """Liveness timer fired - post event to queue."""
        self.post_event(ArpEvent(
            ArpEventType.LIVENESS_CHECK,
            {"t_fired_ms": self._now_ms()}
        ))

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _handle_key_press(self, event: ArpEvent):
        """Handle key press event."""
        note = event.data.get("note", -1)
        if not 0 <= note <= 127:
            return

        # Sample velocity snapshot at handler entry
        vel_snapshot = self._get_velocity()

        # Update physical tracking
        self.runtime.physical_held.add(note)
        if note not in self.runtime.physical_order:
            self.runtime.physical_order.append(note)

        # Capture velocity (clamped)
        self.runtime.note_velocity[note] = max(1, min(127, vel_snapshot))

        if not self.settings.enabled:
            # Legacy behavior: emit note on immediately
            targets = self._get_targets()
            if targets:
                velocity = self._get_legacy_velocity(note, vel_snapshot)
                self._note_on_legacy(note, velocity, targets)
        else:
            # ARP enabled
            if self.settings.hold:
                # Toggle latch membership
                if note in self.runtime.latched:
                    self.runtime.latched.discard(note)
                    if note in self.runtime.latched_order:
                        self.runtime.latched_order.remove(note)
                else:
                    self.runtime.latched.add(note)
                    if note not in self.runtime.latched_order:
                        self.runtime.latched_order.append(note)

            # Check state transition
            if self._get_active_set():
                self._state = ArpState.ENABLED_PLAYING

    def _handle_key_release(self, event: ArpEvent):
        """Handle key release event."""
        note = event.data.get("note", -1)
        if not 0 <= note <= 127:
            return

        # Update physical tracking
        self.runtime.physical_held.discard(note)
        if note in self.runtime.physical_order:
            self.runtime.physical_order.remove(note)

        if not self.settings.enabled:
            # Legacy behavior: emit note off immediately
            self._note_off_legacy(note)
        else:
            # ARP enabled - check if active set becomes empty
            if not self._get_active_set():
                self._note_off_last_played()
                self._state = ArpState.ENABLED_IDLE

    def _handle_arp_toggle(self, event: ArpEvent):
        """Handle ARP enable/disable toggle."""
        enabled = event.data.get("enabled", False)

        if enabled == self.settings.enabled:
            return

        # Sample velocity snapshot at handler entry
        vel_snapshot = self._get_velocity()

        if enabled:
            # DISABLED -> ENABLED
            # Turn off legacy notes
            self._note_off_all_legacy()

            # Initialize playback state
            self.runtime.current_step_index = 0
            self.runtime.last_played_note = None
            self.runtime.last_played_targets = self._get_targets()

            # Copy physical to latched if hold is on
            if self.settings.hold:
                self.runtime.latched = self.runtime.physical_held.copy()
                self.runtime.latched_order = self.runtime.physical_order.copy()

            # Set clock mode to AUTO
            self.runtime.clock_mode = ClockMode.AUTO

            # Start fallback if BPM valid
            bpm = self._get_bpm()
            if bpm > 0:
                self._start_or_restart_fallback("enable")

            self.settings.enabled = True
            self._state = (ArpState.ENABLED_PLAYING
                           if self._get_active_set()
                           else ArpState.ENABLED_IDLE)

        else:
            # ENABLED -> DISABLED
            # Turn off last played ARP note
            self._note_off_last_played()

            # Stop stepping
            self._stop_fallback()
            self._stop_liveness_timer()
            self.runtime.clock_mode = ClockMode.STOPPED

            # Clear playback state
            self.runtime.current_step_index = 0

            # Resume legacy sustain for held notes
            targets = self._get_targets()
            for note in self.runtime.physical_held:
                velocity = self._get_legacy_velocity(note, vel_snapshot)
                self._note_on_legacy(note, velocity, targets)

            self.settings.enabled = False
            self._state = ArpState.DISABLED

    def _handle_hold_toggle(self, event: ArpEvent):
        """Handle hold/latch toggle."""
        enabled = event.data.get("enabled", False)

        if enabled == self.settings.hold:
            return

        if enabled:
            # OFF -> ON
            self.settings.hold = True
            self.runtime.latched = self.runtime.physical_held.copy()
            self.runtime.latched_order = self.runtime.physical_order.copy()
        else:
            # ON -> OFF
            self.settings.hold = False
            self.runtime.latched.clear()
            self.runtime.latched_order.clear()

        self.runtime.current_step_index = 0

        # Post-toggle empty-set rule
        if self.settings.enabled and not self._get_active_set():
            self._note_off_last_played()
            self._state = ArpState.ENABLED_IDLE

    def _handle_rate_change(self, event: ArpEvent):
        """Handle rate change."""
        rate_index = event.data.get("rate_index", ARP_DEFAULT_RATE_INDEX)
        rate_index = max(0, min(len(ARP_RATE_LABELS) - 1, rate_index))

        self.settings.rate_index = rate_index
        self.runtime.current_step_index = 0

        # Restart fallback if in AUTO mode
        if self.settings.enabled and self.runtime.clock_mode == ClockMode.AUTO:
            bpm = self._get_bpm()
            if bpm > 0:
                self._start_or_restart_fallback("rateChange")
            else:
                self._stop_fallback()

        # Check if expanded list becomes empty
        if self.settings.enabled and not self._get_expanded_list():
            self._note_off_last_played()
            self._state = ArpState.ENABLED_IDLE

    def _handle_pattern_change(self, event: ArpEvent):
        """Handle pattern change."""
        pattern = event.data.get("pattern", ArpPattern.UP)

        self.settings.pattern = pattern
        self.runtime.current_step_index = 0

        # Check if expanded list becomes empty
        if self.settings.enabled and not self._get_expanded_list():
            self._note_off_last_played()
            self._state = ArpState.ENABLED_IDLE

    def _handle_octaves_change(self, event: ArpEvent):
        """Handle octaves change."""
        octaves = event.data.get("octaves", 1)
        octaves = max(1, min(4, octaves))

        self.settings.octaves = octaves
        self.runtime.current_step_index = 0

        # Restart fallback if in AUTO mode
        if self.settings.enabled and self.runtime.clock_mode == ClockMode.AUTO:
            bpm = self._get_bpm()
            if bpm > 0:
                self._start_or_restart_fallback("octavesChange")
            else:
                self._stop_fallback()

        # Check if expanded list becomes empty
        if self.settings.enabled and not self._get_expanded_list():
            self._note_off_last_played()
            self._state = ArpState.ENABLED_IDLE

    def _handle_target_change(self, event: ArpEvent):
        """Handle target slot changes."""
        if not self.settings.enabled:
            return

        new_targets = self._get_targets()

        if self.runtime.last_played_note is not None:
            # Note off for removed targets
            removed = self.runtime.last_played_targets - new_targets
            for slot in removed:
                self._emit_note_off(slot, self.runtime.last_played_note)

        self.runtime.last_played_targets = new_targets

    def _handle_bpm_change(self, event: ArpEvent):
        """Handle BPM change."""
        if not self.settings.enabled:
            return

        bpm = event.data.get("bpm", 0)

        if self.runtime.clock_mode == ClockMode.AUTO:
            if bpm > 0:
                self._start_or_restart_fallback("bpmChange")
            else:
                self._stop_fallback()

    def _handle_master_tick(self, event: ArpEvent):
        """Handle master clock tick."""
        rate_index = event.data.get("rate_index", -1)
        tick_time_ms = event.data.get("tick_time_ms", 0.0)

        # Always update timing info
        self.runtime.last_master_tick_time_by_rate[rate_index] = tick_time_ms
        if rate_index == self.settings.rate_index:
            self.runtime.last_eligible_master_tick_time = tick_time_ms

        # Check stepping eligibility
        if not self.settings.enabled or self.runtime.clock_mode == ClockMode.STOPPED:
            return

        if self.runtime.clock_mode == ClockMode.MASTER:
            # Only step on matching rate
            if rate_index == self.settings.rate_index:
                self._execute_step(tick_time_ms)

        elif self.runtime.clock_mode == ClockMode.AUTO:
            # Promotion to MASTER
            if rate_index == self.settings.rate_index:
                # Stop fallback
                self._stop_fallback()

                # Promote to MASTER
                self.runtime.clock_mode = ClockMode.MASTER

                # Start liveness timer
                self._start_liveness_timer()

                # Double-step suppression
                if self.runtime.last_arp_step_time is not None:
                    delta = abs(tick_time_ms - self.runtime.last_arp_step_time)
                    if delta <= PROMOTION_SUPPRESS_WINDOW_MS:
                        # Suppress step, just update timing
                        self.runtime.last_arp_step_time = tick_time_ms
                        return

                # Execute step
                self._execute_step(tick_time_ms)

    def _handle_fallback_fire(self, event: ArpEvent):
        """Handle fallback timer fire."""
        generation = event.data.get("generation", -1)
        t_scheduled_ms = event.data.get("t_scheduled_ms", 0.0)
        t_fired_ms = event.data.get("t_fired_ms", 0.0)

        # Check eligibility
        if not self.settings.enabled:
            return
        if self.runtime.clock_mode != ClockMode.AUTO:
            return
        if self._get_bpm() <= 0:
            return
        if not self.runtime.fallback_timer_running:
            return
        if generation != self.runtime.fallback_generation:
            return  # Stale event

        # Execute step
        self._execute_step(t_fired_ms)

        # Schedule next fire
        bpm = self._get_bpm()
        if bpm <= 0:
            self._stop_fallback()
            return

        interval_ms = self._compute_interval_ms(bpm)
        if interval_ms is None:
            self._stop_fallback()
            return

        # Subsequent-fire computation
        now = self._now_ms()
        t_next = t_scheduled_ms + interval_ms

        # Catch up if late
        while t_next <= now + 1.0:
            t_next += interval_ms

        delay_ms = max(1, int(t_next - now))
        self._fallback_timer.start(delay_ms)
        self.runtime.last_scheduled_fallback_fire_time = t_next

    def _handle_liveness_check(self, event: ArpEvent):
        """Handle liveness check for MASTER mode."""
        if not self.settings.enabled:
            return
        if self.runtime.clock_mode != ClockMode.MASTER:
            return

        # Check liveness
        timeout_ms = self._get_liveness_timeout_ms()
        now = self._now_ms()

        if self.runtime.last_eligible_master_tick_time is None:
            # No ticks ever received, demote
            self._demote_to_auto()
        elif now - self.runtime.last_eligible_master_tick_time > timeout_ms:
            # Ticks stopped, demote
            self._demote_to_auto()

    def _demote_to_auto(self):
        """Demote from MASTER to AUTO mode."""
        self._stop_liveness_timer()
        self.runtime.clock_mode = ClockMode.AUTO
        self.runtime.fallback_generation += 1

        bpm = self._get_bpm()
        if bpm > 0:
            self._start_or_restart_fallback("demotion")
        else:
            self.runtime.fallback_timer_running = False

    def _handle_teardown(self, event: ArpEvent):
        """Handle overlay teardown."""
        # Stop timers
        self._stop_fallback()
        self._stop_liveness_timer()
        self.runtime.clock_mode = ClockMode.STOPPED

        # Turn off ARP note
        self._note_off_last_played()

        # Turn off legacy notes
        self._note_off_all_legacy()

        # Reset state
        self.settings = ArpSettings()
        self.runtime = ArpRuntime()
        self._state = ArpState.DISABLED
        self._legacy_notes_on.clear()

        # Reinitialize PRNG
        self._init_prng()

    # =========================================================================
    # STEP EXECUTION
    # =========================================================================

    def _execute_step(self, step_time_ms: float):
        """Execute one ARP step."""
        # Sample snapshots at handler entry
        vel_snapshot = self._get_velocity()
        targets_snapshot = self._get_targets()

        # Get expanded list
        expanded_list = self._get_expanded_list()

        if not expanded_list:
            # Empty list - turn off and go idle
            self._note_off_last_played()
            self._state = ArpState.ENABLED_IDLE
            self.runtime.last_arp_step_time = step_time_ms
            return

        # Select next note
        next_note = self._select_next_note(expanded_list)

        # Turn off previous note
        self._note_off_last_played()

        # Turn on new note (if targets exist)
        if targets_snapshot:
            velocity = self._get_arp_velocity(next_note, vel_snapshot)
            for slot in targets_snapshot:
                self._emit_note_on(slot, next_note, velocity)
            self.runtime.last_played_note = next_note
            self.runtime.last_played_targets = targets_snapshot
        else:
            self.runtime.last_played_note = None
            self.runtime.last_played_targets = set()

        self.runtime.last_arp_step_time = step_time_ms
        self._state = ArpState.ENABLED_PLAYING
