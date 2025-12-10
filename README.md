# Noise Engine

Physics-based, expressive noise instrument controlled by Akai MIDIMix.

## Architecture

- Python control layer (GUI + MIDI input)
- SuperCollider audio engine (modular generators)
- Parameter-based system with physics metaphors

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Status

- [x] Project structure
- [x] SuperCollider installed
- [ ] GUI control interface
- [ ] OSC bridge to SuperCollider
- [ ] First generator (Grainy PT2399)
