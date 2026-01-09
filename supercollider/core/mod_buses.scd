/*
Mod Buses
Control buses for modulation sources (4 slots x 4 outputs = 16 buses)

SSOT: Bus count matches Python MOD_BUS_COUNT = 16
Index domains:
  - slot: 1-4 (1-indexed)
  - output: 0-3 (0-indexed: A/X=0, B/Y=1, C/Z=2, D/R=3)
  - bus: 0-15 (calculated: (slot-1)*4 + output)
*/

~setupModBuses = {
    "Setting up mod buses...".postln;
    
    // 16 control buses for mod outputs (4 slots x 4 outputs)
    ~modBuses = Array.fill(16, { Bus.control(s, 1).set(0) });
    
    // Helper to calculate bus index from slot and output
    // slot: 1-4, output: 0-3
    ~modBusIndex = { |slot, output|
        ((slot - 1) * 4) + output;
    };
    
    // Helper to get bus for slot/output
    ~modBus = { |slot, output|
        ~modBuses[~modBusIndex.(slot, output)];
    };
    
    // Zero all mod buses (used when switching to Empty)
    ~zeroModBuses = { |slot|
        4.do { |out|
            ~modBuses[~modBusIndex.(slot, out)].set(0);
        };
    };
    
    "  [x] Mod buses ready (16 control buses)".postln;
};
