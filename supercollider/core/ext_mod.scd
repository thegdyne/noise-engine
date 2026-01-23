// ext_mod.scd - Extended Modulation System (v2.4 - minimal value stream)
~extTargets = Dictionary.new;
~extUserParams = Dictionary.new;
~extParamConfig = Dictionary.new;

// Configs - [min, max, isDiscrete, default]
~extParamConfig.put(\mod_p1, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_p2, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_p3, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_p4, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_rate, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_wave, [0, 7, true, 0]);
~extParamConfig.put(\mod_phase, [0, 23, true, 0]);
~extParamConfig.put(\mod_pol, [0, 2, true, 0]);
~extParamConfig.put(\mod_atk, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_rel, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_depth, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_grav, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_reso, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_excur, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_calm, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_tens, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_mass, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_shape, [0, 1, false, 0.5]);
~extParamConfig.put(\mod_pattern, [0, 5, true, 0]);
~extParamConfig.put(\mod_mode, [0, 1, true, 0]);
~extParamConfig.put(\fx_drive, [0, 1, false, 0.0]);
~extParamConfig.put(\fx_mix, [0, 1, false, 1.0]);
~extParamConfig.put(\fx_circuit, [0, 3, true, 0]);
~extParamConfig.put(\fx_time, [0, 1, false, 0.3]);
~extParamConfig.put(\fx_feedback, [0, 1, false, 0.3]);
~extParamConfig.put(\fx_tone, [0, 1, false, 0.7]);
~extParamConfig.put(\fx_wow, [0, 1, false, 0.1]);
~extParamConfig.put(\fx_spring, [0, 1, false, 0.0]);
~extParamConfig.put(\fx_size, [0, 1, false, 0.75]);
~extParamConfig.put(\fx_decay, [0, 1, false, 0.65]);
~extParamConfig.put(\fx_freq1, [0, 1, false, 0.6]);
~extParamConfig.put(\fx_reso1, [0, 1, false, 0.3]);
~extParamConfig.put(\fx_freq2, [0, 1, false, 0.6]);
~extParamConfig.put(\fx_reso2, [0, 1, false, 0.3]);
~extParamConfig.put(\fx_routing, [0, 3, true, 0]);
~extParamConfig.put(\fx_syncAmt, [0, 1, false, 0.0]);
~extParamConfig.put(\send_ec, [0, 1, false, 0.0]);
~extParamConfig.put(\send_vb, [0, 1, false, 0.0]);
~extParamConfig.put(\chan_pan, [-1, 1, false, 0.0]);

~parseExtTarget = { |targetStr|
    var parts = targetStr.asString.split($:);
    var tt = parts[0].asSymbol;
    case
    { tt == \mod } { [\mod, parts[1].asInteger, parts[2].asSymbol] }
    { tt == \fx } { [\fx, parts[1].asSymbol, parts[2].asSymbol] }
    { tt == \send } { [\send, parts[1].asInteger, parts[2].asSymbol] }
    { tt == \chan } { [\chan, parts[1].asInteger, parts[2].asSymbol] }
    { [\unknown, 0, \unknown] }
};

~getParamConfigKey = { |targetStr|
    var parts = targetStr.asString.split($:);
    var tt = parts[0];
    var param = parts[2];
    case
    { tt == "mod" } {
        case
        { param == "p1" } { \mod_p1 }
        { param == "p2" } { \mod_p2 }
        { param == "p3" } { \mod_p3 }
        { param == "p4" } { \mod_p4 }
        { param == "rate" } { \mod_rate }
        { param.beginsWith("wave") } { \mod_wave }
        { param.beginsWith("pol") } { \mod_pol }
        { param.beginsWith("atk") } { \mod_atk }
        { param.beginsWith("rel") } { \mod_rel }
        { param.beginsWith("tens") } { \mod_tens }
        { param.beginsWith("mass") } { \mod_mass }
        { param == "depth" } { \mod_depth }
        { param == "gravity" or: { param == "grav" } } { \mod_grav }
        { param == "resonance" or: { param == "reso" } } { \mod_reso }
        { param == "excursion" or: { param == "excur" } } { \mod_excur }
        { param == "calm" } { \mod_calm }
        { param == "shape" } { \mod_shape }
        { param == "pattern" } { \mod_pattern }
        { param == "rotate" } { \mod_phase }
        { param == "mode" } { \mod_mode }
        { \mod_p1 }
    }
    { tt == "fx" } {
        case
        { param == "drive" } { \fx_drive }
        { param == "mix" } { \fx_mix }
        { param == "circuit" or: { param == "type" } } { \fx_circuit }
        { param == "time" } { \fx_time }
        { param == "feedback" or: { param == "fbk" } } { \fx_feedback }
        { param == "tone" } { \fx_tone }
        { param == "wow" } { \fx_wow }
        { param == "spring" or: { param == "spr" } } { \fx_spring }
        { param == "size" or: { param == "siz" } } { \fx_size }
        { param == "decay" or: { param == "dec" } } { \fx_decay }
        { param == "freq1" } { \fx_freq1 }
        { param == "reso1" } { \fx_reso1 }
        { param == "freq2" } { \fx_freq2 }
        { param == "reso2" } { \fx_reso2 }
        { param == "routing" } { \fx_routing }
        { param == "syncAmt" } { \fx_syncAmt }
        { \fx_mix }
    }
    { tt == "send" } { if(param == "ec") { \send_ec } { \send_vb } }
    { tt == "chan" } { \chan_pan }
    { \mod_p1 }
};

~ensureExtTarget = { |targetStr|
    var key = targetStr.asString;
    var entry = ~extTargets.at(key);
    if(entry.isNil) {
        entry = (
            routes: List.new,
            parsed: ~parseExtTarget.(key),
            cfgKey: ~getParamConfigKey.(key)
        );
        ~extTargets.put(key, entry);
    };
    entry
};

~addExtModRoute = { |sourceBus, targetStr, depth, amount, offset, polarity, invert|
    var t = ~ensureExtTarget.(targetStr);
    var routes = t.at(\routes);
    var existing = routes.detectIndex { |r| r.notNil and: { r.at(\sourceBus) == sourceBus } };
    var route = (
        sourceBus: sourceBus.asInteger,
        depth: depth.asFloat,
        amount: amount.asFloat,
        offset: offset.asFloat,
        polarity: polarity.asInteger,
        invert: invert.asInteger
    );
    if(existing.notNil) { routes.put(existing, route) } { routes.add(route) };
    route
};

~removeExtModRoute = { |sourceBus, targetStr|
    var key = targetStr.asString;
    var t = ~extTargets.at(key);
    if(t.notNil) {
        var routes = t.at(\routes);
        var idx = routes.detectIndex { |r| r.notNil and: { r.at(\sourceBus) == sourceBus } };
        if(idx.notNil) { routes.removeAt(idx) };
        if(routes.size == 0) { ~extTargets.removeAt(key) };
    };
};

~setExtModUserParam = { |targetStr, value|
    ~extUserParams.put(targetStr.asString, value);
};

~setExtTargetValue = { |parsed, value|
    var tt = parsed[0];
    var slotOrType = parsed[1];
    var param = parsed[2];
    case
    { tt == \mod } {
        var slot = slotOrType;
        if([\p1, \p2, \p3, \p4].includes(param)) {
            ~setModParam.(slot, param.asString, value);
        } {
            var paramSym = case
            { param == \grav } { \gravity }
            { param == \reso } { \resonance }
            { param == \excur } { \excursion }
            { param == \pol_1 } { \polarityA }
            { param == \pol_2 } { \polarityB }
            { param == \pol_3 } { \polarityC }
            { param == \pol_4 } { \polarityD }
            { param == \wave_1 } { \waveA }
            { param == \wave_2 } { \waveB }
            { param == \wave_3 } { \waveC }
            { param == \wave_4 } { \waveD }
            { param == \atk_1 } { \atkA }
            { param == \atk_2 } { \atkB }
            { param == \atk_3 } { \atkC }
            { param == \atk_4 } { \atkD }
            { param == \rel_1 } { \relA }
            { param == \rel_2 } { \relB }
            { param == \rel_3 } { \relC }
            { param == \rel_4 } { \relD }
            { param == \tens_1 } { \tension1 }
            { param == \tens_2 } { \tension2 }
            { param == \tens_3 } { \tension3 }
            { param == \tens_4 } { \tension4 }
            { param == \mass_1 } { \mass1 }
            { param == \mass_2 } { \mass2 }
            { param == \mass_3 } { \mass3 }
            { param == \mass_4 } { \mass4 }
            { param };
            if(~modNodes.notNil and: { ~modNodes[slot - 1].notNil }) {
                ~modNodes[slot - 1].set(paramSym, value);
            };
        };
    }
    { tt == \fx } {
        var fxType = slotOrType;
        var paramSym = case
        { param == \type } { \circuit }
        { param == \fbk } { \feedback }
        { param == \spr } { \spring }
        { param == \siz } { \size }
        { param == \dec } { \decay }
        { param };
        case
        { fxType == \heat } { if(~heatSynth.notNil) { ~heatSynth.set(paramSym, value) } }
        { fxType == \echo } { if(~echoSynth.notNil) { ~echoSynth.set(paramSym, value) } }
        { fxType == \reverb } { if(~verbSynth.notNil) { ~verbSynth.set(paramSym, value) } }
        { fxType == \dual_filter } { if(~dualFilterSynth.notNil) { ~dualFilterSynth.set(paramSym, value) } };
    }
    { tt == \send } {
        var stripIdx = slotOrType - 1;
        if(~channelStrips.notNil and: { stripIdx >= 0 } and: { stripIdx < 8 }) {
            var strip = ~channelStrips[stripIdx];
            if(strip.notNil) {
                case
                { param == \ec } { strip.set(\echoSend, value) }
                { param == \vb } { strip.set(\verbSend, value) };
            };
        };
    }
    { tt == \chan } {
        var stripIdx = slotOrType - 1;
        if(~channelStrips.notNil and: { stripIdx >= 0 } and: { stripIdx < 8 }) {
            var strip = ~channelStrips[stripIdx];
            if(strip.notNil) {
                if(param == \pan) { strip.set(\pan, value) };
            };
        };
    };
};

// Compute final value for one target (used by both apply and value stream)
~computeExtTargetValue = { |targetStr, t|
    var routes = t.at(\routes);
    var cfgKey = t.at(\cfgKey);
    var cfg = ~extParamConfig.at(cfgKey) ? [0, 1, false, 0.5];
    var minVal = cfg[0];
    var maxVal = cfg[1];
    var isDiscrete = cfg[2];
    var defVal = cfg[3];
    var base = ~extUserParams.at(targetStr) ? defVal;
    var range = maxVal - minVal;
    var sumDelta = 0;
    var final;

    routes.do { |r|
        if(r.notNil) {
            var sb = r.at(\sourceBus);
            var s = 0;
            var delta;
            if(~modBusSnapshot.notNil and: { sb >= 0 } and: { sb < ~modBusSnapshot.size }) {
                s = ~modBusSnapshot[sb] ? 0;
            };
            if(r.at(\invert) == 1) { s = s.neg };
            case
            { r.at(\polarity) == 1 } { s = (s + 1) * 0.5 }
            { r.at(\polarity) == 2 } { s = ((s + 1) * 0.5).neg };
            delta = (s * r.at(\amount) * r.at(\depth)) + r.at(\offset);
            sumDelta = sumDelta + delta;
        };
    };
    sumDelta = sumDelta.clip(-1, 1);
    if(isDiscrete) {
        final = (base + (sumDelta * range)).round.clip(minVal, maxVal);
    } {
        final = (base + (sumDelta * range)).clip(minVal, maxVal);
    };
    final
};

~applyExtTarget = { |targetStr, t|
    var final = ~computeExtTargetValue.(targetStr, t);
    ~setExtTargetValue.(t.at(\parsed), final);
    final
};

~restoreExtTargetToBase = { |targetStr|
    var t = ~extTargets.at(targetStr);
    if(t.notNil) {
        var cfg = ~extParamConfig.at(t.at(\cfgKey)) ? [0, 1, false, 0.5];
        var base = ~extUserParams.at(targetStr) ? cfg[3];
        ~setExtTargetValue.(t.at(\parsed), base);
    };
};

// ========================================
// APPLY TASK (500Hz - fast modulation)
// ========================================
~extModApplyTask = nil;

~startExtModApplyTask = {
    if(~modSnapshotBus.isNil or: { ~modSnapshotSynth.isNil }) {
        ~setupModBusSnapshot.value;
    };
    if(~extModApplyTask.notNil) { ~extModApplyTask.stop };
    ~extModApplyTask = Task({
        inf.do {
            try {
                ~snapshotModBuses.value;
                ~extTargets.keysValuesDo { |k, v| ~applyExtTarget.(k, v) };
            };
            0.002.wait;
        };
    }).play(SystemClock);
};

~stopExtModApplyTask = {
    if(~extModApplyTask.notNil) {
        ~extModApplyTask.stop;
        ~extModApplyTask = nil;
    };
};

// ========================================
// VALUE STREAM (20Hz - UI feedback)
// Matches mod_apply.scd pattern exactly
// ========================================
~extModValueStreamAddr = NetAddr("127.0.0.1", 57121);
~extModValueStreamRate = 20;
~extModValueStreamRoutine = nil;

~startExtModValueStream = {
    if(~extModValueStreamRoutine.notNil) {
        ~extModValueStreamRoutine.stop;
    };

    ~extModValueStreamRoutine = Routine({
        loop {
            var messages = List.new;
            var keys = ~extTargets.keys.asArray;  // snapshot keys to avoid mutation issues

            keys.do { |targetStr|
                var t = ~extTargets.at(targetStr);
                if(t.notNil) {
                    var cfg = ~extParamConfig.at(t.at(\cfgKey)) ? [0, 1, false, 0.5];
                    var minVal = cfg[0];
                    var maxVal = cfg[1];
                    var range = maxVal - minVal;
                    var final = ~computeExtTargetValue.(targetStr, t);
                    var normVal;

                    // Normalize to 0-1
                    normVal = if(range != 0) { (final - minVal) / range } { 0.5 };
                    normVal = normVal.clip(0, 1);

                    messages.add([targetStr, normVal]);
                };
            };

            // Send if we have any values
            if(messages.size > 0) {
                var flat = messages.collect({ |m| m }).flatten;
                ~extModValueStreamAddr.sendMsg('/noise/extmod/values', *flat);
            };

            (1 / ~extModValueStreamRate).wait;
        };
    }).play;

    "Ext mod value stream started".postln;
};

~stopExtModValueStream = {
    if(~extModValueStreamRoutine.notNil) {
        ~extModValueStreamRoutine.stop;
        ~extModValueStreamRoutine = nil;
    };
    "Ext mod value stream stopped".postln;
};

~clearAllExtModRoutes = {
    ~extTargets.keysDo { |k| ~restoreExtTargetToBase.(k) };
    ~extTargets = Dictionary.new;
    ~stopExtModApplyTask.value;
    ~stopExtModValueStream.value;
};

// ========================================
// OSC HANDLERS
// ========================================
OSCdef(\extModAddRoute).free;
OSCdef(\extModAddRoute, { |msg|
    var sourceBus = msg[1].asInteger;
    var targetStr = msg[2].asString;
    var depth = msg[3].asFloat;
    var amount = msg[4].asFloat;
    var offset = msg[5].asFloat;
    var polarity = msg[6].asInteger;
    var invert = msg[7].asInteger;

    ~addExtModRoute.(sourceBus, targetStr, depth, amount, offset, polarity, invert);

    // Always ensure both tasks running
    if(~extModApplyTask.isNil or: { ~extModApplyTask.isPlaying.not }) {
        ~startExtModApplyTask.();
    };
    if(~extModValueStreamRoutine.isNil or: { ~extModValueStreamRoutine.isPlaying.not }) {
        ~startExtModValueStream.();
    };
}, '/noise/extmod/add_route');

OSCdef(\extModRemoveRoute).free;
OSCdef(\extModRemoveRoute, { |msg|
    var sourceBus = msg[1].asInteger;
    var targetStr = msg[2].asString;
    ~removeExtModRoute.(sourceBus, targetStr);
    if(~extTargets.size == 0) {
        ~stopExtModApplyTask.();
        ~stopExtModValueStream.();
    };
}, '/noise/extmod/remove_route');

OSCdef(\extModSetUserParam).free;
OSCdef(\extModSetUserParam, { |msg|
    var targetStr = msg[1].asString;
    var value = msg[2].asFloat;
    ~setExtModUserParam.(targetStr, value);
}, '/noise/extmod/set_user_param');

OSCdef(\extModClearAll).free;
OSCdef(\extModClearAll, { |msg|
    ~clearAllExtModRoutes.();
}, '/noise/extmod/clear_all');

"ext_mod v2.4 loaded (500Hz apply, 20Hz value stream)".postln;
