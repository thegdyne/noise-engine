SynthDef(\forge_seagrass_bay_manatee_call, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var chirp, squeak, warm, bend, echo;
    var modFreq, modIndex, carrier, bendMod, chirpMod, echoSig;

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
    chirp = In.kr(customBus0);      // Vocalization rate
    squeak = In.kr(customBus1);     // High harmonics
    warm = In.kr(customBus2);       // Body/fullness
    bend = In.kr(customBus3);       // Pitch inflection
    echo = In.kr(customBus4);       // Underwater resonance

    // Pitch bend - characteristic manatee pitch warble
    bendMod = SinOsc.kr(chirp.linexp(0, 1, 2, 8)) * bend * 0.08;
    freq = freq * (1 + bendMod);

    // Chirp modulation - vibrato-like
    chirpMod = SinOsc.kr(chirp.linexp(0, 1, 4, 15)) * chirp * 0.02;
    freq = freq * (1 + chirpMod);

    // FM synthesis for squeaky character
    modFreq = freq * squeak.linlin(0, 1, 1.5, 4);
    modIndex = squeak.linlin(0, 1, 0.5, 3);

    carrier = SinOsc.ar(freq + (SinOsc.ar(modFreq) * modFreq * modIndex));

    // Warmth - add fundamental and sub
    sig = carrier * (1 - (warm * 0.3));
    sig = sig + (SinOsc.ar(freq) * warm * 0.5);
    sig = sig + (SinOsc.ar(freq * 0.5) * warm * 0.2);

    // Echo - comb filter for underwater quality
    echoSig = CombL.ar(sig, 0.2, echo.linlin(0, 1, 0.02, 0.1), echo * 2);
    sig = sig + (echoSig * echo * 0.4);

    // Gentle stereo
    sig = ~stereoSpread.(sig, 0.3, 0.25);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_seagrass_bay_manatee_call loaded".postln;
