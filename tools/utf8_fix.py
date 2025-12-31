#!/usr/bin/env python3
"""
UTF-8 Corruption Detection & ASCII Normalization Tool

BROAD MODE: Catches ANY non-ASCII character in code files.
For code (Python, SuperCollider, etc.), ASCII is almost always correct.

SMART MODE: Distinguishes between:
  - Legitimate: Isolated non-ASCII (intentional symbols like • ↻ →)
  - Suspicious: Clustered non-ASCII (likely corruption like â†')

Detects:
- Invalid UTF-8 sequences (partial/corrupted bytes)
- Replacement characters (U+FFFD)
- Smart quotes, curly apostrophes
- Em/en dashes
- Non-breaking spaces
- Any other non-ASCII sneaking into code

Usage:
    python utf8_fix.py --report path/to/dir/     # Scan directory for ALL non-ASCII
    python utf8_fix.py --report path/to/file.py  # Scan single file
    python utf8_fix.py --dry-run path/to/file.py # Preview what --fix would change
    python utf8_fix.py --dry-run --smart file.py # Categorize as legitimate vs suspicious
    python utf8_fix.py --fix path/to/file.scd    # Fix ALL non-ASCII (creates backup)
    python utf8_fix.py --smart-fix file.py       # Fix SUSPICIOUS only (creates backup)
    python utf8_fix.py --report . --ext .scd .py # Directory with extension filter
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, List, Tuple, Optional, Dict
import re


# ASCII normalization map: Unicode -> ASCII equivalent
# Be aggressive - in code files, ASCII is almost always what you want
NORMALIZE_MAP = {
    # Dashes
    '\u2014': '--',    # em dash
    '\u2013': '-',     # en dash
    '\u2012': '-',     # figure dash
    '\u2015': '--',    # horizontal bar
    '\u2010': '-',     # hyphen
    '\u2011': '-',     # non-breaking hyphen
    
    # Quotes - single
    '\u2018': "'",     # left single quote
    '\u2019': "'",     # right single quote (apostrophe)
    '\u201a': "'",     # single low-9 quote
    '\u201b': "'",     # single high-reversed-9 quote
    '\u2039': "'",     # single left-pointing angle quote
    '\u203a': "'",     # single right-pointing angle quote
    '\u0060': "'",     # grave accent (backtick often misused)
    '\u00b4': "'",     # acute accent
    
    # Quotes - double
    '\u201c': '"',     # left double quote
    '\u201d': '"',     # right double quote
    '\u201e': '"',     # double low-9 quote
    '\u201f': '"',     # double high-reversed-9 quote
    '\u00ab': '"',     # left-pointing double angle quote
    '\u00bb': '"',     # right-pointing double angle quote
    
    # Spaces
    '\u00a0': ' ',     # non-breaking space
    '\u2002': ' ',     # en space
    '\u2003': ' ',     # em space
    '\u2004': ' ',     # three-per-em space
    '\u2005': ' ',     # four-per-em space
    '\u2006': ' ',     # six-per-em space
    '\u2007': ' ',     # figure space
    '\u2008': ' ',     # punctuation space
    '\u2009': ' ',     # thin space
    '\u200a': ' ',     # hair space
    '\u200b': '',      # zero-width space (DELETE)
    '\u202f': ' ',     # narrow no-break space
    '\u205f': ' ',     # medium mathematical space
    '\u3000': ' ',     # ideographic space
    '\ufeff': '',      # BOM / zero-width no-break space (DELETE)
    
    # Ellipsis
    '\u2026': '...',   # horizontal ellipsis
    
    # Bullets and symbols
    '\u2022': '*',     # bullet
    '\u2023': '>',     # triangular bullet
    '\u2043': '-',     # hyphen bullet
    '\u25aa': '*',     # black small square
    '\u25ab': '*',     # white small square
    '\u25cf': '*',     # black circle
    '\u25cb': 'o',     # white circle
    
    # Arrows (common in comments)
    '\u2192': '->',    # rightwards arrow
    '\u2190': '<-',    # leftwards arrow
    '\u2191': '^',     # upwards arrow
    '\u2193': 'v',     # downwards arrow
    '\u21d2': '=>',    # rightwards double arrow
    '\u21d0': '<=',    # leftwards double arrow
    '\u21bb': '[refresh]',  # clockwise rotation arrow
    
    # Math
    '\u00d7': 'x',     # multiplication sign
    '\u00f7': '/',     # division sign
    '\u2212': '-',     # minus sign
    '\u00b1': '+/-',   # plus-minus
    '\u2248': '~=',    # almost equal
    '\u2260': '!=',    # not equal
    '\u2264': '<=',    # less than or equal
    '\u2265': '>=',    # greater than or equal
    '\u221e': 'inf',   # infinity
    
    # Common symbols
    '\u00a9': '(c)',   # copyright
    '\u00ae': '(R)',   # registered
    '\u2122': '(TM)',  # trademark
    '\u00b0': ' deg',  # degree (or just remove?)
    '\u00a7': 'S',     # section sign
    '\u00b6': 'P',     # pilcrow (paragraph)
    '\u2020': '+',     # dagger
    '\u2021': '++',    # double dagger
    
    # Replacement character (corruption indicator)
    '\ufffd': '?',     # replacement character - DEFINITELY BAD
    
    # Check/cross marks
    '\u2713': '[x]',   # check mark
    '\u2714': '[x]',   # heavy check mark
    '\u2715': '[X]',   # multiplication x
    '\u2716': '[X]',   # heavy multiplication x
    '\u2717': '[ ]',   # ballot x
    '\u2718': '[ ]',   # heavy ballot x
    '\u274c': '[X]',   # cross mark
    '\u2705': '[x]',   # white heavy check mark
    
    # Stars
    '\u2605': '*',     # black star
    '\u2606': '*',     # white star
    '\u2729': '*',     # stress outlined white star
    
    # Fractions (expand to ASCII)
    '\u00bc': '1/4',
    '\u00bd': '1/2',
    '\u00be': '3/4',
    '\u2153': '1/3',
    '\u2154': '2/3',
}


class Issue(NamedTuple):
    """A single non-ASCII occurrence."""
    line_num: int
    col: int
    char: str
    codepoint: str
    replacement: str
    context: str


class FileReport(NamedTuple):
    """Report for a single file."""
    path: Path
    issues: List[Issue]
    has_invalid_utf8: bool
    error: Optional[str] = None


def is_printable_ascii(char: str) -> bool:
    """Check if character is printable ASCII or common whitespace."""
    code = ord(char)
    # Tab, newline, carriage return, or printable ASCII (space through tilde)
    return code == 9 or code == 10 or code == 13 or (32 <= code <= 126)


def classify_issues_smart(line: str, issues: List[Issue]) -> Tuple[List[Issue], List[Issue]]:
    """
    Classify issues on a line as legitimate (isolated) or suspicious (clustered).
    
    Legitimate: non-ASCII character surrounded by ASCII (intentional use)
    Suspicious: non-ASCII characters adjacent to each other (likely corruption)
    
    Returns (legitimate, suspicious) tuple.
    """
    if not issues:
        return [], []
    
    # Get positions of all non-ASCII chars on this line
    non_ascii_cols = {issue.col for issue in issues}
    
    legitimate = []
    suspicious = []
    
    for issue in issues:
        col = issue.col
        # Check if there's another non-ASCII within 1 position (adjacent)
        has_adjacent = (col - 1 in non_ascii_cols) or (col + 1 in non_ascii_cols)
        
        # Also check the actual characters at adjacent positions in the line
        # (handles cases where we might have missed something)
        line_idx = col - 1  # 0-indexed
        left_char = line[line_idx - 1] if line_idx > 0 else ' '
        right_char = line[line_idx + 1] if line_idx < len(line) - 1 else ' '
        
        left_is_non_ascii = not is_printable_ascii(left_char)
        right_is_non_ascii = not is_printable_ascii(right_char)
        
        if has_adjacent or left_is_non_ascii or right_is_non_ascii:
            suspicious.append(issue)
        else:
            legitimate.append(issue)
    
    return legitimate, suspicious


def scan_content(content: str) -> List[Issue]:
    """Find ALL non-ASCII characters."""
    issues = []
    
    for line_num, line in enumerate(content.split('\n'), 1):
        for col, char in enumerate(line, 1):
            if not is_printable_ascii(char):
                codepoint = f"U+{ord(char):04X}"
                replacement = NORMALIZE_MAP.get(char, '?')
                
                # Build context (surrounding characters)
                start = max(0, col - 15)
                end = min(len(line), col + 15)
                context = line[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(line):
                    context = context + "..."
                
                issues.append(Issue(
                    line_num=line_num,
                    col=col,
                    char=repr(char),
                    codepoint=codepoint,
                    replacement=replacement,
                    context=context
                ))
    
    return issues


def check_utf8_validity(filepath: Path) -> Tuple[bool, Optional[str]]:
    """Check if file contains invalid UTF-8. Returns (is_valid, error_or_content)."""
    try:
        raw_bytes = filepath.read_bytes()
    except Exception as e:
        return False, f"Read error: {e}"
    
    try:
        content = raw_bytes.decode('utf-8')
        return True, content
    except UnicodeDecodeError as e:
        return False, f"Invalid UTF-8 at byte {e.start}: {e.reason}"


def scan_file(filepath: Path) -> FileReport:
    """Scan a single file for any non-ASCII."""
    # First check UTF-8 validity
    is_valid, result = check_utf8_validity(filepath)
    
    if not is_valid and not result.startswith("Read error"):
        # Try to read with errors='replace' to find issues
        try:
            raw_bytes = filepath.read_bytes()
            content = raw_bytes.decode('utf-8', errors='replace')
            issues = scan_content(content)
            return FileReport(
                path=filepath,
                issues=issues,
                has_invalid_utf8=True,
                error=result
            )
        except Exception as e:
            return FileReport(path=filepath, issues=[], has_invalid_utf8=True, error=str(e))
    
    if not is_valid:
        return FileReport(path=filepath, issues=[], has_invalid_utf8=False, error=result)
    
    # Valid UTF-8, scan for non-ASCII
    content = result
    issues = scan_content(content)
    return FileReport(path=filepath, issues=issues, has_invalid_utf8=False)


def fix_content(content: str, only_suspicious: bool = False) -> Tuple[str, int]:
    """
    Replace non-ASCII with ASCII equivalents.
    
    If only_suspicious=True, only fix characters that are adjacent to other non-ASCII.
    """
    if not only_suspicious:
        # Original behavior: fix everything
        result = []
        fix_count = 0
        
        for char in content:
            if is_printable_ascii(char):
                result.append(char)
            else:
                replacement = NORMALIZE_MAP.get(char, '?')
                result.append(replacement)
                fix_count += 1
        
        return ''.join(result), fix_count
    
    # Smart mode: only fix suspicious (clustered) characters
    lines = content.split('\n')
    result_lines = []
    fix_count = 0
    
    for line_num, line in enumerate(lines, 1):
        # Find non-ASCII positions on this line
        non_ascii_positions = []
        for col, char in enumerate(line):
            if not is_printable_ascii(char):
                non_ascii_positions.append(col)
        
        if not non_ascii_positions:
            result_lines.append(line)
            continue
        
        # Determine which are suspicious (adjacent to other non-ASCII)
        non_ascii_set = set(non_ascii_positions)
        suspicious_cols = set()
        
        for col in non_ascii_positions:
            # Check if adjacent to another non-ASCII
            if (col - 1 in non_ascii_set) or (col + 1 in non_ascii_set):
                suspicious_cols.add(col)
        
        # Build fixed line
        result_chars = []
        for col, char in enumerate(line):
            if col in suspicious_cols:
                replacement = NORMALIZE_MAP.get(char, '?')
                result_chars.append(replacement)
                fix_count += 1
            else:
                result_chars.append(char)
        
        result_lines.append(''.join(result_chars))
    
    return '\n'.join(result_lines), fix_count


def fix_file_with_invalid_utf8(filepath: Path, only_suspicious: bool = False) -> Tuple[str, int]:
    """Handle files with invalid UTF-8 by reading as bytes and cleaning."""
    raw_bytes = filepath.read_bytes()
    
    # Decode with replacement, then normalize
    content = raw_bytes.decode('utf-8', errors='replace')
    return fix_content(content, only_suspicious=only_suspicious)


def collect_files(path: Path, extensions: Optional[List[str]] = None) -> List[Path]:
    """Collect all files to process."""
    if path.is_file():
        return [path]
    
    files = []
    default_extensions = {
        '.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml', '.yml',
        '.html', '.css', '.scss', '.xml', '.csv', '.rst', '.scd',
        '.sh', '.bash', '.zsh', '.conf', '.cfg', '.ini', '.toml',
        '.c', '.h', '.cpp', '.hpp', '.java', '.go', '.rs', '.rb',
    }
    
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            filepath = Path(root) / filename
            
            # Skip hidden files/dirs
            if any(part.startswith('.') for part in filepath.parts):
                continue
            
            # Skip backups
            if '_utf8_backups' in str(filepath):
                continue
            
            # Filter by extension
            check_extensions = set(extensions) if extensions else default_extensions
            if filepath.suffix.lower() not in check_extensions:
                continue
            
            files.append(filepath)
    
    return sorted(files)


def print_report(reports: List[FileReport], verbose: bool = True) -> Tuple[int, int, int]:
    """Print report. Returns (files_with_issues, total_issues, invalid_utf8_count)."""
    files_with_issues = 0
    total_issues = 0
    invalid_utf8_count = 0
    
    for report in reports:
        if report.error and "Read error" in report.error:
            print(f"\n  {report.path}: ERROR - {report.error}")
            continue
        
        if report.has_invalid_utf8:
            invalid_utf8_count += 1
            print(f"\n  {report.path}")
            print(f"   ⚠️  INVALID UTF-8: {report.error}")
        
        if not report.issues and not report.has_invalid_utf8:
            continue
        
        if report.issues:
            files_with_issues += 1
            total_issues += len(report.issues)
            
            if not report.has_invalid_utf8:
                print(f"\n  {report.path}")
            print(f"   Found {len(report.issues)} non-ASCII character(s)")
            
            if verbose:
                # Group by character
                by_char: Dict[str, List[Tuple[int, int]]] = {}
                for issue in report.issues:
                    key = (issue.codepoint, issue.replacement)
                    if key not in by_char:
                        by_char[key] = []
                    by_char[key].append((issue.line_num, issue.col))
                
                for (codepoint, replacement), positions in list(by_char.items())[:10]:
                    pos_str = ', '.join(f"L{l}:C{c}" for l, c in positions[:3])
                    if len(positions) > 3:
                        pos_str += f" (+{len(positions)-3} more)"
                    print(f"   - {codepoint} -> '{replacement}' at {pos_str}")
                
                if len(by_char) > 10:
                    print(f"   ... and {len(by_char) - 10} more unique characters")
    
    return files_with_issues, total_issues, invalid_utf8_count


def print_dry_run(reports: List[FileReport], smart: bool = False) -> Tuple[int, int]:
    """
    Show line-by-line preview of what --fix would change.
    
    If smart=True, categorize as legitimate vs suspicious.
    Returns (legitimate_count, suspicious_count).
    """
    total_legitimate = 0
    total_suspicious = 0
    
    for report in reports:
        if not report.issues and not report.has_invalid_utf8:
            continue
        if report.error and "Read error" in report.error:
            continue
        
        filepath = report.path
        print(f"\n{'='*60}")
        print(f"FILE: {filepath}")
        print('='*60)
        
        # Read content
        if report.has_invalid_utf8:
            content = filepath.read_bytes().decode('utf-8', errors='replace')
        else:
            content = filepath.read_text(encoding='utf-8')
        
        lines = content.split('\n')
        
        # Group issues by line
        issues_by_line: Dict[int, List[Issue]] = {}
        for issue in report.issues:
            if issue.line_num not in issues_by_line:
                issues_by_line[issue.line_num] = []
            issues_by_line[issue.line_num].append(issue)
        
        if smart:
            # Smart mode: categorize and display separately
            file_legitimate = []
            file_suspicious = []
            
            for line_num in sorted(issues_by_line.keys()):
                line = lines[line_num - 1]
                legit, susp = classify_issues_smart(line, issues_by_line[line_num])
                file_legitimate.extend(legit)
                file_suspicious.extend(susp)
            
            total_legitimate += len(file_legitimate)
            total_suspicious += len(file_suspicious)
            
            # Print legitimate
            if file_legitimate:
                print("\nLEGITIMATE (isolated non-ASCII):")
                for issue in file_legitimate:
                    # Get actual char from line
                    line = lines[issue.line_num - 1]
                    char = line[issue.col - 1] if issue.col <= len(line) else '?'
                    print(f"  L{issue.line_num}:C{issue.col}  {char}  ({issue.codepoint}) in '...{issue.context}...'")
            else:
                print("\nLEGITIMATE (isolated non-ASCII):")
                print("  (none)")
            
            # Print suspicious with fix preview
            if file_suspicious:
                print("\nSUSPICIOUS (adjacent to other non-ASCII):")
                # Group by line for preview
                susp_by_line: Dict[int, List[Issue]] = {}
                for issue in file_suspicious:
                    if issue.line_num not in susp_by_line:
                        susp_by_line[issue.line_num] = []
                    susp_by_line[issue.line_num].append(issue)
                
                for line_num in sorted(susp_by_line.keys()):
                    original_line = lines[line_num - 1]
                    fixed_line = original_line
                    
                    # Apply fixes (in reverse column order to preserve positions)
                    for issue in sorted(susp_by_line[line_num], key=lambda i: i.col, reverse=True):
                        col = issue.col - 1  # 0-indexed
                        char = original_line[col] if col < len(original_line) else ''
                        replacement = NORMALIZE_MAP.get(char, '?')
                        fixed_line = fixed_line[:col] + replacement + fixed_line[col+1:]
                    
                    print(f"\n  L{line_num}:")
                    print(f"    - {repr(original_line)}")
                    print(f"    + {repr(fixed_line)}")
                    
                    changes = [f"{i.codepoint}->'{i.replacement}'" for i in susp_by_line[line_num]]
                    print(f"      ({', '.join(changes)})")
            else:
                print("\nSUSPICIOUS (adjacent to other non-ASCII):")
                print("  (none)")
            
        else:
            # Original dry-run behavior: show all as fixes
            for line_num in sorted(issues_by_line.keys()):
                original_line = lines[line_num - 1]
                fixed_line = original_line
                
                # Apply fixes (in reverse column order to preserve positions)
                for issue in sorted(issues_by_line[line_num], key=lambda i: i.col, reverse=True):
                    col = issue.col - 1  # 0-indexed
                    char = original_line[col] if col < len(original_line) else ''
                    replacement = NORMALIZE_MAP.get(char, '?')
                    fixed_line = fixed_line[:col] + replacement + fixed_line[col+1:]
                
                print(f"\nL{line_num}:")
                print(f"  - {repr(original_line)}")
                print(f"  + {repr(fixed_line)}")
                
                # Show what chars changed
                changes = [f"{i.codepoint}->'{i.replacement}'" for i in issues_by_line[line_num]]
                print(f"    ({', '.join(changes)})")
    
    return total_legitimate, total_suspicious


def create_backup(filepath: Path, backup_dir: Path) -> Path:
    """Create backup preserving relative path structure."""
    # Get relative path from backup_dir's parent
    try:
        rel_path = filepath.relative_to(backup_dir.parent.parent)
    except ValueError:
        rel_path = filepath.name
    
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    return backup_path


def main():
    parser = argparse.ArgumentParser(
        description='Broad UTF-8/ASCII Normalization Tool - catches EVERYTHING',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Catches ANY non-ASCII character in code files:
  - Invalid/corrupted UTF-8 byte sequences
  - Smart quotes, curly apostrophes
  - Em/en dashes, fancy hyphens
  - Non-breaking spaces, zero-width chars
  - Unicode arrows, bullets, symbols
  - Replacement characters (corruption indicator)

Smart mode distinguishes:
  - LEGITIMATE: Isolated non-ASCII (surrounded by ASCII) - likely intentional
  - SUSPICIOUS: Clustered non-ASCII (adjacent to each other) - likely corruption

Examples:
  %(prog)s --report packs/           # Find ALL non-ASCII in packs dir
  %(prog)s --report tools/foo.py     # Check single file
  %(prog)s --dry-run file.py         # Preview all fixes
  %(prog)s --dry-run --smart file.py # Categorize legitimate vs suspicious
  %(prog)s --fix packs/gen.scd       # Fix ALL non-ASCII
  %(prog)s --smart-fix file.py       # Fix SUSPICIOUS only (keep legitimate)
  %(prog)s --report . --ext .scd     # Check only .scd files in dir
        """
    )
    
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', action='store_true',
                      help='Scan and report all non-ASCII')
    mode.add_argument('--dry-run', action='store_true',
                      help='Preview fixes line-by-line (no changes made)')
    mode.add_argument('--fix', action='store_true',
                      help='Normalize ALL non-ASCII to ASCII (backups created)')
    mode.add_argument('--smart-fix', action='store_true',
                      help='Normalize only SUSPICIOUS non-ASCII (backups created)')
    
    parser.add_argument('path', type=Path, help='File or directory to process')
    parser.add_argument('--smart', action='store_true',
                        help='With --dry-run: categorize as legitimate vs suspicious')
    parser.add_argument('--ext', nargs='+', metavar='EXT',
                        help='File extensions (e.g., .scd .py)')
    parser.add_argument('--backup-dir', type=Path,
                        help='Custom backup directory')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Summary only')
    
    args = parser.parse_args()
    
    if not args.path.exists():
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)
    
    if args.smart and not args.dry_run:
        print("Error: --smart only works with --dry-run")
        print("       Use --smart-fix to fix only suspicious characters")
        sys.exit(1)
    
    # Normalize extensions
    extensions = None
    if args.ext:
        extensions = [e if e.startswith('.') else f'.{e}' for e in args.ext]
    
    print(f"Scanning: {args.path}")
    files = collect_files(args.path, extensions)
    
    if not files:
        print("No matching files found.")
        sys.exit(0)
    
    if len(files) == 1 and args.path.is_file():
        print(f"Checking single file for non-ASCII...")
    else:
        print(f"Checking {len(files)} file(s) for non-ASCII...")
    
    reports = [scan_file(f) for f in files]
    files_with_issues, total_issues, invalid_utf8 = print_report(reports, verbose=not args.quiet)
    
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Files with non-ASCII: {files_with_issues}")
    print(f"  Total non-ASCII chars: {total_issues}")
    if invalid_utf8:
        print(f"  ⚠️  Files with INVALID UTF-8: {invalid_utf8}")
    
    if total_issues == 0 and invalid_utf8 == 0:
        print("\n✓ All clean - pure ASCII!")
        sys.exit(0)
    
    if args.report:
        print("\nRun with --dry-run to preview fixes, or --fix to apply")
        print("Run with --dry-run --smart to see legitimate vs suspicious")
        sys.exit(1 if invalid_utf8 else 0)
    
    if args.dry_run:
        total_legit, total_susp = print_dry_run(reports, smart=args.smart)
        print("\n" + "=" * 60)
        if args.smart:
            print(f"{total_legit} legitimate, {total_susp} suspicious")
            if total_susp > 0:
                print("Run with --smart-fix to replace SUSPICIOUS only")
            if total_legit > 0:
                print("Run with --fix to replace ALL (including legitimate)")
        else:
            print("DRY RUN - no changes made")
            print("Run with --fix to apply these changes")
            print("Run with --dry-run --smart to categorize legitimate vs suspicious")
        sys.exit(0)
    
    # Fix mode (--fix or --smart-fix)
    only_suspicious = args.smart_fix
    
    print("\n" + "=" * 60)
    if only_suspicious:
        print("Normalizing SUSPICIOUS non-ASCII to ASCII (keeping legitimate)...")
    else:
        print("Normalizing ALL non-ASCII to ASCII...")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if args.backup_dir:
        backup_dir = args.backup_dir
    else:
        base = args.path if args.path.is_dir() else args.path.parent
        backup_dir = base / f"_utf8_backups_{timestamp}"
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"Backups: {backup_dir}")
    
    fixed_count = 0
    chars_fixed = 0
    for report in reports:
        if not report.issues and not report.has_invalid_utf8:
            continue
        if report.error and "Read error" in report.error:
            continue
        
        filepath = report.path
        create_backup(filepath, backup_dir)
        
        if report.has_invalid_utf8:
            fixed_content, fix_count = fix_file_with_invalid_utf8(filepath, only_suspicious=only_suspicious)
        else:
            content = filepath.read_text(encoding='utf-8')
            fixed_content, fix_count = fix_content(content, only_suspicious=only_suspicious)
        
        if fix_count > 0:
            filepath.write_text(fixed_content, encoding='utf-8')
            fixed_count += 1
            chars_fixed += fix_count
            
            if not args.quiet:
                print(f"  Fixed: {filepath} ({fix_count} chars)")
        elif not args.quiet and not only_suspicious:
            print(f"  Fixed: {filepath} ({fix_count} chars)")
    
    print(f"\nFixed {chars_fixed} char(s) in {fixed_count} file(s)")


if __name__ == '__main__':
    main()
