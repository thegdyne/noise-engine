(
// prove_runner.scd
// usage:
//   sclang prove_runner.scd /absolute/path/to/build_or_section_file.scd

var buildPath = thisProcess.argv.at(0);
var s = Server.default;
var x;
var busIdxs = [0, 1, 2, 3];
var ok = true;

// finite test without isNaN/isInf
var isBad = { |v|
    if(v.isNil) { ^true };
    if(v.isNumber.not) { ^true };
    // NaN: v != v
    if(v != v) { ^true };
    // "Inf-ish": absurd magnitude
    if(v.abs > 1e12) { ^true };
    ^false
};

if(buildPath.isNil) {
    "ERROR: missing build file path. Usage: sclang prove_runner.scd /abs/path/to/file.scd".postln;
    ("argv = " ++ thisProcess.argv.asString).postln;
    1.exit;
};

("PROVE: " ++ buildPath).postln;

// ---------------------------------------------------------------------
// SERVER BOOT WITH HIGH-CAPACITY OPTIONS (required by test harness)
// ---------------------------------------------------------------------
s = Server.local;
Server.default = s;

// ensure options actually apply (must be set before boot)
if(s.serverRunning) {
    "PROVE: quitting existing server to apply new ServerOptions...".postln;
    s.quit;
    0.3.wait;
};

s.options.memSize = 262144;          // KB (256MB RT mem)
s.options.maxNodes = 65536;
s.options.numWireBufs = 256;
s.options.maxSynthDefs = 8192;
s.options.numBuffers = 4096;
s.options.numAudioBusChannels = 1024;
s.options.numControlBusChannels = 8192;

s.boot;

s.waitForBoot({

    buildPath.load; // must define SynthDef(\ne_mod_sauce_of_grav).add;
    s.sync;

    x = Synth(\ne_mod_sauce_of_grav, [
        \out1, 0, \out2, 1, \out3, 2, \out4, 3,
        \clockMode, 1, \rate, 0.3
    ]);

    s.sync;

    Routine({
        var resp;

        // reply to /c_get is /c_set [busIndex, value]
        resp = OSCFunc({ |msg|
            var idx = msg[1];
            var val = msg[2];
            if(isBad.(val)) {
                ("BAD BUS " ++ idx ++ " = " ++ val).postln;
                ok = false;
            };
        }, '/c_set', s.addr);

        // sample a few times
        3.do {
            busIdxs.do { |idx|
                s.sendMsg(\c_get, idx);
            };
            0.06.wait;
        };

        // cleanup
        x.free;
        0.05.wait;
        resp.free;

        (ok.if("PROVE_OK", "PROVE_FAIL")).postln;
        (ok.if(0, 1)).exit;
    }).play(SystemClock);

});
)
