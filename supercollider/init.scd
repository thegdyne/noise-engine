/*
Noise Engine - SuperCollider Initialization
Modular loader - each component in its own file
*/

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
    
    // Load generators
    "Loading generators...".postln;
    (~basePath +/+ "generators/test_synth.scd").load;
    (~basePath +/+ "generators/pt2399_grainy.scd").load;
    
    // Load OSC handlers (after everything else exists)
    (~basePath +/+ "core/osc_handlers.scd").load;
    ~setupOSC.();
    
    s.sync;
    
    // Start audio
    ~startClock.();
    ~startMasterPassthrough.();
    
    "".postln;
    "========================================".postln;
    "✓ Noise Engine ready!".postln;
    "✓ Modules loaded:".postln;
    "    - core/buses".postln;
    "    - core/clock".postln;
    "    - core/helpers".postln;
    "    - core/osc_handlers".postln;
    "    - effects/master_passthrough".postln;
    "    - generators/test_synth".postln;
    "    - generators/pt2399_grainy".postln;
    "========================================".postln;
    "".postln;
    "Listening for OSC on port 57120".postln;
});
