---
status: approved
version: v0.0.2
review: v0.0.2 decisions resolved (SC-local timing)
date: 2026-02-11
depends-on: none (bufBus allocated inline; no BUFBUS_SPEC prerequisite)
---

# MOLTI-SAMP — Multi-sample Generator (Korg .korgmultisample)

## Goals
- **Hardware-like timing:** note→zone selection happens in SuperCollider (no per-note Python OSC).
- Load `.korgmultisample` and referenced `.wav` files.
- Hot-swap per-slot multisample sets (reload tables + audio bufs) without restarting SC.
- User params remain normal P1–P5 (LOOP, STRT, END, GAIN, etc).

## Non-goals (v0.0.2)
- Time-stretching, slicing UI, round-robin groups.
- Streaming from disk (RAM load only).

## Architecture (double indirection)
Per slot, Python builds two **control buffers**:
1) `noteMapBuf` (128 int-ish entries): MIDI note → `zoneIndex`
2) `zoneBufBuf` (zoneCount entries): `zoneIndex` → **audio bufnum**

SynthDef selects zone **SC-side**:
`zone = Index.kr(noteMapBuf, note)` → `bufnum = Index.kr(zoneBufBuf, zone)` → `BufRd`

This yields immediate note response (limited only by control-rate + trigger scheduling), matching "hardware" feel.

## Phase 0 — bufBus substrate (inline allocation)
### SC init (core init / init.scd)
Allocate one 4ch control bus per slot:

```supercollider
// Phase 0: bufBus substrate (8 slots × 4ch)
~bufBuses = Array.fill(8, { Bus.control(s, 4) });
8.do { |i| ~bufBuses[i].setn([-1, -1, 0, 0]); }; // noteMapBuf, zoneBufBuf, zoneCount, reserved
```

### bufBus channel mapping (KEEP)
- ch0: `noteMapBuf` bufnum (>=0 valid, -1 = none)
- ch1: `zoneBufBuf` bufnum (>=0 valid, -1 = none)
- ch2: `zoneCount` (0 = none)
- ch3: reserved (0)

### startGenerator contract
When starting `forge_molti_samp`, pass:
- `\bufBus, ~bufBuses[idx].index`
- `\midiTrigBus, ~midiTrigBus.index` (already standard)
- `\slotIndex, idx` (already standard)

If start helper can't introspect SynthDef args, gate by generator type == `molti_samp`.

## Resolved Decisions (v0.0.2 review)
1. **BUFBUS_SPEC removed:** bufBus allocated inline (Phase 0).
2. **bufBus mapping:** ch0=noteMapBuf, ch1=zoneBufBuf, ch2=zoneCount, ch3=reserved.
3. **Passing buses:** `forge_molti_samp` receives `bufBus`; MIDI trig uses `midiTrigBus + slotIndex`.
4. **Buffer number allocation:** Python owns reserved bufnum range + free-list (avoid collisions).
5. **Note latch:** **MIDI-only** latch so clock retriggers replay same zone.
6. **Sample path resolution:** korg dir → `~` → `sample_roots[]` → fail with attempted paths.
7. **Safety:** never read invalid bufnums; guard playback when bufnum < 0.
8. **Mono→stereo:** load via `/b_allocReadChannel` ([0,0] for mono); SynthDef reads 2ch safely.

---

# SuperCollider — SynthDef

## Inputs / buses
- `out` audio out bus
- `freqBus` and `customBus0..4` remain user params (P1–P5) — do NOT repurpose.
- `bufBus` (4ch) provides infrastructure (noteMapBuf / zoneBufBuf / zoneCount)

## Triggering

Note: `midiTrigBus` is **audio-rate** (trigger pulses). Always read with `In.ar` and convert with `A2K.kr` for latching.

- `midiTrig` = `In.ar(midiTrigBus + slotIndex, 1)` (audio-rate trigger pulse on MIDI note-on)
- Optional clock trig: if you also support clock retriggering, it must **not** change the latched note.

## Note latch (MIDI-only)
In the main SynthDef body:

```supercollider
// midiTrig is audio-rate; convert to kr for Latch
var midiTrig = In.ar(midiTrigBus + slotIndex, 1);
lastNote = Latch.kr(currentNote, A2K.kr(midiTrig));
```

(Replace any prior `Latch.kr(..., trigK)` usage.)

## Guarding invalid buffers (no Index.kr(-1) assumptions)
- If `noteMapBuf < 0` OR `zoneBufBuf < 0` OR `zoneCount <= 0` → output `Silent.ar(2)`
- If looked-up `bufnum < 0` → output `Silent.ar(2)`

Prefer explicit `Select.ar`/`Gate`/`LagUD` guard over "multiply by zero" if there's any chance of NaN propagation.

---

# File Format — .korgmultisample (Binary, NOT XML)

**Important:** Despite some documentation suggesting XML, `.korgmultisample` files use a
**binary protobuf-like** format. Verified against real files from Korg Sample Builder v1.2.7.

## Overall structure
1. **4-byte header:** `Korg` (ASCII)
2. **Chunk 1** (LE uint32 size + data): Header info — contains "ExtendedFileInfo", "MultiSample" tags
3. **Chunk 2** (LE uint32 size + data): Metadata — "SingleItem", app name/version, timestamp
4. **Chunk 3** (LE uint32 size + data): Multisample data — name, zones, wav paths

## Chunk 3 — Multisample data (protobuf field encoding)
Fields use protobuf wire format: `(field_number << 3) | wire_type`

### Top-level fields:
- field 1 (bytes): Multisample name
- field 2 (bytes): Author
- field 3 (bytes): Category
- field 4 (bytes): Comment
- field 5 (bytes): Sample zone blocks (tag = 0x2a, repeated)
- field 7 (bytes): UUID

### Sample zone block (nested inside field 5):
- field 1 (bytes): Nested sample data submessage
  - sub-field 1 (bytes): wav file path (UTF-8 string, relative)
  - sub-field 2 (varint): sample start frame
  - sub-field 3 (varint): loop start frame
  - sub-field 4 (varint): sample end frame
  - sub-field 9 (varint): one_shot flag (1 = one-shot)
  - sub-field 10 (varint): boost_12db flag
- field 2 (varint): key_bottom (MIDI note 0-127)
- field 3 (varint): key_top (MIDI note 0-127)
- field 4 (varint): key_original / root note (MIDI note 0-127)
- field 5 (varint): fixed_pitch flag
- field 6 (float): tune (-999..999, normalized by 1000)
- field 7 (float): level_left
- field 8 (float): level_right
- field 10 (varint): color (display color, ignored by engine)

## Varint encoding
Standard protobuf 7-bit variable-length: each byte uses bit 7 as continuation flag,
bits 0-6 carry data in little-endian order.

## Reference implementation
Parser: `src/audio/korg_multisample.py`
Format reference: [ConvertWithMoss](https://github.com/git-moss/ConvertWithMoss)

---

# Python — Loader / Allocations

## Bufnum allocation
- Reserve a high bufnum range for MOLTI-SAMP, managed by Python:
  - e.g. `MOLTI_BUF_BASE=4000`, `MOLTI_BUF_COUNT=512` (tune to expected max)
- Python maintains a free-list; allocates for:
  - `noteMapBuf`
  - `zoneBufBuf`
  - each audio `.wav` buffer

## Audio file loading (mono/stereo)
Use `/b_allocReadChannel`:
- Stereo: channels `[0,1]`
- Mono: channels `[0,0]` (duplicate to 2ch at load)

This guarantees SynthDef `BufRd.ar(2, ...)` never reads garbage on channel 2.

## Sample path resolution
Given `.korgmultisample` path `ms_path` and wav path string `wav_path` from file:
Try in order:
1) `ms_path.parent / wav_path`
2) `Path.home() / wav_path`
3) for each `root in config.sample_roots`: `root / wav_path`
4) Fail with error that lists attempted absolute paths.

## Table construction
- Build `noteMap` (len 128): each note maps to a zone index (0..zoneCount-1) or -1
- Build `zoneBuf` (len zoneCount): each zone index maps to an audio bufnum (>=0) or -1

Write tables into SC buffers:
- `/b_setn noteMapBuf 0 128 <ints>`
- `/b_setn zoneBufBuf 0 zoneCount <ints>`

## Hot-swap update (per slot)
After buffers are loaded and tables written, update bufBus:
- `/c_setn bufBusIndex 4 noteMapBuf zoneBufBuf zoneCount 0`

No per-note OSC is required.

## Cleanup
When unloading a multisample from a slot:
- Set slot bufBus to silent: `[-1, -1, 0, 0]`
- Free all owned bufnums in that slot (audio + table bufs) and return to pool.

---

# UI / Params (P1–P5 stay user-facing)
Example mapping (can match your generator UI conventions):
- P1 LOOP (0/1)
- P2 STRT (0..1 normalized → applied inside SynthDef as frame start)
- P3 END (0..1 normalized → applied inside SynthDef as frame end)
- P4 GAIN (dB)
- P5 optional (tune, rootKey offset, xfade)

(These are independent of bufBus; bufBus is infrastructure only.)

---

# Phases (kept from existing plan)
## Phase 0
- Inline allocate `~bufBuses` (above)
- Ensure `forge_molti_samp` gets `bufBus` arg in start path

## Phase 1 — Parser
- Parse `.korgmultisample` into zones + wav paths + key ranges
- Output normalized internal model suitable for table building

## Phase 2 — SynthDef + Loading
- Implement SynthDef (single canonical version; no duplicate fragments in doc)
- Implement loader: bufnum pool, audio loads, table writes, bufBus update
- Guard invalid bufnums; MIDI-only note latch

## Phase 3 — GUI
- Add generator type entry + basic controls + load button
- Show resolved path errors clearly

## Phase 4 — Browser
- File picker / multisample browser + recent list

---

# Acceptance Criteria
- AC1: MIDI note changes zone with no Python per-note OSC.
- AC2: Clock retrigger (if supported) replays **same** latched zone.
- AC3: Mono files play correctly (no garbage right channel).
- AC4: Unloaded slot is silent (no NaNs, no stuck audio).
- AC5: Hot-swap a multisample set while running without SC restart.
