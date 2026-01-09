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
    // Default values are real values matching Python config
    ~genParams = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genParams[slot] = Dictionary.new;
        ~genParams[slot][\frequency] = Bus.control(s, 1).set(400);         // Hz (midpoint)
        ~genParams[slot][\cutoff] = Bus.control(s, 1).set(16000);          // Hz (fully up)
        ~genParams[slot][\resonance] = Bus.control(s, 1).set(1.0);         // rq (no resonance)
        ~genParams[slot][\attack] = Bus.control(s, 1).set(0.0001);         // s (snappiest)
        ~genParams[slot][\decay] = Bus.control(s, 1).set(1.0);              // s (1s)
        ~genParams[slot][\filterType] = Bus.control(s, 1).set(0);
        ~genParams[slot][\envEnabled] = Bus.control(s, 1).set(0);          // Legacy, kept for compat
        ~genParams[slot][\envSource] = Bus.control(s, 1).set(0);           // 0=OFF, 1=CLK, 2=MIDI
        ~genParams[slot][\clockRate] = Bus.control(s, 1).set(6);  // 6 = CLK (quarter notes)
        ~genParams[slot][\portamento] = Bus.control(s, 1).set(0.0);
        
        // Custom params (5 per slot) - defaults based on generator JSON
        ~genParams[slot][\custom] = Array.fill(5, { Bus.control(s, 1).set(0.5) });
    };
    
    // User-set parameter values (for relative modulation)
    // Sliders write here, modApply reads this as center point
    // When no modulation active, these are copied to ~genParams
    ~genUserParams = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genUserParams[slot] = Dictionary.new;
        ~genUserParams[slot][\frequency] = Bus.control(s, 1).set(400);
        ~genUserParams[slot][\cutoff] = Bus.control(s, 1).set(16000);
        ~genUserParams[slot][\resonance] = Bus.control(s, 1).set(1.0);
        ~genUserParams[slot][\attack] = Bus.control(s, 1).set(0.0001);
        ~genUserParams[slot][\decay] = Bus.control(s, 1).set(1.0);
        // Custom params (P1-P5)
        ~genUserParams[slot][\custom] = Array.fill(5, { Bus.control(s, 1).set(0.5) });
    };
    
    // Audio buses
    ~masterBus = Bus.audio(s, 2);
    
    // Per-generator output buses (8 stereo buses, one per slot)
    ~genBus = Array.fill(8, { Bus.audio(s, 2) });

    // === FX BUSES (Phase 1) ===
    // Dry sum (channel strips write here)
    ~drySumBus = Bus.audio(s, 2);
    
    // Send buses (channel strips tap here based on send amounts)
    ~echoSendBus = Bus.audio(s, 2);
    ~verbSendBus = Bus.audio(s, 2);
    
    // Return buses (FX synths write 100% wet here)
    ~echoReturnBus = Bus.audio(s, 2);
    ~verbReturnBus = Bus.audio(s, 2);

    
    // Solo system
    ~soloActive = Bus.control(s, 1).set(0);  // 1 if any channel soloed
    ~soloCount = 0;  // Track number of active solos
    ~stripSoloState = Array.fill(8, { 0 });  // Per-strip solo state
    
    // Instance tracking
    ~generators = Dictionary.new;
    ~channelStrips = Array.fill(8, { nil });  // Per-slot channel strips
    ~masterEffects = nil;
    ~clockSynth = nil;
    
    // Groups (order matters: clock -> generators -> strips -> fx)
    ~clockGroup = nil;
    ~genGroup = nil;
    ~stripGroup = nil;
    ~fxGroup = nil;
    ~mixerGroup = nil;
    ~masterGroup = nil;
    
    "  [x] Buses ready (% clock rates, % gen buses, user params for relative mod)".format(~clockRates.size, ~genBus.size).postln;
};
