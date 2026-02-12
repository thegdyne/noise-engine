/*
Noise Engine - SuperCollider Initialization
Modular loader - each component in its own file
*/

// Guard: must be loaded from file, not copy-pasted into REPL
if (thisProcess.nowExecutingPath.isNil) {
    Error("NoiseEngine init.scd must be loaded from file (use Cmd+Enter on file, not copy-paste)").throw;
};

// Base path for loading files (needed before boot)
~basePath = PathName(thisProcess.nowExecutingPath).parentPath;

// Load central config
(~basePath +/+ "config.scd").load;

// Configure server options BEFORE booting
(
s.options.numAudioBusChannels = 512;     // Headroom for intermediate + FX routing
s.options.numControlBusChannels = 4096;  // ~420 used (buses + bus_unification 176)
s.options.memSize = 131072;              // 128MB — headroom for telemetry buffers
s.options.numBuffers = 8192;             // MOLTI-SAMP pool starts at 4000 (needs 4512+)
s.options.maxNodes = 4096;               // Headroom for crossmod + FX chains
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
    // Clock registry MUST load first (SSOT for 13 clock rates)
    (~basePath +/+ "core/clock_registry.scd").load;

    (~basePath +/+ "core/buses.scd").load;
    ~setupBuses.();

    // Load mod buses (before mod slots)
    (~basePath +/+ "core/mod_buses.scd").load;
    ~setupModBuses.();

    (~basePath +/+ "core/clock.scd").load;
    ~setupClock.();
    ~setupClockBroadcast.();

    (~basePath +/+ "core/helpers.scd").load;
    ~setupHelpers.();

    // Load channel strips (must be before helpers use them)
    (~basePath +/+ "core/channel_strips.scd").load;
    ~setupChannelStrips.();

    // Load FX mixer (sums dry + 4 returns)
    (~basePath +/+ "core/fx_mixer.scd").load;
    ~setupFxMixer.();

    // === FX SLOT SYSTEM (UI Refresh Phase 1) ===
    // Load canonical FX slot SynthDefs (must load before fx_slots.scd)
    (~basePath +/+ "effects/fx_empty.scd").load;
    (~basePath +/+ "effects/fx_echo.scd").load;
    (~basePath +/+ "effects/fx_reverb.scd").load;
    (~basePath +/+ "effects/fx_chorus.scd").load;
    (~basePath +/+ "effects/fx_lofi.scd").load;

    // Load FX Slot Manager
    (~basePath +/+ "core/fx_slots.scd").load;
    ~setupFxSlots.();

    // === LEGACY EFFECTS (still used for master inserts) ===
    // Load Heat (saturation) - master insert
    (~basePath +/+ "effects/heat.scd").load;
    ~setupHeat.();

    // Load Tape Echo (delay) - legacy, now also available via fx_slots
    (~basePath +/+ "effects/tape_echo.scd").load;
    ~setupTapeEcho.();

    // Load Reverb - legacy, now also available via fx_slots
    (~basePath +/+ "effects/reverb.scd").load;
    ~setupReverb.();

    // Load Dual Filter - master insert
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

    // Load cross-mod buses (provides ~getModSourceBus resolver)
    (~basePath +/+ "core/crossmod_buses.scd").load;
    ~setupCrossModBuses.();

    // NOTE: Legacy mod_apply_v2.scd and mod_routing.scd removed.
    // Generator modulation routes now use the unified bus system (bus_unification.scd).
    // Python sends routes via /noise/bus/route/set which queues to ~modRoutes.

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

    // Load end-stage processing (after helpers + bus_unification for ~multiFilter, ~envVCA, ~busRegistry)
    (~basePath +/+ "core/endstage.scd").load;
    ~setupEndstage.();

    // Load scope tap (after endstage SynthDef exists, before boot)
    (~basePath +/+ "core/scope_tap.scd").load;
    ~setupScopeTap.();

    // Load telemetry tap (development tool)
    (~basePath +/+ "core/telemetry_tap.scd").load;
    ~setupTelemetryTap.();

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

    // Load Step Engine SynthDef (setup deferred to post-boot, after ~startClock creates groups)
    (~basePath +/+ "core/step_engine.scd").load;

    // Load keyboard overlay OSC handlers (after midi_handler for ~triggerMidiGate, ~startMidiRetrig)
    (~basePath +/+ "core/keyboard_osc.scd").load;
    ~setupKeyboardOSC.();

    // Load audio device handler
    (~basePath +/+ "core/audio_device.scd").load;
    ~setupAudioDevice.();

    s.sync;

    // Start audio
    ~startClock.();

    // Boot step engine (after ~startClock creates ~genGroup, after s.sync compiles SynthDef)
    ~setupStepEngine.();

    // Boot end-stage infrastructure (after groups exist from ~startClock,
    // after ~setupEndstage defined SynthDefs, after bus_unification allocated buses)
    ~bootEndstageInfra.();

    // Boot scope tap (after endstage infra provides ~intermediateBus + groups)
    ~bootScopeTap.();
    ~setupScopeTapOSC.();

    // Boot telemetry tap (after endstage infra provides ~intermediateBus + ~generators)
    ~bootTelemetryTap.();

    // Boot hardware send (after telemetry tap, uses same ~intermediateBus)
    ~bootHardwareSend.();

    ~startFxMixer.();
    ~setupFxMixerOSC.();
    ~startFxSlots.();        // Initialize FX slots with default types
    ~setupFxSlotsOSC.();     // FX slot OSC handlers
    ~startMasterPassthrough.();
    ~startHeat.();
    ~setupHeatOSC.();
    // DISABLED: Legacy FX synths conflict with new FX slot system on slots 1-2
    // Both systems read/write same buses (~fx1SendBus/~fx1ReturnBus etc.)
    // causing duplicate processing. New slot system supersedes legacy.
    // See FX_HOTFIX_GUIDE_CONSOLIDATED.md for details. (2026-01-28)
    // ~startTapeEcho.();
    // ~setupTapeEchoOSC.();
    // ~startReverb.();
    // ~setupReverbOSC.();
    ~startDualFilter.();
    ~setupDualFilterOSC.();
    ~setupMasterOSC.();
    ~setupChannelMeterForward.();  // Forward channel levels to Python

    "".postln;
    "========================================".postln;
    "[x] Noise Engine ready!".postln;
    "[x] Core modules loaded".postln;
    "[x] End-stage infrastructure booted (8 slots)".postln;
    ("[x] " ++ ~generatorFiles.size ++ " core generators loaded").postln;
    if(~packGeneratorCount.notNil && (~packGeneratorCount > 0), {
        ("[x] " ++ ~packGeneratorCount ++ " pack generators loaded").postln;
    });
    "[x] Step engine ready (8 slots, clock-locked)".postln;
    "[x] 4 mod source slots ready".postln;
    "[x] 4 FX slots ready (UI Refresh)".postln;
    "[x] 8 cross-mod buses ready".postln;
    "[x] Scope tap ready (ping-pong v0.8.15, 1024 samples)".postln;
    "[x] Telemetry tap ready (dev tool)".postln;
    "[x] Hardware send ready (outputs 3-6)".postln;
    "[x] Boid modulation ready (via bus unification)".postln;
    ("[x] OSC listening on port " ++ ~scListenPort).postln;
    "========================================".postln;
    "".postln;
});
