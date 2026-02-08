/*
Audio Device Management
Handles device listing, selection, and switching
*/

~setupAudioDevice = {
    // Store current device
    ~currentAudioDevice = s.options.device ? "default";
    
    // Handler: Query available devices
    // Responds with device list to Python
    OSCdef(\audioDeviceList, { |msg|
        var devices = ServerOptions.devices;
        var current = s.options.device ? "default";

        // Send device count first, then each device name
        if(~pythonAddr.notNil) {
            ~pythonAddr.sendMsg('/noise/audio/devices/count', devices.size, current);
            devices.do { |dev, i|
                ~pythonAddr.sendMsg('/noise/audio/devices/item', i, dev);
            };
            ~pythonAddr.sendMsg('/noise/audio/devices/done');
        };

        ("  Audio devices: " ++ devices.size ++ " available").postln;
    }, '/noise/audio/devices/query');
    
    // Handler: Set audio device
    // This will reboot the server and reinitialize everything
    OSCdef(\audioDeviceSet, { |msg|
        var deviceName = msg[1].asString;
        var devices = ServerOptions.devices;
        
        if(devices.includesEqual(deviceName), {
            ("  Switching audio device to: " ++ deviceName).postln;
            ~currentAudioDevice = deviceName;
            
            // Set device and reboot
            s.options.device = deviceName;
            
            // Notify Python we're rebooting
            if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/audio/device/changing', deviceName); };
            
            // Schedule reboot and reinit
            fork {
                0.1.wait;
                s.reboot;
                s.waitForBoot {
                    // Reinitialize everything
                    "".postln;
                    "=== Audio Device Changed - Reinitializing ===".postln;
                    
                    // Reload core systems
                    ~setupBuses.();
                    ~setupClock.();
                    ~setupClockBroadcast.();
                    ~setupHelpers.();
                    ~setupChannelStrips.();
                    ~setupMasterPassthrough.();
                    ~setupMaster.();
                    ~setupOSC.();
                    ~setupMIDI.();
                    ~setupMIDIOSC.();
                    ~startClock.();  // This creates groups too
                    ~startMasterPassthrough.();
                    ~setupMasterOSC.();
                    ~setupChannelMeterForward.();  // Note: was misspelled as ~startChannelMeterForwarding
                    
                    "".postln;
                    ("[x] Audio device now: " ++ deviceName).postln;
                    "========================================".postln;
                    
                    // Notify Python we're ready
                    if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/audio/device/ready', deviceName); };
                };
            };
        }, {
            ("  ? Device not found: " ++ deviceName).postln;
            if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/audio/device/error', "Device not found: " ++ deviceName); };
        });
    }, '/noise/audio/device/set');
    
    "  [x] Audio device handlers ready".postln;
};
