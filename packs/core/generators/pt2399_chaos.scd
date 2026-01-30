// core/pt2399_chaos — Lightweight end-stage generator
/*
PT2399 Chaos Generator
The unhinged version - dying chip simulation with MADNESS macro

Signal flow: Noise Bursts -> Delay/Chaos -> Degradation -> Filter -> ENV VCA -> Output

Custom params:
  - P1 delay_time: 0.005-5.0 s (longer = more degradation)
  - P2 feedback: 0.0-0.95 (high values = self-oscillation)
  - P3 retrig_rate: 0.1-50 Hz (burst rate)
  - P4 madness: 0.0-1.0 (normal <-> complete meltdown)
  - P5 wet_dry: 0.0-1.0 (dry signal <-> wet chaos)
*/

SynthDef(\pt2399Chaos, { |out, freqBus, customBus0|
    var sig, grain;
    var p = In.kr(customBus0, 5);
    var delayTime, feedback, retrigRate, madness, wetDry;
    var delayed, dry, fbSig, degraded, fbDistort, panPos;
    var internalTrig, jitteredRate, burstEnv;
    var srClock, roundStep, wobbleDepth, pitchWobble;


    delayTime = p[0].clip(0.005, 5.0);
    feedback = p[1].clip(0.0, 0.95);
    retrigRate = p[2];
    madness = p[3];
    wetDry = p[4];

    // === SOUND SOURCE ===
    jitteredRate = retrigRate * LFNoise1.kr(retrigRate * 0.5).range(1 - (madness * 0.5), 1 + (madness * 0.5));
    internalTrig = Impulse.ar(jitteredRate);
    burstEnv = EnvGen.ar(Env.perc(0.001, 0.1 + (madness * 0.2)), internalTrig);

    grain = WhiteNoise.ar * burstEnv;
    grain = grain + (Dust.ar(madness.linexp(0, 1, 1, 500)) * madness * 0.5);

    dry = ~ensure2ch.(grain);  // Dual mono for channel strip panning

    fbSig = LocalIn.ar(2);
    fbDistort = (fbSig * (1 + (madness * 8))).tanh;

    wobbleDepth = madness.linexp(0, 1, 0.001, 0.1);
    pitchWobble = LFNoise1.kr(madness.linexp(0, 1, 0.5, 20)).range(1 - wobbleDepth, 1 + wobbleDepth);
    delayed = DelayC.ar(dry + (fbDistort * feedback), 5.5, (delayTime * pitchWobble).clip(0.001, 5.0));

    srClock = madness.linexp(0, 1, 48000, 4000);
    roundStep = madness.linexp(0, 1, 0.0001, 0.2);
    degraded = Latch.ar(delayed, Impulse.ar(srClock));
    degraded = degraded.round(roundStep);
    degraded = degraded + (PinkNoise.ar * madness * 0.1);

    LocalOut.ar(degraded);

    sig = (dry * (1 - wetDry)) + (degraded * wetDry);
    sig = sig.tanh;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] pt2399Chaos loaded".postln;
