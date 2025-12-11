// VCA Ring - OTA/Dual-VCA topology
SynthDef(\vcaRing, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    carrier_freq=440, audio_level=0.7, cv_depth=0.8, topology=1, drive=0.3|
    
    var carrier, audio, sig, env;
    
    // Audio source (internal oscillator as stand-in)
    audio = Saw.ar(freq) * audio_level;
    
    // Carrier/CV signal
    carrier = SinOsc.ar(carrier_freq);
    
    // VCA topology variations
    sig = Select.ar(topology.round, [
        // 0: Single VCA (tremolo-like)
        audio * ((carrier + 1) * 0.5),
        // 1: Dual VCA (balanced ring mod)
        audio * carrier,
        // 2: Quad VCA (complex modulation)
        (audio * carrier) + (audio * SinOsc.ar(carrier_freq * 2) * 0.3)
    ]);
    
    sig = sig * cv_depth;
    
    // OTA drive/distortion character
    sig = (sig * (1 + drive * 3)).tanh;
    
    // Filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
