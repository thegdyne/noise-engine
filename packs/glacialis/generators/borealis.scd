// BOREALIS - Aurora sweep and shimmer
// AM chorus with phase spread for curtain-like motion

SynthDef(\forge_glacialis_borealis, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wave, sweep, curtain, glow, phase;
    var voices, sweepLFO, carrier, am, voiceSig;

    // Theme params
    wave = In.kr(customBus0);      // Waveform
    sweep = In.kr(customBus1);     // Sweep rate
    curtain = In.kr(customBus2);   // Voice layers
    glow = In.kr(customBus3);      // Saturation
    phase = In.kr(customBus4);     // Phase spread

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

    // Main sweep LFO
    sweepLFO = SinOsc.kr(sweep.linexp(0, 1, 0.03, 0.5));

    // Multiple voice layers with phase offset - 6 voices with crossfade
    voices = Mix.fill(6, { |i|
        var voicePhase, detune, amRate, voiceAmp, osc;

        // Voice amplitude based on curtain parameter
        voiceAmp = (curtain * 6 - i).clip(0, 1) * (6 - i).reciprocal;

        // Phase offset per voice
        voicePhase = i * phase * pi / 3;

        // Slight detune per voice
        detune = 1 + (i * 0.003 * phase);

        // AM rate varies per voice
        amRate = sweep.linexp(0, 1, 0.5, 4) * (1 + (i * 0.2));

        // Carrier oscillator - blend between sine and triangle based on wave
        osc = (SinOsc.ar(freq * detune, voicePhase) * (1 - wave)) +
              (LFTri.ar(freq * detune, voicePhase / (2pi)) * wave);

        // AM modulation
        am = SinOsc.kr(amRate, i * 0.5).range(0.3, 1);

        osc * am * voiceAmp
    });

    sig = voices * 0.4;

    // Soft saturation for glow
    sig = (sig * (1 + glow)).tanh * (1 + glow).reciprocal;

    // Sweep filter modulation
    sig = RLPF.ar(sig,
        sweepLFO.range(freq * 2, freq * 8).clip(100, 16000),
        0.5
    );

    // Stereo phase spread
    sig = [
        sig + (DelayC.ar(sig, 0.05, phase.linlin(0, 1, 0.003, 0.02)) * 0.3),
        sig + (DelayC.ar(sig, 0.05, phase.linlin(0, 1, 0.005, 0.025)) * 0.3)
    ];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_glacialis_borealis loaded".postln;
