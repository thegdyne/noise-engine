#!/usr/bin/env python3
"""
Hardware Characterization Tool for MIDI-CV response measurement.

Sends CV values via MIDI->CV.OCD and captures audio response from Buchla 258.

Hardware chain:
    Python -> MOTU M6 MIDI Out -> CV.OCD -> CVA -> Buchla 258 Morph CV
                                                        |
    Python <- MOTU M6 Audio In <------------------------+

Usage:
    # List available devices
    python tools/hw_characterize.py --list-devices

    # Manual CC test (Phase 1 verification)
    python tools/hw_characterize.py --manual --midi-port "MOTU M6"

    # Full sweep with audio capture
    python tools/hw_characterize.py --sweep --midi-port "MOTU M6" --audio-device 1

    # Sweep with custom range
    python tools/hw_characterize.py --sweep --start 0 --end 127 --step 4
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from hardware.midi_cv import MidiCV, find_motu_port


def list_devices():
    """List all available MIDI and audio devices."""
    print("=== MIDI Output Ports ===")
    try:
        ports = MidiCV.list_ports()
        if ports:
            for i, port in enumerate(ports):
                print(f"  [{i}] {port}")
        else:
            print("  (no MIDI ports found)")
    except Exception as e:
        print(f"  Error listing MIDI ports: {e}")

    print("\n=== Audio Devices ===")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(devices)
    except Exception as e:
        print(f"  Error listing audio devices: {e}")


def manual_test(midi_port: str, cc: int = 1, channel: int = 0):
    """
    Interactive manual CC test for Phase 1 verification.

    Use a multimeter on CV.OCD output or listen to pitch changes.
    """
    print(f"\n=== Manual CC Test ===")
    print(f"MIDI Port: {midi_port}")
    print(f"CC{cc} on Channel {channel + 1}")
    print("\nCommands:")
    print("  0-127  : Send CC value")
    print("  s      : Sweep 0->127")
    print("  r      : Reverse sweep 127->0")
    print("  q      : Quit")
    print()

    with MidiCV(port_name=midi_port, cc_number=cc, channel=channel) as midi_cv:
        while True:
            try:
                cmd = input("CC value (0-127) or command: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd == 'q':
                break
            elif cmd == 's':
                print("Sweeping 0->127...")
                midi_cv.sweep(0, 127, step=1, delay=0.05)
                print("Done")
            elif cmd == 'r':
                print("Sweeping 127->0...")
                midi_cv.sweep(127, 0, step=1, delay=0.05)
                print("Done")
            elif cmd.isdigit():
                value = int(cmd)
                if 0 <= value <= 127:
                    midi_cv.send_cv(value)
                    print(f"Sent CC{cc}={value}")
                else:
                    print("Value must be 0-127")
            else:
                print("Unknown command")


def capture_audio(
    device: int,
    duration: float = 0.5,
    sample_rate: int = 48000,
    channels: int = 1,
) -> np.ndarray:
    """Capture audio from input device."""
    import sounddevice as sd

    frames = int(duration * sample_rate)
    recording = sd.rec(frames, samplerate=sample_rate, channels=channels,
                       device=device, dtype='float32')
    sd.wait()
    return recording.flatten()


def measure_frequency(audio: np.ndarray, sample_rate: int = 48000) -> float:
    """
    Estimate fundamental frequency using zero-crossing rate.

    Returns frequency in Hz, or 0 if signal too weak.
    """
    # Check if signal is strong enough
    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 0.01:
        return 0.0

    # Zero-crossing detection
    zero_crossings = np.where(np.diff(np.signbit(audio)))[0]
    if len(zero_crossings) < 2:
        return 0.0

    # Average period from zero crossings
    periods = np.diff(zero_crossings)
    avg_period = np.mean(periods) * 2  # Full cycle = 2 half-cycles
    frequency = sample_rate / avg_period

    return frequency


def measure_rms(audio: np.ndarray) -> float:
    """Calculate RMS amplitude."""
    return float(np.sqrt(np.mean(audio ** 2)))


def run_sweep(
    midi_port: str,
    audio_device: int,
    start: int = 0,
    end: int = 127,
    step: int = 4,
    settle_time: float = 0.1,
    capture_duration: float = 0.2,
    cc: int = 1,
    channel: int = 0,
    output_file: Optional[str] = None,
):
    """
    Run a CV sweep and measure audio response at each step.

    Args:
        midi_port: MIDI output port name
        audio_device: Audio input device index
        start: Starting CC value
        end: Ending CC value
        step: CC value increment
        settle_time: Time to wait after CC change before capture
        capture_duration: Audio capture duration per measurement
        cc: CC number for CV.OCD
        channel: MIDI channel (0-indexed)
        output_file: Optional JSON file for results
    """
    import sounddevice as sd

    print(f"\n=== CV Sweep Characterization ===")
    print(f"MIDI Port: {midi_port}")
    print(f"Audio Device: {audio_device}")
    print(f"Sweep: CC{cc} {start}->{end} step {step}")
    print()

    # Get sample rate from device
    device_info = sd.query_devices(audio_device)
    sample_rate = int(device_info['default_samplerate'])
    print(f"Sample rate: {sample_rate} Hz")

    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'midi_port': midi_port,
            'audio_device': audio_device,
            'sample_rate': sample_rate,
            'cc_number': cc,
            'channel': channel + 1,
            'settle_time': settle_time,
            'capture_duration': capture_duration,
        },
        'measurements': []
    }

    values = range(start, end + 1, step) if start <= end else range(start, end - 1, -step)
    total = len(list(values))
    values = range(start, end + 1, step) if start <= end else range(start, end - 1, -step)

    with MidiCV(port_name=midi_port, cc_number=cc, channel=channel) as midi_cv:
        for i, cv_value in enumerate(values):
            # Send CV
            midi_cv.send_cv(cv_value)
            time.sleep(settle_time)

            # Capture audio
            audio = capture_audio(audio_device, capture_duration, sample_rate)

            # Measure
            freq = measure_frequency(audio, sample_rate)
            rms = measure_rms(audio)

            measurement = {
                'cc_value': cv_value,
                'frequency_hz': round(freq, 2),
                'rms': round(rms, 6),
            }
            results['measurements'].append(measurement)

            # Progress
            progress = (i + 1) / total * 100
            print(f"[{progress:5.1f}%] CC={cv_value:3d}  freq={freq:7.1f} Hz  rms={rms:.4f}")

    # Save results
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = Path('characterization_results.json')

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # Summary
    measurements = results['measurements']
    freqs = [m['frequency_hz'] for m in measurements if m['frequency_hz'] > 0]
    if freqs:
        print(f"\nFrequency range: {min(freqs):.1f} - {max(freqs):.1f} Hz")
        print(f"Measurements with signal: {len(freqs)}/{len(measurements)}")


def main():
    parser = argparse.ArgumentParser(
        description='Hardware characterization for MIDI-CV response measurement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Actions
    parser.add_argument('--list-devices', action='store_true',
                        help='List available MIDI and audio devices')
    parser.add_argument('--manual', action='store_true',
                        help='Interactive manual CC test')
    parser.add_argument('--sweep', action='store_true',
                        help='Run automated CV sweep with audio capture')

    # MIDI settings
    parser.add_argument('--midi-port', type=str,
                        help='MIDI output port name')
    parser.add_argument('--cc', type=int, default=1,
                        help='CC number (default: 1 for CV.OCD CVA)')
    parser.add_argument('--channel', type=int, default=1,
                        help='MIDI channel 1-16 (default: 1)')

    # Audio settings
    parser.add_argument('--audio-device', type=int,
                        help='Audio input device index')

    # Sweep settings
    parser.add_argument('--start', type=int, default=0,
                        help='Sweep start CC value (default: 0)')
    parser.add_argument('--end', type=int, default=127,
                        help='Sweep end CC value (default: 127)')
    parser.add_argument('--step', type=int, default=4,
                        help='Sweep step size (default: 4)')
    parser.add_argument('--settle', type=float, default=0.1,
                        help='Settle time after CC change (default: 0.1s)')
    parser.add_argument('--capture', type=float, default=0.2,
                        help='Audio capture duration (default: 0.2s)')
    parser.add_argument('--output', type=str,
                        help='Output JSON file for results')

    args = parser.parse_args()

    # Convert channel to 0-indexed
    channel = args.channel - 1

    if args.list_devices:
        list_devices()
        return

    if args.manual:
        port = args.midi_port or find_motu_port()
        if not port:
            print("Error: --midi-port required (or connect a MOTU device)")
            print("Run with --list-devices to see available ports")
            sys.exit(1)
        manual_test(port, cc=args.cc, channel=channel)
        return

    if args.sweep:
        port = args.midi_port or find_motu_port()
        if not port:
            print("Error: --midi-port required")
            sys.exit(1)
        if args.audio_device is None:
            print("Error: --audio-device required for sweep")
            print("Run with --list-devices to see available devices")
            sys.exit(1)

        run_sweep(
            midi_port=port,
            audio_device=args.audio_device,
            start=args.start,
            end=args.end,
            step=args.step,
            settle_time=args.settle,
            capture_duration=args.capture,
            cc=args.cc,
            channel=channel,
            output_file=args.output,
        )
        return

    # Default: show help
    parser.print_help()


if __name__ == '__main__':
    main()
