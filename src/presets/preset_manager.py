"""
Preset manager - handles save/load operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .preset_schema import (
    PresetState,
    SlotState,
    ChannelState,
    MixerState,
    validate_preset,
    PRESET_VERSION,
)


class PresetError(Exception):
    """Raised when preset operations fail."""
    pass


class PresetManager:
    """
    Manages preset save/load operations.
    
    Usage:
        manager = PresetManager()
        
        # Save current state
        state = PresetState(
            name="My Patch",
            slots=[slot.get_state() for slot in generator_slots],
            mixer=mixer_panel.get_state(),
        )
        filepath = manager.save(state)
        
        # Load preset
        state = manager.load(filepath)
        for i, slot_state in enumerate(state.slots):
            generator_slots[i].set_state(slot_state)
        mixer_panel.set_state(state.mixer)
    """
    
    DEFAULT_DIR = Path.home() / "noise-engine-presets"
    
    def __init__(self, presets_dir: Optional[Path] = None):
        self.presets_dir = presets_dir or self.DEFAULT_DIR
        self.presets_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, state: PresetState, name: Optional[str] = None, overwrite: bool = False) -> Path:
        """
        Save preset to file.
        
        Args:
            state: PresetState to save
            name: Optional filename (without extension). If None, auto-generates.
            overwrite: If True, overwrite existing file. If False, add numeric suffix.
        
        Returns:
            Path to saved file
        """
        # Set metadata
        state.version = PRESET_VERSION
        state.created = datetime.now().isoformat()
        
        if name:
            state.name = name
            filename = self._sanitize_filename(name) + ".json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"preset_{timestamp}.json"
            if not state.name or state.name == "Untitled":
                state.name = f"Preset {timestamp}"
        
        filepath = self.presets_dir / filename
        
        # Handle existing file (only add suffix if not overwriting)
        if filepath.exists() and not overwrite:
            # Add numeric suffix
            base = filepath.stem
            counter = 1
            while filepath.exists():
                filepath = self.presets_dir / f"{base}_{counter}.json"
                counter += 1
        
        # Write file
        try:
            with open(filepath, "w") as f:
                f.write(state.to_json(indent=2))
        except IOError as e:
            raise PresetError(f"Failed to save preset: {e}")
        
        return filepath
    
    def load(self, filepath: Path) -> PresetState:
        """
        Load preset from file.
        
        Args:
            filepath: Path to preset JSON file
        
        Returns:
            PresetState object
        
        Raises:
            PresetError: If file doesn't exist, is invalid JSON, or fails validation
        """
        if not filepath.exists():
            raise PresetError(f"Preset file not found: {filepath}")
        
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PresetError(f"Invalid JSON in preset file: {e}")
        except IOError as e:
            raise PresetError(f"Failed to read preset file: {e}")
        
        # Validate
        is_valid, errors = validate_preset(data)
        if not is_valid:
            raise PresetError(f"Invalid preset: {'; '.join(errors)}")
        
        return PresetState.from_dict(data)
    
    def list_presets(self) -> list[Path]:
        """
        List all preset files in the presets directory.
        
        Returns:
            List of preset file paths, sorted by modification time (newest first)
        """
        presets = list(self.presets_dir.glob("*.json"))
        presets.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return presets
    
    def delete(self, filepath: Path) -> bool:
        """
        Delete a preset file.
        
        Args:
            filepath: Path to preset file
        
        Returns:
            True if deleted, False if file didn't exist
        """
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid filename characters."""
        invalid = '<>:"/\\|?*'
        result = name
        for char in invalid:
            result = result.replace(char, "_")
        return result.strip()


# Convenience functions for integration with main_frame

def collect_state(generator_slots: list, mixer_panel, master_section) -> PresetState:
    """
    Collect current state from UI components.
    
    Args:
        generator_slots: List of GeneratorSlot widgets
        mixer_panel: MixerPanel widget
        master_section: MasterSection widget
    
    Returns:
        PresetState with current values
    """
    slots = []
    for slot in generator_slots:
        slots.append(slot.get_state())
    
    channels = []
    for strip in mixer_panel.channel_strips:
        channels.append(strip.get_state())
    
    mixer = MixerState(
        channels=[ChannelState.from_dict(ch) for ch in channels],
        master_volume=master_section.get_volume(),
    )
    
    return PresetState(slots=slots, mixer=mixer)


def apply_state(state: PresetState, generator_slots: list, mixer_panel, master_section):
    """
    Apply preset state to UI components.
    
    Args:
        state: PresetState to apply
        generator_slots: List of GeneratorSlot widgets
        mixer_panel: MixerPanel widget  
        master_section: MasterSection widget
    """
    # Apply to generator slots
    for i, slot_state in enumerate(state.slots):
        if i < len(generator_slots):
            generator_slots[i].set_state(slot_state.to_dict())
    
    # Apply to mixer channels
    for i, channel_state in enumerate(state.mixer.channels):
        if i < len(mixer_panel.channel_strips):
            mixer_panel.channel_strips[i].set_state(channel_state.to_dict())
    
    # Apply master volume
    master_section.set_volume(state.mixer.master_volume)
