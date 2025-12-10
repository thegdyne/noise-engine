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
    ~clockSynth = Synth(\masterClock, [
        \bpmBus, ~clockBus.index,
        \outBus, ~clockTrigBus.index
    ], addAction: \addToHead);
    
    "  ✓ Clock running".postln;
};
