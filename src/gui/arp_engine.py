"""
Arpeggiator Engine — Per-Slot (v2.0)

Implements PER_SLOT_ARP_SPEC v1.2.1:
- Each engine targets exactly one slot (no multi-target broadcast)
- Serialized event queue for thread-safe operation
- Master clock integration with fallback timer
- Pattern generation (UP, DOWN, UPDOWN, RANDOM, ORDER)
- Hold/latch functionality that persists across overlay hide/show

Key invariants:
- Monophonic: at most one ARP note sounding at any time
- No stuck notes: all notes turned off on teardown/empty set
- Deterministic: PRNG uses xorshift32, order tracking for ORDER pattern
- Single slot: engine always emits to self._slot_id
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set

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

# =============================================================================
# EUCLIDEAN HIT FUNCTION
# =============================================================================

def euclidean_hit(step: int, n: int, k: int, rotation: int = 0) -> bool:
    """True if step is a hit in Euclidean rhythm E(k,n).
    O(1) per step. Bresenham/floor method."""
    if k <= 0:
        return False
    if k >= n:
        return True
    i = (step + rotation) % n
    return (i * k) // n != (((i - 1) * k) // n) if i > 0 else (0 != (((n - 1) * k) // n))


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
    BPM_CHANGE = auto()
    MASTER_TICK = auto()
    FALLBACK_FIRE = auto()
    LIVENESS_CHECK = auto()
    EUCLID_SET = auto()
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
    """User-configurable ARP settings."""
    enabled: bool = False
    rate_index: int = ARP_DEFAULT_RATE_INDEX
    pattern: ArpPattern = ARP_DEFAULT_PATTERN
    octaves: int = ARP_DEFAULT_OCTAVES
    hold: bool = False
    euclid_enabled: bool = False
    euclid_n: int = 16
    euclid_k: int = 16   # Default = all hits (same as off)
    euclid_rot: int = 0


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

    # Euclidean gate
    euclid_step: int = 0

    # Repeating reset: fabric index to trigger on, or None
    rst_fabric_idx: Optional[int] = None
    rst_fired_count: int = 0

    # Clock/timing
    clock_mode: ClockMode = ClockMode.STOPPED
    last_master_tick_time_by_rate: Dict[int, float] = field(default_factory=dict)
    last_eligible_master_tick_time: Optional[float] = None
    last_arp_step_time: Optional[float] = None
    fallback_timer_running: bool = False
    last_scheduled_fallback_fire_time: Optional[float] = None
    fallback_generation: int = 0


# =============================================================================
# ARP ENGINE (Per-Slot v2.0)
# =============================================================================

class ArpEngine:
    """
    Per-slot arpeggiator engine (PER_SLOT_ARP_SPEC v1.2.1).

    Each engine targets exactly one slot. All external inputs are posted
    to the event queue and processed serialized.
    """

    def __init__(
        self,
        slot_id: int,
        send_note_on: Callable[[int, int, int], None],
        send_note_off: Callable[[int, int], None],
        get_velocity: Callable[[], int],
        get_bpm: Callable[[], float],
        rng_seed_override: Optional[int] = None,
    ):
        """
        Initialize ARP engine for a single slot.

        Args:
            slot_id: Target slot (0-indexed, fixed for lifetime)
            send_note_on: Callback (slot, note, velocity)
            send_note_off: Callback (slot, note)
            get_velocity: Callback to get current overlay velocity
            get_bpm: Callback to get current BPM
            rng_seed_override: Optional seed for deterministic testing
        """
        self._slot_id = slot_id
        self._send_note_on = send_note_on
        self._send_note_off = send_note_off
        self._get_velocity = get_velocity
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

        # Legacy note tracking (for notes sent when ARP is off)
        self._legacy_note_on: Optional[int] = None  # Single slot, single legacy note

        # Callback for SC step engine: push updated expanded list when notes change
        self.on_notes_changed: Optional[Callable] = None

        # Initialize PRNG
        self._init_prng()

    # =========================================================================
    # PROPERTIES (per spec v1.2.1)
    # =========================================================================

    @property
    def slot_id(self) -> int:
        """Target slot (0-indexed, read-only)."""
        return self._slot_id

    @property
    def is_active(self) -> bool:
        """True if ARP is enabled and has notes in active set."""
        return self.settings.enabled and bool(self._get_active_set())

    @property
    def has_hold(self) -> bool:
        """True if ARP+HOLD is active with latched notes."""
        return (self.settings.enabled and self.settings.hold
                and bool(self.runtime.latched))

    @property
    def currently_sounding_note(self) -> Optional[int]:
        """The note currently playing, or None."""
        return self.runtime.last_played_note

    # =========================================================================
    # INIT
    # =========================================================================

    def _notify_notes_changed(self):
        """Notify SC step engine that the expanded note list may have changed."""
        if self.on_notes_changed is not None:
            self.on_notes_changed()

    def _init_prng(self):
        """Initialize PRNG with seed."""
        if self._rng_seed_override is not None:
            seed = self._rng_seed_override & 0xFFFFFFFF
            if seed == 0:
                seed = XorShift32.DEFAULT_SEED
        else:
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
            ArpEventType.BPM_CHANGE: self._handle_bpm_change,
            ArpEventType.MASTER_TICK: self._handle_master_tick,
            ArpEventType.FALLBACK_FIRE: self._handle_fallback_fire,
            ArpEventType.LIVENESS_CHECK: self._handle_liveness_check,
            ArpEventType.EUCLID_SET: self._handle_euclid_set,
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

    def notify_bpm_changed(self, bpm: float):
        """Notify BPM change."""
        self.post_event(ArpEvent(ArpEventType.BPM_CHANGE, {"bpm": bpm}))

    def master_tick(self, rate_index: int, tick_time_ms: float):
        """Handle master clock tick."""
        self.post_event(ArpEvent(
            ArpEventType.MASTER_TICK,
            {"rate_index": rate_index, "tick_time_ms": tick_time_ms}
        ))

    def set_euclid(self, enabled: bool, n: int, k: int, rot: int):
        """Set Euclidean gate parameters (single event for all params)."""
        self.post_event(ArpEvent(ArpEventType.EUCLID_SET, {
            "enabled": bool(enabled),
            "n": int(n), "k": int(k), "rot": int(rot)
        }))

    def teardown(self):
        """Tear down ARP engine: stop timers, note-off, reset state."""
        self.post_event(ArpEvent(ArpEventType.TEARDOWN, {}))

    def is_enabled(self) -> bool:
        """Check if ARP is enabled."""
        return self.settings.enabled

    def get_settings(self) -> ArpSettings:
        """Get current ARP settings."""
        return self.settings

    # =========================================================================
    # ONE-SHOT RESET (called from MotionManager under slot lock)
    # =========================================================================

    def reset_on_tick(self, tick_time_ms: float):
        """Execute ARP phase reset. Called from MotionManager when fabric tick matches.

        Repeating: stays armed (rst_fabric_idx is NOT cleared).
        Fires every time the matching fabric tick arrives.
        """
        self._note_off_currently_sounding()
        self.runtime.current_step_index = 0
        self.runtime.euclid_step = 0
        # Clear tick-dedupe state so master_tick() can emit step 0 on this same tick.
        self.runtime.last_arp_step_time = None
        self.runtime.last_eligible_master_tick_time = None
        rate = self.settings.rate_index
        self.runtime.last_master_tick_time_by_rate.pop(rate, None)
        self.runtime.rst_fired_count += 1

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
        """Compute expanded note list from active set, across octaves."""
        active_set = self._get_active_set()
        if not active_set:
            return []

        if self.settings.pattern == ArpPattern.ORDER:
            base_list = [n for n in self._get_active_order() if n in active_set]
        else:
            base_list = sorted(active_set)

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
        """Select next note from expanded list based on pattern."""
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

        return expanded_list[0]

    # =========================================================================
    # VELOCITY HELPERS
    # =========================================================================

    def _get_arp_velocity(self, note: int, vel_snapshot: int) -> int:
        """Get velocity for ARP note."""
        if note in self.runtime.note_velocity:
            return self.runtime.note_velocity[note]
        return vel_snapshot

    # =========================================================================
    # MIDI EMISSION HELPERS (single-slot)
    # =========================================================================

    def _emit_note_on(self, note: int, velocity: int):
        """Emit note on to this engine's slot."""
        self._send_note_on(self._slot_id, note, velocity)

    def _emit_note_off(self, note: int):
        """Emit note off to this engine's slot."""
        self._send_note_off(self._slot_id, note)

    def _note_off_currently_sounding(self):
        """Turn off the currently sounding ARP note."""
        if self.runtime.last_played_note is not None:
            self._emit_note_off(self.runtime.last_played_note)
            self.runtime.last_played_note = None

    def _note_off_legacy(self):
        """Turn off legacy note (non-ARP)."""
        if self._legacy_note_on is not None:
            self._emit_note_off(self._legacy_note_on)
            self._legacy_note_on = None

    def _note_on_legacy(self, note: int, velocity: int):
        """Turn on a legacy note on this slot."""
        # Turn off previous legacy note first
        self._note_off_legacy()
        self._legacy_note_on = note
        self._emit_note_on(note, velocity)

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
        """Start or restart fallback timer."""
        self._fallback_timer.stop()
        self.runtime.fallback_generation += 1

        bpm = self._get_bpm()
        interval_ms = self._compute_interval_ms(bpm)

        if interval_ms is None or interval_ms <= 0:
            self.runtime.fallback_timer_running = False
            return

        now = self._now_ms()

        t_anchor = now
        if self.runtime.last_arp_step_time is not None:
            t_anchor = self.runtime.last_arp_step_time
        elif self.settings.rate_index in self.runtime.last_master_tick_time_by_rate:
            t_anchor = self.runtime.last_master_tick_time_by_rate[self.settings.rate_index]
        elif self.runtime.last_scheduled_fallback_fire_time is not None:
            t_anchor = self.runtime.last_scheduled_fallback_fire_time

        t_anchor_effective = min(t_anchor, now)

        k = max(1, int((now + 1.0 - t_anchor_effective) / interval_ms) + 1)
        t_first = t_anchor_effective + k * interval_ms

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
        """Fallback timer fired."""
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
        """Liveness timer fired."""
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

        vel_snapshot = self._get_velocity()

        # Update physical tracking
        self.runtime.physical_held.add(note)
        if note not in self.runtime.physical_order:
            self.runtime.physical_order.append(note)

        self.runtime.note_velocity[note] = max(1, min(127, vel_snapshot))

        if not self.settings.enabled:
            # Legacy: direct note-on to this slot
            velocity = self.runtime.note_velocity.get(note, vel_snapshot)
            self._note_on_legacy(note, velocity)
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

            if self._get_active_set():
                self._state = ArpState.ENABLED_PLAYING
            self._notify_notes_changed()

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
            # Legacy: note off for this note
            if self._legacy_note_on == note:
                self._note_off_legacy()
        else:
            # ARP: check if active set becomes empty
            if not self._get_active_set():
                # Note-off for currently sounding note (not the released key)
                self._note_off_currently_sounding()
                self._state = ArpState.ENABLED_IDLE
            self._notify_notes_changed()

    def _handle_arp_toggle(self, event: ArpEvent):
        """Handle ARP enable/disable toggle."""
        enabled = event.data.get("enabled", False)

        if enabled == self.settings.enabled:
            return

        vel_snapshot = self._get_velocity()

        if enabled:
            # DISABLED -> ENABLED
            self._note_off_legacy()

            self.runtime.current_step_index = 0
            self.runtime.last_played_note = None

            if self.settings.hold:
                self.runtime.latched = self.runtime.physical_held.copy()
                self.runtime.latched_order = self.runtime.physical_order.copy()

            self.runtime.clock_mode = ClockMode.AUTO

            bpm = self._get_bpm()
            if bpm > 0:
                self._start_or_restart_fallback("enable")

            self.settings.enabled = True
            self._state = (ArpState.ENABLED_PLAYING
                           if self._get_active_set()
                           else ArpState.ENABLED_IDLE)

        else:
            # ENABLED -> DISABLED
            self._note_off_currently_sounding()

            self._stop_fallback()
            self._stop_liveness_timer()
            self.runtime.clock_mode = ClockMode.STOPPED
            self.runtime.current_step_index = 0

            # Resume legacy sustain for held notes
            for note in self.runtime.physical_held:
                velocity = self.runtime.note_velocity.get(note, vel_snapshot)
                self._note_on_legacy(note, velocity)

            self.settings.enabled = False
            self._state = ArpState.DISABLED

    def _handle_hold_toggle(self, event: ArpEvent):
        """Handle hold/latch toggle."""
        enabled = event.data.get("enabled", False)

        if enabled == self.settings.hold:
            return

        if enabled:
            self.settings.hold = True
            self.runtime.latched = self.runtime.physical_held.copy()
            self.runtime.latched_order = self.runtime.physical_order.copy()
        else:
            self.settings.hold = False
            self.runtime.latched.clear()
            self.runtime.latched_order.clear()

        self.runtime.current_step_index = 0

        # Post-toggle empty-set rule
        if self.settings.enabled and not self._get_active_set():
            self._note_off_currently_sounding()
            self._state = ArpState.ENABLED_IDLE
        self._notify_notes_changed()

    def _handle_rate_change(self, event: ArpEvent):
        """Handle rate change."""
        rate_index = event.data.get("rate_index", ARP_DEFAULT_RATE_INDEX)
        rate_index = max(0, min(len(ARP_RATE_LABELS) - 1, rate_index))

        self.settings.rate_index = rate_index
        self.runtime.current_step_index = 0

        if self.settings.enabled and self.runtime.clock_mode == ClockMode.AUTO:
            bpm = self._get_bpm()
            if bpm > 0:
                self._start_or_restart_fallback("rateChange")
            else:
                self._stop_fallback()

        if self.settings.enabled and not self._get_expanded_list():
            self._note_off_currently_sounding()
            self._state = ArpState.ENABLED_IDLE

    def _handle_pattern_change(self, event: ArpEvent):
        """Handle pattern change."""
        pattern = event.data.get("pattern", ArpPattern.UP)

        self.settings.pattern = pattern
        self.runtime.current_step_index = 0

        if self.settings.enabled and not self._get_expanded_list():
            self._note_off_currently_sounding()
            self._state = ArpState.ENABLED_IDLE
        self._notify_notes_changed()

    def _handle_octaves_change(self, event: ArpEvent):
        """Handle octaves change."""
        octaves = event.data.get("octaves", 1)
        octaves = max(1, min(4, octaves))

        self.settings.octaves = octaves
        self.runtime.current_step_index = 0

        if self.settings.enabled and self.runtime.clock_mode == ClockMode.AUTO:
            bpm = self._get_bpm()
            if bpm > 0:
                self._start_or_restart_fallback("octavesChange")
            else:
                self._stop_fallback()

        if self.settings.enabled and not self._get_expanded_list():
            self._note_off_currently_sounding()
            self._state = ArpState.ENABLED_IDLE
        self._notify_notes_changed()

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

        self.runtime.last_master_tick_time_by_rate[rate_index] = tick_time_ms
        if rate_index == self.settings.rate_index:
            self.runtime.last_eligible_master_tick_time = tick_time_ms

        if not self.settings.enabled or self.runtime.clock_mode == ClockMode.STOPPED:
            return

        if self.runtime.clock_mode == ClockMode.MASTER:
            if rate_index == self.settings.rate_index:
                if self._euclid_gate():
                    self._execute_step(tick_time_ms)

        elif self.runtime.clock_mode == ClockMode.AUTO:
            if rate_index == self.settings.rate_index:
                self._stop_fallback()
                self.runtime.clock_mode = ClockMode.MASTER
                self._start_liveness_timer()

                if self.runtime.last_arp_step_time is not None:
                    delta = abs(tick_time_ms - self.runtime.last_arp_step_time)
                    if delta <= PROMOTION_SUPPRESS_WINDOW_MS:
                        self.runtime.last_arp_step_time = tick_time_ms
                        return

                if self._euclid_gate():
                    self._execute_step(tick_time_ms)

    def _handle_fallback_fire(self, event: ArpEvent):
        """Handle fallback timer fire."""
        generation = event.data.get("generation", -1)
        t_scheduled_ms = event.data.get("t_scheduled_ms", 0.0)
        t_fired_ms = event.data.get("t_fired_ms", 0.0)

        if not self.settings.enabled:
            return
        if self.runtime.clock_mode != ClockMode.AUTO:
            return
        if self._get_bpm() <= 0:
            return
        if not self.runtime.fallback_timer_running:
            return
        if generation != self.runtime.fallback_generation:
            return

        if self._euclid_gate():
            self._execute_step(t_fired_ms)

        bpm = self._get_bpm()
        if bpm <= 0:
            self._stop_fallback()
            return

        interval_ms = self._compute_interval_ms(bpm)
        if interval_ms is None:
            self._stop_fallback()
            return

        now = self._now_ms()
        t_next = t_scheduled_ms + interval_ms

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

        timeout_ms = self._get_liveness_timeout_ms()
        now = self._now_ms()

        if self.runtime.last_eligible_master_tick_time is None:
            self._demote_to_auto()
        elif now - self.runtime.last_eligible_master_tick_time > timeout_ms:
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

    def _handle_euclid_set(self, event: ArpEvent):
        """Handle Euclidean gate parameter change."""
        en = bool(event.data.get("enabled", False))
        n = int(event.data.get("n", 16))
        n = max(1, min(64, n))
        k = int(event.data.get("k", n))
        k = max(0, min(n, k))
        rot = int(event.data.get("rot", 0))
        rot = max(0, min(n - 1, rot)) if n > 1 else 0

        changed_n = (n != self.settings.euclid_n)

        self.settings.euclid_enabled = en
        self.settings.euclid_n = n
        self.settings.euclid_k = k
        self.settings.euclid_rot = rot

        # Reset phase when enabling or changing N (keeps it predictable)
        if en or changed_n:
            self.runtime.euclid_step = 0

    def _handle_teardown(self, event: ArpEvent):
        """Handle teardown: stop timers first, then note-off, then reset."""
        # 1. Cancel timers (prevents new note-on after teardown)
        self._stop_fallback()
        self._stop_liveness_timer()
        self.runtime.clock_mode = ClockMode.STOPPED

        # 2. Note-off for currently sounding note
        self._note_off_currently_sounding()

        # 3. Note-off for legacy notes
        self._note_off_legacy()

        # 4. Reset state
        self.settings = ArpSettings()
        self.runtime = ArpRuntime()
        self._state = ArpState.DISABLED
        self._legacy_note_on = None

        # 5. Reinitialize PRNG
        self._init_prng()

    # =========================================================================
    # EUCLIDEAN GATE
    # =========================================================================

    def _euclid_gate(self) -> bool:
        """Returns True = fire note, False = skip. Always advances euclid_step."""
        if not self.settings.euclid_enabled:
            return True

        n = max(1, min(64, int(self.settings.euclid_n)))
        k = max(0, min(n, int(self.settings.euclid_k)))

        # rot must be valid even when n==1
        rot_max = max(0, n - 1)
        rot = max(0, min(rot_max, int(self.settings.euclid_rot)))

        hit = euclidean_hit(self.runtime.euclid_step % n, n, k, rot)
        self.runtime.euclid_step += 1
        return hit

    # =========================================================================
    # STEP EXECUTION
    # =========================================================================

    def _execute_step(self, step_time_ms: float):
        """Execute one ARP step."""
        vel_snapshot = self._get_velocity()

        expanded_list = self._get_expanded_list()

        if not expanded_list:
            self._note_off_currently_sounding()
            self._state = ArpState.ENABLED_IDLE
            self.runtime.last_arp_step_time = step_time_ms
            return

        next_note = self._select_next_note(expanded_list)

        # Turn off previous note
        self._note_off_currently_sounding()

        # Turn on new note
        velocity = self._get_arp_velocity(next_note, vel_snapshot)
        self._emit_note_on(next_note, velocity)
        self.runtime.last_played_note = next_note

        self.runtime.last_arp_step_time = step_time_ms
        self._state = ArpState.ENABLED_PLAYING
