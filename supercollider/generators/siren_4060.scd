// 4060 Siren - Counter + mux wailing siren
SynthDef(\siren4060, {
    |out=0, amp=0.5, gate=1,
    freq=440, filterType=0, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    osc_resistance=0.5, resistor_pattern=4, tone_cap=0.5, counter_bits=5, drive_level=0.7|
    
    var sig, env, baseFreq, stepFreq, pattern, counter;
    
    // Base oscillator frequency
    baseFreq = freq * osc_resistance.linexp(0, 1, 0.5, 2);
    
    // Counter stepping through pattern (simulates 4060 + mux)
    counter = LFSaw.kr(tone_cap.linexp(0, 1, 0.2, 5)).range(0, counter_bits.linlin(0, 1, 2, 8).round);
    
    // Stepped frequency pattern (resistor chain selection)
    pattern = Select.kr(counter.floor % 8, [
        1.0, 1.2, 0.9, 1.5, 0.8, 1.3, 1.1, 0.7
    ] * (resistor_pattern.linlin(0, 7, 0.5, 2)));
    
    // Siren tone with stepped pitch
    stepFreq = baseFreq * pattern;
    sig = Pulse.ar(stepFreq, 0.5);
    
    // Add harmonics for that cheap speaker sound
    sig = sig + (Pulse.ar(stepFreq * 2, 0.3) * 0.3);
    
    // Drive/saturation
    sig = (sig * drive_level.linexp(0, 1, 1, 4)).tanh;
    
    // Filter
    sig = ~multiFilter.(sig, filterType, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
