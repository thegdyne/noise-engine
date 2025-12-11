# Future Ideas

Captured ideas for potential future development.

---

## External Audio Processing (Eurorack Send/Return)

**Concept:** Route audio out to Eurorack, process through hardware, return to software FX chain.

**Signal flow:**
```
SC Generator → Interface Out → Eurorack → Interface In → SC FX Chain → Main Out
```

**Requirements:**
- Multi-output audio interface (MOTU M6 has 4 out / 4 in)
- Level matching (line ≠ Eurorack, may need output module like ES-8)

**Implementation:**
- "External FX" slot in effects chain
- Routes to specific hardware output
- Listens on corresponding input
- Wet/dry mix in software

**Considerations:**
- Latency: round trip adds 5-20ms depending on buffer size
- May need latency compensation for clock-synced material
- Feedback risk if routing misconfigured

**Synergy:** Already have CV.OCD for control - this adds audio to the hybrid setup.

---
