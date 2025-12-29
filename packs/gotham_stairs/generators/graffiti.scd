SynthDef(\forge_gotham_stairs_graffiti, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var spray, grit, drip, layer, vandal;
    var hiss, texture, drips, layers;

    // Theme params
    spray = In.kr(customBus0);
    grit = In.kr(customBus1);
    drip = In.kr(customBus2);
    layer = In.kr(customBus3);
    vandal = In.kr(customBus4);

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

    // Spray paint hiss - high frequency noise bursts
    hiss = WhiteNoise.ar(spray * 0.4);
    hiss = RHPF.ar(hiss, freq * 4 + (spray * 2000), 0.3);
    hiss = hiss * LFNoise2.kr(3 + (vandal * 5)).range(0.3, 1);

    // Wall texture - gritty filtered noise
    texture = BrownNoise.ar(0.3) + (PinkNoise.ar(0.2) * grit);
    texture = Resonz.ar(texture, freq * (1 + (grit * 2)), 0.5 + (grit * 0.3)) * 4;

    // Paint drips - irregular resonant pings
    drips = Dust.ar(drip.linlin(0, 1, 0.5, 8));
    drips = Ringz.ar(drips, freq * [1.5, 2.1], drip.linlin(0, 1, 0.1, 0.4)).sum * 0.3;

    // Layered depth - multiple filtered noise bands
    layers = Mix.fill(4, { |i|
        var layerFreq = freq * (1 + (i * 0.5 * layer));
        var layerNoise = PinkNoise.ar(0.15);
        Resonz.ar(layerNoise, layerFreq, 0.2 + (layer * 0.3)) * 3
    });

    // Combine with vandal chaos modulation
    sig = hiss + texture + drips + (layers * layer);
    sig = sig * (1 + (LFNoise0.kr(vandal.linlin(0, 1, 0.5, 8)).range(0, 0.5) * vandal));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_gotham_stairs_graffiti loaded".postln;
