// Geiger - Radioactive click generator
SynthDef(\geiger, {
    |out=0, amp=0.5, gate=1,
    freq=440, filterType=0, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    count_rate=5, dead_time=0.3, click_brightness=0.6, click_decay=0.4, background_noise=0.1|
    
    var trig, click, noise, sig, env, effectiveRate;
    
    // Poisson-distributed triggers (Dust is already Poisson)
    // Dead time reduces effective rate at high counts
    effectiveRate = count_rate / (1 + (dead_time * count_rate * 0.1));
    trig = Dust.ar(effectiveRate);
    
    // Click transient (GM tube discharge)
    click = trig * WhiteNoise.ar;
    click = EnvGen.ar(
        Env.perc(0.0001, click_decay.linexp(0, 1, 0.005, 0.05)),
        trig
    ) * WhiteNoise.ar;
    
    // Brightness = highpass filter on click
    click = HPF.ar(click, click_brightness.linexp(0, 1, 200, 8000));
    click = click * 4;
    
    // Background tube hiss/crackle
    noise = PinkNoise.ar * background_noise * 0.1;
    noise = noise + (Dust.ar(count_rate * 10) * 0.02 * background_noise);
    
    sig = click + noise;
    
    // Output filter
    sig = ~multiFilter.(sig, filterType, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
