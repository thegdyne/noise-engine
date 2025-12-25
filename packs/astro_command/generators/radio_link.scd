// Radio Link - Communication signals with SSB character and static
// Role: foreground (melodic)

SynthDef(\forge_astro_command_radio_link, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                             portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sigStr, stx, sql, sdr, dft;
    var carrier, sideband, static, squelchGate;
    var driftMod, signalLevel;

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

    // Custom params
    sigStr = In.kr(customBus0).linlin(0, 1, 0, 1);
    stx = In.kr(customBus1).linlin(0, 1, 0, 1);
    sql = In.kr(customBus2).linlin(0, 1, 0, 1);
    sdr = In.kr(customBus3).linlin(0, 1, 0, 1);
    dft = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Frequency drift
    driftMod = LFNoise1.kr(dft.linlin(0, 1, 0.1, 2)).range(
        1 - (dft * 0.03),
        1 + (dft * 0.03)
    );

    // Main carrier tone
    carrier = SinOsc.ar(freq * driftMod);

    // Sideband coloration - ring mod with nearby frequency
    sideband = carrier * SinOsc.ar(freq * driftMod * sdr.linlin(0, 1, 1.001, 1.01));
    carrier = carrier.blend(sideband, sdr * 0.5);

    // Add some harmonic content for radio character
    carrier = carrier + (SinOsc.ar(freq * driftMod * 2) * 0.1 * sdr);

    // Band-limit for radio character (300Hz - 3kHz feel)
    carrier = BPF.ar(carrier, 1500, 0.8);

    // Static / atmospheric noise
    static = BPF.ar(
        WhiteNoise.ar(1) + (Crackle.ar(1.8) * 0.3),
        LFNoise1.kr(0.5).range(800, 2500),
        0.5
    ) * stx;

    // Signal fading based on signal strength
    signalLevel = sigStr * LFNoise1.kr(0.3).range(0.7, 1);

    // Combine carrier and static inversely
    sig = (carrier * signalLevel) + (static * (1 - (signalLevel * 0.5)));

    // Squelch gate - gates out noise when signal is weak
    squelchGate = Lag.kr(signalLevel > sql, 0.05);
    sig = sig * squelchGate + (static * (1 - squelchGate) * 0.3);

    // Output chain
    sig = ~stereoSpread.(sig, 0.2, 0.15);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_radio_link loaded".postln;
