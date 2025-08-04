#!/usr/bin/env python3
"""
Quick script to fix the missing _get_secret function in config.py
Run this before deployment to fix the critical import issue.
"""

import os
import sys

def fix_config_file():
    """Add the missing _get_secret function to config.py"""
    
    config_path = os.path.join(os.path.dirname(__file__), 'app', 'core', 'config.py')
    
    # Read the current file
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Check if _get_secret is already defined
    if 'def _get_secret' in content:
        print("✓ _get_secret function already exists in config.py")
        return True
    
    # Find where to insert the function (after the imports, before the Settings class)
    insert_position = content.find('class Settings(BaseSettings):')
    if insert_position == -1:
        print("✗ Could not find Settings class in config.py")
        return False
    
    # Function to insert
    get_secret_function = '''
def _get_secret(secret_id: str) -> Optional[str]:
    """Get secret from Secret Manager or environment."""
    if secret_manager and hasattr(secret_manager, 'get_secret'):
        return secret_manager.get_secret(secret_id)
    # Fallback to environment variable
    env_key = secret_id.upper().replace('-', '_')
    return os.getenv(env_key)


'''
    
    # Insert the function
    new_content = content[:insert_position] + get_secret_function + content[insert_position:]
    
    # Write back
    with open(config_path, 'w') as f:
        f.write(new_content)
    
    print("✓ Added _get_secret function to config.py")
    return True


def fix_route_imports():
    """Fix database imports in route files"""
    
    routes_dir = os.path.join(os.path.dirname(__file__), 'app', 'routes')
    
    # Find all Python files in routes directory
    import glob
    route_files = glob.glob(os.path.join(routes_dir, '**', '*.py'), recursive=True)
    
    fixed_count = 0
    
    for route_file in route_files:
        try:
            with open(route_file, 'r') as f:
                content = f.read()
            
            # Check if file has the wrong import
            if 'from app.db.base import get_db' in content:
                # Replace with correct import
                new_content = content.replace(
                    'from app.db.base import get_db',
                    'from app.database import get_db'
                )
                
                with open(route_file, 'w') as f:
                    f.write(new_content)
                
                print(f"✓ Fixed import in {os.path.basename(route_file)}")
                fixed_count += 1
                
        except Exception as e:
            print(f"✗ Error processing {route_file}: {e}")
    
    print(f"\nFixed {fixed_count} import statements")
    return fixed_count > 0


def fix_duplicate_middleware():
    """Remove duplicate middleware registration in main.py"""
    
    main_path = os.path.join(os.path.dirname(__file__), 'app', 'main.py')
    
    try:
        with open(main_path, 'r') as f:
            lines = f.readlines()
        
        # Look for the duplicate line
        found_duplicate = False
        new_lines = []
        skip_next = False
        
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
                
            if 'performance_middleware = PerformanceOptimizationMiddleware(app)' in line:
                # Check if next line is the duplicate
                if i + 1 < len(lines) and 'app.add_middleware(PerformanceOptimizationMiddleware)' in lines[i + 1]:
                    found_duplicate = True
                    skip_next = True
                    new_lines.append(line)
                    print("✓ Found and removed duplicate PerformanceOptimizationMiddleware registration")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        if found_duplicate:
            with open(main_path, 'w') as f:
                f.writelines(new_lines)
            print("✓ Fixed main.py")
        else:
            print("✓ No duplicate middleware found in main.py (may already be fixed)")
            
        return True
        
    except Exception as e:
        print(f"✗ Error fixing main.py: {e}")
        return False


def main():
    """Run all fixes"""
    print("🔧 Running deployment fixes...\n")
    
    # Fix 1: Add missing _get_secret function
    print("1. Fixing missing _get_secret function...")
    fix_config_file()
    
    # Fix 2: Fix database imports
    print("\n2. Fixing database imports in routes...")
    fix_route_imports()
    
    # Fix 3: Fix duplicate middleware
    print("\n3. Fixing duplicate middleware...")
    fix_duplicate_middleware()
    
    print("\n✅ All fixes complete!")
    print("\n📝 Next steps:")
    print("1. Review the changes made")
    print("2. Test with: python -m uvicorn app.main_incremental:app --reload")
    print("3. Deploy using main_incremental.py instead of main.py")


if __name__ == "__main__":
    main()