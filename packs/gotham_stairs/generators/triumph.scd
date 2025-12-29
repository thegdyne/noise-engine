SynthDef(\forge_gotham_stairs_triumph, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var power, spread, rise, dark, glory;
    var sawStack, subOsc, riseOsc, numSaws, detunes, pans;

    // Theme params
    power = In.kr(customBus0);
    spread = In.kr(customBus1);
    rise = In.kr(customBus2);
    dark = In.kr(customBus3);
    glory = In.kr(customBus4);

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

    // Rising motion - slow upward pitch drift
    freq = freq * (1 + (rise * SinOsc.kr(0.15).range(0, 0.1)));

    // Supersaw stack - detuned saw waves for massive sound
    numSaws = 7;
    detunes = [-0.12, -0.08, -0.04, 0, 0.04, 0.08, 0.12] * power.linlin(0, 1, 0.5, 2);
    pans = [-1, -0.6, -0.3, 0, 0.3, 0.6, 1] * spread;

    sawStack = Mix.fill(7, { |i|
        var sawFreq = freq * (1 + (detunes[i] * 0.01));
        var sawSig = Saw.ar(sawFreq);
        var panPos = pans[i];
        Pan2.ar(sawSig, panPos) * (0.15 / numSaws.sqrt)
    });

    // Sub oscillator for dark undertone
    subOsc = SinOsc.ar(freq * 0.5, 0, dark * 0.3);
    subOsc = subOsc + (Pulse.ar(freq * 0.5, 0.3) * dark * 0.15);

    // Glory harmonics - additional brightness
    riseOsc = Saw.ar(freq * 2) * glory * 0.1;
    riseOsc = riseOsc + (Pulse.ar(freq * 3, 0.2) * glory * 0.05);

    sig = sawStack + subOsc + riseOsc;

    // Power swell modulation
    sig = sig * (0.7 + (power * 0.3));

    // Slight chorus for extra width
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.5).range(0.01, 0.02)) * spread * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_gotham_stairs_triumph loaded".postln;
