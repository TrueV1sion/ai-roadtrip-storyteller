#!/usr/bin/env python3
"""Fix all database import inconsistencies in route files."""

import os
import re
from pathlib import Path


def fix_database_imports():
    """Standardize all database imports to use 'from app.database import get_db'."""
    routes_dir = Path("app/routes")
    
    # Patterns to match various incorrect imports
    patterns = [
        (r"from app\.db\.base import get_db", "from app.database import get_db"),
        (r"from app\.core\.database_manager import get_db", "from app.database import get_db"),
        (r"from app\.db\.base import get_db # Or your actual path to get_db", "from app.database import get_db"),
        # Also fix the multi-import line
        (r"from app\.database import get_db, get_database_health, get_database_info, check_database_migrations",
         "from app.database import get_db, get_database_health, get_database_info, check_database_migrations")
    ]
    
    fixed_files = []
    
    # Process all Python files in routes directory (including subdirectories)
    for file_path in routes_dir.rglob("*.py"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        for old_pattern, new_import in patterns:
            content = re.sub(old_pattern, new_import, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            fixed_files.append(str(file_path))
            print(f"Fixed import in: {file_path}")
    
    if fixed_files:
        print(f"\nFixed {len(fixed_files)} files")
    else:
        print("No files needed fixing.")
    
    return fixed_files


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    fixed = fix_database_imports()
    
    # Show summary
    if fixed:
        print("\nFixed files:")
        for f in sorted(fixed):
            print(f"  - {f}")