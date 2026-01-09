(
// run_v14_suite.scd
// usage:
//   sclang run_v14_suite.scd /abs/path/to/mod_sauce_of_grav.scd /abs/path/to/sauce_test_v14.scd

var buildPath = thisProcess.argv.at(0);
var suitePath = thisProcess.argv.at(1);

var s = Server.default;
var repoRoot, initPath;

if(buildPath.isNil) {
    "ERROR: missing buildPath".postln;
    "usage: sclang run_v14_suite.scd /abs/mod_sauce_of_grav.scd /abs/sauce_test_v14.scd".postln;
    1.exit;
};

if(suitePath.isNil) {
    "ERROR: missing suitePath".postln;
    "usage: sclang run_v14_suite.scd /abs/mod_sauce_of_grav.scd /abs/sauce_test_v14.scd".postln;
    1.exit;
};

("RUN_SUITE build=" ++ buildPath).postln;
("RUN_SUITE suite=" ++ suitePath).postln;

// infer repo root from .../noise-engine/supercollider/core/...
repoRoot = PathName(buildPath).pathOnly;           // .../supercollider/core/
repoRoot = PathName(repoRoot).parentPath;         // .../supercollider/
repoRoot = PathName(repoRoot).parentPath;         // .../noise-engine/
initPath = repoRoot ++ "supercollider/init.scd";

("RUN_SUITE init=" ++ initPath).postln;

s.waitForBoot({
    // must exist for ~modBuses / ~clockTrigBus / ~clockBus etc
    initPath.load;
    s.sync;

    // load assembled mod file (defines SynthDef \ne_mod_sauce_of_grav)
    buildPath.load;
    s.sync;

    // load your v14 suite (your file schedules everything)
    suitePath.load;

    // ---- EXIT WHEN DONE ----
    // v14 sets: ~sauceDone[slot]=true in protect cleanup
    // Poll until all 4 slots done, then exit 0 if no FAIL lines found in logs.
    // (Your suite currently tracks pass/fail per run; we detect via log grep below in shell wrapper.)
    SystemClock.sched(2.0, {
        var allDone = true;
        if(~sauceDone.isNil) { allDone = false } {
            4.do { |i| if(~sauceDone[i] != true) { allDone = false } };
        };

        if(allDone) {
            "RUN_SUITE_DONE".postln;
            0.exit;
        }{
            2.0; // resched
        };
    });
});
)

