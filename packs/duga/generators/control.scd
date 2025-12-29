SynthDef(\forge_duga_control, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var hum, flkr, pwid, dead, dustAmt;
    var humSig, flickerMod, pulseSig, deadSig, dustSig;

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
    hum = In.kr(customBus0);
    flkr = In.kr(customBus1);
    pwid = In.kr(customBus2);
    dead = In.kr(customBus3);
    dustAmt = In.kr(customBus4);

    // Main pulse oscillator - dark hollow character
    pulseSig = Pulse.ar(freq, pwid.linlin(0, 1, 0.2, 0.8));
    pulseSig = pulseSig + Pulse.ar(freq * 0.5, 0.5) * 0.5;
    pulseSig = LPF.ar(pulseSig, freq * 3);

    // Electrical hum - 50Hz harmonics
    humSig = SinOsc.ar(50) + (SinOsc.ar(100) * 0.5) + (SinOsc.ar(150) * 0.25);
    humSig = humSig * hum * 0.15;

    // Fluorescent flicker modulation
    flickerMod = LFNoise2.kr(flkr.linexp(0, 1, 2, 15)).range(0.7, 1);
    flickerMod = flickerMod * LFPulse.kr(flkr.linexp(0, 1, 0.5, 8), 0, 0.9).range(0.8, 1);

    // Dead equipment - low rumble
    deadSig = LPF.ar(BrownNoise.ar(1), 100);
    deadSig = deadSig * dead * 0.2;

    // Dust particles
    dustSig = Dust.ar(dustAmt.linexp(0, 1, 0.5, 5)) * 0.1;
    dustSig = Ringz.ar(dustSig, freq * 4, 0.02);

    // Mix
    sig = (pulseSig * 0.3 * flickerMod) + humSig + deadSig + dustSig;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_control loaded".postln;
