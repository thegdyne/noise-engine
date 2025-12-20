# Skin System - Phases

**Created:** December 15, 2025  
**Status:** Phase 1 Complete

---

## Overview

The skin system allows visual customization of the entire Noise Engine interface. Skins are Python modules that define colour palettes, fonts, and sizing.

---

## Phase 1: Foundation ✅ COMPLETE

**Goal:** Establish skin architecture with high-contrast default.

### Completed
- [x] Created `src/gui/skins/` directory
- [x] Created `src/gui/skins/__init__.py` (skin loader)
- [x] Created `src/gui/skins/default.py` (high-contrast theme)
- [x] Updated `src/gui/theme.py` to load from active skin
- [x] Backwards compatibility - COLORS dict still works
- [x] Added module accent colours (generator, mod_lfo, mod_sloth, effect)
- [x] Updated mod_source_slot.py to use accent colours
- [x] Updated mod_scope.py to use skin colours

### Skin Structure (`default.py`)

```python
SKIN = {
    # Palette
    'bg_darkest': '#000000',
    'bg_dark': '#0d0d0d',
    ...
    
    # Accents (per module type)
    'accent_generator': '#00ff66',
    'accent_mod_lfo': '#00ccff',
    'accent_mod_sloth': '#ff8800',
    'accent_effect': '#aa88ff',
    'accent_master': '#ffffff',
    
    # States
    'state_enabled_bg': '#0a2a15',
    'state_enabled_text': '#00ff66',
    ...
    
    # Fonts
    'font_family': 'Helvetica',
    'font_mono': 'Menlo',  # Platform-aware
    ...
}
```

---

## Phase 2: Component Migration

**Goal:** Migrate existing components to use skin accent colours.

### Tasks
- [ ] Update `generator_slot.py` / `generator_slot_builder.py` to use `accent_generator`
- [ ] Update `mixer_panel.py` to use skin colours
- [ ] Update `effect_slot.py` to use `accent_effect`
- [ ] Update `master_section.py` to use `accent_master`
- [ ] Update `bpm_display.py` to use skin colours
- [ ] Audit all hardcoded hex colours in GUI files
- [ ] Replace `COLORS['enabled_text']` with `theme.accent('generator')` where appropriate

### API Migration

**From:**
```python
from .theme import COLORS
color = COLORS['enabled_text']
```

**To:**
```python
from . import theme
color = theme.accent('generator')
# Or for backwards compatibility:
color = COLORS['accent_generator']
```

---

## Phase 3: Additional Skins

**Goal:** Create alternative skins demonstrating the system.

### Planned Skins

1. **Subtle** - Lower contrast, muted colours (current original theme)
2. **Dark Blue** - Blue accent palette
3. **High Visibility** - Maximum contrast for accessibility
4. **Retro Media** - 90s media player aesthetic
5. **Terminal** - Green-on-black monochrome

### Skin Template

```python
# src/gui/skins/subtle.py
"""
Subtle Skin - Low contrast, muted colours
Based on the original Noise Engine theme before high-contrast update.
"""

SKIN = {
    # Copy structure from default.py
    # Adjust colours for lower contrast
    'bg_darkest': '#0a0a0a',
    'text_bright': '#aaaaaa',  # vs #d0d0d0 in high-contrast
    'accent_generator': '#88ff88',  # vs #00ff66
    ...
}
```

---

## Phase 4: Runtime Switching

**Goal:** Allow skin changes without restart.

### Tasks
- [ ] Add `theme.set_skin(skin_module)` function
- [ ] Add skin selector in settings/preferences
- [ ] Emit signal on skin change
- [ ] Components subscribe and refresh styles
- [ ] Persist skin preference to config file

### Implementation Notes

```python
# theme.py
def set_skin(skin_module):
    global _active_skin, COLORS, FONT_FAMILY, ...
    _active_skin = skin_module.SKIN
    # Rebuild COLORS dict
    COLORS = _build_colors_dict()
    # Emit signal for components to refresh
    skin_changed.emit()
```

Components would need to:
1. Connect to `skin_changed` signal
2. Re-apply stylesheets on change

---

## Phase 5: Skin Editor (Future)

**Goal:** In-app skin customization.

### Features (Conceptual)
- Visual colour picker for palette
- Live preview
- Export as new skin file
- Import community skins

---

## Files

```
src/gui/skins/
    __init__.py         # Skin loader, active skin reference
    default.py          # High-contrast default
    subtle.py           # (Phase 3) Low contrast
    dark_blue.py        # (Phase 3) Blue palette
    ...

src/gui/theme.py        # Theme manager, backwards compat
```

---

## Skin Categories

### Palette
- `bg_*` - Background colours (darkest to brightest)
- `border_*` - Border colours
- `text_*` - Text colours (dim to bright)

### Accents
- `accent_generator` - Audio generator modules (green)
- `accent_mod_lfo` - LFO modulation (cyan)
- `accent_mod_sloth` - Sloth modulation (orange)
- `accent_effect` - Effects chain (purple)
- `accent_master` - Master section (white)

Each accent has:
- `accent_X` - Primary colour
- `accent_X_dim` - Dimmed variant
- `accent_X_bg` - Background tint

### States
- `state_enabled_*` - Active/on state
- `state_disabled_*` - Inactive/off state
- `state_selected_*` - Selected item
- `state_warning_*` - Warning/alert
- `state_submenu_*` - Secondary action

### Indicators
- `led_*` - LED/lamp indicators
- `meter_*` - Level meter colours

### Controls
- `slider_*` - Slider styling
- `midi_ch_*` - MIDI channel buttons

### Special
- `bpm_text` - BPM display
- `scope_*` - Oscilloscope colours
- `wip_*` - Work-in-progress panels

---

## Testing Checklist

When adding a new skin, verify:
- [ ] All required keys present (compare to default.py)
- [ ] Contrast ratios meet accessibility guidelines
- [ ] Text readable on all backgrounds
- [ ] Accent colours distinguishable
- [ ] Meters/indicators visible
- [ ] No magenta (#ff00ff) appearing (missing key indicator)
