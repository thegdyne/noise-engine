// robotjox/stomp — Lightweight end-stage generator
SynthDef(\forge_robotjox_stomp, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, ground, quake, debris, pace;
    var trig, impact, membrane, subBoom, debrisNoise, rumble;

    mass = p[0];
    ground = p[1];
    quake = p[2];
    debris = p[3];
    pace = p[4];

    freq = In.kr(freqBus);

    // Step trigger
    trig = Dust.ar(pace.linexp(0, 1, 0.5, 4));

    // Impact transient
    impact = HPF.ar(WhiteNoise.ar(0.8), 100) * Decay.ar(trig, 0.02);
    impact = impact + (BrownNoise.ar(0.5) * Decay.ar(trig, 0.05));

    // Membrane resonance - ground surface
    membrane = Ringz.ar(trig, freq * (0.5 + (ground * 0.5)), 0.2 + (mass * 0.3), 0.4);
    membrane = membrane + Ringz.ar(trig, freq * 0.7, 0.15 + (mass * 0.2), 0.3);
    membrane = membrane + Ringz.ar(trig, freq * 1.3, 0.1 + (ground * 0.15), 0.25);

    // Sub boom - massive weight
    subBoom = SinOsc.ar(freq * 0.25, 0, 0.5 * mass);
    subBoom = subBoom * Decay.ar(trig, 0.3 + (mass * 0.4));
    subBoom = subBoom + (SinOsc.ar(freq * 0.125, 0, 0.3 * mass) * Decay.ar(trig, 0.5));

    // Debris scatter
    debrisNoise = HPF.ar(PinkNoise.ar(0.4), 1000);
    debrisNoise = debrisNoise * Decay2.ar(trig, 0.01, 0.2 + (debris * 0.3));
    debrisNoise = debrisNoise * debris;

    sig = impact + membrane + subBoom + debrisNoise;

    // Continuous ground rumble
    rumble = LPF.ar(BrownNoise.ar(0.2), 100 + (freq * 0.3));
    rumble = rumble * LFNoise2.kr(0.5).range(0.5, 1.0);
    rumble = rumble * (0.3 + (quake * 0.7));

    sig = sig + rumble;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.1), 200);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_stomp loaded".postln;
