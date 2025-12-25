SynthDef(\forge_block_walk_street_hum, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var hum, distance, wire, drift, air;
    var humSig, wireSig, airSig, driftLFO, freqDrift, ampDrift;

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
    hum = In.kr(customBus0);        // Power fundamental
    distance = In.kr(customBus1);   // Distance filtering
    wire = In.kr(customBus2);       // Wire buzz
    drift = In.kr(customBus3);      // Slow wandering
    air = In.kr(customBus4);        // Breeze/air

    // Drift LFOs for organic movement
    driftLFO = LFNoise1.kr(0.2);
    freqDrift = driftLFO * drift.linlin(0, 1, 0, 3);
    ampDrift = LFNoise1.kr(0.3).range(1 - (drift.linlin(0, 1, 0, 0.15)), 1);

    // Power line hum - 60Hz harmonics modulated by freq param
    humSig = SinOsc.ar(freq + freqDrift) * 0.5;
    humSig = humSig + (SinOsc.ar((freq * 2) + (freqDrift * 2)) * 0.3);
    humSig = humSig + (SinOsc.ar((freq * 3) + (freqDrift * 3)) * 0.15);
    humSig = humSig + (SinOsc.ar((freq * 5) + (freqDrift * 5)) * 0.08);
    humSig = humSig * hum.linlin(0, 1, 0.3, 0.9);

    // Wire buzz - filtered noise at high freq
    wireSig = BPF.ar(WhiteNoise.ar(0.3), 4000 + (LFNoise1.kr(2) * 1000), 0.3);
    wireSig = wireSig * Dust.kr(8).lag(0.05);  // Intermittent crackle
    wireSig = wireSig * wire.linlin(0, 1, 0, 0.5);

    // Air/breeze layer
    airSig = LPF.ar(PinkNoise.ar(0.2), 800 + (LFNoise1.kr(0.5) * 400));
    airSig = airSig * LFNoise1.kr(0.8).range(0.3, 1);
    airSig = airSig * air.linlin(0, 1, 0, 0.4);

    sig = (humSig + wireSig + airSig) * ampDrift;

    // Distance = lowpass filtering (further = darker)
    sig = LPF.ar(sig, distance.linexp(0, 1, 8000, 800));

    // Output chain
    sig = ~stereoSpread.(sig, 0.1, 0.5);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_block_walk_street_hum loaded".postln;
