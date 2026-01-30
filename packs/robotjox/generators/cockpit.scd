// robotjox/cockpit — Lightweight end-stage generator
SynthDef(\forge_robotjox_cockpit, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var alertLvl, hud, comms, power, damage;
    var carrier, modulator, fmSig, alertTone, hudBeep, powerDrone, glitch;

    alertLvl = p[0];
    hud = p[1];
    comms = p[2];
    power = p[3];
    damage = p[4];

    freq = In.kr(freqBus);

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

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_cockpit loaded".postln;
