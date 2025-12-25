// Wave Crash - Explosive impact of water on basalt
// Noise burst with resonant impact and spray particles

SynthDef(\forge_drangarnir_wave_crash, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var force, spray, rock, foam, ring;
    var impact, spraySound, foamSound, resonance;

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
    force = In.kr(customBus0);
    spray = In.kr(customBus1);
    rock = In.kr(customBus2);
    foam = In.kr(customBus3);
    ring = In.kr(customBus4);

    // Main impact - broadband noise burst
    impact = WhiteNoise.ar(force);
    impact = impact * EnvGen.ar(Env.perc(0.001, force.linlin(0, 1, 0.1, 0.4)));
    impact = LPF.ar(impact, freq * 4);

    // Rock resonance - the surface being hit
    resonance = Mix.fill(3, { |i|
        var resFreq = freq * (1 + (i * rock * 0.5));
        var ringTime = ring.linlin(0, 1, 0.05, 0.5);
        Ringz.ar(impact * 0.3, resFreq, ringTime);
    });

    // Spray particles - high frequency sparkles
    spraySound = Dust2.ar(spray.linlin(0, 1, 100, 2000)) * 0.3;
    spraySound = HPF.ar(spraySound, 4000);
    spraySound = spraySound * EnvGen.ar(Env([0, 1, 0.3, 0], [0.01, 0.1, 0.3]));

    // Foam aftermath - filtered noise sustain
    foamSound = PinkNoise.ar(foam * 0.4);
    foamSound = BPF.ar(foamSound, LFNoise1.kr(2).range(500, 2000), 0.5);
    foamSound = foamSound * EnvGen.ar(Env([0, 0, 1, 0], [0.05, 0.2, foam.linlin(0, 1, 0.3, 1.5)]));

    // Combine
    sig = impact + resonance + spraySound + foamSound;

    // Add low thump for big impacts
    sig = sig + (SinOsc.ar(freq * 0.5) * EnvGen.ar(Env.perc(0.001, 0.1)) * force * 0.3);

    // Stereo spread
    sig = ~stereoSpread.(sig, 0.3, spray.linlin(0, 1, 0.2, 0.8));

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_wave_crash loaded".postln;
