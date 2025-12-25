// Data Stream - Telemetry tones with FSK-style modulation
// Role: bed (foundation)

SynthDef(\forge_astro_command_data_stream, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bps, mod, nos, tlm, crr;
    var dataRate, dataBits, carrier, fskMod, noise;
    var carrierDrift, markFreq, spaceFreq;

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
    bps = In.kr(customBus0).linlin(0, 1, 0, 1);
    mod = In.kr(customBus1).linlin(0, 1, 0, 1);
    nos = In.kr(customBus2).linlin(0, 1, 0, 1);
    tlm = In.kr(customBus3).linlin(0, 1, 0, 1);
    crr = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Data rate (bits per second equivalent)
    dataRate = bps.linexp(0, 1, 50, 2400);

    // Generate random data bits
    dataBits = LFPulse.ar(
        dataRate,
        0,
        LFNoise0.kr(dataRate * 0.5).range(0.3, 0.7)
    );

    // Carrier drift based on stability
    carrierDrift = LFNoise1.kr(
        (1 - crr).linlin(0, 1, 0.1, 5)
    ).range(
        1 - ((1 - crr) * 0.02),
        1 + ((1 - crr) * 0.02)
    );

    // FSK frequencies (mark and space)
    markFreq = freq * carrierDrift;
    spaceFreq = freq * carrierDrift * (1 + (mod * 0.2));

    // FSK carrier - frequency shifts with data
    fskMod = Select.ar(dataBits, [
        SinOsc.ar(markFreq),
        SinOsc.ar(spaceFreq)
    ]);

    // Telemetry character - add some structure/framing
    carrier = fskMod * (1 - (tlm * 0.3 * LFPulse.ar(dataRate / 8, 0, 0.1)));

    // Add sync pulses
    carrier = carrier + (
        SinOsc.ar(freq * 0.5) *
        LFPulse.ar(dataRate / 16, 0, 0.02) *
        tlm * 0.5
    );

    // Channel noise
    noise = BPF.ar(
        WhiteNoise.ar(1),
        freq,
        0.5
    ) * nos * 0.3;

    // Combine
    sig = carrier + noise;

    // Add some warmth
    sig = sig + (SinOsc.ar(freq * 0.5) * 0.1);

    // Output chain
    sig = ~stereoSpread.(sig, 0.15, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_data_stream loaded".postln;
