SynthDef(\forge_kaiju_beats_stomp, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var weight, punch, thud, rumble, width;
    var subOsc, pulseOsc, noiseHit;

    // Theme params
    weight = In.kr(customBus0);       // P1: Weight - sub content
    punch = In.kr(customBus1);        // P2: Punch - transient attack
    thud = In.kr(customBus2);         // P3: Thud - body thickness
    rumble = In.kr(customBus3);       // P4: Rumble - low frequency motion
    width = In.kr(customBus4);        // P5: Stereo width

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

    // Sub oscillator - sine for clean low end
    subOsc = SinOsc.ar(freq * 0.5);
    subOsc = subOsc * weight;

    // Add rumble modulation
    subOsc = subOsc * (1 + (LFNoise2.kr(0.5 + (rumble * 2)) * rumble * 0.3));

    // Pulse oscillator for body/thud
    pulseOsc = Pulse.ar(freq, 0.3 + (thud * 0.2));
    pulseOsc = pulseOsc + (Pulse.ar(freq * 0.5, 0.5) * 0.5);

    // Add saw for grit
    pulseOsc = pulseOsc + (LFSaw.ar(freq) * thud * 0.3);

    // Punch - noise transient
    noiseHit = LPF.ar(BrownNoise.ar(1), 200 + (punch * 300));
    noiseHit = noiseHit * punch * 0.4;

    // Mix
    sig = (subOsc * 0.6) + (pulseOsc * 0.5) + noiseHit;

    // Add stereo width via subtle detune
    sig = [
        sig + (SinOsc.ar(freq * 0.501) * width * 0.1),
        sig + (SinOsc.ar(freq * 0.499) * width * 0.1)
    ];

    // Soft saturation
    sig = (sig * 1.3).tanh * 0.8;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_kaiju_beats_stomp loaded".postln;
