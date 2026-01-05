# init.scd Idempotency Changes

Goal: make `supercollider/init.scd` safe to load multiple times without duplicating responders, tasks, nodes, or allocations.

---

## Minimum Required Guard

Wrap the entire init content with this pattern:

```supercollider
(
~noiseEngine = ~noiseEngine ? ();
if (~noiseEngine[\initDone] == true) {
    "NoiseEngine: init already loaded; skipping".postln;
} {
    ~noiseEngine[\initDone] = true;

    // ========================================
    // EXISTING INIT CONTENT GOES HERE
    // ========================================

    "NoiseEngine: init complete".postln;
};
)
```

---

## Applying to Your Current init.scd

Your init.scd currently looks like:

```supercollider
/*
Noise Engine - SuperCollider Initialization
...
*/

~basePath = PathName(thisProcess.nowExecutingPath).parentPath;
(~basePath +/+ "config.scd").load;
...
s.waitForBoot({
    ...
});
```

### Change 1: Add guard at TOP

Replace the opening with:

```supercollider
/*
Noise Engine - SuperCollider Initialization
Modular loader - each component in its own file
*/

(
// Idempotency guard
~noiseEngine = ~noiseEngine ? ();
if (~noiseEngine[\initDone] == true) {
    "NoiseEngine: init already loaded; skipping".postln;
} {

// Base path for loading files (needed before boot)
~basePath = PathName(thisProcess.nowExecutingPath).parentPath;

// Load central config
(~basePath +/+ "config.scd").load;

// ... rest of existing content ...
```

### Change 2: Close guard at END of s.waitForBoot

Find the end of the `s.waitForBoot({ ... });` block and add:

```supercollider
    // ... existing s.waitForBoot content ...

    // Mark init complete
    ~noiseEngine[\initDone] = true;
    "NoiseEngine: init complete".postln;

}); // end s.waitForBoot

// Close idempotency guard
};
)
```

---

## Non-Negotiables for True Idempotency

### 1. OSCdefs Must Use Stable Symbol Keys

**Bad** (anonymous - will stack):
```supercollider
OSCdef({ |msg| ... }, '/noise_engine/foo');
```

**Good** (stable key - redefinition replaces):
```supercollider
OSCdef(\ne_foo, { |msg| ... }, '/noise_engine/foo');
```

### 2. MIDIdefs Must Use Stable Keys

```supercollider
MIDIdef.noteOn(\ne_noteOn, { |vel, num, chan, src| ... });
MIDIdef.cc(\ne_cc, { |val, num, chan, src| ... });
```

### 3. Tasks/Routines Must Be Stored and Guarded

**Pattern:**
```supercollider
~noiseEngine[\tasks] = ~noiseEngine[\tasks] ? IdentityDictionary.new;

if (~noiseEngine[\tasks][\clock].isNil) {
    ~noiseEngine[\tasks][\clock] = Task({
        loop { 1.wait; "tick".postln; }
    }).play;
};
```

### 4. Groups/Busses/Buffers Created Once

**Groups:**
```supercollider
~noiseEngine[\grp] = ~noiseEngine[\grp] ? Group.head(s);
```

**Audio Busses:**
```supercollider
~noiseEngine[\busses] = ~noiseEngine[\busses] ? ();
~noiseEngine[\busses][\main] = ~noiseEngine[\busses][\main] ? Bus.audio(s, 2);
```

**Buffers:**
```supercollider
~noiseEngine[\bufs] = ~noiseEngine[\bufs] ? ();
if (~noiseEngine[\bufs][\ir].isNil) {
    ~noiseEngine[\bufs][\ir] = Buffer.read(s, "/path/to/ir.wav");
};
```

---

## Audit Checklist

Run through your init.scd and sub-files:

- [ ] Every `OSCdef` has a symbol key starting `\ne_`
- [ ] Every `MIDIdef` has a symbol key starting `\ne_`
- [ ] Any `.play` stores a handle and is guarded
- [ ] Allocations stored under `~noiseEngine[...]`
- [ ] Server boot is NOT triggered inside init (bootstrap owns boot)
- [ ] No duplicate handler accumulation on reload

---

## Verification

After making changes:

1. Start fresh SC
2. Load init.scd (Cmd+A, Cmd+Enter)
3. See "NoiseEngine: init complete" in post window
4. Load init.scd again (Cmd+A, Cmd+Enter)
5. See "NoiseEngine: init already loaded; skipping"

If you see any errors or duplicate output, something wasn't wrapped correctly.

---

## Note on Sub-Files

Your init.scd loads many sub-files (`core/buses.scd`, `core/clock.scd`, etc.). The top-level guard should prevent double-loading entirely. However, if you ever load sub-files independently, they should have their own guards using the same pattern:

```supercollider
// core/buses.scd
if (~noiseEngine[\busesReady] != true) {
    ~noiseEngine[\busesReady] = true;
    // ... bus setup ...
};
```

For Phase 1, the top-level guard is sufficient.
