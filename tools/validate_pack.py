#!/usr/bin/env python3
"""Pack validation tool - checks manifest and generator files."""

import json
import sys
from pathlib import Path

REQUIRED_MANIFEST_FIELDS = ["pack_format", "name", "version", "author", "description", "enabled", "generators"]
REQUIRED_GENERATOR_JSON_FIELDS = ["name", "synthdef", "custom_params"]
REQUIRED_PARAM_FIELDS = ["key", "label", "tooltip", "default", "min", "max", "curve", "unit"]


def validate_pack(pack_path: Path) -> list[str]:
    """Validate a pack directory. Returns list of errors."""
    errors = []
    
    # Skip user directory
    if pack_path.name == "user":
        return []
    
    # Check manifest exists
    manifest_path = pack_path / "manifest.json"
    if not manifest_path.exists():
        errors.append(f"Missing manifest.json")
        return errors
    
    # Parse manifest
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in manifest.json: {e}")
        return errors
    
    # Check required fields
    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"manifest.json missing required field: {field}")
    
    # Check pack_format
    if manifest.get("pack_format") != 1:
        errors.append(f"pack_format should be 1, got: {manifest.get('pack_format')}")
    
    # Check enabled is boolean
    if "enabled" in manifest and not isinstance(manifest["enabled"], bool):
        errors.append(f"enabled should be boolean, got: {type(manifest['enabled']).__name__}")
    
    # Check generators directory
    gen_dir = pack_path / "generators"
    if not gen_dir.exists():
        errors.append("Missing generators/ directory")
        return errors
    
    # Validate each generator - use lowercase for file matching
    generators = manifest.get("generators", [])
    for gen_name in generators:
        gen_errors = validate_generator(gen_dir, gen_name)
        errors.extend(gen_errors)
    
    # Check for orphan files (generators not in manifest) - case insensitive
    json_files = {f.stem.lower() for f in gen_dir.glob("*.json")}
    scd_files = {f.stem.lower() for f in gen_dir.glob("*.scd")}
    manifest_gens = {g.lower() for g in generators}
    
    orphan_json = json_files - manifest_gens
    orphan_scd = scd_files - manifest_gens
    
    for orphan in orphan_json:
        errors.append(f"Generator '{orphan}' has .json but not in manifest")
    for orphan in orphan_scd:
        errors.append(f"Generator '{orphan}' has .scd but not in manifest")
    
    return errors


def validate_generator(gen_dir: Path, gen_name: str) -> list[str]:
    """Validate a single generator's JSON and SCD files."""
    errors = []
    
    # Try exact case first, then lowercase
    json_path = gen_dir / f"{gen_name}.json"
    scd_path = gen_dir / f"{gen_name}.scd"
    
    if not json_path.exists():
        json_path = gen_dir / f"{gen_name.lower()}.json"
    if not scd_path.exists():
        scd_path = gen_dir / f"{gen_name.lower()}.scd"
    
    # Check files exist
    if not json_path.exists():
        errors.append(f"{gen_name}: Missing .json file")
    if not scd_path.exists():
        errors.append(f"{gen_name}: Missing .scd file")
    
    if not json_path.exists():
        return errors
    
    # Parse JSON
    try:
        with open(json_path) as f:
            gen_json = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"{gen_name}: Invalid JSON: {e}")
        return errors
    
    # Check required fields
    for field in REQUIRED_GENERATOR_JSON_FIELDS:
        if field not in gen_json:
            errors.append(f"{gen_name}: Missing required field: {field}")
    
    # Check custom_params
    params = gen_json.get("custom_params", [])
    if len(params) > 5:
        errors.append(f"{gen_name}: Too many custom_params ({len(params)}), max is 5")
    
    for i, param in enumerate(params):
        for field in REQUIRED_PARAM_FIELDS:
            if field not in param:
                errors.append(f"{gen_name}: custom_params[{i}] missing field: {field}")
        
        # Validate ranges
        if "min" in param and "max" in param:
            if param["min"] >= param["max"]:
                errors.append(f"{gen_name}: custom_params[{i}] min >= max")
        
        if "default" in param and "min" in param and "max" in param:
            if not (param["min"] <= param["default"] <= param["max"]):
                errors.append(f"{gen_name}: custom_params[{i}] default out of range")
        
        # Check label length
        if "label" in param and len(param["label"]) > 4:
            errors.append(f"{gen_name}: custom_params[{i}] label too long (max 4 chars)")
    
    # Check SCD has matching synthdef name
    if scd_path.exists():
        scd_content = scd_path.read_text()
        synthdef_name = gen_json.get("synthdef", "")
        if f"SynthDef(\\{synthdef_name}" not in scd_content:
            errors.append(f"{gen_name}: SCD missing SynthDef(\\{synthdef_name})")
    
    return errors


def main():
    if len(sys.argv) < 2:
        # Validate all packs
        packs_dir = Path(__file__).parent.parent / "packs"
        pack_dirs = [d for d in packs_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    else:
        pack_dirs = [Path(sys.argv[1])]
    
    total_errors = 0
    
    for pack_path in sorted(pack_dirs):
        if pack_path.name == "user":
            continue
            
        print(f"\n{'='*50}")
        print(f"Validating: {pack_path.name}")
        print('='*50)
        
        errors = validate_pack(pack_path)
        
        if errors:
            for error in errors:
                print(f"  ❌ {error}")
            total_errors += len(errors)
        else:
            print(f"  ✅ All checks passed")
    
    print(f"\n{'='*50}")
    if total_errors:
        print(f"Total errors: {total_errors}")
        sys.exit(1)
    else:
        print("All packs valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
