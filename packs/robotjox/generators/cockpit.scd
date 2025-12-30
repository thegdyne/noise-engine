SynthDef(\forge_robotjox_cockpit, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var alertLvl, hud, comms, power, damage;
    var carrier, modulator, fmSig, alertTone, hudBeep, powerDrone, glitch;

    // Theme params
    alertLvl = In.kr(customBus0);
    hud = In.kr(customBus1);
    comms = In.kr(customBus2);
    power = In.kr(customBus3);
    damage = In.kr(customBus4);

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

    // FM modulator
    modulator = SinOsc.ar(freq * (2 + (comms * 2)), 0, freq * (1 + (alertLvl * 4)));

    // FM carrier
    carrier = SinOsc.ar(freq + modulator, 0, 0.3);

    // Second FM layer
    fmSig = carrier + SinOsc.ar((freq * 1.5) + (modulator * 0.5), 0, 0.2 * comms);

    // Alert warning tone - pulsing
    alertTone = SinOsc.ar(freq * 2, 0, 0.25 * alertLvl);
    alertTone = alertTone * LFPulse.kr(alertLvl.linexp(0, 1, 1, 6), 0, 0.5).lag(0.02);

    // HUD beeps and blips
    hudBeep = SinOsc.ar(freq * 4, 0, 0.15 * hud);
    hudBeep = hudBeep * LFPulse.kr(hud.linexp(0, 1, 2, 12), 0, 0.1).lag(0.005);
    hudBeep = hudBeep + (Pulse.ar(freq * 3, 0.3, 0.1 * hud) * LFNoise0.kr(8).range(0, 1));

    // Power systems drone
    powerDrone = Saw.ar(freq * 0.5, 0.15 * power);
    powerDrone = powerDrone + SinOsc.ar(freq * 0.25, 0, 0.2 * power);
    powerDrone = powerDrone * LFNoise2.kr(0.3).range(0.8, 1.0);

    // System damage glitch
    glitch = WhiteNoise.ar(0.2) * LFNoise0.kr(damage.linexp(0, 1, 1, 20)).range(0, 1);
    glitch = glitch * damage;
    glitch = HPF.ar(glitch, 2000);

    sig = fmSig + alertTone + hudBeep + powerDrone + glitch;

    // Continuous electronic hum
    sig = sig + SinOsc.ar(60, 0, 0.08);
    sig = sig + PinkNoise.ar(0.04);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_robotjox_cockpit loaded".postln;
