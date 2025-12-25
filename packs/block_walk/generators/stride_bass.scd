SynthDef(\forge_block_walk_stride_bass, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var glide, thick, grit, bounce, warmth;
    var sub, saw1, saw2, saw3, detune, pitchEnv, envTrig;

    // Standard bus reads
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

    // Theme params
    glide = In.kr(customBus0);      // GLI - legato smoothness
    thick = In.kr(customBus1);      // THK - detune spread
    grit = In.kr(customBus2);       // GRT - saturation
    bounce = In.kr(customBus3);     // BNC - pitch envelope
    warmth = In.kr(customBus4);     // WRM - sub blend

    // Additional glide smoothing layered on portamento
    freq = Lag.kr(freq, glide.linexp(0, 1, 0.001, 0.15));

    // Pitch envelope for bounce/walking feel
    envTrig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    pitchEnv = EnvGen.ar(Env.perc(0.001, 0.08), envTrig) * bounce.linlin(0, 1, 0, 0.15);

    // Oscillators with thickness-controlled detune
    detune = thick.linexp(0, 1, 1.001, 1.02);
    saw1 = Saw.ar(freq * (1 + pitchEnv));
    saw2 = Saw.ar(freq * detune * (1 + pitchEnv));
    saw3 = Saw.ar(freq / detune * (1 + pitchEnv));

    // Sub oscillator for warmth
    sub = SinOsc.ar(freq * 0.5) * warmth.linlin(0, 1, 0.2, 0.7);

    // Mix saws
    sig = (saw1 + (saw2 * 0.7) + (saw3 * 0.7)) * 0.4;

    // Warm saturation/grit
    sig = (sig + sub).tanh;
    sig = sig + (sig.clip2(0.3) * grit.linlin(0, 1, 0, 2));
    sig = LeakDC.ar(sig);

    // Output chain
    sig = ~stereoSpread.(sig, 0.2, thick.linlin(0, 1, 0.1, 0.4));
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_block_walk_stride_bass loaded".postln;
