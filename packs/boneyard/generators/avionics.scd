// AVIONICS - Dead electronics, ghost signals, capacitor discharge
// Role: foreground
SynthDef(\forge_boneyard_avionics, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var discharge, drift, static, ghost, power;
    var oscillators, staticBurst, ghostEcho, powerMod, driftLFO;

    // Custom params
    discharge = In.kr(customBus0);  // Discharge rate
    drift = In.kr(customBus1);      // Frequency drift
    static = In.kr(customBus2);     // Static bursts
    ghost = In.kr(customBus3);      // Ghost echoes
    power = In.kr(customBus4);      // Power fade

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

    // Power modulation - dying voltage
    powerMod = LFNoise2.kr(power.linexp(0, 1, 0.1, 2));
    powerMod = powerMod.range(power, 1);

    // Frequency drift - unstable oscillators
    driftLFO = LFNoise1.kr(drift.linexp(0, 1, 0.2, 5));
    driftLFO = driftLFO * drift * 50;

    // Main oscillator bank - electronic tones
    oscillators = SinOsc.ar(freq + driftLFO, 0, 0.4);
    oscillators = oscillators + Pulse.ar(
        (freq * 0.5) + (driftLFO * 0.5),
        LFNoise2.kr(0.5).range(0.3, 0.7),
        0.2
    );
    oscillators = oscillators + SinOsc.ar(
        freq * 2 + (driftLFO * -1),
        0,
        0.15 * discharge
    );

    // Capacitor whine - high frequency component
    oscillators = oscillators + SinOsc.ar(
        freq * discharge.linexp(0, 1, 4, 16),
        0,
        0.1 * discharge * EnvGen.kr(Env.perc(0.01, discharge.linexp(0, 1, 0.5, 3)))
    );

    // Static bursts
    staticBurst = WhiteNoise.ar(0.5) * Dust.kr(static.linexp(0, 1, 0.5, 20));
    staticBurst = HPF.ar(staticBurst, 2000);
    staticBurst = staticBurst * EnvGen.ar(
        Env.perc(0.001, static.linexp(0, 1, 0.02, 0.15)),
        Dust.kr(static.linexp(0, 1, 1, 15))
    );
    staticBurst = staticBurst * static;

    // Ghost echoes - delayed signal artifacts
    ghostEcho = CombL.ar(
        oscillators,
        0.5,
        LFNoise1.kr(0.3).range(0.1, 0.4),
        ghost * 3
    );
    ghostEcho = ghostEcho * ghost * 0.4;
    ghostEcho = LPF.ar(ghostEcho, 2000);  // Degraded echo

    // Combine
    sig = (oscillators * powerMod) + staticBurst + ghostEcho;

    // Overall power fade effect
    sig = sig * power.linlin(0, 1, 0.3, 1);

    // Digital degradation
    sig = sig.round(power.linexp(0, 1, 0.001, 0.05));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_boneyard_avionics loaded".postln;
