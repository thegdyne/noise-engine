/*
Tape Echo - RE-201 Inspired Delay
Tape delay with degradation, spring reverb, and verb bus cross-feed

Signal flow:
  echoSendBus → PreEQ → Delay+Feedback(sat+LPF+wow) → Spring → Output
                                                          ↓
                                                    verbSendBus (cross-feed)

Features:
  - Tape saturation in feedback path (repeats degrade)
  - Progressive HF loss in feedback
  - Wow/flutter pitch modulation
  - Optional spring reverb
  - Verb send for RE-201 style routing
*/

~setupTapeEcho = {
    "Setting up Tape Echo...".postln;
    
    // State defaults
    ~echoTime = 0.3;        // 50-500ms mapped from 0-1
    ~echoFeedback = 0.3;    // 0-1
    ~echoTone = 0.7;        // 0-1 (maps to LPF freq)
    ~echoWow = 0.1;         // 0-1
    ~echoSpring = 0.0;      // 0-1
    ~echoVerbSend = 0.0;    // 0-1 cross-feed to reverb
    
    SynthDef(\tapeEcho, { |inBus, outBus, verbSendBus,
                           time=0.3, feedback=0.3, tone=0.7, wow=0.1, 
                           spring=0.0, verbSend=0|
        var sig, delayed, fb, wowLfo, toneFreq;
        var springed, output;
        
        // Smooth all params
        time = Lag.kr(time, 0.05);
        feedback = Lag.kr(feedback, 0.02);
        tone = Lag.kr(tone, 0.02);
        wow = Lag.kr(wow, 0.02);
        spring = Lag.kr(spring, 0.02);
        verbSend = Lag.kr(verbSend, 0.02);
        
        // Map tone 0-1 to LPF freq (500Hz - 8000Hz)
        toneFreq = tone.linexp(0, 1, 500, 8000);
        
        // Wow LFO (0.5-2Hz, subtle pitch modulation)
        wowLfo = SinOsc.kr(LFNoise1.kr(0.2).range(0.5, 2)).range(0, 1) * wow * 0.002;
        
        // Read input from send bus
        sig = In.ar(inBus, 2);
        
        // Pre-emphasis EQ (slight HF boost before delay)
        sig = BHiShelf.ar(sig, 2000, 1, 2);
        
        // Feedback path with internal loop
        fb = LocalIn.ar(2);
        
        // Delay with wow modulation
        delayed = DelayC.ar(sig + (fb * feedback.clip(0, 0.95)), 0.6, time + wowLfo);
        
        // Tape saturation on delayed signal (soft clip)
        delayed = (delayed * 1.2).tanh * 0.9;
        
        // Progressive HF loss in feedback
        delayed = LPF.ar(delayed, toneFreq);
        
        // Write back to feedback loop
        LocalOut.ar(delayed);
        
        // Post-emphasis EQ (restore balance)
        delayed = BHiShelf.ar(delayed, 2000, 1, -2);
        
        // Spring reverb simulation (always runs, scaled by spring amount)
        springed = delayed;
        springed = AllpassC.ar(springed, 0.05, 0.03, 0.1);
        springed = AllpassC.ar(springed, 0.05, 0.022, 0.15);
        springed = CombC.ar(springed, 0.1, 0.047, 0.2);
        springed = LPF.ar(springed, 4000);
        springed = springed * spring;
        
        output = delayed + springed;
        
        // Write to echo return bus (100% wet)
        Out.ar(outBus, output);
        
        // Cross-feed to reverb bus
        Out.ar(verbSendBus, output * verbSend);
    }).add;
    
    "  ✓ Tape Echo SynthDef ready".postln;
};

~startTapeEcho = {
    ~echoSynth = Synth(\tapeEcho, [
        \inBus, ~echoSendBus,
        \outBus, ~echoReturnBus,
        \verbSendBus, ~verbSendBus,
        \time, ~echoTime,
        \feedback, ~echoFeedback,
        \tone, ~echoTone,
        \wow, ~echoWow,
        \spring, ~echoSpring,
        \verbSend, ~echoVerbSend
    ], ~fxGroup, \addToTail);
    
    "  ✓ Tape Echo running".postln;
};

~setupTapeEchoOSC = {
    OSCdef(\echoTime, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        // Map 0-1 to 50-500ms
        ~echoTime = val.linlin(0, 1, 0.05, 0.5);
        if(~echoSynth.notNil) {
            ~echoSynth.set(\time, ~echoTime);
        };
    }, '/noise/master/echo/time');
    
    OSCdef(\echoFeedback, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoFeedback = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\feedback, val);
        };
    }, '/noise/master/echo/feedback');
    
    OSCdef(\echoTone, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoTone = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\tone, val);
        };
    }, '/noise/master/echo/tone');
    
    OSCdef(\echoWow, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoWow = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\wow, val);
        };
    }, '/noise/master/echo/wow');
    
    OSCdef(\echoSpring, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoSpring = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\spring, val);
        };
    }, '/noise/master/echo/spring');
    
    OSCdef(\echoVerbSend, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoVerbSend = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\verbSend, val);
        };
    }, '/noise/master/echo/verb_send');
    
    "  ✓ Tape Echo OSC handlers ready".postln;
};
