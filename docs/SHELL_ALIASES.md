# Noise Engine Shell Aliases

Development aliases to streamline workflow. Add to `~/.zshrc`.

## Quick Start

| Alias | Description |
|-------|-------------|
| `noise` | Launch Noise Engine |
| `noise_venv` | Activate venv without launching |
| `noise-debug` | Launch with debug layout borders |

## Aliases

### Core
```bash
# Activate venv only
alias noise_venv="cd ~/repos/noise-engine && source venv/bin/activate"

# Launch app
alias noise="cd ~/repos/noise-engine && source venv/bin/activate && python src/main.py"

# Launch with debug layout visualization
alias noise-debug="cd ~/repos/noise-engine && source venv/bin/activate && DEBUG_LAYOUT=1 python src/main.py"
```

### Testing & Sandbox
```bash
# Generator layout sandbox
alias noise-sandbox="cd ~/repos/noise-engine && source venv/bin/activate && python tools/layout_sandbox.py --generator"

# Modulator layout sandbox
alias noise-mod-sandbox="cd ~/repos/noise-engine && source venv/bin/activate && python tools/layout_sandbox.py --modulator"

# Generator torture test (stress test layouts)
alias noise-torture="cd ~/repos/noise-engine && source venv/bin/activate && python tools/layout_sandbox.py --generator --torture"
```

### Export & Sharing
```bash
# Tar changed files (vs main) for sharing
alias noise-tar="cd ~/repos/noise-engine && git diff --name-only main | xargs -I {} sh -c 'test -f {} && echo {}' | COPYFILE_DISABLE=1 tar -cvf ~/Downloads/changes.tar -T - && echo '\n~/Downloads/changes.tar'"

# Full project tar (excludes .git, venv, cache)
alias noise-full="cd ~/repos/noise-engine && COPYFILE_DISABLE=1 tar -cvf ~/Downloads/noise-engine-full.tar --exclude='.git' --exclude='node_modules' --exclude='__pycache__' --exclude='.venv' --exclude='venv' --exclude='*.pyc' --exclude='docs' --exclude='.pytest_cache' --exclude='*.egg-info' --exclude='.DS_Store' . && echo '\n~/Downloads/noise-engine-full.tar'"
```

### Git
```bash
# Commit with branch reminder (avoids committing to wrong branch)
alias gc='echo "Branch: $(git branch --show-current)" && git commit'
```

### Utilities
```bash
# Clean Downloads of dev files (scd, py, md, html, pdf, json, zip, duplicates)
alias dlclear='find ~/Downloads -maxdepth 1 \( -name "*.scd" -o -name "*.py" -o -name "*.md" -o -name "*.html" -o -name "*.pdf" -o -name "*.json" -o -name "*.zip" -o -regex ".* ([0-9]+)\..*" \) -delete'

# Copy stdin to clipboard AND echo (use: cmd | cpb)
cpb() {
    local tmp=$(mktemp)
    cat > "$tmp"
    if [ -s "$tmp" ]; then
        cat "$tmp"
        pbcopy < "$tmp"
    else
        echo "(no output)"
        echo "(no output)" | pbcopy
    fi
    rm -f "$tmp"
}
```

## Installation

Add all aliases to `~/.zshrc`:
```bash
# Copy the aliases above into ~/.zshrc
# Then reload:
source ~/.zshrc
```

## Usage Examples
```bash
# Start working
noise_venv
python -m pytest tests/ -x -q

# Quick launch
noise

# Debug layout issues
noise-debug

# Share changes with collaborator
noise-tar
# Sends ~/Downloads/changes.tar

# Share full project
noise-full
```

---

*Last updated: 2025-12-19*
