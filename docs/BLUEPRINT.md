# Code Blueprint

## Questions While Coding

- Written this before? → Centralize
- Behavior in component? → Make a widget
- Know where to find it in 6 months? → Move it there
- Change X breaks Y? → Decouple

## Layers

| Layer | Knows | Contains |
|-------|-------|----------|
| Config | Values | Constants, mappings |
| Theme | Appearance | Colors, styles, sizes |
| Widgets | Behavior | Mouse, keyboard, drag |
| Components | Layout | Wire widgets, emit signals |
| Main | Connections | Route signals |

## Rules

- Same value 2+ places → centralize
- Name by what it IS, not where it's USED
- Widgets emit signals, never call business logic
- Start messy, refactor when patterns emerge

## Test

"Can I change X without touching Y?"
