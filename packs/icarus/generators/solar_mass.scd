// Solar Mass — immense gravitational presence
// Role: bed

SynthDef(\forge_icarus_solar_mass, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gravity, fusion, mass, pressure, radiation;
    var saws, sub, high, fusionLfo, drive;

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
    gravity = In.kr(customBus0).linlin(0, 1, 0.5, 1.0);      // Overall level/weight
    fusion = In.kr(customBus1).linlin(0, 1, 0.05, 2);        // Beating rate
    mass = In.kr(customBus2).linlin(0, 1, 0.0, 0.7);         // Sub level
    pressure = In.kr(customBus3).linlin(0, 1, 1, 8);         // Drive amount
    radiation = In.kr(customBus4).linlin(0, 1, 0.0, 0.4);    // High freq content

    // Slow fusion reactor beating
    fusionLfo = SinOsc.kr(fusion, 0, 0.02, 1);

    // Massive detuned saws - the gravitational pull
    saws = Saw.ar(freq * fusionLfo) * 0.3;
    saws = saws + (Saw.ar(freq * 1.002 * fusionLfo) * 0.3);
    saws = saws + (Saw.ar(freq * 0.998 * fusionLfo) * 0.3);
    saws = saws + (Saw.ar(freq * 0.5 * fusionLfo) * 0.2);

    // Sub-harmonic mass
    sub = SinOsc.ar(freq * 0.25, 0, mass);
    sub = sub + SinOsc.ar(freq * 0.5, 0, mass * 0.5);

    // Core pressure - soft clipping/saturation
    drive = saws * pressure;
    drive = (drive.tanh) * (1 / pressure.sqrt);

    // Radiation - upper harmonics
    high = Pulse.ar(freq * 2, 0.3, radiation * 0.3);
    high = HPF.ar(high, 2000);

    // Combine with gravity weight
    sig = (drive + sub + high) * gravity;

    // Gentle stereo spread
    sig = ~stereoSpread.(sig, 0.1, 0.3);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_solar_mass loaded".postln;
