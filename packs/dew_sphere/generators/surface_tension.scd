// Surface Tension - Cohesive force holding droplets together
// Subtractive bed with phase-locked oscillators and slow binding modulation

SynthDef(\forge_dew_sphere_surface_tension, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tension, cohesion, size, drift, air;
    var osc1, osc2, osc3, bindMod, driftMod, breath;
    var detune, phaseLink;

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
    tension = In.kr(customBus0);    // Binding force
    cohesion = In.kr(customBus1);   // Phase cohesion
    size = In.kr(customBus2);       // Droplet size
    drift = In.kr(customBus3);      // Organic drift
    air = In.kr(customBus4);        // Breathiness

    // Binding modulation - slow cohesive force
    bindMod = SinOsc.kr(tension.linexp(0, 1, 0.05, 0.5)) * tension * 0.02;

    // Organic drift - very slow random movement
    driftMod = LFNoise1.kr(drift.linexp(0, 1, 0.02, 0.2)) * drift * 0.015;

    // Detune based on size (larger = more spread)
    detune = size.linexp(0, 1, 1.001, 1.02);

    // Phase-linked oscillators - cohesion controls how tightly they track
    phaseLink = cohesion.linlin(0, 1, 0.0, 0.8);
    osc1 = VarSaw.ar(freq * (1 + bindMod + driftMod), 0, 0.5);
    osc2 = VarSaw.ar(freq * detune * (1 + (bindMod * phaseLink)), 0, 0.4);
    osc3 = VarSaw.ar(freq / detune * (1 + (bindMod * phaseLink) - driftMod), 0, 0.6);

    // Mix oscillators with size-dependent balance
    sig = (osc1 * 0.5) + (osc2 * size * 0.3) + (osc3 * (1 - size) * 0.3);

    // Breath layer - filtered noise for air
    breath = BPF.ar(PinkNoise.ar(0.3), freq * 2, 0.5) * air;
    sig = sig + breath;

    // Gentle saturation for cohesion
    sig = (sig * (1 + (tension * 0.5))).tanh * 0.8;

    // Output chain
    sig = ~stereoSpread.(sig, 0.1 + (drift * 0.3), 0.2 + (size * 0.3));
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_surface_tension loaded".postln;
