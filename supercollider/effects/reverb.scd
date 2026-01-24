/*
Reverb - Clean Plate/Room
Spatial ambience separate from Tape Echo character

Signal flow:
  verbSendBus -> HPF (80Hz) -> FreeVerb -> LPF (tone) -> verbReturnBus
*/

~setupReverb = {
    "Setting up Reverb...".postln;
    
    // State defaults
    ~verbSize = 0.75;     // 0-1 room size (75%)
    ~verbDecay = 0.65;    // 0-1 decay time (65%)
    ~verbTone = 0.7;      // 0-1 brightness
    
    SynthDef(\reverb, { |inBus, outBus, size=0.75, decay=0.65, tone=0.7,
                         sizeBus=(-1), decayBus=(-1), toneBus=(-1)|
        var sig, verb, toneFreq;
        var sizeEff, decayEff, toneEff;

        // Bus unification: read from bus if valid index, otherwise use direct arg
        sizeEff = Select.kr(sizeBus >= 0, [size, In.kr(sizeBus)]);
        decayEff = Select.kr(decayBus >= 0, [decay, In.kr(decayBus)]);
        toneEff = Select.kr(toneBus >= 0, [tone, In.kr(toneBus)]);

        // Smooth params
        sizeEff = Lag.kr(sizeEff, 0.05);
        decayEff = Lag.kr(decayEff, 0.05);
        toneEff = Lag.kr(toneEff, 0.02);

        // Map tone 0-1 to LPF freq (2000-12000Hz)
        toneFreq = toneEff.linexp(0, 1, 2000, 12000);
        
        // Read from send bus
        sig = In.ar(inBus, 2);
        
        // HPF to prevent low-end wash
        sig = HPF.ar(sig, 80);
        
        // FreeVerb (mix=1 for 100% wet on send bus)
        verb = FreeVerb2.ar(sig[0], sig[1],
            mix: 1,             // 100% wet
            room: sizeEff,      // Room size
            damp: 1 - decayEff  // Damping (inverted: low decay = high damp)
        );
        
        // Tone control (darken tails)
        verb = LPF.ar(verb, toneFreq);
        
        // Output 100% wet
        Out.ar(outBus, verb);
    }).add;
    
    "  [x] Reverb SynthDef ready".postln;
};

~startReverb = {
    // Get bus indices from bus unification (if available)
    var sizeBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_verb_size) ? -1 }, { -1 });
    var decayBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_verb_decay) ? -1 }, { -1 });
    var toneBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_verb_tone) ? -1 }, { -1 });

    ~verbSynth = Synth(\reverb, [
        \inBus, ~verbSendBus,
        \outBus, ~verbReturnBus,
        \size, ~verbSize,
        \decay, ~verbDecay,
        \tone, ~verbTone,
        \sizeBus, sizeBusIdx,
        \decayBus, decayBusIdx,
        \toneBus, toneBusIdx
    ], ~fxGroup, \addToTail);

    "  [x] Reverb running".postln;
};

~setupReverbOSC = {
    OSCdef(\verbSize, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~verbSize = val;
        if(~verbSynth.notNil) {
            ~verbSynth.set(\size, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_verb_size, val);
        };
    }, '/noise/master/verb/size');

    OSCdef(\verbDecay, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~verbDecay = val;
        if(~verbSynth.notNil) {
            ~verbSynth.set(\decay, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_verb_decay, val);
        };
    }, '/noise/master/verb/decay');

    OSCdef(\verbTone, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~verbTone = val;
        if(~verbSynth.notNil) {
            ~verbSynth.set(\tone, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_verb_tone, val);
        };
    }, '/noise/master/verb/tone');

    "  [x] Reverb OSC handlers ready".postln;
};
