# Synth Pack Loader — Implementation Spec

*Phases 1-4: From directory structure to working UI integration*

---

## Overview

This spec covers implementing a pack loading system that allows users to add third-party generator collections to Noise Engine without modifying core code. Generators from packs appear in the UI dropdown alongside built-in generators.

**Current state:**
- 22 core generators in `supercollider/generators/`
- `GENERATOR_CYCLE` is a static list in `src/config/__init__.py`
- Generators are auto-discovered from JSON files, but must be manually added to `GENERATOR_CYCLE`

**Target state:**
- Core generators remain in `supercollider/generators/`
- User packs live in `packs/{pack_name}/`
- `GENERATOR_CYCLE` builds dynamically: core first, then enabled packs
- No code changes required to add/remove packs

**Security / trust boundary:** Packs include `.scd` code that will be executed by SuperCollider when loaded. Treat packs as **trusted code only**; do not install packs from unknown sources.

---

## Phase 1: Directory Structure & Manifest Format

### 1.1 Directory Layout

```
noise-engine/
├── supercollider/
│   └── generators/           # Core generators (unchanged)
│       ├── subtractive.json
│       ├── subtractive.scd
│       └── ...
├── packs/                    # NEW: User packs directory
│   ├── .gitkeep              # Keep in repo, empty by default
│   └── classic_synths/       # Example pack
│       ├── manifest.json
│       ├── generators/
│       │   ├── tb303.json
│       │   ├── tb303.scd
│       │   ├── juno.json
│       │   ├── juno.scd
│       │   └── ...
│       └── README.md         # Optional: pack documentation
└── docs/
    └── PACK_SPEC.md          # Pack creation guide
```

### 1.2 Manifest Schema

**`packs/{pack_name}/manifest.json`**

```json
{
    "pack_format": 1,
    "name": "Classic Synths",
    "version": "1.0.0",
    "author": "Gareth",
    "description": "Emulations of classic analog synthesizers",
    "url": "https://github.com/example/classic-synths-pack",
    "enabled": true,
    "generators": [
        "TB-303",
        "Juno",
        "SH-101",
        "C64 SID"
    ]
}
```

**Field definitions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pack_format` | int | Yes | Schema version, currently `1` |
| `name` | string | Yes | Display name (shown in UI) |
| `version` | string | Yes | Semver version string |
| `author` | string | No | Pack creator |
| `description` | string | No | Short description |
| `url` | string | No | Link to source/docs |
| `enabled` | bool | Yes | Whether pack loads on startup |
| `generators` | array | Yes | Ordered list of generator file stems or display names |

**Generator list rules:**
- In `pack_format: 1`, each entry may be either:
  - a generator JSON **file stem** (recommended, e.g. `"tb303"` matching `tb303.json`), or
  - a generator **display name** matching the `"name"` field in that generator's JSON
- File-stem matches take precedence; display-name lookup is fallback
- Order determines display order in UI dropdown
- Missing generators logged as warning, skipped

### 1.3 Generator Files

Pack generators use the exact same format as core generators (per `GENERATOR_SPEC.md`):

**`packs/{pack_name}/generators/{name}.json`**
```json
{
    "name": "TB-303",
    "synthdef": "tb303",
    "custom_params": [
        {
            "key": "accent",
            "label": "ACC",
            "tooltip": "Accent amount",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0,
            "curve": "lin"
        }
    ]
}
```

**`packs/{pack_name}/generators/{name}.scd`**
```supercollider
SynthDef(\tb303, { |out, freqBus, ... |
    // Standard generator structure
}).add;

"  ✓ tb303 loaded".postln;
```

### 1.4 Phase 1 Deliverables

- [ ] Create `packs/` directory with `.gitkeep`
- [ ] Create `packs/_example/` with valid manifest and 1-2 generators
- [ ] Create `docs/PACK_SPEC.md` documenting the format
- [ ] Add `packs/` to `.gitignore` (except `.gitkeep` and `_example/`)

### 1.5 Validation Criteria

```bash
# Directory exists
test -d packs/

# Example pack has valid structure
test -f packs/_example/manifest.json
test -d packs/_example/generators/
python3 -c "import json; json.load(open('packs/_example/manifest.json'))"
```

---

## Phase 2: Pack Discovery

### 2.1 New Data Structures

Add to `src/config/__init__.py`:

```python
# Pack configs loaded from manifest.json files
# Maps pack_id (directory name) -> {id, display_name, version, author, enabled, generators, path}
_PACK_CONFIGS = {}

# Track which generators came from which pack (for UI grouping)
# Maps generator_name -> pack_id (None for core generators)
_GENERATOR_SOURCES = {}
```

### 2.2 Discovery Function

```python
def _discover_packs():
    """
    Scan packs/ directory for valid pack manifests.
    Populates _PACK_CONFIGS with metadata (does not load generators).
    
    Returns:
        dict: {pack_id: {id, display_name, version, author, enabled, generators, path}}
    """
    global _PACK_CONFIGS
    
    try:
        from src.utils.logger import logger
    except ImportError:
        logger = None
    
    _PACK_CONFIGS = {}
    
    # Find packs directory
    config_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(config_dir)
    project_dir = os.path.dirname(src_dir)
    packs_dir = os.path.join(project_dir, 'packs')
    
    if not os.path.exists(packs_dir):
        if logger:
            logger.debug("No packs/ directory found", component="PACKS")
        return
    
    for entry in sorted(os.listdir(packs_dir)):
        pack_path = os.path.join(packs_dir, entry)
        
        # Skip files, hidden dirs, and special entries
        if not os.path.isdir(pack_path):
            continue
        if entry.startswith('.'):
            continue
        
        manifest_path = os.path.join(pack_path, 'manifest.json')
        if not os.path.exists(manifest_path):
            if logger:
                logger.warning(f"Pack '{entry}' missing manifest.json, skipping", component="PACKS")
            continue
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Validate required fields
            required = ['pack_format', 'name', 'enabled', 'generators']
            missing = [f for f in required if f not in manifest]
            if missing:
                if logger:
                    logger.warning(f"Pack '{entry}' manifest missing fields: {missing}", component="PACKS")
                continue
            
            # Check format version
            if manifest['pack_format'] != 1:
                if logger:
                    logger.warning(f"Pack '{entry}' has unsupported format version {manifest['pack_format']}", component="PACKS")
                continue
            
            pack_id = entry  # directory name = stable unique pack ID
            display_name = manifest['name']  # UI name (can collide, not used as key)
            
            _PACK_CONFIGS[pack_id] = {
                'id': pack_id,
                'display_name': display_name,
                'version': manifest.get('version', '0.0.0'),
                'author': manifest.get('author', 'Unknown'),
                'description': manifest.get('description', ''),
                'enabled': manifest.get('enabled', True),
                'generators': manifest.get('generators', []),
                'path': pack_path,
            }
            
            status = "enabled" if manifest.get('enabled', True) else "disabled"
            gen_count = len(manifest.get('generators', []))
            if logger:
                logger.info(
                    f"Found pack: {display_name} v{manifest.get('version', '?')} "
                    f"(id={pack_id}, {gen_count} generators, {status})",
                    component="PACKS"
                )
        
        except json.JSONDecodeError as e:
            if logger:
                logger.warning(f"Pack '{entry}' has invalid manifest.json: {e}", component="PACKS")
        except IOError as e:
            if logger:
                logger.warning(f"Failed to read pack '{entry}': {e}", component="PACKS")
    
    return _PACK_CONFIGS
```

### 2.3 Public API Functions

```python
def get_discovered_packs():
    """
    Get all discovered packs (enabled and disabled).
    
    Returns:
        dict: {pack_id: {id, display_name, version, author, enabled, generators, path}}
    """
    return _PACK_CONFIGS.copy()


def get_enabled_packs():
    """
    Get only enabled packs, in discovery order.
    
    Note: Returned dicts may be augmented during load (e.g., 'loaded_generators' 
    is added by _load_generator_configs()).
    
    Returns:
        list: [{id, display_name, version, author, generators, path, ...}, ...]
    """
    return [p for p in _PACK_CONFIGS.values() if p.get('enabled', False)]


def get_generator_source(generator_name):
    """
    Get which pack a generator came from.
    
    Returns:
        str or None: Pack id (directory name), or None if core generator
    """
    return _GENERATOR_SOURCES.get(generator_name)
```

### 2.4 Integration Point

Call discovery early in module load:

```python
# At end of src/config/__init__.py, BEFORE _load_generator_configs()

_discover_packs()  # NEW: Find available packs (needed for get_enabled_packs())
```

### 2.5 Phase 2 Deliverables

- [ ] Add `_PACK_CONFIGS` and `_GENERATOR_SOURCES` globals
- [ ] Implement `_discover_packs()` function
- [ ] Implement `get_discovered_packs()`, `get_enabled_packs()`, `get_generator_source()`
- [ ] Call `_discover_packs()` on module load
- [ ] Add test: `tests/test_packs.py` with discovery tests

### 2.6 Test Cases

```python
# tests/test_packs.py

def test_discover_packs_empty():
    """No packs directory should not crash."""
    # Temporarily rename packs/ if exists
    # Call _discover_packs()
    # Assert _PACK_CONFIGS is empty dict

def test_discover_packs_valid():
    """Valid pack should be discovered."""
    # Ensure _example pack exists
    from src.config import get_discovered_packs
    packs = get_discovered_packs()
    # Assert '_example' or similar in packs

def test_discover_packs_invalid_manifest():
    """Invalid manifest should be skipped with warning."""
    # Create temp pack with broken JSON
    # Assert it's not in _PACK_CONFIGS

def test_discover_packs_missing_fields():
    """Manifest missing required fields should be skipped."""
    # Create temp pack with incomplete manifest

def test_enabled_packs_filter():
    """get_enabled_packs() should filter disabled packs."""
    # Create two packs, one disabled
    # Assert only enabled one returned
```

### 2.7 Console Output Example

```
[PACKS] Found pack: Classic Synths v1.0.0 (id=classic_synths, 4 generators, enabled)
[PACKS] Found pack: Drum Machines v0.9.0 (id=drum_machines, 8 generators, disabled)
[PACKS] Pack 'broken_pack' has invalid manifest.json: Expecting property name...
```

---

## Phase 3: Generator Loading from Packs

### 3.1 Extend `_load_generator_configs()`

Modify the existing function to also load from enabled packs:

```python
def _load_generator_configs():
    """Load generator configs from core + enabled packs."""
    global _GENERATOR_CONFIGS, _GENERATOR_SOURCES
    
    try:
        from src.utils.logger import logger
    except ImportError:
        logger = None
    
    # ... existing code to find generators_dir ...
    
    _GENERATOR_CONFIGS = {"Empty": {"synthdef": None, "custom_params": [], "pitch_target": None, "output_trim_db": 0.0}}
    _GENERATOR_SOURCES = {"Empty": None}  # None = core
    _LOADED_SYNTHDEFS = set()  # Track SynthDef symbols across core + packs
    
    # === LOAD CORE GENERATORS (existing logic) ===
    if os.path.exists(generators_dir):
        for filename in os.listdir(generators_dir):
            if not filename.endswith('.json') or filename.startswith('.'):
                continue
            # ... existing loading code ...
            # After parsing config:
            synthdef = config.get('synthdef')
            if synthdef:
                _LOADED_SYNTHDEFS.add(synthdef)
            _GENERATOR_SOURCES[name] = None  # Mark as core
    
    # === LOAD PACK GENERATORS (new) ===
    for pack in get_enabled_packs():
        pack_generators_dir = os.path.join(pack['path'], 'generators')
        
        if not os.path.exists(pack_generators_dir):
            if logger:
                logger.warning(f"Pack '{pack['display_name']}' has no generators/ directory", component="PACKS")
            continue
        
        loaded_from_pack = []
        
        for gen_entry in pack['generators']:
            # Try file-stem match first (recommended), then display-name fallback
            json_file = None
            gen_name = None
            
            # 1. Try file-stem match: gen_entry.json
            stem_path = os.path.join(pack_generators_dir, f"{gen_entry}.json")
            if os.path.exists(stem_path):
                try:
                    with open(stem_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        json_file = stem_path
                        gen_name = config.get('name', gen_entry)  # Use display name from JSON
                except (json.JSONDecodeError, IOError):
                    pass
            
            # 2. Fallback: search by display name
            if not json_file:
                for filename in os.listdir(pack_generators_dir):
                    if filename.endswith('.json') and not filename.startswith('.'):
                        filepath = os.path.join(pack_generators_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                                if config.get('name') == gen_entry:
                                    json_file = filepath
                                    gen_name = gen_entry
                                    break
                        except (json.JSONDecodeError, IOError):
                            continue
            
            if not json_file:
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': generator '{gen_entry}' not found", component="PACKS")
                continue
            
            # Check for conflicts
            if gen_name in _GENERATOR_CONFIGS and _GENERATOR_SOURCES.get(gen_name) is None:
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': '{gen_name}' conflicts with core generator, skipping", component="PACKS")
                continue
            
            if gen_name in _GENERATOR_CONFIGS:
                existing_pack = _GENERATOR_SOURCES.get(gen_name)
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': '{gen_name}' already loaded from '{existing_pack}', skipping", component="PACKS")
                continue
            
            # Load the config
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Validate SynthDef symbol uniqueness (core + packs)
                synthdef = config.get('synthdef')
                if not synthdef:
                    if logger:
                        logger.warning(f"Pack '{pack['display_name']}': '{gen_name}' missing synthdef, skipping", component="PACKS")
                    continue
                
                if synthdef in _LOADED_SYNTHDEFS:
                    if logger:
                        logger.warning(
                            f"Pack '{pack['display_name']}': synthdef '{synthdef}' already loaded "
                            f"(conflicts with core/another pack), skipping '{gen_name}'",
                            component="PACKS"
                        )
                    continue
                
                _GENERATOR_CONFIGS[gen_name] = {
                    "synthdef": synthdef,
                    "custom_params": config.get('custom_params', []),
                    "pitch_target": config.get('pitch_target'),
                    "output_trim_db": config.get('output_trim_db', 0.0),
                    "pack": pack['id'],  # pack_id (directory name)
                    "pack_path": pack['path'],  # For SC to find .scd
                }
                _GENERATOR_SOURCES[gen_name] = pack['id']
                _LOADED_SYNTHDEFS.add(synthdef)
                loaded_from_pack.append(gen_name)
                
            except (json.JSONDecodeError, IOError, KeyError) as e:
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': failed to load '{gen_name}': {e}", component="PACKS")
        
        # Store resolved generator names for Phase 4 cycle building
        pack['loaded_generators'] = loaded_from_pack
        
        if logger and loaded_from_pack:
            logger.info(f"Loaded {len(loaded_from_pack)} generators from pack '{pack['display_name']}'", component="PACKS")
```

### 3.2 SuperCollider Integration

SC needs to load .scd files from packs. Two approaches:

**Option A: Extend init.scd (simpler)**

Modify `supercollider/init.scd` to also scan packs:

```supercollider
// Load generators (auto-load all .scd files)
"Loading generators...".postln;

// Core generators
~generatorPath = ~basePath +/+ "generators/";
~generatorFiles = PathName(~generatorPath).files.select({ |f| f.extension == "scd" });
~generatorFiles.do({ |file|
    file.fullPath.load;
});

// Pack generators (NEW)
~packsPath = ~basePath.dirname +/+ "packs/";
// NOTE: can be brittle depending on ~basePath; consider sending project root from Python via OSC at startup
if(File.exists(~packsPath), {
    "Loading pack generators...".postln;
    PathName(~packsPath).folders.do({ |packDir|
        var manifestPath = packDir.fullPath +/+ "manifest.json";
        var genPath = packDir.fullPath +/+ "generators/";
        
        if(File.exists(manifestPath) && File.exists(genPath), {
            var packFiles = PathName(genPath).files.select({ |f| f.extension == "scd" });
            packFiles.do({ |file|
                file.fullPath.load;
            });
            ("  Pack: " ++ packDir.folderName ++ " (" ++ packFiles.size ++ " generators)").postln;
        });
    });
});
```

**Option B: OSC-triggered loading (more complex, enables hot-reload later)**

Add OSC handler for dynamic SynthDef loading:

```supercollider
OSCdef(\loadPackGenerator, { |msg|
    var path = msg[1].asString;
    if(File.exists(path), {
        path.load;
        ("  ✓ Loaded: " ++ path).postln;
    }, {
        ("  ✗ Not found: " ++ path).postln;
    });
}, '/noise/pack/load');
```

**Recommendation:** Start with Option A for MVP. Add Option B later for hot-reload support.

**Enabled semantics (MVP):** `enabled: false` means the pack is **hidden in the Python UI** (not added to `GENERATOR_CYCLE`). With Option A scanning, SuperCollider may still load the pack `.scd` files; they simply won't be selectable.

### 3.3 Enabled Check in SC

SC currently loads ALL .scd files it finds. To respect the `enabled` flag, either:

1. **Python-side:** Only enabled pack paths get communicated to SC (if using OSC approach)
2. **SC-side:** Parse manifest.json in SC (messy, JSON parsing in SC is awkward)
3. **Convention:** Rename disabled packs or use a separate disabled/ folder

**Recommendation:** Use Option A (scan all) for now. The Python side controls what appears in GENERATOR_CYCLE. Unused SynthDefs in SC are harmless.

### 3.4 Phase 3 Deliverables

- [ ] Extend `_load_generator_configs()` to load from enabled packs
- [ ] Add conflict detection (core wins, first-loaded-pack wins)
- [ ] Add `pack` and `pack_path` fields to generator configs
- [ ] Modify `supercollider/init.scd` to scan `packs/*/generators/`
- [ ] Add tests for pack generator loading
- [ ] Add tests for conflict handling

### 3.5 Test Cases

```python
def test_pack_generators_loaded():
    """Generators from enabled packs should be in _GENERATOR_CONFIGS."""
    from src.config import _GENERATOR_CONFIGS, _GENERATOR_SOURCES
    # Assuming _example pack has a generator
    # Assert it's in _GENERATOR_CONFIGS
    # Assert _GENERATOR_SOURCES[name] == pack_id

def test_core_generator_wins_conflict():
    """Core generator should take precedence over pack generator with same name."""
    # Create pack with generator named "Subtractive" (exists in core)
    # Assert core version is loaded, pack version skipped

def test_first_pack_wins_conflict():
    """First loaded pack wins when two packs have same generator name."""
    # Create two packs with same generator name
    # Assert first one loaded

def test_disabled_pack_not_loaded():
    """Generators from disabled packs should not load."""
    # Create pack with enabled: false
    # Assert its generators not in _GENERATOR_CONFIGS
```

### 3.6 Console Output Example

```
[PACKS] Found pack: Classic Synths v1.0.0 (id=classic_synths, 4 generators, enabled)
[PACKS] Loaded 4 generators from pack 'Classic Synths'
[PACKS] Found pack: Extras v0.5.0 (id=extras, 2 generators, enabled)
[PACKS] Pack 'Extras': 'TB-303' already loaded from 'classic_synths', skipping
[PACKS] Pack 'Extras': synthdef 'juno' already loaded (conflicts with core/another pack), skipping 'Juno Clone'
[PACKS] Loaded 1 generators from pack 'Extras'
```

---

## Phase 4: Dynamic GENERATOR_CYCLE

### 4.1 Refactor GENERATOR_CYCLE

Replace the static list with a function that builds dynamically:

```python
# Keep static list for CORE generators only (preserves your preferred order)
_CORE_GENERATOR_ORDER = [
    "Empty",
    # Basic synthesis
    "Test Synth",
    "Subtractive",
    "Additive",
    "FM",
    "Wavetable",
    "Granular",
    # Physical modeling
    "Karplus",
    "Modal",
    # Relaxation oscillators
    "VCO Relax",
    "UJT Relax",
    "Neon",
    "CapSense",
    # Siren circuits
    "4060 Siren",
    "FBI Siren",
    "FBI Doppler",
    # Ring modulators
    "Diode Ring",
    "4-Quad Ring",
    "VCA Ring",
    # Noise/chaos
    "PT2399",
    "PT Chaos",
    "Geiger",
    "Giant B0N0",
]


def _build_generator_cycle():
    """
    Build complete generator list: core + enabled packs.
    
    Returns:
        list: Ordered generator names for UI dropdown
    """
    cycle = []
    
    # 1. Core generators (in defined order)
    for name in _CORE_GENERATOR_ORDER:
        if name in _GENERATOR_CONFIGS:
            cycle.append(name)
    
    # 2. Pack generators (grouped by pack, in manifest order)
    for pack in get_enabled_packs():
        # Use resolved display names stored during loading (preserves manifest order)
        pack_generators = pack.get('loaded_generators', [])
        
        if pack_generators:
            # Add separator (special entry, handled by UI)
            cycle.append(f"──── {pack['display_name']} ────")
            cycle.extend(pack_generators)
    
    return cycle


# Build on import (after configs loaded)
GENERATOR_CYCLE = []  # Placeholder, populated by _finalize_config()


def _finalize_config():
    """Called after all loading complete to build dynamic lists."""
    global GENERATOR_CYCLE
    GENERATOR_CYCLE = _build_generator_cycle()


# Call at end of module
_discover_packs()
_load_generator_configs()
_finalize_config()
```

### 4.2 UI Separator Handling

The dropdown needs to handle separator entries. In `generator_slot.py` (or wherever the combo box is populated):

```python
from src.config import GENERATOR_CYCLE

def populate_generator_dropdown(combo_box):
    """Populate generator dropdown with separators for packs."""
    combo_box.clear()
    
    for item in GENERATOR_CYCLE:
        if item.startswith("────"):
            # Separator - add as disabled item or visual divider
            # PyQt5 approach:
            combo_box.addItem(item)
            index = combo_box.count() - 1
            # Make it non-selectable
            model = combo_box.model()
            model.item(index).setEnabled(False)
            # Optional: style it differently
            model.item(index).setForeground(QColor(128, 128, 128))
        else:
            combo_box.addItem(item)
```

**Alternative: Submenus**

If the dropdown gets too long, consider grouping into submenus:
- Core → [list]
- Classic Synths → [list]
- Drum Machines → [list]

This requires a QMenu instead of QComboBox, more complex but scales better.

### 4.3 Handling Selection

Ensure generator selection logic skips separators:

```python
def on_generator_changed(self, index):
    """Handle generator dropdown selection."""
    name = self.generator_combo.currentText()
    
    # Skip separators
    if name.startswith("────"):
        return
    
    # ... existing selection logic ...
```

### 4.4 Backward Compatibility

Code that iterates GENERATOR_CYCLE needs to handle separators:

```python
# OLD (breaks with separators):
for gen_name in GENERATOR_CYCLE:
    config = get_generator_config(gen_name)  # Fails on separator

# NEW (safe):
for gen_name in GENERATOR_CYCLE:
    if gen_name.startswith("────"):
        continue
    config = get_generator_config(gen_name)
```

Or provide a filtered accessor **(CANONICAL - use this everywhere you need a list of selectable generator names)**:

```python
def get_valid_generators():
    """Get generator names only (no separators)."""
    return [g for g in GENERATOR_CYCLE if not g.startswith("────")]
```

### 4.5 Phase 4 Deliverables

- [ ] Rename `GENERATOR_CYCLE` to `_CORE_GENERATOR_ORDER` (static)
- [ ] Implement `_build_generator_cycle()` function
- [ ] Implement `_finalize_config()` called on module load
- [ ] Make `GENERATOR_CYCLE` dynamically built
- [ ] Update dropdown population to handle separators
- [ ] Update selection handler to skip separators
- [ ] Add `get_valid_generators()` helper
- [ ] Audit all `GENERATOR_CYCLE` usages for separator safety
- [ ] Add integration tests

### 4.6 Test Cases

```python
def test_generator_cycle_includes_core():
    """Core generators should appear in cycle."""
    from src.config import GENERATOR_CYCLE
    assert "Subtractive" in GENERATOR_CYCLE
    assert "Empty" in GENERATOR_CYCLE

def test_generator_cycle_includes_pack_generators():
    """Pack generators should appear after core."""
    from src.config import GENERATOR_CYCLE, get_enabled_packs
    # Assuming a pack is enabled with known generator
    packs = get_enabled_packs()
    if packs:
        # Use loaded_generators (resolved display names), not generators (file stems)
        gen_name = packs[0].get('loaded_generators', [None])[0]
        if gen_name:
            assert gen_name in GENERATOR_CYCLE

def test_generator_cycle_has_separators():
    """Pack sections should have separator headers."""
    from src.config import GENERATOR_CYCLE
    separators = [g for g in GENERATOR_CYCLE if g.startswith("────")]
    # Should have one separator per enabled pack
    # (only if pack has at least one loaded generator)

def test_generator_cycle_order():
    """Core generators should come before pack generators."""
    from src.config import GENERATOR_CYCLE
    core_last = GENERATOR_CYCLE.index("Giant B0N0")  # Last core generator
    first_separator = next((i for i, g in enumerate(GENERATOR_CYCLE) if g.startswith("────")), None)
    if first_separator:
        assert core_last < first_separator

def test_get_valid_generators_excludes_separators():
    """get_valid_generators() should not include separators."""
    from src.config import get_valid_generators
    valid = get_valid_generators()
    assert not any(g.startswith("────") for g in valid)
```

### 4.7 Files to Modify

| File | Changes |
|------|---------|
| `src/config/__init__.py` | Core changes: discovery, loading, cycle building |
| `src/gui/generator_slot.py` | Dropdown population, separator handling |
| `supercollider/init.scd` | Pack .scd loading |
| `tests/test_packs.py` | New test file |
| `tests/test_config.py` | Update existing tests if they assume static cycle |

---

## Migration Path

### Step-by-step implementation order:

1. **Create directory structure** (Phase 1)
   - No code changes, just files
   - Can merge immediately

2. **Add discovery code** (Phase 2)  
   - Pure addition, doesn't change existing behavior
   - Empty packs/ means no change to GENERATOR_CYCLE

3. **Add pack loading** (Phase 3)
   - Only activates if packs exist
   - Core generators unaffected

4. **Refactor GENERATOR_CYCLE** (Phase 4)
   - Breaking change for code iterating cycle
   - Do this last, all at once

### Rollback plan:

If issues arise, revert Phase 4 (restore static GENERATOR_CYCLE). Phases 1-3 are safe to keep - they just add capability without changing behavior.

---

## Example: Complete Pack

**`packs/classic_synths/manifest.json`**
```json
{
    "pack_format": 1,
    "name": "Classic Synths",
    "version": "1.0.0",
    "author": "Gareth",
    "description": "Roland and Moog inspired generators",
    "enabled": true,
    "generators": [
        "tb303",
        "juno",
        "sh101",
        "minimoog"
    ]
}
```

Note: Generator entries are file stems (recommended). The display names come from each generator's JSON `"name"` field.

**`packs/classic_synths/generators/tb303.json`**
```json
{
    "name": "TB-303",
    "synthdef": "tb303",
    "custom_params": [
        {"key": "accent", "label": "ACC", "tooltip": "Accent amount", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin"},
        {"key": "slide", "label": "SLD", "tooltip": "Slide time", "default": 0.0, "min": 0.0, "max": 1.0, "curve": "lin"},
        {"key": "envMod", "label": "ENV", "tooltip": "Filter envelope mod", "default": 0.5, "min": 0.0, "max": 1.0, "curve": "lin"}
    ]
}
```

**Result in UI dropdown:**
```
Empty
Test Synth
Subtractive
...
Giant B0N0
──── Classic Synths ────
TB-303
Juno
SH-101
Minimoog
```

---

## Open Questions

1. **Hot-reload?** Defer to Phase 5+ — requires OSC messaging and UI refresh

2. **Pack dependencies?** (e.g., pack requires specific helper functions) — Not in MVP, document as limitation

3. **Sample/buffer support?** Some generators need audio files — Could add `samples/` folder to pack structure, load buffers on pack init. Defer for now.

4. **Pack ordering?** When multiple packs enabled, what order? Current: `sorted(os.listdir())` gives alphabetical by directory name. Could add priority field to manifest later for explicit ordering.

5. **Separator style?** Current uses Unicode box-drawing. Alternative: `"--- Classic Synths ---"` or empty string + pack name in next item's prefix.
