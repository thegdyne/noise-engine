// osc: Classic analog oscillator with drift
SynthDef(\forge_mod_caf_osc, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var drift, shape, thick, warmth, sub;
    var driftMod;

    // Theme params
    drift = In.kr(customBus0).linlin(0, 1, 0.001, 0.02);    // P1: Pitch drift
    shape = In.kr(customBus1).linlin(0, 1, 0.1, 0.9);       // P2: Pulse width
    thick = In.kr(customBus2).linlin(0, 1, 0, 0.015);       // P3: Detuning
    warmth = In.kr(customBus3).linlin(0, 1, 1, 3);          // P4: Saturation
    sub = In.kr(customBus4).linlin(0, 1, 0, 0.5);           // P5: Sub oscillator

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // DSP: Analog drift
    driftMod = LFNoise1.kr(0.3).range(1 - drift, 1 + drift);

    // Main oscillators with drift and thickness
    sig = Saw.ar(freq * driftMod * [1, 1 + thick]) * 0.3;
    sig = sig + (Pulse.ar(freq * driftMod * [1.001, 1 - thick], shape) * 0.25);

    // Warmth saturation
    sig = (sig * warmth).tanh;

    // Sub oscillator
    sig = sig + (SinOsc.ar(freq * 0.5 * driftMod) * sub * 0.4);

    sig = Splay.ar(sig, 0.6) * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_osc loaded".postln;
