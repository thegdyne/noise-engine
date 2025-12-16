#!/usr/bin/env python3
"""
SuperCollider Syntax Validator

Checks SC files for common syntax errors that would cause runtime failures.
This is a static analysis tool - it doesn't require sclang installed.

Checks:
1. var declarations must be at top of function blocks
2. Balanced braces, brackets, parentheses
"""

import os
import re
import sys
from pathlib import Path


class SCValidationError:
    def __init__(self, file, line_num, message, line_content):
        self.file = file
        self.line_num = line_num
        self.message = message
        self.line_content = line_content
    
    def __str__(self):
        return f"{self.file}:{self.line_num}: {self.message}\n  {self.line_content.strip()}"


def strip_strings_and_comments(content: str):
    """
    Return lines with all content inside:
      - double-quoted strings
      - line comments //
      - block comments /* ... */
    replaced by spaces (length preserved per-line).
    This prevents false delimiter matches and enables simple line heuristics.
    """
    lines = content.split('\n')
    out = []
    in_string = False
    in_block = False
    
    for line in lines:
        res = []
        i = 0
        while i < len(line):
            # End block comment
            if in_block:
                if line[i:i+2] == '*/':
                    in_block = False
                    res.append('  ')
                    i += 2
                else:
                    res.append(' ')
                    i += 1
                continue

            # String toggle (must be handled BEFORE comment starts)
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                in_string = not in_string
                res.append(' ')
                i += 1
                continue

            # Inside string: blank everything until closing quote
            if in_string:
                res.append(' ')
                i += 1
                continue

            # Start block comment
            if line[i:i+2] == '/*':
                in_block = True
                res.append('  ')
                i += 2
                continue

            # Line comment: blank rest of line
            if line[i:i+2] == '//':
                res.append(' ' * (len(line) - i))
                break

            res.append(line[i])
            i += 1
        out.append(''.join(res))
    return out


def check_var_placement(content, filepath):
    """
    Heuristic check: inside any { ... } block, once we see a non-var executable
    line, later `var ...` lines in that same block are flagged.
    
    Handles two arg styles:
    1. Pipe style: { |arg1, arg2| ... } - may span multiple lines
    2. Keyword style: { arg a, b; ... } - may span multiple lines until ;
    """
    errors = []
    raw_lines = content.split('\n')
    code_lines = strip_strings_and_comments(content)

    class Frame:
        __slots__ = ("saw_stmt", "in_pipe_args", "in_arg_keyword", "pipe_open_line")
        def __init__(self):
            self.saw_stmt = False
            self.in_pipe_args = False
            self.in_arg_keyword = False  # For `arg x, y;` style
            self.pipe_open_line = 0

    stack = []  # one Frame per '{'
    
    for ln, line in enumerate(code_lines, 1):
        s = line.strip()
        
        # Track braces and detect pipe-arg start
        for i, ch in enumerate(line):
            if ch == '{':
                frame = Frame()
                # Check if pipe args start on this line: { |
                rest = line[i+1:].lstrip()
                if rest.startswith('|'):
                    # Check if args complete on same line (two pipes total)
                    after_open_pipe = rest[1:]
                    if '|' not in after_open_pipe:
                        frame.in_pipe_args = True
                        frame.pipe_open_line = ln
                stack.append(frame)
            elif ch == '}':
                if stack:
                    stack.pop()
        
        if not stack:
            continue
        
        frame = stack[-1]
        
        # Handle pipe-style args
        if frame.in_pipe_args:
            if ln > frame.pipe_open_line and '|' in s:
                frame.in_pipe_args = False
            continue  # Skip while in pipe args
        
        # Handle arg keyword style
        if frame.in_arg_keyword:
            if ';' in s:
                frame.in_arg_keyword = False
            continue  # Skip while in arg keyword block
        
        # Check if arg keyword block starts
        if re.match(r'^arg\b', s):
            if ';' not in s:
                # Multi-line arg declaration
                frame.in_arg_keyword = True
            continue  # Skip this line (it's an arg declaration)
        
        # Classify current line within current block
        if s and s not in ('{', '}', '};', ');', '),', '});'):
            if re.match(r'^var\b', s):
                if frame.saw_stmt:
                    errors.append(SCValidationError(
                        filepath, ln,
                        "var declaration appears after executable code in this block",
                        raw_lines[ln - 1] if ln - 1 < len(raw_lines) else ""
                    ))
            elif s.startswith('|') or s.endswith('|'):
                pass  # pipe args (shouldn't reach here normally)
            elif 'SynthDef(' in s or 'SynthDef (' in s:
                pass  # SynthDef declaration line
            elif '{' in line:
                pass  # Line contains brace - skip to avoid misattribution
            else:
                frame.saw_stmt = True

    return errors


def check_balanced_delimiters(content, filepath):
    """Check for balanced braces, brackets, parentheses."""
    errors = []
    raw_lines = content.split('\n')
    lines = strip_strings_and_comments(content)
    
    # Track counts
    braces = 0
    brackets = 0
    parens = 0
    
    # Track where imbalance starts
    brace_lines = []
    bracket_lines = []
    paren_lines = []
    
    for i, line in enumerate(lines, 1):
        for j, char in enumerate(line):
            if char == '{':
                braces += 1
                brace_lines.append(i)
            elif char == '}':
                braces -= 1
                if braces < 0:
                    errors.append(SCValidationError(
                        filepath, i,
                        "Extra closing brace '}'",
                        raw_lines[i - 1] if i - 1 < len(raw_lines) else ""
                    ))
                    braces = 0
                elif brace_lines:
                    brace_lines.pop()
            elif char == '[':
                brackets += 1
                bracket_lines.append(i)
            elif char == ']':
                brackets -= 1
                if brackets < 0:
                    errors.append(SCValidationError(
                        filepath, i,
                        "Extra closing bracket ']'",
                        raw_lines[i - 1] if i - 1 < len(raw_lines) else ""
                    ))
                    brackets = 0
                elif bracket_lines:
                    bracket_lines.pop()
            elif char == '(':
                parens += 1
                paren_lines.append(i)
            elif char == ')':
                parens -= 1
                if parens < 0:
                    errors.append(SCValidationError(
                        filepath, i,
                        "Extra closing paren ')'",
                        raw_lines[i - 1] if i - 1 < len(raw_lines) else ""
                    ))
                    parens = 0
                elif paren_lines:
                    paren_lines.pop()
    
    if braces != 0:
        line_num = brace_lines[0] if brace_lines else 1
        errors.append(SCValidationError(
            filepath, line_num,
            f"Unbalanced braces: {braces} unclosed",
            raw_lines[line_num - 1] if line_num <= len(raw_lines) else ""
        ))
    
    if brackets != 0:
        line_num = bracket_lines[0] if bracket_lines else 1
        errors.append(SCValidationError(
            filepath, line_num,
            f"Unbalanced brackets: {brackets} unclosed",
            raw_lines[line_num - 1] if line_num <= len(raw_lines) else ""
        ))
    
    if parens != 0:
        line_num = paren_lines[0] if paren_lines else 1
        errors.append(SCValidationError(
            filepath, line_num,
            f"Unbalanced parentheses: {parens} unclosed",
            raw_lines[line_num - 1] if line_num <= len(raw_lines) else ""
        ))
    
    return errors


def validate_file(filepath):
    """Run all validations on a single file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return [SCValidationError(filepath, 0, f"Could not read file: {e}", "")]
    
    errors = []
    errors.extend(check_var_placement(content, filepath))
    errors.extend(check_balanced_delimiters(content, filepath))
    
    return errors


def main():
    """Validate all .scd files in supercollider directory."""
    script_dir = Path(__file__).parent.parent
    sc_dir = script_dir / 'supercollider'
    
    if not sc_dir.exists():
        print(f"ERROR: SuperCollider directory not found: {sc_dir}")
        sys.exit(1)
    
    all_errors = []
    files_checked = 0
    
    for scd_file in sc_dir.rglob('*.scd'):
        files_checked += 1
        errors = validate_file(scd_file)
        all_errors.extend(errors)
    
    print(f"Checked {files_checked} SuperCollider files")
    
    if all_errors:
        print(f"\n❌ Found {len(all_errors)} error(s):\n")
        for error in all_errors:
            print(f"  {error}\n")
        sys.exit(1)
    else:
        print("✓ All SuperCollider files passed syntax validation")
        sys.exit(0)


if __name__ == '__main__':
    main()
