(
// Noise Engine bootstrap (v0.2.3)
// Portable mode: opened directly by Run_NoiseEngine.command or tools/ne-run
// Hook mode: loaded from startup.scd (sets ~noiseEngineHook = true) -> disables autoPython
//
// FIXES:
// - Writes config/state under ~/Library/Application Support/NoiseEngine (NOT SuperCollider app support)
// - Default config sets autoPython:false + pythonCmd:nil (prevents double Python instances)
// - Keeps launchPython machinery (won’t run unless user enables it)
// - Makes ready.json device string nil-safe
// - Forces fixed sclang OSC listen port via thisProcess.openUDPPort (Python targets known port)
// - ready.json reports BOTH sclang port (sc_port) + scsynth port (scsynth_port)

var neVersion = "0.2.3";

var root, cfgDir, cfgPath, stateDir, readyPath;
var cfg, wantedDevice, devices, haveDevice;
var initPath, timeoutSec, writeReady;
var autoPython, pythonCmd;
var hookMode;
var writeReadyFile;
var launchPython;

// NEW
var scListenPort;

if (thisProcess.nowExecutingPath.isNil) {
    Error("NoiseEngine: must load bootstrap from file (nowExecutingPath is nil)").throw;
};

// ---- resolve root ----
// this file: <root>/supercollider/bootstrap/noise_engine_startup.scd
root = PathName(thisProcess.nowExecutingPath).pathOnly.dirname.dirname.standardizePath;

initPath = (root +/+ "supercollider" +/+ "init.scd").standardizePath;

// ---- config paths ----
// IMPORTANT: app-level support dir (matches tools/ne-run polling location)
cfgDir    = (Platform.userHomeDir +/+ "Library" +/+ "Application Support" +/+ "NoiseEngine").standardizePath;
cfgPath   = (cfgDir +/+ "config.scd").standardizePath;
stateDir  = (cfgDir +/+ "state").standardizePath;
readyPath = (stateDir +/+ "ready.json").standardizePath;

// ---- ensure dirs ----
File.mkdir(cfgDir);
File.mkdir(stateDir);

// ---- default config ----
cfg = (
    device: nil,
    bootTimeoutSec: 15,
    scListenPort: 57120,   // NEW: sclang OSC listen port (Python -> sclang OSCdefs)
    autoPython: false,     // default OFF (ne-run / .command launches python)
    pythonCmd: nil,        // user can enable later if desired
    writeReadyFile: true
);

// ---- load / create config ----
if (File.exists(cfgPath)) {
    try {
        cfg = cfgPath.load.value ? cfg;
    } { |e|
        "NoiseEngine: config read FAILED".warn;
        e.reportError;
    };
} {
    // portable-first defaults:
    // - autoPython false (avoid double Python when ne-run also starts Python)
    // - pythonCmd nil (user may opt-in later)
    File.use(cfgPath, "w", { |f|
        f.write("(\n");
        f.write("  device: nil,                 // e.g. \"MOTU M6\" (exact match)\n");
        f.write("  bootTimeoutSec: 15,\n");
        f.write("  scListenPort: 57120,          // sclang OSC listen port (Python -> sclang)\n");
        f.write("  autoPython: false,           // default OFF (ne-run / .command starts Python)\n");
        f.write("  pythonCmd: nil,              // opt-in: \"cd /path && ./tools/ne-py\" etc\n");
        f.write("  writeReadyFile: true\n");
        f.write(")\n");
    });
    ("NoiseEngine: wrote default config -> " ++ cfgPath).postln;

    // reload so defaults apply immediately
    try { cfg = cfgPath.load.value ? cfg } { |e| e.reportError };
};

// ---- hook mode flag ----
hookMode = (~noiseEngineHook == true);

// ---- apply config ----
wantedDevice = cfg[\device];
timeoutSec   = (cfg[\bootTimeoutSec] ? 15).asInteger.max(1);
autoPython   = (cfg[\autoPython] ? false) == true;
pythonCmd    = cfg[\pythonCmd];
writeReady   = (cfg[\writeReadyFile] ? true) != false;

// ---- FORCE FIXED sclang OSC PORT (language side) ----
// Must happen ASAP so external Python can always target a known port.
scListenPort = (cfg[\scListenPort] ? 57120).asInteger.max(1024);

try {
    thisProcess.openUDPPort(scListenPort);
    ("✓ OSC port forced to " ++ scListenPort ++ " (NetAddr.langPort=" ++ NetAddr.langPort ++ ")").postln;
} { |e|
    "NoiseEngine: openUDPPort FAILED".warn;
    e.reportError;
};

// In hook mode, never auto-launch python
if (hookMode) { autoPython = false; };

// ---- device selection (best-effort) ----
devices = ServerOptions.devices;
haveDevice = wantedDevice.notNil and: { devices.includes(wantedDevice) };

if (wantedDevice.notNil) {
    if (haveDevice) {
        s.options.device = wantedDevice;
        ("NoiseEngine: using audio device -> " ++ wantedDevice).postln;
    } {
        "NoiseEngine: requested device not found".warn;
        ("Wanted: " ++ wantedDevice).warn;
        "Available devices:".postln;
        devices.do(_.postln);
        "NoiseEngine: using default device".postln;
    };
} {
    "NoiseEngine: using default device".postln;
};

// ---- write ready.json ----
writeReadyFile = { |status|
    var ts, dev, port, synthPort, json;

    if (writeReady) {
        ts = Date.getDate.rawSeconds;
        dev = (s.options.device ? "default").asString;   // nil-safe

        // sclang receive port (what Python should target)
        port = NetAddr.langPort;

        // scsynth port (debug/info)
        synthPort = s.addr.port;

        json =
            "{\n"
            ++ "  \"status\": \"" ++ status ++ "\",\n"
            ++ "  \"ts\": " ++ ts.asString ++ ",\n"
            ++ "  \"sc_device\": " ++ dev.quote ++ ",\n"
            ++ "  \"sc_port\": " ++ port.asString ++ ",\n"
            ++ "  \"scsynth_port\": " ++ synthPort.asString ++ ",\n"
            ++ "  \"ne_version\": " ++ neVersion.quote ++ "\n"
            ++ "}\n";

        try {
            File.use(readyPath, "w", { |f| f.write(json) });
        } { |e|
            "NoiseEngine: ready.json write FAILED".warn;
            e.reportError;
        };
    };
};

// ---- launch python (delayed slightly to reduce race) ----
launchPython = {
    if (autoPython and: { pythonCmd.notNil }) {
        SystemClock.sched(0.5, {
            try {
                ("bash -lc " ++ pythonCmd.quote).unixCmd;
            } { |e|
                "NoiseEngine: python launch FAILED".warn;
                e.reportError;
            };
            nil;
        });
    };
};

// ---- boot timeout watchdog ----
SystemClock.sched(timeoutSec, {
    if (s.serverRunning.not) {
        "NoiseEngine: boot timeout".warn;
        writeReadyFile.("boot_timeout");
    };
    nil;
});

// ---- boot / reuse server, then init ----
if (s.serverRunning) {
    "NoiseEngine: server already running".postln;

    try { initPath.load } { |e|
        "NoiseEngine: init load FAILED".warn;
        e.reportError;
    };

    writeReadyFile.("ready");
    "NoiseEngine: READY".postln;

    launchPython.();

} {
    s.waitForBoot({
        ("NoiseEngine: server booted (" ++ (s.options.device ? "default").asString ++ ")").postln;

        try { initPath.load } { |e|
            "NoiseEngine: init load FAILED".warn;
            e.reportError;
        };

        writeReadyFile.("ready");
        "NoiseEngine: READY".postln;

        launchPython.();
    });

    s.boot;
};
)
