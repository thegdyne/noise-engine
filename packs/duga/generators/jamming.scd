SynthDef(\forge_duga_jamming, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bits, srate, dens, tone, chop;
    var noiseSig, toneSig, bitDepth, sampleRate, chopSig;

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
    bits = In.kr(customBus0);
    srate = In.kr(customBus1);
    dens = In.kr(customBus2);
    tone = In.kr(customBus3);
    chop = In.kr(customBus4);

    // Noise component - broadband interference
    noiseSig = WhiteNoise.ar(1) * (0.3 + (dens * 0.7));
    noiseSig = BPF.ar(noiseSig, freq * LFNoise0.kr(5).range(0.5, 2), 0.5);

    // Tonal component - jamming carriers
    toneSig = Pulse.ar(freq * LFNoise0.kr(2).range(0.9, 1.1), 0.5);
    toneSig = toneSig + Pulse.ar(freq * 1.5, 0.3) * 0.5;
    toneSig = toneSig * 0.4;

    // Mix tone and noise
    sig = (noiseSig * (1 - tone)) + (toneSig * tone);

    // Bitcrushing
    bitDepth = bits.linexp(0, 1, 16, 3);
    sampleRate = srate.linexp(0, 1, 44100, 2000);
    sig = Latch.ar(sig, Impulse.ar(sampleRate));
    sig = (sig * (2 ** bitDepth)).round / (2 ** bitDepth);

    // Signal chopping - less aggressive, always some signal
    chopSig = LFPulse.kr(chop.linexp(0, 1, 1, 20), 0, LFNoise0.kr(1).range(0.3, 0.7));
    sig = sig * (0.4 + (chopSig.lag(0.01) * 0.6));

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_jamming loaded".postln;
