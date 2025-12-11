/*
Master Clock
Generates triggers at all musical rates
Rates output on 12-channel bus:
  0: /32 (8 bars)
  1: /16 (4 bars)
  2: /12 (3 bars)
  3: /8  (2 bars)
  4: /4  (whole notes)
  5: /2  (half notes)
  6: CLK (quarter notes)
  7: x2  (8th notes)
  8: x4  (16th notes)
  9: x12 (triplet 16ths)
  10: x16 (64th notes)
  11: x32 (128th notes)
*/

// Multipliers relative to quarter note (slowest to fastest)
~clockRates = [1/32, 1/16, 1/12, 1/8, 1/4, 1/2, 1, 2, 4, 12, 16, 32];

~setupClock = {
    "Setting up clock...".postln;
    
    SynthDef(\masterClock, { |bpmBus, outBus|
        var bpm, baseRate, trigs;
        
        bpm = In.kr(bpmBus);
        baseRate = bpm / 60;  // Quarter note rate in Hz
        
        // Generate all 12 rates
        trigs = ~clockRates.collect { |mult|
            Impulse.ar(baseRate * mult)
        };
        
        Out.ar(outBus, trigs);
    }).add;
    
    "  ✓ Clock SynthDef ready (12 rates)".postln;
};

~startClock = {
    ~clockGroup = Group.head(s);
    ~genGroup = Group.after(~clockGroup);
    ~fxGroup = Group.after(~genGroup);
    
    ~clockSynth = Synth(\masterClock, [
        \bpmBus, ~clockBus.index,
        \outBus, ~clockTrigBus.index
    ], ~clockGroup);
    
    "  ✓ Clock running".postln;
    "  ✓ Groups: clock -> gen -> fx".postln;
};
