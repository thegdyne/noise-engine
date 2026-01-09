/*
Master Section - Volume Control OSC Handler
Metering is now integrated into masterPassthrough to avoid DC issues

See docs/MASTER_OUT.md for full roadmap
*/

~setupMaster = {
    "Setting up master section...".postln;
    
    // Master volume (linear, 0-1)
    ~masterVolume = 0.8;
    
    "  [x] Master section ready".postln;
};

// OSC handler for master volume
~setupMasterOSC = {
    // Master volume control
    OSCdef(\masterVolume, { |msg|
        var vol = msg[1].clip(0, 1);
        ~masterVolume = vol;
        
        // Update the master passthrough synth
        if (~masterEffects.notNil) {
            ~masterEffects.set(\masterVol, vol);
        };
    }, '/noise/master/volume');
    
    "  [x] Master OSC handlers ready".postln;
};
