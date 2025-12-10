/*
Master Clock
Generates BPM-synced triggers
*/

~setupClock = {
    "Setting up clock...".postln;
    
    SynthDef(\masterClock, { |bpmBus, outBus|
        var bpm, freq, trig;
        bpm = In.kr(bpmBus);
        freq = bpm / 60;
        trig = Impulse.ar(freq);
        Out.ar(outBus, trig);
    }).add;
    
    "  ✓ Clock SynthDef ready".postln;
};

~startClock = {
    // Create groups in correct order within default group
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
