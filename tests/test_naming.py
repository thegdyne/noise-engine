"""
tests/test_naming.py
Tests for imaginarium/naming.py unified naming schema

Updated for CQD_FORGE_SPEC.md convention: forge_{pack}_{gen}
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
    
    def test_invalid_empty(self):
        with pytest.raises(NamingError, match="empty"):
            validate_pack_id("")
    
    def test_invalid_too_long(self):
        with pytest.raises(NamingError, match="exceeds"):
            validate_pack_id("a" * 25)  # 25 chars, max 24
    
    def test_invalid_starts_with_number(self):
        with pytest.raises(NamingError, match="slug"):
            validate_pack_id("123pack")
    
    def test_invalid_uppercase(self):
        with pytest.raises(NamingError, match="slug"):
            validate_pack_id("MyPack")
    
    def test_invalid_hyphen(self):
        with pytest.raises(NamingError, match="slug"):
            validate_pack_id("my-pack")
    
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
        validate_generator_id("a" * 24)  # Max length
    
    def test_invalid_empty(self):
        with pytest.raises(NamingError, match="empty"):
            validate_generator_id("")
    
    def test_invalid_too_long(self):
        with pytest.raises(NamingError, match="exceeds"):
            validate_generator_id("a" * 25)


class TestMakeSynthdefName:
    """Tests for make_synthdef_name function"""
    
    def test_basic_format(self):
        result = make_synthdef_name("abyssal_depths", "pressure_wave")
        assert result == "forge_abyssal_depths_pressure_wave"
    
    def test_starts_with_forge(self):
        result = make_synthdef_name("test_pack", "gen_0")
        assert result.startswith("forge_")
    
    def test_custom_prefix(self):
        result = make_synthdef_name("my_pack", "my_gen", prefix="imaginarium")
        assert result == "imaginarium_my_pack_my_gen"
    
    def test_max_length_enforcement(self):
        # pack_id: 24 chars, generator_id: 24 chars
        # forge_ (6) + 24 + _ (1) + 24 = 55, under 56
        pack_id = "a" * 24
        gen_id = "b" * 24
        result = make_synthdef_name(pack_id, gen_id)
        assert len(result) <= MAX_SYNTHDEF_LENGTH
    
    def test_validates_inputs(self):
        with pytest.raises(NamingError):
            make_synthdef_name("INVALID", "gen")
        with pytest.raises(NamingError):
            make_synthdef_name("pack", "GEN-BAD")


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
    
    def test_forge_prefix(self):
        prefix, pack_id, gen_id = parse_synthdef_name("forge_abyssal_depths_pressure_wave")
        assert prefix == "forge"
        assert pack_id == "abyssal_depths"
        assert gen_id == "pressure_wave"
    
    def test_imaginarium_prefix(self):
        prefix, pack_id, gen_id = parse_synthdef_name("imaginarium_test_pack_simple_fm_000")
        assert prefix == "imaginarium"
        assert pack_id == "test_pack"
        assert gen_id == "simple_fm_000"
    
    def test_invalid_no_prefix(self):
        with pytest.raises(NamingError, match="Cannot parse"):
            parse_synthdef_name("abyssal_depths_pressure_wave")
    
    def test_roundtrip(self):
        original_pack = "test_pack"
        original_gen = "my_generator"
        synthdef = make_synthdef_name(original_pack, original_gen)
        prefix, pack_id, gen_id = parse_synthdef_name(synthdef)
        assert prefix == "forge"
        assert pack_id == original_pack
        assert gen_id == original_gen


class TestParseGeneratorRef:
    """Tests for parse_generator_ref function"""
    
    def test_basic_parse(self):
        pack_id, gen_id = parse_generator_ref("abyssal_depths:pressure_wave")
        assert pack_id == "abyssal_depths"
        assert gen_id == "pressure_wave"
    
    def test_invalid_no_separator(self):
        with pytest.raises(NamingError, match="missing ':'"):
            parse_generator_ref("abyssal_depths_pressure_wave")
    
    def test_roundtrip(self):
        original_pack = "test_pack"
        original_gen = "my_generator"
        ref = make_generator_ref(original_pack, original_gen)
        pack_id, gen_id = parse_generator_ref(ref)
        assert pack_id == original_pack
        assert gen_id == original_gen


class TestIntegration:
    """Integration tests for the naming system"""
    
    def test_full_workflow(self):
        """Test a complete pack naming workflow"""
        # Start with user input
        pack_name = "Abyssal Depths"
        generator_name = "pressure_wave"
        
        # Sanitize pack name
        pack_id = sanitize_to_slug(pack_name)
        assert pack_id == "abyssal_depths"
        
        # Generator ID (already valid)
        generator_id = generator_name
        
        # Generate SynthDef name
        synthdef = make_synthdef_name(pack_id, generator_id)
        assert synthdef == "forge_abyssal_depths_pressure_wave"
        
        # Generate generator reference
        ref = make_generator_ref(pack_id, generator_id)
        assert ref == "abyssal_depths:pressure_wave"
        
        # Parse back
        prefix, parsed_pack, parsed_gen = parse_synthdef_name(synthdef)
        assert prefix == "forge"
        assert parsed_pack == pack_id
        assert parsed_gen == generator_id
    
    def test_length_budget(self):
        """Verify length constraints work together"""
        # Maximum valid lengths
        pack_id = "a" * MAX_PACK_ID_LENGTH  # 24
        gen_id = "b" * MAX_GENERATOR_ID_LENGTH  # 24
        
        synthdef = make_synthdef_name(pack_id, gen_id)
        # forge_ (6) + 24 + _ (1) + 24 = 55
        assert len(synthdef) == 55
        assert len(synthdef) <= MAX_SYNTHDEF_LENGTH
