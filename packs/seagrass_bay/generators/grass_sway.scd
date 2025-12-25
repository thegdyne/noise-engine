SynthDef(\forge_seagrass_bay_grass_sway, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sway, density, green, current, root;
    var blades, swayRate, currentMod, rootOsc;

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
    sway = In.kr(customBus0);       // Undulation rate
    density = In.kr(customBus1);    // Number of grass blades
    green = In.kr(customBus2);      // Brightness
    current = In.kr(customBus3);    // Water flow mod
    root = In.kr(customBus4);       // Low anchor

    // Sway rate
    swayRate = sway.linexp(0, 1, 0.05, 0.8);

    // Current adds random drift
    currentMod = LFNoise1.kr(0.2) * current * 0.015;

    // Multiple detuned "blades" swaying at different phases
    blades = Mix.fill(6, { |i|
        var detune, phase, swayMod, blade;
        detune = (i - 2.5) * density.linlin(0, 1, 0.002, 0.008);
        phase = i * 0.5;
        swayMod = SinOsc.kr(swayRate, phase) * 0.01 * sway;
        blade = Pulse.ar(
            freq * (1 + detune + swayMod + currentMod),
            0.3 + (SinOsc.kr(swayRate * 0.7, phase) * 0.15)
        );
        blade * (1 / 6);
    });

    // Green = brightness/harmonics
    sig = LPF.ar(blades, green.linexp(0, 1, 1500, 6000));

    // Root - sub oscillator anchor
    rootOsc = SinOsc.ar(freq * 0.5) * root * 0.4;
    sig = sig + rootOsc;

    // Gentle stereo
    sig = ~stereoSpread.(sig, swayRate, 0.4);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_seagrass_bay_grass_sway loaded".postln;
