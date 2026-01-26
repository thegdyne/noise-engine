/*
FX Slot Manager - UI Refresh Phase 1
Manages 4 swappable FX slots with generic send/return architecture

Each slot can be assigned a different effect type:
  - empty: Silent passthrough
  - echo: Tape delay (adapted from tape_echo.scd)
  - reverb: Plate reverb (adapted from reverb.scd)
  - chorus: Stereo ensemble
  - lofi: Bitcrush/sample rate reduction

All FX types share the canonical parameter pattern:
  p1, p2, p3, p4 - 4 generic params (0-1, meaning varies by type)
  return - Return level (0-1)
  bypass - Bypass toggle (0/1)

The slot manager handles:
  - Tracking which synth is in each slot
  - Hot-swapping effect types
  - Connecting to appropriate send/return buses
*/

~setupFxSlots = {
    "Setting up FX Slot Manager...".postln;

    // Track synth instances (nil = empty)
    ~fxSlotSynths = Array.fill(4, { nil });

    // Track effect types (symbol)
    ~fxSlotTypes = [\empty, \empty, \empty, \empty];

    // Default slot parameters (4 slots x 5 params each: p1, p2, p3, p4, return)
    ~fxSlotParams = Array.fill(4, {
        Dictionary[\p1 -> 0.5, \p2 -> 0.5, \p3 -> 0.5, \p4 -> 0.5, \return -> 0.5, \bypass -> 0]
    });

    // Available FX types
    ~fxSlotAvailableTypes = [\empty, \echo, \reverb, \chorus, \lofi];

    // Map type symbols to SynthDef names
    ~fxSlotSynthNames = Dictionary[
        \empty -> \fxSlot_empty,
        \echo -> \fxSlot_echo,
        \reverb -> \fxSlot_reverb,
        \chorus -> \fxSlot_chorus,
        \lofi -> \fxSlot_lofi
    ];

    "  [x] FX Slot Manager state ready".postln;
};

// Set FX type for a slot (0-3)
~setFxSlotType = { |slotIndex, fxType|
    var inBus, outBus, synthName, params;

    if((slotIndex < 0) || (slotIndex >= 4)) {
        ("FX Slot: Invalid slot index " ++ slotIndex).warn;
    } {
        // Free existing synth
        if(~fxSlotSynths[slotIndex].notNil) {
            ~fxSlotSynths[slotIndex].free;
            ~fxSlotSynths[slotIndex] = nil;
        };

        // Get buses for this slot
        inBus = ~fxSendBuses[slotIndex];
        outBus = ~fxReturnBuses[slotIndex];

        // Get SynthDef name
        synthName = ~fxSlotSynthNames[fxType] ? \fxSlot_empty;

        // Get current params
        params = ~fxSlotParams[slotIndex];

        // Create new synth in fxGroup
        ~fxSlotSynths[slotIndex] = Synth(synthName, [
            \inBus, inBus,
            \outBus, outBus,
            \p1, params[\p1],
            \p2, params[\p2],
            \p3, params[\p3],
            \p4, params[\p4],
            \returnLevel, params[\return],
            \bypass, params[\bypass]
        ], ~fxGroup, \addToTail);

        // Update type tracking
        ~fxSlotTypes[slotIndex] = fxType;

        ("  [x] FX Slot " ++ (slotIndex + 1) ++ " -> " ++ fxType).postln;
    };
};

// Set a parameter on a slot
~setFxSlotParam = { |slotIndex, paramKey, value|
    if((slotIndex >= 0) && (slotIndex < 4)) {
        ~fxSlotParams[slotIndex][paramKey] = value;

        // Update synth if running
        if(~fxSlotSynths[slotIndex].notNil) {
            case
            { paramKey == \p1 } { ~fxSlotSynths[slotIndex].set(\p1, value) }
            { paramKey == \p2 } { ~fxSlotSynths[slotIndex].set(\p2, value) }
            { paramKey == \p3 } { ~fxSlotSynths[slotIndex].set(\p3, value) }
            { paramKey == \p4 } { ~fxSlotSynths[slotIndex].set(\p4, value) }
            { paramKey == \return } { ~fxSlotSynths[slotIndex].set(\returnLevel, value) }
            { paramKey == \bypass } { ~fxSlotSynths[slotIndex].set(\bypass, value) };
        };
    };
};

// Initialize default slot configuration
~startFxSlots = {
    // By default, start slots 1-4 with echo, reverb, chorus, lofi
    // (Can be changed via OSC)
    ~setFxSlotType.(0, \echo);
    ~setFxSlotType.(1, \reverb);
    ~setFxSlotType.(2, \chorus);
    ~setFxSlotType.(3, \lofi);

    "  [x] FX Slots initialized with default types".postln;
};

// OSC handlers for FX slots
~setupFxSlotsOSC = {
    // Set slot type: /noise/fx/slot/N/type "echo"
    4.do { |i|
        var slotNum = i + 1;

        OSCdef(("fxSlotType" ++ slotNum).asSymbol, { |msg|
            var typeStr = msg[1].asString;
            var typeSym = typeStr.asSymbol;
            if(~fxSlotAvailableTypes.includes(typeSym)) {
                ~setFxSlotType.(i, typeSym);
            } {
                ("FX Slot: Unknown type '" ++ typeStr ++ "'").warn;
            };
        }, '/noise/fx/slot/' ++ slotNum ++ '/type');

        // Per-param handlers: /noise/fx/slot/N/p1 etc
        [\p1, \p2, \p3, \p4, \return, \bypass].do { |param|
            OSCdef(("fxSlot" ++ slotNum ++ "_" ++ param).asSymbol, { |msg|
                var val = msg[1].asFloat.clip(0, 1);
                ~setFxSlotParam.(i, param, val);
            }, '/noise/fx/slot/' ++ slotNum ++ '/' ++ param);
        };
    };

    "  [x] FX Slot OSC handlers ready".postln;
};
