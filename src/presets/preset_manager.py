"""
Preset manager - handles save/load operations.

R1.1: Added atomic writes, timestamp application, and write_preset_file.
"""

import json
import os
import tempfile
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
from .preset_utils import TimestampProvider, canonical_path


class PresetError(Exception):
    """Raised when preset operations fail."""
    pass


class PresetManager:
    """
    Manages preset save/load operations.

    R1.1 features:
    - Atomic writes via write_preset_file
    - Timestamp application for created/updated
    - Support for preset browser operations

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

    def write_preset_file(
        self,
        dest_path: Path,
        preset_state: PresetState,
        *,
        allow_overwrite: bool = True
    ) -> None:
        """
        Write preset to file atomically.

        R1.1 canonical write entry point per spec:
        1. Serialize full preset state via to_dict() then json.dumps(indent=2)
        2. Write temp file in dirname(dest_path)
        3. Commit using os.replace(temp, dest_path) if allow_overwrite=True
        4. If allow_overwrite=False, fail if dest_path already exists

        Args:
            dest_path: Destination file path
            preset_state: PresetState to write
            allow_overwrite: If False, raise PresetError if dest_path exists

        Raises:
            PresetError: If write fails or file exists when allow_overwrite=False
        """
        dest_path = Path(dest_path)

        # Check overwrite permission
        if not allow_overwrite and dest_path.exists():
            raise PresetError(f"File already exists: {dest_path}")

        # Ensure directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize
        data = preset_state.to_dict()
        json_str = json.dumps(data, indent=2)

        # Atomic write: temp file in same directory, then os.replace
        try:
            # Create temp file in same directory for atomic replace
            fd, temp_path = tempfile.mkstemp(
                suffix='.tmp',
                prefix='.preset_',
                dir=dest_path.parent
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                os.replace(temp_path, dest_path)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            raise PresetError(f"Failed to write preset: {e}")

    def apply_timestamps(
        self,
        state: PresetState,
        operation_timestamp: str
    ) -> None:
        """
        Apply timestamp rules to preset state per R1.1 spec.

        - If state.created is empty: set state.created = operation_timestamp
        - Set state.updated = operation_timestamp

        Args:
            state: PresetState to modify in-place
            operation_timestamp: ISO 8601 timestamp from TimestampProvider
        """
        if not state.created:
            state.created = operation_timestamp
        state.updated = operation_timestamp

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
        # Generate timestamp
        operation_timestamp = TimestampProvider.now()

        # Set metadata
        state.version = PRESET_VERSION
        self.apply_timestamps(state, operation_timestamp)

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

        # Write file atomically
        self.write_preset_file(filepath, state, allow_overwrite=overwrite or not filepath.exists())

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
