(
"serverRunning: %".format(s.serverRunning).postln;
"modBuses >= 16: %".format(~modBuses.notNil and: { ~modBuses.size >= 16 }).postln;
"SynthDef ok: %".format(SynthDescLib.global.at(\ne_mod_sauce_of_grav).notNil).postln;
)

(
// quick "movement per second" probe for RATE
// higher = more movement within the same wall-clock time
var slot = 0;        // 0..3
var lane = 0;        // 0..3
var secs = 10.0;
var hz = 40;         // sampling rate for this probe

var baseBus = slot * 4;

~probeMove = { |rateVal=0.1|
    Routine.run({
        var n = (secs * hz).asInteger;
        var prev, sum = 0.0;
        var i;

        ~modNodes[slot].set(\rate, rateVal);
        s.sync;
        0.2.wait;

        prev = ~modBuses[baseBus + lane].getSynchronous;

        n.do {
            var v = ~modBuses[baseBus + lane].getSynchronous;
            sum = sum + (v - prev).abs;
            prev = v;
            (1/hz).wait;
        };

        ("rate=% -> movement/sec=%"
            .format(rateVal, (sum / secs).round(0.001))).postln;
    });
};

~probeMove.(0.1);
SystemClock.sched(secs + 1.0, { ~probeMove.(1.0); nil });
)

(
var init   = "/Users/garethmillar/repos/noise-engine/supercollider/init.scd";
var sauce  = "/Users/garethmillar/repos/noise-engine/supercollider/core/mod_sauce_of_grav.scd";
var runner = "/Users/garethmillar/repos/noise-engine/tools/sauce_of_grav_test_v14_runner.scd";

["init exists", File.exists(init)].postln;
["sauce exists", File.exists(sauce)].postln;
["runner exists", File.exists(runner)].postln;
)

SystemClock.clear;
TempoClock.default.clear;
CmdPeriod.run;


(
// HARD reset (optional but recommended if you're already wedged)
CmdPeriod.run;
s.quit;

// New server opts
s = Server.local;
s.options.memSize = 262144;      // KB  (256 MB RT mem)  <-- main fix
s.options.maxNodes = 65536;      // node limit
s.options.numWireBufs = 256;     // control-rate wiring buffers
s.options.maxSynthDefs = 8192;   // synthdef limit
s.options.numBuffers = 4096;     // buffers (safe)
s.options.numAudioBusChannels = 1024;
s.options.numControlBusChannels = 8192;

s.boot;
)



(
var init   = "/Users/garethmillar/repos/noise-engine/supercollider/init.scd";
var sauce  = "/Users/garethmillar/repos/noise-engine/supercollider/core/mod_sauce_of_grav.scd";
var runner = "/Users/garethmillar/repos/noise-engine/tools/sauce_of_grav_test_v14_1_runner.scd";

SystemClock.clear;
TempoClock.default.clear;
CmdPeriod.run;

s.waitForBoot({
    "=== booted ===".postln;

    init.load;  s.sync;
    sauce.load; s.sync;
    runner.load;
});

if(s.serverRunning) {
    "Server already running - running immediately".postln;
    s.waitForBoot({}); // noop but keeps pattern consistent
} {
    s.boot;
};
)


"pkill tail".unixCmd;

~tailProcs.tryPerform(\do, { |p| p.tryPerform(\terminate) }); ~tailProcs = nil;

(
// 1) stop the Routine (if you stored it)
~tailRoutine.tryPerform(\stop);
~tailRoutine = nil;

// 2) terminate the Pipe (this actually kills `tail -f`)
~tailProc.tryPerform(\close);      // close the pipe
~tailProc.tryPerform(\terminate);  // terminate the process (safe even if nil/closed)
~tailProc = nil;

// 3) flush the post window line buffer (optional)
"--- tail stopped ---".postln;
)

(
~tailRoutine.tryPerform(\stop);
~tailRoutine = nil;

~tailProc.tryPerform(\close);
~tailProc.tryPerform(\terminate);
~tailProc = nil;

// nuke any tail -f watching your /tmp sauce logs
"pkill -f 'tail.*sauce_test'".unixCmd;
"pkill -f 'tail.*sauce_test_v14'".unixCmd;
"pkill -f 'tail.*sauce_test_v14_1'".unixCmd;

"--- killed tail processes matching sauce_test ---".postln;
)


(
~tailProc.tryPerform(\terminate);
~tailProc = Pipe.new("tail -n 80 -f /tmp/sauce_test_v14_1_slot1.txt", "r");

Routine({
    var line;
    while({ (line = ~tailProc.getLine).notNil }, { line.postln; });
}).play(AppClock);
)

"ls -lh /tmp | grep sauce_test | sort".unixCmd;


