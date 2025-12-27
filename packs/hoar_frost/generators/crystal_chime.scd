// crystal_chime: Ice crystals tinkling - metallic Klank tones (continuous shimmer)
SynthDef(\forge_hoar_frost_crystal_chime, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var metallic, ringTime, spread, density, brightness;
    var trig, exciter;

    // Theme params
    metallic = In.kr(customBus0).linlin(0, 1, 1, 2.5);
    ringTime = In.kr(customBus1).linlin(0, 1, 0.5, 4);
    spread = In.kr(customBus2).linlin(0, 1, 0, 0.01);
    density = In.kr(customBus3).linlin(0, 1, 2, 15);
    brightness = In.kr(customBus4).linlin(0, 1, 0.3, 1.5);

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

    // DSP: Continuous chime excitation with Dust
    trig = Dust.ar(density);
    exciter = trig * 0.3;

    // Resonant bank tuned to metallic partials
    sig = DynKlank.ar(
        `[[1, 2.2, 3.5, 4.7, 6.1] * metallic.sqrt,
          [1, 0.5, 0.35, 0.25, 0.15] * brightness,
          [1, 0.8, 0.6, 0.4, 0.3] * ringTime],
        exciter,
        freq
    );

    // Stereo spread
    sig = [
        DynKlank.ar(
            `[[1, 2.2, 3.5, 4.7, 6.1] * metallic.sqrt,
              [1, 0.5, 0.35, 0.25, 0.15] * brightness,
              [1, 0.8, 0.6, 0.4, 0.3] * ringTime],
            Dust.ar(density) * 0.3,
            freq
        ),
        DynKlank.ar(
            `[[1, 2.2, 3.5, 4.7, 6.1] * metallic.sqrt * 1.003,
              [1, 0.5, 0.35, 0.25, 0.15] * brightness,
              [1, 0.8, 0.6, 0.4, 0.3] * ringTime],
            Dust.ar(density) * 0.3,
            freq * (1 + spread)
        )
    ];

    sig = sig * 0.25;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_crystal_chime loaded".postln;
