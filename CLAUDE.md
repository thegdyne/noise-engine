# Claude Instructions for Noise Engine

**Current year: 2025** (use this for all dates, timestamps, milestones)

**READ FIRST:** Before making any changes, read the docs:
- `docs/PROJECT_STRATEGY.md` - Architecture, principles, current status
- `docs/DECISIONS.md` - All design decisions (DO NOT violate these)
- `docs/BLUEPRINT.md` - Code organization rules
- `docs/TECH_DEBT.md` - Known issues to fix
- `docs/FUTURE_IDEAS.md` - Planned features

## Important Rules

### DO NOT include docs/index.html in zips
The landing page badge is updated by `bash tools/ssot.sh` on the user's machine. Including index.html in Claude's zip will overwrite the badge with stale data.

## Workflow

### Giving Files to Claude

Always zip from the **dev branch** using the helper tool:
```bash
./tools/zip_for_claude.sh
# Creates ~/Downloads/noise-engine-dev.zip
# Upload this file to Claude
```

⚠️ **Never zip from main** - dev has the latest work. The filename includes the branch name so you can verify.

### Receiving Changes from Claude

Claude outputs **individual changed files only**, not full project zips.
This prevents accidentally overwriting newer files with older versions.

After downloading individual files, copy them to your repo manually or drag into your editor.

### After Applying Changes
```bash
cd ~/repos/noise-engine
git add -A
git commit -m "Component: brief description of change"
git push
```

### If Something Goes Wrong
```bash
./tools/rollback.sh  # Undoes the last commit (asks for confirmation)
```

### Merge dev to main
When ready to release to main:

```bash
cd ~/repos/noise-engine
bash tools/ssot.sh              # Always run first - updates badge
git checkout main
git merge dev -m "Merge dev: brief description"
git push
git checkout dev
```

The `-m` flag avoids opening vi for a merge commit message.
Always run `ssot.sh` before merging - it updates the badge in index.html.

### Publish Landing Page Update
To push index.html changes to the live site (GitHub Pages on main branch):

```bash
cd ~/repos/noise-engine
git checkout main
git checkout dev -- docs/index.html
git add docs/index.html
git commit -m "Update landing page"
git push
git checkout dev
```

Site: https://thegdyne.github.io/noise-engine/

## Critical: OSC Connection

Port 57120 is **forced** in SC init.scd - no manual checking needed.

Connection features:
- **Ping/pong** verification on connect (1 second timeout)
- **Heartbeat** monitoring every 2 seconds during performance
- **CONNECTION LOST** warning after 3 missed heartbeats
- **One-click reconnect** button

If connection fails on startup, SC isn't running or init.scd wasn't loaded.

## Key Patterns

### Generator Structure (use helpers!)
```supercollider
SynthDef(\name, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                   filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                   midiTrigBus=0, slotIndex=0,
                   customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    // ... etc
    
    // === SOUND SOURCE === (unique per generator)
    sig = ...;
    
    // === PROCESSING CHAIN === (use helpers - DO NOT duplicate!)
    sig = ~stereoSpread.(sig, 0.2, 0.3);  // optional
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;
```

### Helpers (defined in helpers.scd)
```supercollider
~multiFilter.(sig, filterType, filterFreq, rq)  // LP/HP/BP
~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex)
~stereoSpread.(sig, rate, width)  // optional stereo movement
```

### Generator JSON Config
```json
{
    "name": "MyGenerator",
    "synthdef": "myGenerator",
    "midi_retrig": false,
    "pitch_target": null,
    "custom_params": [
        {"key": "param1", "label": "P1", "default": 0.5, "min": 0, "max": 1, "curve": "lin"}
    ]
}
```

## Do NOT

- Use horizontal sliders (except sequencer)
- Hardcode colors/fonts outside theme.py:
  - Colors: use `COLORS['key']` from theme.py
  - Font sizes: use `FONT_SIZES['key']` from theme.py (NOT `14px`, `12px`, etc.)
  - Font family: use `FONT_FAMILY` or `MONO_FONT` from theme.py
- Create menu diving / hidden UI
- Skip reading docs before making changes
- Forget the git workflow at the end
- Reset slot settings (ENV, clock rate, MIDI channel, filter) when changing generator type - these are STICKY per slot
- Duplicate envelope/filter code in generators - USE HELPERS
- Use `~clockRates.size` in helpers - hardcode 13 (clock rates) and 8 (slots)
- Hardcode OSC paths - use OSC_PATHS from config
- Commit debug output to main branch
- Merge to main without explicit user agreement

## Debugging

When investigating issues:
```bash
./tools/debug_add.sh   # Add debug output (creates backups)
# ... investigate ...
./tools/debug_remove.sh  # Remove debug output (restores backups)
```

See `docs/DEBUGGING.md` for common issues and solutions.

## SSOT Compliance

After making changes, verify SSOT compliance:
```bash
bash tools/ssot.sh  # Runs check, updates badge, commits if changed
```

100% = 👑 crown appears on the badge!

## Tools Reference

| Script | Purpose |
|--------|---------|
| `tools/zip_for_claude.sh` | Create zip of current branch for uploading to Claude |
| `tools/rollback.sh` | Undo the last commit (with confirmation) |
| `tools/update_from_claude.sh` | Extract Claude's zip, apply changes, auto-checkout dev |
| `tools/ssot.sh` | Run SSOT check + update badge + auto-commit |
| `tools/_check_ssot.sh` | Internal: SSOT compliance check |
| `tools/_update_ssot_badge.sh` | Internal: Update badge in index.html |
| `tools/debug_add.sh` | Add debug output to SC files |
| `tools/debug_remove.sh` | Remove debug output from SC files |
| `tools/add_milestone.sh` | Add milestone to index.html |
