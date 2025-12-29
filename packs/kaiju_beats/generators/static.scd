SynthDef(\forge_kaiju_beats_static, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var tune, burst, scan, crackle, carrier;
    var radioNoise, tuningWhine, staticBursts, scanSweep;

    // Theme params
    tune = In.kr(customBus0);         // P1: Tuning dial - sweeps frequency
    burst = In.kr(customBus1);        // P2: Static burst intensity
    scan = In.kr(customBus2);         // P3: Frequency scanning rate
    crackle = In.kr(customBus3);      // P4: Crackle/pop amount
    carrier = In.kr(customBus4);      // P5: Carrier tone mix

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
    ampVal = 0.2;

    // Base radio static
    radioNoise = WhiteNoise.ar(0.3) + (PinkNoise.ar(0.2));
    radioNoise = BPF.ar(radioNoise, freq * 2 + (tune * 2000), 0.3);

    // Tuning whine - carrier tone
    tuningWhine = SinOsc.ar(freq + (tune * 500) + (LFNoise1.kr(scan * 5) * 100));
    tuningWhine = tuningWhine * carrier * 0.3;

    // Static bursts - rhythmic
    staticBursts = WhiteNoise.ar(1);
    staticBursts = staticBursts * Dust.ar(3 + (burst * 20));
    staticBursts = staticBursts * burst * 0.5;

    // Scan sweep - slow frequency movement
    scanSweep = LFSaw.kr(0.1 + (scan * 0.5)).range(500, 3000);
    radioNoise = radioNoise + BPF.ar(WhiteNoise.ar(0.2), scanSweep, 0.1);

    // Crackle pops
    staticBursts = staticBursts + (Dust.ar(crackle * 30) * crackle * 0.4);

    // Mix
    sig = radioNoise + tuningWhine + staticBursts;

    // Add continuous bed for drone mode
    sig = sig + (PinkNoise.ar(0.05));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_kaiju_beats_static loaded".postln;
