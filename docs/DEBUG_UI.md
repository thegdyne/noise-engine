# Debug UI Hierarchy Tool

Press **Fn+F12** (or just **F12** on some keyboards) while the app is running to dump the widget hierarchy to `/tmp/mod_slots_dump.txt`.

## Usage

1. Run the app: `python src/main.py`
2. Navigate to the UI area you want to inspect
3. Press **Fn+F12**
4. Check console for confirmation: `"Dumped to /tmp/mod_slots_dump.txt"`
5. View the dump: `cat /tmp/mod_slots_dump.txt`

## Output Format

```
widget_name (WidgetClass) WxH [flags]
  └─ hint:WxH | min:WxH | H:Policy V:Policy
```

### Fields

| Field | Meaning |
|-------|---------|
| `WxH` | Actual rendered size (width x height in pixels) |
| `⚠️FIXED WxH` | Widget has fixed size constraint |
| `⚠️H-FIXED W` | Only horizontal dimension is fixed |
| `⚠️V-FIXED H` | Only vertical dimension is fixed |
| `hint:WxH` | Widget's sizeHint (preferred size) |
| `min:WxH` | Minimum size constraint |
| `H:Policy` | Horizontal size policy |
| `V:Policy` | Vertical size policy |

### Size Policies

| Policy | Behavior |
|--------|----------|
| `Fixed` | Cannot grow or shrink |
| `Minimum` | Can grow, prefers minimum |
| `Maximum` | Can shrink, prefers maximum |
| `Preferred` | Prefers sizeHint, can grow/shrink |
| `Expanding` | Wants to grow |
| `MinimumExpanding` | Minimum size but wants to expand |
| `Ignored` | sizeHint ignored |

## Example Output

```
mod1_slot (ModulatorSlot) 176x377
  └─ hint:176x271 | min:140x0 | H:MinimumExpanding V:MinimumExpanding
  (unnamed) (QWidget) 168x84
    (unnamed) (QWidget) 20x76 ⚠️H-FIXED 20
      └─ hint:27x76 | min:20x0 | H:Fixed V:MinimumExpanding
      mod1_rate (DragSlider) 18x60 ⚠️FIXED 18x60
        └─ hint:22x84 | min:18x60 | H:Fixed V:7
```

This shows:
- `mod1_slot` is 176x377px, wants to expand both directions
- Contains an unnamed container (168x84)
- Which contains a fixed-width column (20px wide)
- Which contains the rate slider (fixed at 18x60)

## Troubleshooting Layout Issues

1. **Widget too wide?** Check if `H:` policy is `Expanding` or `MinimumExpanding` - it wants to grow
2. **Widget not respecting setFixedWidth?** Look for missing `⚠️FIXED` flag - the constraint isn't being applied
3. **Unexpected size?** Compare `hint:` vs actual size - layout may be overriding the hint
4. **Spacing issues?** Check parent container's spacing (not shown in dump - check code)

## Quick Commands

```bash
# View dump
cat /tmp/mod_slots_dump.txt

# Copy to clipboard (macOS)
cat /tmp/mod_slots_dump.txt | pbcopy

# Search for specific widget
grep "mod1_rate" /tmp/mod_slots_dump.txt

# Count widgets
wc -l /tmp/mod_slots_dump.txt
```

## Files

- `src/gui/debug_dump.py` - The dump implementation
- `src/gui/main_frame.py` - F12 hotkey registration (in `__init__`)
