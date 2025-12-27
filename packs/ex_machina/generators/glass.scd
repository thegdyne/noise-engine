// glass: Facility glass walls - cold, clinical
SynthDef(\forge_ex_machina_glass, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pane, cold, touch, hum, sterile;

    // Theme params
    pane = In.kr(customBus0).linlin(0, 1, 0.2, 0.8);        // P1: Glass pane resonance
    cold = In.kr(customBus1).linlin(0, 1, 3000, 10000);     // P2: Cold brightness
    touch = In.kr(customBus2).linlin(0, 1, 1, 8);           // P3: Touch/tap rate
    hum = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);         // P4: Facility hum
    sterile = In.kr(customBus4).linlin(0, 1, 0.1, 0.4);     // P5: Sterile air

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

    // DSP: Glass resonance - high pitched ring
    sig = Ringz.ar(Dust.ar(touch) * 0.2, freq * [6, 8, 12], 0.3) * pane;
    sig = Splay.ar(sig, 0.6);

    // Cold brightness - continuous shimmer
    sig = sig + (BPF.ar(WhiteNoise.ar(pane * 0.25), cold, 0.1));

    // Facility hum - electrical
    sig = sig + (SinOsc.ar(60 * [1, 2, 3]) * hum * [0.3, 0.15, 0.08]).sum;

    // Sterile air - filtered noise
    sig = sig + (HPF.ar(PinkNoise.ar(sterile * 0.3), 2000));

    // Glass body tone
    sig = sig + (SinOsc.ar(freq * [1, 2.01]) * pane * 0.15);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_glass loaded".postln;
