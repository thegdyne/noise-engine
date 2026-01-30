// kaiju_beats/city — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_city, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var traffic, steel, jackhammer, sirens, crowd;
    var trafficRumble, steelWork, hammerHits, sirenWail, crowdMurmur;

    traffic = p[0];  // P1: Traffic rumble
    steel = p[1];  // P2: Steel work/girders
    jackhammer = p[2];  // P3: Jackhammer intensity
    sirens = p[3];  // P4: Distant sirens
    crowd = p[4];  // P5: Crowd murmur

    freq = In.kr(freqBus);
    ampVal = 0.2;

    // Traffic rumble - filtered brown noise
    trafficRumble = LPF.ar(BrownNoise.ar(0.5), 150 + (traffic * 200));
    trafficRumble = trafficRumble * (1 + (LFNoise2.kr(0.3) * 0.3));
    trafficRumble = trafficRumble * traffic * 0.5;

    // Steel work - resonant clangs tuned to freq
    steelWork = Ringz.ar(
        Dust.ar(1 + (steel * 5)),
        [freq * 2, freq * 3.2, freq * 5.1],
        [0.3, 0.2, 0.15]
    ).sum * steel * 0.2;

    // Jackhammer - rhythmic noise bursts
    hammerHits = BPF.ar(WhiteNoise.ar(1), 800, 0.3);
    hammerHits = hammerHits * LFPulse.ar(8 + (jackhammer * 8), 0, 0.3);
    hammerHits = hammerHits * jackhammer * 0.3;

    // Sirens - doppler-shifted sine
    sirenWail = SinOsc.ar(
        LFNoise1.kr(0.5).range(600, 1200) * (1 + (sirens * 0.5))
    );
    sirenWail = sirenWail * LFNoise2.kr(0.2).range(0.3, 1);
    sirenWail = sirenWail * sirens * 0.15;

    // Crowd murmur - filtered noise with formant-like bumps
    crowdMurmur = PinkNoise.ar(0.3);
    crowdMurmur = BPF.ar(crowdMurmur, 300, 0.5) + (BPF.ar(crowdMurmur, 1200, 0.4) * 0.5);
    crowdMurmur = crowdMurmur * (1 + (LFNoise2.kr(2) * 0.3));
    crowdMurmur = crowdMurmur * crowd * 0.4;

    // Mix all city sounds
    sig = trafficRumble + steelWork + hammerHits + sirenWail + crowdMurmur;

    // Add base noise bed for drone safety
    sig = sig + (PinkNoise.ar(0.03));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_city loaded".postln;
