# Preset System - Minimal Spec

**Status:** Building Now  
**Goal:** Save and load patches. Nothing fancy.

---

## Scope (v1)

**In scope:**
- Save all 8 generator slots (type + params + settings)
- Save mixer state (volume, pan, mute)
- Save master volume
- JSON files in `~/noise-engine-presets/`
- File picker for load, auto-name for save

**Out of scope (for now):**
- Preset browser UI
- Categories/tags
- Modulation routing
- FX settings
- EQ/Compressor/Limiter settings
- Cloud sync

---

## JSON Schema

```json
{
  "version": 1,
  "name": "My Preset",
  "created": "2025-12-20T12:00:00Z",
  "slots": [
    {
      "generator": "Subtractive",
      "params": {
        "frequency": 0.5,
        "cutoff": 0.7,
        "resonance": 0.3,
        "attack": 0.1,
        "decay": 0.4,
        "custom_0": 0.5,
        "custom_1": 0.5,
        "custom_2": 0.5,
        "custom_3": 0.5,
        "custom_4": 0.5
      },
      "filter_type": 0,
      "env_source": 1,
      "clock_rate": 4,
      "midi_channel": 1
    }
  ],
  "mixer": {
    "channels": [
      {"volume": 0.8, "pan": 0.5, "mute": false, "solo": false}
    ],
    "master_volume": 0.8
  }
}
```

**Notes:**
- `params` values are normalized 0-1 (UI slider values / 1000)
- `filter_type`: 0=LP, 1=HP, 2=BP
- `env_source`: 0=OFF, 1=CLK, 2=MIDI
- `clock_rate`: 0-12 index into clock divisions
- Empty slots have `"generator": null`

---

## Files to Create

```
src/
├── presets/
│   ├── __init__.py
│   ├── preset_manager.py    # save/load logic
│   └── preset_schema.py     # validation
```

---

## API

```python
# preset_manager.py

class PresetManager:
    def __init__(self, presets_dir: Path = None):
        self.presets_dir = presets_dir or Path.home() / "noise-engine-presets"
        self.presets_dir.mkdir(exist_ok=True)
    
    def save(self, state: dict, name: str = None) -> Path:
        """Save preset, returns filepath."""
        pass
    
    def load(self, filepath: Path) -> dict:
        """Load preset, returns state dict."""
        pass
    
    def list_presets(self) -> list[Path]:
        """List all preset files."""
        pass
```

---

## State Extraction

Need methods on main_frame or generator_slot to get current state:

```python
# generator_slot.py
def get_state(self) -> dict:
    return {
        "generator": self.generator_type,
        "params": {
            "frequency": self.sliders["frequency"].value() / 1000,
            "cutoff": self.sliders["cutoff"].value() / 1000,
            # ...
        },
        "filter_type": self.filter_type_index,
        "env_source": self.env_source_index,
        "clock_rate": self.clock_rate_index,
        "midi_channel": self.midi_channel,
    }

def set_state(self, state: dict):
    if state["generator"]:
        self.set_generator(state["generator"])
    for param, value in state["params"].items():
        self.sliders[param].setValue(int(value * 1000))
    # ...
```

---

## UI Integration

**Option A: Menu items (simplest)**
- File → Save Preset (Cmd+S)
- File → Load Preset (Cmd+O)

**Option B: Toolbar buttons**
- [SAVE] [LOAD] in header bar

**Decision:** Start with menu items. Can add toolbar later.

---

## Implementation Order

1. Create `preset_schema.py` with validation
2. Create `preset_manager.py` with save/load
3. Add `get_state()` / `set_state()` to generator_slot.py
4. Add `get_state()` / `set_state()` to mixer_panel.py
5. Wire up menu items in main_frame.py
6. Test save → quit → load cycle

---

## File Naming

Auto-generated: `preset_YYYYMMDD_HHMMSS.json`

User can rename in file picker or filesystem.
