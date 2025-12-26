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
    var bendEnv, bendMul, modIndex, carrier, modulator;
    var rainbowMod, spreadSig;
    var trig;

    // Standard bus reads
    freq = In.kr(freqBus).clip(20, 20000);
    portamento = In.kr(portamentoBus).clip(0, 1);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus).clip(30, 18000);
    rq = In.kr(resBus).clip(0.05, 0.98);
    attack = In.kr(attackBus).clip(0.0005, 10);
    decay = In.kr(decayBus).clip(0.005, 30);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus).clip(0, 2);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]).clip(0, 1);

    // Theme params
    bend = In.kr(customBus0).clip(0, 1);
    spread = In.kr(customBus1).clip(0, 1);
    focus = In.kr(customBus2).clip(0, 1);
    rainbow = In.kr(customBus3).clip(0, 1);
    snap = In.kr(customBus4).clip(0, 1);

    // Trigger for pitch bend envelope (audio rate buses)
    trig = Select.ar(envSource.round.clip(0, 2), [
        Impulse.ar(0),  // OFF: single trigger at start
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Pitch bend envelope
    bendEnv = EnvGen.ar(
        Env.perc(0.001, snap.linexp(0, 1, 0.3, 0.05)),
        trig
    );
    bendMul = (bendEnv * bend).linexp(0, 1, 1.0, 0.5);

    // FM modulation index
    modIndex = (1 - focus).linexp(0, 1, 1, 8);

    // Rainbow modulator
    rainbowMod = SinOsc.ar(freq * (2 + (rainbow * 3))) * rainbow * modIndex * 0.5;

    // Main FM pair
    modulator = SinOsc.ar(freq * 2 * bendMul) * modIndex * 100;
    carrier = SinOsc.ar((freq * bendMul) + modulator + rainbowMod);

    // Spectral spread
    spreadSig = SinOsc.ar((freq * bendMul * 1.01) + (modulator * 0.8)) * spread * 0.4;
    spreadSig = spreadSig + (SinOsc.ar((freq * bendMul * 0.99) + (modulator * 0.9)) * spread * 0.4);

    sig = carrier + spreadSig;

    // Focus filtering
    sig = BPF.ar(sig, (freq * bendMul).clip(20, 20000), focus.linexp(0, 1, 0.8, 0.2)) * focus;
    sig = sig + (carrier * (1 - focus) * 0.5);

    // Snap transient
    sig = sig + (HPF.ar(WhiteNoise.ar(0.5), 8000) * EnvGen.ar(Env.perc(0.0001, 0.005), trig) * snap);

    // Normalize
    sig = sig * 0.2;

    // Safety
    sig = LeakDC.ar(sig);
    sig = HPF.ar(sig, 20);

    // Output chain
    sig = ~stereoSpread.(sig, 0.3, spread * 0.5);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    sig = Limiter.ar(sig, 0.95);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_refract_hit loaded".postln;