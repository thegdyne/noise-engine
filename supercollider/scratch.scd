/*
=== SUPERCOLLIDER SCRATCH PAD ===
Common commands for debugging and testing
Execute lines with Cmd+Return (Mac) or Ctrl+Return (Win/Linux)
*/

// ============================================================
// SERVER CONTROL
// ============================================================

s.boot;              // Start audio server
s.quit;              // Stop audio server
s.reboot;            // Restart server (clears everything)
s.freeAll;           // Stop all synths but keep server running

Server.killAll;      // Nuclear option - kill all SC servers


// ============================================================
// RELOAD PROJECT
// ============================================================

// Full reload (after making changes):
// 1. s.freeAll;
// 2. Open init.scd, Cmd+A, Cmd+Return


// ============================================================
// DEBUG - WHAT'S RUNNING?
// ============================================================

s.queryAllNodes;     // Show all running synths/groups

// Expected structure:
// NODE TREE Group 0
//    1 group
//       clockGroup
//          masterClock
//       genGroup
//          (generators here when active)
//       fxGroup
//          masterPassthrough

s.plotTree;          // Visual node tree (opens window)
s.meter;             // Show audio levels
s.scope;             // Oscilloscope


// ============================================================
// BUS INSPECTION
// ============================================================

// Check BPM bus value
~clockBus.get({ |val| ("BPM: " ++ val).postln });

// Check generator frequency bus (slot 1)
~genParams[1][\frequency].get({ |val| ("Gen1 freq: " ++ val).postln });

// Check envelope source (slot 1): 0=OFF, 1=CLK, 2=MIDI
~genParams[1][\envSource].get({ |val| ("Gen1 envSource: " ++ val).postln });

// Check all gen1 params
~genParams[1].keysValuesDo({ |k, v| v.get({ |val| (k ++ ": " ++ val).postln }) });


// ============================================================
// MANUAL GENERATOR CONTROL
// ============================================================

// Start a generator manually (bypassing Python)
~startGenerator.(1, \additive);      // Slot 1, additive synth
~startGenerator.(2, \subtractive);   // Slot 2, subtractive synth

// Stop a generator
~stopGenerator.(1);

// List available generator types
PathName(~generatorPath).files.do({ |f| f.fileName.postln });


// ============================================================
// MANUAL PARAMETER CHANGES
// ============================================================

// Set BPM
~clockBus.set(90);

// Set generator params (slot 1)
~genParams[1][\frequency].set(220);    // Hz
~genParams[1][\cutoff].set(2000);      // Hz
~genParams[1][\resonance].set(0.3);    // 0.001-1.0 (lower = more resonant)
~genParams[1][\attack].set(0.01);      // seconds
~genParams[1][\decay].set(0.5);        // seconds
~genParams[1][\envSource].set(1);      // 0=OFF, 1=CLK, 2=MIDI
~genParams[1][\clockRate].set(6);      // 0=/32 ... 6=CLK ... 12=x32

// Set custom param (slot 1, param 0)
~genParams[1][\custom][0].set(0.7);


// ============================================================
// MIDI DEBUGGING
// ============================================================

// List MIDI sources
MIDIClient.init;
MIDIClient.sources;

// Connect to first MIDI device
~connectMIDI.(0);

// Check MIDI channel assignments
~genMidiChannel.postln;   // Array of 8 values (0=OFF, 1-16=channel)

// Set gen1 to listen on MIDI channel 1
~genMidiChannel[0] = 1;

// Test MIDI trigger manually
~handleMidiNoteOn.(100, 60, 0);  // velocity, note, channel(0-indexed)


// ============================================================
// OSC DEBUGGING
// ============================================================

// Trace all incoming OSC
OSCFunc.trace(true);
OSCFunc.trace(false);   // Turn off

// Send test OSC from SC (simulating Python)
NetAddr("127.0.0.1", 57110).sendMsg('/noise/clock/bpm', 140);
NetAddr("127.0.0.1", 57110).sendMsg('/noise/gen/frequency', 1, 440);


// ============================================================
// AUDIO DEBUGGING
// ============================================================

// Simple test tone (bypasses everything)
{ SinOsc.ar(440, 0, 0.2) ! 2 }.play;

// Test master bus is working
{ In.ar(~masterBus, 2) }.play;

// Check if clock is generating triggers
{ In.ar(~clockTrigBus, 1) }.scope;


// ============================================================
// EMERGENCY STOP
// ============================================================

// If things go wrong:
CmdPeriod.run;       // Cmd+. equivalent - stops all sound
s.freeAll;           // Clear all synths
s.reboot;            // Full restart
