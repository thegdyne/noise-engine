// CONCRETE - Textured movement, urban particles
// Family: texture (dust_resonator)
// Role: motion

SynthDef(\forge_barbican_hound_concrete, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var dust, echoAmt, grain, aged, patter;
    var impulses, resonated, reverb, patternMod;

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
    dust = In.kr(customBus0);     // Density
    echoAmt = In.kr(customBus1); // Reverberant
    grain = In.kr(customBus2);   // Particle size
    aged = In.kr(customBus3);    // Weathering
    patter = In.kr(customBus4);  // Rhythmic

    // Pattern modulation for rhythmic quality
    patternMod = LFPulse.kr(freq * 0.02 * (1 + patter), 0, 0.3 + (patter * 0.4)).lag(0.05);

    // Dust impulses - density affected by pattern
    impulses = Dust2.ar(dust.linexp(0, 1, 5, 80) * (1 + (patternMod * patter)));

    // Grain size affects exciter character
    impulses = impulses * grain.linexp(0, 1, 0.5, 2);
    impulses = LPF.ar(impulses, grain.linexp(0, 1, 8000, 2000));

    // Resonator bank - tuned to frequency (reduced gains)
    resonated = Mix([
        Ringz.ar(impulses, freq * 0.5, echoAmt.linexp(0, 1, 0.05, 0.5)) * 0.15,
        Ringz.ar(impulses, freq, echoAmt.linexp(0, 1, 0.03, 0.3)) * 0.4,
        Ringz.ar(impulses, freq * 1.5, echoAmt.linexp(0, 1, 0.02, 0.2)) * 0.2,
        Ringz.ar(impulses, freq * 2.3, echoAmt.linexp(0, 1, 0.01, 0.1)) * 0.1
    ]);

    // Aged weathering - add noise layer
    resonated = resonated + (BPF.ar(impulses, freq * 3, 0.5) * aged * 0.3);

    // Echo/reverb - comb filter simulation
    reverb = CombL.ar(resonated, 0.3, echoAmt.linexp(0, 1, 0.05, 0.2), echoAmt.linexp(0, 1, 0.1, 1));
    sig = resonated + (reverb * echoAmt * 0.4);

    // Aged filtering
    sig = LPF.ar(sig, aged.linexp(0, 1, 8000, 3000));

    // Soft limit peaks
    sig = (sig * 0.7).tanh;

    // DC removal for dust sources
    sig = LeakDC.ar(sig);

    // Stereo spread
    sig = Pan2.ar(sig, LFNoise1.kr(0.3) * 0.6);

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_concrete loaded".postln;
