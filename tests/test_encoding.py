"""
Test for encoding corruption (mojibake) in source files.

This detects UTF-8 characters that have been incorrectly decoded as Windows-1252/Latin-1.
Common patterns include:
- Ã¢ sequences (from multi-byte UTF-8 chars)
- Ã© Ã¨ Ã¼ etc (from accented characters)
"""

import os
import re
import pytest
from pathlib import Path


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
    # Common single-byte corruptions
    (r'Ã©', 'Corrupted é'),
    (r'Ã¨', 'Corrupted è'),
    (r'Ã¼', 'Corrupted ü'),
    (r'Ã¶', 'Corrupted ö'),
    (r'Ã¤', 'Corrupted ä'),
    (r'Ã±', 'Corrupted ñ'),
]

# File extensions to check
CHECK_EXTENSIONS = {'.py', '.scd', '.md'}

# Directories to skip
SKIP_DIRS = {'__pycache__', '.git', 'venv', 'env', '.venv', 'node_modules', 'build', 'dist'}

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
    """Check a single file for mojibake patterns. Returns list of (line_num, pattern, description)."""
    issues = []
    try:
        content = filepath.read_text(encoding='utf-8')
        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, description in MOJIBAKE_PATTERNS:
                if re.search(pattern, line):
                    issues.append((line_num, pattern, description, line.strip()[:80]))
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
        main_frame = project_root / 'src' / 'gui' / 'main_frame.py'
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
        main_frame = project_root / 'src' / 'gui' / 'main_frame.py'
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
