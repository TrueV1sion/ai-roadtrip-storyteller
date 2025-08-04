#!/usr/bin/env python3
"""
Check for dependency conflicts in requirements.txt
"""

import subprocess
import sys
import tempfile
import os

def check_dependency_resolution():
    """Test if pip can resolve all dependencies without conflicts."""
    print("🔍 Checking for dependency conflicts...\n")
    
    # Create a temporary virtual environment
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = os.path.join(tmpdir, "test_venv")
        
        print("📦 Creating temporary virtual environment...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", venv_path],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
        
        # Get pip path in virtual environment
        if sys.platform == "win32":
            pip_path = os.path.join(venv_path, "Scripts", "pip")
        else:
            pip_path = os.path.join(venv_path, "bin", "pip")
        
        # Upgrade pip first
        print("📦 Upgrading pip...")
        try:
            subprocess.run(
                [pip_path, "install", "--upgrade", "pip"],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to upgrade pip: {e}")
            return False
        
        # Test dependency resolution with dry run
        print("📦 Testing dependency resolution (dry run)...")
        try:
            result = subprocess.run(
                [pip_path, "install", "--dry-run", "-r", "requirements.txt"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("❌ Dependency resolution failed!")
                print("\nError output:")
                print(result.stderr)
                return False
            
            print("✅ All dependencies can be resolved without conflicts!")
            
            # Show what would be installed
            print("\n📋 Dependencies that would be installed:")
            lines = result.stdout.split('\n')
            for line in lines:
                if "Would install" in line or "Successfully installed" in line:
                    print(f"  {line.strip()}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Dependency check failed: {e}")
            if e.stderr:
                print("\nError details:")
                print(e.stderr)
            return False

def check_security_vulnerabilities():
    """Check for known security vulnerabilities."""
    print("\n🔒 Checking for security vulnerabilities...")
    
    # Key security updates we've made
    security_checks = [
        ("aiohttp", "3.9.3", "CVE-2024-23334"),
    ]
    
    with open("requirements.txt", "r") as f:
        requirements = f.read()
    
    all_secure = True
    for package, min_version, cve in security_checks:
        if f"{package}=={min_version}" in requirements:
            print(f"✅ {package} updated to {min_version} (fixes {cve})")
        else:
            print(f"⚠️  {package} may need update to {min_version} (fixes {cve})")
            all_secure = False
    
    return all_secure

def main():
    """Run all dependency checks."""
    print("🚀 AI Road Trip Storyteller - Dependency Check\n")
    
    # Change to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found!")
        sys.exit(1)
    
    # Run checks
    resolution_ok = check_dependency_resolution()
    security_ok = check_security_vulnerabilities()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print("=" * 60)
    print(f"Dependency Resolution: {'✅ PASS' if resolution_ok else '❌ FAIL'}")
    print(f"Security Check: {'✅ PASS' if security_ok else '⚠️  NEEDS ATTENTION'}")
    
    if resolution_ok and security_ok:
        print("\n✅ All checks passed! Ready for deployment.")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()