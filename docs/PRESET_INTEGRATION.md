# Preset Integration Guide

Add these methods to existing classes to enable preset save/load.

---

## 1. GeneratorSlot (src/gui/generator_slot.py)

Add these methods:

```python
def get_state(self) -> dict:
    """Get current slot state for preset save."""
    return {
        "generator": self.generator_type,
        "params": {
            "frequency": self._get_slider_value("frequency"),
            "cutoff": self._get_slider_value("cutoff"),
            "resonance": self._get_slider_value("resonance"),
            "attack": self._get_slider_value("attack"),
            "decay": self._get_slider_value("decay"),
            "custom_0": self._get_slider_value("custom_0"),
            "custom_1": self._get_slider_value("custom_1"),
            "custom_2": self._get_slider_value("custom_2"),
            "custom_3": self._get_slider_value("custom_3"),
            "custom_4": self._get_slider_value("custom_4"),
        },
        "filter_type": self.filter_type_button.current_index,
        "env_source": self.env_source_button.current_index,
        "clock_rate": self.clock_rate_button.current_index,
        "midi_channel": self.midi_channel,
    }

def _get_slider_value(self, param: str) -> float:
    """Get normalized slider value (0-1)."""
    slider = self.sliders.get(param)
    if slider:
        return slider.value() / 1000.0
    return 0.5

def set_state(self, state: dict):
    """Apply state from preset load."""
    # Set generator type first (this resets params)
    gen = state.get("generator")
    if gen:
        self.set_generator(gen)
    else:
        self.clear_generator()
        return
    
    # Set params
    params = state.get("params", {})
    for param, value in params.items():
        self._set_slider_value(param, value)
    
    # Set buttons
    ft = state.get("filter_type", 0)
    self.filter_type_button.set_index(ft)
    
    es = state.get("env_source", 0)
    self.env_source_button.set_index(es)
    
    cr = state.get("clock_rate", 4)
    self.clock_rate_button.set_index(cr)
    
    mc = state.get("midi_channel", 1)
    self.set_midi_channel(mc)

def _set_slider_value(self, param: str, value: float):
    """Set slider from normalized value (0-1)."""
    slider = self.sliders.get(param)
    if slider:
        slider.setValue(int(value * 1000))
```

---

## 2. ChannelStrip (src/gui/mixer_panel.py)

Add to ChannelStrip class:

```python
def get_state(self) -> dict:
    """Get current channel state for preset save."""
    return {
        "volume": self.volume_fader.value() / 1000.0,
        "pan": self.pan_slider.value() / 1000.0,
        "mute": self.mute_button.isChecked(),
        "solo": self.solo_button.isChecked(),
    }

def set_state(self, state: dict):
    """Apply state from preset load."""
    vol = state.get("volume", 0.8)
    self.volume_fader.setValue(int(vol * 1000))
    
    pan = state.get("pan", 0.5)
    self.pan_slider.setValue(int(pan * 1000))
    
    mute = state.get("mute", False)
    self.mute_button.setChecked(mute)
    
    solo = state.get("solo", False)
    self.solo_button.setChecked(solo)
```

---

## 3. MasterSection (src/gui/master_section.py)

Add these methods:

```python
def get_volume(self) -> float:
    """Get master volume as normalized 0-1 value."""
    return self.master_fader.value() / 1000.0

def set_volume(self, value: float):
    """Set master volume from normalized 0-1 value."""
    self.master_fader.setValue(int(value * 1000))
```

---

## 4. MainFrame (src/gui/main_frame.py)

Add preset manager and menu items:

```python
# In __init__:
from src.presets import PresetManager, PresetState, collect_state, apply_state

self.preset_manager = PresetManager()
self._setup_preset_menu()

# Add method:
def _setup_preset_menu(self):
    """Add preset menu items."""
    menu_bar = self.menuBar()
    file_menu = menu_bar.addMenu("File")
    
    save_action = QAction("Save Preset", self)
    save_action.setShortcut("Ctrl+S")
    save_action.triggered.connect(self._save_preset)
    file_menu.addAction(save_action)
    
    load_action = QAction("Load Preset", self)
    load_action.setShortcut("Ctrl+O")
    load_action.triggered.connect(self._load_preset)
    file_menu.addAction(load_action)

def _save_preset(self):
    """Save current state to preset file."""
    from PyQt5.QtWidgets import QFileDialog, QMessageBox
    
    # Collect state
    state = collect_state(
        self.generator_slots,
        self.mixer_panel,
        self.master_section,
    )
    
    # Get filename from user
    filepath, _ = QFileDialog.getSaveFileName(
        self,
        "Save Preset",
        str(self.preset_manager.presets_dir),
        "Preset Files (*.json)",
    )
    
    if filepath:
        try:
            name = Path(filepath).stem
            saved_path = self.preset_manager.save(state, name)
            QMessageBox.information(self, "Saved", f"Preset saved to:\n{saved_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save preset:\n{e}")

def _load_preset(self):
    """Load preset from file."""
    from PyQt5.QtWidgets import QFileDialog, QMessageBox
    
    filepath, _ = QFileDialog.getOpenFileName(
        self,
        "Load Preset",
        str(self.preset_manager.presets_dir),
        "Preset Files (*.json)",
    )
    
    if filepath:
        try:
            state = self.preset_manager.load(Path(filepath))
            apply_state(
                state,
                self.generator_slots,
                self.mixer_panel,
                self.master_section,
            )
            QMessageBox.information(self, "Loaded", f"Preset loaded:\n{state.name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load preset:\n{e}")
```

---

## 5. File Structure

Create the presets module:

```
src/
├── presets/
│   ├── __init__.py          # Copy from presets_init.py
│   ├── preset_schema.py     # Copy from preset_schema.py
│   └── preset_manager.py    # Copy from preset_manager.py
```

---

## 6. Test It

1. Start the app
2. Set up some generators with different params
3. File → Save Preset (Cmd+S)
4. Change everything
5. File → Load Preset (Cmd+O)
6. Verify state restored

---

## Notes

- The `sliders` dict in GeneratorSlot needs to include custom params (custom_0 through custom_4)
- If your slider names differ (e.g., "freq" vs "frequency"), adjust the param keys
- The `set_generator()` method should already exist and handle starting the generator
- CycleButton needs a `set_index(i)` method if it doesn't exist (just sets `current_index` and updates display)
