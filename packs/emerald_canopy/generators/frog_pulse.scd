// Frog Pulse - FM bass with rhythmic croak
// Role: foreground | Family: FM

SynthDef(\forge_emerald_canopy_frog_pulse, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var croak, throat, wet, inflate, hop;
    var croakLfo, pitchEnv, modFreq, modIndex, carrier, sub, formant;

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
    croak = In.kr(customBus0);    // FM wobble
    throat = In.kr(customBus1);   // Resonance size
    wet = In.kr(customBus2);      // Formant character
    inflate = In.kr(customBus3);  // Sub emphasis
    hop = In.kr(customBus4);      // Pitch envelope

    // Croak LFO - irregular wobble like frog throat
    croakLfo = LFNoise1.kr(croak.linexp(0, 1, 4, 20));
    croakLfo = croakLfo * croak;

    // Hop - pitch drops down quickly
    pitchEnv = EnvGen.kr(Env.perc(0.001, 0.1), 1);
    freq = freq * (1 + (pitchEnv * hop * 0.5));

    // FM synthesis for croak texture
    modFreq = freq * throat.linexp(0, 1, 0.5, 2);
    modIndex = croak.linexp(0, 1, 1, 12) * (1 + croakLfo);

    carrier = SinOsc.ar(freq + (SinOsc.ar(modFreq) * modIndex * freq * 0.5));

    // Sub bass layer
    sub = SinOsc.ar(freq * 0.5) * inflate * 0.6;
    sub = sub + (SinOsc.ar(freq * 0.25) * inflate * 0.3);

    // Wet formant - like frog vocal sac
    formant = Formant.ar(
        freq,
        throat.linexp(0, 1, 200, 800),
        throat.linexp(0, 1, 50, 200)
    ) * wet * 0.4;

    sig = carrier + sub + formant;

    // Throat resonance - bandpass
    sig = sig + (BPF.ar(sig, throat.linexp(0, 1, 100, 400), 0.3) * throat * 0.5);

    // Soft saturation for body
    sig = (sig * 1.5).tanh * 0.8;

    // Center-heavy but slight movement
    sig = Pan2.ar(sig, croakLfo * 0.2);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_frog_pulse loaded".postln;
