# Discord Update Style Guide

Templates and examples for posting project updates.

---

## Structure

```
**🔧 Noise Engine - [Topic]**

[What happened - 2-3 sentences max]

[Code block or visual breakdown if relevant]

**Check suite after:** (if applicable)
```
SSOT compliance:  X% 👑 (crown at 100%)
Tech debt score:  X% 🚜 (tractor at 100%)
```

---

**📋 What's Next**

*Quick wins:*
- [ ] Item (~time estimate)

*Foundation:*
- [ ] Item

*The fun stuff:*
- [ ] Item

[One-liner wrap-up]

**GitHub:** https://github.com/thegdyne/noise-engine
```

---

## Principles

- **Visual** - use code blocks, checkboxes, emoji sparingly
- **Scannable** - headers, short lines, whitespace
- **Honest** - "not flashy but..." is fine
- **Numbers** - line counts, percentages, time estimates
- **One-liner wrap-up** - tie it together at the end

---

## Emoji Usage

| Emoji | Meaning |
|-------|---------|
| 🔧 | Refactoring / maintenance |
| ✨ | New feature |
| 🐛 | Bug fix |
| 🎨 | UI / visual change |
| 🔊 | Audio / generator work |
| 📋 | Planning / roadmap |
| 👑 | 100% SSOT |
| 🚜 | 100% Tech Debt |
| ✓ | Complete |
| 😬 | Honest about gaps |

---

## Example: Refactoring Session

```
**🔧 Noise Engine - Session Update**

Quick refactoring win today. Had a 562-line `generator_slot.py` doing too much - UI construction mixed with state management and event handling.

Split it into two files, each with one job:
```
generator_slot.py         332 lines  ← signals, state, handlers
generator_slot_builder.py 273 lines  ← pure layout construction
─────────────────────────────────────
Total                     605 lines
```

Yes, more lines. But separation of concerns > line count.

**Check suite after:**
```
SSOT compliance:  100% 👑
Tech debt score:  100% 🚜
```

Docs updated, decision logged, Phase 2.7 complete. ✓

---

**📋 What's Next**

*Quick wins:*
- [ ] Hardcoded paths in scripts (~20 min)
- [ ] SSOT warning cleanup (~5 min)  
- [ ] README freshness check

*Foundation:*
- [ ] Automated tests (currently zero 😬)
- [ ] CI/CD via GitHub Actions

*The fun stuff:*
- [ ] Preset system - save/load patches as JSON
- [ ] MIDI CC mapping - MIDIMix integration
- [ ] More effects - delay, reverb

Not flashy but this is the stuff that makes the next phase easier.

**GitHub:** https://github.com/thegdyne/noise-engine
```

---

## Example: New Feature

```
**✨ Noise Engine - Preset System**

Finally. Save/load patches as JSON.

What gets saved:
- All 8 generator slots (type, params, custom params)
- Sticky settings (ENV, clock rate, MIDI channel, filter)
- Effects chain state
- Master volume

**Location:** `~/noise-engine-presets/` or custom folder

Drop a `.json`, it shows up in the preset browser. That simple.

---

**📋 What's Next**

*Quick wins:*
- [ ] Preset categories/folders
- [ ] Duplicate preset

*The fun stuff:*
- [ ] MIDI CC mapping
- [ ] Init preset (blank slate)

**GitHub:** https://github.com/thegdyne/noise-engine
```

---

## Example: Bug Fix

```
**🐛 Noise Engine - Fixed**

Generator wasn't responding to MIDI in slot 5-8. 

Cause: Off-by-one in the MIDI channel routing.
Fix: One line change in `midi_handler.scd`.

Tested all 8 slots, all 16 channels. ✓

---

**GitHub:** https://github.com/thegdyne/noise-engine
```

---

## Tips

- Keep it under 400 words
- Code blocks make technical stuff readable
- Checkbox lists for roadmap items
- Link to GitHub at the end
- "Not flashy but..." is honest and relatable
- Numbers are more interesting than adjectives
