#!/usr/bin/env python3
"""
Script to find and fix bare except blocks in the codebase.
"""

import os
import re
import sys
from typing import List, Tuple

def find_bare_except_blocks(file_path: str) -> List[Tuple[int, str]]:
    """Find bare except blocks in a file."""
    bare_excepts = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            # Look for bare except: statements
            if re.match(r'^\s*except:\s*$', line):
                bare_excepts.append((i + 1, line.rstrip()))
                
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return bare_excepts

def fix_bare_except_in_file(file_path: str) -> int:
    """Fix bare except blocks in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace bare except: with except Exception as e:
        original_content = content
        content = re.sub(
            r'^(\s*)except:\s*$',
            r'\1except Exception as e:',
            content,
            flags=re.MULTILINE
        )
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Count how many replacements were made
            count = len(re.findall(r'^\s*except:\s*$', original_content, re.MULTILINE))
            return count
        
        return 0
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return 0

def main():
    """Main function to find and fix bare except blocks."""
    # Directories to scan
    directories = [
        'backend/app',
        'backend/tests',
        'alembic',
        'scripts',
        'agent_taskforce',
        'knowledge_graph'
    ]
    
    total_files = 0
    total_fixed = 0
    files_with_bare_except = []
    
    print("Scanning for bare except blocks...")
    print("-" * 60)
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
            
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    bare_excepts = find_bare_except_blocks(file_path)
                    
                    if bare_excepts:
                        files_with_bare_except.append((file_path, bare_excepts))
                        total_files += 1
                        
                        print(f"\n{file_path}:")
                        for line_num, line in bare_excepts:
                            print(f"  Line {line_num}: {line}")
    
    if not files_with_bare_except:
        print("\nNo bare except blocks found!")
        return
    
    print(f"\n{'-' * 60}")
    print(f"Found {total_files} files with bare except blocks")
    print(f"{'-' * 60}")
    
    # Ask user if they want to fix them
    response = input("\nDo you want to fix all bare except blocks? (y/n): ")
    
    if response.lower() == 'y':
        print("\nFixing bare except blocks...")
        print("-" * 60)
        
        for file_path, _ in files_with_bare_except:
            count = fix_bare_except_in_file(file_path)
            if count > 0:
                total_fixed += count
                print(f"Fixed {count} bare except blocks in {file_path}")
        
        print(f"\n{'-' * 60}")
        print(f"Total bare except blocks fixed: {total_fixed}")
    else:
        print("\nNo changes made.")

if __name__ == "__main__":
    main()