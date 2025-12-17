# Layout Debugging Guide

When Qt layouts misbehave, it's usually because of invisible constraints that dominate geometry:
- A single `setFixedSize(40, 22)` 
- A stray `addStretch(1)`
- A widget's `sizeHint()` being larger than expected
- Custom `paintEvent()` drawing outside widget bounds

## Quick Start

### F9 Toggle (Runtime)
Press **F9** at any time to toggle the layout debug overlay on/off.

```
[Layout Debug] Press F9 to toggle X-ray mode
[Layout Debug] ENABLED - Red borders = fixed size
[Layout Debug] DISABLED
```

### Environment Variable (Startup)
```bash
DEBUG_LAYOUT=1 python src/main.py
```

### Layout Sandbox (Isolated Testing)
```bash
# Test generator slot in isolation
python tools/layout_sandbox.py --generator

# Test modulator slot
python tools/layout_sandbox.py --modulator

# Torture test with long names
python tools/layout_sandbox.py --generator --torture
```

## What the Overlay Shows

- **Colored backgrounds** by widget type (red=QFrame, green=QWidget, etc.)
- **Red borders** = widget has FIXED size constraints (watch these!)
- **Text overlay** shows: name, actual size, size hint
- **⚠️ FIXED** marker in console output for constrained widgets

## Debug Functions

### Print Widget Tree
```python
from gui.layout_debug import print_widget_info
print_widget_info(self)  # In any widget
```

### Quick One-Liner
```python
from gui.layout_debug import dump_layout
dump_layout(self.type_btn)
# Output: type_btn: geo=75x22 hint=120x22 policy=(Fixed,Fixed) min=40x22 max=75x22
```

### Log Single Widget
```python
from gui.layout_debug import log_size_constraints
log_size_constraints(self.type_btn, "type_btn")
# Output: [type_btn] geo=75x22 hint=120x22 policy=(Fixed,Fixed) min=40x22 max=75x22 ⚠️FIXED
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
