#!/usr/bin/env python3
"""
Script to enhance exception handling with proper logging.
"""

import os
import re
import sys
from typing import List, Tuple, Dict

# Files that need specific exception handling improvements
CRITICAL_FILES = {
    'backend/app/core/api_security.py': [
        (287, 'ValueError', 'Failed to validate timestamp'),
    ],
    'backend/app/middleware/api_versioning.py': [
        (153, 'json.JSONDecodeError', 'Failed to parse request body for version transformation'),
    ],
    'backend/app/middleware/security_monitoring_v2.py': [
        (161, None, 'Failed to read request body for security monitoring'),
        (214, 'json.JSONDecodeError', 'Failed to parse authentication request body'),
    ],
    'backend/app/middleware/rate_limit_middleware.py': [
        (346, 'RedisError', 'Redis error when calculating rate limit headers'),
        (446, 'RedisError', 'Failed to log rate limit violation to Redis'),
        (541, 'json.JSONDecodeError', 'Failed to parse rate limit violation data'),
    ],
    'backend/app/integrations/recreation_gov_client.py': [
        (1115, None, 'Failed to get facility activities'),
        (1134, None, 'Failed to get facility media'),
    ],
}

def enhance_exception_handling(file_path: str, line_info: List[Tuple[int, str, str]]) -> bool:
    """Enhance exception handling in a specific file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        
        # Sort line info by line number in reverse to avoid offset issues
        line_info_sorted = sorted(line_info, key=lambda x: x[0], reverse=True)
        
        for line_num, exc_type, log_msg in line_info_sorted:
            # Adjust for 0-based indexing
            idx = line_num - 1
            
            if idx < len(lines) and 'except Exception as e:' in lines[idx]:
                # Check if there's already logging in the next few lines
                has_logging = False
                for i in range(idx + 1, min(idx + 5, len(lines))):
                    if 'logger' in lines[i] or 'log' in lines[i]:
                        has_logging = True
                        break
                
                if not has_logging:
                    # Determine indentation
                    indent_match = re.match(r'^(\s*)', lines[idx])
                    indent = indent_match.group(1) if indent_match else ''
                    
                    # Add logging statement
                    if exc_type and exc_type != 'None':
                        # Replace with specific exception type
                        lines[idx] = f"{indent}except {exc_type} as e:\n"
                    
                    # Insert logging after the except line
                    log_line = f"{indent}    logger.error(f\"{log_msg}: {{e}}\")\n"
                    lines.insert(idx + 1, log_line)
                    modified = True
                    print(f"  Enhanced line {line_num} with logging: {log_msg}")
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error enhancing {file_path}: {e}")
        return False

def add_imports_if_needed(file_path: str) -> bool:
    """Add necessary imports if they're missing."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        lines = content.split('\n')
        
        # Check if logger is imported
        has_logger = any('logger' in line and 'import' in line for line in lines[:50])
        
        if not has_logger:
            # Find where to insert the import
            import_idx = 0
            for i, line in enumerate(lines[:50]):
                if line.startswith('from ') or line.startswith('import '):
                    import_idx = i + 1
            
            # Check if there's already a get_logger import
            if 'from app.core.logger import get_logger' not in content:
                lines.insert(import_idx, 'from app.core.logger import get_logger')
                lines.insert(import_idx + 1, '')
                
                # Find where to initialize logger (after imports)
                for i in range(import_idx + 2, len(lines)):
                    if lines[i] and not lines[i].startswith(('import ', 'from ')):
                        lines.insert(i, 'logger = get_logger(__name__)')
                        lines.insert(i + 1, '')
                        break
                
                modified = True
                print(f"  Added logger import and initialization")
        
        if 'json' in str(CRITICAL_FILES.get(file_path, [])) and 'import json' not in content:
            # Add json import if needed
            for i, line in enumerate(lines[:30]):
                if line.startswith('import '):
                    lines.insert(i + 1, 'import json')
                    modified = True
                    print(f"  Added json import")
                    break
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return True
        
        return False
        
    except Exception as e:
        print(f"Error adding imports to {file_path}: {e}")
        return False

def main():
    """Main function to enhance exception handling."""
    print("Enhancing exception handling with proper logging...")
    print("-" * 60)
    
    total_enhanced = 0
    
    for file_path, line_info in CRITICAL_FILES.items():
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        
        print(f"\nProcessing {file_path}:")
        
        # First add imports if needed
        imports_added = add_imports_if_needed(file_path)
        
        # Then enhance exception handling
        enhanced = enhance_exception_handling(file_path, line_info)
        
        if enhanced or imports_added:
            total_enhanced += 1
            print(f"  [OK] Enhanced successfully")
        else:
            print(f"  - No changes needed")
    
    print(f"\n{'-' * 60}")
    print(f"Total files enhanced: {total_enhanced}")
    
    # Also create a verification script
    print("\nCreating verification script...")
    create_verification_script()

def create_verification_script():
    """Create a script to verify no bare except blocks remain."""
    script_content = '''#!/usr/bin/env python3
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
            if re.match(r'^\\s*except:\\s*$', line):
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
                            print("\\nFound bare except blocks:")
                            print("-" * 60)
                            found_any = True
                        
                        print(f"\\n{file_path}:")
                        for line_num, line in bare_excepts:
                            print(f"  Line {line_num}: {line}")
    
    if not found_any:
        print("[OK] No bare except blocks found in the codebase!")
        return 0
    else:
        print(f"\\n{'-' * 60}")
        print("[FAIL] Bare except blocks still exist!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    with open('backend/verify_no_bare_except.py', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("[OK] Created backend/verify_no_bare_except.py")

if __name__ == "__main__":
    main()