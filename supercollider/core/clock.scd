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
    
    "  [x] Clock SynthDef ready (% rates)".format(~clockRates.size).postln;
};

~setupClockBroadcast = {
    SynthDef(\clockTickBroadcast, { |clockTrigBus|
        var allTrigs = In.ar(clockTrigBus, 13);
        // Broadcast fabric indices 4-9 (covers /4..x8)
        [4, 5, 6, 7, 8, 9].do { |idx|
            var trigK = A2K.kr(Trig1.ar(allTrigs[idx], ControlDur.ir * 2));
            SendReply.kr(trigK, '/clock/tick', [idx]);
        };
    }).add;
    "  [x] ClockTickBroadcast SynthDef ready".postln;
};

~startClock = {
    ~clockGroup = Group.head(s);
    ~genGroup = Group.after(~clockGroup);
    ~stripGroup = Group.after(~genGroup);  // Channel strips after generators
    ~fxGroup = Group.after(~stripGroup);   // FX processors after strips
    ~mixerGroup = Group.after(~fxGroup);   // FX mixer sums dry + returns
    ~masterGroup = Group.after(~mixerGroup); // Master chain (EQ, comp, limiter)
    
    ~clockSynth = Synth(\masterClock, [
        \bpmBus, ~clockBus.index,
        \outBus, ~clockTrigBus.index
    ], ~clockGroup);
    
    ~clockBroadcastSynth = Synth(\clockTickBroadcast, [
        \clockTrigBus, ~clockTrigBus.index
    ], ~clockGroup);
    "  [x] Clock tick broadcast running".postln;

    "  [x] Clock running".postln;
    "  [x] Groups: clock -> gen -> strips -> fx".postln;
};
