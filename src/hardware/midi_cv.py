"""
MIDI-to-CV control wrapper for CV.OCD with voltage calibration.

Sends MIDI CC messages to CV.OCD which converts them to control voltages.
Supports calibrated voltage output and bipolar mode for hardware profiling.

Hardware chain:
    Python -> MOTU M6 MIDI Out -> CV.OCD -> CVA -> Buchla 258 Morph CV

Requirements satisfied:
    R5: Enhanced MIDI port detection with priority list
    R6: Voltage calibration support (vmax_calibrated)
    R9: cv_range is in volts at CV.OCD output
    R10: Bipolar mode (0V = CC 64, safe = CC 64)
    R11: Return actual CC sent (post-clamp, post-round)
    R12: Consistent mapping in volts_to_cc() and send_cv_volts()
"""

import time
from typing import List, Optional

import mido

try:
    from src.utils.logger import logger
except ImportError:
    # Standalone usage fallback
    import logging
    logger = logging.getLogger(__name__)


def find_preferred_port(preferred_substrings: List[str] = None) -> Optional[str]:
    """
    Find MIDI output port matching preferred substrings (R5).

    Searches for CV.OCD first, then MOTU as fallback.

    Args:
        preferred_substrings: Priority list (default: ["CV.OCD", "CV-OCD", "MOTU", "M6"])

    Returns:
        First matching port name or None
    """
    if preferred_substrings is None:
        preferred_substrings = ["CV.OCD", "CV-OCD", "MOTU", "M6"]

    outputs = mido.get_output_names()

    for substring in preferred_substrings:
        matches = [p for p in outputs if substring in p]
        if matches:
            logger.info(f"[MIDI CV] Found port matching '{substring}': {matches[0]}")
            return matches[0]

    logger.warning(f"[MIDI CV] No preferred ports found. Available: {outputs}")
    return None


# Legacy alias for backwards compatibility
def find_motu_port() -> Optional[str]:
    """Find MOTU M6 MIDI port by name pattern (legacy alias)."""
    return find_preferred_port(["MOTU", "M6"])


class MidiCV:
    """
    MIDI-to-CV control with voltage calibration (R6, R10, R11, R12).

    Sends CC messages to CV.OCD for controlling external hardware.
    Supports both unipolar (0-Vmax) and bipolar (-Vmax/2 to +Vmax/2) modes.
    """

    # Default CV.OCD configuration: CVA responds to CC1 on channel 1
    DEFAULT_CC = 1
    DEFAULT_CHANNEL = 0  # mido uses 0-indexed channels

    def __init__(
        self,
        port_name: str,
        cc_number: int = DEFAULT_CC,
        channel: int = DEFAULT_CHANNEL,
        vmax_calibrated: float = 5.0,
        mode: str = 'unipolar'
    ):
        """
        Initialize MIDI CV controller.

        Args:
            port_name: MIDI output port name
            cc_number: MIDI CC number (1 = CV.OCD CVA)
            channel: MIDI channel 0-15 (0 = channel 1)
            vmax_calibrated: Measured max voltage at CC=127 (R6)
            mode: 'unipolar' (0-Vmax) or 'bipolar' (-Vmax/2 to +Vmax/2) (R10)
        """
        self.port_name = port_name
        self.cc = cc_number
        self.channel = channel
        self.vmax = vmax_calibrated
        self.mode = mode
        self.port = None
        self._is_open = False

        # R10: Safe neutral value
        self.safe_cc = 64 if mode == 'bipolar' else 0

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open(self):
        """Open MIDI port."""
        if self._is_open:
            return

        try:
            self.port = mido.open_output(self.port_name)
            self._is_open = True
            logger.info(f"[MIDI CV] Opened {self.port_name}")
        except Exception as e:
            logger.error(f"[MIDI CV] Failed to open {self.port_name}: {e}")
            raise

    def close(self):
        """Close MIDI port."""
        if self.port:
            self.port.close()
            self.port = None
            self._is_open = False

    def send_cv(self, value: int) -> int:
        """
        Send raw MIDI CC value (0-127).

        Args:
            value: MIDI CC value 0-127

        Returns:
            Actual CC value sent (clamped)
        """
        if not self.port:
            raise RuntimeError("MIDI port not open")

        val = max(0, min(127, int(value)))
        msg = mido.Message('control_change',
                          channel=self.channel,
                          control=self.cc,
                          value=val)
        self.port.send(msg)
        return val

    def volts_to_cc(self, volts: float) -> int:
        """
        Convert volts to CC value using calibration (R11, R12).

        CRITICAL: This mapping MUST match send_cv_volts() exactly.

        Args:
            volts: Target voltage

        Returns:
            MIDI CC value 0-127 (clamped, rounded)
        """
        if self.mode == 'unipolar':
            # Map 0-Vmax to CC 0-127
            safe_volts = max(0.0, min(volts, self.vmax))
            cc_val = round((safe_volts / self.vmax) * 127)
        else:  # bipolar
            # Map -Vmax/2 to +Vmax/2 → CC 0-127
            # R10: 0V = CC 64
            volts_offset = volts + (self.vmax / 2)
            safe_volts = max(0.0, min(volts_offset, self.vmax))
            cc_val = round((safe_volts / self.vmax) * 127)

        return max(0, min(127, cc_val))

    def send_cv_volts(self, volts: float) -> int:
        """
        Send voltage using calibration (R6, R11, R12).

        CRITICAL: Returns actual CC sent for recording (R11).

        Args:
            volts: Target voltage

        Returns:
            Actual CC value sent (for recording in snapshot)
        """
        cc_val = self.volts_to_cc(volts)
        self.send_cv(cc_val)
        return cc_val  # R11: Return actual CC for recording

    def send_cv_normalized(self, value: float) -> int:
        """
        Send a normalized CV value (0.0-1.0).

        Args:
            value: Normalized value 0.0-1.0

        Returns:
            Actual CC value sent
        """
        cc_value = int(value * 127)
        return self.send_cv(cc_value)

    def send_safe(self):
        """Send safe neutral value (R10, R14)."""
        self.send_cv(self.safe_cc)

    def sweep(
        self,
        start: int = 0,
        end: int = 127,
        step: int = 1,
        delay: float = 0.1,
        callback=None,
    ) -> None:
        """
        Sweep through CV values.

        Args:
            start: Starting CC value (0-127)
            end: Ending CC value (0-127)
            step: Step size (negative to sweep down)
            delay: Delay between steps in seconds
            callback: Optional callback(value) called after each step
        """
        if start <= end:
            values = range(start, end + 1, abs(step))
        else:
            values = range(start, end - 1, -abs(step))

        for value in values:
            self.send_cv(value)
            if callback:
                callback(value)
            time.sleep(delay)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @staticmethod
    def list_ports() -> List[str]:
        """List all available MIDI output ports."""
        return mido.get_output_names()
