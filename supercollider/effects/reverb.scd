/*
Reverb - Clean Plate/Room
Spatial ambience separate from Tape Echo character

Signal flow:
  verbSendBus → HPF (80Hz) → FreeVerb → LPF (tone) → verbReturnBus
*/

~setupReverb = {
    "Setting up Reverb...".postln;
    
    // State defaults
    ~verbSize = 0.5;      // 0-1 room size
    ~verbDecay = 0.5;     // 0-1 decay time
    ~verbTone = 0.7;      // 0-1 brightness
    
    SynthDef(\reverb, { |inBus, outBus, size=0.5, decay=0.5, tone=0.7|
        var sig, verb, toneFreq;
        
        // Smooth params
        size = Lag.kr(size, 0.05);
        decay = Lag.kr(decay, 0.05);
        tone = Lag.kr(tone, 0.02);
        
        // Map tone 0-1 to LPF freq (2000-12000Hz)
        toneFreq = tone.linexp(0, 1, 2000, 12000);
        
        // Read from send bus
        sig = In.ar(inBus, 2);
        
        // HPF to prevent low-end wash
        sig = HPF.ar(sig, 80);
        
        // FreeVerb (mix=1 for 100% wet on send bus)
        verb = FreeVerb2.ar(sig[0], sig[1], 
            mix: 1,           // 100% wet
            room: size,       // Room size
            damp: 1 - decay   // Damping (inverted: low decay = high damp)
        );
        
        // Tone control (darken tails)
        verb = LPF.ar(verb, toneFreq);
        
        // Output 100% wet
        Out.ar(outBus, verb);
    }).add;
    
    "  ✓ Reverb SynthDef ready".postln;
};

~startReverb = {
    ~verbSynth = Synth(\reverb, [
        \inBus, ~verbSendBus,
        \outBus, ~verbReturnBus,
        \size, ~verbSize,
        \decay, ~verbDecay,
        \tone, ~verbTone
    ], ~fxGroup, \addToTail);
    
    "  ✓ Reverb running".postln;
};

~setupReverbOSC = {
    OSCdef(\verbSize, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~verbSize = val;
        if(~verbSynth.notNil) {
            ~verbSynth.set(\size, val);
        };
    }, '/noise/master/verb/size');
    
    OSCdef(\verbDecay, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~verbDecay = val;
        if(~verbSynth.notNil) {
            ~verbSynth.set(\decay, val);
        };
    }, '/noise/master/verb/decay');
    
    OSCdef(\verbTone, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~verbTone = val;
        if(~verbSynth.notNil) {
            ~verbSynth.set(\tone, val);
        };
    }, '/noise/master/verb/tone');
    
    "  ✓ Reverb OSC handlers ready".postln;
};
