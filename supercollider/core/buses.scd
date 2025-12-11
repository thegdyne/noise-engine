/*
Bus Setup
Creates all control and audio buses

Default values are real values (not normalized):
  - frequency: 6.3 Hz (midpoint of 0.5-80 exp)
  - cutoff: 1131 Hz (midpoint of 80-16000 exp)
  - resonance: 0.55 (midpoint of 0.1-1.0 lin, inverted)
  - attack: 0.022 s (midpoint of 0.001-0.5 exp)
  - decay: 0.14 s (midpoint of 0.01-2.0 exp)
*/

~setupBuses = {
    "Setting up buses...".postln;
    
    // Global parameters
    ~params = Dictionary.new;
    ~params[\gravity] = Bus.control(s, 1).set(0.5);
    ~params[\density] = Bus.control(s, 1).set(0.5);
    ~params[\filter_cutoff] = Bus.control(s, 1).set(0.7);
    ~params[\amplitude] = Bus.control(s, 1).set(0.5);
    
    // Master clock
    ~clockBus = Bus.control(s, 1).set(120);
    ~clockTrigBus = Bus.audio(s, 8);  // 8 channels for 8 rates
    
    // Per-generator parameters (8 slots)
    // Default values are real values matching Python config midpoints
    ~genParams = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genParams[slot] = Dictionary.new;
        ~genParams[slot][\frequency] = Bus.control(s, 1).set(6.3);      // Hz
        ~genParams[slot][\cutoff] = Bus.control(s, 1).set(1131);        // Hz
        ~genParams[slot][\resonance] = Bus.control(s, 1).set(0.55);     // rq
        ~genParams[slot][\attack] = Bus.control(s, 1).set(0.022);       // s
        ~genParams[slot][\decay] = Bus.control(s, 1).set(0.14);         // s
        ~genParams[slot][\filterType] = Bus.control(s, 1).set(0);
        ~genParams[slot][\envEnabled] = Bus.control(s, 1).set(0);
        ~genParams[slot][\clockRate] = Bus.control(s, 1).set(3);  // 3 = CLK (quarter notes)
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
    
    "  ✓ Buses ready".postln;
};
