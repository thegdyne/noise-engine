// ============================================================================
// MOD BUS SNAPSHOT SYSTEM (v1.6.1 - WITH GUARDS)
// ============================================================================
//
// Purpose: Capture control-rate mod bus values at 50Hz for extended modulation
// Usage: ~setupModBusSnapshot.(); then ~snapshotModBuses.() in apply loop
//
// Part of: Mod Matrix Expansion (MOD_MATRIX_EXPANSION_SPEC_v1.6.1)
// ============================================================================

~modSnapshotBus = nil;
~modSnapshotSynth = nil;
~modBusSnapshot = Array.fill(16, { 0 });

// SynthDef: no env captures, no FreeSelf (persistent)
if(SynthDescLib.global.at(\modBusSnapshot).isNil) {
    SynthDef(\modBusSnapshot, { |outBus=0,
        in0=0, in1=0, in2=0, in3=0, in4=0, in5=0, in6=0, in7=0,
        in8=0, in9=0, in10=0, in11=0, in12=0, in13=0, in14=0, in15=0|
        var vals = [
            In.kr(in0),  In.kr(in1),  In.kr(in2),  In.kr(in3),
            In.kr(in4),  In.kr(in5),  In.kr(in6),  In.kr(in7),
            In.kr(in8),  In.kr(in9),  In.kr(in10), In.kr(in11),
            In.kr(in12), In.kr(in13), In.kr(in14), In.kr(in15)
        ];
        ReplaceOut.kr(outBus, vals);
    }).add;
    s.sync;
};

~setupModBusSnapshot = {
    // v1.6.1 GUARDS - prevent crashes if called too early
    if(~modBuses.isNil or: { ~modBuses.size < 16 }) {
        "ERROR: ~modBuses not ready (need 16)".warn;
        ^nil;
    };
    if(~modGroup.isNil) {
        "ERROR: ~modGroup not ready".warn;
        ^nil;
    };
    
    // Create snapshot output bus if needed
    if(~modSnapshotBus.isNil) {
        ~modSnapshotBus = Bus.control(s, 16);
    };
    
    // Free old synth if exists
    if(~modSnapshotSynth.notNil) {
        ~modSnapshotSynth.free;
        ~modSnapshotSynth = nil;
    };
    
    // Create new snapshot synth AFTER mod sources in signal chain
    ~modSnapshotSynth = Synth(\modBusSnapshot, [
        \outBus, ~modSnapshotBus.index,
        \in0,  ~modBuses[0].index,  \in1,  ~modBuses[1].index,
        \in2,  ~modBuses[2].index,  \in3,  ~modBuses[3].index,
        \in4,  ~modBuses[4].index,  \in5,  ~modBuses[5].index,
        \in6,  ~modBuses[6].index,  \in7,  ~modBuses[7].index,
        \in8,  ~modBuses[8].index,  \in9,  ~modBuses[9].index,
        \in10, ~modBuses[10].index, \in11, ~modBuses[11].index,
        \in12, ~modBuses[12].index, \in13, ~modBuses[13].index,
        \in14, ~modBuses[14].index, \in15, ~modBuses[15].index
    ], target: ~modGroup, addAction: \addAfter);
    
    "Mod bus snapshot system ready".postln;
};

~snapshotModBuses = {
    // Synchronous read of all 16 mod buses
    var vals = ~modSnapshotBus.getnSynchronous(16);
    16.do { |i| ~modBusSnapshot[i] = vals[i] };
};

"Mod snapshot system loaded".postln;
