/*
PT2399 Chaos Generator
The unhinged version - dying chip simulation with MADNESS macro

Signal flow: Noise → Delay/Chaos → Degradation → Filter → ENVELOPE → Output

Standard params:
  - frequency: not used (noise source)
  - cutoff: post-chaos filter
  - resonance: filter resonance
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] delay_time: 0.005-5.0 s (longer = more degradation)
  - custom[1] feedback: 0.0-0.95 (high values = self-oscillation)
  - custom[2] wet_dry: 0.0-1.0 (dry signal <-> wet chaos)
  - custom[3] madness: 0.0-1.0 (THE MACRO: normal PT2399 <-> complete meltdown)
  - custom[4] tone: 0.0-1.0 (dark <-> bright)

MADNESS controls:
  - 0.0: Relatively normal PT2399 (mild degradation, stable feedback)
  - 0.5: Getting weird (more artifacts, wobble, crackle)
  - 1.0: Complete meltdown (self-oscillation, extreme bitcrush, chaos)

ENV OFF = drone (continuous output)
ENV ON = clock-synced envelope gates final output

See also: PT2399 for the musical/tame version
*/

SynthDef(\pt2399Chaos, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, grain, env, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockRate, allTrigs, clockTrig;
    var delayTime, feedback, wetDry, madness, tone;
    var delayed, dry, fbSig, degraded, fbDistort;
    var degradeAmt, chaosAmt;
    var degradeNormal, degradeCrazy, chaosNormal, chaosCrazy;
    var fbMax, fbGain, wobbleDepth, wobbleRate, pitchWobble;
    var srClockNormal, srClockCrazy, srClock, roundStep;
    
    // Read standard params
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    delayTime = In.kr(customBus0).clip(0.005, 5.0);
    feedback = In.kr(customBus1).clip(0.0, 0.95);
    wetDry = In.kr(customBus2).clip(0.0, 1.0);
    madness = In.kr(customBus3).clip(0.0, 1.0);
    tone = In.kr(customBus4).clip(0.0, 1.0);
    
    // === MORPHING DEGRADE/CHAOS AMOUNTS ===
    // "Normal PT2399" profile (milder)
    degradeNormal = delayTime.linexp(0.005, 0.8, 0.02, 0.5);
    chaosNormal = feedback.linlin(0, 0.7, 0.0, 0.4).max(0);
    
    // "Crazy" profile (full chaos)
    degradeCrazy = delayTime.linexp(0.005, 5.0, 0.01, 1.0);
    chaosCrazy = feedback.linexp(0, 0.95, 0.01, 1.5);
    
    // Morph between them with madness
    degradeAmt = degradeNormal + ((degradeCrazy - degradeNormal) * madness);
    chaosAmt = chaosNormal + ((chaosCrazy - chaosNormal) * madness);
    degradeAmt = degradeAmt.clip(0.0, 1.0);
    chaosAmt = chaosAmt.clip(0.0, 2.0);
    
    // === SOUND SOURCE ===
    grain = WhiteNoise.ar(0.7);
    sig = (grain * 2).tanh * 0.6;
    
    panPos = LFNoise1.kr(0.5).range(-0.5, 0.5);
    dry = Pan2.ar(sig, panPos);
    
    // === FEEDBACK PATH WITH MADNESS-SCALED CHAOS ===
    fbSig = LocalIn.ar(2);
    
    // Feedback gain: <1 at madness=0, >1 (self-osc) at madness=1
    fbMax = LinLin.kr(madness, 0, 1, 0.99, 1.5);
    fbGain = feedback.linexp(0, 0.95, 0.2, fbMax);
    
    // Delay-time modulation: subtle at normal, wild at mad
    wobbleDepth = LinLin.kr(madness, 0, 1, 0.02, 0.1);
    wobbleRate = 0.5 + (chaosAmt * LinLin.kr(madness, 0, 1, 1, 3));
    
    pitchWobble = LFNoise2.kr(wobbleRate).range(
        1 - (chaosAmt * wobbleDepth),
        1 + (chaosAmt * wobbleDepth)
    );
    
    // Main delay
    delayed = DelayC.ar(
        dry + (fbSig * fbGain),
        5.0,
        (delayTime * pitchWobble).clip(0.001, 5.0)
    );
    
    // === DEGRADATION CHAIN (madness-scaled) ===
    // Sample-rate reduction
    srClockNormal = 48000 / (1 + (degradeAmt * 5) + (chaosAmt * 2));
    srClockCrazy = 48000 / (1 + (degradeAmt * 30) + (chaosAmt * 20));
    srClock = srClockNormal + ((srClockCrazy - srClockNormal) * madness);
    
    degraded = Latch.ar(delayed, Impulse.ar(srClock));
    
    // Bit depth reduction
    roundStep = 0.0005 + (0.0045 * degradeAmt * madness);
    degraded = degraded.round(roundStep);
    
    // === DISTORTION / NOISE (madness-scaled) ===
    // Base saturation (always on - PT2399 is never clean)
    fbDistort = (degraded * (1 + (chaosAmt * 4 * (0.3 + (0.7 * madness))))).tanh;
    
    // Extra folding only when madness > 0
    fbDistort = fbDistort + (
        (fbDistort * chaosAmt * 4 * madness).fold(-1, 1) * chaosAmt * madness
    );
    
    // Ring-mod chaos scales with madness
    fbDistort = fbDistort * (
        1 + (SinOsc.ar(delayTime.reciprocal * chaosAmt * (10 + (40 * madness)))
             * chaosAmt * 0.5 * madness)
    );
    
    // Crunchy filter
    fbDistort = RLPF.ar(
        fbDistort,
        (2000
         + (chaosAmt * 4000)
         + (LFNoise1.kr(2) * chaosAmt * 2000 * madness)
        ).clip(100, 16000),
        0.4 + (chaosAmt * 0.3) + (madness * 0.1)
    );
    
    // Noise and crackle (near-zero at madness=0)
    fbDistort = fbDistort + (Dust.ar(50 * chaosAmt * madness) * 0.3 * chaosAmt * madness);
    fbDistort = fbDistort + (Crackle.ar(1.3 + (chaosAmt * 0.5 * madness)) * 0.1 * chaosAmt * madness);
    fbDistort = fbDistort + (
        PinkNoise.ar(0.05) *
        degradeAmt *
        (0.3 + (0.7 * madness)) *
        (0.3 + (0.7 * chaosAmt))
    );
    
    // === BANDWIDTH LIMITING ===
    degraded = LPF.ar(fbDistort, tone.linexp(0, 1, 1500, 12000));
    degraded = HPF.ar(degraded, 20 + (chaosAmt * 100));
    
    // Mix delay with degraded
    delayed = (delayed * (1 - degradeAmt.sqrt)) + (degraded * degradeAmt.sqrt);
    delayed = (delayed * 1.5).tanh;
    
    // Send to feedback loop
    LocalOut.ar(delayed);
    
    // === WET/DRY MIX ===
    sig = (dry * (1 - wetDry)) + (delayed * wetDry);
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, 12);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    // Safety limiting
    sig = LeakDC.ar(sig);
    sig = Limiter.ar(sig * amp, 0.99, 0.01);
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Chaos loaded".postln;
