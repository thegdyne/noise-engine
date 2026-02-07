/*
Clock Rate Registry — Single Source of Truth

All clock consumers (modulators, FX) MUST use these definitions.
DO NOT define local clockMults arrays elsewhere.

Order is stable — changing breaks presets.
*/

(
// === THE REGISTRY ===
~CLOCK_RATE_LABELS = [
    "/32", "/16", "/12", "/8", "/4", "/2",
    "CLK",
    "x2", "x4", "x8", "x12", "x16", "x32"
];

~CLOCK_RATE_MULTS = [
    1/32, 1/16, 1/12, 1/8, 1/4, 1/2,
    1,
    2, 4, 8, 12, 16, 32
];

// === ACCESSORS ===

// Get multiplier by index (clamped 0-12)
~clockMultAt = { |idx|
    ~CLOCK_RATE_MULTS[idx.clip(0, 12).asInteger];
};

// Get label by index (clamped 0-12)
~clockLabelAt = { |idx|
    ~CLOCK_RATE_LABELS[idx.clip(0, 12).asInteger];
};

// Get index from label string (returns -1 if not found / "OFF")
~clockRateIndexOfLabel = { |label|
    var idx;
    if (label.isNil or: { label == "" } or: { label.asString.toUpper == "OFF" }) {
        -1
    } {
        idx = ~CLOCK_RATE_LABELS.indexOf(label.asString);
        idx ?? -1;
    };
};

// Get multiplier from label string (returns 0 if not found / "OFF")
~clockMultOfLabel = { |label|
    var idx = ~clockRateIndexOfLabel.(label);
    if (idx >= 0) { ~CLOCK_RATE_MULTS[idx] } { 0 };
};

"[clock_registry] Loaded: 13 clock rates".postln;
)
