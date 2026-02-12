// molti_samp pack — Multi-sample player (Korg .korgmultisample)
/*
MOLTI Sampler Generator (pack variant)
Plays back multi-sample sets loaded from .korgmultisample files.

Double indirection: noteMapBuf[note] -> zoneIdx -> zoneBufBuf[zoneIdx] -> audio bufnum
All zone selection happens SC-side (no per-note Python OSC).

Custom params (P1-P5):
  - P1 LOOP: 0=one-shot, 1=loop
  - P2 STRT: Playback start point (0..1 normalized)
  - P3 END:  Playback end point (0..1 normalized)
  - P4 GAIN: Output gain (-24dB to +6dB)
  - P5 TUNE: Fine tune (0.5=center, +/-1 semitone)

Infrastructure (via bufBus):
  - ch0: noteMapBuf bufnum
  - ch1: zoneBufBuf bufnum
  - ch2: zoneCount
  - ch3: reserved
*/

SynthDef(\moltisamp_molti_samp, { |out, freqBus, customBus0, bufBus, midiTrigBus, noteBus, slotIndex=0|
    // === VAR DECLARATIONS (must be at top of block) ===
    var p, sig;
    var noteMapBufNum, zoneBufBufNum, zoneCount;
    var midiTrig, midiTrigK, currentNote, lastNote;
    var zoneIdx, zoneIdxRaw, bufnum, readBuf, numFrames;
    var phase, phaseInc, startFrame, endFrame;
    var loopFlag, elapsed, running, started, frameCount;
    var valid, gainDb;

    // === READ PARAMS ===
    p = In.kr(customBus0, 5);
    // p[0] = LOOP (0/1)
    // p[1] = STRT (0..1 normalized)
    // p[2] = END  (0..1 normalized)
    // p[3] = GAIN (0..1 -> dB mapping)
    // p[4] = TUNE (0..1, 0.5=center, +/-1 semitone)

    // === READ BUFBUS (infrastructure) ===
    noteMapBufNum = In.kr(bufBus, 1);      // ch0
    zoneBufBufNum = In.kr(bufBus + 1, 1);  // ch1
    zoneCount     = In.kr(bufBus + 2, 1);  // ch2

    // === SAFETY: guard invalid infrastructure ===
    valid = (noteMapBufNum >= 0) * (zoneBufBufNum >= 0) * (zoneCount > 0);

    // === MIDI TRIGGER (audio-rate bus — always In.ar) ===
    midiTrig = In.ar(midiTrigBus + slotIndex, 1);
    midiTrigK = A2K.kr(midiTrig);

    // === CURRENT NOTE (SC-side — raw MIDI note, no Hz round-trip) ===
    // noteBus carries the integer MIDI note set by keyboard_osc / midi_handler / step_engine
    // directly on the control bus. No .midicps → .cpsmidi conversion = no precision/timing issues.
    currentNote = In.kr(noteBus + slotIndex).round(1).clip(0, 127);

    // No latch needed: noteBus already holds the correct note (step_engine
    // latches via noteHeld; keyboard_osc/midi_handler update atomically).
    // Previous Latch.kr(currentNote, midiTrigK) caused A2K one-block-late
    // zone lookup during ARP/SEQ stepping.
    lastNote = currentNote;

    // === ZONE LOOKUP (double indirection, SC-side) ===
    zoneIdxRaw = Select.kr(valid > 0, [
        -1,
        Index.kr(noteMapBufNum, lastNote)
    ]);
    valid = valid * (zoneIdxRaw >= 0) * (zoneIdxRaw < zoneCount);

    zoneIdx = zoneIdxRaw.clip(0, zoneCount - 1);
    bufnum = Select.kr(valid > 0, [
        0,
        Index.kr(zoneBufBufNum, zoneIdx)
    ]);

    // Second guard: bufnum itself must be valid
    valid = valid * (bufnum >= 0);

    // DEBUG: remove after diagnosis — fires on every MIDI trigger
    SendReply.kr(midiTrigK, "/noise/molti/debug", [lastNote, zoneIdxRaw, zoneIdx, bufnum, valid]);
    SendReply.kr(midiTrigK, "/noise/molti/trig", [slotIndex, lastNote, p[0]]);

    // === PLAYBACK (Phasor + audio-rate one-shot gate) ===
    // When invalid, use safe constants so BufFrames/Phasor/BufRd never touch a bad bufnum.
    readBuf   = bufnum.max(0);
    numFrames = Select.kr(valid > 0, [2, BufFrames.kr(readBuf)]);
    startFrame = (p[1] * numFrames).round(1);
    endFrame   = (p[2] * numFrames).round(1).max(startFrame + 1);
    loopFlag   = (p[0] > 0.5);

    // Rate with TUNE (P5): +/-1 semitone around center
    phaseInc = Select.kr(valid > 0, [1, BufRateScale.kr(readBuf)]) * p[4].linlin(0, 1, -1, 1).midiratio;

    phase = Phasor.ar(
        trig: midiTrig,
        rate: phaseInc,
        start: startFrame,
        end: endFrame,
        resetPos: startFrame
    );

    // One-shot gate: Sweep counts elapsed playback frames at audio rate
    frameCount = (endFrame - startFrame);

    // started=0 until first midiTrig, then stays 1 (subsequent trigs just restart Sweep)
    started = (PulseCount.ar(midiTrig) > 0);

    elapsed = Sweep.ar(midiTrig, phaseInc.abs * SampleRate.ir);
    running = Select.ar(loopFlag, [
        started * (elapsed < frameCount),  // one-shot: silent until first trig
        DC.ar(1)                            // loop: always running
    ]);

    // Gate BufRd behind valid — never read from a bad bufnum
    sig = Select.ar(valid > 0, [
        Silent.ar(2),
        BufRd.ar(2, readBuf, phase, loop: 0) * running
    ]);

    // === GAIN (P4: -24dB to +6dB) ===
    gainDb = p[3].linlin(0, 1, -24, 6);
    sig = sig * gainDb.dbamp;

    // === MANDATORY TAIL ===
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] moltisamp_molti_samp loaded".postln;
