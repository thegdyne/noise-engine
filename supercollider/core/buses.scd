/*
Bus Setup
Creates all control and audio buses

Default values are real values (not normalized):
  - frequency: 400 Hz (midpoint of 20-8000 exp)
  - cutoff: 16000 Hz (fully up = filter open)
  - resonance: 1.0 (fully down = no resonance, rq=1)
  - attack: 0.0001 s (snappiest = 0.1ms)
  - decay: 1.0 s
*/

// === CLOCK RATES (SSOT) ===
// Multipliers relative to quarter note (slowest to fastest)
// This is the single source of truth for clock rates
~clockRates = [1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 8, 12, 16, 32];

~setupBuses = {
    "Setting up buses...".postln;
    
    // Global parameters
    ~params = Dictionary.new;
    ~params[\gravity] = Bus.control(s, 1).set(0.5);
    ~params[\density] = Bus.control(s, 1).set(0.5);
    ~params[\filter_cutoff] = Bus.control(s, 1).set(0.7);
    ~params[\amplitude] = Bus.control(s, 1).set(0.5);
    
    // Master clock - uses ~clockRates.size for channel count
    ~clockBus = Bus.control(s, 1).set(120);
    ~clockTrigBus = Bus.audio(s, ~clockRates.size);
    
    // MIDI trigger bus - 8 audio channels, one per generator slot
    ~midiTrigBus = Bus.audio(s, 8);
    
    // Per-generator parameters (8 slots)
    // NOTE (Phase 6): Modulatable params (freq, cutoff, res, attack, decay, custom)
    // now use unified buses via ~busRegistry. Only non-modulatable params below
    // are still active. Legacy entries kept for backward compat but unused.
    ~genParams = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genParams[slot] = Dictionary.new;
        // DEPRECATED - now read from unified buses (~busRegistry)
        ~genParams[slot][\frequency] = Bus.control(s, 1).set(400);
        ~genParams[slot][\cutoff] = Bus.control(s, 1).set(16000);
        ~genParams[slot][\resonance] = Bus.control(s, 1).set(1.0);
        ~genParams[slot][\attack] = Bus.control(s, 1).set(0.0001);
        ~genParams[slot][\decay] = Bus.control(s, 1).set(1.0);
        // ACTIVE - non-modulatable params (not in unified system)
        ~genParams[slot][\filterType] = Bus.control(s, 1).set(0);
        ~genParams[slot][\envEnabled] = Bus.control(s, 1).set(0);
        ~genParams[slot][\envSource] = Bus.control(s, 1).set(0);           // 0=OFF, 1=CLK, 2=MIDI
        ~genParams[slot][\clockRate] = Bus.control(s, 1).set(6);  // 6 = CLK (quarter notes)
        ~genParams[slot][\portamento] = Bus.control(s, 1).set(0.0);
        // Analog output stage (per-slot)
        ~genParams[slot][\analogEnable] = Bus.control(s, 1).set(0);
        ~genParams[slot][\analogType] = Bus.control(s, 1).set(0);
        ~genParams[slot][\analogDrive] = Bus.control(s, 1).set(0.5);   // v0.2 — allocated, ignored by v0.1 types
        ~genParams[slot][\analogMix] = Bus.control(s, 1).set(1.0);     // v0.2 — allocated, ignored by v0.1 types
        // DEPRECATED - now read from unified buses
        ~genParams[slot][\custom] = Array.fill(5, { Bus.control(s, 1).set(0.5) });
    };

    // DEPRECATED (Phase 6): User-set parameter values for relative modulation
    // Unified bus system now handles base values via ~modTargetState in bus_unification.scd
    // Kept for backward compat with any external code that references these
    ~genUserParams = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genUserParams[slot] = Dictionary.new;
        ~genUserParams[slot][\frequency] = Bus.control(s, 1).set(400);
        ~genUserParams[slot][\cutoff] = Bus.control(s, 1).set(16000);
        ~genUserParams[slot][\resonance] = Bus.control(s, 1).set(1.0);
        ~genUserParams[slot][\attack] = Bus.control(s, 1).set(0.0001);
        ~genUserParams[slot][\decay] = Bus.control(s, 1).set(1.0);
        ~genUserParams[slot][\custom] = Array.fill(5, { Bus.control(s, 1).set(0.5) });
    };
    
    // Audio buses
    ~masterBus = Bus.audio(s, 2);
    
    // Per-generator output buses (8 stereo buses, one per slot)
    ~genBus = Array.fill(8, { Bus.audio(s, 2) });

    // === FX BUSES (Phase 1 - UI Refresh expansion to 4 slots) ===
    // Dry sum (channel strips write here)
    ~drySumBus = Bus.audio(s, 2);

    // Send buses (channel strips tap here based on send amounts)
    // Slot 1 & 2 (aliases for backward compat)
    ~fx1SendBus = Bus.audio(s, 2);
    ~fx2SendBus = Bus.audio(s, 2);
    ~fx3SendBus = Bus.audio(s, 2);  // NEW - UI Refresh
    ~fx4SendBus = Bus.audio(s, 2);  // NEW - UI Refresh

    // Legacy aliases for backward compat
    ~echoSendBus = ~fx1SendBus;
    ~verbSendBus = ~fx2SendBus;

    // Return buses (FX synths write 100% wet here)
    ~fx1ReturnBus = Bus.audio(s, 2);
    ~fx2ReturnBus = Bus.audio(s, 2);
    ~fx3ReturnBus = Bus.audio(s, 2);  // NEW - UI Refresh
    ~fx4ReturnBus = Bus.audio(s, 2);  // NEW - UI Refresh

    // Legacy aliases for backward compat
    ~echoReturnBus = ~fx1ReturnBus;
    ~verbReturnBus = ~fx2ReturnBus;

    // FX slot bus arrays (for slot manager)
    ~fxSendBuses = [~fx1SendBus, ~fx2SendBus, ~fx3SendBus, ~fx4SendBus];
    ~fxReturnBuses = [~fx1ReturnBus, ~fx2ReturnBus, ~fx3ReturnBus, ~fx4ReturnBus];

    
    // Solo system
    ~soloActive = Bus.control(s, 1).set(0);  // 1 if any channel soloed
    ~soloCount = 0;  // Track number of active solos
    ~stripSoloState = Array.fill(8, { 0 });  // Per-strip solo state
    
    // Instance tracking
    ~generators = Dictionary.new;
    ~channelStrips = Array.fill(8, { nil });  // Per-slot channel strips
    ~masterEffects = nil;
    ~clockSynth = nil;

    // Per-generator transpose (semitone offsets, 8 slots)
    ~genTranspose = Array.fill(8, { 0 });

    // Groups (order matters: clock -> generators -> strips -> fx)
    ~clockGroup = nil;
    ~genGroup = nil;
    ~stripGroup = nil;
    ~fxGroup = nil;
    ~mixerGroup = nil;
    ~masterGroup = nil;

    // End-stage infrastructure (allocated by endstage.scd ~bootEndstageInfra)
    // These are nil until boot; declared here for visibility
    ~intermediateBus = nil;     // Array[8] of stereo audio buses
    ~enhancedBus = nil;         // Array[8] of stereo audio buses (post-analog stage)
    ~slotGroup = nil;           // Array[8] of per-slot parent groups
    ~genSubGroup = nil;         // Array[8] of generator sub-groups
    ~analogSubGroup = nil;      // Array[8] of analog stage sub-groups
    ~endstageSubGroup = nil;    // Array[8] of end-stage sub-groups
    ~endstageNodes = nil;       // Array[8] of end-stage synth nodes
    ~analogNodes = nil;         // Array[8] of analog stage synth nodes
    ~silenceNodes = nil;        // Array[8] of silence gen nodes

    "  [x] Buses ready (% clock rates, % gen buses, 4 FX send/return pairs)".format(~clockRates.size, ~genBus.size).postln;
};
