"""
MidiCCController - Handles MIDI CC mapping, learn mode, and flood control.

Extracted from MainFrame as Phase 2 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QWidget
from PyQt5.QtCore import QTimer

from src.midi import MidiCCMappingManager, MidiCCLearnManager
from src.utils.logger import logger


class MidiCCController:
    """Handles MIDI CC mapping, learn mode, and flood control."""
    
    def __init__(self, main_frame):
        self.main = main_frame
        
        # MIDI CC managers
        self.cc_mapping_manager = MidiCCMappingManager()
        self.cc_learn_manager = MidiCCLearnManager(self.cc_mapping_manager)
        
        # MIDI CC flood control (~60Hz update rate)
        self._pending_cc = {}  # (channel, cc) -> value
        self._cc_timer = QTimer(main_frame)
        self._cc_timer.timeout.connect(self._process_pending_cc)
        self._cc_timer.start(16)  # ~60Hz
        
        # MIDI mapping tracking
        self._current_midi_mapping_name = None
        self._current_midi_mapping_path = None
    
    def _setup_midi_menu(self):
        """Create MIDI menu in menu bar."""
        menu_bar = self.main.menuBar()
        midi_menu = menu_bar.addMenu("MIDI")

        midi_menu.addAction("Save Mappings", self.save_midi_mappings)
        midi_menu.addAction("Save Mappings As...", self.save_midi_mappings_as)
        midi_menu.addSeparator()
        midi_menu.addAction("Load Mappings...", self.load_midi_mappings)
        midi_menu.addSeparator()
        midi_menu.addAction("Clear All Mappings", self.clear_all_midi_mappings)

    def _on_midi_cc(self, channel, cc, value):
        """Handle MIDI CC from OSC bridge."""
        if self.cc_learn_manager.is_learning():
            self.cc_learn_manager.on_cc_received(channel, cc, value)
        else:
            self._pending_cc[(channel, cc)] = value

    def _process_pending_cc(self):
        """Process buffered CC updates (~60Hz)."""
        if not self._pending_cc:
            return

        pending = dict(self._pending_cc)
        self._pending_cc.clear()

        for (channel, cc), value in pending.items():
            controls = self.cc_mapping_manager.get_controls(channel, cc)
            for control in controls:
                self._apply_cc_to_control(control, channel, cc, value)

    def _apply_cc_to_control(self, control, channel, cc, value):
        """Apply CC value to a control with pickup mode."""
        if hasattr(control, 'handle_cc'):
            should_activate = control.handle_cc(value)
            if should_activate:
                if hasattr(control, 'cycle_forward'):
                    control.cycle_forward()
                else:
                    control.click()
            return

        if not hasattr(control, 'minimum') or not hasattr(control, 'maximum'):
            return

        # Use cc_range() for controls with fine mode, else full slider range
        if hasattr(control, 'cc_range'):
            min_val, max_val = control.cc_range()
        else:
            min_val = control.minimum()
            max_val = control.maximum()
        param_range = max_val - min_val
        cc_scaled = min_val + (value / 127.0) * param_range
        eps = (param_range / 127.0) * 3

        is_caught = self.cc_mapping_manager.is_caught(channel, cc, control)

        if not is_caught:
            current_val = control.value()
            if abs(cc_scaled - current_val) <= eps:
                self.cc_mapping_manager.set_caught(channel, cc, control, True)
                control.setValue(int(cc_scaled))
                if hasattr(control, 'set_cc_ghost'):
                    control.set_cc_ghost(None)
            else:
                if hasattr(control, 'set_cc_ghost'):
                    ghost_norm = value / 127.0
                    control.set_cc_ghost(ghost_norm)
        else:
            control.setValue(int(cc_scaled))

    def _on_learn_started(self, control):
        """Visual feedback when MIDI Learn starts."""
        if hasattr(control, 'set_midi_armed'):
            control.set_midi_armed(True)
        logger.info(f"MIDI Learn armed: {control.objectName()}", component="MIDI")

    def _on_learn_completed(self, channel, cc, control):
        """Visual feedback when MIDI Learn completes."""
        if hasattr(control, 'set_midi_armed'):
            control.set_midi_armed(False)
        if hasattr(control, 'set_midi_mapped'):
            control.set_midi_mapped(True)

        existing = self.cc_mapping_manager.get_controls(channel, cc)
        other_controls = [c for c in existing if c != control]
        if other_controls:
            names = [c.objectName() for c in other_controls if c.objectName()]
            if names:
                self.main._show_toast(f"CC{cc} also mapped to: {', '.join(names)}")

        logger.info(f"MIDI mapped: Ch{channel} CC{cc} -> {control.objectName()}", component="MIDI")
        self._update_midi_status()

    def _on_learn_cancelled(self, control):
        """Visual feedback when MIDI Learn cancelled."""
        if control and hasattr(control, 'set_midi_armed'):
            control.set_midi_armed(False)
        logger.info("MIDI Learn cancelled", component="MIDI")

    def _find_control_by_name(self, name):
        """Find a control widget by objectName (includes telemetry window)."""
        result = self.main.findChild(QWidget, name)
        if result is None:
            tw = getattr(self.main, '_telemetry_widget', None)
            if tw is not None:
                result = tw.findChild(QWidget, name)
        return result

    def save_midi_mappings(self):
        """Save MIDI mappings - dialog pre-fills with current name."""
        data = self.cc_mapping_manager.to_dict()
        if not data:
            logger.info("No MIDI mappings to save", component="MIDI")
            return

        midi_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'midi_mappings')
        os.makedirs(midi_dir, exist_ok=True)

        if self._current_midi_mapping_name:
            default_path = os.path.join(midi_dir, f"{self._current_midi_mapping_name}.json")
        else:
            default_path = midi_dir

        path, _ = QFileDialog.getSaveFileName(
            self.main, "Save MIDI Mappings", default_path, "JSON Files (*.json)"
        )
        if path:
            if not path.endswith('.json'):
                path += '.json'
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            self._current_midi_mapping_name = Path(path).stem
            self._current_midi_mapping_path = path
            logger.info(f"Saved MIDI mappings to {path}", component="MIDI")

    def save_midi_mappings_as(self):
        """Save MIDI mappings as new file - dialog starts blank."""
        data = self.cc_mapping_manager.to_dict()
        if not data:
            logger.info("No MIDI mappings to save", component="MIDI")
            return

        midi_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'midi_mappings')
        os.makedirs(midi_dir, exist_ok=True)

        path, _ = QFileDialog.getSaveFileName(
            self.main, "Save MIDI Mappings As", midi_dir, "JSON Files (*.json)"
        )
        if path:
            if not path.endswith('.json'):
                path += '.json'
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            self._current_midi_mapping_name = Path(path).stem
            self._current_midi_mapping_path = path
            logger.info(f"Saved MIDI mappings to {path}", component="MIDI")

    def load_midi_mappings(self):
        """Load MIDI mappings from file."""
        midi_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'midi_mappings')
        os.makedirs(midi_dir, exist_ok=True)

        path, _ = QFileDialog.getOpenFileName(
            self.main, "Load MIDI Mappings", midi_dir, "JSON Files (*.json)"
        )
        if path:
            with open(path, 'r') as f:
                data = json.load(f)
            self.cc_mapping_manager.from_dict(data, self._find_control_by_name)
            self._current_midi_mapping_name = Path(path).stem
            self._current_midi_mapping_path = path
            logger.info(f"Loaded MIDI mappings from {path}", component="MIDI")
        self._update_midi_status()

    def clear_all_midi_mappings(self):
        """Clear all MIDI mappings."""
        for controls in self.cc_mapping_manager.get_all_mappings().values():
            for control in controls:
                if hasattr(control, 'set_midi_mapped'):
                    control.set_midi_mapped(False)
        self.cc_mapping_manager.clear_all()
        self._current_midi_mapping_name = None
        self._current_midi_mapping_path = None
        logger.info("Cleared all MIDI mappings", component="MIDI")
        self._update_midi_status()

    def _update_midi_status(self):
        """Update MIDI status label with mapping count."""
        from src.gui.theme import COLORS
        count = len(self.cc_mapping_manager.to_dict())
        if count == 0:
            self.main.midi_status_label.setText("MIDI: Ready")
            self.main.midi_status_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        else:
            self.main.midi_status_label.setText(f"MIDI: {count} mapped")
            self.main.midi_status_label.setStyleSheet(f"color: {COLORS['enabled_text']};")
