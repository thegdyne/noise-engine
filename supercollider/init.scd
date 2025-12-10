/*
Noise Engine - SuperCollider Initialization
Standard generator interface with per-slot parameters
*/

s.waitForBoot({
    
    "=== Noise Engine - SuperCollider ===".postln;
    "Initializing...".postln;
    
    // Global parameters (for modulation panel)
    ~params = Dictionary.new;
    ~params[\gravity] = Bus.control(s, 1).set(0.5);
    ~params[\density] = Bus.control(s, 1).set(0.5);
    ~params[\filter_cutoff] = Bus.control(s, 1).set(0.7);
    ~params[\amplitude] = Bus.control(s, 1).set(0.5);
    
    // Per-generator parameters (8 slots)
    // Standard interface: every generator gets these buses
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
    };
    
    // Audio buses
    ~masterBus = Bus.audio(s, 2);
    
    // Generator instances
    ~generators = Dictionary.new;
    ~masterEffects = nil;
    
    /*
    ============================================
    STANDARD GENERATOR INTERFACE
    All generators receive these arguments:
      - out: audio output bus
      - freqBus: frequency/pitch (0-1)
      - cutoffBus: filter cutoff (0-1)
      - resBus: filter resonance (0-1)
      - attackBus: VCA attack time (0-1)
      - decayBus: VCA decay time (0-1)
      - filterTypeBus: 0=LP, 1=HP, 2=BP
    
    Generators can interpret these as appropriate
    for their sound design.
    ============================================
    */
    
    // Helper function to start any generator with standard params
    ~startGenerator = { |slotID, genType|
        var params = ~genParams[slotID];
        
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
        });
        
        ~generators[slotID] = Synth(genType, [
            \out, ~masterBus,
            \freqBus, params[\frequency].index,
            \cutoffBus, params[\cutoff].index,
            \resBus, params[\resonance].index,
            \attackBus, params[\attack].index,
            \decayBus, params[\decay].index,
            \filterTypeBus, params[\filterType].index
        ], addAction: \addToHead);
        
        "Started % in slot %".format(genType, slotID).postln;
    };
    
    // Test Synth - simple pulse + noise with filter
    SynthDef(\testSynth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus, filterTypeBus|
        var sig, freq, filterFreq, rq, filterType, attack, decay, amp, env;
        
        // Read standard params
        freq = In.kr(freqBus).linexp(0, 1, 50, 2000);
        filterFreq = In.kr(cutoffBus).linexp(0, 1, 100, 10000);
        rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
        attack = In.kr(attackBus).linexp(0, 1, 0.001, 1);
        decay = In.kr(decayBus).linexp(0, 1, 0.001, 4);
        filterType = In.kr(filterTypeBus);
        amp = In.kr(~params[\amplitude]);
        
        // Sound source
        sig = Pulse.ar(freq, 0.5, 0.5) + PinkNoise.ar(0.3);
        
        // Multi-mode filter
        sig = Select.ar(filterType, [
            RLPF.ar(sig, filterFreq, rq),
            RHPF.ar(sig, filterFreq, rq),
            BPF.ar(sig, filterFreq, rq)
        ]);
        
        // VCA always open (CLK off = drone)
        sig = sig * amp * 0.3;
        
        Out.ar(out, sig ! 2);
    }).add;
    
    // PT2399 Grainy - granular with tape degradation
    SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus, filterTypeBus|
        var sig, grain, env, trig, rate, freq, crush, flutter;
        var filterFreq, rq, filterType, attack, decay, amp;
        var panPos;
        
        // Read standard params
        freq = In.kr(freqBus).linexp(0, 1, 0.25, 4);
        filterFreq = In.kr(cutoffBus).linexp(0, 1, 200, 8000);
        rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
        attack = In.kr(attackBus).linexp(0, 1, 0.001, 0.5);
        decay = In.kr(decayBus).linexp(0, 1, 0.01, 2);
        filterType = In.kr(filterTypeBus);
        
        // Global params
        amp = In.kr(~params[\amplitude]);
        rate = In.kr(~params[\density]).linexp(0, 1, 0.5, 60);
        
        // Grain trigger
        trig = Impulse.kr(rate);
        
        // Pitch with flutter
        flutter = LFNoise1.kr(3).range(0.95, 1.05);
        freq = freq * flutter;
        
        // Grain envelope using attack/decay
        env = EnvGen.kr(Env.perc(attack, decay), trig);
        
        // Noise source
        grain = PinkNoise.ar(0.5);
        
        // Bit crushing based on frequency param
        crush = freq.linlin(0.25, 4, 4, 12);
        grain = grain.round(2.pow(crush).reciprocal * 2) - 1;
        
        sig = grain * env;
        
        // Multi-mode filter
        sig = Select.ar(filterType, [
            RLPF.ar(sig, filterFreq, rq),
            RHPF.ar(sig, filterFreq, rq),
            BPF.ar(sig, filterFreq, rq)
        ]);
        
        // Soft clip
        sig = (sig * 2).tanh * 0.5;
        
        // Random pan per grain
        panPos = TRand.kr(-1.0, 1.0, trig);
        sig = Pan2.ar(sig, panPos);
        
        sig = sig * amp * 0.4;
        
        Out.ar(out, sig);
    }).add;
    
    // Master passthrough
    SynthDef(\masterPassthrough, { |inBus, outBus=0, fidelityAmount=1.0|
        var sig;
        
        sig = In.ar(inBus, 2);
        
        sig = sig.round(2.pow(fidelityAmount.linexp(0, 1, 4, 16)).reciprocal * 2) - 1;
        sig = Latch.ar(sig, Impulse.ar(fidelityAmount.linexp(0, 1, 4000, 44100)));
        sig = LPF.ar(sig, fidelityAmount.linexp(0, 1, 2000, 18000));
        
        Out.ar(outBus, sig);
    }).add;
    
    // ========== OSC HANDLERS ==========
    
    // Global parameters
    OSCdef(\gravity, { |msg| ~params[\gravity].set(msg[1]); }, '/noise/gravity');
    OSCdef(\density, { |msg| ~params[\density].set(msg[1]); }, '/noise/density');
    OSCdef(\filterCutoff, { |msg| ~params[\filter_cutoff].set(msg[1]); }, '/noise/filter_cutoff');
    OSCdef(\amplitude, { |msg| ~params[\amplitude].set(msg[1]); }, '/noise/amplitude');
    OSCdef(\fidelityAmount, { |msg|
        if(~masterEffects.notNil, { ~masterEffects.set(\fidelityAmount, msg[1]); });
    }, '/noise/fidelity_amount');
    
    // Per-generator parameters (all use same handler pattern)
    OSCdef(\genFrequency, { |msg|
        ~genParams[msg[1].asInteger][\frequency].set(msg[2].asFloat);
    }, '/noise/gen/frequency');
    
    OSCdef(\genCutoff, { |msg|
        ~genParams[msg[1].asInteger][\cutoff].set(msg[2].asFloat);
    }, '/noise/gen/cutoff');
    
    OSCdef(\genResonance, { |msg|
        ~genParams[msg[1].asInteger][\resonance].set(msg[2].asFloat);
    }, '/noise/gen/resonance');
    
    OSCdef(\genAttack, { |msg|
        ~genParams[msg[1].asInteger][\attack].set(msg[2].asFloat);
    }, '/noise/gen/attack');
    
    OSCdef(\genDecay, { |msg|
        ~genParams[msg[1].asInteger][\decay].set(msg[2].asFloat);
    }, '/noise/gen/decay');
    
    OSCdef(\genFilterType, { |msg|
        ~genParams[msg[1].asInteger][\filterType].set(msg[2].asInteger);
    }, '/noise/gen/filterType');
    
    // Generator start/stop
    OSCdef(\startGenerator, { |msg|
        ~startGenerator.(msg[1].asInteger, msg[2].asSymbol);
    }, '/noise/start_generator');
    
    OSCdef(\stopGenerator, { |msg|
        var slotID = msg[1].asInteger;
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
            "Stopped generator in slot %".format(slotID).postln;
        });
    }, '/noise/stop_generator');
    
    s.sync;
    
    ~masterEffects = Synth(\masterPassthrough, [
        \inBus, ~masterBus,
        \outBus, 0,
        \fidelityAmount, 1.0
    ], addAction: \addToTail);
    
    "".postln;
    "✓ Noise Engine ready!".postln;
    "✓ Master passthrough active".postln;
    "✓ 8 generator slots with standard interface".postln;
    "".postln;
    "Standard params: FRQ, CUT, RES, ATK, DEC, FilterType".postln;
    "Listening for OSC on port 57120".postln;
});
