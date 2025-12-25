// Dew Ripple - Disturbed water surface pulsing outward
// Modulated oscillators with feedback creating wave patterns

SynthDef(\forge_dew_sphere_dew_ripple, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wave, depth, damp, center, echo;
    var rippleMod, waveOsc, centerFreq;
    var feedback, dampedSig;

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
    wave = In.kr(customBus0);       // Wave intensity
    depth = In.kr(customBus1);      // Modulation depth
    damp = In.kr(customBus2);       // Damping
    center = In.kr(customBus3);     // Center frequency
    echo = In.kr(customBus4);       // Self-reflection

    // Center frequency shifted by param
    centerFreq = freq * center.linexp(0, 1, 0.5, 2);

    // Ripple modulation - concentric waves spreading out
    rippleMod = SinOsc.ar(wave.linexp(0, 1, 0.5, 8)) * depth;

    // Main wave oscillator with ripple modulation
    waveOsc = SinOsc.ar(centerFreq * (1 + (rippleMod * 0.1)));

    // Add harmonics spreading like wave interference
    waveOsc = waveOsc + (SinOsc.ar(centerFreq * 2 * (1 + (rippleMod * 0.05))) * 0.3 * wave);
    waveOsc = waveOsc + (SinOsc.ar(centerFreq * 0.5 * (1 - (rippleMod * 0.05))) * 0.4);

    // Amplitude ripple - pulsing intensity
    waveOsc = waveOsc * (1 + (SinOsc.ar(wave.linexp(0, 1, 1, 12)) * depth * 0.3));

    // Feedback path - echo/self-reflection
    feedback = LocalIn.ar(2);
    sig = waveOsc + (feedback[0] * echo * 0.4);

    // Damping - higher = less decay
    dampedSig = LPF.ar(sig, damp.linexp(0, 1, 1000, 8000));
    dampedSig = dampedSig * damp.linlin(0, 1, 0.95, 0.7);

    // Send to feedback with delay (ripple travel time)
    LocalOut.ar(DelayL.ar(dampedSig!2, 0.2, wave.linexp(0, 1, 0.02, 0.15)));

    // Stereo spread based on wave
    sig = [
        sig + (SinOsc.ar(centerFreq * 1.003) * wave * 0.2),
        sig + (SinOsc.ar(centerFreq * 0.997) * wave * 0.2)
    ];

    // Center bandpass focus
    sig = BPF.ar(sig, centerFreq, center.linexp(0, 1, 0.5, 0.1)) * 2;
    sig = sig + (LPF.ar(waveOsc, 500) * (1 - center) * 0.3);

    // Normalize
    sig = sig * 0.5;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_dew_ripple loaded".postln;
