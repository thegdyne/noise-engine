# Noise Engine Tools

Development utilities for the Noise Engine project.

## Layout & UI

| Tool | Description |
|------|-------------|
| `tune_layout.py` | Interactive CLI for adjusting generator slot layout. See [docs/layout-tuning.md](../docs/layout-tuning.md) |
| `layout_sandbox.py` | Test slots in isolation with resizable window and torture tests |

## Layout Debugging

```bash
# Visual overlay showing widget sizes (or press F9 at runtime)
DEBUG_LAYOUT=1 python src/main.py

# Test slot in isolation
python tools/layout_sandbox.py --generator --torture
```

See [docs/LAYOUT_DEBUGGING.md](../docs/LAYOUT_DEBUGGING.md) for full guide.

## Code Quality

| Tool | Description |
|------|-------------|
| `check_all.sh` | Run all checks (SSOT, tech debt, SC syntax) |
| `check_ssot.py` | Verify Single Source of Truth compliance |
| `check_tech_debt.py` | Scan for tech debt markers |
| `check_sc_syntax.py` | Validate SuperCollider syntax |
| `ssot.sh` | Quick SSOT check wrapper |

## Debugging

| Tool | Description |
|------|-------------|
| `debug_add.sh` | Add debug logging to a module |
| `debug_remove.sh` | Remove debug logging |

## Git & Releases

| Tool | Description |
|------|-------------|
| `add_milestone.sh` | Add a milestone to DECISIONS.md |
| `rollback.sh` | Quick git rollback helper |
| `update_from_claude.sh` | Apply Claude-provided patches |
| `zip_for_claude.sh` | Package files for Claude context |

## CI/CD (prefixed with _)

| Tool | Description |
|------|-------------|
| `_check_ssot.sh` | CI wrapper for SSOT check |
| `_update_ssot_badge.sh` | Update SSOT badge in README |
| `_update_techdebt_badge.sh` | Update tech debt badge |
