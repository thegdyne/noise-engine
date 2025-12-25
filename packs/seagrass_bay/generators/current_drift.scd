SynthDef(\forge_seagrass_bay_current_drift, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flow, width, tumble, pressure, eddy;
    var noiseBase, flowMod, tumbleMod, pressureWave, eddySwirl, sigL, sigR;

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
    flow = In.kr(customBus0);       // Current rate
    width = In.kr(customBus1);      // Stereo width
    tumble = In.kr(customBus2);     // Turbulence
    pressure = In.kr(customBus3);   // Pressure waves
    eddy = In.kr(customBus4);       // Swirling motion

    // Base noise - mix of pink (low rumble) and brown (very low)
    noiseBase = (PinkNoise.ar * 0.7) + (BrownNoise.ar * 0.3);

    // Flow modulation - slow sweeping filter
    flowMod = LFTri.kr(flow.linexp(0, 1, 0.05, 0.5)).range(0.3, 1);
    noiseBase = LPF.ar(noiseBase, freq * flowMod * 2);

    // Tumble - irregular bursts
    tumbleMod = LFNoise1.kr(tumble.linexp(0, 1, 0.5, 4)).range(0.5, 1);
    noiseBase = noiseBase * (1 - (tumble * 0.3) + (tumbleMod * tumble * 0.3));

    // Pressure waves - low frequency amplitude modulation
    pressureWave = SinOsc.kr(pressure.linexp(0, 1, 0.1, 0.8)).range(1 - (pressure * 0.2), 1);
    noiseBase = noiseBase * pressureWave;

    // Resonant peak at freq for tonal quality
    sig = BPF.ar(noiseBase, freq, 0.5) * 2;
    sig = sig + (noiseBase * 0.3);

    // Eddy - swirling stereo effect
    eddySwirl = LFTri.kr(eddy.linexp(0, 1, 0.1, 0.6));
    sigL = sig * (1 + (eddySwirl * eddy * 0.3));
    sigR = sig * (1 - (eddySwirl * eddy * 0.3));

    // Width control
    sig = [sigL, sigR];
    sig = (sig * width) + (Mix(sig) * (1 - width) * 0.5);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_seagrass_bay_current_drift loaded".postln;
