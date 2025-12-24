"""
tests/test_naming.py
Tests for imaginarium/naming.py unified naming schema
"""

import pytest
from imaginarium.naming import (
    sanitize_to_slug,
    validate_pack_id,
    validate_generator_id,
    make_synthdef_name,
    make_generator_ref,
    parse_synthdef_name,
    parse_generator_ref,
    make_generator_id_from_method,
    is_valid_pack_id,
    is_valid_generator_id,
    NamingError,
    RESERVED_PACK_IDS,
    MAX_PACK_ID_LENGTH,
    MAX_GENERATOR_ID_LENGTH,
    MAX_SYNTHDEF_LENGTH,
)


class TestSanitizeToSlug:
    """Tests for sanitize_to_slug function"""
    
    def test_basic_conversion(self):
        assert sanitize_to_slug("Hello World") == "hello_world"
        assert sanitize_to_slug("My Pack 123") == "my_pack_123"
    
    def test_special_characters(self):
        assert sanitize_to_slug("Pack!@#$%Name") == "pack_name"
        assert sanitize_to_slug("test--name") == "test_name"
    
    def test_collapse_underscores(self):
        assert sanitize_to_slug("a___b") == "a_b"
        assert sanitize_to_slug("test____pack") == "test_pack"
    
    def test_strip_leading_trailing(self):
        assert sanitize_to_slug("___test___") == "test"
        assert sanitize_to_slug("  spaces  ") == "spaces"
    
    def test_ensure_starts_with_letter(self):
        assert sanitize_to_slug("123abc") == "x123abc"
        assert sanitize_to_slug("_test") == "test"  # Stripped, starts with t
    
    def test_truncation(self):
        long_name = "a" * 50
        result = sanitize_to_slug(long_name, max_length=24)
        assert len(result) == 24
    
    def test_minimum_length(self):
        assert sanitize_to_slug("ab") == "abx"  # Padded to 3
        assert sanitize_to_slug("a") == "axx"   # Padded to 3
    
    def test_empty_input(self):
        assert sanitize_to_slug("") == "unnamed"
        assert sanitize_to_slug("!!!") == "unnamed"


class TestValidatePackId:
    """Tests for validate_pack_id function"""
    
    def test_valid_pack_ids(self):
        # Should not raise
        validate_pack_id("abc")
        validate_pack_id("my_pack")
        validate_pack_id("pack123")
        validate_pack_id("abyssal_depths")
        validate_pack_id("a" * 24)  # Max length
    
    def test_invalid_too_short(self):
        with pytest.raises(NamingError, match="must match"):
            validate_pack_id("ab")  # 2 chars, need 3
    
    def test_invalid_too_long(self):
        with pytest.raises(NamingError, match="must match"):
            validate_pack_id("a" * 25)  # 25 chars, max 24
    
    def test_invalid_starts_with_number(self):
        with pytest.raises(NamingError, match="must match"):
            validate_pack_id("123pack")
    
    def test_invalid_uppercase(self):
        with pytest.raises(NamingError, match="must match"):
            validate_pack_id("MyPack")
    
    def test_invalid_double_underscore(self):
        with pytest.raises(NamingError, match="__"):
            validate_pack_id("my__pack")
    
    def test_reserved_ids(self):
        for reserved in RESERVED_PACK_IDS:
            with pytest.raises(NamingError, match="reserved"):
                validate_pack_id(reserved)


class TestValidateGeneratorId:
    """Tests for validate_generator_id function"""
    
    def test_valid_generator_ids(self):
        validate_generator_id("a")  # 1 char OK
        validate_generator_id("bright_saw_0")
        validate_generator_id("pressure_wave")
        validate_generator_id("a" * 32)  # Max length
    
    def test_invalid_too_long(self):
        with pytest.raises(NamingError, match="must match"):
            validate_generator_id("a" * 33)
    
    def test_invalid_double_underscore(self):
        with pytest.raises(NamingError, match="__"):
            validate_generator_id("bright__saw")


class TestMakeSynthdefName:
    """Tests for make_synthdef_name function"""
    
    def test_basic_format(self):
        result = make_synthdef_name("abyssal_depths", "pressure_wave")
        assert result == "ne_abyssal_depths__pressure_wave"
    
    def test_starts_with_ne(self):
        result = make_synthdef_name("test_pack", "gen_0")
        assert result.startswith("ne_")
    
    def test_double_underscore_separator(self):
        result = make_synthdef_name("my_pack", "my_gen")
        assert "__" in result
        assert result.count("__") == 1  # Only separator, not in IDs
    
    def test_max_length_enforcement(self):
        # pack_id: 24 chars, generator_id: 32 chars
        # ne_ (3) + 24 + __ (2) + 32 = 61, under 64
        pack_id = "a" * 24
        gen_id = "b" * 32
        result = make_synthdef_name(pack_id, gen_id)
        assert len(result) <= MAX_SYNTHDEF_LENGTH
    
    def test_validates_inputs(self):
        with pytest.raises(NamingError):
            make_synthdef_name("INVALID", "gen")
        with pytest.raises(NamingError):
            make_synthdef_name("pack", "GEN__BAD")


class TestMakeGeneratorRef:
    """Tests for make_generator_ref function"""
    
    def test_basic_format(self):
        result = make_generator_ref("abyssal_depths", "pressure_wave")
        assert result == "abyssal_depths:pressure_wave"
    
    def test_colon_separator(self):
        result = make_generator_ref("pack", "gen")
        assert ":" in result
        assert result.count(":") == 1


class TestParseSynthdefName:
    """Tests for parse_synthdef_name function"""
    
    def test_basic_parse(self):
        pack_id, gen_id = parse_synthdef_name("ne_abyssal_depths__pressure_wave")
        assert pack_id == "abyssal_depths"
        assert gen_id == "pressure_wave"
    
    def test_invalid_no_prefix(self):
        with pytest.raises(NamingError, match="must start with 'ne_'"):
            parse_synthdef_name("abyssal_depths__pressure_wave")
    
    def test_invalid_no_separator(self):
        with pytest.raises(NamingError, match="missing '__' separator"):
            parse_synthdef_name("ne_abyssal_depths_pressure_wave")
    
    def test_roundtrip(self):
        original_pack = "test_pack"
        original_gen = "my_generator_0"
        synthdef = make_synthdef_name(original_pack, original_gen)
        pack_id, gen_id = parse_synthdef_name(synthdef)
        assert pack_id == original_pack
        assert gen_id == original_gen


class TestParseGeneratorRef:
    """Tests for parse_generator_ref function"""
    
    def test_basic_parse(self):
        pack_id, gen_id = parse_generator_ref("abyssal_depths:pressure_wave")
        assert pack_id == "abyssal_depths"
        assert gen_id == "pressure_wave"
    
    def test_invalid_no_separator(self):
        with pytest.raises(NamingError, match="missing ':' separator"):
            parse_generator_ref("abyssal_depths_pressure_wave")
    
    def test_roundtrip(self):
        original_pack = "test_pack"
        original_gen = "my_generator_0"
        ref = make_generator_ref(original_pack, original_gen)
        pack_id, gen_id = parse_generator_ref(ref)
        assert pack_id == original_pack
        assert gen_id == original_gen


class TestMakeGeneratorIdFromMethod:
    """Tests for make_generator_id_from_method function"""
    
    def test_basic_conversion(self):
        result = make_generator_id_from_method("subtractive/bright_saw", 0)
        assert result == "bright_saw_0"
    
    def test_extracts_method_name(self):
        result = make_generator_id_from_method("fm/simple_fm", 3)
        assert result == "simple_fm_3"
    
    def test_handles_plain_method(self):
        result = make_generator_id_from_method("karplus", 7)
        assert result == "karplus_7"
    
    def test_sanitizes_invalid_chars(self):
        result = make_generator_id_from_method("some/weird-method!", 1)
        assert result == "weird_method_1"


class TestValidityHelpers:
    """Tests for is_valid_* helper functions"""
    
    def test_is_valid_pack_id(self):
        assert is_valid_pack_id("valid_pack") is True
        assert is_valid_pack_id("ab") is False
        assert is_valid_pack_id("core") is False
    
    def test_is_valid_generator_id(self):
        assert is_valid_generator_id("valid_gen") is True
        assert is_valid_generator_id("a__b") is False


class TestIntegration:
    """Integration tests for the naming system"""
    
    def test_full_workflow(self):
        """Test a complete pack naming workflow"""
        # Start with user input
        pack_name = "Abyssal Depths"
        method_id = "physical/karplus"
        slot_index = 0
        
        # Sanitize pack name
        pack_id = sanitize_to_slug(pack_name)
        assert pack_id == "abyssal_depths"
        
        # Generate generator ID
        generator_id = make_generator_id_from_method(method_id, slot_index)
        assert generator_id == "karplus_0"
        
        # Generate SynthDef name
        synthdef = make_synthdef_name(pack_id, generator_id)
        assert synthdef == "ne_abyssal_depths__karplus_0"
        
        # Generate generator reference
        ref = make_generator_ref(pack_id, generator_id)
        assert ref == "abyssal_depths:karplus_0"
        
        # Parse back
        parsed_pack, parsed_gen = parse_synthdef_name(synthdef)
        assert parsed_pack == pack_id
        assert parsed_gen == generator_id
    
    def test_length_budget(self):
        """Verify length constraints work together"""
        # Maximum valid lengths
        pack_id = "a" * MAX_PACK_ID_LENGTH  # 24
        gen_id = "b" * MAX_GENERATOR_ID_LENGTH  # 32
        
        synthdef = make_synthdef_name(pack_id, gen_id)
        # ne_ (3) + 24 + __ (2) + 32 = 61
        assert len(synthdef) == 61
        assert len(synthdef) <= MAX_SYNTHDEF_LENGTH
