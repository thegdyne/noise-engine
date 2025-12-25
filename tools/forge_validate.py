#!/usr/bin/env python3
"""
tools/forge_validate.py
Pack validation for Noise Engine - contract compliance and static analysis

Validates packs against CQD_FORGE_SPEC.md (frozen 2025-12-23):
- pack_id:       slug, max 24 chars
- generator_id:  slug, max 24 chars  
- synthdef:      forge_{pack_id}_{generator_id}

Usage:
    python tools/forge_validate.py packs/leviathan/
    python tools/forge_validate.py packs/leviathan/ --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Set


# ============================================================================
# NAMING CONVENTION (from CQD_FORGE_SPEC.md)
# ============================================================================

# Slug pattern: lowercase, digits, underscores, starts with letter
SLUG_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')

MAX_PACK_ID_LENGTH = 24
MAX_GENERATOR_ID_LENGTH = 24
MAX_SYNTHDEF_LENGTH = 56  # forge_ + 24 + _ + 24 = 55

RESERVED_PACK_IDS = {"core", "mod", "test"}


def validate_pack_id(pack_id: str) -> List[str]:
    """Validate pack_id, return list of errors."""
    errors = []
    if not pack_id:
        errors.append("pack_id is empty")
    elif not SLUG_PATTERN.match(pack_id):
        errors.append(f"pack_id '{pack_id}' must be lowercase slug (a-z, 0-9, _)")
    elif len(pack_id) > MAX_PACK_ID_LENGTH:
        errors.append(f"pack_id '{pack_id}' exceeds {MAX_PACK_ID_LENGTH} chars")
    elif pack_id in RESERVED_PACK_IDS:
        errors.append(f"pack_id '{pack_id}' is reserved")
    return errors


def validate_generator_id(gen_id: str) -> List[str]:
    """Validate generator_id, return list of errors."""
    errors = []
    if not gen_id:
        errors.append("generator_id is empty")
    elif not SLUG_PATTERN.match(gen_id):
        errors.append(f"generator_id '{gen_id}' must be lowercase slug")
    elif len(gen_id) > MAX_GENERATOR_ID_LENGTH:
        errors.append(f"generator_id '{gen_id}' exceeds {MAX_GENERATOR_ID_LENGTH} chars")
    return errors


def make_synthdef_name(pack_id: str, generator_id: str) -> str:
    """Generate synthdef name per spec: forge_{pack}_{gen}"""
    return f"forge_{pack_id}_{generator_id}"


# ============================================================================
# GENERATOR CONTRACT
# ============================================================================

# Required bus arguments for all generators
REQUIRED_BUS_ARGS = [
    "out", "freqBus", "cutoffBus", "resBus", "attackBus", "decayBus",
    "filterTypeBus", "envEnabledBus", "envSourceBus",
    "clockRateBus", "clockTrigBus",
    "midiTrigBus", "slotIndex",
    "customBus0", "customBus1", "customBus2", "customBus3", "customBus4",
    "portamentoBus",
]

REQUIRED_HELPERS = [
    "~ensure2ch",
    "~multiFilter", 
    "~envVCA",
]

# Order matters - required post-chain order
POST_CHAIN_ORDER = [
    "~multiFilter",
    "~envVCA", 
    "~ensure2ch",
]

VALID_LABEL_PATTERN = re.compile(r'^[A-Z0-9]{3}$')


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ValidationResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, msg: str):
        self.errors.append(msg)
        self.passed = False
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)


@dataclass
class PackValidation:
    pack_path: Path
    pack_id: str = ""
    generators: List[str] = field(default_factory=list)
    results: dict = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results.values())
    
    @property
    def total_errors(self) -> int:
        return sum(len(r.errors) for r in self.results.values())
    
    @property
    def total_warnings(self) -> int:
        return sum(len(r.warnings) for r in self.results.values())


# ============================================================================
# MANIFEST VALIDATION
# ============================================================================

def validate_manifest(pack_path: Path) -> ValidationResult:
    """Validate pack manifest.json"""
    result = ValidationResult(passed=True)
    manifest_path = pack_path / "manifest.json"
    
    if not manifest_path.exists():
        result.add_error("manifest.json not found")
        return result
    
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error(f"manifest.json parse error: {e}")
        return result
    
    # Required fields
    required_fields = ["pack_id", "name", "generators"]
    for fld in required_fields:
        if fld not in manifest:
            result.add_error(f"manifest missing required field: {fld}")
    
    # Recommended fields
    recommended_fields = ["description", "author", "version"]
    for fld in recommended_fields:
        if fld not in manifest:
            result.add_warning(f"manifest missing recommended field: {fld}")
    
    # Pack ID validation
    pack_id = manifest.get("pack_id", "")
    for err in validate_pack_id(pack_id):
        result.add_error(err)
    
    # Generators array
    generators = manifest.get("generators", [])
    if not isinstance(generators, list):
        result.add_error("generators must be an array")
    elif len(generators) != 8:
        result.add_warning(f"generators array has {len(generators)} entries (expected 8)")
    
    # Check generator IDs
    seen_gen_ids: Set[str] = set()
    for gen_id in generators:
        for err in validate_generator_id(gen_id):
            result.add_error(err)
        
        if gen_id in seen_gen_ids:
            result.add_error(f"duplicate generator_id: {gen_id}")
        seen_gen_ids.add(gen_id)
    
    return result


# ============================================================================
# GENERATOR JSON VALIDATION
# ============================================================================

def validate_generator_json(json_path: Path, pack_id: str) -> ValidationResult:
    """Validate generator .json file"""
    result = ValidationResult(passed=True)
    
    if not json_path.exists():
        result.add_error(f"JSON file not found: {json_path.name}")
        return result
    
    try:
        with open(json_path) as f:
            gen = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error(f"JSON parse error: {e}")
        return result
    
    # Required fields
    required_fields = ["generator_id", "name", "synthdef", "custom_params", 
                       "output_trim_db", "midi_retrig", "pitch_target"]
    for fld in required_fields:
        if fld not in gen:
            result.add_error(f"missing required field: {fld}")
    
    # Generator ID matches filename
    gen_id = gen.get("generator_id", "")
    expected_id = json_path.stem
    if gen_id != expected_id:
        result.add_error(f"generator_id '{gen_id}' doesn't match filename '{expected_id}'")
    
    # Validate generator_id format
    for err in validate_generator_id(gen_id):
        result.add_error(err)
    
    # SynthDef name format: forge_{pack_id}_{generator_id}
    synthdef = gen.get("synthdef", "")
    if synthdef:
        expected_synthdef = make_synthdef_name(pack_id, gen_id)
        
        if not synthdef.startswith("forge_"):
            result.add_error(f"synthdef '{synthdef}' must start with 'forge_' prefix")
        elif synthdef != expected_synthdef:
            result.add_error(f"synthdef '{synthdef}' should be '{expected_synthdef}'")
        
        if len(synthdef) > MAX_SYNTHDEF_LENGTH:
            result.add_error(f"synthdef '{synthdef}' exceeds {MAX_SYNTHDEF_LENGTH} chars")
    
    # Custom params validation
    custom_params = gen.get("custom_params", [])
    if not isinstance(custom_params, list):
        result.add_error("custom_params must be an array")
    elif len(custom_params) != 5:
        result.add_error(f"custom_params has {len(custom_params)} entries (must be exactly 5)")
    else:
        result = validate_custom_params(custom_params, result)
    
    return result


def validate_custom_params(params: List[dict], result: ValidationResult) -> ValidationResult:
    """Validate the 5 custom_params entries"""
    seen_labels: Set[str] = set()
    
    for i, param in enumerate(params):
        prefix = f"custom_params[{i}]"
        
        # Required fields
        required = ["key", "label", "tooltip", "default", "min", "max", "curve", "unit"]
        for fld in required:
            if fld not in param:
                result.add_error(f"{prefix} missing field: {fld}")
        
        # Label validation
        label = param.get("label", "")
        if label == "---":
            # Placeholder slot - that's fine
            continue
        
        if not VALID_LABEL_PATTERN.match(label):
            result.add_error(f"{prefix} label '{label}' must be 3 chars, uppercase A-Z/0-9")
        
        if label in seen_labels:
            result.add_error(f"{prefix} duplicate label '{label}'")
        seen_labels.add(label)
        
        # Tooltip required for non-placeholder
        tooltip = param.get("tooltip", "")
        if not tooltip:
            result.add_error(f"{prefix} tooltip is required (non-empty)")
        
        # Range validation
        min_val = param.get("min", 0)
        max_val = param.get("max", 1)
        default = param.get("default", 0.5)
        
        if min_val != 0.0 or max_val != 1.0:
            result.add_warning(f"{prefix} range should be 0.0-1.0 (normalized)")
        
        if not (0.0 <= default <= 1.0):
            result.add_error(f"{prefix} default {default} outside 0.0-1.0 range")
        
        # Curve validation
        curve = param.get("curve", "lin")
        if curve not in ("lin", "exp"):
            result.add_error(f"{prefix} curve '{curve}' must be 'lin' or 'exp'")
    
    return result


# ============================================================================
# SYNTHDEF VALIDATION (Static Analysis)
# ============================================================================

def validate_synthdef(scd_path: Path, pack_id: str, generator_id: str) -> ValidationResult:
    """Validate generator .scd file (static analysis)"""
    result = ValidationResult(passed=True)
    
    if not scd_path.exists():
        result.add_error(f"SynthDef file not found: {scd_path.name}")
        return result
    
    try:
        content = scd_path.read_text()
    except Exception as e:
        result.add_error(f"Failed to read file: {e}")
        return result
    
    # Check for SynthDef declaration
    if "SynthDef(" not in content and "SynthDef\\" not in content:
        result.add_error("No SynthDef declaration found")
        return result
    
    # Check SynthDef name matches expected
    expected_synthdef = make_synthdef_name(pack_id, generator_id)
    if expected_synthdef not in content:
        # Try to find what name is actually used
        synthdef_match = re.search(r'SynthDef\s*\(\s*[\\\'"]?(\w+)', content)
        if synthdef_match:
            actual_name = synthdef_match.group(1)
            result.add_error(f"SynthDef name '{actual_name}' should be '{expected_synthdef}'")
        else:
            result.add_warning(f"Could not verify SynthDef name is '{expected_synthdef}'")
    
    # Check required bus arguments
    for arg in REQUIRED_BUS_ARGS:
        patterns = [
            rf'\b{arg}\b',
            rf'\|[^|]*\b{arg}\b',
        ]
        found = any(re.search(p, content) for p in patterns)
        if not found:
            result.add_error(f"missing required argument: {arg}")
    
    # Check for seed argument (optional for hand-crafted, required for Imaginarium)
    if "seed" not in content:
        result.add_warning("no 'seed' argument found (required for Imaginarium determinism)")
    
    # Check RandSeed
    if "RandSeed.ir" not in content:
        result.add_warning("RandSeed.ir not found (required for determinism)")
    
    # Check required helpers
    for helper in REQUIRED_HELPERS:
        if helper not in content:
            result.add_error(f"missing required helper: {helper}")
    
    # Check post-chain order
    helper_positions = {}
    for helper in POST_CHAIN_ORDER:
        match = re.search(re.escape(helper), content)
        if match:
            helper_positions[helper] = match.start()
    
    if len(helper_positions) == len(POST_CHAIN_ORDER):
        positions = [helper_positions[h] for h in POST_CHAIN_ORDER]
        if positions != sorted(positions):
            result.add_error("post-chain order wrong: must be ~multiFilter → ~envVCA → ~ensure2ch")
    
    # Check Out.ar
    if "Out.ar" not in content:
        result.add_error("missing Out.ar")
    
    # Check customBus reads
    custom_bus_reads = re.findall(r'In\.kr\(customBus(\d)\)', content)
    if len(custom_bus_reads) < 1:
        result.add_warning("no customBus reads found (P1-P5 won't work)")
    
    # Check portamento is read
    if "In.kr(portamentoBus)" not in content:
        result.add_warning("portamentoBus not read with In.kr (portamento won't work)")
    
    # Check for Lag.kr on freq
    if "Lag.kr" not in content:
        result.add_warning("no Lag.kr found (portamento may not be implemented)")
    
    return result


# ============================================================================
# PACK VALIDATION
# ============================================================================

def validate_pack(pack_path: Path, verbose: bool = False) -> PackValidation:
    """Validate an entire pack"""
    validation = PackValidation(pack_path=pack_path)
    
    # Validate manifest
    validation.results["manifest"] = validate_manifest(pack_path)
    
    # Get pack_id and generators from manifest
    manifest_path = pack_path / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            validation.pack_id = manifest.get("pack_id", "")
            validation.generators = manifest.get("generators", [])
        except:
            pass
    
    # Validate each generator
    generators_dir = pack_path / "generators"
    if not generators_dir.exists():
        validation.results["structure"] = ValidationResult(passed=False)
        validation.results["structure"].add_error("generators/ directory not found")
    else:
        for gen_id in validation.generators:
            json_path = generators_dir / f"{gen_id}.json"
            scd_path = generators_dir / f"{gen_id}.scd"
            
            # JSON validation
            json_result = validate_generator_json(json_path, validation.pack_id)
            validation.results[f"{gen_id}.json"] = json_result
            
            # SynthDef validation
            scd_result = validate_synthdef(scd_path, validation.pack_id, gen_id)
            validation.results[f"{gen_id}.scd"] = scd_result
    
    return validation


# ============================================================================
# REPORTING
# ============================================================================

def print_validation_report(validation: PackValidation, verbose: bool = False):
    """Print formatted validation report"""
    print(f"\n{'='*60}")
    print(f"Pack: {validation.pack_id or validation.pack_path.name}")
    print(f"Path: {validation.pack_path}")
    print(f"Convention: forge_{{pack}}_{{gen}} (CQD_FORGE_SPEC.md)")
    print(f"{'='*60}\n")
    
    for name, result in validation.results.items():
        if result.passed:
            status = "✓ PASS"
            color = "\033[92m"
        else:
            status = "✗ FAIL"
            color = "\033[91m"
        reset = "\033[0m"
        
        print(f"{color}{status}{reset}  {name}")
        
        if verbose or not result.passed:
            for error in result.errors:
                print(f"       \033[91m✗ {error}\033[0m")
        
        if verbose:
            for warning in result.warnings:
                print(f"       \033[93m⚠ {warning}\033[0m")
    
    print(f"\n{'-'*60}")
    
    if validation.passed:
        print(f"\033[92m✓ ALL CHECKS PASSED\033[0m")
    else:
        print(f"\033[91m✗ VALIDATION FAILED\033[0m")
        print(f"  Errors: {validation.total_errors}")
    
    if validation.total_warnings > 0:
        print(f"  Warnings: {validation.total_warnings}")
    
    print()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Validate Noise Engine packs (CQD_FORGE_SPEC convention)"
    )
    parser.add_argument(
        "pack_path",
        type=Path,
        help="Path to pack directory"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show all checks including passed ones and warnings"
    )
    
    args = parser.parse_args()
    
    if not args.pack_path.exists():
        print(f"Error: Pack path does not exist: {args.pack_path}")
        sys.exit(1)
    
    if not args.pack_path.is_dir():
        print(f"Error: Pack path is not a directory: {args.pack_path}")
        sys.exit(1)
    
    validation = validate_pack(args.pack_path, args.verbose)
    print_validation_report(validation, args.verbose)
    
    sys.exit(0 if validation.passed else 1)


if __name__ == "__main__":
    main()
