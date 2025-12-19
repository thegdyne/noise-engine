/*
ABYSS Generator
The deep ocean void - crushing darkness with alien life

Features:
  - Crushing pressure drone
  - Dense darkness texture
  - Bioluminescent pings
  - Distant leviathan calls
  - Deep current movement

Custom params:
  - P1 pressure: Weight of the depths
  - P2 dark: Density of darkness
  - P3 biolum: Bright creature pings
  - P4 leviathan: Distant massive creature calls
  - P5 current: Underwater current movement

Primarily drone/continuous - the abyss is always there.
*/

SynthDef(\abyss, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                    midiTrigBus=0, slotIndex=0,
                    customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var pressure, dark, biolum, leviathan, current;
    var trig;
    var pressureSig, darkSig, biolumSig, leviathanSig, currentSig;
    var pressureOsc, pressureLFO;
    var darkNoise, darkMod;
    var biolumPing, biolumTrig;
    var levCall, levMod;
    var currentNoise, currentLFO;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    pressure = In.kr(customBus0);
    pressure = Lag.kr(pressure, 0.1);
    dark = In.kr(customBus1);
    dark = Lag.kr(dark, 0.1);
    biolum = In.kr(customBus2);
    leviathan = In.kr(customBus3);
    leviathan = Lag.kr(leviathan, 0.1);
    current = In.kr(customBus4);
    current = Lag.kr(current, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === PRESSURE (crushing weight) ===
    // Very low frequency drone that pulses slowly
    pressureLFO = LFTri.kr(0.1).range(0.9, 1);  // Slow compression cycle
    pressureOsc = SinOsc.ar(freq * 0.125) * pressureLFO;  // 3 octaves down
    pressureOsc = pressureOsc + (SinOsc.ar(freq * 0.0625) * 0.6);  // 4 octaves down
    // Subsonic rumble
    pressureOsc = pressureOsc + (LPF.ar(BrownNoise.ar, 40) * 0.4);
    pressureSig = pressureOsc * pressure;
    
    // === DARK (density texture) ===
    // Heavily filtered noise with slow modulation
    darkNoise = BrownNoise.ar;
    darkMod = LFNoise2.kr(0.2).range(0.8, 1.2);
    darkSig = LPF.ar(darkNoise, 100 + (dark * 150) * darkMod);
    darkSig = darkSig + (BPF.ar(darkNoise, 60 * darkMod, 0.5) * 0.5);
    darkSig = darkSig * dark * 0.6;
    
    // === BIOLUMINESCENCE (bright pings) ===
    // Random high-frequency pings suggesting deep-sea creatures
    biolumTrig = Dust.ar(2 + (biolum * 8));  // Random triggers
    biolumPing = SinOsc.ar(
        TRand.ar(freq * 3, freq * 8, biolumTrig)  // Random high pitches
    );
    biolumPing = biolumPing * EnvGen.ar(Env.perc(0.001, 0.1 + (TRand.ar(0, 0.2, biolumTrig))), biolumTrig);
    // Add some triggered by clock for rhythmic option
    biolumPing = biolumPing + (
        SinOsc.ar(freq * 5) * EnvGen.ar(Env.perc(0.001, 0.15), trig) * 0.5
    );
    biolumSig = HPF.ar(biolumPing, 800) * biolum * 0.4;
    
    // === LEVIATHAN (distant creature calls) ===
    // Low whale-like calls with pitch bending
    levMod = EnvGen.ar(
        Env([0, 1, 0.8, 0], [0.3, 1.5, 1], \sine),
        Dust.ar(0.15 + (leviathan * 0.2))  // Occasional calls
    );
    levCall = SinOsc.ar(freq * 0.5 * (1 + (levMod * 0.3)));  // Pitch rises then falls
    levCall = levCall + (SinOsc.ar(freq * 0.52) * 0.3);  // Slight detune for depth
    levCall = levCall + (SinOsc.ar(freq * 0.25) * 0.4);  // Sub harmonic
    // FM for organic quality
    levCall = levCall + (SinOsc.ar(freq * 0.5, SinOsc.ar(freq * 0.1) * 1.5) * 0.3);
    levCall = LPF.ar(levCall, 400 + (levMod * 600));
    leviathanSig = levCall * levMod * leviathan;
    
    // === CURRENT (deep water movement) ===
    // Filtered noise with very slow amplitude modulation
    currentNoise = PinkNoise.ar;
    currentLFO = LFNoise2.kr(0.15).range(0.3, 1);
    currentSig = BPF.ar(currentNoise, 150 + (current * 200), 0.6);
    currentSig = currentSig + (LPF.ar(currentNoise, 80) * 0.3);
    currentSig = currentSig * currentLFO * current * 0.5;
    
    // === MIX ===
    sig = pressureSig + darkSig + biolumSig + leviathanSig + currentSig;
    
    // Soft saturation
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.05, 0.4);  // Slow wide movement
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ abyss loaded".postln;
