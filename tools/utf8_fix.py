#!/usr/bin/env python3
"""
UTF-8 Corruption Removal Tool

Detects and fixes common UTF-8 encoding corruptions where multi-byte
UTF-8 sequences were misinterpreted as Latin-1/Windows-1252.

Usage:
    python utf8_fix.py --report <path>           # Scan and report issues
    python utf8_fix.py --fix <path>              # Fix issues (creates backups)
    python utf8_fix.py --report <path> --ext .md .py  # Specific extensions only
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, List, Tuple, Optional, Dict


def build_corruption_map() -> Dict[str, str]:
    """
    Build the corruption map dynamically to avoid encoding issues in source.
    
    When UTF-8 bytes are read as Latin-1/CP1252, multi-byte sequences become
    multiple single-byte characters. We detect these corrupted sequences.
    """
    patterns = {}
    
    # Format: (UTF-8 bytes as hex, correct unicode codepoint)
    # The "corrupted" string is what you get when UTF-8 bytes are read as Latin-1
    mappings = [
        # Em dash U+2014 (UTF-8: E2 80 94)
        (b'\xe2\x80\x94', '\u2014'),
        # En dash U+2013 (UTF-8: E2 80 93)
        (b'\xe2\x80\x93', '\u2013'),
        # Cross mark U+274C (UTF-8: E2 9D 8C)
        (b'\xe2\x9d\x8c', '\u274c'),
        # Check mark U+2713 (UTF-8: E2 9C 93)
        (b'\xe2\x9c\x93', '\u2713'),
        # Heavy check mark U+2714 (UTF-8: E2 9C 94)
        (b'\xe2\x9c\x94', '\u2714'),
        # Right arrow U+2192 (UTF-8: E2 86 92)
        (b'\xe2\x86\x92', '\u2192'),
        # Left arrow U+2190 (UTF-8: E2 86 90)
        (b'\xe2\x86\x90', '\u2190'),
        # Up arrow U+2191 (UTF-8: E2 86 91)
        (b'\xe2\x86\x91', '\u2191'),
        # Down arrow U+2193 (UTF-8: E2 86 93)
        (b'\xe2\x86\x93', '\u2193'),
        # Bullet U+2022 (UTF-8: E2 80 A2)
        (b'\xe2\x80\xa2', '\u2022'),
        # Ellipsis U+2026 (UTF-8: E2 80 A6)
        (b'\xe2\x80\xa6', '\u2026'),
        # Left single quote U+2018 (UTF-8: E2 80 98)
        (b'\xe2\x80\x98', '\u2018'),
        # Right single quote U+2019 (UTF-8: E2 80 99)
        (b'\xe2\x80\x99', '\u2019'),
        # Left double quote U+201C (UTF-8: E2 80 9C)
        (b'\xe2\x80\x9c', '\u201c'),
        # Right double quote U+201D (UTF-8: E2 80 9D)
        (b'\xe2\x80\x9d', '\u201d'),
        # Trademark U+2122 (UTF-8: E2 84 A2)
        (b'\xe2\x84\xa2', '\u2122'),
        # Star U+2605 (UTF-8: E2 98 85)
        (b'\xe2\x98\x85', '\u2605'),
        # White star U+2606 (UTF-8: E2 98 86)
        (b'\xe2\x98\x86', '\u2606'),
    ]
    
    for utf8_bytes, correct_char in mappings:
        # Simulate double-encoding: UTF-8 bytes read as Latin-1
        corrupted = utf8_bytes.decode('latin-1')
        patterns[corrupted] = correct_char
    
    # Additional patterns for Latin-1 range (single byte with 0xC2/0xC3 prefix)
    latin1_mappings = [
        # Degree U+00B0 (UTF-8: C2 B0)
        (b'\xc2\xb0', '\u00b0'),
        # Non-breaking space U+00A0 (UTF-8: C2 A0)
        (b'\xc2\xa0', '\u00a0'),
        # Copyright U+00A9 (UTF-8: C2 A9)
        (b'\xc2\xa9', '\u00a9'),
        # Registered U+00AE (UTF-8: C2 AE)
        (b'\xc2\xae', '\u00ae'),
        # Plus-minus U+00B1 (UTF-8: C2 B1)
        (b'\xc2\xb1', '\u00b1'),
        # Section U+00A7 (UTF-8: C2 A7)
        (b'\xc2\xa7', '\u00a7'),
        # Multiplication U+00D7 (UTF-8: C3 97)
        (b'\xc3\x97', '\u00d7'),
        # Division U+00F7 (UTF-8: C3 B7)
        (b'\xc3\xb7', '\u00f7'),
    ]
    
    for utf8_bytes, correct_char in latin1_mappings:
        corrupted = utf8_bytes.decode('latin-1')
        patterns[corrupted] = correct_char
    
    return patterns


# Build the map once at module load
CORRUPTION_MAP = build_corruption_map()


class FileIssue(NamedTuple):
    """Represents a corruption found in a file."""
    line_num: int
    corrupted: str
    correct: str
    context: str


class FileReport(NamedTuple):
    """Report for a single file."""
    path: Path
    issues: List[FileIssue]
    error: Optional[str] = None


def find_corruptions(content: str) -> List[FileIssue]:
    """Find all corruption instances in content."""
    issues = []
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        for corrupted, correct in CORRUPTION_MAP.items():
            if corrupted in line:
                # Find position for context
                pos = line.find(corrupted)
                start = max(0, pos - 20)
                end = min(len(line), pos + len(corrupted) + 20)
                context = line[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(line):
                    context = context + "..."
                
                issues.append(FileIssue(
                    line_num=line_num,
                    corrupted=repr(corrupted),
                    correct=correct,
                    context=context
                ))
    
    return issues


def fix_content(content: str) -> Tuple[str, int]:
    """Fix all corruptions in content. Returns (fixed_content, fix_count)."""
    fixed = content
    total_fixes = 0
    
    for corrupted, correct in CORRUPTION_MAP.items():
        count = fixed.count(corrupted)
        if count > 0:
            fixed = fixed.replace(corrupted, correct)
            total_fixes += count
    
    return fixed, total_fixes


def scan_file(filepath: Path) -> FileReport:
    """Scan a single file for corruptions."""
    try:
        # Try UTF-8 first, then Latin-1 as fallback
        try:
            content = filepath.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = filepath.read_text(encoding='latin-1')
        
        issues = find_corruptions(content)
        return FileReport(path=filepath, issues=issues)
    
    except Exception as e:
        return FileReport(path=filepath, issues=[], error=str(e))


def collect_files(path: Path, extensions: Optional[List[str]] = None) -> List[Path]:
    """Collect all files to process."""
    if path.is_file():
        return [path]
    
    files = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            filepath = Path(root) / filename
            
            # Skip hidden files and directories
            if any(part.startswith('.') for part in filepath.parts):
                continue
            
            # Skip backup directory
            if '_utf8_backups' in str(filepath):
                continue
            
            # Filter by extension if specified
            if extensions:
                if filepath.suffix.lower() not in [e.lower() for e in extensions]:
                    continue
            else:
                # Default: only text-like files
                text_extensions = {
                    '.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml', '.yml',
                    '.html', '.css', '.scss', '.xml', '.csv', '.rst', '.scd',
                    '.sh', '.bash', '.zsh', '.conf', '.cfg', '.ini', '.toml'
                }
                if filepath.suffix.lower() not in text_extensions:
                    continue
            
            files.append(filepath)
    
    return sorted(files)


def create_backup(filepath: Path, backup_dir: Path) -> Path:
    """Create a backup of the file."""
    backup_path = backup_dir / filepath.name
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    return backup_path


def print_report(reports: List[FileReport], verbose: bool = True) -> Tuple[int, int]:
    """Print the corruption report. Returns (files_with_issues, total_issues)."""
    files_with_issues = 0
    total_issues = 0
    
    for report in reports:
        if report.error:
            print(f"\n  {report.path}: ERROR - {report.error}")
            continue
        
        if not report.issues:
            continue
        
        files_with_issues += 1
        total_issues += len(report.issues)
        
        print(f"\n  {report.path}")
        print(f"   Found {len(report.issues)} corruption(s)")
        
        if verbose:
            # Group by corruption type
            by_type: Dict[Tuple[str, str], List[int]] = {}
            for issue in report.issues:
                key = (issue.corrupted, issue.correct)
                if key not in by_type:
                    by_type[key] = []
                by_type[key].append(issue.line_num)
            
            for (corrupted, correct), lines in by_type.items():
                lines_str = ', '.join(str(l) for l in lines[:5])
                if len(lines) > 5:
                    lines_str += f" (+{len(lines)-5} more)"
                print(f"   - {corrupted} -> '{correct}' on lines: {lines_str}")
    
    return files_with_issues, total_issues


def main():
    parser = argparse.ArgumentParser(
        description='UTF-8 Corruption Removal Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --report ./docs              # Report issues in docs folder
  %(prog)s --fix ./docs                 # Fix issues (creates backups first)
  %(prog)s --report file.md             # Check single file
  %(prog)s --fix . --ext .md .txt       # Fix only .md and .txt files
        """
    )
    
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', action='store_true', 
                      help='Scan and report corruptions without changing files')
    mode.add_argument('--fix', action='store_true',
                      help='Fix corruptions (backups created automatically)')
    
    parser.add_argument('path', type=Path,
                        help='File or directory to process')
    parser.add_argument('--ext', nargs='+', metavar='EXT',
                        help='File extensions to process (e.g., .md .py)')
    parser.add_argument('--backup-dir', type=Path,
                        help='Custom backup directory (default: <path>_utf8_backups_<timestamp>)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Minimal output (summary only)')
    
    args = parser.parse_args()
    
    # Validate path
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}")
        sys.exit(1)
    
    # Normalize extensions
    extensions = None
    if args.ext:
        extensions = [e if e.startswith('.') else f'.{e}' for e in args.ext]
    
    # Collect files
    print(f"Scanning: {args.path}")
    files = collect_files(args.path, extensions)
    
    if not files:
        print("No matching files found.")
        sys.exit(0)
    
    print(f"   Found {len(files)} file(s) to check")
    
    # Scan all files
    reports = [scan_file(f) for f in files]
    
    # Print report
    files_with_issues, total_issues = print_report(reports, verbose=not args.quiet)
    
    # Summary
    print("\n" + "="*60)
    print(f"Summary: {files_with_issues} file(s) with {total_issues} corruption(s)")
    
    if total_issues == 0:
        print("No corruptions found!")
        sys.exit(0)
    
    # If report mode, we're done
    if args.report:
        print("\nRun with --fix to repair these issues")
        sys.exit(0)
    
    # Fix mode - create backups and fix
    print("\n" + "="*60)
    print("Fixing corruptions...")
    
    # Create backup directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if args.backup_dir:
        backup_dir = args.backup_dir
    else:
        base = args.path if args.path.is_dir() else args.path.parent
        backup_dir = base / f"_utf8_backups_{timestamp}"
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"Backup directory: {backup_dir}")
    
    # Process files with issues
    fixed_count = 0
    for report in reports:
        if not report.issues or report.error:
            continue
        
        filepath = report.path
        
        # Create backup
        create_backup(filepath, backup_dir)
        
        # Read and fix content
        try:
            content = filepath.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = filepath.read_text(encoding='latin-1')
        
        fixed_content, fix_count = fix_content(content)
        
        # Write fixed content
        filepath.write_text(fixed_content, encoding='utf-8')
        fixed_count += 1
        
        if not args.quiet:
            print(f"   Fixed: {filepath} ({fix_count} replacements)")
    
    print(f"\nFixed {fixed_count} file(s)")
    print(f"Backups saved to: {backup_dir}")


if __name__ == '__main__':
    main()
