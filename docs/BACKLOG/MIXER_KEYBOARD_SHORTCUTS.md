# Mixer Keyboard Shortcuts

## What

Add keyboard shortcut support to the mixer with a discoverable help menu.

## Why

Speed up workflow for common mixer operations. Reduce mouse dependency during performance/mixing sessions.

## Candidate Shortcuts

| Action | Shortcut | Notes |
|--------|----------|-------|
| Mute channel 1-8 | `1`-`8` | Toggle mute |
| Solo channel 1-8 | `Shift+1`-`8` | Toggle solo |
| Reset channel fader | `Ctrl+1`-`8` | Return to 0dB |
| Reset all faders | `Ctrl+0` | |
| Clear all solos | `Esc` | |
| Clear all mutes | `Shift+Esc` | |
| Master mute | `M` | |
| Help overlay | `?` | Show shortcut reference |

## UI

- `?` opens floating overlay showing all shortcuts
- Or: dedicated menu item (Help → Keyboard Shortcuts)
- Keep overlay minimal, dismiss on any key

## Open Questions

- Scope: Mixer only, or include generator/mod shortcuts?
- Conflict check: Any existing Qt shortcuts to avoid?
- Focus requirement: Only active when mixer has focus?

## Decision

*Pending*
