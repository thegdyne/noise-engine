// Refract Hit - Sharp light refraction through a water sphere
// FM synthesis with pitch bend and spectral spread like a prism

SynthDef(\forge_dew_sphere_refract_hit, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bend, spread, focus, rainbow, snap;
    var bendEnv, modIndex, carrier, modulator;
    var rainbowMod, spreadSig;

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

    // Theme params
    bend = In.kr(customBus0);       // Pitch bend amount
    spread = In.kr(customBus1);     // Spectral spread
    focus = In.kr(customBus2);      // Beam focus
    rainbow = In.kr(customBus3);    // Harmonic color
    snap = In.kr(customBus4);       // Attack sharpness

    // Pitch bend envelope - quick downward bend simulating refraction
    bendEnv = EnvGen.ar(
        Env.perc(0.001, snap.linexp(0, 1, 0.3, 0.05)),
        Impulse.ar(0)
    ) * bend.linexp(0, 1, 1.01, 2.0);

    // FM modulation index - focus controls how complex
    modIndex = (1 - focus).linexp(0, 1, 1, 8);

    // Rainbow modulator - adds harmonic color
    rainbowMod = SinOsc.ar(freq * (2 + (rainbow * 3))) * rainbow * modIndex * 0.5;

    // Main FM pair
    modulator = SinOsc.ar(freq * 2 * bendEnv) * modIndex * freq;
    carrier = SinOsc.ar((freq * bendEnv) + modulator + rainbowMod);

    // Spectral spread - add detuned copies
    spreadSig = SinOsc.ar((freq * bendEnv * 1.01) + (modulator * 0.8)) * spread * 0.4;
    spreadSig = spreadSig + (SinOsc.ar((freq * bendEnv * 0.99) + (modulator * 0.9)) * spread * 0.4);

    sig = carrier + spreadSig;

    // Focus filtering - focused = narrower bandwidth
    sig = BPF.ar(sig, freq * bendEnv, focus.linexp(0, 1, 0.8, 0.2)) * focus;
    sig = sig + (carrier * (1 - focus) * 0.5);

    // Snap transient - click for sharp attack
    sig = sig + (HPF.ar(WhiteNoise.ar(0.5), 8000) * EnvGen.ar(Env.perc(0.0001, 0.005)) * snap);

    // Normalize
    sig = sig * 0.6;

    // Output chain
    sig = ~stereoSpread.(sig, 0.3, spread * 0.5);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_refract_hit loaded".postln;
