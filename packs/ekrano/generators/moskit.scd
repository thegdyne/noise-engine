// ekrano/moskit — Lightweight end-stage generator
SynthDef(\forge_ekrano_moskit, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var lock, scan, burn, seek, tone;
    var masterFreq, slaveRatio, syncSig, fmMod, scanMod, seekOsc;

    freq = In.kr(freqBus);

    lock = p[0].linlin(0, 1, 1.0, 4.0);
    scan = p[1].linexp(0, 1, 0.2, 12);
    burn = p[2].linlin(0, 1, 0.5, 8);
    seek = p[3].linlin(0, 1, 0.5, 3);
    tone = p[4];

    // Master frequency
    masterFreq = freq;

    // Scanning modulation
    scanMod = LFTri.kr(scan).range(0.95, 1.05);

    // Hard sync using SyncSaw
    syncSig = SyncSaw.ar(masterFreq, masterFreq * lock * scanMod);

    // FM modulation for burn/afterburner character
    fmMod = SinOsc.ar(masterFreq * seek) * burn * masterFreq;
    seekOsc = SinOsc.ar(masterFreq + fmMod);

    // Mix sync and FM
    sig = (syncSig * 0.5) + (seekOsc * 0.5);

    // Tone control via filtering
    sig = SelectX.ar(tone, [LPF.ar(sig, 2000), sig]);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_moskit loaded".postln;
