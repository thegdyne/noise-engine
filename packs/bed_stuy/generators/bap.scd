// bap: Snare/clap texture - crisp hits
SynthDef(\forge_bed_stuy_bap, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var snap, body, wire, room, tight;

    // Theme params
    snap = In.kr(customBus0).linlin(0, 1, 0.2, 0.8);        // P1: Snap transient
    body = In.kr(customBus1).linlin(0, 1, 0.2, 0.7);        // P2: Body tone
    wire = In.kr(customBus2).linlin(0, 1, 0.1, 0.6);        // P3: Snare wire
    room = In.kr(customBus3).linlin(0, 1, 0.2, 0.6);        // P4: Room ambience
    tight = In.kr(customBus4).linlin(0, 1, 0.02, 0.15);     // P5: Decay tightness

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

    // DSP: Continuous room noise bed (always present)
    sig = LPF.ar(PinkNoise.ar(room * 0.5), 1000);

    // Snap transient - noise burst (boosted rate)
    sig = sig + (HPF.ar(Dust2.ar(8) * snap * 0.4, 800).lag(0.001, tight));

    // Body tone - tuned resonance
    sig = sig + (Ringz.ar(Dust.ar(8) * body, freq * [1, 1.5], tight * 2) * 0.5);

    // Snare wire - continuous filtered noise
    sig = sig + (BPF.ar(WhiteNoise.ar(wire * 0.4), 4000, 0.4));

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_bap loaded".postln;
