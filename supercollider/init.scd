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
("[x] OSC port forced to " ++ ~scListenPort).postln;
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

    // Load FX mixer (sums dry + returns)
    (~basePath +/+ "core/fx_mixer.scd").load;
    ~setupFxMixer.();

    // Load Heat (saturation)
    (~basePath +/+ "effects/heat.scd").load;
    ~setupHeat.();

    // Load Tape Echo (delay)
    (~basePath +/+ "effects/tape_echo.scd").load;
    ~setupTapeEcho.();

    // Load Reverb
    (~basePath +/+ "effects/reverb.scd").load;
    ~setupReverb.();

    // Load Dual Filter
    (~basePath +/+ "effects/dual_filter.scd").load;
    ~setupDualFilter.();

    // Load effects
    (~basePath +/+ "effects/master_passthrough.scd").load;
    ~setupMasterPassthrough.();

    // Load master section (metering, volume)
    (~basePath +/+ "core/master.scd").load;
    ~setupMaster.();

    // Load pack generators FIRST (so core can override any SynthDef name collisions)
    ~packGeneratorCount = 0;
    ~packsPath = ~basePath.dirname +/+ "packs/";
    if(File.exists(~packsPath), {
        "Loading pack generators...".postln;
        PathName(~packsPath).folders.do({ |packDir|
            var manifestPath, genPath;

            // Skip hidden directories (e.g., .git)
            if(packDir.folderName.beginsWith(".").not, {
                manifestPath = packDir.fullPath +/+ "manifest.json";
                genPath = packDir.fullPath +/+ "generators/";

                // Only load if manifest exists and generators folder exists
                if(File.exists(manifestPath) && File.exists(genPath), {
                    var packFiles = PathName(genPath).files.select({ |f| f.extension == "scd" });
                    if(packFiles.size > 0, {
                        ("  Pack: " ++ packDir.folderName).postln;
                        packFiles.do({ |file|
                            file.fullPath.load;
                            ("    [x] " ++ file.fileNameWithoutExtension).postln;
                        });
                        ~packGeneratorCount = ~packGeneratorCount + packFiles.size;
                    });
                });
            });
        });
    });

    // Load core generators AFTER packs (core wins on SynthDef name collisions)
    "Loading generators...".postln;
    ~generatorPath = ~basePath +/+ "generators/";
    ~generatorFiles = PathName(~generatorPath).files.select({ |f| f.extension == "scd" });
    ~generatorFiles.do({ |file|
        file.fullPath.load;
        ("  [x] " ++ file.fileNameWithoutExtension).postln;
    });

    // Load mod slots (after clock exists for ~clockTrigBus reference)
    (~basePath +/+ "core/mod_slots.scd").load;
    ~setupModSlots.();

    // Load mod SynthDefs
    (~basePath +/+ "core/mod_lfo.scd").load;
    (~basePath +/+ "core/mod_sloth.scd").load;
    (~basePath +/+ "core/mod_arseq_plus.scd").load;
    (~basePath +/+ "core/mod_sauce_of_grav.scd").load;

    // Load cross-mod buses BEFORE mod_apply (provides ~getModSourceBus resolver)
    (~basePath +/+ "core/crossmod_buses.scd").load;
    ~setupCrossModBuses.();

    // Load mod routing/apply system (uses ~getModSourceBus from crossmod_buses)
    (~basePath +/+ "core/mod_apply_v2.scd").load;
    ~setupModApply.();

    // Sync to ensure \modApply SynthDef is registered before creating instances
    s.sync;

    // Initialize passthrough synths (must be after mod_apply and mod_slots)
    ~initPassthroughs.();

    // Load mod routing OSC handlers (depends on mod_apply)
    (~basePath +/+ "core/mod_routing.scd").load;
    ~setupModRouting.();

    // Load cross-mod followers and OSC (after mod_apply)
    (~basePath +/+ "core/crossmod_followers.scd").load;
    ~setupCrossModFollowers.();
    (~basePath +/+ "core/crossmod_osc.scd").load;
    ~setupCrossModOSC.();

    // Load extended modulation system (mod matrix expansion)
    (~basePath +/+ "core/mod_snapshot.scd").load;
    ~setupModBusSnapshot.();
    (~basePath +/+ "core/ext_mod.scd").load;
    (~basePath +/+ "core/ext_mod_osc.scd").load;

    // Load Bus Unification (unified parameter control - replaces ext_mod)
    (~basePath +/+ "core/bus_unification.scd").load;
    ~setupBusUnification.();
    (~basePath +/+ "core/bus_unification_osc.scd").load;
    ~setupBusUnificationOSC.();
    ~startApplyTick.();  // Start the 500Hz apply loop

    // NOTE: Boid modulation handled by bus_unification.scd (see bus_unification_osc.scd)

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

    // Load keyboard overlay OSC handlers
    (~basePath +/+ "core/keyboard_osc.scd").load;

    // Load audio device handler
    (~basePath +/+ "core/audio_device.scd").load;
    ~setupAudioDevice.();

    s.sync;

    // Start audio
    ~startClock.();
    ~startFxMixer.();
    ~setupFxMixerOSC.();
    ~startMasterPassthrough.();
    ~startHeat.();
    ~setupHeatOSC.();
    ~startTapeEcho.();
    ~setupTapeEchoOSC.();
    ~startReverb.();
    ~setupReverbOSC.();
    ~startDualFilter.();
    ~setupDualFilterOSC.();
    ~setupMasterOSC.();
    ~setupChannelMeterForward.();  // Forward channel levels to Python

    "".postln;
    "========================================".postln;
    "[x] Noise Engine ready!".postln;
    "[x] Core modules loaded".postln;
    ("[x] " ++ ~generatorFiles.size ++ " core generators loaded").postln;
    if(~packGeneratorCount.notNil && (~packGeneratorCount > 0), {
        ("[x] " ++ ~packGeneratorCount ++ " pack generators loaded").postln;
    });
    "[x] 4 mod source slots ready".postln;
    "[x] 8 cross-mod buses ready".postln;
    "[x] Boid modulation ready (via bus unification)".postln;
    ("[x] OSC listening on port " ++ ~scListenPort).postln;
    "========================================".postln;
    "".postln;
});
