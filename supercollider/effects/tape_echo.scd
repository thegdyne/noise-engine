/*
Tape Echo - RE-201 Inspired Delay
Tape delay with degradation, spring reverb, and verb bus cross-feed

Signal flow:
  echoSendBus -> PreEQ -> Delay+Feedback(sat+LPF+wow) -> Spring -> Output
                                                          v
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
                           spring=0.0, verbSend=0,
                           timeBus=(-1), feedbackBus=(-1), toneBus=(-1),
                           wowBus=(-1), springBus=(-1), verbSendModBus=(-1)|
        var sig, delayed, fb, wowLfo, toneFreq;
        var springed, output;
        var timeEff, feedbackEff, toneEff, wowEff, springEff, verbSendEff;

        // Bus unification: read from bus if valid index, otherwise use direct arg
        timeEff = Select.kr(timeBus >= 0, [time, In.kr(timeBus)]);
        feedbackEff = Select.kr(feedbackBus >= 0, [feedback, In.kr(feedbackBus)]);
        toneEff = Select.kr(toneBus >= 0, [tone, In.kr(toneBus)]);
        wowEff = Select.kr(wowBus >= 0, [wow, In.kr(wowBus)]);
        springEff = Select.kr(springBus >= 0, [spring, In.kr(springBus)]);
        verbSendEff = Select.kr(verbSendModBus >= 0, [verbSend, In.kr(verbSendModBus)]);

        // Smooth all params
        timeEff = Lag.kr(timeEff, 0.05);
        feedbackEff = Lag.kr(feedbackEff, 0.02);
        toneEff = Lag.kr(toneEff, 0.02);
        wowEff = Lag.kr(wowEff, 0.02);
        springEff = Lag.kr(springEff, 0.02);
        verbSendEff = Lag.kr(verbSendEff, 0.02);
        
        // Map tone 0-1 to LPF freq (500Hz - 8000Hz)
        toneFreq = toneEff.linexp(0, 1, 500, 8000);

        // Wow LFO (0.5-2Hz, subtle pitch modulation)
        wowLfo = SinOsc.kr(LFNoise1.kr(0.2).range(0.5, 2)).range(0, 1) * wowEff * 0.002;
        
        // Read input from send bus
        sig = In.ar(inBus, 2);
        
        // Pre-emphasis EQ (slight HF boost before delay)
        sig = BHiShelf.ar(sig, 2000, 1, 2);
        
        // Feedback path with internal loop
        fb = LocalIn.ar(2);
        
        // Delay with wow modulation
        delayed = DelayC.ar(sig + (fb * feedbackEff.clip(0, 0.95)), 0.6, timeEff + wowLfo);
        
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
        springed = springed * springEff;

        output = delayed + springed;

        // Write to echo return bus (100% wet)
        Out.ar(outBus, output);

        // Cross-feed to reverb bus
        Out.ar(verbSendBus, output * verbSendEff);
    }).add;
    
    "  [x] Tape Echo SynthDef ready".postln;
};

~startTapeEcho = {
    // Get bus indices from bus unification (if available)
    var timeBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_echo_time) ? -1 }, { -1 });
    var feedbackBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_echo_feedback) ? -1 }, { -1 });
    var toneBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_echo_tone) ? -1 }, { -1 });
    var wowBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_echo_wow) ? -1 }, { -1 });
    var springBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_echo_spring) ? -1 }, { -1 });
    var verbSendBusIdx = if(~getBusIndex.notNil, { ~getBusIndex.(\fx_echo_verbSend) ? -1 }, { -1 });

    ~echoSynth = Synth(\tapeEcho, [
        \inBus, ~echoSendBus,
        \outBus, ~echoReturnBus,
        \verbSendBus, ~verbSendBus,
        \time, ~echoTime,
        \feedback, ~echoFeedback,
        \tone, ~echoTone,
        \wow, ~echoWow,
        \spring, ~echoSpring,
        \verbSend, ~echoVerbSend,
        \timeBus, timeBusIdx,
        \feedbackBus, feedbackBusIdx,
        \toneBus, toneBusIdx,
        \wowBus, wowBusIdx,
        \springBus, springBusIdx,
        \verbSendModBus, verbSendBusIdx
    ], ~fxGroup, \addToTail);

    "  [x] Tape Echo running".postln;
};

~setupTapeEchoOSC = {
    OSCdef(\echoTime, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        // Map 0-1 to 50-500ms
        ~echoTime = val.linlin(0, 1, 0.05, 0.5);
        if(~echoSynth.notNil) {
            ~echoSynth.set(\time, ~echoTime);
        };
        // Bus unification: send mapped value (synth reads mapped time)
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_echo_time, ~echoTime);
        };
    }, '/noise/master/echo/time');

    OSCdef(\echoFeedback, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoFeedback = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\feedback, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_echo_feedback, val);
        };
    }, '/noise/master/echo/feedback');

    OSCdef(\echoTone, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoTone = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\tone, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_echo_tone, val);
        };
    }, '/noise/master/echo/tone');

    OSCdef(\echoWow, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoWow = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\wow, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_echo_wow, val);
        };
    }, '/noise/master/echo/wow');

    OSCdef(\echoSpring, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoSpring = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\spring, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_echo_spring, val);
        };
    }, '/noise/master/echo/spring');

    OSCdef(\echoVerbSend, { |msg|
        var val = msg[1].asFloat.clip(0, 1);
        ~echoVerbSend = val;
        if(~echoSynth.notNil) {
            ~echoSynth.set(\verbSend, val);
        };
        if(~queueBaseUpdate.notNil) {
            ~queueBaseUpdate.(\fx_echo_verbSend, val);
        };
    }, '/noise/master/echo/verb_send');

    "  [x] Tape Echo OSC handlers ready".postln;
};
