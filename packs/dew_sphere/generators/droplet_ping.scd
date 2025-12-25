// Droplet Ping - Light striking a perfect water sphere
// Karplus-Strong with crystalline character and spherical decay

SynthDef(\forge_dew_sphere_droplet_ping, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sphere, glisten, ring, prism, clarity;
    var exciter, pluck, delay, decayTime, coef;
    var shimmer, prismOsc;

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
    sphere = In.kr(customBus0);     // Sphericity/purity
    glisten = In.kr(customBus1);    // Initial brightness
    ring = In.kr(customBus2);       // Ring time
    prism = In.kr(customBus3);      // Inharmonic color
    clarity = In.kr(customBus4);    // Crystal clarity

    // Exciter - short bright burst, glisten controls brightness
    exciter = WhiteNoise.ar(1) * EnvGen.ar(Env.perc(0.001, 0.01));
    exciter = HPF.ar(exciter, glisten.linexp(0, 1, 500, 4000));

    // Delay time from frequency
    delay = freq.reciprocal;

    // Decay coefficient - sphere makes it purer (less damping)
    coef = sphere.linlin(0, 1, 0.95, 0.995);
    decayTime = ring.linexp(0, 1, 0.3, 4.0);

    // Main Karplus-Strong pluck
    pluck = Pluck.ar(
        exciter,
        Impulse.ar(0),  // Trigger handled by envVCA
        0.2,
        delay.clip(0.0001, 0.2),
        decayTime,
        coef
    );

    // Prismatic inharmonic partial - slight detuning for color
    prismOsc = Pluck.ar(
        exciter * 0.5,
        Impulse.ar(0),
        0.2,
        (delay * (1 + (prism * 0.03))).clip(0.0001, 0.2),
        decayTime * 0.7,
        coef * 0.98
    ) * prism;

    // Shimmer - high frequency sparkle
    shimmer = Pluck.ar(
        exciter * 0.3,
        Impulse.ar(0),
        0.1,
        (delay * 0.5).clip(0.0001, 0.1),
        decayTime * 0.5,
        coef
    ) * clarity * 0.4;

    // Mix
    sig = pluck + prismOsc + shimmer;

    // Clarity filtering - cleaner water = more highs
    sig = LPF.ar(sig, clarity.linexp(0, 1, 4000, 18000));

    // Gentle saturation for warmth
    sig = (sig * 1.2).tanh * 0.8;

    // Output chain
    sig = ~stereoSpread.(sig, 0.15, 0.2 + (prism * 0.3));
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_droplet_ping loaded".postln;
