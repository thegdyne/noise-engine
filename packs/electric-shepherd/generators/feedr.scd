// electric-shepherd/feedr — Lightweight end-stage generator
/*
FEEDR Generator
The charging station - industrial power infrastructure

Features:
  - Transformer hum (50/60Hz harmonics)
  - Power cycling rhythm
  - Energy transfer pulse
  - Surge events
  - Aged equipment decay

Custom params:
  - P1 hum: Transformer hum intensity
  - P2 cycle: Power cycling rhythm
  - P3 transfer: Energy transfer pulse
  - P4 surge: Power surge events
  - P5 age: Equipment decay artifacts

The machine that feeds the empty shells.
*/

SynthDef(\feedr, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var hum, cycle, transfer, surge, age;
    var trig;
    var humSig, cycleSig, transferSig, surgeSig, ageSig;
    var humOsc, humMod;
    var cycleLFO, cycleOsc;
    var transferEnv, transferOsc;
    var surgeEnv, surgeOsc;
    var ageNoise, ageMod;

    freq = In.kr(freqBus);

    // Custom params with smoothing
    hum = p[0];
    hum = Lag.kr(hum, 0.05);
    cycle = p[1];
    cycle = Lag.kr(cycle, 0.05);
    transfer = p[2];
    surge = p[3];
    age = p[4];
    age = Lag.kr(age, 0.05);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // === HUM (transformer harmonics) ===
    // 50Hz mains hum with harmonics
    humMod = LFNoise2.kr(0.2).range(0.99, 1.01);
    humOsc = SinOsc.ar(50 * humMod);  // Fundamental
    humOsc = humOsc + (SinOsc.ar(100 * humMod) * 0.5);  // 2nd harmonic
    humOsc = humOsc + (SinOsc.ar(150 * humMod) * 0.3);  // 3rd
    humOsc = humOsc + (SinOsc.ar(200 * humMod) * 0.2);  // 4th
    humOsc = humOsc + (SinOsc.ar(250 * humMod) * 0.15); // 5th
    // Slight beating from nearby equipment
    humOsc = humOsc + (SinOsc.ar(50.5) * 0.2);
    humSig = humOsc * hum * 0.3;

    // === CYCLE (power rhythm) ===
    // Slow rhythmic pulse of charging cycle
    cycleLFO = LFPulse.kr(0.2 + (cycle * 0.5), 0, 0.6).lag(0.3);
    cycleOsc = SinOsc.ar(freq * 0.5) * cycleLFO;
    cycleOsc = cycleOsc + (LPF.ar(Saw.ar(freq * 0.25), 200) * cycleLFO * 0.3);
    cycleSig = cycleOsc * cycle * 0.4;

    // === TRANSFER (energy pulse) ===
    // Triggered bursts of energy flow
    transferEnv = EnvGen.ar(Env.perc(0.01, 0.5, 1, -4), trig);
    transferOsc = SinOsc.ar(freq * (1 + (transferEnv * 0.5)));  // Rising pitch
    transferOsc = transferOsc + (Pulse.ar(freq * 2, 0.3) * 0.3);
    // Add "flow" noise
    transferOsc = transferOsc + (BPF.ar(WhiteNoise.ar, freq * 2, 0.3) * transferEnv);
    transferSig = transferOsc * transferEnv * transfer;

    // === SURGE (power events) ===
    // Random surge events
    surgeEnv = EnvGen.ar(
        Env.perc(0.001, 0.3, 1, -6),
        trig + Dust.ar(surge * 2)
    );
    surgeOsc = SinOsc.ar(freq * 4) * surgeEnv;
    surgeOsc = surgeOsc + (HPF.ar(WhiteNoise.ar, 2000) * surgeEnv * 0.5);
    // Voltage sag effect
    surgeOsc = surgeOsc + (SinOsc.ar(50 * (1 - (surgeEnv * 0.1))) * surgeEnv * 0.3);
    surgeSig = surgeOsc * surge * 0.5;

    // === AGE (decay artifacts) ===
    // Crackle, buzz, failing components
    ageNoise = Dust.ar(age * 50) * 0.3;
    ageNoise = ageNoise + (Crackle.ar(1.5 + (age * 0.3)) * 0.1);
    // Intermittent buzz from loose connection
    ageMod = LFNoise0.kr(2).range(0, 1) > (1 - age);
    ageNoise = ageNoise + (BPF.ar(Saw.ar(100), 800, 0.3) * ageMod * 0.2);
    ageSig = ageNoise * age;

    // === MIX ===
    sig = humSig + cycleSig + transferSig + surgeSig + ageSig;

    // Soft saturation
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.1, 0.15);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] feedr loaded".postln;
