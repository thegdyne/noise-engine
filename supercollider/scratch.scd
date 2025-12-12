/*
SUPERCOLLIDER SCRATCH PAD - Execute with Cmd+Return
*/

// === MOST USED ===
s.reboot;                    // Full restart (clears everything)
s.freeAll;                   // Stop all synths, keep server
s.queryAllNodes;             // What's running?
CmdPeriod.run;               // Emergency stop (Cmd+.)

// === SERVER ===
s.boot;
s.quit;
Server.killAll;              // Nuclear option

// === RELOAD PROJECT ===
// 1. s.freeAll;
// 2. Open init.scd, Cmd+A, Cmd+Return

// === VISUALS ===
s.plotTree;                  // Node tree window
s.meter;                     // Audio levels
s.scope;                     // Oscilloscope

// === CHECK BUSES ===
~clockBus.get({ |v| ("BPM: " ++ v).postln });
~genParams[1][\frequency].get({ |v| ("Gen1 freq: " ++ v).postln });
~genParams[1][\envSource].get({ |v| ("Gen1 env: " ++ v).postln });  // 0=OFF 1=CLK 2=MIDI
~genParams[1].keysValuesDo({ |k, v| v.get({ |val| (k ++ ": " ++ val).postln }) });

// === MANUAL GENERATOR CONTROL ===
~startGenerator.(1, \additive);
~startGenerator.(1, \subtractive);
~stopGenerator.(1);
PathName(~generatorPath).files.do({ |f| f.fileName.postln });  // List types

// === SET PARAMS (slot 1) ===
~clockBus.set(120);
~genParams[1][\frequency].set(440);
~genParams[1][\cutoff].set(2000);
~genParams[1][\resonance].set(0.3);
~genParams[1][\attack].set(0.01);
~genParams[1][\decay].set(0.5);
~genParams[1][\envSource].set(1);     // 0=OFF 1=CLK 2=MIDI
~genParams[1][\clockRate].set(6);     // 0=/32 ... 6=CLK ... 12=x32
~genParams[1][\custom][0].set(0.7);

// === MIDI DEBUG ===
MIDIClient.init;
MIDIClient.sources;
~connectMIDI.(0);                     // Connect first device
~genMidiChannel.postln;               // Channel assignments
~genMidiChannel[0] = 1;               // Gen1 listens on ch1
~handleMidiNoteOn.(100, 60, 0);       // Test: vel, note, chan

// === OSC DEBUG ===
OSCFunc.trace(true);
OSCFunc.trace(false);
NetAddr("127.0.0.1", 57110).sendMsg('/noise/clock/bpm', 140);
NetAddr("127.0.0.1", 57110).sendMsg('/noise/gen/frequency', 1, 440);

// === AUDIO DEBUG ===
{ SinOsc.ar(440, 0, 0.2) ! 2 }.play;  // Test tone
{ In.ar(~masterBus, 2) }.play;        // Monitor master bus
{ In.ar(~clockTrigBus, 1) }.scope;    // Watch clock triggers
