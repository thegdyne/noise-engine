/*
Cross-Modulation Buses
8 control buses for generator-to-generator modulation

Source: Envelope follower on each generator's audio output
Output: Control rate signal in UNIPOLAR range (0 to 1)
        silence=0, loud=1 (differs from LFO/Sloth which are -1..+1)

Bus indices in mod system: 16-23 (after mod buses 0-15)

SSOT: CROSSMOD_BUS_OFFSET = 16, CROSSMOD_BUS_COUNT = 8
*/

~setupCrossModBuses = {
    "Setting up cross-mod buses...".postln;
    
    // Constants (SSOT - must match Python config)
    ~crossmodBusOffset = 16;  // First crossmod source ID
    ~crossmodBusCount = 8;    // One per generator slot
    
    // 8 control buses for cross-mod outputs
    // Output range: 0 to 1 (unipolar, silence=0, loud=1)
    ~crossModBus = Array.fill(8, { Bus.control(s, 1).set(0) });
    
    // Envelope follower parameters (per slot)
    ~crossModAttack = Array.fill(8, { 0.01 });   // Attack time in seconds
    ~crossModRelease = Array.fill(8, { 0.1 });   // Release time in seconds
    
    // Per-slot trim (mirrors ~stripTrimState for loudness normalization)
    ~crossModTrim = Array.fill(8, { 0.0 });  // dB
    
    // Follower synths (created when generator starts)
    ~crossModFollowers = Array.fill(8, { nil });
    
    // Cross-mod enabled state (per slot) - can disable per generator
    ~crossModEnabled = Array.fill(8, { true });
    
    // =====================================================
    // UNIFIED MOD SOURCE BUS RESOLVER (SSOT)
    // Used by mod_apply_v2 to get actual Bus for any source ID
    // =====================================================
    // sourceBus: 0-15 = mod buses, 16-23 = crossmod buses
    // Returns: Bus object (or nil if invalid)
    ~getModSourceBus = { |sourceBus|
        if(sourceBus < ~crossmodBusOffset) {
            // Standard mod bus (0-15)
            if(sourceBus >= 0 && sourceBus < ~modBuses.size) {
                ~modBuses[sourceBus];
            } {
                nil;
            };
        } {
            // Cross-mod bus (16-23)
            var idx = sourceBus - ~crossmodBusOffset;
            if(idx >= 0 && idx < ~crossmodBusCount) {
                ~crossModBus[idx];
            } {
                nil;
            };
        };
    };
    
    // Helper: get source ID for mod routing from slot number
    // slot: 1-8 (1-indexed)
    // returns: 16-23 (source ID for mod_apply_v2)
    ~crossModBusIndex = { |slot|
        ~crossmodBusOffset + slot - 1;  // slot 1 → 16, slot 8 → 23
    };
    
    // Helper: get actual bus for a slot (0-indexed internal)
    ~getCrossModBus = { |slot|
        var idx = slot - 1;
        if(idx >= 0 && idx < ~crossmodBusCount) {
            ~crossModBus[idx];
        } {
            nil;
        };
    };
    
    "  ✓ Cross-mod buses ready (8 control buses, source IDs 16-23)".postln;
    "  ✓ Unified mod source resolver (~getModSourceBus) ready".postln;
};
