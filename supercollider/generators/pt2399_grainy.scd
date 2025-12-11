/*
PT2399 Grainy Generator
Bandpass-filtered noise through lo-fi delay - the "musical" version

Signal flow: Noise → Bandpass(FRQ) → Delay → Light Degradation → Filter → ENVELOPE → Output

Standard params:
  - frequency: bandpass center frequency (pitched noise)
  - cutoff: post-delay filter
  - resonance: filter resonance
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] delay_time: 0.001-0.5 s (short = comb, long = echo)
  - custom[1] feedback: 0.0-0.85 (stays stable)
  - custom[2] bandwidth: 0.01-1.0 (narrow = tonal, wide = noisy)
  - custom[3] tone: 0.0-1.0 (dark <-> bright delay character)
  - custom[4] grit: 0.0-1.0 (clean <-> lo-fi)

ENV OFF = drone (continuous output)
ENV ON = clock-synced envelope gates final output

See also: PT2399 Chaos for the unhinged version
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, source, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockRate, allTrigs, clockTrig;
    var delayTime, feedback, bandwidth, tone, grit;
    var delayed, dry, fbSig, pitchWobble, degraded;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    delayTime = In.kr(customBus0);   // 0.001-0.5 s
    feedback = In.kr(customBus1);    // 0.0-0.85 (tamer)
    bandwidth = In.kr(customBus2);   // 0.01-1.0
    tone = In.kr(customBus3);        // 0.0-1.0 (dark <-> bright)
    grit = In.kr(customBus4);        // 0.0-1.0 (clean <-> lo-fi)
    
    // === SOUND SOURCE ===
    // White noise through resonant bandpass - FRQ controls pitch
    source = WhiteNoise.ar(0.8);
    source = BPF.ar(source, freq.clip(20, 16000), bandwidth.linexp(0, 1, 0.01, 0.5));
    source = source * 4;
    
    // Gentle saturation
    source = (source * 1.3).tanh;
    
    // Stereo spread
    panPos = LFNoise1.kr(0.3).range(-0.4, 0.4);
    dry = Pan2.ar(source, panPos);
    
    // === FEEDBACK DELAY PATH ===
    fbSig = LocalIn.ar(2);
    
    // Subtle pitch wobble (PT2399 clock instability)
    pitchWobble = LFNoise2.kr(0.3 + (grit * 2)).range(
        1 - (grit * 0.03),
        1 + (grit * 0.03)
    );
    
    // Main delay
    delayed = DelayC.ar(
        dry + (fbSig * feedback),
        0.5,
        (delayTime * pitchWobble).clip(0.0001, 0.5)
    );
    
    // === GENTLE DEGRADATION ===
    // Mild sample rate reduction when grit is up
    degraded = Latch.ar(delayed, Impulse.ar(48000 / (1 + (grit * 10))));
    
    // Very light bit reduction
    degraded = degraded.round(0.001 * (1 + (grit * 2)));
    
    // Soft saturation
    degraded = (degraded * (1 + (grit * 2))).tanh;
    
    // Mix clean/degraded
    delayed = (delayed * (1 - grit)) + (degraded * grit);
    
    // Tone control (filter in feedback path)
    delayed = LPF.ar(delayed, tone.linexp(0, 1, 2000, 12000));
    delayed = HPF.ar(delayed, 40);
    
    // Light saturation
    delayed = (delayed * 1.1).tanh;
    
    // Send to feedback loop
    LocalOut.ar(delayed);
    
    // === OUTPUT MIX ===
    sig = (dry * 0.5) + (delayed * 0.7);
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, 12);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
