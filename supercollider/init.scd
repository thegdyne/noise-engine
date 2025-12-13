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

// === FORCE FIXED OSC PORT ===
// This ensures SC always listens on 57120, regardless of session
// Critical for reliable Python <-> SC communication
(
~oscPort = 57120;
thisProcess.openUDPPort(~oscPort);
("✓ OSC port forced to " ++ ~oscPort).postln;
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
    
    // Load channel strips (must be before helpers use them)
    (~basePath +/+ "core/channel_strips.scd").load;
    ~setupChannelStrips.();
    
    // Load effects
    (~basePath +/+ "effects/master_passthrough.scd").load;
    ~setupMasterPassthrough.();
    
    // Load master section (metering, volume)
    (~basePath +/+ "core/master.scd").load;
    ~setupMaster.();
    
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
    ~setupMasterOSC.();
    
    "".postln;
    "========================================".postln;
    "✓ Noise Engine ready!".postln;
    "✓ Core modules loaded".postln;
    ("✓ " ++ ~generatorFiles.size ++ " generators available").postln;
    ("✓ OSC listening on port " ++ ~oscPort).postln;
    "========================================".postln;
    "".postln;
});
