// STRIATE -- Muscle striations
// Rhythmic banded patterns -- the repeating structure of muscle tissue

SynthDef(\forge_nerve_glow_striate, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var band, rhythm, sweep, tension, gap;
    var noise, bands, bandFreq, gatePattern, sweepMod;

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
    band = In.kr(customBus0).linexp(0, 1, 0.02, 0.3);      // Band Q (width)
    rhythm = In.kr(customBus1).linexp(0, 1, 2, 20);        // Pattern rate
    sweep = In.kr(customBus2).linlin(0, 1, 0.0, 0.5);     // Freq modulation
    tension = In.kr(customBus3).linexp(0, 1, 0.5, 10);    // Resonance
    gap = In.kr(customBus4).linlin(0, 1, 0.1, 0.9);       // Duty cycle

    // Rhythmic gate pattern
    gatePattern = LFPulse.kr(rhythm, 0, gap);

    // Sweep modulation
    sweepMod = SinOsc.kr(rhythm * 0.25, 0, sweep, 1);

    // Noise source with banding
    noise = PinkNoise.ar(1) + (WhiteNoise.ar(0.3));

    // Multiple resonant bands at harmonic intervals
    bands = Mix.fill(6, { |i|
        var bFreq = freq * (i + 1) * sweepMod;
        var bAmp = (0.7 ** i);
        RLPF.ar(noise, bFreq.clip(20, 16000), band) * bAmp * tension.sqrt
    });

    sig = bands * 0.2;

    // Apply rhythmic gating
    sig = sig * Lag.kr(gatePattern, 0.005);

    // Add transient click at band start
    sig = sig + (Impulse.ar(rhythm) * WhiteNoise.ar(0.05) * (1 - gap));

    // Stereo variation
    sig = [
        sig * (1 + (SinOsc.kr(rhythm * 0.1, 0, 0.1))),
        sig * (1 + (SinOsc.kr(rhythm * 0.1, pi, 0.1)))
    ];

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_nerve_glow_striate loaded".postln;
