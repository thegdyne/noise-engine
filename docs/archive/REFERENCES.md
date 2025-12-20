# Generator References

Circuit concepts and parameters for Noise Engine generators are derived from various sources including Elektor magazine articles, Eurorack module designs, and physics models. This index documents the source material.

---

## Elektor Magazine

### Relaxation Oscillators

| Circuit Type | Elektor Issue | Article / Column | Generator | Notes |
|--------------|---------------|------------------|-----------|-------|
| VCO relaxation (XR2206/MAX038 style) | March 2007 | Signal generator / function generator test article | `vco_relax` | Current-source charging timing capacitor |
| CapSense relaxation (charge-time) | July/August 2011 (Vol. 37, No. 415/416) | Capacitive sensing article | `capsense` | Charge-time measurement of sensor capacitance |
| NPN/UJT/PUT relaxation (RC) | July/August 2011 (Vol. 37, No. 415/416) | "NPN Relaxation Oscillators" – Burkhard Kainka | `ujt_relax` | Classic RC oscillators, project ref. 110037 |
| PUT (programmable unijunction) | May 2014 | "Exclusively for Students" UJT/PUT article | `ujt_relax` | 2N6027 PUT RC relaxation oscillator |
| Neon-bulb relaxation | November 2014 | Neon bulb article | `neon_relax` | RC neon relaxation, multi-stage ring/divider |

### Sirens

| Circuit Type | Elektor Issue | Article / Column | Generator | Notes |
|--------------|---------------|------------------|-----------|-------|
| 4060 + analogue multiplexer siren | December 2006 (i-TRIXX supplement) | "When the siren sounds…" | `siren_4060` | CD4060 counter + mux stepping through resistor chain |
| NE556 "FBI siren with flashing light" | March 2006 | "FBI siren with flashing light" – Arthur Schilp | `fbi_siren` | Dual 555: slow sweep + lamp, audio VCO + speaker |
| Blue flashing light for models | November 2011 | Blue flashing light for model emergency vehicles | — | CD4060-based flasher for model vehicles |
| 7400 TTL siren | June 1976 (PCB ref Dec 1975) | "7400 siren 9119" | — | Classic TTL siren, PCB order reference |

### Ring Modulators

| Circuit Type | Elektor Issue | Article / Column | Generator | Notes |
|--------------|---------------|------------------|-----------|-------|
| Formant ring modulator (mk II) | April 2008 | Retronics: "Formant music synthesiser" | `diode_ring`, `fourquad_ring`, `vca_ring` | Revisiting 1977–78 Formant; ring mod as add-on module |
| Original Formant ring mod | May 1977 – April 1978 (multi-part) | "Formant" synthesiser series – C. Chapman | `diode_ring`, `fourquad_ring`, `vca_ring` | Original DIY modular synth series |

---

## Nonlinear Circuits (NLC)

| Circuit | Designer | Generator | Notes |
|---------|----------|-----------|-------|
| Giant B0N0 | Andrew F | `giant_bono` | Chaotic PLL (CD4046) with overdriven PT2399 delay in feedback path |

**Source:** [nonlinearcircuits.com](https://www.nonlinearcircuits.com)

The Giant B0N0 combines:
- CD4046 PLL deliberately pushed into chaotic operating regions
- PT2399 delay chip severely overdriven in feedback path
- Dual vactrols for CV control
- Multiple outputs: Mix, VCO, PC1, PC2 (burst), Saw, CV
- "1V per Couric" tuning (frequency control)
- Character: "nutty chunks or liquid baby green"

---

## Physics Models

| Generator | Model | Notes |
|-----------|-------|-------|
| `geiger` | Geiger-Müller tube | Poisson-distributed clicks, dead time clustering, discharge transients |

---

## Parameter Mapping

Each generator's custom parameters (P1–P5) are derived from the physical controls and circuit characteristics documented in the source material:

### Relaxation Oscillators (Elektor)
- **Timing components** (RC, current sources) → frequency/period controls
- **Threshold voltages** (Vb, Vd, peak voltage) → trigger point controls
- **Hysteresis** → snap/discharge character
- **Supply voltage** → amplitude and frequency range

### Sirens (Elektor)
- **Oscillator RC** → base pitch
- **Counter/pattern** → wail shape and complexity
- **Modulation depth** → sweep range
- **Drive level** → output loudness/distortion

### Ring Modulators (Elektor)
- **Carrier/modulator frequencies** → sum/difference tones
- **Input levels** → sideband strength
- **Balance/null trims** → carrier suppression
- **Topology** → clean vs distorted character

### Giant B0N0 (NLC)
- **Courics** → PLL frequency (main pitch control)
- **PLL>Delay** → chaos interaction between PLL and delay
- **Delay feedback** → PT2399 overdrive amount
- **Delay time** → delay chip timing
- **Character** → filter/mix ("nutty chunks" ↔ "liquid baby green")

### Geiger Counter (Physics)
- **Count rate** → average clicks/second (Poisson statistics)
- **Dead time** → tube recovery, click clustering at high rates
- **Click brightness** → spectral content of discharge transient
- **Click decay** → tube/speaker resonance ringout
- **Background noise** → continuous tube hiss between clicks

---

## Further Reading

### Elektor
- Elektor magazine archives: [elektor.com](https://www.elektor.com)
- Formant synthesiser book (1980 reprint)
- i-TRIXX circuit collections (2006–2009)

### Nonlinear Circuits
- NLC website: [nonlinearcircuits.com](https://www.nonlinearcircuits.com)
- Build documents and schematics available for all modules
