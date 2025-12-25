// Dewdrop - Crystalline plucks like morning dew
// Role: accent | Family: physical

SynthDef(\forge_emerald_canopy_dewdrop, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var dropsize, shine, ripple, surface, sparkle;
    var exciter, pluck, damping, coef, rippleOsc, sparkleNoise;

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
    dropsize = In.kr(customBus0);   // Body/sustain
    shine = In.kr(customBus1);      // Brightness
    ripple = In.kr(customBus2);     // Secondary resonance
    surface = In.kr(customBus3);    // Damping
    sparkle = In.kr(customBus4);    // High shimmer

    // Exciter - noise burst shaped by drop size
    exciter = PinkNoise.ar * EnvGen.ar(
        Env.perc(0.001, dropsize.linexp(0, 1, 0.005, 0.05)),
        1  // Always on, env handled by envVCA
    );

    // Add some click for small drops
    exciter = exciter + (Impulse.ar(0) * (1 - dropsize) * 0.5);

    // Damping coefficient based on surface tension
    damping = surface.linexp(0, 1, 0.99, 0.9);
    coef = shine.linlin(0, 1, 0.3, 0.8);  // Brightness affects filter

    // Karplus-Strong style pluck
    pluck = Pluck.ar(
        exciter,
        1,
        freq.reciprocal,
        freq.reciprocal,
        dropsize.linexp(0, 1, 1, 8),  // Decay time based on drop size
        coef
    );

    // Ripple - secondary pitched resonance
    rippleOsc = SinOsc.ar(freq * 2.01) * EnvGen.ar(
        Env.perc(0.001, ripple.linexp(0, 1, 0.1, 0.5))
    ) * ripple * 0.3;

    // Sparkle - filtered high noise
    sparkleNoise = HPF.ar(WhiteNoise.ar, 8000) * EnvGen.ar(
        Env.perc(0.001, 0.05)
    ) * sparkle * 0.2;

    sig = pluck + rippleOsc + sparkleNoise;

    // Stereo spread based on shine
    sig = Pan2.ar(sig, LFNoise2.kr(2) * shine * 0.3);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_dewdrop loaded".postln;
