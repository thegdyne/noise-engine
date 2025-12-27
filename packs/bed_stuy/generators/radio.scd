// radio: Boombox speaker - lo-fi blown driver
SynthDef(\forge_bed_stuy_radio, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var blown, bass, treble, static, battery;

    // Theme params
    blown = In.kr(customBus0).linlin(0, 1, 1, 4);           // P1: Blown speaker drive
    bass = In.kr(customBus1).linlin(0, 1, 0.3, 1);          // P2: Bass boost
    treble = In.kr(customBus2).linlin(0, 1, 1000, 6000);    // P3: Treble cutoff
    static = In.kr(customBus3).linlin(0, 1, 0, 0.3);        // P4: Static noise
    battery = In.kr(customBus4).linlin(0, 1, 0.95, 1.05);   // P5: Battery wobble

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

    // DSP: Base tone - slightly detuned
    sig = Saw.ar(freq * [1, 1.003] * LFNoise1.kr(0.2).range(battery.reciprocal, battery)) * 0.4;

    // Bass boost
    sig = sig + (SinOsc.ar(freq * 0.5) * bass * 0.3);

    // Blown speaker saturation
    sig = (sig * blown).tanh;

    // Speaker resonance - bandpass character
    sig = BPF.ar(sig, 800, 0.8) + (sig * 0.3);

    // Treble rolloff
    sig = LPF.ar(sig, treble);

    // Static noise
    sig = sig + (HPF.ar(WhiteNoise.ar(static), 2000) * LFNoise1.kr(0.5).range(0.5, 1));

    // Cabinet resonance
    sig = sig + (Ringz.ar(sig * 0.05, 150, 0.1));

    sig = sig * 0.4;

    // Output chain (with Limiter for saturation)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_radio loaded".postln;
