// Wax Wings -- melting, failing, coming apart
// Role: foreground

SynthDef(\forge_icarus_wax_wings, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var melt, drip, feather, fail, shimmer;
    var tone, meltMod, drips, flutter, shine;

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
    melt = In.kr(customBus0).linlin(0, 1, 0.0, 0.3);      // Pitch drop amount
    drip = In.kr(customBus1).linlin(0, 1, 1, 15);         // Drip rate
    feather = In.kr(customBus2).linlin(0, 1, 0.0, 0.5);   // Flutter level
    fail = In.kr(customBus3).linlin(0, 1, 0.0, 0.4);      // Instability
    shimmer = In.kr(customBus4).linlin(0, 1, 0.0, 3);     // FM index

    // Melting - slow pitch descent with wobble
    meltMod = LFNoise2.kr(0.3, melt, 1 - (melt * 0.5));

    // Core tone - sine with FM shimmer (light catching on wax)
    shine = SinOsc.ar(freq * meltMod * (1 + SinOsc.ar(freq * 2.01, 0, shimmer * 0.1)));

    // Feather flutter - fast tremolo texture
    flutter = SinOsc.ar(freq * 3 * meltMod, 0, feather);
    flutter = flutter * LFNoise2.ar(20 + (fail * 30));

    // Dripping wax - random impulses with pitch drop
    drips = Dust.ar(drip) * 0.5;
    drips = Ringz.ar(drips, freq * LFNoise0.kr(drip, 0.5, 1.5), 0.1);

    // Structural failure - random amplitude drops
    tone = shine + flutter + drips;
    tone = tone * (1 - (LFNoise2.kr(2 + (fail * 5)) * fail * 0.5));

    sig = tone;

    // Gentle stereo spread
    sig = ~stereoSpread.(sig, 0.2, 0.4);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_wax_wings loaded".postln;
