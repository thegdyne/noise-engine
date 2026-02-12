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

SynthDef(\moltisamp_molti_samp, { |out, freqBus, customBus0, bufBus, midiTrigBus, slotIndex=0|
    // === VAR DECLARATIONS (must be at top of block) ===
    var p, sig;
    var noteMapBufNum, zoneBufBufNum, zoneCount;
    var midiTrig, midiTrigK, currentNote, lastNote;
    var zoneIdx, zoneIdxRaw, bufnum, readBuf, numFrames;
    var phase, phaseK, phaseInc, startFrame, endFrame;
    var loopFlag, doneTrig, running;
    var valid, gainDb;
    var safeBuf = LocalBuf(2, 2).clear;  // silent 2ch fallback (avoids buffer 0 mismatch)

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

    // === CURRENT NOTE ===
    // freqBus contains frequency in Hz; .cpsmidi converts to MIDI note number
    currentNote = In.kr(freqBus).cpsmidi.round(1).clip(0, 127);

    // MIDI-only latch: only update note on MIDI trigger, NOT clock
    lastNote = Latch.kr(currentNote, midiTrigK).round(1);  // belt + braces

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

    // Safe buffer: use real audio buffer when valid, silent LocalBuf otherwise
    readBuf = Select.kr(valid > 0, [safeBuf, bufnum.max(0)]);

    // === PLAYBACK (single Phasor+BufRd core for both modes) ===
    numFrames  = BufFrames.kr(readBuf);
    startFrame = (p[1] * numFrames).round(1);
    endFrame   = (p[2] * numFrames).round(1).max(startFrame + 1);
    loopFlag   = (p[0] > 0.5).asInteger;  // explicit 0/1 for Select

    // Rate with TUNE (P5): +/-1 semitone around center
    phaseInc = BufRateScale.kr(readBuf) * p[4].linlin(0, 1, -1, 1).midiratio;

    phase = Phasor.ar(
        trig: midiTrig,
        rate: phaseInc,
        start: startFrame,
        end: endFrame,
        resetPos: startFrame
    );

    // One-shot gate: start on MIDI trig, stop when phase reaches endFrame
    phaseK   = A2K.kr(phase);  // ar->kr value stream for comparison
    doneTrig = Trig1.kr((phaseK >= (endFrame - 1)) * (1 - loopFlag), 0.001);
    running = Select.kr(loopFlag, [
        SetResetFF.kr(midiTrigK, doneTrig),  // one-shot: set on MIDI, reset at end
        1                                     // loop: always running
    ]);

    sig = BufRd.ar(2, readBuf, phase, loop: 0) * running;

    // === GAIN (P4: -24dB to +6dB) ===
    gainDb = p[3].linlin(0, 1, -24, 6);
    sig = sig * gainDb.dbamp;

    // === SAFETY GATE: silence when infrastructure invalid ===
    sig = Select.ar(valid > 0, [
        Silent.ar(2),
        sig
    ]);

    // === MANDATORY TAIL ===
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] moltisamp_molti_samp loaded".postln;
