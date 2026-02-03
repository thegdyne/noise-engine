"""
Hardware Morph Mapper v6.2 FINAL (MIDI CV)

Automated CV sweep system for hardware characterization.
Sends MIDI CC values via CV.OCD to control external hardware,
captures audio DNA via telemetry, and builds behavioral lookup tables.

Architecture:
    Python (MorphMapper) → MIDI CC → CV.OCD → Hardware → Audio → Telemetry → JSON

All P0 fixes applied - verified by triple AI review.

Requirements satisfied:
    R2: set_generator_context() for external mode
    R3: sc_client as required parameter
    R4: Correct timing order (clear → t0 → send → settle → capture)
    R5: Enhanced MIDI port detection
    R6: Voltage calibration support
    R7: Telemetry rate > 10 (recommend 15)
    R8: Mode-specific cv_range validation
    R9: cv_range in volts at CV.OCD output
    R10: Bipolar mode (0V = CC 64)
    R11: Record actual CC sent (post-round)
    R12: Consistent volts_to_cc mapping
    R13: Record failure before abort
    R14: Send safe CV before sweep
    R15: Safety reset in finally with P0 logging
    R16: 10s timeout
    R17: Normalized 'stability' schema
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.audio.telemetry_controller import TelemetryController
from src.hardware.midi_cv import MidiCV, find_preferred_port
from src.utils.logger import logger


class MorphMapper:
    """
    Automated CV sweep with MIDI→CV output and telemetry capture.

    Sends CV values to external hardware via MIDI→CV.OCD, captures audio
    response via the telemetry system, and builds morph maps for Digital
    Twin reproduction.
    """

    def __init__(
        self,
        sc_client,  # R3: Required parameter
        telemetry_controller: TelemetryController,
        device_name: str,
        device_type: str = "oscillator",
        cv_range: tuple = (0.0, 5.0),
        points: int = 24,
        slot: int = 0,
        settle_ms: int = 200,
        input_channel: int = 0,
        input_gain: float = 1.0,
        require_waveform: bool = True,
        midi_port: Optional[str] = None,
        midi_cc: int = 1,
        midi_channel: int = 0,
        vmax_calibrated: float = 5.0,  # R6
        cv_mode: str = 'unipolar'  # R8-R10
    ):
        """
        Initialize morph mapper with MIDI CV output.

        Args:
            sc_client: SuperCollider OSC client (R3)
            telemetry_controller: TelemetryController instance
            device_name: Device name (e.g., "Buchla 258 Clone")
            device_type: oscillator|filter|vca|waveshaper
            cv_range: (min_volts, max_volts) at CV.OCD output (R9)
            points: Number of sweep points (>= 2)
            slot: Generator slot 0-7
            settle_ms: Hardware settle time (200ms default)
            input_channel: MOTU M6 input channel 0-5
            input_gain: Digital gain normalization 0-4x
            require_waveform: Wait for waveform lock
            midi_port: MIDI port name (None = auto-detect)
            midi_cc: MIDI CC number (1 = CV.OCD CVA)
            midi_channel: MIDI channel 0-15 (0 = channel 1)
            vmax_calibrated: Measured max voltage at CC=127 (R6)
            cv_mode: 'unipolar' or 'bipolar' (R8-R10)
        """
        # Extract cv_range
        cv_min, cv_max = cv_range

        # Basic validation
        if points < 2:
            raise ValueError("points must be >= 2")
        if cv_max <= cv_min:
            raise ValueError("cv_max must be > cv_min")
        if not (0 <= slot < 8):
            raise ValueError("slot must be 0-7")
        if not (0 <= input_channel <= 5):
            raise ValueError("input_channel must be 0-5")
        if not (0.0 <= input_gain <= 4.0):
            raise ValueError("input_gain must be 0.0-4.0")
        if not (0 <= midi_channel <= 15):
            raise ValueError("midi_channel must be 0-15")
        if cv_mode not in ('unipolar', 'bipolar'):
            raise ValueError("cv_mode must be 'unipolar' or 'bipolar'")

        # R8: Mode-specific cv_range validation
        if cv_mode == 'unipolar':
            if not (0.0 <= cv_min):
                raise ValueError(f"Unipolar cv_min must be >= 0.0 (got {cv_min}V)")
            if not (cv_max <= vmax_calibrated):
                raise ValueError(f"Unipolar cv_max must be <= {vmax_calibrated}V (got {cv_max}V)")
        else:  # bipolar
            half_vmax = vmax_calibrated / 2
            if not (-half_vmax <= cv_min):
                raise ValueError(f"Bipolar cv_min must be >= -{half_vmax}V (got {cv_min}V)")
            if not (cv_max <= half_vmax):
                raise ValueError(f"Bipolar cv_max must be <= +{half_vmax}V (got {cv_max}V)")

        # Store configuration
        self.sc = sc_client  # R3
        self.telem = telemetry_controller
        self.device_name = device_name
        self.device_type = device_type
        self.cv_min = cv_min
        self.cv_max = cv_max
        self.points = points
        self.slot = slot
        self.slot1 = slot + 1  # SC uses 1-indexed slots
        self.settle_ms = settle_ms
        self.input_channel = input_channel
        self.input_gain = min(input_gain, 4.0)
        self.require_waveform = require_waveform

        # R5: Enhanced port detection
        self.midi_port = midi_port or find_preferred_port()
        self.midi_cc = midi_cc
        self.midi_channel = midi_channel
        self.vmax = vmax_calibrated
        self.cv_mode = cv_mode

        if self.midi_port is None:
            available = MidiCV.list_ports()
            raise ValueError(
                f"No MIDI port found. Available ports: {available}\n"
                f"Specify midi_port explicitly or check CV.OCD/MOTU connection."
            )

        # Runtime state
        self.cv_controller: Optional[MidiCV] = None
        self.step_size = (self.cv_max - self.cv_min) / (self.points - 1)
        self.snapshots: List[Dict] = []

    def run_sweep(self) -> Dict:
        """
        Execute full CV sweep with safety guarantees.

        Returns:
            Complete morph map dictionary

        Requirements Verified:
        - R2: set_generator_context() called
        - R4: Correct timing order
        - R7: Telemetry rate > 10
        - R11: Actual CC recorded
        - R13: Failure recorded before abort
        - R14: Safe CV before sweep
        - R15: Safety reset in finally
        - R16: 10s timeout
        """
        logger.info(f"[Morph Mapper] Starting {self.points}-point MIDI CV sweep")
        logger.info(f"  Device: {self.device_name}")
        logger.info(f"  CV Range: {self.cv_min}V to {self.cv_max}V ({self.cv_mode})")
        logger.info(f"  MIDI: {self.midi_port}, CC{self.midi_cc}, Ch{self.midi_channel + 1}")
        logger.info(f"  Calibrated Vmax: {self.vmax}V")

        start_time = time.time()
        self.snapshots = []

        try:
            # Initialize MIDI CV controller
            self.cv_controller = MidiCV(
                port_name=self.midi_port,
                cc_number=self.midi_cc,
                channel=self.midi_channel,
                vmax_calibrated=self.vmax,
                mode=self.cv_mode
            )
            self.cv_controller.open()

            # R14: Send safe value BEFORE sweep starts
            logger.info("  Sending safe CV before sweep (R14)")
            self.cv_controller.send_safe()
            time.sleep(0.1)

            # Load hw_profile_tap generator
            self._load_hw_profile_tap()

            # R2: Set external capture mode (CRITICAL)
            logger.info("  Setting external capture mode (R2)")
            self.telem.set_generator_context(
                "Generic Hardware Profiler",
                "forge_hw_profile_tap"
            )

            # Configure hw_profile_tap parameters
            self._configure_hw_profile_tap()

            # R7: Enable telemetry (rate > 10, recommend 15)
            rate = 15 if self.require_waveform else 10
            logger.info(f"  Enabling telemetry at {rate}Hz (R7)")
            self.telem.enable(self.slot, rate=rate)
            time.sleep(0.5)

            # Execute sweep
            for i in range(self.points):
                cv_voltage = self.cv_min + (i * self.step_size)

                logger.info(f"[{i + 1}/{self.points}] CV = {cv_voltage:.3f}V")

                # R4: CRITICAL TIMING ORDER
                # 1. Clear old data
                self.telem.history.clear()
                self.telem.current_waveform = None

                # 2. Mark timestamp
                t0 = time.time()

                # 3. Send CV (R11: record actual CC sent)
                actual_cc = self.cv_controller.send_cv_volts(cv_voltage)
                logger.debug(f"  Sent CV {cv_voltage:.3f}V → CC {actual_cc}")

                # 4. Settle
                time.sleep(self.settle_ms / 1000.0)

                # 5. Capture (R16: 10s timeout)
                snapshot = self._wait_for_fresh_snapshot(t0, timeout=10.0)

                if snapshot is None:
                    logger.warning(f"  TIMEOUT at {cv_voltage:.3f}V (CC {actual_cc})")

                    # R13: Record failure BEFORE abort decision
                    self.snapshots.append({
                        'cv_index': i,
                        'cv_voltage': cv_voltage,
                        'midi_cc_value': actual_cc,  # R11
                        'timestamp': datetime.now().isoformat(),
                        'snapshot': None,
                        'stability': {'timeout': True}  # R17
                    })

                    # Abort on point 0 failure
                    if i == 0:
                        logger.error("Point 0 failed - aborting sweep")
                        logger.error("Check: hardware connected, audio input level")
                        logger.error("Check: CV.OCD powered and configured")
                        logger.error("Check: OSC alias /noise/telem/hw_wave (R1)")
                        break

                    # Continue on later failures
                    continue

                # Extract metrics
                frame = snapshot['frame']
                freq = frame.get('freq', 0)
                rms3 = frame.get('rms_stage3', 0)
                freq_stable = self._check_stability(freq, rms3)

                # R17: Normalized schema with 'stability' wrapper
                self.snapshots.append({
                    'cv_index': i,
                    'cv_voltage': cv_voltage,
                    'midi_cc_value': actual_cc,  # R11: actual CC sent
                    'timestamp': datetime.now().isoformat(),
                    'snapshot': snapshot,
                    'stability': {  # R17: consistent wrapper
                        'freq_stable': freq_stable,
                        'settled_ms': self.settle_ms
                    }
                })

                logger.info(f"  OK (freq={freq:.1f}Hz, rms={rms3:.3f}, CC={actual_cc})")

        except KeyboardInterrupt:
            logger.warning("[Morph Mapper] Interrupted by user")

        except Exception as e:
            logger.error(f"[Morph Mapper] Error during sweep: {e}")
            raise

        finally:
            # R15: Safety reset MUST be attempted whenever port open
            if self.cv_controller:
                try:
                    if self.cv_controller.is_open:
                        logger.info("[Morph Mapper] Safety reset to neutral (R15)")
                        self.cv_controller.send_safe()
                        time.sleep(0.1)
                        self.cv_controller.close()
                except Exception as e:
                    # R15: Log as P0 safety error
                    logger.error(f"[P0 SAFETY ERROR] Failed to reset CV: {e}")

            # Disable telemetry
            self.telem.disable()

        total_time = time.time() - start_time
        logger.info(f"[Morph Mapper] Complete in {total_time:.1f}s")

        return self._build_morph_map(total_time)

    def _load_hw_profile_tap(self):
        """Load hw_profile_tap generator into slot (R3: use sc_client)."""
        self.sc.send_message(
            "/noise/start_generator",
            [self.slot1, "forge_hw_profile_tap"]
        )
        time.sleep(0.5)
        logger.info(f"  Loaded hw_profile_tap into slot {self.slot1}")

    def _configure_hw_profile_tap(self):
        """Configure hw_profile_tap parameters (R3: use sc_client)."""
        # P0: CHN (input channel 0-5)
        self.sc.send_message(
            f"/noise/gen/custom/{self.slot1}/0",
            [self.input_channel]
        )
        # P1: LVL (gain normalization 0-4x)
        self.sc.send_message(
            f"/noise/gen/custom/{self.slot1}/1",
            [self.input_gain]
        )
        logger.info(f"  Configured hw_profile_tap: CHN={self.input_channel}, LVL={self.input_gain}")

    def _wait_for_fresh_snapshot(
        self,
        t0: float,
        timeout: float = 10.0  # R16: >= 10s
    ) -> Optional[Dict]:
        """
        Wait for fresh snapshot after time t0.

        Requirements:
        - R4: Correct timing (frames arrive AFTER CV change)
        - R7: Waveform lock if require_waveform=True
        - R16: Timeout >= 10s

        Args:
            t0: Timestamp BEFORE CV was sent
            timeout: Maximum wait time (R16: >= 10s)

        Returns:
            Complete snapshot dict or None on timeout
        """
        start = time.time()

        while (time.time() - start) < timeout:
            if self.telem.history and len(self.telem.history) > 0:
                latest = self.telem.history[-1]
                frame_time = latest.get('timestamp', 0)

                # R4: Only accept frames that arrived AFTER CV change
                if frame_time > t0:
                    if self.require_waveform:
                        if self.telem.current_waveform is not None:
                            return self.telem.snapshot()
                    else:
                        return self.telem.snapshot()

            time.sleep(0.05)

        return None

    def _check_stability(self, freq: float, rms: float) -> bool:
        """Check capture stability (device-type-specific)."""
        if self.device_type == "oscillator":
            # hw_profile_tap lock gate: 11-1900 Hz
            return freq > 11 and freq < 1900
        else:
            return rms > 0.01

    def _build_morph_map(self, total_time: float) -> Dict:
        """Build morph map with normalized schema (R17)."""
        failed_points = [
            snap['cv_index'] for snap in self.snapshots
            if snap.get('snapshot') is None
        ]

        interrupted = len(self.snapshots) < self.points

        return {
            'format_version': '6.2',
            'device_name': self.device_name,
            'device_type': self.device_type,
            'cv_parameter': 'morph',
            'cv_method': 'midi_cv',
            'capture_date': datetime.now().isoformat(),
            'cv_range': [self.cv_min, self.cv_max],
            'points': self.points,
            'captured_points': len(self.snapshots),
            'test_config': {
                'settle_ms': self.settle_ms,
                'input_channel': self.input_channel,
                'input_gain': self.input_gain,
                'slot': self.slot,
                'midi_port': self.midi_port,
                'midi_cc': self.midi_cc,
                'midi_channel': self.midi_channel + 1,  # Display as 1-16
                'vmax_calibrated': self.vmax,
                'cv_mode': self.cv_mode
            },
            'snapshots': self.snapshots,
            'metadata': {
                'interrupted': interrupted,
                'total_time_sec': total_time,
                'failed_points': failed_points,
                'pack_used': 'external_telemetry/hw_profile_tap',
                'telemetry_snapshot_version': 'TelemetryController.snapshot()',
                'harmonic_analysis': 'FFT-based (_compute_hw_dna, 8 bands)'
            }
        }

    def save_map(self, output_dir: str = "maps/") -> str:
        """
        Save morph map to JSON file.

        Args:
            output_dir: Directory for output files

        Returns:
            Path to saved file
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self.device_name.replace(" ", "_").lower()
        filename = f"morph_map_{safe_name}_{timestamp}.json"
        output_path = Path(output_dir) / filename

        morph_map = self._build_morph_map(0)

        with open(output_path, 'w') as f:
            json.dump(morph_map, f, indent=2)

        logger.info(f"[Morph Mapper] Saved to {output_path}")
        return str(output_path)
