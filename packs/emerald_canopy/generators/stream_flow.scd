// Stream Flow - Water texture with bubbling flow
// Role: motion | Family: texture/noise

SynthDef(\forge_emerald_canopy_stream_flow, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                               filterTypeBus, envEnabledBus, envSourceBus=0,
                                               clockRateBus, clockTrigBus,
                                               midiTrigBus=0, slotIndex=0,
                                               customBus0, customBus1, customBus2, customBus3, customBus4,
                                               portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flow, rocks, splash, curl, bubble;
    var flowNoise, flowLfo, rockResonance, splashSound, bubbleSound, curlLfo;
    var bubbleTrig, bubbleFreq, bubbleEnv;

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

    // Theme params
    flow = In.kr(customBus0);     // Movement speed
    rocks = In.kr(customBus1);    // Resonant bumps
    splash = In.kr(customBus2);   // Transients
    curl = In.kr(customBus3);     // Filter movement
    bubble = In.kr(customBus4);   // Pitched pops

    // Flow LFO - organic water movement
    flowLfo = LFNoise2.kr(flow.linexp(0, 1, 0.3, 3));

    // Base flow - filtered noise
    flowNoise = PinkNoise.ar + (BrownNoise.ar * 0.5);
    flowNoise = LPF.ar(flowNoise, flow.linexp(0, 1, 500, 4000) * (1 + (flowLfo * 0.3)));

    // Curl - modulated bandpass for swirling
    curlLfo = SinOsc.kr(curl.linexp(0, 1, 0.1, 2)) * curl;
    flowNoise = flowNoise + (BPF.ar(
        flowNoise,
        freq * (1 + curlLfo),
        0.3
    ) * curl * 0.5);

    // Rocks - resonant bumps (comb filtering)
    rockResonance = CombL.ar(
        flowNoise * rocks,
        0.1,
        (freq * rocks.linexp(0, 1, 0.5, 2)).reciprocal.clip(0.002, 0.1),
        rocks.linexp(0, 1, 0.05, 0.3)
    ) * 0.4;

    // Splash - random transients
    splashSound = Dust.ar(splash.linexp(0, 1, 1, 30)) * WhiteNoise.ar;
    splashSound = HPF.ar(splashSound, 2000) * splash * 0.4;
    splashSound = splashSound * EnvGen.ar(Env.perc(0.001, 0.05), Dust.kr(splash.linexp(0, 1, 1, 20)));

    // Bubbles - pitched pops
    bubbleTrig = Dust.kr(bubble.linexp(0, 1, 0.5, 15));
    bubbleFreq = TRand.kr(freq * 2, freq * 8, bubbleTrig);
    bubbleEnv = EnvGen.ar(Env.perc(0.001, 0.03), bubbleTrig);
    bubbleSound = SinOsc.ar(bubbleFreq) * bubbleEnv * bubble * 0.3;

    // Add subtle pitch drop to bubbles
    bubbleSound = bubbleSound + (SinOsc.ar(bubbleFreq * 0.5) * bubbleEnv * bubble * 0.15);

    sig = flowNoise + rockResonance + splashSound + bubbleSound;

    // Stereo movement like water flowing
    sig = Balance2.ar(
        sig,
        DelayN.ar(sig, 0.02, 0.01 + (flowLfo.abs * 0.01)),
        flowLfo * flow
    );

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_stream_flow loaded".postln;
