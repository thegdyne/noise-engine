// seagrass_bay/bubble_rise — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_bubble_rise, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var size, rise, cluster, pop, air;
    var bubbleFreq, riseEnv, popNoise, bubbleTone, airNoise, clusterMod;

    // Standard bus reads
    freq = In.kr(freqBus);

    size = p[0];  // Bubble size -> pitch
    rise = p[1];  // Rise speed
    cluster = p[2];  // Multiple bubbles
    pop = p[3];  // Surface pop
    air = p[4];  // Breathiness

    // Bubble frequency - small bubbles = higher pitch
    bubbleFreq = freq * size.linexp(0, 1, 2.0, 0.5);

    // Rise envelope - pitch rises as bubble ascends
    riseEnv = LFSaw.kr(rise.linexp(0, 1, 0.5, 4), 1).range(1, 1 + (rise * 0.3));
    bubbleFreq = bubbleFreq * riseEnv;

    // Main bubble tone - resonant sine-ish
    bubbleTone = SinOsc.ar(bubbleFreq) * 0.5;
    bubbleTone = bubbleTone + (SinOsc.ar(bubbleFreq * 2.02) * 0.2);

    // Cluster - add slightly detuned copies
    clusterMod = Mix.fill(3, { |i|
        var detune = LFNoise1.kr(2).range(-0.03, 0.03) * cluster;
        SinOsc.ar(bubbleFreq * (1 + detune + (i * 0.01))) * (cluster / 4);
    });
    bubbleTone = bubbleTone + clusterMod;

    // Pop transient - filtered noise burst
    popNoise = BPF.ar(WhiteNoise.ar, bubbleFreq * 3, 0.3) * pop * 2;
    popNoise = popNoise * EnvGen.kr(Env.perc(0.001, 0.05), Impulse.kr(rise.linexp(0, 1, 0.5, 4)));

    // Air - continuous breathy texture
    airNoise = BPF.ar(PinkNoise.ar, bubbleFreq * 1.5, 0.5) * air * 0.3;

    sig = bubbleTone + popNoise + airNoise;

    // Random stereo placement for bubbles
    sig = Pan2.ar(sig, LFNoise1.kr(1).range(-0.6, 0.6));

    // Standard output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_bubble_rise loaded".postln;
