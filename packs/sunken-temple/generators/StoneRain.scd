// sunken-temple/StoneRain — Lightweight end-stage generator
/*
STONERAIN Generator
Rain falling on ancient stone surfaces

Features:
  - Filtered rain noise
  - Stone impact resonance
  - Pool splashes
  - Running water

Custom params:
  - P1 drops: Rain density
  - P2 stone: Surface resonance
  - P3 pool: Water pooling
  - P4 distance: Spatial depth
  - P5 flow: Running streams
*/

SynthDef(\stonerain, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var drops, stone, pool, distance, flow;
    var rainSig, stoneSig, poolSig, flowSig;
    var dropTrig, stoneRes;

    freq = In.kr(freqBus);

    drops = p[0];
    drops = Lag.kr(drops, 0.1);
    stone = p[1];
    stone = Lag.kr(stone, 0.1);
    pool = p[2];
    pool = Lag.kr(pool, 0.1);
    distance = p[3];
    distance = Lag.kr(distance, 0.2);
    flow = p[4];
    flow = Lag.kr(flow, 0.1);

    // === RAIN (filtered noise) ===
    rainSig = WhiteNoise.ar;
    rainSig = BPF.ar(rainSig, 3000 + (LFNoise1.kr(2).range(-500, 500)), 0.5);
    rainSig = rainSig * (1 + (LFNoise1.kr(0.5).range(-0.3, 0.3)));  // Intensity variation
    // Distance filtering
    rainSig = LPF.ar(rainSig, LinExp.kr(distance, 0, 1, 8000, 2000));
    rainSig = rainSig * drops * 0.4;

    // === STONE (impact resonance) ===
    dropTrig = Dust.ar(20 + (drops * 60));
    stoneRes = SinOsc.ar(freq * TRand.ar(1, 4, dropTrig));
    stoneRes = stoneRes * EnvGen.ar(Env.perc(0.001, 0.05), dropTrig);
    stoneRes = BPF.ar(stoneRes + (dropTrig * 0.5), freq * 2, 0.2);
    stoneSig = stoneRes * stone * 0.3;

    // === POOL (water splashes) ===
    poolSig = SinOsc.ar(
        freq * 3 * TRand.ar(0.8, 1.5, Dust.ar(pool * 15)),
        0,
        EnvGen.ar(Env.perc(0.001, 0.08), Dust.ar(pool * 15))
    );
    // Ripple effect
    poolSig = CombL.ar(poolSig, 0.1, 0.03, 0.3);
    poolSig = LPF.ar(poolSig, 4000);
    poolSig = poolSig * pool * 0.4;

    // === FLOW (running water) ===
    flowSig = PinkNoise.ar;
    flowSig = BPF.ar(flowSig, 600 * LFNoise2.kr(0.5).range(0.7, 1.4), 0.4);
    flowSig = flowSig + (BPF.ar(PinkNoise.ar, 1500, 0.3) * 0.5);
    flowSig = flowSig * LFNoise1.kr(1 + flow).range(0.5, 1);
    flowSig = flowSig * flow * 0.3;

    // === SPATIAL (distance reverb) ===
    sig = rainSig + stoneSig + poolSig + flowSig;
    sig = sig + (CombL.ar(sig, 0.3, 0.11, distance * 2) * distance * 0.3);
    sig = sig + (CombL.ar(sig, 0.3, 0.17, distance * 1.5) * distance * 0.2);

    sig = sig.tanh;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] stonerain loaded".postln;
