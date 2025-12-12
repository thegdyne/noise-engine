/*
PT2399 Chaos Generator
The unhinged version - dying chip simulation with MADNESS macro

Signal flow: Noise Bursts → Delay/Chaos → Degradation → Filter → ENVELOPE → Output

Standard params:
  - frequency: not used (noise source)
  - cutoff: post-chaos filter
  - resonance: filter resonance
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] delay_time: 0.005-5.0 s (longer = more degradation)
  - custom[1] feedback: 0.0-0.95 (high values = self-oscillation)
  - custom[2] retrig_rate: 0.1-50 Hz (burst rate, free-running with jitter)
  - custom[3] madness: 0.0-1.0 (THE MACRO: normal PT2399 <-> complete meltdown)
  - custom[4] wet_dry: 0.0-1.0 (dry signal <-> wet chaos)

MADNESS controls:
  - 0.0: Relatively normal PT2399 (mild degradation, stable feedback)
  - 0.5: Getting weird (more artifacts, wobble, crackle)
  - 1.0: Complete meltdown (self-oscillation, extreme bitcrush, chaos)

RTG gives rhythmic chaos bursts rather than constant noise wall.
Jitter amount increases with madness for more unpredictable timing.

ENV OFF = drone (continuous output based on RTG)
ENV ON = clock-synced envelope gates final output

See also: PT2399 for the musical/tame version
*/

SynthDef(\pt2399Chaos, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, grain, env, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockRate, allTrigs, clockTrig;
    var delayTime, feedback, retrigRate, madness, wetDry;
    var delayed, dry, fbSig, degraded, fbDistort;
    var degradeAmt, chaosAmt;
    var degradeNormal, degradeCrazy, chaosNormal, chaosCrazy;
    var fbMax, fbGain, wobbleDepth, wobbleRate, pitchWobble;
    var srClockNormal, srClockCrazy, srClock, roundStep;
    var internalTrig, jitteredRate, burstEnv;
    
    // Read standard params
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);  // 0=OFF, 1=CLK, 2=MIDI
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    delayTime = In.kr(customBus0).clip(0.005, 5.0);
    feedback = In.kr(customBus1).clip(0.0, 0.95);
    retrigRate = In.kr(customBus2).clip(0.1, 50.0);
    madness = In.kr(customBus3).clip(0.0, 1.0);
    wetDry = In.kr(customBus4).clip(0.0, 1.0);
    
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
    
    // === INTERNAL TRIGGER WITH JITTER ===
    // Jitter increases with madness - more unpredictable at high madness
    jitteredRate = retrigRate * LFNoise1.kr(retrigRate * 0.5).range(
        1 - (0.3 * madness),  // up to 30% slower
        1 + (0.5 * madness)   // up to 50% faster
    );
    internalTrig = Impulse.ar(jitteredRate);
    
    // Burst envelope - short attack, variable decay
    burstEnv = EnvGen.ar(
        Env.perc(0.001, LFNoise1.kr(2).range(0.01, 0.1 + (madness * 0.2))),
        internalTrig
    );
    
    // === SOUND SOURCE ===
    grain = WhiteNoise.ar(0.7);
    // Gate the noise with burst envelope
    sig = grain * burstEnv;
    sig = (sig * 2).tanh * 0.6;
    
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
    degraded = LPF.ar(fbDistort, filterFreq.clip(100, 16000));
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
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, ~clockRates.size);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // MIDI trigger - read all 8 channels and select by slotIndex
    allMidiTrigs = In.ar(midiTrigBus, 8);
    midiTrig = Select.ar(slotIndex, allMidiTrigs);
    
    // Select trigger based on envSource: 0=none, 1=clock, 2=midi
    trig = Select.ar(envSource, [
        DC.ar(0),      // 0: OFF - no triggers
        clockTrig,     // 1: CLK - clock triggers only  
        midiTrig       // 2: MIDI - midi triggers only
    ]);
    
    // Envelope
    env = EnvGen.ar(Env.perc(attack, decay), trig);
    
    // Apply envelope only when envSource > 0, otherwise drone
    sig = sig * Select.kr(envSource > 0, [1.0, env]);
    
    // Safety limiting
    sig = LeakDC.ar(sig);
    sig = Limiter.ar(sig * amp, 0.99, 0.01);
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Chaos loaded".postln;
