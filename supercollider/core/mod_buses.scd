/*
Mod Buses
Control buses for modulation sources (4 slots × 3 outputs = 12 buses)

SSOT: Bus count matches Python MOD_BUS_COUNT = 12
Index domains:
  - slot: 1-4 (1-indexed)
  - output: 0-2 (0-indexed: A/X=0, B/Y=1, C/Z=2)
  - bus: 0-11 (calculated: (slot-1)*3 + output)
*/

~setupModBuses = {
    "Setting up mod buses...".postln;
    
    // 12 control buses for mod outputs (4 slots × 3 outputs)
    ~modBuses = Array.fill(12, { Bus.control(s, 1).set(0) });
    
    // Helper to calculate bus index from slot and output
    // slot: 1-4, output: 0-2
    ~modBusIndex = { |slot, output|
        ((slot - 1) * 3) + output;
    };
    
    // Helper to get bus for slot/output
    ~modBus = { |slot, output|
        ~modBuses[~modBusIndex.(slot, output)];
    };
    
    // Zero all mod buses (used when switching to Empty)
    ~zeroModBuses = { |slot|
        3.do { |out|
            ~modBuses[~modBusIndex.(slot, out)].set(0);
        };
    };
    
    "  ✓ Mod buses ready (12 control buses)".postln;
};
