#!/usr/bin/env python3
"""
Update the application to use the secure JWT manager with Secret Manager integration.
This script updates imports and ensures backward compatibility.
"""
import os
import re
from pathlib import Path
import argparse


def update_imports_in_file(file_path: Path, dry_run: bool = False):
    """Update JWT imports in a single file."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: Direct jwt_manager imports
    pattern1 = r'from app\.core\.jwt_manager import (\w+)'
    replacement1 = r'from app.core.jwt_secret_manager import \1'
    
    if re.search(pattern1, content):
        content = re.sub(pattern1, replacement1, content)
        changes.append("Updated jwt_manager imports")
    
    # Pattern 2: Import of jwt_manager module
    pattern2 = r'from app\.core import jwt_manager'
    replacement2 = r'from app.core import jwt_secret_manager as jwt_manager'
    
    if re.search(pattern2, content):
        content = re.sub(pattern2, replacement2, content)
        changes.append("Updated jwt_manager module import")
    
    # Pattern 3: jwt_manager.method() calls
    pattern3 = r'jwt_manager\.(\w+)'
    replacement3 = r'secure_jwt_manager.\1'
    
    # Only update if we've imported the module
    if 'jwt_secret_manager' in content and re.search(pattern3, content):
        content = re.sub(pattern3, replacement3, content)
        changes.append("Updated jwt_manager method calls")
    
    if content != original_content:
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return True, changes
    
    return False, []


def find_files_with_jwt_imports(root_dir: Path):
    """Find all Python files that import jwt_manager."""
    files = []
    
    for file_path in root_dir.rglob('*.py'):
        # Skip migration scripts and the jwt modules themselves
        if 'jwt_manager.py' in str(file_path) or 'jwt_secret_manager.py' in str(file_path):
            continue
            
        if 'scripts/security' in str(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'jwt_manager' in content:
                files.append(file_path)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return files


def main():
    parser = argparse.ArgumentParser(description='Update to secure JWT manager')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be changed without making changes')
    parser.add_argument('--backend-dir', default='backend', 
                       help='Path to backend directory')
    
    args = parser.parse_args()
    
    backend_dir = Path(args.backend_dir)
    if not backend_dir.exists():
        print(f"Backend directory not found: {backend_dir}")
        return
    
    print("Searching for files with JWT imports...")
    files = find_files_with_jwt_imports(backend_dir)
    
    if not files:
        print("No files found with jwt_manager imports")
        return
    
    print(f"\nFound {len(files)} files with JWT imports:")
    
    updated_count = 0
    for file_path in files:
        relative_path = file_path.relative_to(backend_dir)
        updated, changes = update_imports_in_file(file_path, args.dry_run)
        
        if updated:
            updated_count += 1
            print(f"\n✓ {relative_path}")
            for change in changes:
                print(f"  - {change}")
        else:
            print(f"\n- {relative_path} (no changes needed)")
    
    if args.dry_run:
        print(f"\nDry run complete. Would update {updated_count} files.")
        print("Run without --dry-run to apply changes.")
    else:
        print(f"\n✅ Updated {updated_count} files to use secure JWT manager")
        
        if updated_count > 0:
            print("\nNext steps:")
            print("1. Run tests to ensure everything works")
            print("2. Generate or migrate JWT keys to Secret Manager")
            print("3. Deploy to staging for testing")
            print("4. Monitor logs for any JWT-related errors")


if __name__ == "__main__":
    main()