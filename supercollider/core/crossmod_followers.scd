/*
Cross-Mod Envelope Followers
Track amplitude of each generator's output and write to cross-mod buses

Signal flow: ~genBus[n] -> Amplitude.kr -> ~crossModBus[n]

OUTPUT RANGE: 0 to 1 (UNIPOLAR)
  - Silence -> 0
  - Max amplitude -> 1

This is intentionally different from LFO/Sloth sources (-1 to +1).
Rationale: silence=0 is intuitive; users expect "no audio = no modulation."

Polarity mode behavior with 0..1 input:
  - bipolar: Treats 0..1 as half-range (0=center, 1=max)
  - uni+: Maps 0..1 -> 0.5..1 (use offset=-0.5 for full 0..1)
  - uni-: Maps 0..1 -> 0.5..0 (use offset=+0.5 for full 0..-1)
  - For sidechain ducking: use uni- with amount=1, offset=0.5

Trim: Applies ~crossModTrim[idx] to normalize loud/quiet generators.
      ~stripTrimState is the canonical trim value, shared with channel strip.

Group: Runs in ~genGroup at tail (after generator, before strip group).
*/

~setupCrossModFollowers = {
    "Setting up cross-mod followers...".postln;
    
    // SynthDef for envelope follower
    // Converts stereo audio to unipolar control signal (0 to 1)
    SynthDef(\crossModFollower, { |inBus, outBus, attack=0.01, release=0.1, enabled=1, trim=0|
        var sig, env, out;
        
        // Read stereo audio from generator bus
        sig = In.ar(inBus, 2);
        
        // Apply trim (dB) for loudness normalization
        // ~stripTrimState is canonical, shared with channel strip
        sig = sig * trim.dbamp;
        
        // Mix to mono, get amplitude (0 to ~1)
        sig = Mix(sig);
        env = Amplitude.kr(sig, attack, release);
        
        // Normalize to 0..1 range (unipolar)
        // silence=0, peak=1 (intuitive for envelope following)
        env = (env * 1.5).clip(0, 1);
        
        // Apply enabled gate (0 when disabled)
        out = env * enabled;
        
        // Write to control bus
        ReplaceOut.kr(outBus, out);
    }).add;
    
    "  [x] Cross-mod follower SynthDef ready (unipolar output 0..1)".postln;
};

// Start envelope follower for a slot (called when generator starts)
~startCrossModFollower = { |slot|
    var idx = slot - 1;
    
    if(idx < 0 || idx >= ~crossmodBusCount) {
        "ERROR: Invalid slot % for cross-mod follower".format(slot).postln;
        ^nil;
    };
    
    // Free existing follower
    if(~crossModFollowers[idx].notNil) {
        ~crossModFollowers[idx].free;
        ~crossModFollowers[idx] = nil;
    };
    
    // Create follower synth
    // Runs in genGroup at tail (after generator, before strip group)
    ~crossModFollowers[idx] = Synth(\crossModFollower, [
        \inBus, ~genBus[idx],
        \outBus, ~crossModBus[idx],
        \attack, ~crossModAttack[idx],
        \release, ~crossModRelease[idx],
        \enabled, if(~crossModEnabled[idx], 1, 0),
        \trim, ~crossModTrim[idx]
    ], ~genGroup, \addToTail);
    
    "  Started cross-mod follower for slot % (trim: %dB)".format(slot, ~crossModTrim[idx]).postln;
};

// Stop envelope follower for a slot (called when generator stops)
~stopCrossModFollower = { |slot|
    var idx = slot - 1;
    
    if(idx >= 0 && idx < ~crossmodBusCount) {
        if(~crossModFollowers[idx].notNil) {
            ~crossModFollowers[idx].free;
            ~crossModFollowers[idx] = nil;
            ~crossModBus[idx].set(0);  // Zero the bus (silence)
            "  Stopped cross-mod follower for slot %".format(slot).postln;
        };
    };
};

// Update follower attack time
~setCrossModAttack = { |slot, attack|
    var idx = slot - 1;
    if(idx >= 0 && idx < ~crossmodBusCount) {
        ~crossModAttack[idx] = attack;
        if(~crossModFollowers[idx].notNil) {
            ~crossModFollowers[idx].set(\attack, attack);
        };
        "Cross-mod attack slot %: %s".format(slot, attack).postln;
    };
};

// Update follower release time
~setCrossModRelease = { |slot, release|
    var idx = slot - 1;
    if(idx >= 0 && idx < ~crossmodBusCount) {
        ~crossModRelease[idx] = release;
        if(~crossModFollowers[idx].notNil) {
            ~crossModFollowers[idx].set(\release, release);
        };
        "Cross-mod release slot %: %s".format(slot, release).postln;
    };
};

// Update follower trim (called when /noise/gen/trim changes)
// ~stripTrimState is the canonical source, shared with channel strip
~setCrossModTrim = { |slot, trimDb|
    var idx = slot - 1;
    if(idx >= 0 && idx < ~crossmodBusCount) {
        ~crossModTrim[idx] = trimDb;
        if(~crossModFollowers[idx].notNil) {
            ~crossModFollowers[idx].set(\trim, trimDb);
        };
    };
};

// Enable/disable cross-mod output for a slot
// When disabled: frees synth (CPU efficient), bus reads 0
// Routes remain configured but receive 0 until re-enabled
~setCrossModEnabled = { |slot, enabled|
    var idx = slot - 1;
    if(idx >= 0 && idx < ~crossmodBusCount) {
        ~crossModEnabled[idx] = enabled;
        if(enabled) {
            // Re-create follower if generator is running
            if(~generators[idx].notNil) {
                ~startCrossModFollower.(slot);
            };
        } {
            // Free follower, zero bus
            if(~crossModFollowers[idx].notNil) {
                ~crossModFollowers[idx].free;
                ~crossModFollowers[idx] = nil;
            };
            ~crossModBus[idx].set(0);
        };
        "Cross-mod slot % %".format(slot, if(enabled, "enabled", "disabled (freed)")).postln;
    };
};

// Debug helper - show all cross-mod follower states
~debugCrossModFollowers = {
    "=== Cross-Mod Follower State ===".postln;
    ~crossmodBusCount.do { |i|
        var slot = i + 1;
        var synth = ~crossModFollowers[i];
        var busVal = ~crossModBus[i].getSynchronous;
        if(synth.notNil) {
            "  Slot %: ACTIVE (atk: %, rel: %, trim: %dB, bus: %)".format(
                slot, 
                ~crossModAttack[i].round(0.001),
                ~crossModRelease[i].round(0.01),
                ~crossModTrim[i],
                busVal.round(0.001)
            ).postln;
        } {
            if(~crossModEnabled[i]) {
                "  Slot %: inactive (no generator)".format(slot).postln;
            } {
                "  Slot %: DISABLED".format(slot).postln;
            };
        };
    };
};
