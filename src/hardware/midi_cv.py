"""
MIDI-CV Controller for CV.OCD hardware.

Sends MIDI CC messages to CV.OCD which converts them to control voltages.
Default configuration assumes CV.OCD's CVA output is mapped to CC1 on channel 1.

Hardware chain:
    Python -> MOTU M6 MIDI Out -> CV.OCD -> CVA -> Buchla 258 Morph CV
"""

import time
from typing import Optional

import mido


class MidiCV:
    """Controller for sending CV via MIDI to CV.OCD."""

    # Default CV.OCD configuration: CVA responds to CC1 on channel 1
    DEFAULT_CC = 1
    DEFAULT_CHANNEL = 0  # mido uses 0-indexed channels

    def __init__(
        self,
        port_name: Optional[str] = None,
        cc_number: int = DEFAULT_CC,
        channel: int = DEFAULT_CHANNEL,
    ):
        """
        Initialize MIDI-CV controller.

        Args:
            port_name: MIDI output port name. If None, lists available ports.
            cc_number: CC number for CV.OCD CVA (default: 1)
            channel: MIDI channel 0-15 (default: 0 for channel 1)
        """
        self.cc_number = cc_number
        self.channel = channel
        self._port: Optional[mido.ports.BaseOutput] = None
        self._port_name = port_name

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @staticmethod
    def list_ports() -> list[str]:
        """List available MIDI output ports."""
        return mido.get_output_names()

    def open(self) -> None:
        """Open the MIDI port."""
        if self._port is not None:
            return

        if self._port_name is None:
            ports = self.list_ports()
            if not ports:
                raise RuntimeError("No MIDI output ports available")
            print(f"Available MIDI ports: {ports}")
            raise ValueError("port_name required. See available ports above.")

        self._port = mido.open_output(self._port_name)

    def close(self) -> None:
        """Close the MIDI port."""
        if self._port is not None:
            self._port.close()
            self._port = None

    def send_cv(self, value: int) -> None:
        """
        Send a CV value (0-127) via MIDI CC.

        Args:
            value: CC value 0-127 (maps to 0-10V on CV.OCD)
        """
        if self._port is None:
            raise RuntimeError("Port not open. Call open() first.")

        value = max(0, min(127, int(value)))
        msg = mido.Message('control_change',
                          channel=self.channel,
                          control=self.cc_number,
                          value=value)
        self._port.send(msg)

    def send_cv_normalized(self, value: float) -> None:
        """
        Send a normalized CV value (0.0-1.0).

        Args:
            value: Normalized value 0.0-1.0
        """
        cc_value = int(value * 127)
        self.send_cv(cc_value)

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


def find_motu_port() -> Optional[str]:
    """Find MOTU M6 MIDI port by name pattern."""
    ports = MidiCV.list_ports()
    for port in ports:
        if 'MOTU' in port.upper() or 'M6' in port:
            return port
    return None
