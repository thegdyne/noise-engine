/*
OSC Handlers
All OSC message routing
*/

~setupOSC = {
    "Setting up OSC handlers...".postln;

    // === GENERATOR BOID OFFSET SUPPORT ===
    // Store base values and offsets separately, compute effective = base + offset
    ~genBaseValues = Dictionary.new;
    ~genBoidOffsets = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genBaseValues[slot] = Dictionary.new;
        ~genBoidOffsets[slot] = Dictionary.new;
        // Initialize with defaults
        ~genBaseValues[slot][\frequency] = 400;
        ~genBaseValues[slot][\cutoff] = 16000;
        ~genBaseValues[slot][\resonance] = 1.0;
        ~genBaseValues[slot][\attack] = 0.0001;
        ~genBaseValues[slot][\decay] = 1.0;
        ~genBoidOffsets[slot][\frequency] = 0;
        ~genBoidOffsets[slot][\cutoff] = 0;
        ~genBoidOffsets[slot][\resonance] = 0;
        ~genBoidOffsets[slot][\attack] = 0;
        ~genBoidOffsets[slot][\decay] = 0;
        // Custom params
        ~genBaseValues[slot][\custom] = Array.fill(5, { 0.5 });
        ~genBoidOffsets[slot][\custom] = Array.fill(5, { 0.0 });
    };

    // Helper to apply base + offset to bus
    // NOTE (Phase 6): Now also writes to unified buses via ~queueBaseUpdate
    ~applyGenParam = { |slot, param, baseValue|
        var offset = ~genBoidOffsets[slot][param] ? 0;
        var effective = baseValue + offset;
        var unifiedKey;
        ~genBaseValues[slot][param] = baseValue;
        // DEPRECATED: write to legacy bus (kept for compat)
        ~genUserParams[slot][param].set(effective);
        // NEW: Forward to unified bus system
        unifiedKey = switch(param,
            \frequency, { ("gen_%_freq").format(slot).asSymbol },
            \cutoff, { ("gen_%_cutoff").format(slot).asSymbol },
            \resonance, { ("gen_%_res").format(slot).asSymbol },
            \attack, { ("gen_%_attack").format(slot).asSymbol },
            \decay, { ("gen_%_decay").format(slot).asSymbol },
            { nil }
        );
        if(unifiedKey.notNil && ~queueBaseUpdate.notNil, {
            ~queueBaseUpdate.(unifiedKey, effective);
        });
    };

    // Helper for custom params
    // NOTE (Phase 6): Now also writes to unified buses via ~queueBaseUpdate
    ~applyGenCustom = { |slot, paramIdx, baseValue|
        var offset = ~genBoidOffsets[slot][\custom][paramIdx] ? 0;
        var effective = baseValue + offset;
        var unifiedKey;
        ~genBaseValues[slot][\custom][paramIdx] = baseValue;
        // DEPRECATED: write to legacy buses (kept for compat)
        ~genParams[slot][\custom][paramIdx].set(effective);
        ~genUserParams[slot][\custom][paramIdx].set(effective);
        // NEW: Forward to unified bus system
        unifiedKey = ("gen_%_custom%").format(slot, paramIdx).asSymbol;
        if(~queueBaseUpdate.notNil, {
            ~queueBaseUpdate.(unifiedKey, effective);
        });
    };

    // === CONNECTION MANAGEMENT ===
    // Ping/pong for connection verification
    // Python sends /noise/ping, SC responds with /noise/pong
    // ~pythonAddr is set in config.scd
    
    OSCdef(\ping, { |msg, time, addr|
        if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/pong', 1); };
    }, '/noise/ping');

    // Heartbeat - Python sends periodically, SC responds
    // If Python misses responses, it knows connection is dead
    OSCdef(\heartbeat, { |msg, time, addr|
        if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/heartbeat_ack', 1); };
    }, '/noise/heartbeat');

    // Python quit notification - stop sending to avoid crashes
    OSCdef(\pythonQuit, { |msg, time, addr|
        "Python GUI disconnected".postln;
        ~pythonAddr = nil;  // Clear address to stop outbound messages
    }, '/noise/quit');

    // Clock tick broadcast relay (SC fabric -> Python)
    // SendReply format: [cmdName, nodeID, replyID, values...]
    // msg[3] is the fabric index
    OSCdef(\clockTickForward, { |msg|
        if(~pythonAddr.notNil) {
            ~pythonAddr.sendMsg('/noise/clock/tick', msg[3].asInteger);
        };
    }, '/clock/tick');

    // Master clock BPM
    OSCdef(\clockBPM, { |msg|
        ~clockBus.set(msg[1]);
    }, '/noise/clock/bpm');
    
    // Global parameters
    OSCdef(\gravity, { |msg| ~params[\gravity].set(msg[1]); }, '/noise/gravity');
    OSCdef(\density, { |msg| ~params[\density].set(msg[1]); }, '/noise/density');
    OSCdef(\filterCutoff, { |msg| ~params[\filter_cutoff].set(msg[1]); }, '/noise/filter_cutoff');
    OSCdef(\amplitude, { |msg| ~params[\amplitude].set(msg[1]); }, '/noise/amplitude');
    OSCdef(\fidelityAmount, { |msg|
        if(~masterEffects.notNil, { ~masterEffects.set(\fidelityAmount, msg[1]); });
    }, '/noise/fidelity_amount');
    
    // Per-generator parameters
    // Write to ~genUserParams ONLY - modApply passthrough handles ~genParams
    // Now uses boid offset support: stores base, applies offset
    OSCdef(\genFrequency, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat;
        var transpose = ~genTranspose[slot - 1];
        var ratio = 2 ** (transpose / 12);
        var transposed = value * ratio;
        ~applyGenParam.(slot, \frequency, transposed);
    }, '/noise/gen/frequency');

    OSCdef(\genCutoff, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat;
        ~applyGenParam.(slot, \cutoff, value);
    }, '/noise/gen/cutoff');

    OSCdef(\genResonance, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat;
        ~applyGenParam.(slot, \resonance, value);
    }, '/noise/gen/resonance');

    OSCdef(\genAttack, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat;
        ~applyGenParam.(slot, \attack, value);
    }, '/noise/gen/attack');

    OSCdef(\genDecay, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat;
        ~applyGenParam.(slot, \decay, value);
    }, '/noise/gen/decay');
    
    OSCdef(\genFilterType, { |msg|
        ~genParams[msg[1].asInteger][\filterType].set(msg[2].asInteger);
    }, '/noise/gen/filterType');
    
    OSCdef(\genEnvEnabled, { |msg|
        ~genParams[msg[1].asInteger][\envEnabled].set(msg[2].asInteger);
    }, '/noise/gen/envEnabled');
    
    // Envelope source: 0=OFF, 1=CLK, 2=MIDI
    OSCdef(\genEnvSource, { |msg|
        var slot = msg[1].asInteger;
        var source = msg[2].asInteger;
        ~genParams[slot][\envSource].set(source);
        ("Gen " ++ slot ++ " env source: " ++ ["OFF", "CLK", "MIDI"][source]).postln;
    }, '/noise/gen/envSource');
    
    OSCdef(\genClockRate, { |msg|
        // Rate index: 0=/32 ... 6=CLK ... 12=x32
        ~genParams[msg[1].asInteger][\clockRate].set(msg[2].asInteger);
    }, '/noise/gen/clockRate');

   // Per-generator transpose (semitones)
    OSCdef(\genTranspose, { |msg|
        var slot = msg[1].asInteger;
        var semitones = msg[2].asInteger;
        ~genTranspose[slot - 1] = semitones;
        ("Gen " ++ slot ++ " transpose: " ++ semitones ++ " semitones").postln;
    }, '/noise/gen/transpose');

    // Portamento per-slot
    OSCdef(\genPortamento, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat;
        ~genParams[slot][\portamento].set(value);
        ("Gen " ++ slot ++ " portamento: " ++ (value * 1000).round(1) ++ "ms").postln;
    }, '/noise/gen/portamento');

    // Step mode: SC step engine controls triggers (suppresses direct MIDI/keyboard)
    OSCdef(\genStepMode, { |msg|
        var slot = msg[1].asInteger;
        var mode = msg[2].asInteger;  // 0=OFF, 1=ARP, 2=SEQ
        var idx = slot - 1;
        if(idx >= 0 && idx < 8, {
            ~genStepMode[idx] = mode > 0;
            // Clean up any running MIDI retrig when entering step mode
            if(mode > 0, {
                ~stopMidiRetrig.(slot);
            });
            // Update step engine mode
            if(~stepEngine.notNil, {
                ~stepEngine[idx][\mode] = mode;
                ~stepEngine[idx][\position] = 0;
            });
            ("Gen " ++ slot ++ " stepMode: " ++ ["OFF", "ARP", "SEQ"][mode]).postln;
        });
    }, '/noise/gen/stepMode');

    // Per-generator custom parameters
    // Path format: /noise/gen/custom/{slot}/{param_index}
    // Now uses boid offset support
    8.do { |i|
        var slot = i + 1;
        5.do { |p|
            OSCdef(("genCustom" ++ slot ++ "_" ++ p).asSymbol, { |msg|
                var val = msg[1].asFloat;
                ~applyGenCustom.(slot, p, val);
            }, "/noise/gen/custom/" ++ slot ++ "/" ++ p);
        };
    };

    // NOTE: Legacy boid handler removed - boids now use unified bus system
    // via /noise/boid/offsets endpoint in bus_unification_osc.scd
    // ~genBoidOffsets kept but always 0 (harmless, used by ~applyGenParam)

    // === ANALOG OUTPUT STAGE ===
    // Per-slot analog stage controls (enable, type, drive, mix)
    // Enable is a first-class bypass bus, independent of type selection.
    OSCdef(\analogEnable, { |msg|
        var slot = msg[1].asInteger;
        var enable = msg[2].asInteger.clip(0, 1);
        if((slot >= 1) && (slot <= 8), {
            ~genParams[slot][\analogEnable].set(enable);
            ("Gen " ++ slot ++ " analog enable: " ++ enable).postln;
        });
    }, '/noise/gen/analogEnable');

    OSCdef(\analogType, { |msg|
        var slot = msg[1].asInteger;
        var type = msg[2].asInteger.clip(0, 3);
        if((slot >= 1) && (slot <= 8), {
            ~genParams[slot][\analogType].set(type);
            ("Gen " ++ slot ++ " analog type: " ++ ["CLEAN", "TAPE", "TUBE", "FOLD"][type]).postln;
        });
    }, '/noise/gen/analogType');

    OSCdef(\analogDrive, { |msg|
        var slot = msg[1].asInteger;
        var drive = msg[2].asFloat.clip(0, 1);
        if((slot >= 1) && (slot <= 8), {
            ~genParams[slot][\analogDrive].set(drive);
        });
    }, '/noise/gen/analogDrive');

    OSCdef(\analogMix, { |msg|
        var slot = msg[1].asInteger;
        var mix = msg[2].asFloat.clip(0, 1);
        if((slot >= 1) && (slot <= 8), {
            ~genParams[slot][\analogMix].set(mix);
        });
    }, '/noise/gen/analogMix');

    // Generator control (routes through dispatch for end-stage support)
    OSCdef(\startGenerator, { |msg|
        ~startGeneratorDispatch.(msg[1].asInteger, msg[2].asSymbol);
    }, '/noise/start_generator');

    OSCdef(\stopGenerator, { |msg|
        ~stopGeneratorDispatch.(msg[1].asInteger);
    }, '/noise/stop_generator');

    // End-stage mute control (click-free via Lag.kr in SynthDef)
    OSCdef(\endstage_mute, { |msg|
        var slot = msg[1].asInteger;
        var muted = msg[2].asInteger;
        var idx = slot - 1;
        if(idx >= 0 && idx < 8 && ~endstageNodes.notNil, {
            if(~endstageNodes[idx].notNil, {
                ~endstageNodes[idx].set(\mute, muted);
            });
        });
    }, '/noise/endstage/mute');
    
    // === CHANNEL STRIP CONTROLS ===
    // All handlers use ~withValidSlot for bounds checking
    // All handlers track state (persists even if strip doesn't exist yet)
    
    // Per-generator volume
    OSCdef(\genVolume, { |msg|
        var slot = msg[1].asInteger;
        var vol = msg[2].asFloat.clip(0, 1);
        
        ~withValidSlot.(slot, { |idx|
            // Track state (persists across generator changes)
            ~stripVolState[idx] = vol;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\vol, vol);
            });
        });
    }, '/noise/gen/volume');
    
    // Per-generator mute
    OSCdef(\genMute, { |msg|
        var slot = msg[1].asInteger;
        var muted = msg[2].asInteger;
        
        ~withValidSlot.(slot, { |idx|
            ~stripMuteState[idx] = muted;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\mute, muted);
            });
        });
    }, '/noise/gen/mute');
    
    // Per-generator solo (with global solo tracking)
    OSCdef(\genSolo, { |msg|
        var slot = msg[1].asInteger;
        var soloed = msg[2].asInteger;
        
        ~withValidSlot.(slot, { |idx|
            var oldSolo = ~stripSoloState[idx] ? 0;
            
            // Always update state (even if strip doesn't exist yet)
            ~stripSoloState[idx] = soloed;
            
            // Update global solo count
            if(soloed == 1 && oldSolo == 0, { ~soloCount = ~soloCount + 1 });
            if(soloed == 0 && oldSolo == 1, { ~soloCount = ~soloCount - 1 });
            
            // Update global soloActive bus
            ~soloActive.set(if(~soloCount > 0, 1, 0));
            
            // Only set on synth if it exists
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\solo, soloed);
            });
        });
    }, '/noise/gen/solo');
    
    // Gain stage control
    OSCdef(\genGain, { |msg|
        var slot = msg[1].asInteger;
        var gainDb = msg[2].asInteger;  // 0, 6, or 12
        var gainLinear = (10 ** (gainDb / 20));
        
        ~withValidSlot.(slot, { |idx|
            ~stripGainState[idx] = gainLinear;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\gain, gainLinear);
            });
        });
    }, '/noise/gen/gain');
    
    // Per-generator pan
    OSCdef(\genPan, { |msg|
        var slot = msg[1].asInteger;
        var pan = msg[2].asFloat.clip(-1, 1);

        ~withValidSlot.(slot, { |idx|
            ~stripPanState[idx] = pan;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\pan, pan);
            });
            // Bus unification
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(("chan_%_pan").format(slot).asSymbol, pan);
            });
        });
    }, '/noise/gen/pan');
    
    // Per-generator trim (loudness normalization from JSON config)
    OSCdef(\genTrim, { |msg|
        var slot = msg[1].asInteger;
        var trimDb = msg[2].asFloat;
        
        ~withValidSlot.(slot, { |idx|
            ~stripTrimState[idx] = trimDb;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\genTrim, trimDb);
            });
        });
    }, '/noise/gen/trim');
    
    // === CHANNEL EQ CONTROLS ===
    // Per-channel EQ - LO band
    OSCdef(\stripEqLo, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 2);  // 0=kill, 1=unity, 2=+6dB
        
        ~withValidSlot.(slot, { |idx|
            ~stripEqLoState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\eqLo, value);
            });
        });
    }, '/noise/strip/eq/lo');
    
    // Per-channel EQ - MID band
    OSCdef(\stripEqMid, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 2);
        
        ~withValidSlot.(slot, { |idx|
            ~stripEqMidState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\eqMid, value);
            });
        });
    }, '/noise/strip/eq/mid');
    
    // Per-channel EQ - HI band
    OSCdef(\stripEqHi, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 2);
        
        ~withValidSlot.(slot, { |idx|
            ~stripEqHiState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\eqHi, value);
            });
        });
    }, '/noise/strip/eq/hi');
    
    // Reset all EQ bands to unity for a slot
    OSCdef(\stripEqReset, { |msg|
        var slot = msg[1].asInteger;
        
        ~withValidSlot.(slot, { |idx|
            ~stripEqLoState[idx] = 1.0;
            ~stripEqMidState[idx] = 1.0;
            ~stripEqHiState[idx] = 1.0;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\eqLo, 1.0, \eqMid, 1.0, \eqHi, 1.0);
            });
        });
    }, '/noise/strip/eq/reset');
    

    // === FX Send OSC Handlers ===
    
    // Per-channel Echo Send
    // Per-channel FX1 Send (was Echo)
    OSCdef(\stripFx1Send, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 1);

        ~withValidSlot.(slot, { |idx|
            ~stripFx1SendState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\fx1Send, value);
            });
            // Bus unification
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(("chan_%_fx1").format(slot).asSymbol, value);
            });
        });
    }, '/noise/strip/fx1/send');

    // Per-channel FX2 Send (was Verb)
    OSCdef(\stripFx2Send, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 1);

        ~withValidSlot.(slot, { |idx|
            ~stripFx2SendState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\fx2Send, value);
            });
            // Bus unification
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(("chan_%_fx2").format(slot).asSymbol, value);
            });
        });
    }, '/noise/strip/fx2/send');

    // Per-channel FX3 Send
    OSCdef(\stripFx3Send, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 1);

        ~withValidSlot.(slot, { |idx|
            ~stripFx3SendState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\fx3Send, value);
            });
            // Bus unification
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(("chan_%_fx3").format(slot).asSymbol, value);
            });
        });
    }, '/noise/strip/fx3/send');

    // Per-channel FX4 Send
    OSCdef(\stripFx4Send, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 1);

        ~withValidSlot.(slot, { |idx|
            ~stripFx4SendState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\fx4Send, value);
            });
            // Bus unification
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(("chan_%_fx4").format(slot).asSymbol, value);
            });
        });
    }, '/noise/strip/fx4/send');

    // Legacy aliases for backward compatibility
    OSCdef(\stripEchoSend, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 1);
        ~withValidSlot.(slot, { |idx|
            ~stripFx1SendState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\fx1Send, value);
            });
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(("chan_%_fx1").format(slot).asSymbol, value);
            });
        });
    }, '/noise/strip/echo/send');

    OSCdef(\stripVerbSend, { |msg|
        var slot = msg[1].asInteger;
        var value = msg[2].asFloat.clip(0, 1);
        ~withValidSlot.(slot, { |idx|
            ~stripFx2SendState[idx] = value;
            if(~channelStrips[idx].notNil, {
                ~channelStrips[idx].set(\fx2Send, value);
            });
            if(~queueBaseUpdate.notNil, {
                ~queueBaseUpdate.(("chan_%_fx2").format(slot).asSymbol, value);
            });
        });
    }, '/noise/strip/verb/send');
    "  [x] OSC handlers ready".postln;
};
