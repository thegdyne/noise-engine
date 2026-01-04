/*
=============================================================================
SauceOfGrav Parameter Test Suite v13.0  (PARALLEL RUNNER - single file)
=============================================================================

- Runs 4 slots in parallel
- Runs N times per slot
- Writes per-slot logs: /tmp/sauce_test_v13_slot1.txt .. slot4.txt
- Uses .protect to always close files + free synth nodes even on error
=============================================================================
*/

(
var slots = 4;
var runsPerSlot = 5;
var delayPerRun = 400.0;
var slotOffset = 120.0;
var totalRuns = slots * runsPerSlot;

~sauceDone ?? { ~sauceDone = IdentityDictionary.new };
~sauceBusy ?? { ~sauceBusy = IdentityDictionary.new };
~sauceGroups ?? { ~sauceGroups = Array.fill(slots, { Group.head(Server.default) }) };


// ensure storage exists
~modNodes ?? { ~modNodes = Array.newClear(slots) };
Server.default.notify = true;  // enables /n_go /n_end so NodeWatcher can track nodes



slots.do { |i|
    ~sauceDone[i] = false;
    ~sauceBusy[i] = false;
};

// ----------------------------------------------------------------------
// ONE RUN (for a given slot + run number)
// ----------------------------------------------------------------------
~runSauceV13 = { |slot=0, runNo=1, total=5|
    fork {
        var baseBus, outFile, testResults, testsPassed, testsFailed;
        var createSynthArgs, resetSynth, captureStats, setParams, runComparison, runFloor;

        baseBus = slot * 4;
        testsPassed = 0;
        testsFailed = 0;
        testResults = List.new;

        createSynthArgs = {
            [
                \out1, ~modBuses[baseBus].index,
                \out2, ~modBuses[baseBus + 1].index,
                \out3, ~modBuses[baseBus + 2].index,
                \out4, ~modBuses[baseBus + 3].index,
                \clockTrigBus, ~clockTrigBus.index,
                \clockIndex, 12,
                \bpmBus, ~clockBus.index
            ]
        };

		resetSynth = {
			// --- ensure per-slot group exists (safe to call every time) ---
			~sauceGroups ?? { ~sauceGroups = Array.newClear(slots) };
			if(~sauceGroups[slot].isNil) {
				~sauceGroups[slot] = Group.head(Server.default);
				Server.default.sync;
			};

			// --- hard kill anything still running in this slot (no NodeWatcher reliance) ---
			~sauceGroups[slot].freeAll;
			Server.default.sync;
			~modNodes[slot] = nil;
			0.05.wait;

			// --- recreate synth inside the slot group ---
			~modNodes[slot] = Synth.tail(~sauceGroups[slot], \ne_mod_sauce_of_grav, createSynthArgs.());
			NodeWatcher.register(~modNodes[slot]);   // <- this is what you wanted
			Server.default.sync;

			"  [Synth recreated - fresh state]".postln;
			0.2.wait;
		};





        captureStats = { |duration=12|
            var samples, mins, maxs, sums, sumsSq, crossings, prevSide, prevVals, totalMovement, allVals;
            var hubMin, hubMax, hubSum, hubPrev, hubMove, hubCross, hubPrevSide;
            var means, stds, corrs, ranges, hubMean;

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

            samples.do {
                var vals, hub, hubSide;
                vals = 4.collect { |j| ~modBuses[baseBus + j].getSynchronous };
                hub = (vals[0] + vals[1] + vals[2] + vals[3]) * 0.25;
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

            // Calculate correlations
            means = 4.collect { |i| sums[i] / samples };
            stds = 4.collect { |i|
                var variance;
                variance = (sumsSq[i] / samples) - (means[i] * means[i]);
                variance.max(0.0001).sqrt;
            };

            corrs = List.new;
            [[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]].do { |pair|
                var i, j, cov;
                i = pair[0];
                j = pair[1];
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
                duration: duration
            )
        };

		setParams = { |params|
			var synth = ~modNodes[slot];

			if(synth.isNil) {
				"  [WARN] setParams: synth is nil (slot %)".format(slot+1).postln;
				^nil;
			};

			if(synth.isPlaying.not) {  // avoids /n_set on a freed node
				"  [WARN] setParams: synth not playing (slot %)".format(slot+1).postln;
				^nil;
			};

			params.keysValuesDo { |key, val| synth.set(key, val) };
			Server.default.sync;   // make sure sets land before capture
			2.wait;
		};


        runComparison = { |testId, name, baseParams, lowParams, highParams, metric, expectedDir, minDelta, description, duration=12|
            var lowStats, highStats, delta, passed, resultStr, isHubMetric;

            isHubMetric = [\hubRange, \hubMeanDev, \hubMovement].includes(metric);

            "\n=== %: % ===".format(testId, name).postln;
            outFile.write("\n=== %: % ===\n".format(testId, name));
            outFile.write("  %\n".format(description));

            "  Testing LOW...".postln;
            resetSynth.value;
            setParams.value(baseParams);
            setParams.value(lowParams);
            lowStats = captureStats.value(duration);

            "  Testing HIGH...".postln;
            resetSynth.value;
            setParams.value(baseParams);
            setParams.value(highParams);
            highStats = captureStats.value(duration);

            delta = switch(metric,
                \avgRange,       { highStats[\avgRange]       - lowStats[\avgRange] },
                \meanDev,        { highStats[\meanDev]        - lowStats[\meanDev] },
                \avgCrossings,   { highStats[\avgCrossings]   - lowStats[\avgCrossings] },
                \rangeSpread,    { highStats[\rangeSpread]    - lowStats[\rangeSpread] },
                \avgMovement,    { highStats[\avgMovement]    - lowStats[\avgMovement] },
                \avgCorrelation, { highStats[\avgCorrelation] - lowStats[\avgCorrelation] },
                \hubRange,       { highStats[\hubRange]       - lowStats[\hubRange] },
                \hubMeanDev,     { highStats[\hubMeanDev]     - lowStats[\hubMeanDev] },
                \hubMovement,    { highStats[\hubMovement]    - lowStats[\hubMovement] }
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

        runFloor = { |testId, name, baseParams, testParams, metric, minValue, description, duration=12|
            var stats, passed, resultStr;

            "\n=== %: % ===".format(testId, name).postln;
            outFile.write("\n=== %: % ===\n".format(testId, name));
            outFile.write("  %\n".format(description));

            "  Testing...".postln;
            resetSynth.value;
            setParams.value(baseParams);
            setParams.value(testParams);
            stats = captureStats.value(duration);

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
        outFile = File("/tmp/sauce_test_v13_slot%.txt".format(slot + 1), "a");

        {
            ("=== RUN % / % (slot % , baseBus %) ===".format(runNo, total, slot + 1, baseBus)).postln;

            outFile.write("\n\n=== RUN % / % (slot % , baseBus %) ===\n".format(runNo, total, slot + 1, baseBus));
            outFile.write("SauceOfGrav Parameter Test Suite v13.0\n");
            outFile.write("Date: %\n".format(Date.localtime.asString));
            outFile.write("R01 metric fix (avgRange instead of avgMovement)\n");
            outFile.write("=".dup(70).join ++ "\n");

            if(~modBuses.isNil or: { ~clockTrigBus.isNil } or: { ~clockBus.isNil }) {
                "ERROR: Required buses not found. Run init.scd first.".postln;
                outFile.write("ERROR: Required buses not found. Run init.scd first.\n");
            } {
                "Starting tests on slot % (baseBus %)...\n".format(slot + 1, baseBus).postln;

                outFile.write("\n=== D01: DEPTH (SKIPPED) ===\n");
                outFile.write("  Hub damping not observable via lane outputs.\n");
                "=== D01: DEPTH (SKIPPED - not testable via outputs) ===".postln;

                runComparison.value("G01", "GRAVITY affects center pull (isolated)",
                    (clockMode: 1, rate: 0.5, depth: 0.5, resonance: 0.5, excursion: 1.0, calm: 0.5, tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5, mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
                    (gravity: 0.0),
                    (gravity: 1.0),
                    \meanDev, \decrease, 0.005,
                    "GRAVITY (isolated): excursion=1 amplifies hub. High gravity = tight around 0.5.",
                    12
                );

                runComparison.value("R01", "RESONANCE sustains dying system",
                    (clockMode: 1, rate: 0.0, depth: 1.0, gravity: 0.7, excursion: 0.5, calm: 0.0, tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5, mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
                    (resonance: 0.0),
                    (resonance: 1.0),
                    \avgRange, \increase, 0.02,
                    "RESONANCE (die vs sustain): high damping regime. Resonance keeps motion alive = larger range.",
                    24
                );

                runComparison.value("E01", "EXCURSION affects hub travel (hub proxy)",
                    (clockMode: 1, rate: 0.0, depth: 0.85, gravity: 0.35, resonance: 0.0, calm: 0.25, tension1: 0.2, tension2: 0.4, tension3: 0.6, tension4: 0.8, mass1: 0.7, mass2: 0.5, mass3: 0.4, mass4: 0.3),
                    (excursion: 0.0),
                    (excursion: 1.0),
                    \hubRange, \increase, 0.03,
                    "EXCURSION scales hubTarget via excursionGain. Use hub proxy (mean of lanes) range.",
                    24
                );

                runComparison.value("C01", "CALM affects motion amplitude",
                    (clockMode: 1, rate: 0.5, depth: 0.5, gravity: 0.5, resonance: 0.5, excursion: 0.5, tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5, mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
                    (calm: 0.0),
                    (calm: 1.0),
                    \avgRange, \increase, 0.1,
                    "CALM: 0=calm(small motion), 1=wild(big swings). Wild has larger range.",
                    12
                );

                outFile.write("\n=== F01: RATE (SKIPPED) ===\n");
                "=== F01: RATE (SKIPPED - refresh timing, not physics) ===".postln;

                runFloor.value("F02", "RATE low still has motion (floor)",
                    (clockMode: 1, depth: 0.5, gravity: 0.5, resonance: 0.5, excursion: 0.5, calm: 0.5, tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5, mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
                    (rate: 0.1),
                    \avgRange, 0.20,
                    "RATE is refresh timing. Assert low rate is not dead (avgRange floor).",
                    12
                );

                runComparison.value("T01", "TENSION affects interaction",
                    (clockMode: 1, rate: 0.5, depth: 0.5, gravity: 0.5, resonance: 0.0, excursion: 0.5, calm: 0.5, mass1: 0.5, mass2: 0.5, mass3: 0.5, mass4: 0.5),
                    (tension1: 0.0, tension2: 0.0, tension3: 0.0, tension4: 0.0),
                    (tension1: 1.0, tension2: 1.0, tension3: 1.0, tension4: 1.0),
                    \avgRange, \increase, 0.1,
                    "TENSION: High tension = more interaction = larger motion range.",
                    12
                );

                runComparison.value("M01", "MASS affects response speed",
                    (clockMode: 1, rate: 0.5, depth: 0.5, gravity: 0.5, resonance: 0.5, excursion: 0.5, calm: 0.5, tension1: 0.5, tension2: 0.5, tension3: 0.5, tension4: 0.5),
                    (mass1: 0.0, mass2: 0.0, mass3: 0.0, mass4: 0.0),
                    (mass1: 1.0, mass2: 1.0, mass3: 1.0, mass4: 1.0),
                    \avgCrossings, \decrease, 1.0,
                    "MASS is inertia. High mass = slow arcs, fewer crossings.",
                    12
                );

                // SUMMARY
                outFile.write("\n" ++ "=".dup(70).join ++ "\n");
                outFile.write("SUMMARY: % PASSED, % FAILED out of % tests (2 skipped)\n".format(testsPassed, testsFailed, testsPassed + testsFailed));

                outFile.write("\nFailed tests:\n");
                testResults.do { |t|
                    if(t[\passed].not) {
                        if(t[\delta].notNil) {
                            outFile.write("  - %: % (delta=%)\n".format(t[\id], t[\name], t[\delta].round(0.001)));
                        } {
                            outFile.write("  - %: % (value=%)\n".format(t[\id], t[\name], t[\value].round(0.001)));
                        };
                    };
                };

                outFile.write("=".dup(70).join ++ "\n");
            };
		}.protect({
			// ALWAYS runs (even if error mid-test)

			if(outFile.notNil) {
				outFile.tryPerform(\flush);
				outFile.tryPerform(\close);
				outFile = nil;
			};

			if(~modNodes.notNil and: { ~modNodes[slot].notNil }) {
				~modNodes[slot].tryPerform(\free);   // free even if client thinks it's not playing
				Server.default.sync;                 // wait for /n_free to land (helps in parallel)
				~modNodes[slot] = nil;               // prevent double-free / stale ids
			};

			~sauceDone[slot] = true;
			~sauceBusy[slot] = false;

			("<<< DONE RUN % / % (slot %) >>>".format(runNo, total, slot + 1)).postln;
		});
    };
};

// ----------------------------------------------------------------------
// SCHEDULER
// ----------------------------------------------------------------------
("=== % RUNS SCHEDULED across % slots ===".format(totalRuns, slots)).postln;

slots.do { |slotIdx|
    runsPerSlot.do { |runIdx|
        var runNum, startTime;
        runNum = runIdx + 1;
        startTime = (runIdx * delayPerRun) + (slotIdx * slotOffset);
		SystemClock.sched(startTime, {
			var tryStart;

			tryStart = {
				if(~sauceBusy[slotIdx] == true) {
					("!!! SLOT % busy, retrying RUN %".format(slotIdx + 1, runNum)).postln;
					SystemClock.sched(1.0, tryStart);   // keep retrying until free
				} {
					~sauceBusy[slotIdx] = true;
					(">>> SLOT % RUN % / %".format(slotIdx + 1, runNum, runsPerSlot)).postln;
					~runSauceV13.(slotIdx, runNum, runsPerSlot);
				};
				nil
			};

			tryStart.value;
			nil
		});
    };
};
)
