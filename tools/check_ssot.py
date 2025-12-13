#!/usr/bin/env python3
"""
Smart SSOT (Single Source of Truth) Checker

Intelligently discovers centralized constants and finds violations.

Features:
- Auto-discovers constant definitions in theme.py, config/__init__.py
- Extracts actual values from COLORS, FONT_SIZES, OSC_PATHS, etc.
- Scans all project files for hardcoded uses of those values
- Detects repeated magic values that should be centralized
- Checks Python and SuperCollider files
- Suggests fixes with the correct constant name

Usage:
    python tools/check_ssot.py [--verbose] [--fix-suggestions]
"""

import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class SSOTChecker:
    """Smart Single Source of Truth checker."""
    
    # Files that define centralized constants
    CENTRAL_SOURCES = [
        'src/gui/theme.py',
        'src/config/__init__.py',
    ]
    
    # Directories to scan for violations
    SCAN_DIRS = [
        'src',
        'supercollider',
    ]
    
    # Files/patterns to skip
    SKIP_PATTERNS = [
        '__pycache__',
        '.pyc',
        'check_ssot.py',  # Don't check ourselves
    ]
    
    # Known constant dictionaries to extract
    KNOWN_DICTS = [
        'COLORS',
        'FONT_SIZES',
        'FONT_FAMILY',
        'MONO_FONT',
        'OSC_PATHS',
        'GENERATOR_PARAMS',
        'CLOCK_RATES',
        'CLOCK_RATE_INDEX',
        'FILTER_TYPE_INDEX',
        'DRAG_SENSITIVITY',
    ]
    
    def __init__(self, repo_dir: str, verbose: bool = False):
        self.repo_dir = Path(repo_dir)
        self.verbose = verbose
        
        # Discovered constants: {source_file: {const_name: {value: key_name}}}
        self.constants: Dict[str, Dict[str, Dict[Any, str]]] = {}
        
        # Reverse lookup: {value: [(source_file, const_name, key_name), ...]}
        self.value_to_const: Dict[Any, List[Tuple[str, str, str]]] = defaultdict(list)
        
        # Violations found
        self.violations: List[Dict] = []
        
        # Warnings (potential issues)
        self.warnings: List[Dict] = []
        
        # Magic values (repeated literals that should maybe be centralized)
        self.magic_values: Dict[Any, List[Tuple[str, int]]] = defaultdict(list)
        
    def run(self) -> Tuple[int, int]:
        """Run the full SSOT check. Returns (violations, warnings)."""
        print(f"{Colors.BOLD}🔍 Smart SSOT Checker{Colors.END}")
        print("=" * 50)
        print()
        
        # Phase 1: Discover centralized constants
        print(f"{Colors.CYAN}📦 Phase 1: Discovering centralized constants...{Colors.END}")
        self.discover_constants()
        print()
        
        # Phase 2: Scan for violations
        print(f"{Colors.CYAN}🔎 Phase 2: Scanning for violations...{Colors.END}")
        self.scan_for_violations()
        print()
        
        # Phase 3: Detect magic values
        print(f"{Colors.CYAN}🔮 Phase 3: Detecting magic values...{Colors.END}")
        self.detect_magic_values()
        print()
        
        # Report results
        self.report_results()
        
        return len(self.violations), len(self.warnings)
    
    def discover_constants(self):
        """Parse central source files and extract constant definitions."""
        for source_file in self.CENTRAL_SOURCES:
            full_path = self.repo_dir / source_file
            if not full_path.exists():
                print(f"  ⚠️  {source_file} not found")
                continue
                
            print(f"  📄 Parsing {source_file}...")
            
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                self.constants[source_file] = {}
                self.extract_constants_from_ast(tree, source_file, content)
                
                # Count what we found
                total = sum(len(v) for v in self.constants[source_file].values())
                names = list(self.constants[source_file].keys())
                print(f"      Found {total} values in: {', '.join(names)}")
                
            except SyntaxError as e:
                print(f"  ❌ Syntax error in {source_file}: {e}")
    
    def extract_constants_from_ast(self, tree: ast.AST, source_file: str, content: str):
        """Extract constant dictionaries and simple assignments from AST."""
        for node in ast.walk(tree):
            # Handle: COLORS = {...}
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if name in self.KNOWN_DICTS or name.isupper():
                            self.extract_value(name, node.value, source_file)
            
            # Handle: COLORS: Dict = {...} (annotated assignment)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    name = node.target.id
                    if name in self.KNOWN_DICTS or name.isupper():
                        if node.value:
                            self.extract_value(name, node.value, source_file)
    
    def extract_value(self, name: str, node: ast.AST, source_file: str):
        """Extract values from an AST node (dict, string, number)."""
        if name not in self.constants[source_file]:
            self.constants[source_file][name] = {}
        
        if isinstance(node, ast.Dict):
            # It's a dictionary
            for key, value in zip(node.keys, node.values):
                if key is None:
                    continue
                key_name = self.get_literal_value(key)
                val = self.get_literal_value(value)
                if key_name is not None and val is not None:
                    self.constants[source_file][name][val] = key_name
                    self.value_to_const[val].append((source_file, name, key_name))
                    
        elif isinstance(node, ast.Constant):
            # Simple constant: FONT_FAMILY = 'Helvetica'
            val = node.value
            self.constants[source_file][name][val] = name
            self.value_to_const[val].append((source_file, name, name))
            
        elif isinstance(node, ast.List):
            # List of values
            for i, item in enumerate(node.elts):
                val = self.get_literal_value(item)
                if val is not None:
                    key_name = f"[{i}]"
                    self.constants[source_file][name][val] = key_name
                    self.value_to_const[val].append((source_file, name, key_name))
    
    def get_literal_value(self, node: ast.AST) -> Optional[Any]:
        """Extract literal value from AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        return None
    
    def scan_for_violations(self):
        """Scan project files for hardcoded values that should use constants."""
        for scan_dir in self.SCAN_DIRS:
            dir_path = self.repo_dir / scan_dir
            if not dir_path.exists():
                continue
                
            for file_path in dir_path.rglob('*'):
                if not file_path.is_file():
                    continue
                if any(skip in str(file_path) for skip in self.SKIP_PATTERNS):
                    continue
                    
                # Check Python files
                if file_path.suffix == '.py':
                    self.check_python_file(file_path)
                    
                # Check SuperCollider files
                elif file_path.suffix == '.scd':
                    self.check_sc_file(file_path)
    
    def check_python_file(self, file_path: Path):
        """Check a Python file for SSOT violations."""
        rel_path = file_path.relative_to(self.repo_dir)
        
        # Skip central source files
        if str(rel_path) in self.CENTRAL_SOURCES:
            return
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not read {rel_path}: {e}")
            return
        
        # Check each line
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
                
            # Check for hardcoded hex colors
            hex_colors = re.findall(r'["\']#([0-9a-fA-F]{3,6})["\']', line)
            for color in hex_colors:
                full_color = f'#{color}'
                # Normalize to 6 digits
                if len(color) == 3:
                    full_color = f'#{color[0]*2}{color[1]*2}{color[2]*2}'
                    
                if full_color.lower() in [v.lower() for v in self.value_to_const.keys() if isinstance(v, str)]:
                    # Find the matching constant
                    for val, const_list in self.value_to_const.items():
                        if isinstance(val, str) and val.lower() == full_color.lower():
                            source, const_name, key = const_list[0]
                            self.add_violation(
                                file_path=str(rel_path),
                                line_num=line_num,
                                line=line.strip(),
                                value=full_color,
                                suggestion=f"{const_name}['{key}']",
                                source=source
                            )
                            break
            
            # Check for hardcoded font-size in stylesheets
            font_size_match = re.search(r'font-size:\s*(\d+)px', line)
            if font_size_match and 'FONT_SIZES' not in line:
                size = int(font_size_match.group(1))
                if size in self.value_to_const:
                    for source, const_name, key in self.value_to_const[size]:
                        if const_name == 'FONT_SIZES':
                            self.add_violation(
                                file_path=str(rel_path),
                                line_num=line_num,
                                line=line.strip(),
                                value=f'{size}px',
                                suggestion=f"{{FONT_SIZES['{key}']}}px",
                                source=source
                            )
                            break
            
            # Check for hardcoded OSC paths
            osc_match = re.search(r'["\'](/noise/[^"\']+)["\']', line)
            if osc_match and 'OSC_PATHS' not in line:
                path = osc_match.group(1)
                if path in self.value_to_const:
                    for source, const_name, key in self.value_to_const[path]:
                        if const_name == 'OSC_PATHS':
                            self.add_violation(
                                file_path=str(rel_path),
                                line_num=line_num,
                                line=line.strip(),
                                value=path,
                                suggestion=f"OSC_PATHS['{key}']",
                                source=source
                            )
                            break
            
            # Track potential magic values (repeated literals)
            self.track_magic_values(line, str(rel_path), line_num)
    
    def check_sc_file(self, file_path: Path):
        """Check a SuperCollider file for SSOT violations."""
        rel_path = file_path.relative_to(self.repo_dir)
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Could not read {rel_path}: {e}")
            return
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('//'):
                continue
                
            # Check for OSC paths that should match Python
            osc_matches = re.findall(r'["\'](/noise/[^"\']+)["\']', line)
            for path in osc_matches:
                # Check if this path exists in Python OSC_PATHS (exact or prefix match)
                path_found = False
                if path in self.value_to_const:
                    path_found = True
                else:
                    # Check if path starts with any defined OSC path (for dynamic paths)
                    # e.g., /noise/gen/custom/1/0 starts with /noise/gen/custom
                    for defined_path in self.value_to_const:
                        if isinstance(defined_path, str) and defined_path.startswith('/noise/'):
                            if path.startswith(defined_path + '/') or path.startswith(defined_path + ' '):
                                path_found = True
                                break
                
                if not path_found:
                    # Path used in SC but not in Python config
                    self.add_warning(
                        file_path=str(rel_path),
                        line_num=line_num,
                        line=line.strip(),
                        message=f"OSC path '{path}' not found in Python OSC_PATHS"
                    )
    
    def track_magic_values(self, line: str, file_path: str, line_num: int):
        """Track repeated literal values that might need centralization."""
        # Skip lines that are just accessing known dicts (e.g., COLORS['text'])
        if re.search(r"(COLORS|FONT_SIZES|OSC_PATHS|DRAG_SENSITIVITY)\[", line):
            return
            
        # Track hex colors that aren't in dict access
        for match in re.finditer(r'#[0-9a-fA-F]{6}', line):
            color = match.group().lower()
            self.magic_values[('color', color)].append((file_path, line_num))
        
        # Track repeated strings - but skip common dict key patterns
        # Only track strings that look like they could be paths or config values
        for match in re.finditer(r'["\']([a-z_/]{6,})["\']', line, re.IGNORECASE):
            value = match.group(1)
            # Skip if it looks like a dict key access
            if re.search(rf"\[['\"]({re.escape(value)})['\"]", line):
                continue
            # Only track path-like or constant-like strings
            if value.startswith('/') or value.isupper() or '_' in value:
                self.magic_values[('string', value)].append((file_path, line_num))
    
    def detect_magic_values(self):
        """Find magic values that appear multiple times and should be centralized."""
        for (val_type, value), locations in self.magic_values.items():
            # Only flag if appears 3+ times in different files
            unique_files = set(loc[0] for loc in locations)
            if len(unique_files) >= 3 and len(locations) >= 3:
                # Check if it's already centralized
                if value not in self.value_to_const and ('color', value) not in self.value_to_const:
                    self.add_warning(
                        file_path="multiple",
                        line_num=0,
                        line=f"Found in {len(unique_files)} files, {len(locations)} times",
                        message=f"Consider centralizing {val_type} '{value}'"
                    )
    
    def add_violation(self, file_path: str, line_num: int, line: str, 
                      value: str, suggestion: str, source: str):
        """Add a violation to the list."""
        self.violations.append({
            'file': file_path,
            'line_num': line_num,
            'line': line,
            'value': value,
            'suggestion': suggestion,
            'source': source,
        })
    
    def add_warning(self, file_path: str, line_num: int, line: str, message: str):
        """Add a warning to the list."""
        self.warnings.append({
            'file': file_path,
            'line_num': line_num,
            'line': line,
            'message': message,
        })
    
    def report_results(self):
        """Print the results report."""
        print(f"{Colors.BOLD}📊 Results{Colors.END}")
        print("=" * 50)
        print()
        
        # Violations
        if self.violations:
            print(f"{Colors.RED}❌ VIOLATIONS ({len(self.violations)}){Colors.END}")
            print("-" * 40)
            for v in self.violations:
                print(f"  {Colors.BOLD}{v['file']}:{v['line_num']}{Colors.END}")
                print(f"    Found: {Colors.RED}{v['value']}{Colors.END}")
                print(f"    Use:   {Colors.GREEN}{v['suggestion']}{Colors.END}")
                if self.verbose:
                    print(f"    Line:  {v['line'][:60]}...")
                print()
        else:
            print(f"{Colors.GREEN}✅ No violations found{Colors.END}")
            print()
        
        # Warnings
        if self.warnings:
            print(f"{Colors.YELLOW}⚠️  WARNINGS ({len(self.warnings)}){Colors.END}")
            print("-" * 40)
            for w in self.warnings:
                if w['line_num'] > 0:
                    print(f"  {Colors.BOLD}{w['file']}:{w['line_num']}{Colors.END}")
                else:
                    print(f"  {Colors.BOLD}{w['file']}{Colors.END}")
                print(f"    {w['message']}")
                print()
        
        # Summary
        print("-" * 50)
        total_constants = sum(
            sum(len(v) for v in source.values()) 
            for source in self.constants.values()
        )
        print(f"📦 Centralized constants discovered: {Colors.CYAN}{total_constants}{Colors.END}")
        print(f"❌ Violations: {Colors.RED if self.violations else Colors.GREEN}{len(self.violations)}{Colors.END}")
        print(f"⚠️  Warnings: {Colors.YELLOW if self.warnings else Colors.GREEN}{len(self.warnings)}{Colors.END}")
        
        # Calculate compliance
        if self.violations:
            print(f"\n{Colors.RED}SSOT compliance: FAIL{Colors.END}")
            return 1
        else:
            print(f"\n{Colors.GREEN}👑 SSOT compliance: PASS{Colors.END}")
            return 0


def find_repo_root() -> Path:
    """Find the repository root directory."""
    # Try to find it relative to this script
    script_dir = Path(__file__).parent
    
    # If we're in tools/, go up one level
    if script_dir.name == 'tools':
        return script_dir.parent
    
    # Otherwise try current directory
    cwd = Path.cwd()
    if (cwd / 'src').exists() and (cwd / 'supercollider').exists():
        return cwd
    
    # Try home directory default
    default = Path.home() / 'repos' / 'noise-engine'
    if default.exists():
        return default
    
    return cwd


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart SSOT Checker')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--repo', '-r', type=str, help='Repository directory')
    args = parser.parse_args()
    
    repo_dir = Path(args.repo) if args.repo else find_repo_root()
    
    if not repo_dir.exists():
        print(f"Error: Repository directory not found: {repo_dir}")
        sys.exit(1)
    
    checker = SSOTChecker(str(repo_dir), verbose=args.verbose)
    violations, warnings = checker.run()
    
    # Exit with error code if violations found
    sys.exit(1 if violations > 0 else 0)


if __name__ == '__main__':
    main()
