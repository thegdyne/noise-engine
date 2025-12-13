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
    
    // Load OSC handlers (will be called after s.sync)
    (~basePath +/+ "core/osc_handlers.scd").load;
    
    // Load MIDI handler
    (~basePath +/+ "core/midi_handler.scd").load;
    ~setupMIDI.();
    
    s.sync;
    
    // Start audio
    ~startClock.();
    ~startMasterPassthrough.();
    
    // Setup OSC handlers AFTER sync (ensures all buses/groups exist)
    ~setupOSC.();
    ~setupMIDIOSC.();
    ~setupMasterOSC.();
    
    // Second sync + re-register channel strip handlers to fix timing issue
    s.sync;
    OSCdef(\genVolume).free;
    OSCdef(\genMute).free;
    OSCdef(\genSolo).free;
    OSCdef(\genVolume, { |msg|
        var slot = msg[1].asInteger;
        var vol = msg[2].asFloat.clip(0, 1);
        if(~channelStrips[slot - 1].notNil, {
            ~channelStrips[slot - 1].set(\vol, vol);
        });
    }, '/noise/gen/volume');
    OSCdef(\genMute, { |msg|
        var slot = msg[1].asInteger;
        var muted = msg[2].asInteger;
        var idx = slot - 1;
        // Track mute state (persists across generator changes)
        ~stripMuteState[idx] = muted;
        if(~channelStrips[idx].notNil, {
            ~channelStrips[idx].set(\mute, muted);
        });
    }, '/noise/gen/mute');
    OSCdef(\genSolo, { |msg|
        var slot = msg[1].asInteger;
        var soloed = msg[2].asInteger;
        var idx = slot - 1;
        var oldSolo = ~stripSoloState[idx] ? 0;
        if(~channelStrips[idx].notNil, {
            ~stripSoloState[idx] = soloed;
            if(soloed == 1 && oldSolo == 0, { ~soloCount = ~soloCount + 1 });
            if(soloed == 0 && oldSolo == 1, { ~soloCount = ~soloCount - 1 });
            ~soloActive.set(if(~soloCount > 0, 1, 0));
            ~channelStrips[idx].set(\solo, soloed);
        });
    }, '/noise/gen/solo');
    
    "".postln;
    "========================================".postln;
    "✓ Noise Engine ready!".postln;
    "✓ Core modules loaded".postln;
    ("✓ " ++ ~generatorFiles.size ++ " generators available").postln;
    ("✓ OSC listening on port " ++ ~oscPort).postln;
    "========================================".postln;
    "".postln;
});
