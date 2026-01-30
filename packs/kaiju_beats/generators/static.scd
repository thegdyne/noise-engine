// kaiju_beats/static — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_static, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tune, burst, scan, crackle, carrier;
    var radioNoise, tuningWhine, staticBursts, scanSweep;

    tune = p[0];  // P1: Tuning dial - sweeps frequency
    burst = p[1];  // P2: Static burst intensity
    scan = p[2];  // P3: Frequency scanning rate
    crackle = p[3];  // P4: Crackle/pop amount
    carrier = p[4];  // P5: Carrier tone mix

    freq = In.kr(freqBus);
    ampVal = 0.2;

    // Base radio static
    radioNoise = WhiteNoise.ar(0.3) + (PinkNoise.ar(0.2));
    radioNoise = BPF.ar(radioNoise, freq * 2 + (tune * 2000), 0.3);

    // Tuning whine - carrier tone
    tuningWhine = SinOsc.ar(freq + (tune * 500) + (LFNoise1.kr(scan * 5) * 100));
    tuningWhine = tuningWhine * carrier * 0.3;

    // Static bursts - rhythmic
    staticBursts = WhiteNoise.ar(1);
    staticBursts = staticBursts * Dust.ar(3 + (burst * 20));
    staticBursts = staticBursts * burst * 0.5;

    // Scan sweep - slow frequency movement
    scanSweep = LFSaw.kr(0.1 + (scan * 0.5)).range(500, 3000);
    radioNoise = radioNoise + BPF.ar(WhiteNoise.ar(0.2), scanSweep, 0.1);

    // Crackle pops
    staticBursts = staticBursts + (Dust.ar(crackle * 30) * crackle * 0.4);

    // Mix
    sig = radioNoise + tuningWhine + staticBursts;

    // Add continuous bed for drone mode
    sig = sig + (PinkNoise.ar(0.05));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_static loaded".postln;
