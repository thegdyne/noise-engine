/*
Bus Setup
Creates all control and audio buses

Default values are real values (not normalized):
  - frequency: 400 Hz (midpoint of 20-8000 exp)
  - cutoff: 16000 Hz (fully up = filter open)
  - resonance: 1.0 (fully down = no resonance, rq=1)
  - attack: 0.0001 s (snappiest = 0.1ms)
  - decay: 0.04 s (~40ms)
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
    
    // MIDI trigger bus - 8 channels, one per generator slot
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
        ~genParams[slot][\decay] = Bus.control(s, 1).set(0.04);            // s (~40ms)
        ~genParams[slot][\filterType] = Bus.control(s, 1).set(0);
        ~genParams[slot][\envEnabled] = Bus.control(s, 1).set(0);
        ~genParams[slot][\clockRate] = Bus.control(s, 1).set(6);  // 6 = CLK (quarter notes)
        
        // Custom params (5 per slot) - defaults based on generator JSON
        ~genParams[slot][\custom] = Array.fill(5, { Bus.control(s, 1).set(0.5) });
    };
    
    // Audio buses
    ~masterBus = Bus.audio(s, 2);
    
    // Instance tracking
    ~generators = Dictionary.new;
    ~masterEffects = nil;
    ~clockSynth = nil;
    
    // Groups
    ~clockGroup = nil;
    ~genGroup = nil;
    ~fxGroup = nil;
    
    "  ✓ Buses ready (% clock rates)".format(~clockRates.size).postln;
};
