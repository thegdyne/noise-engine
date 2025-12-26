SynthDef(\forge_seagrass_bay_submerged_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, pressure, murk, drift, body;
    var subOsc, mainOsc, driftMod, pressureEnv;

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

    // Custom params
    depth = In.kr(customBus0);      // Sub-octave intensity
    pressure = In.kr(customBus1);   // Compression density
    murk = In.kr(customBus2);       // Filter darkness
    drift = In.kr(customBus3);      // Pitch wandering
    body = In.kr(customBus4);       // Harmonic fullness

    // Slow drift modulation
    driftMod = LFNoise1.kr(0.1 + (drift * 0.3)) * (drift * 0.02);
    freq = freq * (1 + driftMod);

    // Main oscillator - warm saw
    mainOsc = Saw.ar(freq) * body.linlin(0, 1, 0.4, 0.7);

    // Sub-octave oscillator
    subOsc = Saw.ar(freq * 0.5) * depth.linlin(0, 1, 0.0, 0.6);

    // Body harmonics - octave up blended in
    sig = mainOsc + subOsc + (Saw.ar(freq * 2) * body * 0.15);

    // Pressure - subtle compression feel via soft clip
    pressureEnv = pressure.linlin(0, 1, 1.0, 0.7);
    sig = (sig * (1 + (pressure * 0.5))).tanh * pressureEnv;

    // Murk - additional low-pass darkness
    sig = LPF.ar(sig, murk.linexp(0, 1, 8000, 800));

    // Stereo spread
    sig = ~stereoSpread.(sig, 0.1, 0.3);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    sig = Limiter.ar(sig, 0.95);
    Out.ar(out, sig);
}).add;
"  * forge_seagrass_bay_submerged_drone loaded".postln;
