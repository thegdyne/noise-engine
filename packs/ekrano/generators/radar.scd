// ekrano/radar — Lightweight end-stage generator
SynthDef(\forge_ekrano_radar, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var pulse, sweep, beam, ping, echo;
    var pulseTrig, sweepMod, additive, pingEnv, echoDelay;

    freq = In.kr(freqBus);

    pulse = p[0].linexp(0, 1, 0.5, 8);
    sweep = p[1].linlin(0, 1, 1, 2);
    beam = p[2].linlin(0, 1, 0.3, 1);
    ping = p[3].linlin(0, 1, 0.01, 0.1);
    echo = p[4].linexp(0, 1, 0.1, 1.5);

    // Pulse trigger
    pulseTrig = Impulse.ar(pulse) + Dust.ar(pulse * 0.3);

    // Ping envelope
    pingEnv = Decay2.ar(pulseTrig, ping * 0.1, ping);

    // Sweep modulation
    sweepMod = LFSaw.kr(pulse * 0.25).range(1, sweep);

    // Additive partials - radar ping character
    additive = Mix.ar([
        SinOsc.ar(freq * sweepMod) * 1.0,
        SinOsc.ar(freq * 2 * sweepMod) * 0.7 * beam,
        SinOsc.ar(freq * 3 * sweepMod) * 0.5 * beam,
        SinOsc.ar(freq * 4 * sweepMod) * 0.35 * beam,
        SinOsc.ar(freq * 5 * sweepMod) * 0.25 * beam,
        SinOsc.ar(freq * 6 * sweepMod) * 0.15 * beam,
        SinOsc.ar(freq * 7 * sweepMod) * 0.1 * beam
    ]) * 0.2;

    sig = additive * pingEnv;

    // Echo delay
    echoDelay = CombL.ar(sig, 2, echo * 0.3 + 0.05, echo * 2);
    sig = sig + (echoDelay * 0.4);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_radar loaded".postln;
