# Layout Debugging Guide

When Qt layouts misbehave, it's usually because of invisible constraints that dominate geometry:
- A single `setFixedSize(40, 22)` 
- A stray `addStretch(1)`
- A widget's `sizeHint()` being larger than expected
- Custom `paintEvent()` drawing outside widget bounds

## Quick Debug Methods

### 1. Environment Variable (Visual Overlay)

```bash
DEBUG_LAYOUT=1 python src/main.py
```

This draws colored overlays on every widget showing:
- Widget name/class
- Actual size (WxH)
- Size hint

### 2. Print Widget Tree

```python
from gui.layout_debug import print_widget_info
print_widget_info(self)  # In any widget
```

Output:
```
GeneratorSlot:
  geometry: 280x350 at (10,10)
  sizeHint: 250x300
  minSizeHint: 200x250
  policy: H=5 V=5
  min: 0x0
  max: 16777215x16777215
  layout: QVBoxLayout
  margins: L=4 T=4 R=4 B=4
  spacing: 6
    type_btn:
      geometry: 75x22 at (...)
      ...
```

### 3. Log Single Widget

```python
from gui.layout_debug import log_size_constraints
log_size_constraints(self.type_btn, "type_btn")
```

Output:
```
[type_btn] geo=75x22 hint=120x22 policy=(Fixed,Fixed) min=40x22 max=75x22
```

### 4. Enable at Runtime

```python
from gui.layout_debug import enable_layout_debug, disable_layout_debug

# Debug specific widget
enable_layout_debug(self.generator_frame)

# Debug all windows
enable_layout_debug()

# Turn off
disable_layout_debug()
```

## Common Qt Layout Gotchas

### 1. sizeHint vs Actual Size

A widget wants to be `sizeHint()` but can be forced smaller/larger by:
- `setFixedWidth()` / `setFixedHeight()` / `setFixedSize()`
- `setMinimumWidth()` / `setMaximumWidth()`
- `QSizePolicy` (Fixed, Expanding, Ignored, etc.)
- Parent layout constraints

**Debug:** If widget is wrong size, check all of these.

### 2. Stretch Dominates

```python
layout.addWidget(sliders)
layout.addStretch(1)  # This consumes ALL extra space
layout.addWidget(buttons)
```

The stretch gets 100% of leftover space. Buttons get pushed to edge.

**Fix:** Remove stretch, or use `addWidget(..., stretch=0)` for fixed items.

### 3. Labels Force Width

QLabel's `sizeHint()` is based on text content. A label saying "WAVETABLE" wants ~80px even if you put it in a 40px column.

**Fix:** 
```python
label.setFixedWidth(40)
label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
```

### 4. Custom Paint Escapes Bounds

```python
def paintEvent(self, event):
    p = QPainter(self)
    p.drawText(0, 15, "Very Long Text Here")  # Draws outside widget!
```

**Fix:**
```python
def paintEvent(self, event):
    p = QPainter(self)
    p.setClipRect(self.rect())  # Clip to widget bounds
    # ... draw
```

### 5. Fixed vs Expanding

| Policy | Behavior |
|--------|----------|
| `Fixed` | Widget is exactly `sizeHint()` |
| `Preferred` | `sizeHint()` preferred, can grow/shrink |
| `Expanding` | Takes all available space |
| `Minimum` | At least `sizeHint()`, can grow |
| `Ignored` | `sizeHint()` ignored, can be any size |

**Common pattern:**
```python
# Shrink to content, don't expand
widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
```

## Widget Color Key (Debug Mode)

| Color | Widget Type |
|-------|-------------|
| Red | QFrame |
| Green | QWidget |
| Blue | QLabel |
| Yellow | QPushButton |
| Magenta | QSlider |
| Gray | Other |

## Adding Debug to New Widgets

```python
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("MyWidget")  # Shows in debug overlay
```

Always set `objectName` for easier debugging!
