# Shell Aliases for Noise Engine

Add these to your `~/.zshrc` (or `~/.bashrc`):

```bash
# Noise Engine aliases
alias noise_venv="cd ~/repos/noise-engine && source venv/bin/activate"
alias noise="cd ~/repos/noise-engine && source venv/bin/activate && python src/main.py"
alias noise-debug="cd ~/repos/noise-engine && source venv/bin/activate && DEBUG_LAYOUT=1 python src/main.py"
alias noise-torture="cd ~/repos/noise-engine && source venv/bin/activate && python tools/layout_sandbox.py --generator --torture"
alias noise-sandbox="cd ~/repos/noise-engine && source venv/bin/activate && python tools/layout_sandbox.py --generator"
alias noise-mod-sandbox="cd ~/repos/noise-engine && source venv/bin/activate && python tools/layout_sandbox.py --modulator"
```

Then reload: `source ~/.zshrc`

## Alias Reference

| Alias | Description |
|-------|-------------|
| `noise_venv` | Activate venv without running app |
| `noise` | Run Noise Engine normally |
| `noise-debug` | Run with layout debug overlay enabled (or press F9) |
| `noise-torture` | Test generator slot with long names |
| `noise-sandbox` | Test generator slot in isolation |
| `noise-mod-sandbox` | Test modulator slot in isolation |

## Usage Tips

### Quick Development Cycle
```bash
noise_venv           # Activate once
python src/main.py   # Run repeatedly without reactivating
```

### Layout Debugging
```bash
noise-debug          # Start with overlay ON
# or
noise                # Start normal, press F9 to toggle
```

### Testing Long Names
```bash
noise-torture        # Click "Next Name" to cycle through torture strings
```

## Runtime Hotkeys

| Key | Action |
|-----|--------|
| **F9** (Fn+F9 on Mac) | Toggle layout debug overlay |

## Dimension Convention

When discussing widget sizes, use `WIDTHxHEIGHT` format matching the debug overlay:

```
# Examples
Button: 160x27 → 180x27    # Width increased
Label: 115x16              # Fixed size
Mode button: 48x22         # Was squeezed to 19x22
```

This matches what you see in the debug overlay and makes changes clear.
