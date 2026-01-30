// duga/coldwar — Lightweight end-stage generator
SynthDef(\forge_duga_coldwar, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tens, throb, feed, dark, dread;
    var baseDrone, throbMod, darkSig, dreadMod, feedAmt;

    freq = In.kr(freqBus);

    tens = p[0];
    throb = p[1];
    feed = p[2];
    dark = p[3];
    dread = p[4];

    // Throbbing modulation
    throbMod = SinOsc.kr(throb.linexp(0, 1, 0.2, 3)).range(0.6, 1);

    // Dread modulation - slow unease
    dreadMod = LFNoise2.kr(0.1).range(1 - (dread * 0.1), 1 + (dread * 0.1));

    // Feedback amount based on tension
    feedAmt = feed.linlin(0, 1, 0.2, 0.85) * tens.linlin(0, 1, 0.8, 1.2);
    feedAmt = feedAmt.clip(0, 0.95);

    // Main feedback FM drone
    baseDrone = SinOscFB.ar(freq * 0.5 * dreadMod, feedAmt);
    baseDrone = baseDrone + SinOscFB.ar(freq * dreadMod, feedAmt * 0.7) * 0.5;
    baseDrone = baseDrone * throbMod;

    // Dark undertones - sub bass
    darkSig = SinOsc.ar(freq * 0.25 * dreadMod);
    darkSig = darkSig + SinOsc.ar(freq * 0.125, 0, 0.5);
    darkSig = darkSig * dark * 0.4;

    // Tension overlay - dissonant high partials
    sig = baseDrone * 0.4;
    sig = sig + (SinOscFB.ar(freq * 2.02 * dreadMod, feedAmt * 0.5) * tens * 0.15);
    sig = sig + (SinOscFB.ar(freq * 3.01, feedAmt * 0.4) * tens * 0.1);

    sig = sig + darkSig;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_coldwar loaded".postln;
