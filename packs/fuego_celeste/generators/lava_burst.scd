SynthDef(\forge_fuego_celeste_lava_burst, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var force, spray, glow, rock, sizzle;
    var burstNoise, rockThud, glowResonance, sizzleTail, sprayMod;

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

    // Theme parameters
    force = In.kr(customBus0);      // eruption intensity
    spray = In.kr(customBus1);      // scatter spread
    glow = In.kr(customBus2);       // molten brightness
    rock = In.kr(customBus3);       // impact weight
    sizzle = In.kr(customBus4);     // crackle tail

    // Explosion burst - filtered noise with sharp attack
    burstNoise = WhiteNoise.ar * force;
    burstNoise = BPF.ar(burstNoise, freq * 2, 0.8);
    burstNoise = burstNoise + (PinkNoise.ar * force * 0.5);

    // Rock impact - low frequency thud
    rockThud = SinOsc.ar(freq * 0.5) * rock;
    rockThud = rockThud + (LFPulse.ar(freq * 0.25, 0, 0.3) * rock * 0.5);
    rockThud = LPF.ar(rockThud, 200);

    // Glow resonance - bright harmonic ring
    glowResonance = Ringz.ar(
        Impulse.ar(0) * glow,
        [freq * 1.5, freq * 2, freq * 3],
        [0.3, 0.2, 0.15]
    ).sum * 0.3;
    glowResonance = HPF.ar(glowResonance, 400);

    // Sizzle tail - crackle and hiss
    sizzleTail = Crackle.ar(1.8) * sizzle * 0.3;
    sizzleTail = sizzleTail + (Dust.ar(sizzle.linexp(0, 1, 50, 500)) * 0.2);
    sizzleTail = HPF.ar(sizzleTail, 2000);

    // Mix all components
    sig = (burstNoise * 0.4) + (rockThud * 0.5) + glowResonance + sizzleTail;

    // Spray scatter - stereo spread modulation
    sprayMod = spray.linlin(0, 1, 0.1, 0.8);

    // Standard post-chain
    sig = ~stereoSpread.(sig, 0.5, sprayMod);
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_lava_burst loaded".postln;
