#\!/usr/bin/env python3
"""
Script to fix all incorrect imports in the backend.
"""
import os
import re

def main():
    fixed_count = 0
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ["venv", "__pycache__", ".git", ".pytest_cache"]]
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    original = content
                    content = re.sub(r"from backend\.app\.", "from app.", content)
                    content = re.sub(r"import backend\.app\.", "import app.", content)
                    if content \!= original:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"Fixed: {filepath}")
                        fixed_count += 1
                except Exception as e:
                    pass
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()
