// BEACON - Lighthouse sweep melodic call
// Source: Lighthouse rotation, guiding light, calling tone
// Role: Foreground - melodic with rotating intensity

SynthDef(\forge_beacon_vigil_beacon, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var swep, beam, call, pier, fade;
    var rotation, beamEnv, melodic, ground, distance;

    // Custom params
    swep = In.kr(customBus0);  // Sweep rate
    beam = In.kr(customBus1);  // Beam focus
    call = In.kr(customBus2);  // Melodic character
    pier = In.kr(customBus3);  // Grounding
    fade = In.kr(customBus4);  // Distance fade

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // === DSP: Lighthouse Beacon ===

    // Rotation: phasor for continuous sweep
    rotation = LFSaw.kr(swep.linexp(0, 1, 0.05, 0.8), 1).range(0, 2pi);

    // Beam envelope: focused pulse as beam sweeps past
    // Uses a Gaussian-like shape based on beam width
    beamEnv = (rotation - pi).abs;
    beamEnv = (beamEnv / (beam.linexp(0, 1, 2, 0.3))).neg.exp;
    beamEnv = beamEnv.clip(0, 1);
    // Smooth the beam
    beamEnv = Lag.kr(beamEnv, 0.05);

    // Melodic core: bright singing tone
    melodic = SinOsc.ar(freq);
    melodic = melodic + (SinOsc.ar(freq * 2) * call * 0.4);
    melodic = melodic + (SinOsc.ar(freq * 3) * call * 0.2);
    melodic = melodic + (SinOsc.ar(freq * 4) * call * 0.1);

    // Add slight vibrato for calling quality
    melodic = melodic + (SinOsc.ar(freq * (1 + (SinOsc.kr(5).range(-0.003, 0.003)))) * call * 0.3);

    // Triangle for additional presence
    melodic = melodic + (LFTri.ar(freq) * (1 - call) * 0.4);

    // Ground/pier: lower register anchor
    ground = SinOsc.ar(freq * 0.5) * pier * 0.4;
    ground = ground + (LFTri.ar(freq * 0.25) * pier * 0.2);

    sig = melodic + ground;

    // Apply beam envelope - intensity rises and falls with rotation
    sig = sig * beamEnv.linlin(0, 1, 0.15, 1);

    // Distance fade: allpass + LP for far-away quality
    distance = AllpassC.ar(sig, 0.1, fade.linlin(0, 1, 0.01, 0.08), fade * 2);
    distance = LPF.ar(distance, fade.linexp(0, 1, 12000, 3000));
    sig = (sig * (1 - fade)) + (distance * fade);

    // Subtle stereo from rotation
    sig = [
        sig * (1 + (rotation.cos * 0.1)),
        sig * (1 + (rotation.sin * 0.1))
    ];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95); sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_beacon loaded".postln;
