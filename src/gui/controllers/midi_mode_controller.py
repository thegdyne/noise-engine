"""
MidiModeController - Handles MIDI mode toggle for all generators.

Extracted from MainFrame as Phase 7 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from src.gui.theme import COLORS, FONT_SIZES
from src.utils.logger import logger


class MidiModeController:
    """Handles MIDI mode toggle for all generators."""
    
    def __init__(self, main_frame):
        self.main = main_frame

    def _midi_mode_btn_style(self, active):
        """Return style for MIDI mode button."""
        if active:
            return f"""
                QPushButton {{
                    background-color: #660066;
                    color: #ff00ff;
                    border: 1px solid #ff00ff;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: {FONT_SIZES['small']}px;
                    font-weight: bold;
                }}
                QPushButton:disabled {{
                    background-color: #220022;
                    color: #440044;
                    border-color: #330033;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: {FONT_SIZES['small']}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #330033;
                    color: #ff00ff;
                    border-color: #aa00aa;
                }}
                QPushButton:disabled {{
                    background-color: {COLORS['background']};
                    color: {COLORS['border']};
                    border-color: {COLORS['border']};
                }}
            """

    def _toggle_midi_mode(self):
        """Toggle all generators to/from MIDI mode."""
        if not self.main._midi_mode_active:
            self.main._midi_mode_changing = True
            for i, slot in enumerate(self.main.generator_grid.slots.values()):
                self.main._midi_mode_saved_states[i] = slot.env_source
                if slot.env_source != 2:
                    slot.env_btn.set_index(2)
                    slot.on_env_source_changed("MIDI")
            self.main._midi_mode_changing = False
            self.main._midi_mode_active = True
            logger.info("MIDI mode activated", component="APP")
        else:
            self._restore_midi_mode_states()
        
        self.main.midi_mode_btn.setChecked(self.main._midi_mode_active)
        self.main.midi_mode_btn.setStyleSheet(self._midi_mode_btn_style(self.main._midi_mode_active))

    def _restore_midi_mode_states(self):
        """Restore saved env_source states."""
        from src.config import ENV_SOURCES
        self.main._midi_mode_changing = True
        for i, slot in enumerate(self.main.generator_grid.slots.values()):
            saved = self.main._midi_mode_saved_states[i]
            slot.env_btn.set_index(saved)
            slot.on_env_source_changed(ENV_SOURCES[saved])
        self.main._midi_mode_changing = False
        self.main._midi_mode_active = False
        logger.info("MIDI mode deactivated", component="APP")

    def _deactivate_midi_mode(self):
        """Deactivate MIDI mode without restoring (user made manual change)."""
        self.main._midi_mode_active = False
        self.main.midi_mode_btn.setChecked(False)
        self.main.midi_mode_btn.setStyleSheet(self._midi_mode_btn_style(False))
        logger.info("MIDI mode cancelled (manual change)", component="APP")
