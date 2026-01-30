// electric-shepherd/liminal — Lightweight end-stage generator
/*
LIMINAL Generator
The in-between space - suburban emptiness

Features:
  - Fluorescent light buzz
  - Distant traffic wash
  - Empty space resonance
  - Power line hum
  - Ghosts of activity

Custom params:
  - P1 fluoro: Fluorescent buzz
  - P2 traffic: Distant road noise
  - P3 void: Empty resonance
  - P4 wire: Power line drone
  - P5 memory: Distant ghostly sounds

The spaces between places.
*/

SynthDef(\liminal, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var fluoro, traffic, void, wire, memory;
    var trig;
    var fluoroSig, trafficSig, voidSig, wireSig, memorySig;
    var fluoroOsc, fluoroMod;
    var trafficNoise, trafficMod;
    var voidOsc, voidLFO;
    var wireOsc, wireMod;
    var memoryNoise, memoryMod;

    freq = In.kr(freqBus);

    // Custom params with smoothing
    fluoro = p[0];
    fluoro = Lag.kr(fluoro, 0.05);
    traffic = p[1];
    traffic = Lag.kr(traffic, 0.1);
    void = p[2];
    void = Lag.kr(void, 0.1);
    wire = p[3];
    wire = Lag.kr(wire, 0.05);
    memory = p[4];
    memory = Lag.kr(memory, 0.1);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // === FLUORO (fluorescent buzz) ===
    // 120Hz buzz with harmonics and flicker
    fluoroMod = LFNoise2.kr(5).range(0.95, 1.05);  // Flicker
    fluoroOsc = SinOsc.ar(120 * fluoroMod) * 0.3;
    fluoroOsc = fluoroOsc + (SinOsc.ar(240 * fluoroMod) * 0.2);
    fluoroOsc = fluoroOsc + (SinOsc.ar(360 * fluoroMod) * 0.1);
    // Occasional flicker dropout
    fluoroOsc = fluoroOsc * (1 - (Dust.kr(fluoro * 2) * 0.5).lag(0.01, 0.1));
    // High frequency buzz component
    fluoroOsc = fluoroOsc + (BPF.ar(WhiteNoise.ar, 4000, 0.3) * 0.05);
    fluoroSig = fluoroOsc * fluoro * 0.4;

    // === TRAFFIC (distant wash) ===
    // Filtered noise suggesting distant highway
    trafficNoise = BrownNoise.ar;
    trafficMod = LFNoise2.kr(0.1).range(0.8, 1.2);  // Very slow variation
    trafficSig = LPF.ar(trafficNoise, 300 * trafficMod);
    trafficSig = trafficSig + (BPF.ar(trafficNoise, 150, 0.5) * 0.3);
    // Occasional louder vehicle
    trafficSig = trafficSig * (1 + (LFNoise2.kr(0.05).range(0, 0.5)));
    trafficSig = trafficSig * traffic * 0.3;

    // === VOID (empty resonance) ===
    // Very low, hollow drone
    voidLFO = LFNoise2.kr(0.08).range(0.97, 1.03);
    voidOsc = SinOsc.ar(freq * 0.125 * voidLFO);
    voidOsc = voidOsc + (SinOsc.ar(freq * 0.126) * 0.4);  // Slow beating
    voidOsc = voidOsc + (SinOsc.ar(freq * 0.0625 * voidLFO) * 0.5);  // Sub
    // Add "room tone"
    voidOsc = voidOsc + (LPF.ar(PinkNoise.ar, 80) * 0.2);
    voidSig = voidOsc * void * 0.4 * LFTri.kr(0.05).range(0.6, 1);

    // === WIRE (power lines) ===
    // 60Hz hum with wind modulation
    wireMod = LFNoise2.kr(0.3).range(0.98, 1.02);
    wireOsc = SinOsc.ar(60 * wireMod);
    wireOsc = wireOsc + (SinOsc.ar(120 * wireMod) * 0.4);
    wireOsc = wireOsc + (SinOsc.ar(180 * wireMod) * 0.2);
    // Wind on wires
    wireOsc = wireOsc + (
        BPF.ar(PinkNoise.ar, 800 * LFNoise2.kr(0.5).range(0.8, 1.2), 0.1) * 0.1
    );
    wireSig = wireOsc * wire * 0.3;

    // === MEMORY (ghost sounds) ===
    // Distant, barely perceptible sounds
    memoryNoise = PinkNoise.ar;
    memoryMod = LFNoise2.kr(0.2).range(0.5, 1.5);
    // Distant voice-like filtering
    memorySig = BPF.ar(memoryNoise, 800 * memoryMod, 0.2) * 0.3;
    memorySig = memorySig + (BPF.ar(memoryNoise, 1500 * memoryMod, 0.3) * 0.2);
    // Occasional "words"
    memorySig = memorySig * LFNoise1.kr(3).range(0, 1);
    // Very distant music/radio
    memorySig = memorySig + (
        SinOsc.ar(freq * LFNoise0.kr(0.5).range(1, 2)) *
        LFNoise2.kr(0.3).range(0, 0.1)
    );
    memorySig = LPF.ar(memorySig, 2000) * memory * 0.3;

    // === MIX ===
    sig = fluoroSig + trafficSig + voidSig + wireSig + memorySig;

    // Soft limiting
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.05, 0.3);  // Wide but slow
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] liminal loaded".postln;
