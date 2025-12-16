/*
Central Configuration for Noise Engine SuperCollider
All ports and shared settings in one place
*/

// === OSC PORTS ===
~scListenPort = 57120;     // Port SC listens on (Python sends here)
~pythonListenPort = 57121; // Port Python listens on (SC sends here)

// === AUDIO ===
~numGeneratorSlots = 8;    // Number of generator slots
~meterRate = 24;           // Metering updates per second (fps)

// === MOD SOURCES ===
// Clock source index (which channel of ~clockTrigBus to use)
// Index 12 = x32 clock (32 ticks per quarter note)
~modClockSourceIndex = 12;
// Ticks per LFO cycle - must match Python MOD_CLOCK_RATES order:
// /64=2048, /32=1024, /16=512, /8=256, /4=128, /2=64, 1=32, x2=16, x4=8, x8=4, x16=2, x32=1
~modClockTicksPerCycle = [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1];

// === Create Python address ===
~pythonAddr = NetAddr("127.0.0.1", ~pythonListenPort);

"✓ Config loaded: SC listens on %, Python on %".format(~scListenPort, ~pythonListenPort).postln;
