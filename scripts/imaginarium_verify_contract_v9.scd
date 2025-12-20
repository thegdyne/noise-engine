// imaginarium_verify_contract_v9.scd
// Phase 0: Generator Contract Verification for Imaginarium
//
// Loads init.scd to bootstrap full Noise Engine context
//
// Run: sclang scripts/imaginarium_verify_contract_v9.scd
//
// SENTINEL TOKENS:
//   IMAGINARIUM_VERIFY_OK   - all checks passed
//   IMAGINARIUM_VERIFY_FAIL - one or more checks failed

(
var errors = 0;
var warnings = 0;
var bootTimedOut = false;
var scriptPath, repoPath, scPath, initPath;

var reportError = { |msg|
    ("FAIL: " ++ msg).postln;
    errors = errors + 1;
};

var reportOK = { |msg|
    ("OK: " ++ msg).postln;
};

var reportWarn = { |msg|
    ("WARN: " ++ msg).postln;
    warnings = warnings + 1;
};

var emitResult = {
    "".postln;
    "== VERIFICATION RESULT ==".postln;
    if(errors > 0) {
        ("Errors: " ++ errors).postln;
        "".postln;
        "IMAGINARIUM_VERIFY_FAIL".postln;
    } {
        if(warnings > 0) {
            ("Warnings: " ++ warnings).postln;
        };
        "All checks passed".postln;
        "".postln;
        "IMAGINARIUM_VERIFY_OK".postln;
    };
    // Schedule exit
    AppClock.sched(0.5, {
        if(errors > 0) { 1.exit } { 0.exit };
    });
};

var runChecks = {
    // ============================================================
    // 2) Check helpers
    // ============================================================
    "".postln;
    "[2/4] Checking helper functions...".postln;

    [
        [\ensure2ch,      { ~ensure2ch }],
        [\multiFilter,    { ~multiFilter }],
        [\envVCA,         { ~envVCA }],
        [\stereoSpread,   { ~stereoSpread }],
    ].do { |pair|
        var name, fn;
        name = pair[0];
        fn = pair[1].value;
        if(fn.isNil) {
            reportError.("~" ++ name ++ " is nil");
        } {
            reportOK.("~" ++ name ++ " present");
        };
    };

    // ============================================================
    // 3) Check ~params[\amplitude]
    // ============================================================
    "".postln;
    "[3/4] Checking ~params...".postln;

    if(~params.isNil) {
        reportError.("~params is nil");
    } {
        if(~params[\amplitude].isNil) {
            reportError.("~params[\\amplitude] is nil");
        } {
            // Can be Bus object or Number (bus index)
            if(~params[\amplitude].isKindOf(Bus)) {
                reportOK.("~params[\\amplitude] = Bus(" ++ ~params[\amplitude].index ++ ")");
            } {
                if(~params[\amplitude].isNumber) {
                    reportOK.("~params[\\amplitude] = " ++ ~params[\amplitude] ++ " (bus index)");
                } {
                    reportError.("~params[\\amplitude] is " ++ ~params[\amplitude].class ++ ", expected Bus or Number");
                };
            };
        };
    };

    // ============================================================
    // 4) SynthDef + instantiation test
    // ============================================================
    "".postln;
    "[4/4] Testing SynthDef compilation + instantiation...".postln;

    if(~ensure2ch.notNil && ~multiFilter.notNil && ~envVCA.notNil && ~params.notNil) {
        Routine({
            var synthDefAdded, synth1, synth2;
            var outBus, freqB, cutoffB, resB, attackB, decayB, ftB, envEnB, envSrcB, clkRateB;
            var clkTrigB, midiTrigB, custom;

            // Compile SynthDef
            try {
                SynthDef(\imaginarium_contract_test, {
                    |out,
                     freqBus, cutoffBus, resBus, attackBus, decayBus,
                     filterTypeBus, envEnabledBus, envSourceBus=0,
                     clockRateBus, clockTrigBus,
                     midiTrigBus=0, slotIndex=0,
                     customBus0, customBus1, customBus2, customBus3, customBus4,
                     seed=0|

                    var freq, filterFreq, rq, attack, decay, filterType, envEnabled, envSource, clockRate, amp, sig;

                    RandSeed.ir(1, seed);

                    freq = In.kr(freqBus);
                    filterFreq = In.kr(cutoffBus);
                    rq = In.kr(resBus);
                    attack = In.kr(attackBus);
                    decay = In.kr(decayBus);
                    filterType = In.kr(filterTypeBus);
                    envEnabled = In.kr(envEnabledBus);
                    envSource = In.kr(envSourceBus);
                    clockRate = In.kr(clockRateBus);
                    amp = In.kr(~params[\amplitude]);

                    sig = Saw.ar(freq) * 0.1;

                    sig = ~stereoSpread.(sig, 0.3, 0.15);
                    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
                    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
                    sig = ~ensure2ch.(sig);

                    Out.ar(out, sig);
                }).add;

                synthDefAdded = true;
                reportOK.("SynthDef compiled");
            } { |err|
                reportError.("SynthDef compilation failed: " ++ err);
                synthDefAdded = false;
            };

            s.sync;
            0.3.wait;

            if(synthDefAdded == true) {
                outBus = 0;
                freqB = Bus.control(s, 1); freqB.set(220);
                cutoffB = Bus.control(s, 1); cutoffB.set(2000);
                resB = Bus.control(s, 1); resB.set(0.3);
                attackB = Bus.control(s, 1); attackB.set(0.01);
                decayB = Bus.control(s, 1); decayB.set(0.3);
                ftB = Bus.control(s, 1); ftB.set(0);
                envEnB = Bus.control(s, 1); envEnB.set(1);
                envSrcB = Bus.control(s, 1); envSrcB.set(0);
                clkRateB = Bus.control(s, 1); clkRateB.set(0);
                clkTrigB = Bus.audio(s, 13);
                midiTrigB = Bus.audio(s, 8);
                custom = Array.fill(5, { Bus.control(s, 1) });
                custom.do(_.set(0.5));

                // Test without seed
                try {
                    synth1 = Synth(\imaginarium_contract_test, [
                        \out, outBus,
                        \freqBus, freqB.index, \cutoffBus, cutoffB.index, \resBus, resB.index,
                        \attackBus, attackB.index, \decayBus, decayB.index,
                        \filterTypeBus, ftB.index,
                        \envEnabledBus, envEnB.index, \envSourceBus, envSrcB.index,
                        \clockRateBus, clkRateB.index,
                        \clockTrigBus, clkTrigB.index, \midiTrigBus, midiTrigB.index,
                        \slotIndex, 0,
                        \customBus0, custom[0].index, \customBus1, custom[1].index,
                        \customBus2, custom[2].index, \customBus3, custom[3].index,
                        \customBus4, custom[4].index
                    ]);
                    0.1.wait;
                    synth1.free;
                    reportOK.("Instantiated WITHOUT seed");
                } { |err|
                    reportError.("Instantiation without seed: " ++ err);
                };

                0.1.wait;

                // Test with seed
                try {
                    synth2 = Synth(\imaginarium_contract_test, [
                        \out, outBus,
                        \freqBus, freqB.index, \cutoffBus, cutoffB.index, \resBus, resB.index,
                        \attackBus, attackB.index, \decayBus, decayB.index,
                        \filterTypeBus, ftB.index,
                        \envEnabledBus, envEnB.index, \envSourceBus, envSrcB.index,
                        \clockRateBus, clkRateB.index,
                        \clockTrigBus, clkTrigB.index, \midiTrigBus, midiTrigB.index,
                        \slotIndex, 0,
                        \customBus0, custom[0].index, \customBus1, custom[1].index,
                        \customBus2, custom[2].index, \customBus3, custom[3].index,
                        \customBus4, custom[4].index,
                        \seed, 123456
                    ]);
                    0.1.wait;
                    synth2.free;
                    reportOK.("Instantiated WITH seed");
                } { |err|
                    reportError.("Instantiation with seed: " ++ err);
                };

                // Cleanup
                [freqB, cutoffB, resB, attackB, decayB, ftB, envEnB, envSrcB, clkRateB, clkTrigB, midiTrigB].do(_.free);
                custom.do(_.free);
            };

            0.5.wait;
            emitResult.();
        }).play;
    } {
        reportError.("Skipping SynthDef test - helpers not loaded");
        emitResult.();
    };
};

"".postln;
"== Imaginarium Phase 0: Generator Contract Verification ==".postln;
"".postln;

// Derive repo path from script location
scriptPath = PathName(thisProcess.nowExecutingPath);
repoPath = scriptPath.pathOnly.dirname;
scPath = repoPath +/+ "supercollider";
initPath = scPath +/+ "init.scd";

("  Script: " ++ scriptPath.fullPath).postln;
("  Repo:   " ++ repoPath).postln;
("  SC dir: " ++ scPath).postln;
("  Init:   " ++ initPath).postln;

// Check if init.scd exists
if(File.exists(initPath).not) {
    "".postln;
    reportError.("Not a Noise Engine repo (missing supercollider/init.scd)");
    emitResult.();
};

"".postln;
"[1/4] Loading Noise Engine via init.scd...".postln;

// Hard timeout
AppClock.sched(30.0, {
    if(bootTimedOut.not) {
        bootTimedOut = true;
        "".postln;
        reportError.("Init timeout (30s)");
        emitResult.();
    };
    nil;
});

// Load init.scd - it handles everything including server boot
try {
    initPath.load;
    reportOK.("init.scd loaded");
} { |err|
    reportError.("Failed to load init.scd: " ++ err);
    emitResult.();
};

// Wait for init.scd to complete (it boots server and sets up everything)
s.waitForBoot({
    if(bootTimedOut) { nil } {
        // Give extra time for init.scd's internal setup
        Routine({
            1.0.wait;
            s.sync;
            runChecks.();
        }).play;
    };
});
)
