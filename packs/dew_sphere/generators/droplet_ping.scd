// Droplet Ping - Light striking a perfect water sphere
// Karplus-Strong with crystalline character and spherical decay

SynthDef(\forge_dew_sphere_droplet_ping, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, startTrig, clkTrig, midiTrig;
    var sphere, glisten, ring, prism, clarity;
    var exciter, pluck, delay, decayTime, coef;
    var shimmer, prismOsc;
    var trigExciter, droneExciter;

    // Standard bus reads (guarded)
    freq = In.kr(freqBus).clip(20, 20000);
    portamento = In.kr(portamentoBus).clip(0, 1);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus).clip(30, 18000);
    rq = In.kr(resBus).clip(0.05, 0.98);
    attack = In.kr(attackBus).clip(0.0005, 10);
    decay = In.kr(decayBus).clip(0.005, 30);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus).clip(0, 2);
    clockRate = In.kr(clockRateBus).clip(0, 12);
    amp = 0.5;

    // Theme params (guarded 0-1)
    sphere = In.kr(customBus0).clip(0, 1);
    glisten = In.kr(customBus1).clip(0, 1);
    ring = In.kr(customBus2).clip(0, 1);
    prism = In.kr(customBus3).clip(0, 1);
    clarity = In.kr(customBus4).clip(0, 1);

    // Trigger for Pluck excitation
    // envSource: 0=DRONE(start impulse), 1=CLOCK, 2=MIDI
    startTrig = Impulse.ar(0.5); // Slow periodic pings in drone mode
    clkTrig   = Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13));
    midiTrig  = Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8));
    trig = Select.ar(envSource.round.clip(0, 2), [startTrig, clkTrig, midiTrig]);
    trig = Trig1.ar(trig, 0.001); // enforce short impulse

    // Exciter - short bright burst (triggered)
    exciter = WhiteNoise.ar(1) * EnvGen.ar(Env.perc(0.001, 0.01), trig);
    exciter = HPF.ar(exciter, glisten.linexp(0, 1, 500, 4000));

    // Delay time from frequency
    delay = freq.reciprocal;

    // Decay coefficient - sphere makes it purer
    coef = sphere.linlin(0, 1, 0.95, 0.995);
    decayTime = ring.linexp(0, 1, 0.3, 4.0);

    // Main Karplus-Strong pluck
    pluck = Pluck.ar(
        exciter,
        trig,
        0.2,
        delay.clip(0.0001, 0.2),
        decayTime,
        coef
    );

    // Prismatic inharmonic partial
    prismOsc = Pluck.ar(
        exciter * 0.5,
        trig,
        0.2,
        (delay * (1 + (prism * 0.03))).clip(0.0001, 0.2),
        decayTime * 0.7,
        (coef * 0.98).clip(0.90, 0.999)
    ) * prism;

    // Shimmer - high frequency sparkle
    shimmer = Pluck.ar(
        exciter * 0.3,
        trig,
        0.1,
        (delay * 0.5).clip(0.0001, 0.1),
        decayTime * 0.5,
        coef
    ) * clarity * 0.4;

    // Mix
    sig = pluck + prismOsc + shimmer;

    // Clarity filtering
    sig = LPF.ar(sig, clarity.linexp(0, 1, 4000, 18000));

    // Gentle saturation
    sig = (sig * 1.2).tanh * 0.8;

    // Safety
    sig = LeakDC.ar(sig);
    sig = HPF.ar(sig, 20);

    // Output chain
    sig = ~stereoSpread.(sig, 0.2, 0.3);
    sig = Limiter.ar(sig, 0.95);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_droplet_ping loaded".postln;

