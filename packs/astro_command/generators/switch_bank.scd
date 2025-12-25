// Switch Bank - Relay clicks, toggle sounds, mechanical control panel
// Role: accent (hits/stabs)

SynthDef(\forge_astro_command_switch_bank, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var clk, rly, arc, mtl, dst;
    var clickTrig, click, relay, spark, metal;
    var trigRate, clickFreq;

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

    // Custom params
    clk = In.kr(customBus0).linlin(0, 1, 0, 1);
    rly = In.kr(customBus1).linlin(0, 1, 0, 1);
    arc = In.kr(customBus2).linlin(0, 1, 0, 1);
    mtl = In.kr(customBus3).linlin(0, 1, 0, 1);
    dst = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Trigger rate based on density
    trigRate = dst.linexp(0, 1, 2, 30);
    clickTrig = Dust.ar(trigRate);

    // Click frequency influenced by main freq
    clickFreq = freq.linlin(20, 8000, 1000, 6000);

    // Click - sharp filtered noise burst
    click = HPF.ar(
        WhiteNoise.ar(1) * EnvGen.ar(
            Env.perc(0.0005, clk.linlin(0, 1, 0.002, 0.02)),
            clickTrig
        ),
        clickFreq
    ) * clk;

    // Relay buzz - short resonant burst
    relay = Ringz.ar(
        clickTrig,
        [120, 180, 240] + TRand.ar(-20, 20, clickTrig),
        rly.linlin(0, 1, 0.005, 0.03)
    ).sum * rly * 0.4;

    // Arc/spark - high frequency crackle
    spark = HPF.ar(
        Crackle.ar(arc.linlin(0, 1, 1.5, 1.95)) *
        EnvGen.ar(Env.perc(0.001, arc.linlin(0, 1, 0.01, 0.05)), Dust.ar(trigRate * 0.3)),
        6000
    ) * arc * 0.3;

    // Metallic panel resonance
    metal = Ringz.ar(
        clickTrig,
        [clickFreq * 0.8, clickFreq, clickFreq * 1.5],
        mtl.linlin(0, 1, 0.01, 0.1)
    ).sum * mtl * 0.3;

    // Combine all mechanical sounds
    sig = click + relay + spark + metal;

    // Output chain
    sig = ~stereoSpread.(sig, 0.5, 0.6);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_switch_bank loaded".postln;
