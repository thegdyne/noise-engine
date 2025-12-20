// imaginarium_determinism_test_v9.scd
// NRT determinism test: same seed must produce identical output
//
// Uses TRand/Rand family (guaranteed to respect RandSeed)
//
// Usage: sclang scripts/imaginarium_determinism_test_v9.scd /path/out.wav 12345
//
// SENTINEL TOKENS:
//   IMAGINARIUM_DETERMINISM_OK   - render succeeded
//   IMAGINARIUM_DETERMINISM_FAIL - render failed

(
var args, outputPath, seed, synthDef, score;

args = thisProcess.argv;

// Debug: show what we got
("DEBUG: argv = " ++ args).postln;
("DEBUG: argv.size = " ++ args.size).postln;

if(args.size < 2) {
    "ERROR: Missing arguments".postln;
    "Usage: sclang imaginarium_determinism_test.scd <output.wav> <seed>".postln;
    "".postln;
    "IMAGINARIUM_DETERMINISM_FAIL".postln;
    2.exit;
};

outputPath = args[0];
seed = args[1].asInteger;

("Determinism test: seed=" ++ seed ++ " output=" ++ outputPath).postln;

// Build test SynthDef using TRand/Rand (guaranteed seeded)
synthDef = SynthDef(\imaginarium_determinism_test, { |out, seed=0|
    var trig, freq, amp, pan, vibRate, baseFreqOffset, vibrato, sig;
    
    RandSeed.ir(1, seed);
    
    // Impulse + TRand for guaranteed seeded randomness
    trig = Impulse.kr(50);
    
    freq = TRand.kr(200, 800, trig);
    amp = TRand.kr(0.3, 0.7, trig);
    pan = TRand.kr(-0.5, 0.5, trig);
    vibRate = TRand.kr(4, 8, trig);
    
    // Rand: initial random value (also seeded)
    baseFreqOffset = Rand(0.98, 1.02);
    
    vibrato = SinOsc.kr(vibRate).range(0.99, 1.01);
    sig = SinOsc.ar(freq * baseFreqOffset * vibrato) * amp;
    sig = Pan2.ar(sig, pan);
    sig = sig * EnvGen.ar(Env.linen(0.1, 0.8, 0.1), doneAction: 2);
    
    Out.ar(out, sig);
});

score = Score([
    [0.0, [\d_recv, synthDef.asBytes]],
    [0.0, [\s_new, \imaginarium_determinism_test, 1000, 0, 0, \seed, seed]],
    [1.0, [\c_set, 0, 0]]
]);

try {
    score.recordNRT(
        outputFilePath: outputPath,
        headerFormat: "WAV",
        sampleFormat: "int16",
        sampleRate: 48000,
        options: ServerOptions.new.numOutputBusChannels_(2),
        duration: 1.0,
        action: {
            ("NRT render complete: " ++ outputPath).postln;
            "".postln;
            "IMAGINARIUM_DETERMINISM_OK".postln;
            0.exit;
        }
    );
} { |err|
    ("NRT render failed: " ++ err).postln;
    "".postln;
    "IMAGINARIUM_DETERMINISM_FAIL".postln;
    1.exit;
};
)
