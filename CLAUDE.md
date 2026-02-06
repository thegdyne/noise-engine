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

Claude provides a ready-to-run command block like this:
```bash
dlclear

cd ~/repos/noise-engine

cp ~/Downloads/file1.py src/gui/
cp ~/Downloads/file2.scd supercollider/effects/

git add -A
git commit -m "Component: brief description of change"
git push
```

Just copy and paste the entire block into Terminal.

- `dlclear` clears ~/Downloads/ first (prevents stale file conflicts)
- Individual `cp` commands put each file in its correct location
- Git commands commit and push the changes

### If Something Goes Wrong
```bash
./tools/rollback.sh  # Undoes the last commit (asks for confirmation)
```

### Merge dev to main
When ready to release to main:

```bash
cd ~/repos/noise-engine
bash tools/check_all.sh          # Run all checks, update badges
git checkout main
git merge dev -m "Merge dev: brief description"
git push
git checkout dev
```

The `-m` flag avoids opening vi for a merge commit message.
Always run `check_all.sh` before merging - it runs SSOT + tech debt checks and updates both badges.

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
    sig = ~ensure2ch.(sig);  // REQUIRED: ensure stereo output for channel strip
    
    Out.ar(out, sig);
}).add;
```

### Helpers (defined in helpers.scd)
```supercollider
~multiFilter.(sig, filterType, filterFreq, rq)  // LP/HP/BP
~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex)
~stereoSpread.(sig, rate, width)  // optional stereo movement
~ensure2ch.(sig)  // REQUIRED: mono→dual-mono, stereo→pass, >2ch→mixdown
```

### Generator JSON Config
```json
{
    "name": "MyGenerator",
    "synthdef": "myGenerator",
    "output_trim_db": -6.0,
    "midi_retrig": false,
    "pitch_target": null,
    "custom_params": [
        {"key": "param1", "label": "P1", "default": 0.5, "min": 0, "max": 1, "curve": "lin"}
    ]
}
```

**Note:** `output_trim_db` is optional (defaults to 0.0). Use for hot generators that need attenuation.

### Adding a New Core Generator (Checklist)
1. Create `packs/core/generators/<name>.scd` — SynthDef (lightweight end-stage pattern)
2. Create `packs/core/generators/<name>.json` — Config metadata
3. **Add the display name to `_CORE_GENERATOR_ORDER` in `src/config/__init__.py`** — without this the generator won't appear in the UI cycle

Pack generators use their `manifest.json` instead of step 3.

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
| `tools/check_all.sh` | Run SSOT + tech debt checks, update both badges |
| `tools/ssot.sh` | Run SSOT check + update badge + auto-commit |
| `tools/check_ssot.py` | Smart SSOT checker (auto-discovers constants) |
| `tools/check_tech_debt.py` | Check for exception handling issues |
| `tools/_update_ssot_badge.sh` | Internal: Update SSOT badge in index.html |
| `tools/_update_techdebt_badge.sh` | Internal: Update tech debt badge in index.html |
| `tools/debug_add.sh` | Add debug output to SC files |
| `tools/debug_remove.sh` | Remove debug output from SC files |
| `tools/add_milestone.sh` | Add milestone to index.html |

## Edit Workflow Preferences

When making code changes:

1. **Small edits:** Use `sed -i ''` commands (no comments in command blocks — breaks copy-paste)
2. **Verify:** Use `grep -n` to confirm changes
3. **Big edits:** Give line numbers, user edits in vi
4. **Multi-step tasks:** Show percentage complete at each step, e.g. `**[Phase 2: 85%]**`

### Process Discipline

- **Keep it lean** — push back when over-engineering process
- **Tiered features:**
  - Large (1+ week): Spec + Rollout + CI gate
  - Medium (2-5 days): Spec only
  - Small (<1 day): Just do it
- Give honest critical feedback when deviating from lean approach

### Key Docs

- `PROCESS.md` — Lean workflow rules
- `BACKLOG.md` — Active work tracking
- `docs/IDEAS.md` — All captured feature ideas
- `docs/rollout/` — Phased rollout plans for large features

## STATE.md Maintenance

After any commit that touches these paths: `src/`, `supercollider/`, `packs/`, `tools/`:
1. Update `STATE.md` with the current truth
2. Include it in the commit

Escape hatch (rare): if you intentionally skip STATE.md, add `STATE_SKIP: <reason>` as its own line in the commit message (starts at column 1).

Rules:
- Always update **Last updated** date when touching STATE.md
- STATE.md describes what IS, not what WAS — no history narrative
- Subsystem status comes from the CODE, not from chat conversations
- Status values are an enum: Stable, Active, Built-unused, Planned, Blocked — no variants
- Only track actively-changing subsystems — remove rows when systems stabilise
- Active Concepts is where "latest approach" information lives — one line per concept
- Recent Changes: one line per session, keep last 10, prune oldest
- Known Issues: update `last_seen` date when re-confirmed; remove when fixed; move to BACKLOG.md if stale 30+ days
- If unsure whether something changed, check the code and update accordingly
- Do NOT update docs/index.html — that's managed separately via ssot.sh
