"""
Waveform Stabilizer — Data Integrity Gatekeeper (Phase 1)

Observer-only module that tags incoming waveform frames with stability
decisions. Prevents transitional/poisoned frames from entering visual
persistence. Pure Python + NumPy, no Qt or OSC knowledge.

State machine:
    NORMAL      — Default. Persistence render, admit clean frames to history.
    REACQUIRE   — Evaluating frames after scrub or instability. Single-frame
                  render, no history admission until stable window achieved.

SCRUB is an instant transition (trigger_scrub → clear state → REACQUIRE).

References:
    docs/TELEMETRY_STABILIZER_SPEC.md (Phase 1 brief)
"""

import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Literal

import numpy as np


# =============================================================================
# STATE & RESULT TYPES
# =============================================================================

class StabilityState(Enum):
    """Stabilizer state machine states."""
    NORMAL = auto()
    REACQUIRE = auto()


@dataclass
class StabilizerResult:
    """Returned from every observe() call — directives for consumers.

    Phase 1: Visual gating only. Consumers use ``admissible_for_visual_history``
    and ``render_mode`` to control persistence display.

    Phase 2 Contract (DO NOT IMPLEMENT YET):
    - Capture pipelines must check ``admissible_for_visual_history`` (or a
      dedicated ``admissible_for_capture`` flag) before storing frames
    - Capture metadata (source, voltage, timestamp) is owned by the sweep
      runner, NOT the stabilizer — stabilizer only gates frame quality
    - TelemetryController capture mode (INTERNAL/EXTERNAL) remains unchanged;
      sweep runner tags snapshots with provenance
    """

    # Poison detection
    poisoned: bool
    poison_reason: str | None  # "zero_run", "nan_inf", "discontinuity", None

    # State machine
    stability_state: StabilityState

    # Directives for consumers
    clear_history: bool               # True on SCRUB transition
    admissible_for_visual_history: bool
    render_mode: Literal["single", "persistence"]

    # Metrics (for logging/tuning)
    similarity: float       # 0.0–1.0, vs previous frame
    stable_count: int       # consecutive stable frames
    required_count: int     # frames needed for stable window


# =============================================================================
# WAVEFORM STABILIZER
# =============================================================================

class WaveformStabilizer:
    """Data Integrity Gatekeeper for waveform telemetry frames.

    Observer-only: tags frames with stability decisions, never blocks delivery.
    Thread-safe via a reentrant lock for cross-thread observe/query.

    Usage:
        stabilizer = WaveformStabilizer()
        result = stabilizer.observe(frame, timestamp)
        if result.admissible_for_visual_history:
            persistence_buffer.append(frame)
    """

    # --- Thresholds (tune empirically, see Appendix A in spec) ---

    # Zero-run: 16+ consecutive exact 0.0 samples indicates buffer dropout.
    # At 1024 samples, this is ~1.5% of the frame as a contiguous block.
    ZERO_RUN_THRESHOLD = 16

    # Similarity: cosine similarity floor for "stable" classification.
    # 0.95 is strict but allows minor drift from noise/jitter.
    SIMILARITY_THRESHOLD = 0.95

    # Stable window: consecutive stable frames required to exit REACQUIRE.
    # At ~10 Hz frame rate, 6 frames ~ 600ms settling time.
    STABLE_WINDOW_FRAMES = 6

    # REACQUIRE timeout: fail-open for visuals after this duration.
    # Don't trap user in single-frame mode indefinitely.
    REACQUIRE_TIMEOUT_MS = 2000
    REACQUIRE_MIN_MS = 250  # Don't exit too quickly (debounce)

    # Discontinuity: max sample-to-sample delta for raw frame.
    # WARNING: May trigger false positives on saw/square edges.
    # Consider raising to 1.8-2.0 if saw waveforms show spurious poison flags.
    # For Phase 1 visual-only, false positives are low-risk (just resets counter).
    DISCONTINUITY_THRESHOLD = 1.5

    def __init__(self, debug: bool = False):
        self._lock = threading.RLock()
        self._state = StabilityState.NORMAL
        self._stable_count = 0
        self._prev_normalized: np.ndarray | None = None
        self._reacquire_entered_at: float | None = None
        self._pending_clear = False  # Set by trigger_scrub, consumed by next observe
        self.debug = debug

    # -----------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------

    def observe(self, frame: np.ndarray, timestamp: float) -> StabilizerResult:
        """Process incoming frame, return stability decisions.

        Args:
            frame: Raw waveform samples (1024 float64 expected).
            timestamp: time.time() of frame arrival.

        Returns:
            StabilizerResult with poison check, state, and directives.
        """
        with self._lock:
            # Consume pending clear from trigger_scrub()
            clear_history = self._pending_clear
            self._pending_clear = False

            # 1. Poison detection (on raw frame)
            poisoned, poison_reason = self._check_poison(frame)

            # 2. Normalize for metrics (does not mutate raw frame)
            normalized = self._normalize(frame)

            # 3. Similarity vs previous frame
            similarity = 0.0
            if self._prev_normalized is not None and not poisoned:
                similarity = self._compute_similarity(normalized, self._prev_normalized)

            # 4. Update stability counter
            self._update_stability(similarity, poisoned, timestamp)

            # 5. Store normalized frame for next comparison
            if not poisoned:
                self._prev_normalized = normalized
            # Poisoned frames don't update reference (would corrupt similarity)

            # 6. Build result
            in_reacquire = self._state == StabilityState.REACQUIRE
            admissible = (not poisoned) and (not in_reacquire)

            result = StabilizerResult(
                poisoned=poisoned,
                poison_reason=poison_reason,
                stability_state=self._state,
                clear_history=clear_history,
                admissible_for_visual_history=admissible,
                render_mode="single" if in_reacquire else "persistence",
                similarity=similarity,
                stable_count=self._stable_count,
                required_count=self.STABLE_WINDOW_FRAMES,
            )

            if self.debug:
                print(
                    f"[Stabilizer] state={self._state.name} "
                    f"similarity={result.similarity:.3f} "
                    f"stable={self._stable_count}/{self.STABLE_WINDOW_FRAMES} "
                    f"poisoned={result.poisoned} reason={result.poison_reason}"
                )

            return result

    def trigger_scrub(self) -> None:
        """Manual stabilize button pressed. Clear state, enter REACQUIRE."""
        with self._lock:
            self._state = StabilityState.REACQUIRE
            self._stable_count = 0
            self._prev_normalized = None
            self._reacquire_entered_at = time.time()
            self._pending_clear = True

            if self.debug:
                print("[Stabilizer] SCRUB triggered → REACQUIRE")

    def get_state(self) -> StabilityState:
        """Current state for UI display."""
        with self._lock:
            return self._state

    # -----------------------------------------------------------------
    # Poison detection
    # -----------------------------------------------------------------

    def _check_poison(self, frame: np.ndarray) -> tuple[bool, str | None]:
        """Run poison checks in priority order."""
        if self._detect_nan_inf(frame):
            return True, "nan_inf"
        if self._detect_zero_run(frame):
            return True, "zero_run"
        if self._detect_discontinuity(frame):
            return True, "discontinuity"
        return False, None

    @staticmethod
    def _detect_nan_inf(frame: np.ndarray) -> bool:
        """Any non-finite value (NaN, Inf, -Inf) = poison."""
        return not np.all(np.isfinite(frame))

    def _detect_zero_run(self, frame: np.ndarray) -> bool:
        """Contiguous exact 0.0 run > threshold samples = poison.

        For an active oscillator, 16+ consecutive samples at exactly 0.0
        indicates buffer clobber/dropout, not signal.
        """
        max_run = 0
        current_run = 0
        for sample in frame:
            if sample == 0.0:
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
            else:
                current_run = 0
        return max_run > self.ZERO_RUN_THRESHOLD

    def _detect_discontinuity(self, frame: np.ndarray) -> bool:
        """Extreme sample-to-sample jumps beyond plausible bound."""
        if len(frame) < 2:
            return False
        diffs = np.abs(np.diff(frame))
        return float(np.max(diffs)) > self.DISCONTINUITY_THRESHOLD

    # -----------------------------------------------------------------
    # Normalization (for metrics only — raw frames still go to consumers)
    # -----------------------------------------------------------------

    @staticmethod
    def _normalize(frame: np.ndarray) -> np.ndarray:
        """DC removal + amplitude normalization for shape comparison.

        Returns a new array; does not mutate the input.
        """
        if len(frame) == 0:
            return frame.astype(np.float64)
        result = frame.astype(np.float64) - np.mean(frame)
        peak = np.max(np.abs(result))
        if peak > 1e-10:
            result = result / peak
        return result

    # -----------------------------------------------------------------
    # Similarity metric
    # -----------------------------------------------------------------

    @staticmethod
    def _compute_similarity(current: np.ndarray, previous: np.ndarray) -> float:
        """Cosine similarity between two frames.

        Returns -1.0 to 1.0 (clamped). Near 1.0 = very similar shape.
        Uses proper normalization: dot(a, b) / (|a| * |b|).
        """
        if len(current) != len(previous) or len(current) == 0:
            return 0.0
        norm_a = np.linalg.norm(current)
        norm_b = np.linalg.norm(previous)
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0
        dot = np.dot(current, previous)
        return float(np.clip(dot / (norm_a * norm_b), -1.0, 1.0))

    # -----------------------------------------------------------------
    # State machine
    # -----------------------------------------------------------------

    def _update_stability(self, similarity: float, poisoned: bool, timestamp: float):
        """Update stable counter and manage REACQUIRE→NORMAL transitions."""
        if poisoned:
            self._stable_count = 0
            return

        if similarity >= self.SIMILARITY_THRESHOLD:
            self._stable_count += 1
        else:
            self._stable_count = 0

        # Only handle transitions when in REACQUIRE
        if self._state != StabilityState.REACQUIRE:
            return

        time_in_reacquire = self._time_in_reacquire_ms(timestamp)

        # Check for stable window achieved (with minimum time guard)
        if (self._stable_count >= self.STABLE_WINDOW_FRAMES
                and time_in_reacquire >= self.REACQUIRE_MIN_MS):
            self._transition_to_normal()
            return

        # Fail-open timeout
        if time_in_reacquire >= self.REACQUIRE_TIMEOUT_MS:
            self._transition_to_normal()

    def _time_in_reacquire_ms(self, timestamp: float) -> float:
        """Milliseconds since entering REACQUIRE state."""
        if self._reacquire_entered_at is None:
            return 0.0
        return (timestamp - self._reacquire_entered_at) * 1000.0

    def _transition_to_normal(self):
        """Exit REACQUIRE, return to NORMAL persistence mode."""
        self._state = StabilityState.NORMAL
        self._reacquire_entered_at = None

        if self.debug:
            print(f"[Stabilizer] → NORMAL (stable_count={self._stable_count})")
