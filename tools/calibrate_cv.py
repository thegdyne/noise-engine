#!/usr/bin/env python3
"""
CV.OCD Voltage Calibration Tool

Measures actual CV.OCD voltage output for accurate voltage mapping.
The measured value is used as vmax_calibrated in MorphMapper.

Usage:
    python tools/calibrate_cv.py

Requirements:
    - CV.OCD connected via USB and configured (CVA = CC1, Channel 1)
    - MOTU M6 or CV.OCD MIDI port available
    - Multimeter connected to CV.OCD CVA output

Hardware setup:
    CV.OCD CVA output → Multimeter (DC voltage mode)
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from hardware.midi_cv import MidiCV, find_preferred_port


def run_calibration():
    """Run CV.OCD voltage calibration procedure (R6)."""
    print("=" * 60)
    print("CV.OCD Voltage Calibration Tool")
    print("=" * 60)
    print()

    # Find MIDI port
    port = find_preferred_port()
    if not port:
        print("ERROR: No CV.OCD or MOTU port found.")
        print("Available ports:", MidiCV.list_ports())
        return

    print(f"Using MIDI port: {port}")
    print()
    print("Setup checklist:")
    print("  [ ] CV.OCD powered and connected via USB")
    print("  [ ] CV.OCD configured: CVA = CC1, Channel 1")
    print("  [ ] Multimeter connected to CVA output (DC voltage mode)")
    print()

    try:
        input("Press Enter when ready...")
    except (EOFError, KeyboardInterrupt):
        print("\nCalibration cancelled.")
        return

    with MidiCV(port_name=port, cc_number=1) as cv:
        # Send minimum value first
        print("\n[1/3] Sending CC 0 (minimum)...")
        cv.send_cv(0)
        print("      Expected: ~0V")
        input("      Press Enter to continue...")

        # Send midpoint
        print("\n[2/3] Sending CC 64 (midpoint)...")
        cv.send_cv(64)
        print("      Expected: ~2.5V (for 5V range)")
        input("      Press Enter to continue...")

        # Send maximum
        print("\n[3/3] Sending CC 127 (maximum)...")
        cv.send_cv(127)
        print()
        print("=" * 60)
        print("MEASUREMENT REQUIRED")
        print("=" * 60)
        print()
        print("Read the multimeter and enter the voltage below.")
        print("Typical range: 4.9V - 5.1V (not exactly 5.0V)")
        print()

        try:
            volts_str = input("Enter measured voltage (e.g., 4.95): ").strip()
            volts = float(volts_str)

            if not (3.0 <= volts <= 6.0):
                print(f"\nWARNING: Unusual voltage {volts}V")
                print("         Verify measurement or CV.OCD configuration")
            elif not (4.5 <= volts <= 5.5):
                print(f"\nNOTE: {volts}V is outside typical 5V range")
                print("      This is OK if CV.OCD is configured for different range")

            print()
            print("=" * 60)
            print("CALIBRATION COMPLETE")
            print("=" * 60)
            print()
            print(f"  Measured Vmax: {volts}V")
            print()
            print("Use this value in MorphMapper:")
            print(f"  vmax_calibrated={volts}")
            print()
            print("Example:")
            print(f"  mapper = MorphMapper(")
            print(f"      ...,")
            print(f"      vmax_calibrated={volts},")
            print(f"      cv_mode='unipolar'")
            print(f"  )")

        except ValueError:
            print("\nERROR: Invalid input. Must be a number (e.g., 4.95)")

        finally:
            print("\nResetting CV to 0V...")
            cv.send_cv(0)
            print("Done.")


def main():
    """Entry point."""
    try:
        run_calibration()
    except KeyboardInterrupt:
        print("\n\nCalibration cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
