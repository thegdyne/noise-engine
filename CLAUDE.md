# Claude Instructions for Noise Engine

**READ FIRST:** Before making any changes, read the docs:
- `docs/PROJECT_STRATEGY.md` - Architecture, principles, current status
- `docs/DECISIONS.md` - All design decisions (DO NOT violate these)
- `docs/BLUEPRINT.md` - Code organization rules

## Workflow

Every response with code changes MUST end with:

```bash
cd ~/repos/noise-engine
~/repos/noise-engine/tools/update_from_claude.sh
git add -A
git commit -m "Component: brief description of change"
git push
```

Download must be named `noise-engine-updated.zip`.

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

## Do NOT

- Use horizontal sliders (except sequencer)
- Hardcode colors/fonts outside theme.py
- Create menu diving / hidden UI
- Skip reading docs before making changes
- Forget the git workflow at the end
- Reset slot settings (ENV, clock rate, MIDI channel, filter) when changing generator type - these are STICKY per slot
- Duplicate envelope/filter code in generators - USE HELPERS
- Use `~clockRates.size` in helpers - hardcode 13 (clock rates) and 8 (MIDI channels)
- Hardcode OSC paths - use OSC_PATHS from config
- Commit debug output to main branch

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
./tools/check_ssot.sh        # Run compliance check
./tools/update_ssot_badge.sh  # Update badge in index.html
```

100% = 👑 crown appears on the badge!
