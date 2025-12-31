"""
MIDI CC Mapping Manager
Stores and manages CC → UI control mappings

Per MIDI CC Control Spec v1.0:
- Mapping key: (channel: 1-16, cc: 0-127)
- Device intentionally ignored in v1
- One CC can map to multiple controls (duplicates allowed)
- Pickup (soft takeover) state tracked per mapping
"""

from PyQt5.QtCore import QObject, pyqtSignal


class MidiCCMappingManager(QObject):
    """Manages MIDI CC to UI control mappings."""

    # Signals
    mapping_added = pyqtSignal(int, int, object)  # channel, cc, control
    mapping_removed = pyqtSignal(object)  # control
    mappings_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Mapping: (channel, cc) -> list of controls
        self._mappings = {}
        # Pickup state: (channel, cc) -> {control: caught}
        self._caught = {}

    def add_mapping(self, channel, cc, control):
        """Add mapping from (channel, cc) to control.

        Args:
            channel: MIDI channel (1-16)
            cc: CC number (0-127)
            control: UI control widget
        """
        key = (channel, cc)
        if key not in self._mappings:
            self._mappings[key] = []
        if control not in self._mappings[key]:
            self._mappings[key].append(control)
        # Initialize caught state
        if key not in self._caught:
            self._caught[key] = {}
        self._caught[key][control] = False
        self.mapping_added.emit(channel, cc, control)

    def get_controls(self, channel, cc):
        """Get list of controls mapped to (channel, cc).

        Args:
            channel: MIDI channel (1-16)
            cc: CC number (0-127)

        Returns:
            List of mapped controls (may be empty)
        """
        return self._mappings.get((channel, cc), [])

    def get_mapping_for_control(self, control):
        """Get (channel, cc) for a control, or None if not mapped.

        Args:
            control: UI control widget

        Returns:
            Tuple (channel, cc) or None
        """
        for key, controls in self._mappings.items():
            if control in controls:
                return key
        return None

    def remove_mapping(self, control):
        """Remove all mappings for a control.

        Args:
            control: UI control widget to unmap
        """
        for key in list(self._mappings.keys()):
            if control in self._mappings[key]:
                self._mappings[key].remove(control)
                if key in self._caught and control in self._caught[key]:
                    del self._caught[key][control]
            # Clean up empty entries
            if not self._mappings[key]:
                del self._mappings[key]
                if key in self._caught:
                    del self._caught[key]
        self.mapping_removed.emit(control)

    def clear_all(self):
        """Clear all mappings."""
        self._mappings.clear()
        self._caught.clear()
        self.mappings_cleared.emit()

    def is_caught(self, channel, cc, control):
        """Check if pickup is caught for this mapping.

        Args:
            channel: MIDI channel (1-16)
            cc: CC number (0-127)
            control: UI control widget

        Returns:
            True if caught (CC value has matched control value)
        """
        return self._caught.get((channel, cc), {}).get(control, False)

    def set_caught(self, channel, cc, control, caught):
        """Set caught state for this mapping.

        Args:
            channel: MIDI channel (1-16)
            cc: CC number (0-127)
            control: UI control widget
            caught: True if pickup caught
        """
        key = (channel, cc)
        if key in self._caught:
            self._caught[key][control] = caught

    def reset_pickup(self, channel, cc):
        """Reset caught state for all controls on (channel, cc).

        Args:
            channel: MIDI channel (1-16)
            cc: CC number (0-127)
        """
        key = (channel, cc)
        if key in self._caught:
            for control in self._caught[key]:
                self._caught[key][control] = False

    def reset_all_pickup(self):
        """Reset all caught states (e.g., on preset load)."""
        for key in self._caught:
            for control in self._caught[key]:
                self._caught[key][control] = False

    def has_mappings(self):
        """Check if any mappings exist.

        Returns:
            True if at least one mapping exists
        """
        return len(self._mappings) > 0

    def get_all_mappings(self):
        """Get all mappings for serialization.

        Returns:
            Dict of {(channel, cc): [controls]}
        """
        return dict(self._mappings)