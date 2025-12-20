// imaginarium_verify_contract.scd
// Phase 0: Generator Contract Verification for Imaginarium
//
// Bootstraps Noise Engine context, verifies helpers + contract, emits sentinel.
// Boot timeout guarantees sentinel emission even if server hangs.
//
// Run: sclang scripts/imaginarium_verify_contract.scd
//
// SENTINEL TOKENS:
//   IMAGINARIUM_VERIFY_OK   - all checks passed
//   IMAGINARIUM_VERIFY_FAIL - one or more checks failed

(
"".postln;
"== Imaginarium Phase 0: Generator Contract Verification ==".postln;
"".postln;

var errors = 0;
var warnings = 0;
var bootTimedOut = false;

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
        thisProcess.exit(1);
    } {
        if(warnings > 0) {
            ("Warnings: " ++ warnings).postln;
        };
        "All checks passed".postln;
        "".postln;
        "IMAGINARIUM_VERIFY_OK".postln;
        thisProcess.exit(0);
    };
};

// ============================================================
// 0) BOOTSTRAP: Load Noise Engine context
// ============================================================
"[0/6] Bootstrapping Noise Engine context...".postln;

// Derive repo path from script location: scripts/../ = repo
var scriptPath = PathName(thisProcess.nowExecutingPath);
var repoPath = scriptPath.pathOnly.dirname;
var scPath = repoPath +/+ "supercollider";

("  Script: " ++ scriptPath.fullPath).postln;
("  Repo:   " ++ repoPath).postln;
("  SC dir: " ++ scPath).postln;

// Check if this is actually a Noise Engine repo
if(File.exists(scPath +/+ "init.scd").not) {
    "".postln;
    reportError.("Not a Noise Engine repo (missing supercollider/init.scd)");
    reportError.("Run from: noise-engine/scripts/");
    emitResult.();
};

// Set ~basePath as init.scd would
~basePath = scPath;

// Load core files in order
var coreFiles = [
    "core/buses.scd",
    "core/helpers.scd",
];

var loadedCore = true;
coreFiles.do { |file|
    var fullPath = scPath +/+ file;
    if(File.exists(fullPath)) {
        try {
            fullPath.load;
            ("  Loaded: " ++ file).postln;
        } { |err|
            reportError.("Failed to load " ++ file ++ ": " ++ err);
            loadedCore = false;
        };
    } {
        reportError.("Missing: " ++ file);
        loadedCore = false;
    };
};

if(loadedCore.not) {
    reportError.("Core bootstrap failed");
    emitResult.();
};

// ============================================================
// 1) Helper function availability
// ============================================================
"".postln;
"[1/6] Checking helper functions...".postln;

[
    [\ensure2ch,      { ~ensure2ch }],
    [\multiFilter,    { ~multiFilter }],
    [\envVCA,         { ~envVCA }],
    [\stereoSpread,   { ~stereoSpread }],
].do { |pair|
    var name = pair[0];
    var fn = pair[1].value;
    if(fn.isNil) {
        reportError.("~" ++ name ++ " is nil");
    } {
        reportOK.("~" ++ name ++ " present");
    };
};

if(~startGenerator.notNil) {
    reportOK.("~startGenerator present");
} {
    reportWarn.("~startGenerator is nil (optional for contract test)");
};

// ============================================================
// 2) ~params[\amplitude] bus
// ============================================================
"".postln;
"[2/6] Checking ~params[\\amplitude]...".postln;

if(~params.isNil) {
    reportError.("~params is nil");
} {
    if(~params[\amplitude].isNil) {
        reportError.("~params[\\amplitude] is nil");
    } {
        if(~params[\amplitude].isNumber.not) {
            reportError.("~params[\\amplitude] is " ++ ~params[\amplitude].class ++ ", expected Number");
        } {
            reportOK.("~params[\\amplitude] = " ++ ~params[\amplitude] ++ " (bus index)");
        };
    };
};

// ============================================================
// 3) envEnabledBus documentation
// ============================================================
"".postln;
"[3/6] envEnabledBus documentation...".postln;
"  INFO: envEnabledBus is vestigial but REQUIRED in arglist".postln;
"  INFO: Actual envelope control via envSourceBus (0=OFF, 1=CLK, 2=MIDI)".postln;

// ============================================================
// 4) SynthDef compilation test
// ============================================================
"".postln;
"[4/6] Testing SynthDef compilation...".postln;

if(~ensure2ch.notNil && ~multiFilter.notNil && ~envVCA.notNil) {
    try {
        SynthDef(\imaginarium_contract_test, {
            |out,
             freqBus, cutoffBus, resBus, attackBus, decayBus,
             filterTypeBus, envEnabledBus, envSourceBus=0,
             clockRateBus, clockTrigBus,
             midiTrigBus=0, slotIndex=0,
             customBus0, customBus1, customBus2, customBus3, customBus4,
             seed=0|

            RandSeed.ir(1, seed);

            var freq = In.kr(freqBus);
            var filterFreq = In.kr(cutoffBus);
            var rq = In.kr(resBus);
            var attack = In.kr(attackBus);
            var decay = In.kr(decayBus);
            var filterType = In.kr(filterTypeBus);
            var envEnabled = In.kr(envEnabledBus);
            var envSource = In.kr(envSourceBus);
            var clockRate = In.kr(clockRateBus);
            var amp = In.kr(~params[\amplitude]);

            var sig = Saw.ar(freq) * 0.1;

            sig = ~stereoSpread.(sig, 0.3, 0.15);
            sig = ~multiFilter.(sig, filterType, filterFreq, rq);
            sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
            sig = ~ensure2ch.(sig);

            Out.ar(out, sig);
        }).add;

        reportOK.("SynthDef compiled (full contract + seed)");
    } { |err|
        reportError.("SynthDef compilation failed: " ++ err);
    };
} {
    reportError.("Skipping SynthDef test - helpers not loaded");
};

// ============================================================
// 5) Server boot with timeout
// ============================================================
"".postln;
"[5/6] Booting server for instantiation test...".postln;

// Hard timeout - guarantees sentinel emission
AppClock.sched(15.0, {
    if(bootTimedOut.not) {
        bootTimedOut = true;
        "".postln;
        reportError.("Server boot timeout (15s)");
        emitResult.();
    };
    nil;
});

// Actually start the boot (v6 fix - was missing in v5)
if(s.serverRunning.not) {
    s.boot;
};

s.waitForBoot({
    if(bootTimedOut) { nil } {
        // ============================================================
        // 6) Instantiation test
        // ============================================================
        "".postln;
        "[6/6] Testing Synth instantiation...".postln;

        Routine({
            var outBus = 0;

            var freqB = Bus.control(s, 1); freqB.set(220);
            var cutoffB = Bus.control(s, 1); cutoffB.set(2000);
            var resB = Bus.control(s, 1); resB.set(0.3);
            var attackB = Bus.control(s, 1); attackB.set(0.01);
            var decayB = Bus.control(s, 1); decayB.set(0.3);
            var ftB = Bus.control(s, 1); ftB.set(0);
            var envEnB = Bus.control(s, 1); envEnB.set(1);
            var envSrcB = Bus.control(s, 1); envSrcB.set(0);
            var clkRateB = Bus.control(s, 1); clkRateB.set(0);

            var clkTrigB = Bus.audio(s, 13);
            var midiTrigB = Bus.audio(s, 8);

            var custom = Array.fill(5, { Bus.control(s, 1) });
            custom.do(_.set(0.5));

            // Test without seed
            try {
                var synth1 = Synth(\imaginarium_contract_test, [
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

            // Test with seed
            try {
                var synth2 = Synth(\imaginarium_contract_test, [
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

            1.wait;
            emitResult.();
        }).play;
    };
});
)
