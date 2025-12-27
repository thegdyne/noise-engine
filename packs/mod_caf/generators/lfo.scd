// lfo: Slow modulation textures - wavering pulse
SynthDef(\forge_mod_caf_lfo, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rate, waveform, depth, cross, bleed;
    var lfo1, lfo2;

    // Theme params
    rate = In.kr(customBus0).linexp(0, 1, 0.05, 5);         // P1: LFO rate
    waveform = In.kr(customBus1).linlin(0, 1, 0, 1);        // P2: Waveform blend
    depth = In.kr(customBus2).linlin(0, 1, 0.2, 1);         // P3: Modulation depth
    cross = In.kr(customBus3).linlin(0, 1, 1, 1.5);         // P4: Cross modulation
    bleed = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);       // P5: Audio bleed

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

    // DSP: Two LFOs for modulation
    lfo1 = SinOsc.kr(rate);
    lfo2 = LFTri.kr(rate * cross);

    // Blend waveforms
    lfo1 = (lfo1 * (1 - waveform)) + (LFPulse.kr(rate, 0, 0.5) * 2 - 1 * waveform);

    // Audio-rate manifestation of LFO
    sig = SinOsc.ar(freq * (1 + (lfo1 * depth * 0.5))) * 0.3;
    sig = sig + (Pulse.ar(freq * (1 + (lfo2 * depth * 0.3)), 0.3 + (lfo1 * 0.2)) * 0.2);

    // LFO bleed into audio - clicking/thumping
    sig = sig + (SinOsc.ar(rate * 20) * bleed * lfo1.abs * 0.2);

    // Continuous sub
    sig = sig + (SinOsc.ar(freq * 0.5) * 0.15);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_lfo loaded".postln;
