# Synthesis Techniques Reference

A comprehensive taxonomy of synthesis methods for generator design.

---

## Core synthesis families

### Oscillator-based

* **Subtractive synthesis** (harmonic-rich source → filters → VCA/envelopes)
* **Additive synthesis** (sum of partials with per-partial amp/freq/env)
* **FM synthesis** (phase/frequency modulation between oscillators; DX-style, 2–8 ops)
* **PM synthesis** (phase modulation; similar to FM but often easier/stabler digitally)
* **AM synthesis** (amplitude modulation; ring-mod is balanced AM)
* **Ring modulation** (multiply two signals → sum/difference sidebands)
* **Waveshaping / distortion synthesis** (nonlinear transfer functions generate harmonics)
* **Wavefolding** (fold signal back on itself; West Coast timbre shaping)
* **PWM** (pulse-width modulation; dynamic harmonic content)
* **Hard sync** (slave oscillator reset by master → sweeping harmonics)
* **Oscillator cross-mod** (audio-rate mod of pitch/phase/shape)
* **Supersaw / unison** (multi-detuned stacks with stereo spreading)
* **Wavetable synthesis** (scan/interpolate through tables; multi-dimensional tables)
* **Vector synthesis** (morph between multiple sources (A/B/C/D))
* **Spectral wavetable** (build wavetables from target spectra / FFT bins)
* **Chebyshev / polynomial waveshaping** (controlled harmonic series generation)
* **Feedback FM / self-FM** (modulator is output of carrier path; chaotic/edgy)

### Filter / resonator-based

* **Classic subtractive filtering** (LP/BP/HP/notch)
* **Formant synthesis** (fixed/moving formant bands; vowel filters)
* **Resonant filtering / pinging** (excite high-Q filters/resonators)
* **Resonator banks** (modal filters tuned to harmonic/in-harmonic sets)
* **Comb-filter synthesis** (delay + feedback = pitched resonance)
* **Phaser-as-resonator** (allpass networks with feedback for comb-like peaks)
* **State-variable filter morphing** (continuous blend LP↔BP↔HP)
* **Nonlinear/drive filters** (ladder w/ saturation; diode ladder; MS-20 style)
* **Vocal tract / physical filter models** (tube/constriction filters)

### Noise & stochastic sources

* **Noise-based subtractive** (white/pink/brown → filters)
* **Dust / impulse noise** (random impulses → resonators)
* **Random walk / slew-noise modulation** (stochastic control signals)
* **Chaos modulation as synthesis driver** (chaotic LFOs at audio rate)
* **Stochastic additive** (partials with randomized drift/amp/jitter)
* **Granular noise** (tiny grains of noise shaped into textures)

---

## Sampling-derived techniques

* **Sample playback / ROMpler synthesis**
* **Multisampling / keymap synthesis** (velocity layers, round-robin)
* **Time-stretching as synthesis** (phase vocoder, WSOLA, elastique-style)
* **Pitch-shift synthesis** (resampling, phase vocoder, PSOLA)
* **Spectral freezing / hold** (freeze FFT frames; morph over time)
* **Spectral cross-synthesis** (impose spectrum of A onto B; vocoding variants)
* **Convolution as synthesis** (impulse responses, resonant body imprinting)
* **Granular synthesis** (from samples or live input)
* **Slice / beat repeat / micro-looping** (buffer gymnastics as timbral source)
* **Wavesequencing** (stepped/continuous sample sequences; wave + timing lanes)
* **Resynthesis** (analysis → additive/FFT/physical model reconstruction)
* **Concatenative synthesis** (assemble sound from a corpus by feature matching)

---

## Physical modelling and "excite + resonate"

* **Karplus–Strong** (plucked string via short delay + filter + feedback)
* **Digital waveguides** (strings, tubes; bidirectional delay lines)
* **Modal synthesis** (sum of resonant modes excited by impulses/noise)
* **Mass-spring networks** (2D/3D physical simulations → audio)
* **Finite Difference Time Domain (FDTD)** (physical PDE discretization)
* **Wave terrain synthesis** (2D surface scanned by oscillators)
* **Bowed string models** (friction nonlinearities)
* **Reed models** (clarinet/sax style nonlinear reed + bore)
* **Membrane / plate models** (drums, cymbals; often modal/FDTD hybrids)
* **Scanned synthesis** (slowly evolving "shape" scanned at audio rate)
* **Impulse response body modelling** (convolution/body resonators)
* **Feedback delay networks as instruments** (FDN + nonlinearities)

---

## Time-domain "algorithmic" synthesis

* **Pulse train synthesis** (bandlimited impulses; click-to-tone techniques)
* **Formant pulse synthesis** (impulse → formant filters)
* **Wave packet synthesis** (short damped sinusoids triggered in patterns)
* **Glottal source synthesis** (LF model → vocal tract filter)
* **Event-based synthesis** (asynchronous events/impulses generating sound)
* **Feedback synthesis** (signal routes back into itself; controlled instability)
* **Nonlinear dynamical systems** (Lorenz/Chua-inspired audio-rate systems)
* **Fractal synthesis** (self-similar control/data mapped to oscillators/filters)
* **Bitwise / bytebeat synthesis** (integer math → audio; harsh/lofi textures)
* **Lookup-table dynamical maps** (logistic map etc. at audio rate)
* **Cellular automata → audio** (rule systems mapped to amplitude/pitch/filters)

---

## Spectral / frequency-domain synthesis

* **FFT additive** (bins as oscillators; manipulate magnitudes/phases)
* **Phase vocoder synthesis** (modify STFT then invert)
* **Sinusoidal modelling** (track partials; resynthesize with sines + noise)
* **Spectral morphing** (interpolate magnitudes/phases across sources)
* **Cepstral / spectral envelope processing** (separate envelope vs fine structure)
* **Spectral gating / spectral dynamics** (per-band expansion/compression)
* **Spectral blur / diffusion** (smear in time/frequency)
* **Harmonic/percussive separation → resynthesis** (HPSS)
* **McAulay–Quatieri style partial tracking** (analysis/resynthesis family)

---

## Modulation and control strategies that become "techniques"

(These aren't a whole synthesis family alone, but they're distinct methods when used as primary timbre engines.)

* **Audio-rate modulation** (AM/FM/PM at audio rates)
* **Phase distortion** (Casio CZ-style; nonlinear phase mapping)
* **Pulse-shaping** (map phase → waveform via shaping functions)
* **Through-zero FM** (carrier crosses 0 Hz; symmetrical sidebands)
* **Crossfading / wavescanning** (continuous morph of sources)
* **Wave multiplication** (frequency multiplication via waveshaping)
* **Subharmonic synthesis** (frequency division; "sub" series generation)
* **Sync + FM hybrids** (sync-reset plus FM for aggressive spectra)
* **Feedback networks** (filters/oscillators in loops; stability management)

---

## Nonlinear / "circuit-ish" synthesis

* **Saturator/tape/tube modelling** (static + dynamic nonlinearities)
* **Diode/transistor waveshapers** (asymmetric distortion)
* **Wavefolder models** (Serge/Buchla-inspired)
* **Comparator / rectifier synthesis** (full-wave/half-wave shaping)
* **Bitcrush / sample-rate reduction** (aliasing as timbre)
* **Aliasing-based synthesis** (intentional non-bandlimited oscillators)
* **Nonlinear filter self-oscillation** (filter as oscillator + drive)

---

## Granular & cloud techniques (expanded)

* **Synchronous granular** (grains locked to pitch)
* **Asynchronous granular** (texture clouds; density-based)
* **Pitch-synchronous granular** (align grains to waveform periods)
* **Granular FM** (grain position/pitch modulated at audio rate)
* **Grain-domain filtering** (filter each grain, not the stream)
* **Granular convolution** (convolve/overlay grains from different sources)
* **Corpus-based grain selection** (feature-matched grains)

---

## Spatial / multichannel synthesis (can be "the synthesis")

* **Stereo decorrelation** (allpass networks, micro-delays)
* **Ambisonic synthesis** (generate directly in HOA/B-format)
* **Wavefield synthesis (WFS)** (speaker array reconstruction)
* **Binaural/HRIR synthesis** (position as part of sound generation)
* **Spatial granular** (grain positions as synthesis parameters)
* **Rotating partials** (partials distributed around space)

---

## Techniques "not originally audio" but very adaptable

* **Image-to-sound** (scanlines → wavetable, spectrogram painting, column FFT)
* **Video-to-sound** (motion vectors → modulation fields)
* **Procedural textures → audio** (Perlin/simplex noise as control or wavetable)
* **L-systems** (growth rules → event streams/pitch trees)
* **Markov chains** (state transitions controlling synthesis + orchestration)
* **Genetic/evolutionary synthesis** (optimize parameters toward a target)
* **Neural / differentiable synthesis** (DDSP-style models; neural oscillators/filters)
* **GAN/latent-space control** (latent → parameter sets)
* **Data sonification** (time series to synthesis parameters)
* **Physics sims** (fluid/cloth/rigid-body collisions mapped to excitations)

---

## Hybrid "instrument design patterns" (useful mental buckets)

* **Exciter → resonator** (impulse/noise/burst → string/body/resonators)
* **Harmonic source → shaper → filter** (osc → fold/shape → SVF/ladder)
* **Partial bank → spectral envelope** (additive + moving envelope)
* **Buffer → micro-ops** (granular/slicing/stretching)
* **Feedback loop with safety** (nonlinear block inside loop + limiter/saturation)

---

## Tagging Cheatsheet

For consistent generator labeling:

| Tag | Category |
|-----|----------|
| SUB | Subtractive |
| ADD | Additive |
| FM/PM/AM/RM | Modulation types |
| WT | Wavetable |
| GRAIN | Granular |
| MODEL | Physical modelling |
| SPEC | Spectral/FFT |
| BUF | Buffer/sample-based |
| NL | Nonlinear/distortion |
| FB | Feedback networks |
| STOCH | Stochastic/noise/chaos |
| SPAT | Spatial |

---

## Imaginarium Implementation Status

### Implemented (Phase 1)

| Method | Family | Technique |
|--------|--------|-----------|
| bright_saw | subtractive | SUB - detuned saws + filter |
| dark_pulse | subtractive | SUB - PWM pulse + filter |
| noise_filtered | subtractive | STOCH - multi-noise + filter |
| supersaw | subtractive | SUB - 7-osc unison |
| simple_fm | fm | FM - 2-op classic |
| feedback_fm | fm | FM/FB - self-modulation |
| ratio_stack | fm | FM - 3-op stacked |
| karplus | physical | MODEL - Karplus-Strong |
| modal | physical | MODEL - resonator banks |
| bowed | physical | MODEL - friction string |

### Candidates for Phase 2

| Method | Family | Technique | Character Gap Filled |
|--------|--------|-----------|---------------------|
| ring_mod | fm | RM | Metallic/atonal/sci-fi |
| formant | physical | Formant synthesis | Breathy/vocal/organic |
| wavefold | subtractive | NL - wavefolding | West Coast/complex harmonics |
| phase_mod | fm | PM/Phase distortion | CZ-style digital |

---

## References

- Curtis Roads, "The Computer Music Tutorial"
- Miller Puckette, "Theory and Techniques of Electronic Music"
- Julius O. Smith, "Physical Audio Signal Processing"
- SuperCollider documentation
