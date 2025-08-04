#!/usr/bin/env python3
"""
Verify no bare except blocks remain in the codebase.
"""

import os
import re
import sys

def check_file(file_path):
    """Check a file for bare except blocks."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        bare_excepts = []
        for i, line in enumerate(lines):
            if re.match(r'^\s*except:\s*$', line):
                bare_excepts.append((i + 1, line.rstrip()))
        
        return bare_excepts
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def main():
    """Check all Python files for bare except blocks."""
    directories = ['backend/app', 'backend/tests', 'alembic', 'scripts', 'agent_taskforce', 'knowledge_graph']
    
    found_any = False
    for directory in directories:
        if not os.path.exists(directory):
            continue
        
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    bare_excepts = check_file(file_path)
                    
                    if bare_excepts:
                        if not found_any:
                            print("\nFound bare except blocks:")
                            print("-" * 60)
                            found_any = True
                        
                        print(f"\n{file_path}:")
                        for line_num, line in bare_excepts:
                            print(f"  Line {line_num}: {line}")
    
    if not found_any:
        print("[OK] No bare except blocks found in the codebase!")
        return 0
    else:
        print(f"\n{'-' * 60}")
        print("[FAIL] Bare except blocks still exist!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
