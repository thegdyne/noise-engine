#!/usr/bin/env python3
"""
tools/check_diversity.py
Check synthesis method diversity across pack generators.

Usage:
    python3 tools/check_diversity.py <pack_id> --check-declared
    python3 tools/check_diversity.py <pack_id> --check-diversity
    python3 tools/check_diversity.py <pack_id> --check-dominance

Exit codes:
    0 = check passed
    1 = check failed
"""

import argparse
import json
import sys
from pathlib import Path


def find_pack_dir(pack_id: str) -> Path:
    """Find pack directory, searching common locations."""
    home = Path.home()
    candidates = [
        Path(f"packs/{pack_id}"),
        Path(f"../packs/{pack_id}"),
        Path(f"../../packs/{pack_id}"),
        Path.cwd() / "packs" / pack_id,
        home / "Downloads" / pack_id,
        home / "Downloads" / "packs" / pack_id,
    ]
    
    for p in candidates:
        if p.exists() and p.is_dir():
            return p.resolve()
    
    # Also check if pack_id is already a path
    direct = Path(pack_id)
    if direct.exists() and direct.is_dir():
        return direct.resolve()
    
    return None


def load_generators(pack_dir: Path) -> list[dict]:
    """Load all generator JSON files from pack."""
    generators = []
    gen_dir = pack_dir / "generators"
    
    if not gen_dir.exists():
        return generators
    
    for json_file in sorted(gen_dir.glob("*.json")):
        try:
            with open(json_file) as f:
                data = json.load(f)
                data["_filename"] = json_file.name
                generators.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {json_file}: {e}", file=sys.stderr)
    
    return generators


def get_family(method: str) -> str:
    """Extract family prefix from synthesis_method."""
    if not method:
        return "unknown"
    # Family is the part before / or : (supports both formats)
    if "/" in method:
        return method.split("/")[0].lower()
    elif ":" in method:
        return method.split(":")[0].lower()
    return method.lower()


def check_declared(generators: list[dict]) -> tuple[bool, dict]:
    """Check that all generators declare synthesis_method."""
    invalid = []
    
    for gen in generators:
        method = gen.get("synthesis_method")
        if not method or not isinstance(method, str) or method.strip() == "":
            invalid.append({
                "generator": gen.get("generator_id", gen.get("_filename", "unknown")),
                "issue": "missing or empty synthesis_method"
            })
    
    passed = len(invalid) == 0
    result = {
        "all_declared": passed,
        "valid_count": len(generators) - len(invalid),
        "total_count": len(generators),
        "invalid": invalid
    }
    
    return passed, result


def check_diversity(generators: list[dict]) -> tuple[bool, dict]:
    """Check that pack uses at least 3 distinct families."""
    families = {}
    
    for gen in generators:
        method = gen.get("synthesis_method", "")
        family = get_family(method)
        if family not in families:
            families[family] = []
        families[family].append(gen.get("generator_id", "unknown"))
    
    distinct = len(families)
    passed = distinct >= 3
    
    result = {
        "distinct_families": distinct,
        "families": families,
        "passed": passed
    }
    
    return passed, result


def check_dominance(generators: list[dict]) -> tuple[bool, dict]:
    """Check that no family has more than 4 generators."""
    families = {}
    
    for gen in generators:
        method = gen.get("synthesis_method", "")
        family = get_family(method)
        families[family] = families.get(family, 0) + 1
    
    max_count = max(families.values()) if families else 0
    max_family = [f for f, c in families.items() if c == max_count]
    passed = max_count <= 4
    
    result = {
        "max_family_count": max_count,
        "max_family": max_family[0] if max_family else None,
        "family_counts": families,
        "passed": passed
    }
    
    return passed, result


def main():
    parser = argparse.ArgumentParser(description="Check pack synthesis diversity")
    parser.add_argument("pack_id", help="Pack ID or path")
    parser.add_argument("--check-declared", action="store_true", help="Check all generators declare method")
    parser.add_argument("--check-diversity", action="store_true", help="Check minimum family diversity")
    parser.add_argument("--check-dominance", action="store_true", help="Check no family dominates")
    
    args = parser.parse_args()
    
    # Find pack
    pack_dir = find_pack_dir(args.pack_id)
    if not pack_dir:
        print(json.dumps({"error": f"Pack not found: {args.pack_id}"}))
        sys.exit(1)
    
    # Load generators
    generators = load_generators(pack_dir)
    if not generators:
        print(json.dumps({"error": f"No generators found in {pack_dir}"}))
        sys.exit(1)
    
    # Run requested check
    if args.check_declared:
        passed, result = check_declared(generators)
    elif args.check_diversity:
        passed, result = check_diversity(generators)
    elif args.check_dominance:
        passed, result = check_dominance(generators)
    else:
        # Default: run all checks
        d1, r1 = check_declared(generators)
        d2, r2 = check_diversity(generators)
        d3, r3 = check_dominance(generators)
        passed = d1 and d2 and d3
        result = {
            "declared": r1,
            "diversity": r2,
            "dominance": r3,
            "all_passed": passed
        }
    
    # Output result and exit with appropriate code
    print(json.dumps(result, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
