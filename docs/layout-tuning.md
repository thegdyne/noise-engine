# Layout Tuning Tool

Interactive tool for adjusting generator slot layout values in Noise Engine.

## Quick Start

```bash
# Show current values
python tools/tune_layout.py

# Move GEN label to the right
python tools/tune_layout.py gen right 4

# Reset to defaults
python tools/tune_layout.py reset
```

## Commands

### Header Position

| Command | Effect |
|---------|--------|
| `gen right [n]` | Move GEN label right |
| `gen left [n]` | Move GEN label left |
| `empty left [n]` | Move selector box left (away from edge) |
| `empty right [n]` | Move selector box right (toward edge) |
| `text right [n]` | Move "Empty" text right inside its box |
| `text left [n]` | Move "Empty" text left inside its box |

### Sizes

| Command | Effect |
|---------|--------|
| `selector wider` | Make selector box wider |
| `selector narrower` | Make selector box narrower |
| `buttons wider` | Make button strip wider |
| `buttons narrower` | Make button strip narrower |

### Vertical Spacing

| Command | Effect |
|---------|--------|
| `sliders up [n]` | Move sliders up (closer to header) |
| `sliders down [n]` | Move sliders down (more gap from header) |
| `rows closer [n]` | Reduce gap between P1-P5 and FRQ-DEC rows |
| `rows apart [n]` | Increase gap between slider rows |
| `sliders shorter` | Make sliders shorter |
| `sliders taller` | Make sliders taller |

### Horizontal Spacing

| Command | Effect |
|---------|--------|
| `columns narrower` | Make slider columns narrower |
| `columns wider` | Make slider columns wider |
| `columns closer` | Reduce gap between columns |
| `columns apart` | Increase gap between columns |
| `buttons closer` | Move button strip closer to sliders |
| `buttons apart` | Move button strip away from sliders |

### Other

| Command | Effect |
|---------|--------|
| `show` | Show all current values |
| `reset` | Reset all values to defaults |
| `help` | Show help |

## Examples

```bash
# Show current layout values
python tools/tune_layout.py show

# Move GEN label 4 pixels to the right
python tools/tune_layout.py gen right 4

# Move selector box to the left (more margin from edge)
python tools/tune_layout.py empty left 2

# Make sliders shorter for a more compact look
python tools/tune_layout.py sliders shorter

# Reduce gap between slider rows
python tools/tune_layout.py rows closer 2

# Reset everything to defaults
python tools/tune_layout.py reset
```

## Theme Keys Reference

The tool modifies these keys in `src/gui/theme.py`:

| Key | Default | Controls |
|-----|---------|----------|
| `header_inset_left` | 14 | Left margin for GEN label |
| `header_inset_right` | 6 | Right margin for selector box |
| `header_selector_text_pad` | 4 | Text padding inside selector |
| `header_type_width` | 40 | Width of selector box |
| `header_content_gap` | 2 | Gap between header and sliders |
| `slider_section_spacing` | 6 | Gap between P1-P5 and FRQ-DEC rows |
| `slider_min_height` | 38 | Minimum height of sliders |
| `slider_column_width` | 22 | Width of each slider column |
| `slider_gap` | 1 | Horizontal gap between columns |
| `button_strip_width` | 40 | Width of button strip |
| `content_row_spacing` | 2 | Gap between sliders and buttons |

## Visual Reference

```
┌─────────────────────────────────────────────────┐
│  ←header_inset_left→  GEN 1     Empty ←header_inset_right→  │
│                                  ↑                │
│                        header_selector_text_pad   │
│                                                   │
│  ←header_content_gap→                             │
│                                                   │
│  P1   P2   P3   P4   P5    ┌──────┐              │
│  ││   ││   ││   ││   ││    │  LP  │              │
│  ││   ││   ││   ││   ││    ├──────┤              │
│  ○│   ○│   ○│   ○│   ○│    │ OFF  │              │
│  ││   ││   ││   ││   ││    ├──────┤              │
│  ││   ││   ││   ││   ││    │ CLK  │              │
│  ↑                    ↑    └──────┘              │
│  slider_column_width  │         ↑                │
│  ←────slider_gap────→      button_strip_width    │
│                                                   │
│  ←slider_section_spacing→                         │
│                                                   │
│  FRQ  CUT  RES  ATK  DEC                         │
│  ...                                              │
└─────────────────────────────────────────────────┘
```

## Tips

- Start with `show` to see current values
- Make small adjustments (1-2 at a time)
- Use `reset` if things get messy
- The selector box width should match `button_strip_width` for alignment
