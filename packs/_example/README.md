# Example Pack

This is a reference pack demonstrating the Noise Engine pack format.

## Generators

### Sine Drone
A simple sine-based drone generator with:
- **HRM** - Harmonic content (pure sine to rich overtones)
- **DTN** - Stereo detune spread
- **VIB** - Vibrato depth

### Pulse Bass
A classic pulse wave bass with:
- **PWM** - Base pulse width
- **DPT** - PWM modulation depth
- **RAT** - PWM modulation rate
- **SUB** - Sub oscillator level

## Creating Your Own Pack

1. Copy this `_example` folder and rename it (e.g., `my_pack`)
2. Edit `manifest.json` with your pack details
3. Add your generators to the `generators/` folder
4. Update the `generators` array in the manifest

See `docs/PACK_SPEC.md` for full documentation.
