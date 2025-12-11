/*
Master Clock
Generates triggers at all musical rates
~clockRates is defined in buses.scd (SSOT)

Rate indices match CLOCK_RATES in Python config:
  0: /32, 1: /16, 2: /12, 3: /8, 4: /4, 5: /2, 6: CLK,
  7: x2, 8: x4, 9: x8, 10: x12, 11: x16, 12: x32
*/

~setupClock = {
    "Setting up clock...".postln;
    
    SynthDef(\masterClock, { |bpmBus, outBus|
        var bpm, baseRate, trigs;
        
        bpm = In.kr(bpmBus);
        baseRate = bpm / 60;  // Quarter note rate in Hz
        
        // Generate all rates from ~clockRates array
        trigs = ~clockRates.collect { |mult|
            Impulse.ar(baseRate * mult)
        };
        
        Out.ar(outBus, trigs);
    }).add;
    
    "  ✓ Clock SynthDef ready (% rates)".format(~clockRates.size).postln;
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
