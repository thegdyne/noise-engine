SynthDef(\forge_pripyat_radio, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tune, stat, bits, fade, voic;
    var carrier, staticSig, voiceSig, bitDepth, sampleRate, fadeMod, tuneDrift;

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

    // Custom params
    tune = In.kr(customBus0);
    stat = In.kr(customBus1);
    bits = In.kr(customBus2);
    fade = In.kr(customBus3);
    voic = In.kr(customBus4);

    // Tuning drift
    tuneDrift = LFNoise2.kr(tune.linexp(0, 1, 0.1, 2)).range(
        1 - (tune * 0.1),
        1 + (tune * 0.1)
    );

    // Fading signal strength
    fadeMod = LFNoise2.kr(fade.linexp(0, 1, 0.1, 1)).range(
        1 - (fade * 0.8),
        1
    );

    // Carrier tone - broken broadcast
    carrier = Pulse.ar(freq * tuneDrift, LFNoise2.kr(0.5).range(0.3, 0.7), 0.2);
    carrier = carrier + SinOsc.ar(freq * tuneDrift * 2, 0, 0.1);

    // Voice remnant - formant-like filtered noise
    voiceSig = BPF.ar(PinkNoise.ar(1), freq * LFNoise0.kr(3).range(1, 4), 0.2);
    voiceSig = voiceSig * LFPulse.kr(LFNoise0.kr(0.5).range(2, 8), 0, 0.6);
    voiceSig = voiceSig * voic * 0.4;

    // Mix carrier and voice
    sig = (carrier * (1 - (voic * 0.5))) + voiceSig;

    // Static interference
    staticSig = WhiteNoise.ar(1) * LFNoise2.kr(5).range(0, 1);
    staticSig = staticSig + (Dust.ar(100) * 0.3);
    staticSig = HPF.ar(staticSig, 500);
    sig = sig + (staticSig * stat * 0.3);

    // Bit crushing
    bitDepth = bits.linexp(0, 1, 16, 3);
    sampleRate = bits.linexp(0, 1, 44100, 4000);
    sig = Latch.ar(sig, Impulse.ar(sampleRate));
    sig = (sig * (2 ** bitDepth)).round / (2 ** bitDepth);

    // Apply fading
    sig = sig * fadeMod;

    // Bandpass for radio character
    sig = BPF.ar(sig, 1500, 1) * 2;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pripyat_radio loaded".postln;
