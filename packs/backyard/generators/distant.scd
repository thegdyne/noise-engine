SynthDef(\forge_backyard_distant, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var traffic, birds, wind, distance, timeVal;
    var roadDrone, birdChirp, windCarry, treesRustle, distanceFilter;

    // Theme params
    traffic = In.kr(customBus0);
    birds = In.kr(customBus1);
    wind = In.kr(customBus2);
    distance = In.kr(customBus3);
    timeVal = In.kr(customBus4);

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
    ampVal = In.kr(~params[\amplitude]);

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

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_backyard_distant loaded".postln;
