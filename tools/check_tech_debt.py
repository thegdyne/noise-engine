#!/usr/bin/env python3
"""
Tech Debt Checker - Analyzes code quality patterns

Checks for:
- Bare except: statements
- Silent exception swallowing (except ...: pass)
- Broad exception catches without logging

Exit codes:
- 0: Pass (no violations)
- 1: Violations found
"""

import os
import re
import sys
from pathlib import Path

# ANSI colors
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Patterns to check
PATTERNS = {
    'bare_except': {
        'pattern': r'^\s*except\s*:\s*$',
        'severity': 'violation',
        'message': 'Bare except: catches all errors including KeyboardInterrupt',
    },
    'silent_broad_swallow': {
        'pattern': r'except\s+Exception\s*:\s*\n\s*pass\s*$',
        'severity': 'violation', 
        'message': 'Silent Exception swallow - all errors hidden',
    },
    'exception_no_binding': {
        'pattern': r'except\s+Exception\s*:(?!\s*\n\s*pass)',
        'severity': 'warning',
        'message': 'Catching Exception without binding (as e) - cannot log details',
    },
}

# Files/directories to scan
SCAN_DIRS = ['src']
SCAN_EXTENSIONS = ['.py']

# Files to skip
SKIP_FILES = ['__pycache__']

# Known false positives: (filename, line_number, pattern_name)
# These are intentional patterns that look like issues but aren't
ALLOWLIST = [
    ('logger.py', 56, 'exception_no_binding'),  # Uses self.handleError() - standard logging pattern
    ('main.py', 27, 'exception_no_binding'),  # Cleanup - OSC may already be gone
    ('main.py', 36, 'exception_no_binding'),  # Cleanup - SC may not be running
    ('main_frame.py', 664, 'exception_no_binding'),  # Startup check - file may not exist
]


def find_python_files(base_path):
    """Find all Python files to scan."""
    files = []
    for scan_dir in SCAN_DIRS:
        dir_path = base_path / scan_dir
        if dir_path.exists():
            for ext in SCAN_EXTENSIONS:
                files.extend(dir_path.rglob(f'*{ext}'))
    return [f for f in files if not any(skip in str(f) for skip in SKIP_FILES)]


def is_allowlisted(filepath, line_num, pattern_name):
    """Check if a finding is in the allowlist."""
    filename = filepath.name
    for allowed_file, allowed_line, allowed_pattern in ALLOWLIST:
        if filename == allowed_file and line_num == allowed_line and pattern_name == allowed_pattern:
            return True
    return False


def check_file(filepath):
    """Check a single file for tech debt patterns."""
    findings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return [('error', filepath, 0, f'Could not read file: {e}')]
    
    for name, check in PATTERNS.items():
        # For multi-line patterns, check full content
        if r'\n' in check['pattern']:
            for match in re.finditer(check['pattern'], content, re.MULTILINE):
                line_num = content[:match.start()].count('\n') + 1
                if not is_allowlisted(filepath, line_num, name):
                    findings.append((check['severity'], filepath, line_num, check['message']))
        else:
            # For single-line patterns, check line by line
            for i, line in enumerate(lines, 1):
                if re.search(check['pattern'], line):
                    # Skip if it's a comment
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    if not is_allowlisted(filepath, i, name):
                        findings.append((check['severity'], filepath, i, check['message']))
    
    return findings


def calculate_score(violations, warnings, total_files):
    """Calculate tech debt score (higher is better)."""
    if total_files == 0:
        return 100
    
    # Violations are -10 points each, warnings are -2 points each
    # Starting from 100
    penalty = (violations * 10) + (warnings * 2)
    score = max(0, 100 - penalty)
    return score


def main():
    # Find repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    print(f"{CYAN}🔧 Tech Debt Checker{RESET}")
    print("=" * 50)
    print()
    
    # Find files
    files = find_python_files(repo_root)
    print(f"{BOLD}📁 Scanning {len(files)} Python files...{RESET}")
    print()
    
    # Check all files
    all_findings = []
    for filepath in files:
        findings = check_file(filepath)
        all_findings.extend(findings)
    
    # Separate by severity
    violations = [f for f in all_findings if f[0] == 'violation']
    warnings = [f for f in all_findings if f[0] == 'warning']
    errors = [f for f in all_findings if f[0] == 'error']
    
    # Print results
    print(f"{BOLD}📊 Results{RESET}")
    print("=" * 50)
    print()
    
    if violations:
        print(f"{RED}❌ VIOLATIONS ({len(violations)}){RESET}")
        print("-" * 40)
        for severity, filepath, line, message in violations:
            rel_path = filepath.relative_to(repo_root)
            print(f"  {rel_path}:{line}")
            print(f"    {message}")
        print()
    
    if warnings:
        print(f"{YELLOW}⚠️  WARNINGS ({len(warnings)}){RESET}")
        print("-" * 40)
        for severity, filepath, line, message in warnings:
            rel_path = filepath.relative_to(repo_root)
            print(f"  {rel_path}:{line}")
            print(f"    {message}")
        print()
    
    if errors:
        print(f"{RED}🚫 ERRORS ({len(errors)}){RESET}")
        print("-" * 40)
        for severity, filepath, line, message in errors:
            print(f"  {filepath}: {message}")
        print()
    
    if not violations and not warnings and not errors:
        print(f"{GREEN}✅ No issues found!{RESET}")
        print()
    
    # Calculate and print score
    score = calculate_score(len(violations), len(warnings), len(files))
    
    print("-" * 50)
    print(f"📁 Files scanned: {len(files)}")
    print(f"❌ Violations: {len(violations)}")
    print(f"⚠️  Warnings: {len(warnings)}")
    print()
    
    if score == 100:
        print(f"{GREEN}{BOLD}🏗️  Tech Debt Score: {score}%{RESET}")
        print(f"{GREEN}🌟 CLEAN BUILD! Gold badge activated!{RESET}")
    elif score >= 80:
        print(f"{GREEN}🏗️  Tech Debt Score: {score}%{RESET}")
    elif score >= 50:
        print(f"{YELLOW}🏗️  Tech Debt Score: {score}%{RESET}")
    else:
        print(f"{RED}🏗️  Tech Debt Score: {score}%{RESET}")
    
    # Output for badge update script
    print(f"\nTech Debt Score: {score}%")
    
    # Return exit code
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main())
