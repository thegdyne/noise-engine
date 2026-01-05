# Needs Spec

Large/Medium features that need specification before implementation.

## MIDI Learn
CC mapping for parameters.

## Mod Matrix Expansion
Additional routing capabilities, relative modulation.

## SC State Sync on Restart
Handle case where Python frontend restarts but SC still running with previous state.

Options:
1. **Warm restart**: Query SC state and restore frontend to match
2. **Cold restart**: Force SC restart when frontend starts
3. **Hybrid**: Detect mismatch and prompt user

## Integration Tests
Tests that boot SuperCollider and verify end-to-end behavior.
