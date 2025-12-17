# Why We Built Layout Debug Tools

**TL;DR:** We lost days trying to move UI elements by changing theme values. Nothing worked because Qt layouts don't behave like CSS. We couldn't see what was actually constraining the geometry. Now we can.

---

## The Problem

### What We Were Trying To Do
Simple stuff:
- Move "GEN 1" label to the right
- Make the generator slots more compact
- Align "Empty" selector with the button strip
- Get the modulator mode button to show "CLK" instead of "C..."

### What Actually Happened

**Day 1:** "I'll just change `header_inset_left` from 6 to 14"
```bash
sed -i '' "s/'header_inset_left': 6/'header_inset_left': 14/" src/gui/theme.py
```
*Nothing moved.*

**Day 1.5:** "Maybe it's the frame padding?"
```bash
sed -i '' "s/'frame_padding': (4, 4, 4, 4)/'frame_padding': (0, 4, 4, 4)/" src/gui/theme.py
```
*Still nothing.*

**Day 2:** "Let me try removing the stretch..."
```bash
# Changed code, ran app, no change
# Changed more code, ran app, now everything is broken
# Reverted, tried again...
```

**Day 2.5:** "WHY WON'T IT MOVE?!"

---

## Why It Didn't Work

### Qt Layouts ≠ CSS Boxes

In CSS/web:
```css
.header { margin-left: 14px; }  /* Just works */
```

In Qt, a widget's position is determined by (in priority order):
1. **setFixedSize/Width/Height** - Absolute override
2. **setMinimum/MaximumSize** - Hard bounds
3. **sizePolicy** - How widget negotiates with layout
4. **sizeHint()** - What widget *wants* to be
5. **Layout margins/spacing** - What we were changing
6. **Stretch factors** - Who gets leftover space

We were changing #5 while #1-4 were locking things in place.

### The Invisible Constraints

A single line buried in the code:
```python
btn.setMaximumWidth(mt['slider_column_width'])  # 26px max!
```

This made the mode button only 26px wide. We could change margins, padding, and spacing all day - the button would never grow past 26px.

### The Stretch Trap

```python
layout.addLayout(slider_section, stretch=1)
layout.addWidget(button_strip)
```

That `stretch=1` meant: "Give ALL extra space to slider_section." The button strip was pushed to the edge. No amount of margin changes could bring it closer - the stretch consumed everything.

### Custom Paint Escapes Bounds

CycleButton used custom `paintEvent()` to draw text. Qt's text rendering doesn't respect widget bounds by default:
```python
def paintEvent(self, event):
    p.drawText(0, 15, "Very Long Synth Name")  # Draws OUTSIDE widget!
```

The text spilled over because we never called `setClipRect()`.

---

## What We Couldn't See

- Which widgets had fixed size constraints
- What each widget's actual sizeHint was
- Which stretches were consuming space
- Where the layout margins actually applied
- Why a 48px-wide button was rendering at 19px

**We were debugging blind.**

---

## The Solution

### 1. Visual Debug Overlay (F9)

Press F9 to see:
- Colored backgrounds showing widget bounds
- **Red borders** on fixed-size widgets (the troublemakers!)
- Text overlay: actual size, sizeHint, widget name

Now when something won't move, we can immediately see "oh, it has a red border - it's fixed size."

### 2. Layout Sandbox

Test slots in isolation:
```bash
python tools/layout_sandbox.py --generator --torture
```

Iterate in seconds without running the full app. Resize window to test different sizes.

### 3. Torture Testing

Force worst-case names:
```
"Subtractive (Resonant Overdrive + Noise)"
"FM + Waveshaper + Feedback"
```

If it looks good with these, it's good everywhere.

### 4. dump_layout() One-Liner

```python
from gui.layout_debug import dump_layout
dump_layout(self.type_btn)
# type_btn: geo=75x22 hint=120x22 policy=(Fixed,Fixed) min=40x22 max=75x22 ⚠️FIXED
```

Instantly reveals why a widget won't resize.

---

## Lessons Learned

### 1. "Kill Stretches First"
When layout is weird, temporarily remove ALL:
- `addStretch()`
- `addSpacerItem()`  
- `Expanding` size policies

Get deterministic, then add elasticity deliberately.

### 2. "Red Borders for Constraints"
Any time you use `setFixedWidth/Height/Size`, add a comment:
```python
btn.setFixedWidth(48)  # FIXED: must match theme.mode_button_width
```

In debug mode, these get red borders.

### 3. "One Knob Per Concept"
Don't reuse theme keys for multiple purposes. Split:
- `column_width` vs `button_width`
- `label_gap` vs `slider_gap`

Prevents "I changed X but Y moved."

### 4. "Container Constrains Contents"
A 26px-wide container cannot hold a 48px button. The button gets squeezed. Always check the container width, not just the widget width.

### 5. "sizeHint Is Just a Wish"
A widget's `sizeHint()` is what it *wants*. What it *gets* depends on policy, min/max, and container. They're often different.

---

## Time Cost

| Without Debug Tools | With Debug Tools |
|---------------------|------------------|
| 2+ days on layout issues | 10 minutes |
| Guessing at constraints | See them instantly |
| Trial-and-error sed commands | Targeted fixes |
| "Why won't it move?!" | "Oh, it's fixed size" |

---

## Files Created

| File | Purpose |
|------|---------|
| `src/gui/layout_debug.py` | Debug overlay, F9 toggle, dump functions |
| `tools/layout_sandbox.py` | Isolated slot testing |
| `tools/tune_layout.py` | Interactive layout adjustment |
| `docs/LAYOUT_DEBUGGING.md` | Usage guide |
| `docs/ALIASES.md` | Shell aliases |

---

## The Moral

**You can't fix what you can't see.**

Qt layouts are powerful but opaque. The debug tools make the invisible visible. Now layout work takes minutes instead of days.

Press F9. See what's really happening. Fix it.
