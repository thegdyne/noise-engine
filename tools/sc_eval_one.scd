// tools/sc_eval_one.scd
// Usage:
//   sclang tools/sc_eval_one.scd /abs/path/to/preload.scd /abs/path/to/target.scd
// Or (no preload):
//   sclang tools/sc_eval_one.scd - /abs/path/to/target.scd
(
var args = thisProcess.argv;
var preload, target;

if(args.size < 2) { "NO_TARGET".postln; 1.exit; };

// If 2 args: [runner, target]
// If 3 args: [runner, preload, target]
if(args.size == 2) {
    preload = "-";
    target = args[1];
} {
    preload = args[1];
    target  = args[2];
};

try {
    ("EVAL_BEGIN\t" ++ target).postln;

    if(preload.notNil and: { preload != "-" } and: { preload.asString.size > 0 }) {
        ("PRELOAD_BEGIN\t" ++ preload).postln;
        preload.load;
        ("PRELOAD_OK\t" ++ preload).postln;
    };

    target.load;

    ("EVAL_OK\t" ++ target).postln;
    0.exit;

} { |err|
    ("EVAL_FAIL\t" ++ target).postln;

    // Robust error printing (reportError can itself fail sometimes)
    ("ERR_CLASS\t" ++ err.class.asString).postln;
    try { err.reportError } { |e| ("(reportError failed) " ++ e.asString).postln; };

    2.exit;
};
)
