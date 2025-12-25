SynthDef(\forge_block_walk_porch_organ, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var drawbar, rotary, grit, warmth, spread;
    var fundamental, second, third, fourth, fifth, sixth;
    var rotaryRate, rotaryDepth, rotaryL, rotaryR, sigL, sigR;

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
    drawbar = In.kr(customBus0);    // Harmonic blend
    rotary = In.kr(customBus1);     // Leslie speed
    grit = In.kr(customBus2);       // Tube overdrive
    warmth = In.kr(customBus3);     // Sub emphasis
    spread = In.kr(customBus4);     // Stereo width

    // Drawbar harmonics - Hammond registration style
    // Low drawbar = more fundamental, high = more upper harmonics
    fundamental = SinOsc.ar(freq * 0.5) * warmth.linlin(0, 1, 0.2, 0.6);  // Sub
    second = SinOsc.ar(freq) * (1 - (drawbar * 0.3));                      // 8'
    third = SinOsc.ar(freq * 2) * drawbar.linlin(0, 1, 0.3, 0.7);         // 4'
    fourth = SinOsc.ar(freq * 3) * drawbar.linlin(0, 1, 0.1, 0.5);        // 2 2/3'
    fifth = SinOsc.ar(freq * 4) * drawbar.linlin(0, 1, 0.1, 0.4);         // 2'
    sixth = SinOsc.ar(freq * 6) * drawbar.linlin(0, 1, 0.05, 0.25);       // 1 1/3'

    sig = (fundamental + second + third + fourth + fifth + sixth) * 0.3;

    // Tube amp grit
    sig = sig * (1 + (grit * 2));
    sig = sig.tanh;
    sig = sig + (sig.clip2(0.3) * grit * 1.5);
    sig = LeakDC.ar(sig);

    // Rotary speaker effect
    rotaryRate = rotary.linexp(0, 1, 0.5, 7);
    rotaryDepth = rotary.linlin(0, 1, 0.1, 0.4);

    // Stereo rotary with spread control
    rotaryL = SinOsc.kr(rotaryRate, 0).range(1 - rotaryDepth, 1);
    rotaryR = SinOsc.kr(rotaryRate, pi).range(1 - rotaryDepth, 1);

    sigL = sig * rotaryL;
    sigR = sig * rotaryR;

    // Spread controls stereo width
    sig = [
        (sigL * spread.linlin(0, 1, 0.7, 1)) + (sigR * spread.linlin(0, 1, 0.3, 0)),
        (sigR * spread.linlin(0, 1, 0.7, 1)) + (sigL * spread.linlin(0, 1, 0.3, 0))
    ];

    // Slight pitch wobble from rotary
    sig = DelayC.ar(sig, 0.01, SinOsc.kr(rotaryRate * 0.97).range(0.001, 0.003 + (rotary * 0.003)));

    // Output chain (already stereo)
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_block_walk_porch_organ loaded".postln;
