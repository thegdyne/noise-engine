"""
MIDI CC Learn Manager
Handles MIDI Learn mode - arming controls and capturing CC assignments

Per MIDI CC Control Spec v1.0 Section 4:
- One control armed at a time
- First CC received creates mapping
- Cancel via Escape or right-click again
- Learn replaces existing mapping on that control
"""

from PyQt5.QtCore import QObject, pyqtSignal


class MidiCCLearnManager(QObject):
    """Manages MIDI Learn mode for CC mapping."""

    # Signals
    learn_started = pyqtSignal(object)  # control
    learn_completed = pyqtSignal(int, int, object)  # channel, cc, control
    learn_cancelled = pyqtSignal(object)  # control (or None)

    def __init__(self, mapping_manager, parent=None):
        """Initialize learn manager.

        Args:
            mapping_manager: MidiCCMappingManager instance
            parent: Parent QObject
        """
        super().__init__(parent)
        self._mapping_manager = mapping_manager
        self._armed_control = None

    def start_learn(self, control):
        """Arm a control for MIDI Learn.

        Args:
            control: UI control widget to arm
        """
        # Cancel any existing learn first
        if self._armed_control is not None:
            self.cancel_learn()

        self._armed_control = control
        self.learn_started.emit(control)

    def cancel_learn(self):
        """Cancel current MIDI Learn operation."""
        control = self._armed_control
        self._armed_control = None
        self.learn_cancelled.emit(control)

    def is_learning(self):
        """Check if learn mode is active.

        Returns:
            True if a control is armed for learning
        """
        return self._armed_control is not None

    def get_armed_control(self):
        """Get the currently armed control.

        Returns:
            Armed control or None
        """
        return self._armed_control

    def on_cc_received(self, channel, cc, value):
        """Handle CC received during learn mode.

        Args:
            channel: MIDI channel (1-16)
            cc: CC number (0-127)
            value: CC value (0-127) - ignored for learn
        """
        if not self.is_learning():
            return

        control = self._armed_control
        self._armed_control = None

        # Remove any existing mapping for this control
        self._mapping_manager.remove_mapping(control)

        # Create new mapping
        self._mapping_manager.add_mapping(channel, cc, control)

        # Emit completion
        self.learn_completed.emit(channel, cc, control)