/*
Master Clock
Generates triggers at all musical rates
Rates output on 8-channel bus:
  0: x8  (32nd notes)
  1: x4  (16th notes)
  2: x2  (8th notes)
  3: CLK (quarter notes)
  4: /2  (half notes)
  5: /4  (whole notes)
  6: /8  (2 bars)
  7: /16 (4 bars)
*/

~clockRates = [8, 4, 2, 1, 0.5, 0.25, 0.125, 0.0625];

~setupClock = {
    "Setting up clock...".postln;
    
    SynthDef(\masterClock, { |bpmBus, outBus|
        var bpm, baseRate, trigs;
        
        bpm = In.kr(bpmBus);
        baseRate = bpm / 60;  // Quarter note rate in Hz
        
        // Generate all 8 rates
        trigs = ~clockRates.collect { |mult|
            Impulse.ar(baseRate * mult)
        };
        
        Out.ar(outBus, trigs);
    }).add;
    
    "  ✓ Clock SynthDef ready (8 rates)".postln;
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
