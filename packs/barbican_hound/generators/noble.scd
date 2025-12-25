// NOBLE - Stately, dignified pad like the Great Dane
// Family: physical (bowed)
// Role: foreground

SynthDef(\forge_barbican_hound_noble, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var poise, grace, gaze, coat, sizeAmt;
    var bowVel, bowPress, string, body, exciter;

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
    poise = In.kr(customBus0);    // Bow pressure/steadiness
    grace = In.kr(customBus1);    // Brightness
    gaze = In.kr(customBus2);     // Expression/modulation
    coat = In.kr(customBus3);     // Body warmth
    sizeAmt = In.kr(customBus4);  // Fundamental depth

    // Adjust frequency for size (lower = bigger dog)
    freq = freq * sizeAmt.linexp(0, 1, 1.5, 0.5);

    // Bow velocity with subtle expression
    bowVel = poise.linexp(0, 1, 0.3, 1.0) + (LFNoise1.kr(0.5) * gaze * 0.2);

    // Bow pressure
    bowPress = poise.linlin(0, 1, 0.3, 0.8);

    // Bowed string exciter - friction simulation (reduced gain)
    exciter = LFNoise1.ar(freq * 3) * bowVel * 0.3;
    exciter = exciter + (Saw.ar(freq * 0.99) * bowPress * 0.1);

    // String resonator - using comb filter for string model
    string = CombL.ar(exciter, 0.1, freq.reciprocal, coat.linexp(0, 1, 1, 4)) * 0.5;

    // Add harmonics based on grace (reduced)
    string = string + (SinOsc.ar(freq * 2) * grace * 0.15);
    string = string + (SinOsc.ar(freq * 3) * grace * 0.07);

    // Body resonance (warmth)
    body = BPF.ar(string, freq * coat.linexp(0, 1, 0.8, 1.5), 0.5) * coat;
    string = string + body;

    // Subtle expression vibrato
    string = string * (1 + (SinOsc.kr(5 + (gaze * 2)) * gaze * 0.05));

    // Grace brightness filter
    string = LPF.ar(string, grace.linexp(0, 1, 2000, 8000));

    // Gentle stereo
    sig = Pan2.ar(string, LFNoise1.kr(0.1) * 0.3);

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_noble loaded".postln;
