// Alert Pulse - Dual-tone urgent alert with radar ping character
// Role: accent (hits/stabs)

SynthDef(\forge_astro_command_alert_pulse, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var urg, alt, rdr, bip, pan;
    var tone1, tone2, radar, pulseRate, altEnv, bipClick;
    var panPos;

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
    urg = In.kr(customBus0).linlin(0, 1, 0, 1);
    alt = In.kr(customBus1).linlin(0, 1, 0, 1);
    rdr = In.kr(customBus2).linlin(0, 1, 0, 1);
    bip = In.kr(customBus3).linlin(0, 1, 0, 1);
    pan = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Pulse rate based on urgency
    pulseRate = urg.linexp(0, 1, 1, 8);

    // Alternating envelope for dual-tone
    altEnv = LFPulse.kr(pulseRate, 0, 0.5);

    // Two tones - classic alert interval (minor third or fourth)
    tone1 = SinOsc.ar(freq) * (1 - (altEnv * alt));
    tone2 = SinOsc.ar(freq * 1.26) * (altEnv * alt); // ~minor third

    // Radar ping - metallic ring with sharp attack
    radar = Ringz.ar(
        Impulse.ar(pulseRate * 0.5),
        freq * 2.5,
        rdr.linlin(0, 1, 0.05, 0.3)
    ) * rdr * 0.5;

    // Bip click - transient
    bipClick = EnvGen.ar(
        Env.perc(0.001, bip.linlin(0, 1, 0.01, 0.05)),
        Impulse.ar(pulseRate)
    ) * HPF.ar(WhiteNoise.ar(1), 4000) * bip * 0.3;

    // Combine
    sig = (tone1 + tone2) * 0.5 + radar + bipClick;

    // Panning movement
    panPos = SinOsc.kr(pulseRate * 0.25).range(pan.neg, pan);

    // Apply urgency-driven amplitude boost
    sig = sig * (1 + (urg * 0.5));

    // Output chain
    sig = Pan2.ar(sig, panPos);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_alert_pulse loaded".postln;
