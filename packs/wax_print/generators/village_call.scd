// ============================================================================
// WAX_PRINT: Village Call
// Role: Foreground - human voice, call and response
// 
// VOW (Vowel)    - Vowel shape morphing A-E-I-O-U
// CHT (Chant)    - Rhythmic chanting modulation
// CHR (Choir)    - Multiple voices, unison spread
// BRT (Breath)   - Breathiness, air in voice
// CRY (Cry)      - Emotional intensity, vibrato
// ============================================================================

SynthDef(\forge_wax_print_village_call, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var vowel, chant, choir, breath, cry;
    var vocalSource, formants, choirVoices;
    var vibrato, breathNoise;
    var f1, f2, f3;

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

    vowel = In.kr(customBus0).linlin(0, 1, 0.0, 4.0);
    chant = In.kr(customBus1).linexp(0, 1, 0.5, 8);
    choir = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    breath = In.kr(customBus3).linlin(0, 1, 0.0, 1.0);
    cry = In.kr(customBus4).linlin(0, 1, 0.0, 1.0);

    // Vibrato
    vibrato = SinOsc.kr(5 + (cry * 2)).range(1 - (cry * 0.02), 1 + (cry * 0.02));
    freq = freq * vibrato;

    // Chant modulation
    freq = freq * (1 + (SinOsc.kr(chant).range(-0.02, 0.02)));

    // Vocal source (pulse-like)
    vocalSource = Pulse.ar(freq, 0.3 + (breath * 0.2)) * 0.5;
    vocalSource = vocalSource + (Saw.ar(freq) * 0.3);

    // Choir voices (detuned unison)
    choirVoices = Pulse.ar(freq * 1.003, 0.35) * choir * 0.3;
    choirVoices = choirVoices + (Pulse.ar(freq * 0.997, 0.32) * choir * 0.3);
    choirVoices = choirVoices + (Saw.ar(freq * 1.005) * choir * 0.2);

    // Formant frequencies (A=0, E=1, I=2, O=3, U=4)
    f1 = Select.kr(vowel.round, [800, 400, 280, 450, 325]);
    f2 = Select.kr(vowel.round, [1200, 2000, 2250, 800, 700]);
    f3 = Select.kr(vowel.round, [2500, 2550, 2900, 2830, 2530]);

    // Formant filtering
    formants = Resonz.ar(vocalSource + choirVoices, f1, 0.1) * 2;
    formants = formants + (Resonz.ar(vocalSource + choirVoices, f2, 0.12) * 1.5);
    formants = formants + (Resonz.ar(vocalSource + choirVoices, f3, 0.15) * 0.8);

    // Breath noise
    breathNoise = PinkNoise.ar * breath * 0.2;
    breathNoise = BPF.ar(breathNoise, f1, 0.5);

    sig = formants + breathNoise;
    sig = (sig * 1.5).tanh * 0.5;

    sig = ~stereoSpread.(sig, 0.1, 0.3 * choir);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_wax_print_village_call loaded".postln;
