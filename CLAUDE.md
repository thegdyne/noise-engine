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

## Key Patterns

### Generator SynthDef Signature
```supercollider
SynthDef(\name, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                   filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                   midiTrigBus=0, slotIndex=0,
                   customBus0, customBus1, customBus2, customBus3, customBus4|
```

### Envelope Source Pattern
```supercollider
// envSource: 0=OFF (drone), 1=CLK, 2=MIDI
trig = Select.ar(envSource, [DC.ar(0), clockTrig, midiTrig]);
env = EnvGen.ar(Env.perc(attack, decay), trig);
sig = sig * Select.kr(envSource > 0, [1.0, env]) * amp;
```

### Filter Helper
```supercollider
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
```

## Do NOT

- Use horizontal sliders (except sequencer)
- Hardcode colors/fonts outside theme.py
- Create menu diving / hidden UI
- Skip reading docs before making changes
- Forget the git workflow at the end
