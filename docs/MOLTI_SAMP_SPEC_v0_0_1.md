# MOLTI-SAMP Generator Spec v0.0.1

---
status: frozen
version: 0.0.1
date: 2026-01-05
approved: 2026-01-05
---

## What

A new generator type that plays Korg multisample files (`.korgmultisample`). Loads a complete keymapped sample set into a single slot, triggering the correct sample based on incoming MIDI notes. Integrates with the standard Noise Engine post-chain (filter, envelope).

## Why

- Reuse existing sample libraries created with Korg Sample Builder (Wavestate/Modwave compatible)
- Add drums, breaks, vocal chops, and other sample-based content to Noise Engine
- No need to invent a new multisample format — leverage Korg's tooling

## How

### File Format

Parse `.korgmultisample` files (protobuf-based, reverse-engineered in spike). Extract:
- Multisample name, author, category (metadata)
- Sample zones: path, root note, low note, high note

### Sample Location

The `.wav` files must be in the same folder (or subfolders) as the `.korgmultisample` file. Paths in the file are relative — we resolve them from the `.korgmultisample` location.

### Playback Model

| Aspect | Behavior |
|--------|----------|
| Slot usage | One multisample per slot |
| Zone selection | MIDI note → keymap lookup → correct zone |
| Pitch | Original pitch (no shifting in v0.0.1) |
| Trigger | Retrigger on new note |
| Polyphony | Mono (standard Noise Engine behavior) |
| Zone overlaps | Resolve by file order (first zone wins) |
| Keymap gaps | Produce silence |
| Stereo/mono | Loader normalizes buffers to 2ch (mono duplicated at load time) |

**Note**: v0.0.1 is intended for drum/break/chop multisamples where each zone is effectively "correct pitch" already. Pitched/melodic multisamples will not behave like Wavestate/Modwave without pitch shifting (deferred).

### Buffer Loading

**Eager loading**: Pre-load all zones when multisample is loaded. Design to allow fallback to lazy loading if memory becomes an issue.

**Silent buffer**: SC maintains a dedicated silent 2ch buffer (buf 0) used as fallback for invalid/unloaded zones.

**Deduplication**: Buffer cache keyed by absolute sample path — if the same .wav is used across multiple slots or multisamples, share the buffer. Buffers are refcounted; released when no slots reference them (or on project close).

**Channel normalization**: Loader normalizes all buffers to 2ch (mono samples duplicated to stereo at load time).

**Loading feedback**: Show "Loading… (n/N)" state on slot during buffer loading. `nLoaded` increments per buffer read; missing files count toward `nTotal` so progress bar completes. Disable triggering / user play until ready (engine may keep synth instantiated outputting silence).

### Custom Parameters

| Param | Range | Description |
|-------|-------|-------------|
| Loop | 0/1 | One-shot (0) or looped (1) playback |
| Start | 0.0–1.0 | Playback start position in sample |
| End | 0.0–1.0 | Playback end position in sample |
| Gain | 0.0–1.0 | Sample output level |

**Note**: Start/End are latched on trigger (per retrigger), not continuously modulated in v0.0.1.

### Standard Parameters (via buses)

Uses standard generator contract:
- `freqBus` — carries note pitch as Hz (from MIDI note conversion), used only for zone selection in v0.0.1
- `cutoffBus`, `resBus`, `filterTypeBus` — standard filter control
- `attackBus`, `decayBus`, `envEnabledBus`, `envSourceBus` — standard envelope
- `clockTrigBus`, `midiTrigBus` — standard triggers

**envSource encoding** (standard Noise Engine):
- `0` = OFF (no envelope)
- `1` = CLK (clock trigger)
- `2` = MIDI (MIDI trigger)

**Clock trigger semantics**: Tracks `currentNote` continuously; latches `lastNote` on `midiTrig`. Clock triggers retrigger using `lastNote` (do not overwrite).

### Transpose

Use existing transpose button concept (not a custom param). Shifts which zone is selected by MIDI note offset.

**SynthDef arg**: `transpose` is driven by existing slot transpose system (±24 semitones).

**Note**: MIDI updates `lastNote` even when envSource=CLK; clock retriggers use most recent MIDI-latched note.

### Post-Chain

Standard contract compliance:
```supercollider
sig = ~ensure2ch.(sig);
sig = ~multiFilter.(sig, filterType, cutoff, rq);
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
Out.ar(out, sig);
```

### UI

**Loading:**
- File picker button in generator slot (opens dialog for `.korgmultisample`)
- Browser panel showing available multisamples

**Browser scan roots** (configurable):
- `config.sample_roots = [...]` — list of directories to scan recursively for `*.korgmultisample`

**Display:**
- Multisample name only (e.g., "Amen MS_01")
- Loading state: "Loading… (n/N)" during buffer loading

**Generator name in UI:** `MOLTI-SAMP`

---

## SuperCollider Implementation Notes

### Data per loaded multisample (per slot)

- `bufnums[]` — buffer number for each zone
- `noteMap[128]` — maps MIDI note (0-127) → zone index (or -1 for silence)
- Start/end frames computed at runtime from `BufFrames * Start/End` params

### Mapping approach

Python precomputes:
- `noteMap[128]` — zone index per MIDI note (or -1 for silence)
- `zoneBuf[zoneCount]` — bufnum per zone

**Storage**: Send as dedicated control buffers per slot. Use `Index.kr` to read them.
- `noteMapBuf`: 128 int32 values
- `zoneBufBuf`: zoneCount int32 values

### Playback core (Phasor + BufRd)

```supercollider
// Trigger sources (follow envSource encoding)
envSource = In.kr(envSourceBus);
midiTrig  = In.kr(midiTrigBus);
clockTrig = In.kr(clockTrigBus);

// Retrigger source follows envSource: 0=OFF, 1=CLK, 2=MIDI
trig = Select.kr(envSource, [0, clockTrig, midiTrig]);

// Zone selection
currentNote = In.kr(freqBus).cpsmidi.round.clip(0, 127);
lastNote = Latch.kr(currentNote, midiTrig);  // latch on MIDI, clock uses lastNote
noteT = (lastNote + transpose).clip(0, 127);

// Zone lookup (via control buffers)
zone = Index.kr(noteMapBuf, noteT);     // -1 means silence
buf  = Index.kr(zoneBufBuf, zone.max(0));
isSilent = (zone < 0) | (buf < 0);      // unmapped or not loaded

// Safe buffer for frame calculations (buf 0 is silent fallback)
safeBuf = buf.max(0);

// Safety: ensure valid frame window (latch on trigger)
startPosL = Latch.kr(startPos, trig);
endPosL   = Latch.kr(endPos, trig);
startPosL = startPosL.clip(0, 0.999);
endPosL   = endPosL.clip(startPosL + 0.001, 1.0);

frames = BufFrames.kr(safeBuf).max(2);
startFrame = (frames * startPosL).floor;
endFrame   = (frames * endPosL).ceil.clip(startFrame + 1, frames);

// Playback
rate = BufRateScale.kr(safeBuf);
phase = Phasor.ar(trig, rate, startFrame, endFrame - 1, startFrame);

// One-shot / looped behavior
done = (phase >= (endFrame - 1));
wrap = (loop > 0) * done;
phase = Select.ar(wrap, [phase, startFrame]);

sig = BufRd.ar(2, safeBuf, phase, loop: 0, interpolation: 2);
sig = sig * (1 - isSilent);  // hard mute if unmapped or not loaded
sig = sig * gain;
// ... post-chain
```

### Trigger lifecycle

- `currentNote = In.kr(freqBus).cpsmidi.round.clip(0,127)` — continuous tracking
- On **midiTrig**: latch `lastNote = currentNote`, retrigger playback
- On **clockTrig**: retrigger using `lastNote` (do not overwrite)
- Retrigger resets `Phasor` phase to `startFrame`
- One-shot mode: when phase reaches end, let envelope close naturally (don't `FreeSelf`)
- If `buf < 0` or not loaded: output silence, keep synth running

### OSC Messages

| Message | Params | Direction | Description |
|---------|--------|-----------|-------------|
| `/ne/molti/load` | slotIdx, msPath, requestId | Py→SC | Start loading multisample |
| `/ne/molti/progress` | slotIdx, requestId, nLoaded, nTotal | SC→Py | Loading progress update |
| `/ne/molti/ready` | slotIdx, requestId, noteMapBufId, zoneBufBufId, zoneCount | SC→Py | Loading complete |
| `/ne/molti/error` | slotIdx, requestId, message | SC→Py | Loading failed |

---

## Implementation Phases

### Phase 1: Parser Integration
- Move spike parser to `src/core/korg_parser.py`
- Add tests for parsing

### Phase 2: SuperCollider SynthDef
- Create `molti_samp.scd` generator
- Buffer pool management in `init.scd`
- OSC messages for buffer loading

### Phase 3: GUI Integration
- Add `MOLTI-SAMP` to generator type dropdown
- File picker for loading
- Custom param controls (Loop, Start, End, Gain)

### Phase 4: Browser Panel
- Scan for `.korgmultisample` files in known locations
- Display in browser (like pack browser)

---

## Out of Scope (v0.0.1)

- Velocity layers
- Round-robin sample selection
- Sample editing (handled by Korg Sample Builder)
- Creating/exporting `.korgmultisample` files
- `.korgbank` support
- Multi-slot spread from single multisample
- Per-zone filter/envelope settings
- Playback speed control
- Reverse playback
- Pitch shifting (deferred, transpose button only)

---

## Resolved Questions

1. **Buffer limit** — 126 zones max (matches Korg's limit)

2. **Missing samples** — Skip loading missing samples; log missing paths once per load; unmapped notes produce silence

3. **Transpose range** — ±24 semitones (±2 octaves)

4. **Start/End implementation** — Use `Phasor` + `BufRd` (not `PlayBuf`) for clean start/end position clamping

5. **Preset portability** — Save both absolute path and project-relative path; on load try relative first, then absolute

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/core/korg_parser.py` | New — parser class |
| `supercollider/generators/molti_samp.scd` | New — SynthDef |
| `supercollider/init.scd` | Modify — buffer pool management |
| `src/gui/generator_slot.py` | Modify — add MOLTI-SAMP type |
| `src/gui/molti_samp_panel.py` | New — custom params UI |
| `src/gui/sampler_browser.py` | New — browser panel |
| `tests/test_korg_parser.py` | New — parser tests |

---

## Approval

- [x] Gareth (2026-01-05)
- [x] AI review (dual-AI workflow complete)
