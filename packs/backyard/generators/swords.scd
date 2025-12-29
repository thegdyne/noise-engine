SynthDef(\forge_backyard_swords, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var force, wood, shield, clash, fury;
    var strikeRate, swordHit, shieldThud, clashRing, battleNoise;
    var exciter, pluck;

    // Theme params
    force = In.kr(customBus0);
    wood = In.kr(customBus1);
    shield = In.kr(customBus2);
    clash = In.kr(customBus3);
    fury = In.kr(customBus4);

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
    ampVal = In.kr(~params[\amplitude]);

    // Strike rate based on battle fury
    strikeRate = fury.linexp(0, 1, 1, 8);

    // Sword hit - Karplus-Strong wooden pluck
    exciter = Dust.ar(strikeRate) * force;
    exciter = exciter * (WhiteNoise.ar(1) * Decay.ar(Dust.ar(strikeRate), 0.008));
    pluck = Pluck.ar(
        exciter,
        Dust.ar(strikeRate),
        0.1,
        (freq * wood.linlin(0, 1, 0.8, 1.5)).reciprocal.clip(0.001, 0.1),
        wood.linlin(0, 1, 3, 12),
        wood.linlin(0, 1, 0.3, 0.6)
    );
    swordHit = pluck * 0.5;

    // Shield thud - low frequency impact
    shieldThud = Dust.ar(strikeRate * 0.5 * shield) * BrownNoise.ar(1);
    shieldThud = LPF.ar(shieldThud, 400);
    shieldThud = shieldThud * Decay.ar(Dust.ar(strikeRate * 0.5), 0.15);
    shieldThud = shieldThud * shield * 0.6;

    // Clash ring - higher pitched wood-on-wood
    clashRing = Dust.ar(strikeRate * clash);
    clashRing = Ringz.ar(clashRing * 0.3, freq * [2.5, 3.2, 4.1], [0.12, 0.08, 0.05]).sum;
    clashRing = clashRing * clash * 0.4;

    // Battle noise - breath and movement
    battleNoise = PinkNoise.ar(0.15);
    battleNoise = BPF.ar(battleNoise, 800, 0.5);
    battleNoise = battleNoise * LFNoise1.kr(fury.linlin(0, 1, 2, 8)).range(0.3, 1);
    battleNoise = battleNoise * (0.3 + (fury * 0.5));

    // Mix all components
    sig = swordHit + shieldThud + clashRing + battleNoise;

    // Add continuous bed for drone stability - battle ambience
    sig = sig + (BrownNoise.ar(0.08) + PinkNoise.ar(0.05));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_backyard_swords loaded".postln;
