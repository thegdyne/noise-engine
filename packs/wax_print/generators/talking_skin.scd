// wax_print/talking_skin — Lightweight end-stage generator
// ============================================================================
// WAX_PRINT: Talking Skin
// Role: Motion - talking drum, pitch-bending communication
//
// TLK (Talk)     - Pitch bend range, speech-like movement
// SQZ (Squeeze)  - Tension change rate, how fast pitch moves
// TNG (Tongue)   - Articulation, syllable definition
// STK (Stick)    - Beater hardness, attack character
// SAY (Say)      - Phrase complexity, melodic contour
// ============================================================================

SynthDef(\forge_wax_print_talking_skin, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var talk, squeeze, tongue, stick, say;
    var membrane, pitchEnv, stickHit;
    var envTrig, talkMod;

    freq = In.kr(freqBus);

    talk = p[0].linlin(0, 1, 1.0, 2.5);  // Pitch bend ratio
    squeeze = p[1].linexp(0, 1, 0.5, 0.05);  // Bend time
    tongue = p[2].linlin(0, 1, 0.0, 1.0);
    stick = p[3].linlin(0, 1, 0.0, 1.0);
    say = p[4].linexp(0, 1, 0.5, 4);  // Phrase rate

    envTrig = Select.ar(envSource, [
        Impulse.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

    // Talk modulation - complex pitch phrase
    talkMod = LFNoise1.kr(say).range(1, talk);
    talkMod = Lag.kr(talkMod, squeeze);

    // Pitch envelope on each hit
    pitchEnv = EnvGen.ar(Env([talk, 1, 1.1, 1], [squeeze, 0.1, 0.2], [\exp, \lin, \lin]), envTrig);

    // Membrane oscillator
    membrane = SinOsc.ar(freq * pitchEnv * talkMod);
    membrane = membrane + (SinOsc.ar(freq * 1.5 * pitchEnv * talkMod) * 0.4);
    membrane = membrane + (SinOsc.ar(freq * 2.3 * pitchEnv * talkMod) * 0.2);
    membrane = membrane * EnvGen.ar(Env.perc(0.001, 0.4), envTrig);

    // Tongue articulation (quick pitch dips)
    membrane = membrane * (1 + (EnvGen.ar(Env([0, -0.1, 0], [0.01, 0.02]), envTrig) * tongue));

    // Stick attack
    stickHit = WhiteNoise.ar * stick * 0.3;
    stickHit = HPF.ar(stickHit, 1000 + (stick * 3000));
    stickHit = stickHit * EnvGen.ar(Env.perc(0.001, 0.02), envTrig);
    // Wood body click
    stickHit = stickHit + (Ringz.ar(envTrig * stick * 0.2, 800, 0.01));

    sig = membrane + stickHit;
    sig = (sig * 2).tanh * 0.5;

    sig = ~stereoSpread.(sig, 0.15, 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_wax_print_talking_skin loaded".postln;
