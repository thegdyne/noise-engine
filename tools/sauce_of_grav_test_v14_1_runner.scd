/*
=============================================================================
SauceOfGrav Parameter Test Suite v14.1  (PARALLEL RUNNER - single file)
=============================================================================
Headless-friendly runner:
- Boots Server.local with big memSize / limits (must be set BEFORE boot)
- Loads init.scd (auto-detect relative to repo, or pass as argv[1])
- Loads build file passed as argv[0] (your assembled 00_all.scd)
- ALWAYS opens /tmp log first (so you get evidence even on FATAL guards)
- Auto-exits when all slots complete (no hanging at sc3> prompt)
=============================================================================

USAGE (your current pattern):
  sclang sauce_of_grav_test_v14_1_runner.scd /abs/path/to/build/00_all.scd

Optional:
  sclang sauce_of_grav_test_v14_1_runner.scd /abs/path/to/build/00_all.scd /abs/path/to/init.scd
*/

(
// ----------------------------------------------------------------------
// ALL var declarations MUST come first (before any executable statements)
// ----------------------------------------------------------------------
var buildPath = thisProcess.argv.at(0);
var initPath  = thisProcess.argv.at(1);
var s = Server.local;
var slots       = 4;
var perSlot     = 4;
var runsPerSlot = 1;
var delayPerRun = 1.0;
var slotOffset  = 0.2;
var totalRuns;
// Hoist these from the if(initPath.isNil) block:
var runnerPath, runnerDir, repoRoot, cands;


// ----------------------------------------------------------------------
// Now executable code can begin
// ----------------------------------------------------------------------

if(buildPath.isNil) {
    "ERROR: missing build_file.\nUSAGE: sclang runner.scd /abs/path/to/build/00_all.scd [ /abs/path/to/init.scd ]".postln;
    ("argv = " ++ thisProcess.argv.asString).postln;
    1.exit;
};

// ----------------------------------------------------------------------
// Server opts (MUST be set before boot)
// ----------------------------------------------------------------------

Server.default = s;

s.options.memSize              = 262144;  // KB (256 MB RT mem)
s.options.maxNodes             = 65536;
s.options.numWireBufs          = 256;
s.options.maxSynthDefs         = 8192;
s.options.numBuffers           = 4096;
s.options.numAudioBusChannels  = 1024;
s.options.numControlBusChannels= 8192;

// ----------------------------------------------------------------------
// Resolve init.scd if not provided
// (assumes runner is in .../noise-engine/tools/ and repo root is parent)
// ----------------------------------------------------------------------
if(initPath.isNil) {
    runnerPath = thisProcess.nowExecutingPath;
    runnerDir  = PathName(runnerPath).pathOnly;      // .../noise-engine/tools/
    repoRoot   = PathName(runnerDir).parentPath;     // .../noise-engine/
    cands = [
        repoRoot ++ "supercollider/init.scd",
        repoRoot ++ "supercollider/core/init.scd",
        repoRoot ++ "supercollider/startup/init.scd"
    ];
    initPath = cands.detect { |p| File.exists(p) };
};

// ----------------------------------------------------------------------
// Test config (FAST "one run" baseline)
// ----------------------------------------------------------------------
totalRuns = slots * runsPerSlot;

~sauceBusOffset ?? { ~sauceBusOffset = 0 };

// shared state
~sauceDone   ?? { ~sauceDone   = IdentityDictionary.new };
~sauceBusy   ?? { ~sauceBusy   = IdentityDictionary.new };
~sauceGroups ?? { ~sauceGroups = Array.newClear(slots) };
~modNodes    ?? { ~modNodes    = Array.newClear(slots) };

// ----------------------------------------------------------------------
// Boot + load + run
// ----------------------------------------------------------------------
("BUILD: " ++ buildPath).postln;
("INIT : " ++ (initPath ? "(none found)")).postln;

s.boot;

s.waitForBoot({

    // make NodeWatcher actually work
    s.notify = true;

    // init dictionaries
    slots.do { |i|
        ~sauceDone[i] = false;
        ~sauceBusy[i] = false;
    };

    // load init (if we found one)
    if(initPath.notNil) {
        ("LOADING INIT: " ++ initPath).postln;
        initPath.load;
        s.sync;
    } {
        "WARN: init.scd not found. If ~modBuses/~clockBus aren't created, tests will FATAL (but will still write logs).".postln;
    };

    // load assembled build (SynthDef etc)
    ("LOADING BUILD: " ++ buildPath).postln;
    buildPath.load;
    s.sync;

    // ----------------------------------------------------------------------
    // ONE RUN (for a given slot + run number)
    // ----------------------------------------------------------------------
    ~runSauceV14 = { |slot=0, runNo=1, total=5|   // NOTE: defaults must be literals
        fork {
            var baseBus, outFile, testResults, testsPassed, testsFailed;
            var createSynthArgs, resetSynth, captureStats, setParams, runComparison, runFloor;

            baseBus = (~sauceBusOffset.asInteger) + (slot * perSlot);

            testsPassed = 0;
            testsFailed = 0;
            testResults = List.new;

            // ALWAYS open log first (so fatal guards still leave evidence)
            outFile = File("/tmp/sauce_test_v14_1_slot%.txt".format(slot + 1), "a");
            outFile.write("\n\n[BOOT] slot=% run=%/% time=%\n"
                .format(slot+1, runNo, total, Date.localtime.asString));
            outFile.write("buildPath=%\n".format(buildPath));
            outFile.write("initPath=%\n".format(initPath ? "(none)"));
            outFile.write("baseBusOffset=% baseBus=%\n".format(~sauceBusOffset, baseBus));
            outFile.flush;

            // --- hard guards (write to file too) ---
            if(~modBuses.isNil) {
                ("[FATAL] ~modBuses is nil. Did init.scd (+ mod_buses.scd + ~setupModBuses.()) run?").postln;
                outFile.write("[FATAL] ~modBuses is nil. Did init.scd (+ mod_buses.scd + ~setupModBuses.()) run?\n"); outFile.flush;
                ^nil;
            };
            if(~modBuses.size < (baseBus + perSlot)) {
                outFile.write("[FATAL] ~modBuses too small: size=% need>=% (slot=% baseBus=% offset=%)\n"
                    .format(~modBuses.size, baseBus + perSlot, slot+1, baseBus, ~sauceBusOffset));
                outFile.flush;
                ^nil;
            };
            perSlot.do { |j|
                if(~modBuses[baseBus + j].isNil) {
                    outFile.write("[FATAL] ~modBuses[%] is nil (slot=% lane=%). Fix mod_buses allocation or set ~sauceBusOffset.\n"
                        .format(baseBus + j, slot+1, j));
                    outFile.flush;
                    ^nil;
                };
            };
            if(~clockTrigBus.isNil or: { ~clockBus.isNil }) {
                outFile.write("[FATAL] clock buses nil: ~clockTrigBus=% ~clockBus=% (init not finished?)\n"
                    .format(~clockTrigBus, ~clockBus));
                outFile.flush;
                ^nil;
            };

            createSynthArgs = {
                [
                    \out1, ~modBuses[baseBus + 0].index,
                    \out2, ~modBuses[baseBus + 1].index,
                    \out3, ~modBuses[baseBus + 2].index,
                    \out4, ~modBuses[baseBus + 3].index,
                    \clockTrigBus, ~clockTrigBus.index,
                    \clockIndex, 12,
                    \bpmBus, ~clockBus.index
                ]
            };

            resetSynth = {
                var g;

                g = ~sauceGroups[slot];

                if(g.isNil or: { g.isPlaying.not }) {
                    g = Group.head(Server.default);
                    ~sauceGroups[slot] = g;
                    Server.default.sync;
                    ("  [Group recreated slot % -> id %]".format(slot+1, g.nodeID)).postln;
                };

                g.freeAll;
                Server.default.sync;

                ~modNodes[slot] = nil;
                0.05.wait;

                ~modNodes[slot] = Synth.tail(g, \ne_mod_sauce_of_grav, createSynthArgs.());
                NodeWatcher.register(~modNodes[slot]);
                Server.default.sync;

                "  [Synth recreated - fresh state]".postln;
                0.2.wait;
            };

            captureStats = { |duration=24, warmup=4|
                var samples, mins, maxs, sums, sumsSq, crossings, prevSide, prevVals, totalMovement, allVals, spreadSum;
                var hubMin, hubMax, hubSum, hubPrev, hubMove, hubCross, hubPrevSide;
                var means, stds, corrs, ranges, hubMean;

                warmup.wait;

                samples = (duration * 20).asInteger;
                mins = [inf, inf, inf, inf];
                maxs = [inf.neg, inf.neg, inf.neg, inf.neg];
                sums = [0.0, 0.0, 0.0, 0.0];
                sumsSq = [0.0, 0.0, 0.0, 0.0];
                crossings = [0, 0, 0, 0];
                prevSide = [0, 0, 0, 0];
                prevVals = [0.5, 0.5, 0.5, 0.5];
                totalMovement = [0.0, 0.0, 0.0, 0.0];
                allVals = [List.new, List.new, List.new, List.new];

                hubMin = inf;
                hubMax = inf.neg;
                hubSum = 0.0;
                hubPrev = 0.5;
                hubMove = 0.0;
                hubCross = 0;
				hubPrevSide = 0;
				spreadSum = 0.0;

                samples.do {
                    var vals, hub, hubSide;

                    vals = 4.collect { |j| ~modBuses[baseBus + j].getSynchronous.clip(0.0, 1.0) };
                    hub = (vals[0] + vals[1] + vals[2] + vals[3]) * 0.25;
					spreadSum = spreadSum + (
						((vals[0] - hub).abs + (vals[1] - hub).abs + (vals[2] - hub).abs + (vals[3] - hub).abs) * 0.25
					);
                    hubSide = if(hub > 0.5, 1, -1);

                    hubMin = min(hubMin, hub);
                    hubMax = max(hubMax, hub);
                    hubSum = hubSum + hub;
                    hubMove = hubMove + (hub - hubPrev).abs;
                    if(hubPrevSide != 0 and: { hubSide != hubPrevSide }) { hubCross = hubCross + 1 };
                    hubPrevSide = hubSide;
                    hubPrev = hub;

                    4.do { |j|
                        var v, side;
                        v = vals[j];
                        side = if(v > 0.5, 1, -1);

                        mins[j] = min(mins[j], v);
                        maxs[j] = max(maxs[j], v);
                        sums[j] = sums[j] + v;
                        sumsSq[j] = sumsSq[j] + (v * v);
                        totalMovement[j] = totalMovement[j] + (v - prevVals[j]).abs;
                        allVals[j].add(v);

                        if(prevSide[j] != 0 and: { side != prevSide[j] }) { crossings[j] = crossings[j] + 1 };
                        prevSide[j] = side;
                        prevVals[j] = v;
                    };

                    0.05.wait;
                };

                means = 4.collect { |i| sums[i] / samples };
                stds = 4.collect { |i|
                    var variance;
                    variance = (sumsSq[i] / samples) - (means[i] * means[i]);
                    variance.max(0.0001).sqrt;
                };

                corrs = List.new;
                [[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]].do { |pair|
                    var i, j, cov;
                    i = pair[0]; j = pair[1];
                    cov = 0.0;
                    samples.do { |k|
                        cov = cov + ((allVals[i][k] - means[i]) * (allVals[j][k] - means[j]));
                    };
                    cov = cov / samples;
                    corrs.add((cov / (stds[i] * stds[j])).abs);
                };

                ranges = 4.collect { |i| maxs[i] - mins[i] };
                hubMean = hubSum / samples;

				(
                    mins: mins, maxs: maxs, ranges: ranges,
                    means: means,
                    meanDev: (means - 0.5).abs.sum / 4,
                    avgRange: ranges.sum / 4,
                    avgCrossings: crossings.sum / 4,
                    rangeSpread: ranges.maxItem - ranges.minItem,
                    avgMovement: totalMovement.sum / (4 * samples),
                    avgCorrelation: corrs.sum / 6,
                    hubMin: hubMin,
                    hubMax: hubMax,
                    hubRange: (hubMax - hubMin),
                    hubMean: hubMean,
                    hubMeanDev: (hubMean - 0.5).abs,
                    hubMovement: (hubMove / samples),
                    hubCrossings: hubCross.asFloat,
                    hubTightness: (spreadSum / samples),
                    normMove: ((totalMovement.sum / (4 * samples)) / ((ranges.sum / 4) + 1e-6)),
                    duration: duration
                )
            };

            setParams = { |params|
                var synth = ~modNodes[slot];
                if(synth.isNil) { ("  [WARN] setParams: synth nil (slot %)".format(slot+1)).postln; ^nil };
                if(synth.isPlaying.not) { ("  [WARN] setParams: synth not playing (slot %)".format(slot+1)).postln; ^nil };

                params.keysValuesDo { |key, val| synth.set(key, val) };
                Server.default.sync;
                1.0.wait;
            };

            runComparison = { |testId, name, baseParams, lowParams, highParams, metric, expectedDir, minDelta, description, duration=24, warmup=4|
                var lowStats, highStats, delta, passed, resultStr, isHubMetric;
                isHubMetric = [\hubRange, \hubMeanDev, \hubMovement].includes(metric);

                "\n=== %: % ===".format(testId, name).postln;
                outFile.write("\n=== %: % ===\n".format(testId, name));
                outFile.write("  %\n".format(description));

                "  Testing LOW...".postln;
                resetSynth.value;
                setParams.value(baseParams);
                setParams.value(lowParams);
                lowStats = captureStats.value(duration, warmup);

                "  Testing HIGH...".postln;
                resetSynth.value;
                setParams.value(baseParams);
                setParams.value(highParams);
                highStats = captureStats.value(duration, warmup);

				delta = switch(metric,
                    \avgRange,       { highStats[\avgRange]       - lowStats[\avgRange] },
                    \meanDev,        { highStats[\meanDev]        - lowStats[\meanDev] },
                    \avgCrossings,   { highStats[\avgCrossings]   - lowStats[\avgCrossings] },
                    \rangeSpread,    { highStats[\rangeSpread]    - lowStats[\rangeSpread] },
                    \avgMovement,    { highStats[\avgMovement]    - lowStats[\avgMovement] },
                    \avgCorrelation, { highStats[\avgCorrelation] - lowStats[\avgCorrelation] },
                    \hubRange,       { highStats[\hubRange]       - lowStats[\hubRange] },
                    \hubMeanDev,     { highStats[\hubMeanDev]     - lowStats[\hubMeanDev] },
                    \hubMovement,    { highStats[\hubMovement]    - lowStats[\hubMovement] },
                    \hubTightness,   { highStats[\hubTightness]   - lowStats[\hubTightness] },
                    \normMove,       { highStats[\normMove]       - lowStats[\normMove] }
                );

                passed = switch(expectedDir,
                    \increase, { delta > minDelta },
                    \decrease, { delta < (minDelta.neg) },
                    \any,      { delta.abs > minDelta }
                );

                if(passed) { testsPassed = testsPassed + 1 } { testsFailed = testsFailed + 1 };

                resultStr = "  LOW:  %=% range=% crossings=% corr=%\n".format(
                    metric, lowStats[metric].round(0.001),
                    lowStats[\avgRange].round(0.01),
                    lowStats[\avgCrossings].round(0.1),
                    lowStats[\avgCorrelation].round(0.01)
                );
                outFile.write(resultStr); resultStr.postln;

                if(isHubMetric) {
                    resultStr = "  HUB (LOW):  hubRange=% hubMeanDev=% hubMove=% hubCross=%\n".format(
                        lowStats[\hubRange].round(0.001),
                        lowStats[\hubMeanDev].round(0.001),
                        lowStats[\hubMovement].round(0.0001),
                        lowStats[\hubCrossings].round(0.1)
                    );
                    outFile.write(resultStr); resultStr.postln;
                };

                resultStr = "  HIGH: %=% range=% crossings=% corr=%\n".format(
                    metric, highStats[metric].round(0.001),
                    highStats[\avgRange].round(0.01),
                    highStats[\avgCrossings].round(0.1),
                    highStats[\avgCorrelation].round(0.01)
                );
                outFile.write(resultStr); resultStr.postln;

                if(isHubMetric) {
                    resultStr = "  HUB (HIGH): hubRange=% hubMeanDev=% hubMove=% hubCross=%\n".format(
                        highStats[\hubRange].round(0.001),
                        highStats[\hubMeanDev].round(0.001),
                        highStats[\hubMovement].round(0.0001),
                        highStats[\hubCrossings].round(0.1)
                    );
                    outFile.write(resultStr); resultStr.postln;
                };

                resultStr = "  DELTA: % (need % %) -> [%]\n".format(
                    delta.round(0.001), expectedDir, minDelta, if(passed, "PASS", "FAIL")
                );
                outFile.write(resultStr); resultStr.postln;

                testResults.add((id: testId, name: name, passed: passed, delta: delta));
            };

            runFloor = { |testId, name, baseParams, testParams, metric, minValue, description, duration=24, warmup=4|
                var stats, passed, resultStr;

                "\n=== %: % ===".format(testId, name).postln;
                outFile.write("\n=== %: % ===\n".format(testId, name));
                outFile.write("  %\n".format(description));

                "  Testing...".postln;
                resetSynth.value;
                setParams.value(baseParams);
                setParams.value(testParams);
                stats = captureStats.value(duration, warmup);

                passed = switch(metric,
                    \avgRange,     { stats[\avgRange] > minValue },
                    \avgCrossings, { stats[\avgCrossings] > minValue },
                    \avgMovement,  { stats[\avgMovement] > minValue }
                );

                if(passed) { testsPassed = testsPassed + 1 } { testsFailed = testsFailed + 1 };

                resultStr = "  %=% range=% crossings=% corr=%\n".format(
                    metric, stats[metric].round(0.001),
                    stats[\avgRange].round(0.01),
                    stats[\avgCrossings].round(0.1),
                    stats[\avgCorrelation].round(0.01)
                );
                outFile.write(resultStr); resultStr.postln;

                resultStr = "  FLOOR: %=% (need > %) -> [%]\n".format(
                    metric, stats[metric].round(0.001), minValue, if(passed, "PASS", "FAIL")
                );
                outFile.write(resultStr); resultStr.postln;

                testResults.add((id: testId, name: name, passed: passed, metric: metric, minValue: minValue, value: stats[metric]));
            };

            // ---- run body protected ----
            {
                ("=== RUN % / % (slot % , baseBus %) ===".format(runNo, total, slot + 1, baseBus)).postln;

                outFile.write("\n=== RUN % / % (slot % , baseBus %) ===\n".format(runNo, total, slot + 1, baseBus));
                outFile.write("SauceOfGrav Parameter Test Suite v14.1\n");
                outFile.write("Date: %\n".format(Date.localtime.asString));
                outFile.write("baseBusOffset=%\n".format(~sauceBusOffset));
                outFile.write("=".dup(70).join ++ "\n");

                "Starting tests...".postln;

                // -------------------------
                // v14.1 comparisons (as you already had)
                // -------------------------
				runComparison.value("G01", "GRAVITY pulls lanes toward 0.5 (meanDev)",
                    (
                        clockMode: 1, rate: 0.5, depth: 0.8, resonance: 0.0, excursion: 0.5, calm: 0.2,
                        tension1: 0.0, tension2: 0.0, tension3: 0.0, tension4: 0.0,
                        mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5
                    ),
                    (gravity: 0.0),
                    (gravity: 1.0),
                    \meanDev, \decrease, 0.005,
                    "Higher gravity should reduce lane mean deviation from 0.5 (fixed-center pull).",
                    40, 4
                );

                runComparison.value("R01", "RESONANCE sustains motion in high damping regime",
                    (
                        clockMode: 1, rate: 0.3, depth: 1.0, gravity: 0.6, excursion: 0.1, calm: 0.0,
                        tension1: 0.0, tension2: 0.0, tension3: 0.0, tension4: 0.0,
                        mass1: 0.6, mass2: 0.6, mass3: 0.6, mass4: 0.6
                    ),
                    (resonance: 0.0),
                    (resonance: 1.0),
                    \avgRange, \increase, 0.01,
                    "With strong damping, resonance should keep avgRange up (low resonance collapses).",
                    60, 4
                );

                runComparison.value("E01", "EXCURSION increases motion (hub-active regime)",
                    (
                        clockMode: 1, rate: 0.5, depth: 0.6, gravity: 0.4, resonance: 0.2, calm: 0.5,
                        tension1: 0.4, tension2: 0.4, tension3: 0.4, tension4: 0.4,
                        mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5
                    ),
                    (excursion: 0.0),
                    (excursion: 1.0),
                    \avgRange, \increase, 0.01,
                    "Higher excursion should produce larger avgRange in active regime.",
                    30, 4
                );

                runComparison.value("C01", "CALM increases amplitude (0=calm, 1=wild)",
                    (
                        clockMode: 1, rate: 0.6, depth: 0.6, gravity: 0.5, resonance: 0.2, excursion: 0.6,
                        tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5,
                        mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5
                    ),
                    (calm: 0.0),
                    (calm: 1.0),
                    \avgRange, \increase, 0.10,
                    "Wild should be *significantly* larger avgRange than calm.",
                    30, 4
                );

				runComparison.value("F01", "RATE increases movement (timescale)",
                    (
                        clockMode: 1, depth: 0.5, gravity: 0.5, resonance: 0.5, excursion: 0.5, calm: 0.5,
                        tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5,
                        mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5
                    ),
                    (rate: 0.05),
                    (rate: 0.80),
                    \normMove, \increase, 0.001,
                    "Higher rate should increase normMove (movement relative to range).",
                    18, 4
                );

                runFloor.value("F02", "RATE low still has motion (avgMovement floor)",
                    (
                        clockMode: 1, rate: 0.1, depth: 0.6, gravity: 0.5, resonance: 0.2, excursion: 0.6, calm: 0.5,
                        tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5,
                        mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5
                    ),
                    (),
                    \avgMovement, 0.0002,
                    "Even at low rate, movement per sample should be > tiny floor.",
                    60, 4
                );

                runComparison.value("T01", "TENSION increases coupling -> bigger range",
                    (
                        clockMode: 1, rate: 0.6, depth: 0.5, gravity: 0.5, resonance: 0.2, excursion: 0.5, calm: 0.7,
                        mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5
                    ),
                    (tension1: 0.0, tension2: 0.0, tension3: 0.0, tension4: 0.0),
                    (tension1: 1.0, tension2: 1.0, tension3: 1.0, tension4: 1.0),
                    \avgRange, \increase, 0.03,
                    "Higher tension -> stronger coupling -> larger avgRange.",
                    30, 5
                );

				runComparison.value("M01", "MASS slows motion -> less avgMovement",
                    (
                        clockMode: 1, rate: 0.6, depth: 0.7, gravity: 0.5, resonance: 0.3, excursion: 0.4, calm: 0.5,
                        tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5
                    ),
                    (mass1: 0.0, mass2: 0.0, mass3: 0.0, mass4: 0.0),
                    (mass1: 1.0, mass2: 1.0, mass3: 1.0, mass4: 1.0),
                    \avgMovement, \decrease, 0.002,
                    "Higher mass -> slower acceleration -> less movement per second.",
                    45, 6
                );

                // summary
                outFile.write("\n" ++ "=".dup(70).join ++ "\n");
                outFile.write("SUMMARY: % PASSED, % FAILED out of % tests\n"
                    .format(testsPassed, testsFailed, testsPassed + testsFailed));

                outFile.write("\nFailed tests:\n");
                testResults.do { |t|
                    if(t[\passed].not) {
                        outFile.write("  - %: % (delta=%)\n"
                            .format(t[\id], t[\name], t[\delta].round(0.001)));
                    };
                };
                outFile.write("=".dup(70).join ++ "\n");

            }.protect({

                if(outFile.notNil) {
                    outFile.tryPerform(\flush);
                    outFile.tryPerform(\close);
                    outFile = nil;
                };

                if(~modNodes.notNil and: { ~modNodes[slot].notNil }) {
                    ~modNodes[slot].tryPerform(\free);
                    Server.default.sync;
                    ~modNodes[slot] = nil;
                };

                ~sauceDone[slot] = true;
                ~sauceBusy[slot] = false;

                ("<<< DONE RUN % / % (slot %) >>>".format(runNo, total, slot + 1)).postln;
            });
        };
    };

    // ----------------------------------------------------------------------
    // Scheduler
    // ----------------------------------------------------------------------
    ("=== % RUNS QUEUED across % slots ===".format(totalRuns, slots)).postln;

    slots.do { |slotIdx|
        Routine.run({
            runsPerSlot.do { |runIdx|
                var runNum = runIdx + 1;

                while({ ~sauceBusy[slotIdx] == true }, { 0.1.wait; });

                ~sauceBusy[slotIdx] = true;
                (">>> SLOT % RUN % / %".format(slotIdx + 1, runNum, runsPerSlot)).postln;

                ~runSauceV14.(slotIdx, runNum, runsPerSlot);

                delayPerRun.wait;
            };
        });
        (slotOffset * slotIdx).wait;
    };

    // ----------------------------------------------------------------------
    // Auto-exit when all slots done (prevents hanging at sc3>)
    // ----------------------------------------------------------------------
    Routine.run({
        var t0 = SystemClock.seconds;
        var timeout = 900.0; // safety: 15 min max

        loop {
            if(~sauceDone.notNil and: { ~sauceDone.values.every(_ == true) }) {
                "ALL DONE -> exit(0)".postln;
                0.exit;
            };
            if((SystemClock.seconds - t0) > timeout) {
                "TIMEOUT -> exit(1)".postln;
                1.exit;
            };
            0.25.wait;
        };
    });

});
)
