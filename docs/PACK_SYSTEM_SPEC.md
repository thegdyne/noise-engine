# Noise Engine Pack System Specification

**Version:** 1.0  
**Status:** Approved  
**Author:** Gareth / Claude  
**Date:** December 2025  

---

## 1. Overview

### 1.1 Purpose

The Pack System allows Noise Engine to organise generators into selectable packs. When a pack is selected, only generators from that pack are available in the generator dropdowns across all 8 slots.

### 1.2 Key Behaviours

- **Exclusive selection:** Selecting a pack filters all generator dropdowns to show only that pack's generators
- **Global scope:** Pack selection affects all 8 slots simultaneously  
- **Instant switching:** Changing packs resets all slots to "Empty" (first generator in pack)
- **Demo-friendly:** Perfect for focused presentations — select "Classic Synths" and only show those 4 generators

### 1.3 Terminology

| Term | Definition |
|------|------------|
| **Core** | Built-in generators that ship with Noise Engine |
| **Pack** | A collection of related generators with a manifest |
| **Manifest** | JSON file describing a pack's metadata and contents |
| **Generator** | A JSON + SCD file pair defining a synthesizer |

---

## 2. Directory Structure

### 2.1 Layout

```
noise-engine/
├── supercollider/
│   └── generators/              # Core generators (ship with app)
│       ├── saw.json
│       ├── saw.scd
│       ├── square.json
│       ├── square.scd
│       └── ...
│
└── packs/                       # User/add-on packs
    ├── classic_synths/
    │   ├── manifest.json
    │   └── generators/
    │       ├── tb303.json
    │       ├── tb303.scd
    │       ├── juno.json
    │       ├── juno.scd
    │       ├── sh101.json
    │       ├── sh101.scd
    │       ├── c64_sid.json
    │       └── c64_sid.scd
    │
    ├── 808_drums/
    │   ├── manifest.json
    │   └── generators/
    │       ├── kick_808.json
    │       ├── kick_808.scd
    │       └── ...
    │
    └── _template/               # Template for creating new packs
        ├── manifest.json
        └── generators/
            └── .gitkeep
```

### 2.2 Core vs Packs

| Aspect | Core | Packs |
|--------|------|-------|
| Location | `supercollider/generators/` | `packs/<pack_name>/generators/` |
| Discovery | Auto-discovered at startup | Auto-discovered via manifest |
| Pack name | "Core" (hardcoded) | From `manifest.json` |
| Removable | No | Yes (delete folder) |
| Version tracked | With app | Independent |

---

## 3. Manifest Format

### 3.1 Schema

```json
{
    "pack_format": 1,
    "name": "Classic Synths",
    "version": "1.0.0",
    "author": "Gareth",
    "description": "Roland and Moog inspired generators",
    "url": "https://github.com/...",
    "generators": [
        "tb303",
        "juno", 
        "sh101",
        "c64_sid"
    ]
}
```

### 3.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pack_format` | int | Yes | Schema version (currently `1`) |
| `name` | string | Yes | Display name in UI |
| `version` | string | Yes | Semantic version (e.g., "1.0.0") |
| `author` | string | No | Pack creator |
| `description` | string | No | Brief description |
| `url` | string | No | Project/download URL |
| `generators` | array | Yes | List of generator file stems |

### 3.3 Generator References

The `generators` array contains **file stems** (filename without extension):

```json
"generators": ["tb303", "juno"]
```

This expects:
- `generators/tb303.json` + `generators/tb303.scd`
- `generators/juno.json` + `generators/juno.scd`

The **display name** comes from each generator's JSON `"name"` field, not the filename.

### 3.4 Validation Rules

1. `pack_format` must equal `1`
2. `name` must be non-empty, unique across all packs
3. `generators` must be non-empty array
4. Each generator in list must have both `.json` and `.scd` files
5. Generator JSON must have valid `"name"` and `"synthdef"` fields
6. SynthDef symbol must be unique across all loaded generators

---

## 4. Discovery and Loading

### 4.1 Startup Sequence

```
1. Load generator configs (core + packs) with validation
   └── Scan supercollider/generators/*.json (core)
   └── Scan packs/*/manifest.json (packs, skip _folders)
   └── Validate each generator:
       └── JSON exists and valid
       └── SCD exists
       └── Synthdef symbol unique (reject on conflict)
       └── Display name unique (skip on conflict)
   └── Store validated configs with _scd_path

2. Load SynthDefs
   └── For each validated generator config:
       └── Send SCD content to SuperCollider

3. Build UI
   └── Populate pack selector with ["Core"] + pack names
   └── Default to "Core" pack
   └── Populate generator dropdowns with Core generators
```

### 4.2 Python Data Structures

```python
# In src/config/__init__.py or new src/config/packs.py

# Core generators - STATIC ordered list (not auto-discovered)
# This is the existing GENERATOR_CYCLE, kept as source of truth for core ordering.
# New core generators must be manually added here.
CORE_GENERATORS = [
    "Empty",
    "Saw", 
    "Square",
    # ... existing generators in desired order
]

# All generator configs keyed by display name
# Populated at startup from core + pack JSONs
GENERATOR_CONFIGS: Dict[str, dict] = {}

# Discovered packs: pack_id -> manifest data
PACKS: Dict[str, PackInfo] = {
    # Populated at startup, e.g.:
    # "classic_synths": {
    #     "name": "Classic Synths",
    #     "version": "1.0.0",
    #     "author": "Gareth",
    #     "path": Path("packs/classic_synths"),
    #     "generators": ["TB-303", "Juno", "SH-101", "C64 SID"]  # Display names, manifest order
    # }
}

# Currently selected pack (None = Core)
_current_pack: Optional[str] = None

def get_current_generators() -> List[str]:
    """Return generator list for currently selected pack.
    
    Empty is always injected as first generator.
    """
    if _current_pack is None:
        return CORE_GENERATORS  # Already has Empty at index 0
    # Prepend Empty to pack generators
    return ["Empty"] + PACKS[_current_pack]["generators"]

def set_current_pack(pack_id: Optional[str]) -> None:
    """Switch to a different pack. None = Core.
    
    Falls back to Core if pack_id doesn't exist (e.g., folder deleted).
    """
    global _current_pack
    
    if pack_id is not None and pack_id not in PACKS:
        logger.warning(f"Pack '{pack_id}' not found, falling back to Core")
        pack_id = None
    
    _current_pack = pack_id
    # Emit signal for UI update
```

### 4.3 Generator Config Loading

Load generator configs and validate SynthDef availability in a **single pass**. This ensures generators with conflicting synthdefs are rejected before appearing in dropdowns.

```python
def _load_generator_configs():
    """Load all generator JSON configs from core and packs.
    
    Validates synthdef uniqueness during config loading, not after.
    Generators with conflicting synthdefs are rejected entirely.
    """
    
    # Track loaded synthdef symbols to prevent duplicates
    loaded_synthdefs = set()
    
    # 1. Load core generators (existing logic)
    core_path = Path("supercollider/generators")
    for json_file in core_path.glob("*.json"):
        config = json.load(json_file.open())
        gen_stem = json_file.stem
        
        # Check synthdef uniqueness
        synthdef_symbol = config["synthdef"]
        if synthdef_symbol in loaded_synthdefs:
            logger.warning(f"Core generator '{gen_stem}': synthdef "
                         f"'{synthdef_symbol}' conflicts, skipping")
            continue
        
        # Store stem and path for later SCD loading
        config["_stem"] = gen_stem
        config["_scd_path"] = core_path / f"{gen_stem}.scd"
        
        loaded_synthdefs.add(synthdef_symbol)
        GENERATOR_CONFIGS[config["name"]] = config
    
    # 2. Load pack generators
    packs_path = Path("packs")
    for manifest_path in packs_path.glob("*/manifest.json"):
        pack_dir = manifest_path.parent
        
        # Skip directories starting with underscore (_template, _example, etc.)
        if pack_dir.name.startswith("_"):
            continue
        
        manifest = json.load(manifest_path.open())
        
        # Validate manifest
        if not _validate_manifest(manifest, pack_dir):
            continue
        
        pack_id = pack_dir.name
        pack_generators = []
        
        # Iterate in manifest order (preserve intended dropdown order)
        for gen_stem in manifest["generators"]:
            json_path = pack_dir / "generators" / f"{gen_stem}.json"
            scd_path = pack_dir / "generators" / f"{gen_stem}.scd"
            
            if not json_path.exists():
                logger.warning(f"Pack '{pack_id}': missing {gen_stem}.json, skipping")
                continue
            
            if not scd_path.exists():
                logger.warning(f"Pack '{pack_id}': missing {gen_stem}.scd, skipping")
                continue
            
            config = json.load(json_path.open())
            
            # Check synthdef uniqueness BEFORE adding to configs
            synthdef_symbol = config["synthdef"]
            if synthdef_symbol in loaded_synthdefs:
                logger.warning(f"Pack '{pack_id}': generator '{gen_stem}' has "
                             f"synthdef '{synthdef_symbol}' which conflicts, skipping")
                continue
            
            # Check for duplicate display names
            if config["name"] in GENERATOR_CONFIGS:
                logger.warning(f"Pack '{pack_id}': generator '{config['name']}' "
                             f"already exists, skipping")
                continue
            
            # Store stem and path for later SCD loading
            config["_stem"] = gen_stem
            config["_scd_path"] = scd_path
            
            loaded_synthdefs.add(synthdef_symbol)
            GENERATOR_CONFIGS[config["name"]] = config
            pack_generators.append(config["name"])  # Preserves manifest order
        
        # Skip packs with no valid generators
        if not pack_generators:
            logger.warning(f"Pack '{pack_id}' has no valid generators, skipping")
            continue
        
        # Store pack metadata
        PACKS[pack_id] = {
            "name": manifest["name"],
            "version": manifest["version"],
            "author": manifest.get("author", "Unknown"),
            "path": pack_dir,
            "generators": pack_generators  # Already in manifest order
        }
```

### 4.4 SynthDef Loading

SynthDefs are loaded using paths stored during config loading. Since synthdef uniqueness was already validated in 4.3, this phase is straightforward.

```python
def _load_synthdefs():
    """Load all SynthDefs from validated generator configs.
    
    Uses _scd_path stored during config loading.
    No uniqueness checks needed - already validated in _load_generator_configs().
    """
    
    for gen_name, config in GENERATOR_CONFIGS.items():
        if gen_name == "Empty":
            continue
        
        scd_path = config.get("_scd_path")
        if not scd_path or not scd_path.exists():
            logger.error(f"Generator '{gen_name}': SCD file not found at {scd_path}")
            continue
        
        # Send to SuperCollider
        scd_content = scd_path.read_text()
        osc_client.send_message("/code", scd_content)
        
        logger.debug(f"Loaded synthdef '{config['synthdef']}' from {scd_path}")
```

---

## 5. UI Components

### 5.1 Pack Selector Widget

**Location:** Main toolbar, left side (before transport controls)

**Widget:** `QComboBox`

```
┌──────────────────────────────────────────────────────────────────┐
│ Pack: [Classic Synths ▼]  │  ▶  ■  │  BPM: 120  │  ...          │
└──────────────────────────────────────────────────────────────────┘
```

**Dropdown contents:**
```
Core
─────────────
Classic Synths
808 Drums
West Coast
```

The separator visually distinguishes built-in Core from add-on packs.

### 5.2 Pack Selector Implementation

```python
# In src/ui/main_window.py or new src/ui/widgets/pack_selector.py

class PackSelector(QComboBox):
    """Dropdown for selecting generator pack."""
    
    pack_changed = pyqtSignal(str)  # Emits pack_id or "" for Core
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(150)
        self.setToolTip("Select generator pack")
        
        self._populate()
        self.currentIndexChanged.connect(self._on_selection_changed)
    
    def _populate(self):
        """Populate dropdown with Core + discovered packs.
        
        Packs are sorted alphabetically by display name.
        Generators within each pack follow manifest order (not sorted).
        """
        self.clear()
        
        # Core is always first
        self.addItem("Core", userData="")
        
        # Add separator if there are packs
        if PACKS:
            self.insertSeparator(1)
        
        # Add packs sorted alphabetically by display name
        for pack_id in sorted(PACKS.keys(), key=lambda p: PACKS[p]["name"]):
            pack = PACKS[pack_id]
            display = f"{pack['name']}"
            self.addItem(display, userData=pack_id)
    
    def _on_selection_changed(self, index: int):
        """Handle pack selection change."""
        pack_id = self.currentData() or None
        set_current_pack(pack_id)
        self.pack_changed.emit(pack_id or "")
```

### 5.3 Generator Dropdown Updates

When pack changes, all generator dropdowns must repopulate:

```python
# In GeneratorSlot or wherever generator combo exists

def _on_pack_changed(self, pack_id: str):
    """Update generator dropdown when pack changes.
    
    Uses blockSignals to prevent redundant synth updates during repopulation.
    """
    
    # Block signals during repopulation to avoid double-triggering
    self.generator_combo.blockSignals(True)
    
    try:
        # Repopulate with new pack's generators
        self.generator_combo.clear()
        for gen_name in get_current_generators():
            self.generator_combo.addItem(gen_name)
        
        # Reset to first generator (Empty)
        self.generator_combo.setCurrentIndex(0)
    finally:
        self.generator_combo.blockSignals(False)
    
    # Single explicit apply after repopulation complete
    self._apply_generator(0)
```

### 5.4 Signal Flow

```
PackSelector.currentIndexChanged
    │
    ▼
set_current_pack(pack_id)     # Update global state
    │
    ▼
pack_changed signal emitted
    │
    ├──▶ Slot 1: _on_pack_changed() ──▶ repopulate dropdown, reset to Empty
    ├──▶ Slot 2: _on_pack_changed() ──▶ repopulate dropdown, reset to Empty
    ├──▶ ...
    └──▶ Slot 8: _on_pack_changed() ──▶ repopulate dropdown, reset to Empty
```

---

## 6. State Management

### 6.1 Application State

```python
# Pack state lives in config module
_current_pack: Optional[str] = None  # None = Core

# Accessed via functions
def get_current_pack() -> Optional[str]: ...
def set_current_pack(pack_id: Optional[str]) -> None: ...
def get_current_generators() -> List[str]: ...
def get_pack_info(pack_id: str) -> Dict: ...
```

### 6.2 Pack Switching Behaviour

When user switches pack:

1. **All slots reset to "Empty"** (or first generator in pack)
2. **All synths update** to new Empty generator
3. **Modulation routings preserved** (targets still valid)
4. **Mixer settings preserved** (volume, pan, mute, solo)
5. **Global settings preserved** (BPM, master volume)

### 6.3 Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Pack has no "Empty" generator | Empty auto-injected as first generator |
| Pack folder deleted while running | Pack remains in dropdown until restart; selecting it falls back to Core with warning |
| Duplicate generator display name | Second generator skipped with warning |
| Duplicate synthdef symbol | Generator rejected entirely (not just synthdef skipped) — prevents silent failures |
| Corrupt manifest.json | Pack skipped with warning |
| Missing generator JSON | Generator skipped, pack still loads (unless all generators fail) |
| Missing generator SCD | Generator skipped, pack still loads (unless all generators fail) |
| All generators in pack fail validation | Pack skipped entirely (not shown in dropdown) |
| Folder name starts with underscore | Ignored (`_template/`, `_example/`, etc.) |
| Generator dropdown order | Follows manifest order (not sorted alphabetically) |
| Core generator order | Follows static `CORE_GENERATORS` list (manually ordered) |

---

## 7. Preset Integration

### 7.1 Preset Format Extension

Add pack reference to preset JSON:

```json
{
    "version": "2.0",
    "name": "Acid House",
    "pack": "classic_synths",
    "slots": [
        {
            "generator": "TB-303",
            "params": { ... }
        },
        ...
    ],
    "modulation": { ... },
    "mixer": { ... }
}
```

### 7.2 Preset Save

```python
def save_preset(name: str) -> Dict:
    """Save current state as preset."""
    return {
        "version": "2.0",
        "name": name,
        "pack": get_current_pack(),  # None for Core, pack_id for packs
        "slots": [slot.get_state() for slot in slots],
        "modulation": modulation_matrix.get_state(),
        "mixer": mixer.get_state()
    }
```

### 7.3 Preset Load

```python
def load_preset(preset: Dict):
    """Load preset, handling pack switching.
    
    Validates preset contents before switching packs to avoid
    partial state changes on error.
    """
    
    pack_id = preset.get("pack")
    
    # === VALIDATION PHASE (before any state changes) ===
    
    # Check if pack exists
    if pack_id and pack_id not in PACKS:
        show_warning(
            f"Preset requires pack '{pack_id}' which is not installed.\n"
            f"Loading with Core generators instead."
        )
        pack_id = None
    
    # Determine target generator list
    if pack_id:
        target_generators = ["Empty"] + PACKS[pack_id]["generators"]
    else:
        target_generators = CORE_GENERATORS
    
    # Validate all generators in preset exist in target pack
    validated_slots = []
    for i, slot_state in enumerate(preset.get("slots", [])):
        gen_name = slot_state.get("generator", "Empty")
        
        if gen_name not in target_generators:
            logger.warning(f"Slot {i}: generator '{gen_name}' not in pack, using Empty")
            gen_name = "Empty"
        
        validated_slots.append({"generator": gen_name, **slot_state})
    
    # === APPLICATION PHASE (all-or-nothing) ===
    
    # Switch pack (triggers UI updates)
    set_current_pack(pack_id)
    pack_selector.setCurrentIndex(...)
    
    # Load validated slot states
    for i, slot_state in enumerate(validated_slots):
        slots[i].set_state(slot_state)
    
    # Load modulation and mixer
    modulation_matrix.set_state(preset.get("modulation", {}))
    mixer.set_state(preset.get("mixer", {}))
```

### 7.4 Backward Compatibility

Presets without `"pack"` field default to Core:

```python
pack_id = preset.get("pack")  # Returns None if missing
# None = Core, so old presets load normally
```

---

## 8. Console Output

### 8.1 Startup Logging

```
[PACKS] Scanning packs directory...
[PACKS] Found pack: Classic Synths v1.0.0 (4 generators)
[PACKS] Found pack: 808 Drums v1.0.0 (4 generators)
[PACKS] Loaded 2 packs with 8 generators total
[PACKS] Core: 22 generators
```

### 8.2 Warning Examples

```
[PACKS] Warning: packs/broken_pack/manifest.json - invalid JSON, skipping pack
[PACKS] Warning: Pack 'test': generator 'tb303' has synthdef 'tb303' which conflicts, skipping
[PACKS] Warning: Pack 'test': generator 'Saw' already exists, skipping
[PACKS] Warning: Pack 'test': missing foo.json, skipping
[PACKS] Warning: Pack 'test': missing foo.scd, skipping
[PACKS] Warning: Pack 'empty_pack' has no valid generators, skipping
```

### 8.3 Pack Switch Logging

```
[PACKS] Switched to pack: Classic Synths (4 generators)
[PACKS] Switched to pack: Core (22 generators)
```

---

## 9. File Specifications

### 9.1 Generator JSON (existing format)

```json
{
    "name": "TB-303",
    "synthdef": "tb303",
    "custom_params": [
        {
            "key": "waveform",
            "label": "WAV",
            "tooltip": "Waveform (Saw/Square)",
            "default": 0,
            "min": 0,
            "max": 1,
            "steps": 2,
            "curve": "lin",
            "unit": ""
        }
    ]
}
```

### 9.2 Generator SCD (existing format)

Must follow standard template with:
- Standard bus arguments
- Custom bus arguments (customBus0-4)
- Helper function usage (`~stereoSpread`, `~multiFilter`, `~envVCA`, `~ensure2ch`)
- Print statement for load confirmation

### 9.3 Manifest JSON

See Section 3.1 for full schema.

---

## 10. Installation / Distribution

### 10.1 Installing a Pack

Users can install packs by:

1. **Manual copy:**
   ```bash
   # Download/extract pack
   cp -r ~/Downloads/classic_synths ~/repos/noise-engine/packs/
   # Restart Noise Engine
   ```

2. **Future: Pack Manager UI** (Phase 2)
   - Drag-drop zip file
   - Browse/install from online repository

### 10.2 Creating a Pack

1. Copy `packs/_template/` to `packs/my_pack/`
2. Edit `manifest.json` with pack metadata
3. Add generator JSON + SCD files to `generators/`
4. Test by restarting Noise Engine

### 10.3 Pack Distribution Format

Packs can be distributed as:
- **Folder:** Direct copy into `packs/`
- **Zip file:** Extract to `packs/`
- **Tar file:** Extract to `packs/`

---

## 11. Implementation Phases

### Phase 1: Core Functionality (ModCaf Demo)

**Goal:** Working pack selector with exclusive generator filtering

**Tasks:**
1. Create `packs/` directory structure
2. Create manifest files for existing generator packs
3. Implement pack discovery in config module
4. Add PackSelector widget to toolbar
5. Wire pack switching to generator dropdowns
6. Test with Classic Synths + 808 Drums packs

**Deliverables:**
- Pack selector in UI
- 2-3 demo packs working
- All existing functionality preserved

### Phase 2: Polish (Post-Demo)

**Goal:** Production-ready pack system

**Tasks:**
1. Preset save/load with pack reference
2. Graceful handling of missing packs
3. Pack info tooltip (hover on dropdown)
4. Improved logging and error messages
5. Documentation for pack creators

### Phase 3: Pack Manager (Future)

**Goal:** User-friendly pack management

**Tasks:**
1. Pack Manager dialog (enable/disable/remove)
2. Pack installation from zip
3. "All Generators" mode option
4. Online pack repository browser

---

## 12. Testing Checklist

### 12.1 Pack Discovery

| Test | Expected |
|------|----------|
| No packs directory | Core only, no errors |
| Empty packs directory | Core only |
| Valid pack | Appears in dropdown |
| Invalid manifest JSON | Warning logged, pack skipped |
| Missing generator JSON | Warning logged, generator skipped |
| Missing generator SCD | Warning logged, generator skipped |
| Duplicate generator display name | Warning logged, second skipped |
| Duplicate synthdef symbol | Warning logged, generator rejected entirely |
| All generators in pack fail | Warning logged, pack not shown in dropdown |
| Folder starts with underscore | Ignored (e.g. `_template/`) |
| Generator dropdown order | Matches manifest order exactly |
| Synthdef symbol ≠ file stem | Works correctly (uses stem for path, symbol for uniqueness) |

### 12.2 Pack Switching

| Test | Expected |
|------|----------|
| Switch Core → Pack | All slots reset, dropdowns repopulate |
| Switch Pack → Core | All slots reset, dropdowns repopulate |
| Switch Pack → Pack | All slots reset, dropdowns repopulate |
| Rapid switching | No crashes, UI responsive |

### 12.3 Generator Functionality

| Test | Expected |
|------|----------|
| Select pack generator | Synth loads, produces sound |
| Modulate pack generator | Modulation works normally |
| Custom params on pack gen | Sliders work, values applied |

### 12.4 Preset Integration (Phase 2)

| Test | Expected |
|------|----------|
| Save preset with pack | `pack` field in JSON |
| Load preset with pack | Pack switches, generators load |
| Load preset, pack missing | Warning, falls back to Core |
| Load old preset (no pack) | Loads as Core |

---

## 13. Design Decisions

1. **"Empty" generator:** Global Empty is automatically injected as index 0 for every pack. Pack authors don't need to include it — the loader prepends it to every pack's generator list. This removes friction and ensures consistent behaviour.

2. **Mixed mode:** No "All Generators" mode for Phase 1. Exclusive-per-pack is cleaner for demo use case and avoids edge cases (duplicate display names across packs). Easy to add later if needed.

3. **Pack ordering:** Alphabetical by display name. Future extension: optional `"order": 10` field in manifest for manual sorting (lower = higher in list). Packs without `order` field sort alphabetically after ordered packs.

4. **Hot reload:** Restart-only for Phase 1. Hot reload adds complexity around mid-performance generator disappearance. Can revisit for Phase 3.

---

## 14. Architectural Notes

### 14.1 Current Approach: Module-Level State

For Phase 1, pack state lives as module-level globals:

```python
_current_pack: Optional[str] = None
PACKS: Dict[str, PackInfo] = {}
```

This is pragmatic and matches the existing config module pattern.

### 14.2 Future Consideration: PackManager Class

If any of these become requirements, refactor to a `PackManager` class:

- Multiple Noise Engine instances
- Unit testing with isolated state  
- Plugin architecture with dependency injection

```python
class PackManager:
    def __init__(self):
        self._current_pack: Optional[str] = None
        self._packs: Dict[str, PackInfo] = {}
    
    def discover_packs(self, packs_dir: Path) -> None: ...
    def get_current_generators(self) -> List[str]: ...
    def set_current_pack(self, pack_id: Optional[str]) -> None: ...

# Passed to components that need it
pack_manager = PackManager()
main_window = MainWindow(pack_manager=pack_manager)
```

Not urgent for Phase 1 — flagged as a clean refactor point.

### 14.3 Future Consideration: Stable Generator IDs

For Phase 1, generators are keyed by display name (`config["name"]`). This works because:
- You control all packs (no third-party naming conflicts)
- No preset save/load yet
- Display names won't change mid-demo

For Phase 2 (presets), consider introducing stable `generator_id`:

```python
generator_id = f"{pack_id}:{gen_stem}"  # e.g., "classic_synths:tb303"
```

This would:
- Survive display name changes
- Allow duplicate display names across packs
- Make presets portable

Implementation would require:
- `GENERATOR_CONFIGS` keyed by `generator_id` instead of display name
- Separate `DISPLAY_NAME_BY_ID` lookup
- Presets store `generator_id`, not display name
- UI dropdowns use `userData=generator_id`

Not needed for ModCaf demo — flagged for preset implementation phase.

---

## Appendix A: Migration Guide

### Moving Existing Generators to Pack Format

If you have generators in `supercollider/generators/` that you want to package:

```bash
# Create pack structure
mkdir -p packs/my_pack/generators

# Move generator files
mv supercollider/generators/my_gen.json packs/my_pack/generators/
mv supercollider/generators/my_gen.scd packs/my_pack/generators/

# Create manifest
cat > packs/my_pack/manifest.json << 'EOF'
{
    "pack_format": 1,
    "name": "My Pack",
    "version": "1.0.0",
    "author": "Your Name",
    "generators": ["my_gen"]
}
EOF

# Remove from GENERATOR_CYCLE in src/config/__init__.py
```

---

## Appendix B: Example Manifests

### Classic Synths

```json
{
    "pack_format": 1,
    "name": "Classic Synths",
    "version": "1.0.0",
    "author": "Gareth",
    "description": "Roland and Moog inspired generators",
    "generators": [
        "tb303",
        "juno",
        "sh101",
        "c64_sid"
    ]
}
```

### 808 Drums

```json
{
    "pack_format": 1,
    "name": "808 Drums",
    "version": "1.0.0",
    "author": "Gareth",
    "description": "TR-808 drum machine sounds",
    "generators": [
        "kick_808",
        "snare_808",
        "hat_808",
        "clap_808"
    ]
}
```

### West Coast

```json
{
    "pack_format": 1,
    "name": "West Coast",
    "version": "1.0.0",
    "author": "Gareth",
    "description": "Buchla and Serge inspired generators",
    "generators": [
        "buchla",
        "drone"
    ]
}
```
