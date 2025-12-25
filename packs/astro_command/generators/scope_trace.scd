// Scope Trace - Oscilloscope sweeps with electron beam character
// Role: motion (movement/texture)

SynthDef(\forge_astro_command_scope_trace, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var swp, bem, pho, wbl, syn;
    var sweepRate, sweep, beam, phosphor, wobble;
    var retrace, syncJitter;

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
    swp = In.kr(customBus0).linlin(0, 1, 0, 1);
    bem = In.kr(customBus1).linlin(0, 1, 0, 1);
    pho = In.kr(customBus2).linlin(0, 1, 0, 1);
    wbl = In.kr(customBus3).linlin(0, 1, 0, 1);
    syn = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Sweep rate derived from freq and swp param
    sweepRate = freq.linlin(20, 8000, 1, 50) * swp.linexp(0, 1, 0.5, 4);

    // Sync jitter - instability in trigger
    syncJitter = LFNoise1.kr(5).range(
        1 - ((1 - syn) * 0.1),
        1 + ((1 - syn) * 0.1)
    );

    // Main sweep - sawtooth with sync variations
    sweep = LFSaw.ar(sweepRate * syncJitter, 0);

    // Beam intensity modulation
    beam = sweep * bem * (1 + (LFNoise2.kr(10).range(-0.1, 0.1) * (1 - syn)));

    // Retrace click (flyback)
    retrace = EnvGen.ar(
        Env.perc(0.0001, 0.002),
        Impulse.ar(sweepRate * syncJitter)
    ) * HPF.ar(WhiteNoise.ar(1), 8000) * bem * 0.3;

    // Wobble - beam instability
    wobble = SinOsc.ar(
        sweepRate + (SinOsc.kr(wbl.linlin(0, 1, 0.5, 10)).range(-50, 50) * wbl)
    ) * wbl * 0.3;

    // Phosphor persistence - reverb-like tail using comb
    phosphor = CombL.ar(
        beam + retrace,
        0.5,
        pho.linlin(0, 1, 0.01, 0.2),
        pho.linlin(0, 1, 0.1, 1)
    ) * pho * 0.5;

    // High frequency CRT whine
    sig = beam + retrace + wobble + phosphor;
    sig = sig + (SinOsc.ar(15734) * bem * 0.02); // ~NTSC horizontal freq

    // Output chain
    sig = ~stereoSpread.(sig, 0.4, 0.4);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_scope_trace loaded".postln;
