SynthDef(\forge_fuego_celeste_galactic_core, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                               filterTypeBus, envEnabledBus, envSourceBus=0,
                                               clockRateBus, clockTrigBus,
                                               midiTrigBus=0, slotIndex=0,
                                               customBus0, customBus1, customBus2, customBus3, customBus4,
                                               portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var core, spiral, pink, mass, ancient;
    var spiralLFO, ancientDrift, harmonics, subMass, pinkResonance;

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

    // Theme parameters
    core = In.kr(customBus0);       // central brightness
    spiral = In.kr(customBus1);     // rotation rate
    pink = In.kr(customBus2);       // warm coloration
    mass = In.kr(customBus3);       // gravitational weight
    ancient = In.kr(customBus4);    // age/depth

    // Spiral rotation - very slow galactic spin
    spiralLFO = SinOsc.kr(spiral.linexp(0, 1, 0.02, 0.2));

    // Ancient drift - subtle pitch wandering over eons
    ancientDrift = LFNoise1.kr(ancient.linexp(0, 1, 0.01, 0.08)).range(0.995, 1.005);

    // Rich harmonics - layered oscillators
    harmonics = Mix([
        SinOsc.ar(freq * ancientDrift, 0, 0.4),
        LFTri.ar(freq * ancientDrift * 0.999, 0, 0.25),
        LFSaw.ar(freq * ancientDrift * 1.001, 0, 0.15 * core),
        SinOsc.ar(freq * 2 * ancientDrift, spiralLFO * pi, 0.15 * core),
        SinOsc.ar(freq * 3 * ancientDrift, 0, 0.1 * core)
    ]);

    // Sub mass - gravitational low end
    subMass = SinOsc.ar(freq * 0.5 * ancientDrift) * mass * 0.4;
    subMass = subMass + (LFPulse.ar(freq * 0.25, 0, 0.5) * mass * 0.2);
    subMass = LPF.ar(subMass, 150);

    // Pink resonance - warm bandpass for nebula color
    pinkResonance = BPF.ar(harmonics, pink.linexp(0, 1, 400, 1500), 0.5) * pink;

    // Mix all sources
    sig = harmonics + subMass + (pinkResonance * 0.5);

    // Core brightness control
    sig = sig * core.linlin(0, 1, 0.6, 1.2);

    // Spiral stereo modulation
    sig = Pan2.ar(sig, spiralLFO * spiral * 0.5);

    // Standard post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_galactic_core loaded".postln;
