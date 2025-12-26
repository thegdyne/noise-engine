// ============================================================================
// WAX_PRINT: Palm Strike
// Role: Accent - hand striking drum skin, djembe character
// 
// SKN (Skin)     - Membrane tension, pitch
// SLP (Slap)     - Edge slap vs center tone
// BOD (Body)     - Drum body resonance
// SIZ (Size)     - Drum diameter
// HND (Hand)     - Hand technique, finger articulation
// ============================================================================

SynthDef(\forge_wax_print_palm_strike, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var skin, slap, body, size, hand;
    var membrane, slapNoise, bodyRes;
    var envTrig, pitchEnv;

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

    skin = In.kr(customBus0).linexp(0, 1, 0.5, 2.0);
    slap = In.kr(customBus1).linlin(0, 1, 0.0, 1.0);
    body = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    size = In.kr(customBus3).linexp(0, 1, 1.5, 0.5);
    hand = In.kr(customBus4).linlin(0, 1, 0.0, 1.0);

    envTrig = Select.ar(envSource, [
        Impulse.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

    // Pitch drop on strike
    pitchEnv = EnvGen.ar(Env([2, 1, 0.9], [0.005, 0.1], [\exp, \lin]), envTrig);

    // Membrane modes
    membrane = SinOsc.ar(freq * skin * size * pitchEnv);
    membrane = membrane + (SinOsc.ar(freq * 1.6 * skin * size * pitchEnv) * 0.5);
    membrane = membrane + (SinOsc.ar(freq * 2.14 * skin * size * pitchEnv) * 0.3);
    membrane = membrane * EnvGen.ar(Env.perc(0.001, 0.3), envTrig);

    // Slap (high, sharp)
    slapNoise = WhiteNoise.ar * slap;
    slapNoise = HPF.ar(slapNoise, 2000);
    slapNoise = slapNoise * EnvGen.ar(Env.perc(0.001, 0.03 + (hand * 0.02)), envTrig);

    // Body resonance
    bodyRes = Ringz.ar(envTrig * 0.1, freq * 0.5 * size, 0.2) * body;
    bodyRes = LPF.ar(bodyRes, 300);

    sig = membrane + slapNoise + bodyRes;
    
    // Hand articulation adds subtle pitch variation
    sig = sig * (1 + (LFNoise1.kr(20).range(-0.02, 0.02) * hand));

    sig = (sig * 2).clip(-1, 1) * 0.6;

    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_wax_print_palm_strike loaded".postln;
