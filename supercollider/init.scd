/*
Noise Engine - SuperCollider Initialization
Modular loader - each component in its own file
*/

// Base path for loading files (needed before boot)
~basePath = PathName(thisProcess.nowExecutingPath).parentPath;

// Load central config
(~basePath +/+ "config.scd").load;

// Configure server options BEFORE booting
(
s.options.numAudioBusChannels = 256;  // Plenty of audio buses
s.options.numControlBusChannels = 4096;
s.options.memSize = 65536;  // More memory for buffers
);

// === FORCE FIXED OSC PORT ===
// This ensures SC always listens on configured port
(
thisProcess.openUDPPort(~scListenPort);
("✓ OSC port forced to " ++ ~scListenPort).postln;
);

s.waitForBoot({
    
    "".postln;
    "=== Noise Engine - SuperCollider ===".postln;
    "Initializing...".postln;
    "".postln;
    
    // Load core systems (order matters!)
    (~basePath +/+ "core/buses.scd").load;
    ~setupBuses.();
    
    // Load mod buses (before mod slots)
    (~basePath +/+ "core/mod_buses.scd").load;
    ~setupModBuses.();
    
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
    
    // Load pack generators (scan packs/*/generators/)
    ~packGeneratorCount = 0;
    ~packsPath = ~basePath.dirname +/+ "packs/";
    if(File.exists(~packsPath), {
        "Loading pack generators...".postln;
        PathName(~packsPath).folders.do({ |packDir|
            var manifestPath = packDir.fullPath +/+ "manifest.json";
            var genPath = packDir.fullPath +/+ "generators/";
            
            // Only load if manifest exists and generators folder exists
            if(File.exists(manifestPath) && File.exists(genPath), {
                var packFiles = PathName(genPath).files.select({ |f| f.extension == "scd" });
                if(packFiles.size > 0, {
                    ("  Pack: " ++ packDir.folderName).postln;
                    packFiles.do({ |file|
                        file.fullPath.load;
                        ("    ✓ " ++ file.fileNameWithoutExtension).postln;
                    });
                    ~packGeneratorCount = ~packGeneratorCount + packFiles.size;
                });
            });
        });
    });
    
    // Load mod slots (after clock exists for ~clockTrigBus reference)
    (~basePath +/+ "core/mod_slots.scd").load;
    ~setupModSlots.();
    
    // Load mod SynthDefs
    (~basePath +/+ "core/mod_lfo.scd").load;
    (~basePath +/+ "core/mod_sloth.scd").load;
    
    // Load mod routing/apply system
    (~basePath +/+ "core/mod_apply_v2.scd").load;
    ~setupModApply.();
    
    // Sync to ensure \modApply SynthDef is registered before creating instances
    s.sync;
    
    // Initialize passthrough synths (must be after mod_apply and mod_slots)
    ~initPassthroughs.();
    
    // Load mod routing OSC handlers (depends on mod_apply)
    (~basePath +/+ "core/mod_routing.scd").load;
    ~setupModRouting.();
    
    // Load OSC handlers (after everything else exists)
    (~basePath +/+ "core/osc_handlers.scd").load;
    ~setupOSC.();
    
    // Load mod OSC handlers
    (~basePath +/+ "core/mod_osc.scd").load;
    ~setupModOSC.();
    
    // Load MIDI handler
    (~basePath +/+ "core/midi_handler.scd").load;
    ~setupMIDI.();
    ~setupMIDIOSC.();
    
    // Load audio device handler
    (~basePath +/+ "core/audio_device.scd").load;
    ~setupAudioDevice.();
    
    s.sync;
    
    // Start audio
    ~startClock.();
    ~startMasterPassthrough.();
    ~setupMasterOSC.();
    ~setupChannelMeterForward.();  // Forward channel levels to Python
    
    // Second sync + re-register channel strip handlers to fix timing issue
    s.sync;
    OSCdef(\genVolume).free;
    OSCdef(\genMute).free;
    OSCdef(\genSolo).free;
    OSCdef(\genGain).free;
    OSCdef(\genPan).free;
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
    OSCdef(\genGain, { |msg|
        var slot = msg[1].asInteger;
        var gainDb = msg[2].asInteger;
        var gainLinear = (10 ** (gainDb / 20));
        var idx = slot - 1;
        ~stripGainState[idx] = gainLinear;
        if(~channelStrips[idx].notNil, {
            ~channelStrips[idx].set(\gain, gainLinear);
        });
    }, '/noise/gen/gain');
    OSCdef(\genPan, { |msg|
        var slot = msg[1].asInteger;
        var pan = msg[2].asFloat.clip(-1, 1);
        var idx = slot - 1;
        ~stripPanState[idx] = pan;
        if(~channelStrips[idx].notNil, {
            ~channelStrips[idx].set(\pan, pan);
        });
    }, '/noise/gen/pan');
    
    "".postln;
    "========================================".postln;
    "✓ Noise Engine ready!".postln;
    "✓ Core modules loaded".postln;
    ("✓ " ++ ~generatorFiles.size ++ " core generators loaded").postln;
    if(~packGeneratorCount.notNil && (~packGeneratorCount > 0), {
        ("✓ " ++ ~packGeneratorCount ++ " pack generators loaded").postln;
    });
    "✓ 4 mod source slots ready".postln;
    ("✓ OSC listening on port " ++ ~scListenPort).postln;
    "========================================".postln;
    "".postln;
});
