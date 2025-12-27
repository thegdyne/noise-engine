#!/usr/bin/env python3
"""
Quick static checks for SC generator files - catches common NRT-breaking patterns.

Usage:
    python tools/forge_sc_check.py packs/pack_name/
"""

import argparse
import re
import sys
from pathlib import Path


PATTERNS = [
    # Mix.fill/Array.fill with UGen count (must be literal integer)
    (r'Mix\.fill\s*\(\s*[a-z]', "Mix.fill count must be integer literal, not variable/UGen"),
    (r'Array\.fill\s*\(\s*[a-z]', "Array.fill count must be integer literal, not variable/UGen"),
    
    # Unary minus before variable (NRT parse issue)
    (r'-[a-z][a-zA-Z]*\s*[^a-zA-Z0-9(]', "Unary minus before variable - use .neg instead"),
    
    # Reserved variable names
    (r'\bvar\s+gate\b', "Reserved variable name 'gate'"),
    (r'\bvar\s+amp\s*[,;]', "Reserved variable name 'amp' (use ampVal)"),
    
    # Boolean in arithmetic without .asInteger
    (r'\([^)]+[<>=!]+[^)]+\)\s*\*', "Boolean in arithmetic - add .asInteger"),
]


def check_file(scd_path: Path) -> list[tuple[int, str, str]]:
    """Check a single .scd file. Returns list of (line_num, pattern_desc, line_text)."""
    issues = []
    try:
        content = scd_path.read_text()
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.split('//')[0]
            
            for pattern, desc in PATTERNS:
                if re.search(pattern, stripped):
                    issues.append((line_num, desc, line.strip()[:60]))
        
    except Exception as e:
        issues.append((0, f"Read error: {e}", ""))
    
    return issues


def check_pack(pack_path: Path, verbose: bool = False) -> tuple[int, int]:
    """Check all .scd files in a pack. Returns (passed, failed)."""
    generators_dir = pack_path / "generators"
    if not generators_dir.exists():
        print(f"Error: No generators/ directory in {pack_path}")
        return 0, 1
    
    scd_files = sorted(generators_dir.glob("*.scd"))
    if not scd_files:
        print(f"Error: No .scd files in {generators_dir}")
        return 0, 1
    
    passed = 0
    failed = 0
    
    print(f"SC Check: {pack_path.name} ({len(scd_files)} files)")
    
    for scd_path in scd_files:
        issues = check_file(scd_path)
        gen_name = scd_path.stem
        
        if not issues:
            if verbose:
                print(f"  ✓ {gen_name}")
            passed += 1
        else:
            print(f"  ✗ {gen_name}")
            for line_num, desc, line_text in issues:
                print(f"    L{line_num}: {desc}")
                if line_text:
                    print(f"         {line_text}")
            failed += 1
    
    return passed, failed


def main():
    parser = argparse.ArgumentParser(description="Static SC checks for Forge packs")
    parser.add_argument("path", type=Path, help="Pack directory or .scd file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all results")
    args = parser.parse_args()
    
    if args.path.suffix == '.scd':
        issues = check_file(args.path)
        if not issues:
            print(f"✓ {args.path.name}")
            sys.exit(0)
        else:
            print(f"✗ {args.path.name}")
            for line_num, desc, line_text in issues:
                print(f"  L{line_num}: {desc}")
            sys.exit(1)
    else:
        passed, failed = check_pack(args.path, args.verbose)
        print(f"\n{'✓' if failed == 0 else '✗'} {passed} passed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
