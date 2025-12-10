/*
Bus Setup
Creates all control and audio buses
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
    ~genParams = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genParams[slot] = Dictionary.new;
        ~genParams[slot][\frequency] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\cutoff] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\resonance] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\attack] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\decay] = Bus.control(s, 1).set(0.5);
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
