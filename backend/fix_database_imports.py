#!/usr/bin/env python3
"""Fix database import inconsistencies in route files."""

import os
import re
from pathlib import Path


def fix_database_imports():
    """Replace all instances of 'from app.db.base import get_db' with 'from app.database import get_db'."""
    routes_dir = Path("backend/app/routes")
    
    # Pattern to match the incorrect import
    old_import = r"from app\.db\.base import get_db"
    new_import = "from app.database import get_db"
    
    fixed_files = []
    
    for file_path in routes_dir.glob("*.py"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if re.search(old_import, content):
            # Replace the import
            new_content = re.sub(old_import, new_import, content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            fixed_files.append(file_path.name)
            print(f"Fixed import in: {file_path.name}")
    
    if fixed_files:
        print(f"\nFixed {len(fixed_files)} files:")
        for file in fixed_files:
            print(f"  - {file}")
    else:
        print("No files needed fixing.")


if __name__ == "__main__":
    fix_database_imports()