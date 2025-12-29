SynthDef(\forge_oldwinch_barrow, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var depthParam, spirit, earth, bronze, timeParam;
    var drone, spiritShimmer, bronzePartials, timeMod, earthFilter;

    // Theme params
    depthParam = In.kr(customBus0);
    spirit = In.kr(customBus1);
    earth = In.kr(customBus2);
    bronze = In.kr(customBus3);
    timeParam = In.kr(customBus4);

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

    // Deep time modulation - very slow
    timeMod = LFNoise2.kr(timeParam.linexp(0, 1, 0.02, 0.1)).range(0.98, 1.02);

    // Core spectral drone - layered sines
    drone = SinOsc.ar(freq * timeMod, 0, 0.25);
    drone = drone + SinOsc.ar(freq * 0.5 * timeMod, 0, 0.3 * depthParam);
    drone = drone + SinOsc.ar(freq * 0.25 * timeMod, 0, 0.25 * depthParam);
    drone = drone + SinOsc.ar(freq * 2 * timeMod, 0, 0.15 * (1 - depthParam));
    drone = drone + SinOsc.ar(freq * 1.5 * timeMod, 0, 0.12);

    // Spirit shimmer - detuned high partials
    spiritShimmer = SinOsc.ar(freq * 3 * LFNoise2.kr(0.5).range(0.99, 1.01), 0, 0.1 * spirit);
    spiritShimmer = spiritShimmer + SinOsc.ar(freq * 4 * LFNoise2.kr(0.4).range(0.99, 1.01), 0, 0.08 * spirit);
    spiritShimmer = spiritShimmer + SinOsc.ar(freq * 5 * LFNoise2.kr(0.3).range(0.99, 1.01), 0, 0.06 * spirit);
    spiritShimmer = spiritShimmer * LFNoise2.kr(1 + (spirit * 3)).range(0.5, 1.0);

    // Bronze Age metallic partials
    bronzePartials = SinOsc.ar(freq * 2.3, 0, 0.1 * bronze);
    bronzePartials = bronzePartials + SinOsc.ar(freq * 3.7, 0, 0.08 * bronze);
    bronzePartials = bronzePartials + SinOsc.ar(freq * 5.1, 0, 0.06 * bronze);
    bronzePartials = bronzePartials * LFNoise2.kr(0.2).range(0.7, 1.0);

    sig = drone + spiritShimmer + bronzePartials;

    // Earth damping - low pass based on earth covering
    earthFilter = earth.linexp(0, 1, 5000, 800);
    sig = LPF.ar(sig, earthFilter);

    // Underground resonance
    sig = sig + LPF.ar(BrownNoise.ar(0.1 * depthParam), 150);

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.06), 300);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_oldwinch_barrow loaded".postln;
