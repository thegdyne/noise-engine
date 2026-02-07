# Clock Rate Registry

Single source of truth for clock rate definitions across SC and Python.

## The 13 Clock Rates

| Idx | Label | Multiplier | Decimal     | Notes |
|-----|-------|------------|-------------|-------|
| 0   | /32   | 1/32       | 0.03125     | Slowest - whole note triplet at 4/4 |
| 1   | /16   | 1/16       | 0.0625      | Half note triplet |
| 2   | /12   | 1/12       | 0.0833...   | Triplet (3:2 ratio) |
| 3   | /8    | 1/8        | 0.125       | Half note |
| 4   | /4    | 1/4        | 0.25        | Quarter note half-time |
| 5   | /2    | 1/2        | 0.5         | Half-time |
| 6   | CLK   | 1          | 1.0         | Base tempo (quarter note at BPM) |
| 7   | x2    | 2          | 2.0         | Double-time (eighth note) |
| 8   | x4    | 4          | 4.0         | Sixteenth note |
| 9   | x8    | 8          | 8.0         | 32nd note |
| 10  | x12   | 12         | 12.0        | Triplet 32nds |
| 11  | x16   | 16         | 16.0        | 64th note |
| 12  | x32   | 32         | 32.0        | Fastest |

**Total:** 13 clock rates (indices 0-12)

## Rules

1. **NO module defines its own clock tables** — use registry only
2. **Index order is stable** — changing breaks presets
3. **To add/change rates:** Edit both files together:
   - `supercollider/core/clock_registry.scd`
   - `src/config/__init__.py`
4. **New rates:** Add at END only (index 13+) to preserve existing preset compatibility

## Architecture

### SuperCollider (SSOT)

**File:** `supercollider/core/clock_registry.scd`

Defines:
- `~CLOCK_RATE_LABELS` - Array of 13 label strings
- `~CLOCK_RATE_MULTS` - Array of 13 multiplier values
- `~clockMultAt.(idx)` - Get multiplier by index (clamped 0-12)
- `~clockLabelAt.(idx)` - Get label by index (clamped 0-12)
- `~clockRateIndexOfLabel.(label)` - Get index from label string (returns -1 if not found / "OFF")
- `~clockMultOfLabel.(label)` - Get multiplier from label string (returns 0 if not found / "OFF")

**Usage in SynthDefs:**
```supercollider
// OLD (duplicated table):
var clockMults = [1/32, 1/16, ...];
var mult = Select.kr(idx, clockMults);

// NEW (registry):
// NOTE: Use Select.kr in SynthDef context (idx is a UGen, not an integer)
var mult = Select.kr(idx.clip(0, 12), ~clockRateMults);
```

**Usage in OSC handlers:**
```supercollider
// OLD (case ladder):
var idx = case
    { rateStr == "/32" } { 0 }
    { rateStr == "/16" } { 1 }
    ...
    { -1 };

// NEW (registry):
var idx = ~clockRateIndexOfLabel.(rateStr);  // -1 if OFF/invalid
var mult = if (idx >= 0) { ~CLOCK_RATE_MULTS[idx] } { 0 };
```

### Python (Mirror)

**File:** `src/config/__init__.py`

```python
# IMPORTANT: Must match SC clock_registry.scd order exactly (13 rates)
# Changing order breaks presets - only add new rates at the end
CLOCK_RATES = ["/32", "/16", "/12", "/8", "/4", "/2", "CLK", "x2", "x4", "x8", "x12", "x16", "x32"]
CLOCK_DEFAULT_INDEX = 6  # CLK
```

## Files Using Registry

| File | Usage | Context |
|------|-------|---------|
| `supercollider/core/buses.scd` | `~clockRates = ~clockRateMults` | Boot time |
| `supercollider/core/mod_lfo.scd` | `clockMult = Select.kr(clkIdxClamped, ~clockRateMults)` | SynthDef (UGen) |
| `supercollider/core/mod_arseq_plus.scd` | `clockMult = Select.kr(clkIdxClamped, ~clockRateMults)` | SynthDef (UGen) |
| `supercollider/effects/dual_filter.scd` | `idx = ~clockRateIndexOfLabel.(rateStr)` | OSC handler (integer) |

## Audit Commands

Run these to verify no duplicate definitions remain:

```bash
# Should return 0 hits (except comments and this doc)
cd ~/repos/noise-engine
grep -R "clockMults = \[" supercollider/ --exclude-dir=.git

# Should return 0 hits
grep -R "fbRateToMult\|fbRateToIndex" supercollider/ --exclude-dir=.git

# Should only hit registry file and buses.scd
grep -R "1/32, 1/16" supercollider/ --exclude-dir=.git

# Verify Python matches SC (should output matching arrays)
python3 -c "from src.config import CLOCK_RATES; print(len(CLOCK_RATES), CLOCK_RATES)"
# Expected: 13 ['/32', '/16', '/12', '/8', '/4', '/2', 'CLK', 'x2', 'x4', 'x8', 'x12', 'x16', 'x32']
```

## Migration History

**Before:** Clock rates defined in 4+ places:
- `buses.scd` - hardcoded array
- `mod_lfo.scd` - local `clockMults` array
- `mod_arseq_plus.scd` - local `clockMults` array
- `dual_filter.scd` - string→mult and string→idx case ladders

**After:** Single registry (`clock_registry.scd`) with accessor functions, all consumers reference it.

## Special Cases

### "OFF" / Disabled State

- Index: `-1`
- Multiplier: `0`
- Label: `""` or `"OFF"` (case-insensitive)

Example:
```supercollider
~clockRateIndexOfLabel.("OFF")  // Returns -1
~clockRateIndexOfLabel.("")     // Returns -1
~clockMultOfLabel.("OFF")       // Returns 0
```

### Free-Running Mode

When a modulator or effect is in "free" mode (not clock-synced):
- `clkIdx` parameter is set to `-1`
- Uses alternative rate parameter (e.g., `rate` slider 0-1 mapped to Hz)

### Legacy Rate Slider Fallback

Modulators support backward compatibility:
```supercollider
// If clkIdx < 0, derive from rate slider (0-1 -> 0-12)
var legacyIdx = (rate * 12).round.clip(0, 12);
var effIdx = Select.kr(clkIdx >= 0, [legacyIdx, clkIdx.round]);
```

This preserves old preset behavior where rate slider directly controlled clock division.

## See Also

- `docs/CLOCK_FABRIC.md` - Clock timing architecture (pre-divided trigger buses)
- `docs/DECISIONS.md` - Design decision log
- `supercollider/core/clock.scd` - Master clock implementation
