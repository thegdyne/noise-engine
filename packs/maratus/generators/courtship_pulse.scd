// Courtship Pulse - Throbbing rhythmic motion of the mating display
// PWM-based pulsing with amplitude and filter modulation

SynthDef(\forge_maratus_courtship_pulse, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pulse, urgency, display, heartbeat, fervor;
    var pulseRate, pwmLFO, ampLFO, filterLFO, pw, subOsc;

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

    // Theme params
    pulse = In.kr(customBus0);  // PWM depth
    urgency = In.kr(customBus1);  // Pulse rate
    display = In.kr(customBus2);  // Filter sweep
    heartbeat = In.kr(customBus3);  // Low freq emphasis
    fervor = In.kr(customBus4);  // Intensity

    // Pulse rate from urgency
    pulseRate = urgency.linexp(0, 1, 1, 12);

    // PWM LFO
    pwmLFO = SinOsc.kr(pulseRate) * pulse * 0.4;
    pw = 0.5 + pwmLFO;

    // Amplitude tremolo LFO (slightly different rate for complexity)
    ampLFO = SinOsc.kr(pulseRate * 1.01).range(1 - (fervor * 0.5), 1);

    // Filter sweep LFO
    filterLFO = SinOsc.kr(pulseRate * 0.99).range(0, display);

// Main pulse oscillator
    sig = Pulse.ar(freq, pw.clip(0.1, 0.9)) * 0.7;

    // Add sub oscillator for heartbeat thump
    subOsc = SinOsc.ar(freq * 0.5) * heartbeat * 0.5;
    sig = sig + subOsc;

    // Add saw layer for fervor/intensity
    sig = sig + (Saw.ar(freq * 1.003) * fervor * 0.25);

    // Apply amplitude tremolo
    sig = sig * ampLFO;

    // Display filter sweep - modulate the filter frequency
    filterFreq = filterFreq * (1 + (filterLFO * 1.0));

    // Soft saturation for drive
    sig = (sig * (1 + (fervor * 0.7))).tanh;

    // Tame before filter
    sig = LeakDC.ar(sig);
    sig = Limiter.ar(sig, 0.85);

    // Medium stereo spread
    sig = ~stereoSpread.(sig, pulseRate * 0.1, 0.4);

    // Mandatory output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = Limiter.ar(sig, 0.9);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_maratus_courtship_pulse loaded".postln;
