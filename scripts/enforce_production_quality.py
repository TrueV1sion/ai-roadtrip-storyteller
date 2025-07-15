#!/usr/bin/env python3
"""
Production Quality Enforcement Script
Ensures no mock, test, or simulated code in production
"""
import os
import re
import sys
from pathlib import Path

# Patterns that indicate mock/test code
FORBIDDEN_PATTERNS = [
    r'mock_mode\s*=\s*True',
    r'USE_MOCK_APIS\s*=\s*[Tt]rue',
    r'TEST_MODE\s*=\s*["\']mock["\']',
    r'_get_mock_\w+',
    r'_mock_\w+',
    r'return\s+.*fake.*',
    r'return\s+.*dummy.*',
    r'return\s+.*test.*',
    r'hardcoded.*=.*40\.7128.*74\.0060',  # NYC coordinates
    r'hardcoded.*=.*37\.7749.*122\.4194',  # SF coordinates
    r'example\.com',
    r'test@example\.com',
    r'555-0\d{3}',  # Fake phone numbers
    r'MOCK_REDIS\s*=\s*[Tt]rue',
    r'MockDatabase',
    r'MockRedis',
    r'simulated',
    r'# FIXME.*production',
    r'# TODO.*production',
    r'dev-secret-key-change-in-production'
]

# Files to check
BACKEND_DIRS = [
    'backend/app/services',
    'backend/app/api',
    'backend/app/integrations',
    'backend/app/core',
    'backend/app/routes'
]

# Files to specifically check for production readiness
CRITICAL_FILES = [
    'backend/app/core/config.py',
    'backend/app/main.py',
    'backend/app/main_production.py',
    'backend/app/services/tts_service.py',
    'backend/app/integrations/open_table_client.py',
    'backend/app/integrations/recreation_gov_client.py',
    'backend/app/integrations/shell_recharge_client.py'
]

def check_file_for_mocks(filepath):
    """Check a single file for mock/test patterns"""
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        for i, line in enumerate(lines, 1):
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        'file': filepath,
                        'line': i,
                        'content': line.strip(),
                        'pattern': pattern
                    })
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return issues

def check_env_files():
    """Check environment files for production settings"""
    issues = []
    
    # Check .env for development settings
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            content = f.read()
            if 'ENVIRONMENT=development' in content:
                issues.append("ERROR: .env has ENVIRONMENT=development")
            if 'dev-secret-key-change-in-production' in content:
                issues.append("ERROR: .env has insecure development secret key")
            if 'USE_MOCK_APIS=true' in content.lower():
                issues.append("ERROR: .env has USE_MOCK_APIS=true")
    
    # Ensure .env.production exists and is correct
    if not os.path.exists('.env.production'):
        issues.append("ERROR: .env.production file missing")
    else:
        with open('.env.production', 'r') as f:
            content = f.read()
            required_settings = [
                'ENVIRONMENT=production',
                'USE_MOCK_APIS=false',
                'TEST_MODE=production',
                'MOCK_REDIS=false'
            ]
            for setting in required_settings:
                if setting not in content:
                    issues.append(f"ERROR: .env.production missing {setting}")
    
    return issues

def check_mobile_issues():
    """Check for known mobile app issues"""
    issues = []
    
    # Check for hardcoded location
    location_service = 'mobile/src/services/locationService.ts'
    if not os.path.exists(location_service):
        issues.append(f"CRITICAL: {location_service} is missing - GPS will be hardcoded to NYC")
    
    # Check for voice service issues
    voice_service = 'mobile/src/services/voiceService.ts'
    if os.path.exists(voice_service):
        with open(voice_service, 'r') as f:
            content = f.read()
            if 'backend' in content and 'STT' in content:
                issues.append(f"WARNING: {voice_service} may be using backend STT instead of native")
    
    return issues

def main():
    """Main enforcement function"""
    print("🔍 Production Quality Enforcement Check")
    print("=" * 50)
    
    all_issues = []
    
    # Check backend directories
    print("\n📁 Checking backend code for mock/test patterns...")
    for dir_path in BACKEND_DIRS:
        if os.path.exists(dir_path):
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.py'):
                        filepath = os.path.join(root, file)
                        issues = check_file_for_mocks(filepath)
                        all_issues.extend(issues)
    
    # Check critical files
    print("\n🎯 Checking critical files...")
    for filepath in CRITICAL_FILES:
        if os.path.exists(filepath):
            issues = check_file_for_mocks(filepath)
            all_issues.extend(issues)
    
    # Check environment configuration
    print("\n⚙️  Checking environment configuration...")
    env_issues = check_env_files()
    if env_issues:
        print("\n❌ Environment Configuration Issues:")
        for issue in env_issues:
            print(f"  - {issue}")
    
    # Check mobile issues
    print("\n📱 Checking mobile app issues...")
    mobile_issues = check_mobile_issues()
    if mobile_issues:
        print("\n⚠️  Mobile App Issues:")
        for issue in mobile_issues:
            print(f"  - {issue}")
    
    # Report findings
    if all_issues:
        print(f"\n❌ Found {len(all_issues)} mock/test patterns in production code:")
        for issue in all_issues[:10]:  # Show first 10
            print(f"\n  File: {issue['file']}:{issue['line']}")
            print(f"  Pattern: {issue['pattern']}")
            print(f"  Code: {issue['content']}")
        
        if len(all_issues) > 10:
            print(f"\n  ... and {len(all_issues) - 10} more issues")
        
        print("\n🚨 FAIL: Production code contains mock/test patterns!")
        print("   Fix these issues before deploying to production.")
        return 1
    else:
        print("\n✅ PASS: No mock/test patterns found in backend code")
    
    # Final recommendations
    print("\n📋 Final Production Checklist:")
    print("  1. [ ] All mock patterns removed from code")
    print("  2. [ ] Production environment variables set")
    print("  3. [ ] Mobile GPS location service implemented")
    print("  4. [ ] Google Cloud TTS connected")
    print("  5. [ ] All API keys in Secret Manager")
    print("  6. [ ] Cloud SQL and Memorystore created")
    print("  7. [ ] No hardcoded test data")
    print("  8. [ ] Production secrets generated")
    
    return 0 if not (all_issues or env_issues or mobile_issues) else 1

if __name__ == "__main__":
    sys.exit(main())