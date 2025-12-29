SynthDef(\forge_kaiju_beats_boom, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var bits, rate, wow, hiss, bass;
    var source, crushed, tapeWow, tapeHiss;

    // Theme params
    bits = In.kr(customBus0);         // P1: Bit depth reduction
    rate = In.kr(customBus1);         // P2: Sample rate reduction
    wow = In.kr(customBus2);          // P3: Tape wow/flutter
    hiss = In.kr(customBus3);         // P4: Tape hiss amount
    bass = In.kr(customBus4);         // P5: Boombox bass boost

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
    ampVal = 0.2;

    // Tape wow - pitch modulation
    tapeWow = SinOsc.kr(0.3 + (LFNoise1.kr(0.1) * 0.2)) * wow * 0.03;

    // Source - thick saw/pulse combo for that boombox vibe
    source = Saw.ar(freq * (1 + tapeWow));
    source = source + Pulse.ar(freq * 0.5 * (1 + tapeWow), 0.5) * 0.7;
    source = source + SinOsc.ar(freq * (1 + tapeWow)) * 0.5;

    // Bass boost - subharmonic
    source = source + (SinOsc.ar(freq * 0.5) * bass * 0.6);

    // Bitcrushing
    crushed = source.round(2.pow(1 - (bits * 8)).max(0.001));

    // Sample rate reduction
    crushed = Latch.ar(crushed, Impulse.ar(SampleRate.ir * (0.1 + (rate.neg + 1) * 0.9)));

    // Tape hiss
    tapeHiss = HPF.ar(WhiteNoise.ar(hiss * 0.15), 2000);

    // Mix
    sig = crushed + tapeHiss;

    // Slight saturation for warmth
    sig = (sig * 1.5).tanh * 0.7;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_kaiju_beats_boom loaded".postln;
