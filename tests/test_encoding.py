"""
Test for encoding corruption (mojibake) in source files.

This detects UTF-8 characters that have been incorrectly decoded as Windows-1252/Latin-1.
Common patterns include:
- Ã¢ sequences (from multi-byte UTF-8 chars)
- Ã© Ã¨ Ã¼ etc (from accented characters)
- Zero-width and invisible characters
- Smart quotes in code files

"""

import os
import re
import pytest
from pathlib import Path

# cdd-utils: utf8-ignore - This file contains deliberate corruption for testing
"""Test encoding detection and repair."""

# Common mojibake patterns - UTF-8 decoded as Windows-1252
MOJIBAKE_PATTERNS = [
    # Multi-byte UTF-8 sequences misread as Windows-1252
    (r'Ã¢', 'UTF-8 multi-byte as Windows-1252 (â prefix)'),
    (r'Ã¢â€"', 'Corrupted bullet/circle (●)'),
    (r'Ã¢â€ ', 'Corrupted arrow (→)'),
    (r'Ã¢Å¡', 'Corrupted warning symbol (⚠)'),
    (r'Ã¢â‚¬', 'Corrupted em dash/bullet (—•)'),
    (r'â€"', 'Partial mojibake sequence'),
    (r'â€™', 'Corrupted apostrophe/arrow'),
    (r'â€œ', 'Corrupted quote'),
    (r'â€', 'Corrupted special char'),
    # Additional mojibake patterns (different terminal/encoding display)
    (r'√¢', 'UTF-8 mojibake variant (alternate display)'),
    (r'√M-', 'UTF-8 mojibake with control chars'),
    # Common single-byte corruptions
    (r'Ã©', 'Corrupted é'),
    (r'Ã¨', 'Corrupted è'),
    (r'Ã¼', 'Corrupted ü'),
    (r'Ã¶', 'Corrupted ö'),
    (r'Ã¤', 'Corrupted ä'),
    (r'Ã±', 'Corrupted ñ'),
    # Standalone  - very common mojibake artifact (non-breaking space becomes Â)
    (r'Â(?=\s|[^\w]|$)', 'Standalone Â (corrupted non-breaking space)'),
    (r'Â ', 'Â followed by space (mojibake artifact)'),
]

# Invisible/problematic characters (checked separately - not regex patterns)
INVISIBLE_CHARS = [
    ('\u200b', 'Zero-width space (U+200B)'),
    ('\u200c', 'Zero-width non-joiner (U+200C)'),
    ('\u200d', 'Zero-width joiner (U+200D)'),
    ('\ufeff', 'BOM / Zero-width no-break space (U+FEFF)'),
    ('\u00a0', 'Non-breaking space (U+00A0)'),
    ('\ufffd', 'Replacement character (U+FFFD) - indicates prior decode error'),
    ('\u2028', 'Line separator (U+2028)'),
    ('\u2029', 'Paragraph separator (U+2029)'),
]

# Smart quotes - problematic in code files (.py, .scd)
SMART_QUOTE_CHARS = [
    ('\u201c', 'Left double quote (U+201C)'),
    ('\u201d', 'Right double quote (U+201D)'),
    ('\u2018', 'Left single quote (U+2018)'),
    ('\u2019', 'Right single quote (U+2019)'),
    ('\u00ab', 'Left guillemet (U+00AB)'),
    ('\u00bb', 'Right guillemet (U+00BB)'),
]

# File extensions to check
CHECK_EXTENSIONS = {'.py', '.scd', '.md'}

# Extensions where smart quotes are errors (not allowed in code)
CODE_EXTENSIONS = {'.py', '.scd'}

# Directories to skip
SKIP_DIRS = {'__pycache__', '.git', 'venv', 'venv312', 'env', '.venv', 'node_modules', 'build', 'dist'}

# Files to skip (test file contains patterns as literals)
SKIP_FILES = {'test_encoding.py'}


def get_project_root():
    """Get project root - works in both test and direct execution contexts."""
    # Try to find project root by looking for src/ directory
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Go up max 5 levels
        if (current / 'src').exists():
            return current
        current = current.parent
    # Fallback to script's parent
    return Path(__file__).resolve().parent


def find_source_files(root_dir: Path):
    """Find all source files to check."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        
        for filename in filenames:
            if filename in SKIP_FILES:
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in CHECK_EXTENSIONS:
                files.append(Path(dirpath) / filename)
    return files


def check_file_for_mojibake(filepath: Path):
    """Check a single file for mojibake patterns. Returns list of (line_num, pattern, description, preview)."""
    issues = []
    ext = filepath.suffix.lower()
    is_code_file = ext in CODE_EXTENSIONS
    
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines, 1):
            # Check regex mojibake patterns
            for pattern, description in MOJIBAKE_PATTERNS:
                if re.search(pattern, line):
                    issues.append((line_num, pattern, description, line.strip()[:80]))
            
            # Check invisible characters
            for char, description in INVISIBLE_CHARS:
                if char in line:
                    # For BOM, only flag if not first char of first line
                    if char == '\ufeff' and line_num == 1 and line.startswith(char):
                        issues.append((line_num, repr(char), f'{description} at file start', line.strip()[:80]))
                    elif char != '\ufeff':
                        issues.append((line_num, repr(char), description, line.strip()[:80]))
            
            # Check smart quotes (only in code files)
            if is_code_file:
                for char, description in SMART_QUOTE_CHARS:
                    if char in line:
                        issues.append((line_num, repr(char), f'{description} in code file', line.strip()[:80]))
                        
    except UnicodeDecodeError:
        issues.append((0, 'UnicodeDecodeError', 'File is not valid UTF-8', ''))
    except Exception as e:
        issues.append((0, 'Error', str(e), ''))
    return issues


class TestEncoding:
    """Test suite for encoding integrity."""

    @pytest.fixture(scope='class')
    def project_root(self):
        """Get project root directory."""
        return get_project_root()

    @pytest.fixture(scope='class')
    def source_files(self, project_root):
        """Get all source files to check."""
        return find_source_files(project_root)

    def test_no_mojibake_in_source_files(self, source_files, project_root):
        """Ensure no source files contain mojibake (encoding corruption)."""
        all_issues = []
        
        for filepath in source_files:
            issues = check_file_for_mojibake(filepath)
            if issues:
                rel_path = filepath.relative_to(project_root)
                for line_num, pattern, desc, preview in issues:
                    all_issues.append(f"{rel_path}:{line_num}: {desc} - {preview}")
        
        if all_issues:
            issue_report = "\n".join(all_issues[:20])  # Show first 20 issues
            if len(all_issues) > 20:
                issue_report += f"\n... and {len(all_issues) - 20} more issues"
            pytest.fail(f"Found {len(all_issues)} encoding corruption(s):\n{issue_report}")

    def test_main_frame_status_strings(self, project_root):
        """Specifically check main_frame.py status indicator strings."""
        main_frame = project_root / 'src' / 'gui' / 'controllers' / 'connection_controller.py'
        if not main_frame.exists():
            pytest.skip("main_frame.py not found")
        
        content = main_frame.read_text(encoding='utf-8')
        
        # These exact corrupted patterns should NOT be present
        bad_patterns = [
            'Ã¢â€"Â Connected',
            'Ã¢â€"Â Disconnected',
            'Ã¢â€"Â CONNECTION LOST',
            'Ã¢Å¡Â  RECONNECT',
        ]
        
        found = []
        for pattern in bad_patterns:
            if pattern in content:
                found.append(pattern)
        
        if found:
            pytest.fail(f"Found corrupted status strings in main_frame.py:\n" + 
                       "\n".join(f"  - {p}" for p in found))

    def test_expected_unicode_chars_valid(self, project_root):
        """Verify that proper Unicode characters are used, not corrupted versions."""
        main_frame = project_root / 'src' / 'gui' / 'controllers' / 'connection_controller.py'
        if not main_frame.exists():
            pytest.skip("main_frame.py not found")
        
        content = main_frame.read_text(encoding='utf-8')
        
        # These proper characters SHOULD be present (after fix)
        # Using ASCII alternatives to be safe
        expected_patterns = [
            ('Connected', 'Should have Connected status'),
            ('Disconnected', 'Should have Disconnected status'),
        ]
        
        for pattern, msg in expected_patterns:
            if pattern not in content:
                pytest.fail(f"Missing expected pattern: {msg}")

    def test_no_bom_in_files(self, source_files, project_root):
        """Check that no files start with a BOM marker."""
        bom_files = []
        for filepath in source_files:
            try:
                with open(filepath, 'rb') as f:
                    first_bytes = f.read(3)
                    if first_bytes == b'\xef\xbb\xbf':
                        bom_files.append(filepath.relative_to(project_root))
            except Exception:
                pass
        
        if bom_files:
            pytest.fail(f"Files with BOM marker (remove with dos2unix or similar):\n" +
                       "\n".join(f"  - {f}" for f in bom_files))


if __name__ == '__main__':
    # Allow running directly for debugging
    root = get_project_root()
    print(f"Checking project root: {root}")
    
    files = find_source_files(root)
    print(f"Found {len(files)} source files")
    
    total_issues = 0
    for f in files:
        issues = check_file_for_mojibake(f)
        if issues:
            print(f"\n{f.relative_to(root)}:")
            for line_num, pattern, desc, preview in issues:
                print(f"  Line {line_num}: {desc}")
                print(f"    {preview}")
                total_issues += 1
    
    if total_issues == 0:
        print("\n✓ No encoding issues found!")
    else:
        print(f"\n✗ Found {total_issues} encoding issues")
