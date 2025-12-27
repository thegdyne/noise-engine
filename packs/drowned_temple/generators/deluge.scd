// deluge: Rain cascading through broken vaults
SynthDef(\forge_drowned_temple_deluge, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var intensity, droplets, sheet, splash, distant;

    // Theme params
    intensity = In.kr(customBus0).linlin(0, 1, 0.4, 1);     // P1: Rain intensity
    droplets = In.kr(customBus1).linlin(0, 1, 10, 60);      // P2: Droplet rate (boosted)
    sheet = In.kr(customBus2).linlin(0, 1, 0.3, 1);         // P3: Sheet rain noise
    splash = In.kr(customBus3).linlin(0, 1, 0.2, 0.8);      // P4: Splash impacts
    distant = In.kr(customBus4).linlin(0, 1, 0.2, 0.6);     // P5: Distant rumble

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

    // DSP: Sheet rain - continuous filtered noise (boosted)
    sig = BPF.ar(PinkNoise.ar(sheet), 2500 * LFNoise1.kr(0.3).range(0.6, 1.4), 0.6) * 4;

    // Droplet impacts - stereo Ringz array (boosted)
    sig = sig + (Ringz.ar(Dust.ar(droplets * intensity) * 0.3, freq * [3, 4.5, 6], 0.05) * splash * 0.6);

    // Splash on stone
    sig = sig + (HPF.ar(Dust2.ar(droplets * 0.7) * splash * 0.2, 1500));

    // Distant thunder rumble (boosted)
    sig = sig + (LPF.ar(BrownNoise.ar(distant), 200) * LFNoise1.kr(0.1).range(0.4, 1) * 0.6);

    // Continuous base layer
    sig = sig + (LPF.ar(PinkNoise.ar(intensity * 0.4), 1000));

    sig = sig * intensity * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_deluge loaded".postln;
