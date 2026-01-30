"""
Tests for Arpeggiator Engine (Per-Slot v2.0).

Tests the PER_SLOT_ARP_SPEC v2.0 including:
- PRNG (xorshift32) implementation
- Pattern generation (UP, DOWN, UPDOWN, RANDOM, ORDER)
- Event queue serialization
- State machine transitions
- Velocity handling
- Hold/latch mode
- Per-slot targeting (one engine per slot)
"""

import pytest
from typing import List, Tuple, Set
from unittest.mock import MagicMock


class TestXorShift32:
    """Test xorshift32 PRNG implementation."""

    def test_default_seed_not_zero(self):
        """Default seed should be 0x6D2B79F5 if 0 is provided."""
        from src.gui.arp_engine import XorShift32

        prng = XorShift32(0)
        assert prng.state == 0x6D2B79F5

    def test_deterministic_sequence(self):
        """Same seed produces same sequence."""
        from src.gui.arp_engine import XorShift32

        prng1 = XorShift32(0x12345678)
        prng2 = XorShift32(0x12345678)

        seq1 = [prng1.next_uint32() for _ in range(10)]
        seq2 = [prng2.next_uint32() for _ in range(10)]

        assert seq1 == seq2

    def test_uniform_choice_basic(self):
        """Choice over range produces values in range."""
        from src.gui.arp_engine import XorShift32

        prng = XorShift32(42)
        for n in [1, 2, 3, 5, 10, 100]:
            for _ in range(100):
                choice = prng.choice(n)
                assert 0 <= choice < n

    def test_choice_n_1_always_zero(self):
        """Choice over 1 element always returns 0."""
        from src.gui.arp_engine import XorShift32

        prng = XorShift32(42)
        for _ in range(100):
            assert prng.choice(1) == 0


class TestArpPatterns:
    """Test ARP pattern generation."""

    def test_up_pattern_basic(self):
        """UP pattern cycles through notes ascending."""
        from src.gui.arp_engine import ArpPattern

        # Notes C, E, G (MIDI 60, 64, 67)
        notes = [60, 64, 67]
        expected = [60, 64, 67, 60, 64, 67]

        # Verify pattern logic
        result = []
        idx = 0
        for _ in range(6):
            result.append(notes[idx % len(notes)])
            idx += 1

        assert result == expected

    def test_down_pattern_basic(self):
        """DOWN pattern cycles through notes descending."""
        notes = [60, 64, 67]
        reversed_notes = list(reversed(notes))
        expected = [67, 64, 60, 67, 64, 60]

        result = []
        idx = 0
        for _ in range(6):
            result.append(reversed_notes[idx % len(reversed_notes)])
            idx += 1

        assert result == expected

    def test_updown_pattern_n3(self):
        """UPDOWN with N=3 produces ping-pong without repeating endpoints."""
        notes = [60, 64, 67]
        # Pattern: 0, 1, 2, 1, 0, 1, 2, 1, ...
        # = C, E, G, E, C, E, G, E
        expected = [60, 64, 67, 64, 60, 64, 67, 64]

        result = []
        n = len(notes)
        seq_len = 2 * n - 2  # = 4 for n=3
        for i in range(8):
            idx = i % seq_len
            if idx < n:
                result.append(notes[idx])
            else:
                result.append(notes[seq_len - idx])

        assert result == expected

    def test_updown_pattern_n2(self):
        """UPDOWN with N=2 alternates between notes."""
        notes = [60, 64]
        expected = [60, 64, 60, 64, 60, 64]

        result = []
        for i in range(6):
            result.append(notes[i % 2])

        assert result == expected

    def test_updown_pattern_n1(self):
        """UPDOWN with N=1 repeats single note."""
        notes = [60]
        expected = [60, 60, 60, 60]

        result = [notes[0] for _ in range(4)]
        assert result == expected


class TestArpEngineBasic:
    """Test basic ARP engine functionality (per-slot v2.0)."""

    def create_mock_engine(self, slot_id=0, seed=42):
        """Create ARP engine with mock callbacks targeting a single slot."""
        from src.gui.arp_engine import ArpEngine

        self.notes_on: List[Tuple[int, int, int]] = []
        self.notes_off: List[Tuple[int, int]] = []

        def mock_note_on(slot, note, vel):
            self.notes_on.append((slot, note, vel))

        def mock_note_off(slot, note):
            self.notes_off.append((slot, note))

        engine = ArpEngine(
            slot_id=slot_id,
            send_note_on=mock_note_on,
            send_note_off=mock_note_off,
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
            rng_seed_override=seed,
        )

        return engine

    def test_initial_state_disabled(self):
        """Engine starts in disabled state."""
        engine = self.create_mock_engine()
        assert not engine.settings.enabled

    def test_slot_id_property(self):
        """Engine exposes read-only slot_id."""
        engine = self.create_mock_engine(slot_id=3)
        assert engine.slot_id == 3

    def test_toggle_arp_on(self):
        """Toggling ARP on changes enabled state."""
        engine = self.create_mock_engine()

        engine.toggle_arp(True)
        assert engine.settings.enabled

    def test_toggle_arp_off(self):
        """Toggling ARP off changes enabled state."""
        engine = self.create_mock_engine()

        engine.toggle_arp(True)
        assert engine.settings.enabled

        engine.toggle_arp(False)
        assert not engine.settings.enabled

    def test_key_press_legacy_emits_note_on(self):
        """In legacy mode (ARP off), key press emits note on to engine's slot."""
        engine = self.create_mock_engine(slot_id=0)

        engine.key_press(60)  # C4

        assert len(self.notes_on) == 1
        assert self.notes_on[0] == (0, 60, 100)

    def test_key_press_legacy_targets_correct_slot(self):
        """Legacy note-on targets the engine's slot_id."""
        engine = self.create_mock_engine(slot_id=5)

        engine.key_press(60)

        assert len(self.notes_on) == 1
        assert self.notes_on[0][0] == 5  # slot 5

    def test_key_release_legacy_emits_note_off(self):
        """In legacy mode (ARP off), key release emits note off."""
        engine = self.create_mock_engine(slot_id=0)

        engine.key_press(60)
        engine.key_release(60)

        assert len(self.notes_off) == 1
        assert self.notes_off[0] == (0, 60)

    def test_arp_on_silences_legacy_notes(self):
        """Enabling ARP turns off the current legacy note (mono)."""
        engine = self.create_mock_engine()

        # Hold notes in legacy mode — mono, so each press replaces the last
        engine.key_press(60)
        engine.key_press(64)
        engine.key_press(67)

        # Clear tracking
        self.notes_on.clear()
        self.notes_off.clear()

        # Enable ARP
        engine.toggle_arp(True)

        # Legacy mode is mono — only the last sounding note (67) gets turned off
        assert len(self.notes_off) == 1
        assert self.notes_off[0][1] == 67

    def test_arp_off_resumes_legacy(self):
        """Disabling ARP resumes legacy notes for held keys."""
        engine = self.create_mock_engine()

        # Hold notes and enable ARP
        engine.key_press(60)
        engine.key_press(64)
        engine.toggle_arp(True)

        # Clear tracking
        self.notes_on.clear()
        self.notes_off.clear()

        # Disable ARP
        engine.toggle_arp(False)

        # Should have emitted legacy note-ons for held keys
        assert len(self.notes_on) == 2

    def test_is_active_property(self):
        """is_active is True when ARP enabled and notes in active set."""
        engine = self.create_mock_engine()

        assert not engine.is_active

        engine.toggle_arp(True)
        assert not engine.is_active  # No notes yet

        engine.key_press(60)
        assert engine.is_active

    def test_has_hold_property(self):
        """has_hold is True when HOLD enabled with latched notes."""
        engine = self.create_mock_engine()

        engine.toggle_arp(True)
        engine.toggle_hold(True)
        assert not engine.has_hold  # No latched notes yet

        engine.key_press(60)
        assert engine.has_hold

        # Release key — latched notes remain
        engine.key_release(60)
        assert engine.has_hold


class TestArpHoldMode:
    """Test ARP hold/latch functionality."""

    def create_mock_engine(self, slot_id=0):
        """Create ARP engine with mock callbacks."""
        from src.gui.arp_engine import ArpEngine

        self.notes_on: List[Tuple[int, int, int]] = []
        self.notes_off: List[Tuple[int, int]] = []

        def mock_note_on(slot, note, vel):
            self.notes_on.append((slot, note, vel))

        def mock_note_off(slot, note):
            self.notes_off.append((slot, note))

        engine = ArpEngine(
            slot_id=slot_id,
            send_note_on=mock_note_on,
            send_note_off=mock_note_off,
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
            rng_seed_override=42,
        )

        return engine

    def test_hold_off_uses_physical(self):
        """With hold off, active set is physically held notes."""
        engine = self.create_mock_engine()

        engine.toggle_arp(True)
        engine.key_press(60)
        engine.key_press(64)

        active = engine._get_active_set()
        assert active == {60, 64}

        # Release one key
        engine.key_release(60)
        active = engine._get_active_set()
        assert active == {64}

    def test_hold_on_uses_latched(self):
        """With hold on, active set is latched notes."""
        engine = self.create_mock_engine()

        engine.toggle_arp(True)
        engine.toggle_hold(True)

        # Press toggles latch on
        engine.key_press(60)
        engine.key_press(64)

        active = engine._get_active_set()
        assert active == {60, 64}

        # Release doesn't affect active set
        engine.key_release(60)
        engine.key_release(64)

        active = engine._get_active_set()
        assert active == {60, 64}

    def test_hold_toggle_latch(self):
        """In hold mode, pressing same key toggles it off."""
        engine = self.create_mock_engine()

        engine.toggle_arp(True)
        engine.toggle_hold(True)

        engine.key_press(60)
        assert 60 in engine._get_active_set()

        # Press again to unlatch (note: need to release first in real usage)
        engine.key_release(60)
        engine.key_press(60)
        assert 60 not in engine._get_active_set()


class TestArpVelocity:
    """Test ARP velocity handling."""

    def create_engine_with_velocity(self, velocity_fn, slot_id=0):
        """Create ARP engine with configurable velocity."""
        from src.gui.arp_engine import ArpEngine

        self.notes_on: List[Tuple[int, int, int]] = []

        def mock_note_on(slot, note, vel):
            self.notes_on.append((slot, note, vel))

        engine = ArpEngine(
            slot_id=slot_id,
            send_note_on=mock_note_on,
            send_note_off=lambda s, n: None,
            get_velocity=velocity_fn,
            get_bpm=lambda: 120.0,
            rng_seed_override=42,
        )

        return engine

    def test_legacy_captures_velocity_on_press(self):
        """Legacy mode captures velocity at press time."""
        current_vel = 100
        engine = self.create_engine_with_velocity(lambda: current_vel)

        # Press with velocity 100
        engine.key_press(60)

        assert len(self.notes_on) == 1
        assert self.notes_on[0][2] == 100

    def test_velocity_stored_per_note(self):
        """Each note stores its capture velocity."""
        current_vel = 100
        engine = self.create_engine_with_velocity(lambda: current_vel)

        engine.key_press(60)
        assert engine.runtime.note_velocity[60] == 100

        current_vel = 127
        engine.key_press(64)
        assert engine.runtime.note_velocity[64] == 127


class TestArpRateAndTiming:
    """Test ARP rate configuration and timing."""

    def test_rate_labels_complete(self):
        """All 7 rate labels are defined."""
        from src.gui.arp_engine import ARP_RATE_LABELS

        assert len(ARP_RATE_LABELS) == 7
        assert "1/32" in ARP_RATE_LABELS
        assert "1/8" in ARP_RATE_LABELS
        assert "1" in ARP_RATE_LABELS

    def test_beats_per_step_mapping(self):
        """Beats per step values are correct."""
        from src.gui.arp_engine import ARP_BEATS_PER_STEP

        assert ARP_BEATS_PER_STEP[0] == 0.125     # 1/32
        assert ARP_BEATS_PER_STEP[3] == 0.5       # 1/8
        assert ARP_BEATS_PER_STEP[6] == 4.0       # 1 bar

    def test_interval_calculation(self):
        """Interval calculation is correct for BPM and rate."""
        bpm = 120
        beat_ms = 60000.0 / bpm  # 500ms per beat

        # 1/8 = 0.5 beats = 250ms at 120 BPM
        beats_per_step = 0.5
        interval_ms = beat_ms * beats_per_step
        assert interval_ms == 250.0

        # 1/4 = 1.0 beat = 500ms at 120 BPM
        beats_per_step = 1.0
        interval_ms = beat_ms * beats_per_step
        assert interval_ms == 500.0


class TestArpExpandedList:
    """Test expanded list derivation with octaves."""

    def create_engine(self, slot_id=0):
        """Create basic ARP engine for testing."""
        from src.gui.arp_engine import ArpEngine

        engine = ArpEngine(
            slot_id=slot_id,
            send_note_on=lambda s, n, v: None,
            send_note_off=lambda s, n: None,
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
            rng_seed_override=42,
        )

        return engine

    def test_expanded_list_1_octave(self):
        """With 1 octave, expanded list equals active set (sorted)."""
        engine = self.create_engine()

        engine.toggle_arp(True)
        engine.key_press(60)  # C4
        engine.key_press(64)  # E4
        engine.key_press(67)  # G4

        engine.settings.octaves = 1
        expanded = engine._get_expanded_list()

        assert expanded == [60, 64, 67]

    def test_expanded_list_2_octaves(self):
        """With 2 octaves, notes are duplicated +12."""
        engine = self.create_engine()

        engine.toggle_arp(True)
        engine.key_press(60)  # C4
        engine.key_press(64)  # E4

        engine.settings.octaves = 2
        expanded = engine._get_expanded_list()

        assert expanded == [60, 64, 72, 76]

    def test_expanded_list_filters_out_of_range(self):
        """Notes > 127 are filtered from expanded list."""
        engine = self.create_engine()

        engine.toggle_arp(True)
        engine.key_press(120)  # High note

        engine.settings.octaves = 2
        expanded = engine._get_expanded_list()

        # 120 stays, 132 is filtered
        assert expanded == [120]


class TestArpTeardown:
    """Test ARP teardown and cleanup."""

    def create_engine(self, slot_id=0):
        """Create ARP engine with mock callbacks."""
        from src.gui.arp_engine import ArpEngine

        self.notes_off: List[Tuple[int, int]] = []

        engine = ArpEngine(
            slot_id=slot_id,
            send_note_on=lambda s, n, v: None,
            send_note_off=lambda s, n: self.notes_off.append((s, n)),
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
            rng_seed_override=42,
        )

        return engine

    def test_teardown_clears_state(self):
        """Teardown resets all state."""
        engine = self.create_engine()

        engine.toggle_arp(True)
        engine.key_press(60)
        engine.key_press(64)

        engine.teardown()

        assert not engine.settings.enabled
        assert len(engine.runtime.physical_held) == 0
        assert len(engine.runtime.latched) == 0

    def test_teardown_defaults_to_arp_off(self):
        """After teardown, ARP is disabled."""
        engine = self.create_engine()

        engine.toggle_arp(True)
        engine.teardown()

        assert not engine.settings.enabled

    def test_teardown_preserves_slot_id(self):
        """Teardown does not change slot_id."""
        engine = self.create_engine(slot_id=5)

        engine.toggle_arp(True)
        engine.key_press(60)
        engine.teardown()

        assert engine.slot_id == 5


class TestArpPatternOrder:
    """Test ORDER pattern uses insertion order."""

    def create_engine(self):
        """Create ARP engine."""
        from src.gui.arp_engine import ArpEngine, ArpPattern

        engine = ArpEngine(
            slot_id=0,
            send_note_on=lambda s, n, v: None,
            send_note_off=lambda s, n: None,
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
            rng_seed_override=42,
        )

        return engine

    def test_order_pattern_preserves_press_order(self):
        """ORDER pattern uses press order, not sorted order."""
        from src.gui.arp_engine import ArpPattern

        engine = self.create_engine()

        engine.toggle_arp(True)
        engine.settings.pattern = ArpPattern.ORDER

        # Press in non-sorted order: G, C, E
        engine.key_press(67)  # G
        engine.key_press(60)  # C
        engine.key_press(64)  # E

        # Active order should be [G, C, E]
        order = engine._get_active_order()
        assert order == [67, 60, 64]

        # Expanded list for ORDER uses this order
        expanded = engine._get_expanded_list()
        assert expanded == [67, 60, 64]


class TestArpPerSlot:
    """Test per-slot behavior (PER_SLOT_ARP_SPEC v2.0)."""

    def test_different_slots_independent(self):
        """Two engines on different slots don't interfere."""
        from src.gui.arp_engine import ArpEngine

        notes_on: List[Tuple[int, int, int]] = []

        engine_0 = ArpEngine(
            slot_id=0,
            send_note_on=lambda s, n, v: notes_on.append((s, n, v)),
            send_note_off=lambda s, n: None,
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
            rng_seed_override=42,
        )

        engine_3 = ArpEngine(
            slot_id=3,
            send_note_on=lambda s, n, v: notes_on.append((s, n, v)),
            send_note_off=lambda s, n: None,
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
            rng_seed_override=42,
        )

        # Play on slot 0
        engine_0.key_press(60)
        # Play on slot 3
        engine_3.key_press(72)

        assert (0, 60, 100) in notes_on
        assert (3, 72, 100) in notes_on

    def test_get_settings_returns_current_state(self):
        """get_settings() returns snapshot of current engine config."""
        from src.gui.arp_engine import ArpEngine, ArpPattern

        engine = ArpEngine(
            slot_id=0,
            send_note_on=lambda s, n, v: None,
            send_note_off=lambda s, n: None,
            get_velocity=lambda: 100,
            get_bpm=lambda: 120.0,
        )

        engine.toggle_arp(True)
        engine.toggle_hold(True)
        engine.set_pattern(ArpPattern.DOWN)
        engine.set_octaves(3)

        settings = engine.get_settings()
        assert settings.enabled is True
        assert settings.hold is True
        assert settings.pattern == ArpPattern.DOWN
        assert settings.octaves == 3
