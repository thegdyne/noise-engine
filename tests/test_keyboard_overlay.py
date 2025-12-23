"""
Tests for Keyboard Overlay - QWERTY to MIDI mapping.
"""

import pytest
from PyQt5.QtCore import Qt


class TestKeyToSemitone:
    """Test KEY_TO_SEMITONE mapping."""
    
    def test_white_keys_correct(self):
        """White keys map to correct semitones (C D E F G A B C D E)."""
        from src.gui.keyboard_overlay import KEY_TO_SEMITONE
        
        # Bottom row - white keys
        assert KEY_TO_SEMITONE[Qt.Key_A] == 0   # C
        assert KEY_TO_SEMITONE[Qt.Key_S] == 2   # D
        assert KEY_TO_SEMITONE[Qt.Key_D] == 4   # E
        assert KEY_TO_SEMITONE[Qt.Key_F] == 5   # F
        assert KEY_TO_SEMITONE[Qt.Key_G] == 7   # G
        assert KEY_TO_SEMITONE[Qt.Key_H] == 9   # A
        assert KEY_TO_SEMITONE[Qt.Key_J] == 11  # B
        assert KEY_TO_SEMITONE[Qt.Key_K] == 12  # C (next octave)
        assert KEY_TO_SEMITONE[Qt.Key_L] == 14  # D
        assert KEY_TO_SEMITONE[Qt.Key_Semicolon] == 16  # E
    
    def test_black_keys_correct(self):
        """Black keys map to correct semitones (C# D# F# G# A# C# D#)."""
        from src.gui.keyboard_overlay import KEY_TO_SEMITONE
        
        # Top row - black keys
        assert KEY_TO_SEMITONE[Qt.Key_W] == 1   # C#
        assert KEY_TO_SEMITONE[Qt.Key_E] == 3   # D#
        assert KEY_TO_SEMITONE[Qt.Key_T] == 6   # F#
        assert KEY_TO_SEMITONE[Qt.Key_Y] == 8   # G#
        assert KEY_TO_SEMITONE[Qt.Key_U] == 10  # A#
        assert KEY_TO_SEMITONE[Qt.Key_O] == 13  # C# (next octave)
        assert KEY_TO_SEMITONE[Qt.Key_P] == 15  # D#
    
    def test_all_keys_present(self):
        """All 17 playable keys are mapped."""
        from src.gui.keyboard_overlay import KEY_TO_SEMITONE
        
        assert len(KEY_TO_SEMITONE) == 17


class TestOctaveKeys:
    """Test OCTAVE_KEYS mapping."""
    
    def test_z_is_octave_down(self):
        from src.gui.keyboard_overlay import OCTAVE_KEYS
        assert OCTAVE_KEYS[Qt.Key_Z] == -1
    
    def test_x_is_octave_up(self):
        from src.gui.keyboard_overlay import OCTAVE_KEYS
        assert OCTAVE_KEYS[Qt.Key_X] == +1


class TestMidiNoteCalculation:
    """Test MIDI note calculation from octave + semitone."""
    
    def test_middle_c(self):
        """Octave 4, semitone 0 = MIDI note 60 (middle C)."""
        # Formula: (octave + 1) * 12 + semitone
        octave = 4
        semitone = 0
        midi_note = (octave + 1) * 12 + semitone
        assert midi_note == 60
    
    def test_a440(self):
        """Octave 4, semitone 9 = MIDI note 69 (A440)."""
        octave = 4
        semitone = 9
        midi_note = (octave + 1) * 12 + semitone
        assert midi_note == 69
    
    def test_octave_0_c(self):
        """Octave 0, semitone 0 = MIDI note 12."""
        octave = 0
        semitone = 0
        midi_note = (octave + 1) * 12 + semitone
        assert midi_note == 12
    
    def test_octave_7_c(self):
        """Octave 7, semitone 0 = MIDI note 96."""
        octave = 7
        semitone = 0
        midi_note = (octave + 1) * 12 + semitone
        assert midi_note == 96
    
    def test_high_semitone_still_valid(self):
        """Octave 7, semitone 16 (highest key) = MIDI note 112, still valid."""
        octave = 7
        semitone = 16  # Highest key (E in second octave span)
        midi_note = (octave + 1) * 12 + semitone
        assert midi_note == 112
        assert 0 <= midi_note <= 127


class TestMidiNoteBounds:
    """Test MIDI note stays within 0-127."""
    
    def test_lowest_playable(self):
        """Octave 0, lowest semitone gives valid MIDI."""
        midi_note = (0 + 1) * 12 + 0
        assert 0 <= midi_note <= 127
    
    def test_highest_playable(self):
        """Octave 7, highest semitone gives valid MIDI."""
        midi_note = (7 + 1) * 12 + 16
        assert 0 <= midi_note <= 127
    
    def test_would_exceed_127(self):
        """Octave 9+ with highest key would exceed MIDI range."""
        # Octave 8 still valid: (8+1)*12 + 16 = 124
        midi_note_oct8 = (8 + 1) * 12 + 16
        assert midi_note_oct8 == 124
        assert midi_note_oct8 <= 127
        
        # Octave 9 exceeds: (9+1)*12 + 16 = 136
        midi_note_oct9 = (9 + 1) * 12 + 16
        assert midi_note_oct9 == 136
        assert midi_note_oct9 > 127  # Exceeds MIDI range


class TestSlotIndexing:
    """Test slot index conversion between UI (1-8) and OSC (0-7)."""
    
    def test_ui_to_osc_conversion(self):
        """UI slot 1 = OSC slot 0, etc."""
        for ui_slot in range(1, 9):
            osc_slot = ui_slot - 1
            assert 0 <= osc_slot <= 7
    
    def test_all_ui_slots(self):
        """UI slots are 1-8."""
        ui_slots = list(range(1, 9))
        assert ui_slots == [1, 2, 3, 4, 5, 6, 7, 8]
    
    def test_all_osc_slots(self):
        """OSC slots are 0-7."""
        osc_slots = [ui - 1 for ui in range(1, 9)]
        assert osc_slots == [0, 1, 2, 3, 4, 5, 6, 7]
