// backyard/distant — Lightweight end-stage generator
SynthDef(\forge_backyard_distant, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var traffic, birds, wind, distance, timeVal;
    var roadDrone, birdChirp, windCarry, treesRustle, distanceFilter;

    traffic = p[0];
    birds = p[1];
    wind = p[2];
    distance = p[3];
    timeVal = p[4];

    freq = In.kr(freqBus);

    // Distance filter cutoff - further = darker
    distanceFilter = distance.linexp(0, 1, 3000, 400);

    // Road drone - continuous low rumble with passing cars
    roadDrone = BrownNoise.ar(0.4) + PinkNoise.ar(0.2);
    roadDrone = LPF.ar(roadDrone, 250);
    // Passing cars - swells in the drone
    roadDrone = roadDrone * (1 + (LFNoise1.kr(traffic.linlin(0, 1, 0.1, 0.5)).range(0, 0.5)));
    roadDrone = roadDrone * traffic * 0.4;

    // Bird chirps - filtered high pings
    birdChirp = Dust.ar(birds.linexp(0, 1, 0.5, 5));
    birdChirp = SinOsc.ar(
        freq * LFNoise0.kr(3).range(4, 12),
        0,
        Decay.ar(birdChirp, LFNoise1.kr(2).range(0.05, 0.15))
    );
    birdChirp = birdChirp * birds * 0.25;

    // Wind carrying sound
    windCarry = PinkNoise.ar(0.3);
    windCarry = BPF.ar(windCarry, LFNoise1.kr(0.2).range(300, 1200), 0.4);
    windCarry = windCarry * LFNoise2.kr(0.3).range(0.3, 1);
    windCarry = windCarry * wind * 0.35;

    // Trees/fir rustling in park
    treesRustle = WhiteNoise.ar(0.15);
    treesRustle = BPF.ar(treesRustle, 3000, 0.6);
    treesRustle = treesRustle * LFNoise1.kr(wind.linlin(0, 1, 0.5, 3)).range(0.2, 1);
    treesRustle = treesRustle * wind * 0.3;

    // Mix all components
    sig = roadDrone + birdChirp + windCarry + treesRustle;

    // Apply distance filtering
    sig = LPF.ar(sig, distanceFilter);

    // Time of day warmth - slight tonal color
    sig = sig + (SinOsc.ar(freq * 0.5, 0, 0.02 * timeVal * (1 - distance)));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_backyard_distant loaded".postln;
