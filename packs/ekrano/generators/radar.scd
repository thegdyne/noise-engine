SynthDef(\forge_ekrano_radar, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pulse, sweep, beam, ping, echo;
    var pulseTrig, sweepMod, additive, pingEnv, echoDelay;

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

    // Custom params
    pulse = In.kr(customBus0).linexp(0, 1, 0.5, 8);
    sweep = In.kr(customBus1).linlin(0, 1, 1, 2);
    beam = In.kr(customBus2).linlin(0, 1, 0.3, 1);
    ping = In.kr(customBus3).linlin(0, 1, 0.01, 0.1);
    echo = In.kr(customBus4).linexp(0, 1, 0.1, 1.5);

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

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_radar loaded".postln;
