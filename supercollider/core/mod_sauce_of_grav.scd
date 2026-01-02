/*
Mod SauceOfGrav SynthDef (Phase A Final - Fixed)
4-output coupled physics modulator inspired by Buchla 266 Source of Uncertainty And NLC Sauce of UNCE!

Phase A Fixes Applied:
- A1: dt = ControlDur.ir, physics runs every control tick
- A2: Init sentinel (kickToggle) + full state initialization
- A3: Polarity uses negation (pos.neg) not mirror (1-pos)
- A4: Refresh events with CLK/FREE modes, CLK is transport-gated
- Index clamping on all Select.kr for safety
- Refresh fade applied before hubTarget (atomic timing)
- Comparator-free refresh fade (multiplier form)
- Rate input clamped before mapping
- FIX: CLK gating uses clockRunning.ceil (binary) so refresh impulses are not fractional
- Optional safety: calm/depth clamped 0..1

Reference: docs/SAUCE_OF_GRAV_SPEC_v1_4_3.md
*/

SynthDef(\ne_mod_sauce_of_grav, {
	arg out1, out2, out3, out4,
	    clockMode = 0,
	    rate = 0.5,
	    depth = 0.5,
	    gravity = 0.5,
	    resonance = 0.5,
	    excursion = 0.5,
	    calm = 0.5,
	    tension1 = 0.5, tension2 = 0.5, tension3 = 0.5, tension4 = 0.5,
	    mass1 = 0.5, mass2 = 0.5, mass3 = 0.5, mass4 = 0.5,
	    polarity1 = 0, polarity2 = 0, polarity3 = 0, polarity4 = 0,
	    clockTrigBus = 0,
	    clockIndex = 12,
	    bpmBus = 0;

	// === CONSTANTS (v1.4.3) ===
	var dt = ControlDur.ir;

	// Rate (refresh events)
	var rateDeadband = 0.05;
	var freeRateMin = 0.001;
	var freeRateMax = 100.0;

	// Mass
	var massBase = 0.25;
	var massGain = 2.1;

	// Coupling
	var hubCoupleGain = 6.0;
	var hubTensionExp = 0.70;
	var ringCoupleGain = 3.5;
	var ringTensionExp = 1.30;
	var ringSkew = 0.015;

	// Gravity
	var gravStiffGain = 6.0;

	// Excursion
	var excursionMin = 0.60;
	var excursionMax = 1.60;

	// CALM multipliers
	var calmDampCalm = 1.30;
	var calmDampWild = 0.75;
	var calmVdpCalm = 0.90;
	var calmVdpWild = 1.15;
	var calmKickCalm = 0.60;

	// Van der Pol
	var vdpInject = 0.8;
	var vdpThreshold = 0.35;
	var vdpHubMod = 0.05;
	var vdpThresholdFloor = 0.05;

	// Calibration trims
	var tensionTrim = #[0.012, -0.008, 0.015, -0.018];
	var massTrim = #[-0.010, 0.014, -0.006, 0.011];

	// Damping
	var dampingBase = 0.10;
	var dampingTension = 0.40;

	// Rails
	var railZone = 0.08;
	var railAbsorb = 0.35;

	// Resonance
	var resoFloorMin = 0.0002;
	var resoFloorMax = 0.0040;
	var resoDriveGain = 6.0;
	var resoDeltaEMax = 0.01;

	// Kickstart
	var resoKickGain = 2.8;
	var resoKickMaxF = 0.30;
	var kickCooldownS = 0.20;

	// Hub
	var hubLimit = 2.0;
	var depthDampMin = 0.005;
	var depthDampMax = 2.50;
	var hubFeedGain = 8.0;
	var hubFeedMax = 0.35;
	var noiseRate = 0.012;

	// === STATE VARIABLES ===
	var pos1, pos2, pos3, pos4;
	var vel1, vel2, vel3, vel4;
	var hubBias, hubVel;
	var kickCooldown, kickToggle, kickIndex;

	// === WORKING VARIABLES ===
	var calmBi, calmDampMul, calmVdpMul, calmKickMul;
	var gravInfluence, excursionGain, hubTarget;
	var kGrav, hubDamp;
	var mass, tensionEff, kHub, kRing, kRingFwd, kRingBwd, dampingBaseMapped;
	var vdpThresholdEff, amp, vdpFactor, dampingEff;
	var noise;
	var fGrav, fHub, fRing, fTotal;
	var eFloor, energy, fReso, fKick;
	var accel, railD, railU;
	var sig1, sig2, sig3, sig4;

	var didInit;
	var clk, atrig, trig, clockRunning;
	var bpm, rateClamped, rateActive, baseHz, clkMult, refreshHz, refreshTrig, fadeFactor;
	var calmClamped, depthClamped;

	// === CLOCK INPUT ===
	clk = In.ar(clockTrigBus + clockIndex);
	atrig = Trig1.ar(clk > 0.5, 0.001);
	trig = Trig1.kr(A2K.kr(atrig), 0.001);
	bpm = In.kr(bpmBus).max(1);
	clockRunning = Decay.kr(trig, 0.2);

	// Optional safety clamps
	calmClamped = calm.clip(0, 1);
	depthClamped = depth.clip(0, 1);

	// === CALM BIPOLAR CONVERSION ===
	calmBi = (calmClamped * 2) - 1;

	// === CALM MULTIPLIERS ===
	calmDampMul = Select.kr(calmBi < 0, [
		1.0.blend(calmDampWild, calmBi),
		1.0.blend(calmDampCalm, calmBi.neg)
	]);
	calmVdpMul = Select.kr(calmBi < 0, [
		1.0.blend(calmVdpWild, calmBi),
		1.0.blend(calmVdpCalm, calmBi.neg)
	]);
	calmKickMul = Select.kr(calmBi < 0, [
		1.0,
		1.0.blend(calmKickCalm, calmBi.neg)
	]);

	// === PARAMETER MAPPING ===
	gravInfluence = 1.0 - gravity;
	excursionGain = excursionMin + (excursion * (excursionMax - excursionMin));
	kGrav = gravStiffGain * gravity;
	hubDamp = depthDampMin + (depthClamped * (depthDampMax - depthDampMin));

	// Per-output mass with trims
	mass = [
		massBase + (massGain * (mass1 + massTrim[0]).clip(0, 1)),
		massBase + (massGain * (mass2 + massTrim[1]).clip(0, 1)),
		massBase + (massGain * (mass3 + massTrim[2]).clip(0, 1)),
		massBase + (massGain * (mass4 + massTrim[3]).clip(0, 1))
	];

	// Per-output tension with trims
	tensionEff = [
		(tension1 + tensionTrim[0]).clip(0, 1),
		(tension2 + tensionTrim[1]).clip(0, 1),
		(tension3 + tensionTrim[2]).clip(0, 1),
		(tension4 + tensionTrim[3]).clip(0, 1)
	];

	// Coupling constants
	kHub = hubCoupleGain * (tensionEff ** hubTensionExp);
	kRing = ringCoupleGain * (tensionEff ** ringTensionExp);
	kRingFwd = kRing * (1 + ringSkew);
	kRingBwd = kRing * (1 - ringSkew);

	// Base damping with CALM scaling
	dampingBaseMapped = (dampingBase + (dampingTension * (1 - tensionEff))) * calmDampMul;

	// === INIT WITH FEEDBACK ===
	# pos1, pos2, pos3, pos4, vel1, vel2, vel3, vel4,
	  hubBias, hubVel, kickCooldown, kickToggle, kickIndex = LocalIn.kr(13);

	// Sentinel: kickToggle only flips ±1, never near zero after init
	didInit = kickToggle.abs > 0.001;

	// Positions to center
	pos1 = Select.kr(didInit, [0.5, pos1]);
	pos2 = Select.kr(didInit, [0.5, pos2]);
	pos3 = Select.kr(didInit, [0.5, pos3]);
	pos4 = Select.kr(didInit, [0.5, pos4]);

	// Velocities to zero
	vel1 = Select.kr(didInit, [0.0, vel1]);
	vel2 = Select.kr(didInit, [0.0, vel2]);
	vel3 = Select.kr(didInit, [0.0, vel3]);
	vel4 = Select.kr(didInit, [0.0, vel4]);

	// Hub to zero
	hubBias = Select.kr(didInit, [0.0, hubBias]);
	hubVel  = Select.kr(didInit, [0.0, hubVel]);

	// Kick state
	kickCooldown = Select.kr(didInit, [0.0, kickCooldown]);
	kickToggle   = Select.kr(didInit, [1.0, kickToggle]);
	kickIndex    = Select.kr(didInit, [0.0, kickIndex]);

	// === REFRESH EVENTS (before hubTarget for atomic timing) ===
	rateClamped = rate.clip(0, 1);
	rateActive  = ((rateClamped - rateDeadband) / (1 - rateDeadband)).clip(0, 1);

	baseHz = bpm / 60;
	clkMult = Select.kr(
		(rateActive * 11).round.clip(0, 11),
		[1/64, 1/32, 1/16, 1/8, 1/4, 1/2, 1, 2, 4, 8, 16, 32]
	);

	refreshHz = rateActive.linexp(0, 1, freeRateMin, freeRateMax);

	refreshTrig = Select.kr(rateClamped < rateDeadband, [
		Select.kr(clockMode.round.clip(0, 1), [
			Impulse.kr(baseHz * clkMult) * clockRunning.ceil,  // FIX: binary gate
			Impulse.kr(refreshHz)
		]),
		0
	]);

	// Comparator-free fade (multiplier form)
	fadeFactor = 0.95 - (depthClamped * 0.95);
	hubBias = hubBias * (1 + (refreshTrig * (fadeFactor - 1)));
	hubVel  = hubVel  * (1 + (refreshTrig * (fadeFactor - 1)));

	// === HUB TARGET ===
	hubTarget = (0.5 + (hubBias * gravInfluence * excursionGain)).clip(0, 1);

	// === VAN DER POL DAMPING ===
	vdpThresholdEff = (vdpThreshold * (1 + (vdpHubMod * hubBias / hubLimit))).max(vdpThresholdFloor);
	amp = ([pos1, pos2, pos3, pos4] - 0.5).abs;
	vdpFactor = (vdpInject * calmVdpMul) * (1 - ((amp / vdpThresholdEff) ** 2));
	dampingEff = dampingBaseMapped - vdpFactor;

	// === VELOCITY NOISE ===
	noise = [
		WhiteNoise.kr(noiseRate) * dt.sqrt,
		WhiteNoise.kr(noiseRate) * dt.sqrt,
		WhiteNoise.kr(noiseRate) * dt.sqrt,
		WhiteNoise.kr(noiseRate) * dt.sqrt
	];
	vel1 = vel1 + noise[0];
	vel2 = vel2 + noise[1];
	vel3 = vel3 + noise[2];
	vel4 = vel4 + noise[3];

	// === FORCES ===
	fGrav = kGrav * (0.5 - [pos1, pos2, pos3, pos4]);
	fHub  = kHub  * (hubTarget - [pos1, pos2, pos3, pos4]);

	fRing = [
		(kRingFwd[0] * (pos2 - pos1)) + (kRingBwd[0] * (pos4 - pos1)),
		(kRingFwd[1] * (pos3 - pos2)) + (kRingBwd[1] * (pos1 - pos2)),
		(kRingFwd[2] * (pos4 - pos3)) + (kRingBwd[2] * (pos2 - pos3)),
		(kRingFwd[3] * (pos1 - pos4)) + (kRingBwd[3] * (pos3 - pos4))
	];

	// === RESONANCE (Phase B will add alignment + rail attenuation) ===
	eFloor = resoFloorMin + (resonance * (resoFloorMax - resoFloorMin));
	energy = 0.5 * ((mass[0] * vel1.squared) + (mass[1] * vel2.squared) +
	                (mass[2] * vel3.squared) + (mass[3] * vel4.squared));

	fReso = Select.kr(energy < eFloor, [
		[0, 0, 0, 0],
		resoDriveGain * resonance * (eFloor - energy).clip(0, resoDeltaEMax) * [vel1, vel2, vel3, vel4].sign
	]);

	// === KICKSTART (Phase B will add pattern cycling) ===
	kickCooldown = (kickCooldown - dt).max(0);

	fKick = Select.kr((energy < eFloor) * (kickCooldown < 0.001) * (resonance > 0.01), [
		[0, 0, 0, 0],
		resoKickGain * calmKickMul * (eFloor - energy).clip(0, resoKickMaxF) *
		kickToggle * [1, -1, 1, -1]
	]);

	kickCooldown = Select.kr((energy < eFloor) * (kickCooldown < 0.001) * (resonance > 0.01), [
		kickCooldown,
		kickCooldownS
	]);
	kickToggle = Select.kr((energy < eFloor) * (kickCooldown < 0.001) * (resonance > 0.01), [
		kickToggle,
		kickToggle.neg
	]);

	// === TOTAL FORCE & ACCELERATION ===
	fTotal = fGrav + fHub + fRing + fReso + fKick;
	accel = fTotal / mass;

	vel1 = vel1 + (accel[0] * dt);
	vel2 = vel2 + (accel[1] * dt);
	vel3 = vel3 + (accel[2] * dt);
	vel4 = vel4 + (accel[3] * dt);

	// === DAMPING ===
	vel1 = vel1 * (dampingEff[0] * dt).neg.exp;
	vel2 = vel2 * (dampingEff[1] * dt).neg.exp;
	vel3 = vel3 * (dampingEff[2] * dt).neg.exp;
	vel4 = vel4 * (dampingEff[3] * dt).neg.exp;

	// === INTEGRATE POSITION ===
	pos1 = pos1 + (vel1 * dt);
	pos2 = pos2 + (vel2 * dt);
	pos3 = pos3 + (vel3 * dt);
	pos4 = pos4 + (vel4 * dt);

	// === RAIL BUMPERS ===
	pos1 = pos1.clip(0, 1);
	pos2 = pos2.clip(0, 1);
	pos3 = pos3.clip(0, 1);
	pos4 = pos4.clip(0, 1);

	railD = [pos1, pos2, pos3, pos4].min(1 - [pos1, pos2, pos3, pos4]);
	railU = ((railZone - railD) / railZone).clip(0, 1);
	vel1 = vel1 * (1 - (railAbsorb * railU[0].squared));
	vel2 = vel2 * (1 - (railAbsorb * railU[1].squared));
	vel3 = vel3 * (1 - (railAbsorb * railU[2].squared));
	vel4 = vel4 * (1 - (railAbsorb * railU[3].squared));

	// === HUB DYNAMICS (Phase B will add overshoot + tanh) ===
	hubVel = hubVel + (hubFeedGain * ((pos1 - hubTarget) * vel1 + (pos2 - hubTarget) * vel2 +
	                                   (pos3 - hubTarget) * vel3 + (pos4 - hubTarget) * vel4).clip(hubFeedMax.neg, hubFeedMax) * dt);
	hubVel = hubVel * (hubDamp * dt).neg.exp;
	hubBias = hubBias + (hubVel * dt);
	hubBias = hubBias.clip(hubLimit.neg, hubLimit);

	// === FEEDBACK STATE ===
	LocalOut.kr([pos1, pos2, pos3, pos4, vel1, vel2, vel3, vel4,
	             hubBias, hubVel, kickCooldown, kickToggle, kickIndex]);

	// === OUTPUT WITH POLARITY (index clamped for safety) ===
	sig1 = Select.kr(polarity1.round.clip(0, 1), [pos1, pos1.neg]);
	sig2 = Select.kr(polarity2.round.clip(0, 1), [pos2, pos2.neg]);
	sig3 = Select.kr(polarity3.round.clip(0, 1), [pos3, pos3.neg]);
	sig4 = Select.kr(polarity4.round.clip(0, 1), [pos4, pos4.neg]);

	// === OUTPUT TO BUSES ===
	Out.kr(out1, sig1);
	Out.kr(out2, sig2);
	Out.kr(out3, sig3);
	Out.kr(out4, sig4);
}).add;

"  ✓ ne_mod_sauce_of_grav SynthDef loaded (Phase A final - fixed)".postln;
