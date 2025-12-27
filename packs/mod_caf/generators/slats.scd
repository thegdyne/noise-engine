// slats: Wood slat architecture resonance
SynthDef(\forge_mod_caf_slats, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var body, spacing, tap, warmth, room;

    // Theme params
    body = In.kr(customBus0).linlin(0, 1, 0.4, 1);          // P1: Wood body resonance
    spacing = In.kr(customBus1).linlin(0, 1, 0.008, 0.04);  // P2: Slat spacing (comb)
    tap = In.kr(customBus2).linlin(0, 1, 2, 12);            // P3: Tap excitation rate
    warmth = In.kr(customBus3).linlin(0, 1, 600, 4000);     // P4: Warmth filter
    room = In.kr(customBus4).linlin(0, 1, 0.2, 0.6);        // P5: Room reflection

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

    // DSP: Wood body - continuous filtered tone
    sig = LPF.ar(Saw.ar(freq * [0.5, 1, 1.002]) * body, warmth) * 0.4;
    sig = Splay.ar(sig, 0.5);

    // Continuous room noise bed
    sig = sig + (LPF.ar(PinkNoise.ar(room * 0.5), 800));

    // Comb resonance - slat spacing
    sig = sig + CombL.ar(sig * 0.4, 0.1, spacing, 0.8);

    // Tap excitation - wood knocks (boosted)
    sig = sig + (Ringz.ar(Dust.ar(tap) * 0.25, freq * [1, 2, 3.5], 0.1) * 0.5);

    sig = sig * 0.5;

    // Output chain (with Limiter for comb)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_slats loaded".postln;
