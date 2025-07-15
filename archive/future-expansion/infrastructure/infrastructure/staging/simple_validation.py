#!/usr/bin/env python3
"""
Simple Staging Environment Validation
Basic validation without external dependencies
"""

import subprocess
import sys
import json
from datetime import datetime

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "info": "\033[0;34m",
        "success": "\033[0;32m", 
        "warning": "\033[1;33m",
        "error": "\033[0;31m"
    }
    reset = "\033[0m"
    color = colors.get(status, "")
    print(f"{color}[{status.upper()}]{reset} {message}")

def test_gcloud_access():
    """Test gcloud access and authentication"""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return True, f"Authenticated as: {result.stdout.strip()}"
        return False, "No active gcloud authentication"
    except Exception as e:
        return False, str(e)

def test_project_access():
    """Test project access"""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            project = result.stdout.strip()
            if project == "roadtrip-460720":
                return True, f"Connected to project: {project}"
            return False, f"Wrong project: {project} (expected: roadtrip-460720)"
        return False, "Cannot get project information"
    except Exception as e:
        return False, str(e)

def test_apis_enabled():
    """Test required APIs are enabled"""
    required_apis = [
        "run.googleapis.com",
        "secretmanager.googleapis.com", 
        "sqladmin.googleapis.com",
        "redis.googleapis.com"
    ]
    
    enabled_count = 0
    for api in required_apis:
        try:
            result = subprocess.run(
                ["gcloud", "services", "list", "--enabled", f"--filter=name:{api}", "--format=value(name)"],
                capture_output=True,
                text=True
            )
            if api in result.stdout:
                enabled_count += 1
        except:
            pass
    
    if enabled_count == len(required_apis):
        return True, f"All {len(required_apis)} required APIs enabled"
    return False, f"Only {enabled_count}/{len(required_apis)} APIs enabled"

def test_secrets_exist():
    """Test staging secrets exist"""
    staging_secrets = [
        "ENVIRONMENT-staging",
        "SECRET_KEY-staging", 
        "JWT_SECRET_KEY-staging"
    ]
    
    found_count = 0
    for secret in staging_secrets:
        try:
            result = subprocess.run(
                ["gcloud", "secrets", "describe", secret],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                found_count += 1
        except:
            pass
    
    if found_count == len(staging_secrets):
        return True, f"All {len(staging_secrets)} staging secrets found"
    return False, f"Only {found_count}/{len(staging_secrets)} secrets found"

def test_terraform_init():
    """Test terraform initialization"""
    try:
        # Check if terraform is available
        result = subprocess.run(
            ["terraform", "version"],
            capture_output=True,
            text=True,
            cwd="."
        )
        if result.returncode != 0:
            return False, "Terraform not available"
            
        # Test terraform init
        result = subprocess.run(
            ["terraform", "init", "-upgrade"],
            capture_output=True,
            text=True,
            cwd="."
        )
        if result.returncode == 0:
            return True, "Terraform initialization successful"
        return False, f"Terraform init failed: {result.stderr}"
    except Exception as e:
        return False, str(e)

def run_all_tests():
    """Run all validation tests"""
    print_status("🚀 Starting Simple Staging Validation", "info")
    print_status(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")
    print("")
    
    tests = [
        ("GCloud Authentication", test_gcloud_access),
        ("Project Access", test_project_access), 
        ("Required APIs", test_apis_enabled),
        ("Staging Secrets", test_secrets_exist),
        ("Terraform Init", test_terraform_init)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print_status(f"Testing: {test_name}", "info")
        try:
            success, message = test_func()
            if success:
                print_status(f"✅ {test_name}: {message}", "success")
                passed += 1
            else:
                print_status(f"❌ {test_name}: {message}", "error")
                failed += 1
        except Exception as e:
            print_status(f"❌ {test_name}: Exception - {str(e)}", "error")
            failed += 1
        print("")
    
    # Summary
    print_status("=" * 50, "info")
    print_status("VALIDATION SUMMARY", "info")
    print_status("=" * 50, "info")
    print("")
    print_status(f"✅ Passed: {passed}", "success")
    print_status(f"❌ Failed: {failed}", "error")
    print_status(f"📊 Total: {passed + failed}", "info")
    print("")
    
    if failed == 0:
        print_status("🎉 ALL TESTS PASSED! Staging environment is ready for deployment.", "success")
        return True
    else:
        print_status(f"⚠️  {failed} tests failed. Please address issues before proceeding.", "warning")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)