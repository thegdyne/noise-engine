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
// Per-slot clock rate selection (replaces hardcoded ~modClockSourceIndex)
// Clock index buses allocated in mod_slots.scd (~modClkIdxBus)

// === Create Python address ===
~pythonAddr = NetAddr("127.0.0.1", ~pythonListenPort);

"[x] Config loaded: SC listens on %, Python on %".format(~scListenPort, ~pythonListenPort).postln;
