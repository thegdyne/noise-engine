# UI Mockups

Static HTML/CSS mockups for visualizing skin concepts.

**Note:** These are design references only, not production code. They don't follow the centralized config/theme pattern.

When implementing real skins in PyQt, we'll use:
```python
# theme.py
SKINS = {
    'default': { ... },
    'winamp': { ... },
}
active_skin = 'default'
COLORS = SKINS[active_skin]
```

## Mockups

- `winamp_skin.html` - Classic Winamp aesthetic (green LED, beveled borders)
