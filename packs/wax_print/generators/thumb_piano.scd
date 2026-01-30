// wax_print/thumb_piano — Lightweight end-stage generator
// ============================================================================
// WAX_PRINT: Thumb Piano
// Role: Foreground - kalimba/mbira plucked tines
//
// TIN (Tine)     - Metal tine brightness
// BUZ (Buzz)     - Bottle cap buzz, traditional rattle
// BOX (Box)      - Resonating body size
// PLK (Pluck)    - Pluck intensity, attack
// DMP (Damp)     - Palm damping, decay control
// ============================================================================

SynthDef(\forge_wax_print_thumb_piano, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tine, buzz, box, pluck, damp;
    var tineOsc, buzzRattle, boxRes;
    var envTrig, pluckEnv;

    freq = In.kr(freqBus);

    tine = p[0].linlin(0, 1, 0.0, 1.0);
    buzz = p[1].linlin(0, 1, 0.0, 1.0);
    box = p[2].linexp(0, 1, 0.5, 2.0);
    pluck = p[3].linlin(0, 1, 0.3, 1.0);
    damp = p[4].linexp(0, 1, 0.1, 1.5);

    envTrig = Select.ar(envSource, [
        Impulse.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

    pluckEnv = EnvGen.ar(Env.perc(0.001, damp), envTrig);

    // Metal tine - Karplus-Strong style
    tineOsc = Pluck.ar(
        WhiteNoise.ar * pluck,
        envTrig,
        1/50,
        1/freq,
        damp * 5,
        0.3 + (tine * 0.4)
    );

    // Harmonic layer for brightness
    tineOsc = tineOsc + (SinOsc.ar(freq * 2) * pluckEnv * tine * 0.3);
    tineOsc = tineOsc + (SinOsc.ar(freq * 3) * pluckEnv * tine * 0.2);

    // Bottle cap buzz
    buzzRattle = Ringz.ar(envTrig * buzz * 0.5, freq * 8 * LFNoise0.kr(30).range(0.95, 1.05), 0.02);
    buzzRattle = buzzRattle + Ringz.ar(envTrig * buzz * 0.3, freq * 12, 0.015);
    buzzRattle = HPF.ar(buzzRattle, 2000);

    // Resonating box body
    boxRes = Ringz.ar(envTrig * 0.3, freq / box, 0.3);
    boxRes = boxRes + Ringz.ar(envTrig * 0.2, freq * 0.5 / box, 0.4);
    boxRes = LPF.ar(boxRes, 1000);

    sig = tineOsc + buzzRattle + boxRes;
    sig = (sig * 1.5).tanh * 0.6;

    sig = ~stereoSpread.(sig, 0.15, 0.25);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_wax_print_thumb_piano loaded".postln;
