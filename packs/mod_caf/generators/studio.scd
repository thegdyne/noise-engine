// studio: Room tone and quiet studio ambience
SynthDef(\forge_mod_caf_studio, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var room, hvac, gear, quiet, presence;

    // Theme params
    room = In.kr(customBus0).linlin(0, 1, 0.2, 0.7);        // P1: Room tone
    hvac = In.kr(customBus1).linlin(0, 1, 0, 0.4);          // P2: HVAC hum
    gear = In.kr(customBus2).linlin(0, 1, 0, 0.3);          // P3: Gear noise
    quiet = In.kr(customBus3).linlin(0, 1, 200, 1500);      // P4: Quiet filter
    presence = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);    // P5: Human presence

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

    // DSP: Room tone - continuous filtered noise
    sig = LPF.ar(PinkNoise.ar(room), quiet) * 0.5;

    // HVAC - low drone
    sig = sig + (LPF.ar(BrownNoise.ar(hvac), 150) * 0.5);

    // Gear noise - high frequency hiss
    sig = sig + (HPF.ar(WhiteNoise.ar(gear * 0.3), 4000));

    // Human presence - occasional subtle movement
    sig = sig + (BPF.ar(PinkNoise.ar(presence), 400 * LFNoise1.kr(0.1).range(0.8, 1.2), 0.3) * LFNoise1.kr(0.2).range(0.3, 1) * 0.3);

    // Sub presence - room resonance
    sig = sig + (SinOsc.ar(freq * 0.25) * room * 0.15);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_studio loaded".postln;
