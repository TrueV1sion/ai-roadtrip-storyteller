#!/usr/bin/env python3
"""Fix hardcoded HTTP status codes to use fastapi.status constants."""

import os
import re
from pathlib import Path


def fix_http_status_codes():
    """Replace hardcoded HTTP status codes with fastapi.status constants."""
    routes_dir = Path("app/routes")
    
    # Common status code replacements
    status_replacements = [
        (r'HTTPException\(status_code=200\b', 'HTTPException(status_code=status.HTTP_200_OK'),
        (r'HTTPException\(status_code=201\b', 'HTTPException(status_code=status.HTTP_201_CREATED'),
        (r'HTTPException\(status_code=204\b', 'HTTPException(status_code=status.HTTP_204_NO_CONTENT'),
        (r'HTTPException\(status_code=400\b', 'HTTPException(status_code=status.HTTP_400_BAD_REQUEST'),
        (r'HTTPException\(status_code=401\b', 'HTTPException(status_code=status.HTTP_401_UNAUTHORIZED'),
        (r'HTTPException\(status_code=403\b', 'HTTPException(status_code=status.HTTP_403_FORBIDDEN'),
        (r'HTTPException\(status_code=404\b', 'HTTPException(status_code=status.HTTP_404_NOT_FOUND'),
        (r'HTTPException\(status_code=409\b', 'HTTPException(status_code=status.HTTP_409_CONFLICT'),
        (r'HTTPException\(status_code=422\b', 'HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY'),
        (r'HTTPException\(status_code=429\b', 'HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS'),
        (r'HTTPException\(status_code=500\b', 'HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR'),
        (r'HTTPException\(status_code=503\b', 'HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE'),
    ]
    
    fixed_files = []
    
    # Files that need status import added
    files_needing_import = [
        'api_documentation_enhanced.py',
        'api_keys.py', 
        'api_secured_example.py',
        'ar.py',
        'async_jobs.py'
    ]
    
    for file_path in routes_dir.rglob("*.py"):
        if file_path.name not in files_needing_import:
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply status code replacements
        for pattern, replacement in status_replacements:
            content = re.sub(pattern, replacement, content)
        
        # Add status import if needed and not already present
        if content != original_content and 'from fastapi import' in content and 'status' not in content:
            # Find the fastapi import line and add status
            content = re.sub(
                r'(from fastapi import .*?)(\n)',
                lambda m: m.group(1) + (', status' if ', status' not in m.group(1) and ' status' not in m.group(1) else '') + m.group(2),
                content,
                count=1
            )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            fixed_files.append(str(file_path))
            print(f"Fixed status codes in: {file_path}")
    
    return fixed_files


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    fixed = fix_http_status_codes()
    
    if fixed:
        print(f"\nFixed {len(fixed)} files")
    else:
        print("No files needed fixing.")