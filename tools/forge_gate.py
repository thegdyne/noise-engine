#!/usr/bin/env python3
"""
Forge Gate - Pre-commit validation for CQD_Forge packs

Catches issues BEFORE code is committed:
1. ASCII enforcement (no UTF-8 corruption)
2. SC syntax patterns that fail in NRT
3. Contract compliance (forge_validate.py)
4. Audio validation (forge_audio_validate.py --render)

Usage:
    python tools/forge_gate.py packs/my_pack/           # Full validation
    python tools/forge_gate.py packs/my_pack/ --quick   # Skip audio render
    python tools/forge_gate.py packs/                   # All packs
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, NamedTuple


class Issue(NamedTuple):
    file: str
    line: int
    severity: str  # ERROR, WARN
    code: str
    message: str


# SC syntax patterns that fail in NRT but work live
SC_SYNTAX_PATTERNS = [
    # Unary minus before parenthesis: -(expr)
    (r'-\([^)]+\)\.', 'SC001', 'ERROR', 'Unary minus before paren - use (..).neg or negative literal'),
    # Unary minus before variable: -varName
    (r'-[a-z][a-zA-Z0-9_]*[^a-zA-Z0-9_\.]', 'SC002', 'WARN', 'Unary minus before variable - use varName.neg'),
    # Boolean used in arithmetic (compile-time issue in NRT)
    (r'\*\s*\([^)]+\s*[<>=!]+\s*[^)]+\)(?!\.asInteger)', 'SC003', 'WARN', 'Boolean in arithmetic - add .asInteger for NRT compatibility'),
]

# Characters that shouldn't be in .scd files
NON_ASCII_PATTERN = re.compile(r'[^\x00-\x7F]')


def check_ascii(file_path: Path) -> List[Issue]:
    """Check for non-ASCII characters in file."""
    issues = []
    try:
        content = file_path.read_text(encoding='utf-8')
        for line_num, line in enumerate(content.split('\n'), 1):
            for match in NON_ASCII_PATTERN.finditer(line):
                char = match.group()
                col = match.start() + 1
                issues.append(Issue(
                    file=str(file_path),
                    line=line_num,
                    severity='ERROR',
                    code='UTF8',
                    message=f"Non-ASCII char U+{ord(char):04X} at col {col}: {repr(char)}"
                ))
    except UnicodeDecodeError as e:
        issues.append(Issue(
            file=str(file_path),
            line=0,
            severity='ERROR',
            code='UTF8',
            message=f"Invalid UTF-8 encoding: {e}"
        ))
    return issues


def check_sc_syntax(file_path: Path) -> List[Issue]:
    """Check for SC syntax patterns that fail in NRT."""
    issues = []
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.split('//')[0]

            for pattern, code, severity, message in SC_SYNTAX_PATTERNS:
                if re.search(pattern, stripped):
                    issues.append(Issue(
                        file=str(file_path),
                        line=line_num,
                        severity=severity,
                        code=code,
                        message=message
                    ))
    except Exception as e:
        issues.append(Issue(
            file=str(file_path),
            line=0,
            severity='ERROR',
            code='READ',
            message=f"Failed to read file: {e}"
        ))
    return issues


def check_contract(pack_path: Path) -> Tuple[bool, str]:
    """Run forge_validate.py on pack. Skip for legacy packs."""
    # Detect legacy pack: SynthDefs don't use forge_ prefix
    scd_files = list(pack_path.glob("generators/*.scd"))
    if scd_files:
        sample = scd_files[0].read_text()
        if "SynthDef(\\forge_" not in sample:
            return True, "Legacy pack - skipped"
    try:
        result = subprocess.run(
            ['python', 'tools/forge_validate.py', str(pack_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        passed = 'ALL CHECKS PASSED' in result.stdout
        return passed, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Contract validation timed out"
    except Exception as e:
        return False, f"Contract validation failed: {e}"


def check_audio(pack_path: Path) -> Tuple[bool, str]:
    """Run forge_audio_validate.py --render on pack."""
    try:
        result = subprocess.run(
            ['python', 'tools/forge_audio_validate.py', str(pack_path), '--render'],
            capture_output=True,
            text=True,
            timeout=300  # 5 min for 8 generators
        )
        # Check for failures
        output = result.stdout + result.stderr
        has_failures = any(x in output for x in ['RENDER_FAILED', 'SILENCE', 'RUNAWAY', 'CLIPPING', 'DC_OFFSET'])
        # But allow if summary says passed
        all_passed = 'passed' in output.lower() and 'issues found' not in output.lower()
        return all_passed or not has_failures, output
    except subprocess.TimeoutExpired:
        return False, "Audio validation timed out (>5min)"
    except Exception as e:
        return False, f"Audio validation failed: {e}"


def validate_pack(pack_path: Path, quick: bool = False) -> Tuple[bool, List[Issue], str]:
    """
    Full validation of a pack.
    Returns (passed, issues, summary)
    """
    issues = []
    summaries = []
    
    # Phase 1: ASCII check on all .scd and .json files
    print(f"  [1/4] Checking ASCII encoding...")
    for scd_file in pack_path.glob('generators/*.scd'):
        issues.extend(check_ascii(scd_file))
    for json_file in pack_path.glob('generators/*.json'):
        issues.extend(check_ascii(json_file))
    
    ascii_errors = [i for i in issues if i.code == 'UTF8']
    if ascii_errors:
        summaries.append(f"ASCII: {len(ascii_errors)} non-ASCII chars found")
    else:
        summaries.append("ASCII: OK")
    
    # Phase 2: SC syntax patterns
    print(f"  [2/4] Checking SC syntax patterns...")
    for scd_file in pack_path.glob('generators/*.scd'):
        issues.extend(check_sc_syntax(scd_file))
    
    syntax_errors = [i for i in issues if i.code.startswith('SC')]
    if syntax_errors:
        summaries.append(f"SC Syntax: {len(syntax_errors)} issues found")
    else:
        summaries.append("SC Syntax: OK")
    
    # Phase 3: Contract validation
    print(f"  [3/4] Checking contract compliance...")
    contract_ok, contract_output = check_contract(pack_path)
    if not contract_ok:
        issues.append(Issue(
            file=str(pack_path),
            line=0,
            severity='ERROR',
            code='CONTRACT',
            message="Contract validation failed"
        ))
        summaries.append("Contract: FAILED")
    else:
        summaries.append("Contract: OK")
    
    # Phase 4: Audio validation (optional)
    if quick:
        summaries.append("Audio: SKIPPED (--quick)")
    else:
        print(f"  [4/4] Running audio validation (NRT render)...")
        audio_ok, audio_output = check_audio(pack_path)
        if not audio_ok:
            issues.append(Issue(
                file=str(pack_path),
                line=0,
                severity='ERROR',
                code='AUDIO',
                message="Audio validation failed - check render output"
            ))
            summaries.append("Audio: FAILED")
        else:
            summaries.append("Audio: OK")
    
    passed = len([i for i in issues if i.severity == 'ERROR']) == 0
    return passed, issues, ' | '.join(summaries)


def print_issues(issues: List[Issue]):
    """Print issues in a readable format."""
    if not issues:
        return
    
    print("\n  Issues:")
    for issue in issues:
        loc = f"{Path(issue.file).name}:{issue.line}" if issue.line else Path(issue.file).name
        print(f"    [{issue.severity}] {issue.code} @ {loc}")
        print(f"           {issue.message}")


def main():
    parser = argparse.ArgumentParser(
        description='Forge Gate - Pre-commit validation for CQD_Forge packs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s packs/icarus/           # Full validation of one pack
  %(prog)s packs/icarus/ --quick   # Skip audio render (faster)
  %(prog)s packs/                  # Validate all packs
        """
    )
    parser.add_argument('path', type=Path, help='Pack directory or packs/ to validate all')
    parser.add_argument('--quick', '-q', action='store_true', 
                        help='Skip audio validation (faster)')
    parser.add_argument('--fix-ascii', action='store_true',
                        help='Auto-fix ASCII issues using cdd-utils utf8')
    
    args = parser.parse_args()
    
    if not args.path.exists():
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)
    
    # Determine packs to validate
    if args.path.name == 'packs' or (args.path / 'manifest.json').exists() is False:
        # Multiple packs
        packs = sorted([p for p in args.path.iterdir() if p.is_dir() and (p / 'manifest.json').exists()])
    else:
        packs = [args.path]
    
    if not packs:
        print("No packs found to validate")
        sys.exit(1)
    
    print(f"{'='*60}")
    print(f"FORGE GATE - Pre-commit Validation")
    print(f"{'='*60}")
    print(f"Packs to validate: {len(packs)}")
    print(f"Mode: {'quick' if args.quick else 'full (with audio render)'}")
    print()
    
    all_passed = True
    results = []
    
    for pack in packs:
        print(f"\n{pack.name}:")
        passed, issues, summary = validate_pack(pack, quick=args.quick)
        results.append((pack.name, passed, summary))
        
        if not passed:
            all_passed = False
            print_issues(issues)
            
            # Offer to fix ASCII issues
            ascii_issues = [i for i in issues if i.code == 'UTF8']
            if ascii_issues and args.fix_ascii:
                print(f"\n  Attempting ASCII fix...")
                subprocess.run(['cdd-utils', 'utf8', '--fix', str(pack)])
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {summary}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed_count = sum(1 for _, p, _ in results if p)
    failed_count = len(results) - passed_count
    
    for name, passed, summary in results:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {summary}")
    
    print(f"\n  {passed_count}/{len(results)} packs passed")
    
    if all_passed:
        print("\n✓ ALL GATES PASSED - Ready to commit")
        sys.exit(0)
    else:
        print(f"\n✗ {failed_count} pack(s) failed - Fix issues before committing")
        sys.exit(1)


if __name__ == '__main__':
    main()
