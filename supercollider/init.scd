/*
Noise Engine - SuperCollider Initialization
Modular loader - each component in its own file
*/

// Configure server options BEFORE booting
(
s.options.numAudioBusChannels = 256;  // Plenty of audio buses
s.options.numControlBusChannels = 4096;
s.options.memSize = 65536;  // More memory for buffers
);

s.waitForBoot({
    
    "".postln;
    "=== Noise Engine - SuperCollider ===".postln;
    "Initializing...".postln;
    "".postln;
    
    // Base path for loading files
    ~basePath = PathName(thisProcess.nowExecutingPath).parentPath;
    
    // Load core systems (order matters!)
    (~basePath +/+ "core/buses.scd").load;
    ~setupBuses.();
    
    (~basePath +/+ "core/clock.scd").load;
    ~setupClock.();
    
    (~basePath +/+ "core/helpers.scd").load;
    ~setupHelpers.();
    
    // Load effects
    (~basePath +/+ "effects/master_passthrough.scd").load;
    ~setupMasterPassthrough.();
    
    // Load generators (auto-load all .scd files)
    "Loading generators...".postln;
    ~generatorPath = ~basePath +/+ "generators/";
    ~generatorFiles = PathName(~generatorPath).files.select({ |f| f.extension == "scd" });
    ~generatorFiles.do({ |file|
        file.fullPath.load;
        ("  ✓ " ++ file.fileNameWithoutExtension).postln;
    });
    
    // Load OSC handlers (after everything else exists)
    (~basePath +/+ "core/osc_handlers.scd").load;
    ~setupOSC.();
    
    // Load MIDI handler
    (~basePath +/+ "core/midi_handler.scd").load;
    ~setupMIDI.();
    ~setupMIDIOSC.();
    
    s.sync;
    
    // Start audio
    ~startClock.();
    ~startMasterPassthrough.();
    
    "".postln;
    "========================================".postln;
    "✓ Noise Engine ready!".postln;
    "✓ Core modules loaded".postln;
    ("✓ " ++ ~generatorFiles.size ++ " generators available").postln;
    "========================================".postln;
    "".postln;
    "Listening for OSC on port 57120".postln;
});
