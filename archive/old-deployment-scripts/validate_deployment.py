#!/usr/bin/env python3
"""
Validate deployment readiness
Checks that all requirements are met before deploying to production
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class DeploymentValidator:
    """Validate deployment readiness"""
    
    def __init__(self, environment: str, version: str):
        self.environment = environment
        self.version = version
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.project_root = Path(__file__).parent.parent
        
    def validate_all(self) -> bool:
        """Run all validation checks"""
        print(f"Validating deployment for {self.environment} environment (version: {self.version})")
        print("=" * 60)
        
        # Run all checks
        self.check_version_format()
        self.check_environment_files()
        self.check_docker_build()
        self.check_database_migrations()
        self.check_test_coverage()
        self.check_security_scan()
        self.check_dependencies()
        self.check_feature_flags()
        
        # Print results
        self.print_results()
        
        # Return success if no errors
        return len(self.errors) == 0
    
    def check_version_format(self):
        """Validate version format"""
        print("Checking version format...")
        
        # Should be in format v1.2.3
        import re
        pattern = r'^v?\d+\.\d+\.\d+(-\w+)?$'
        
        if re.match(pattern, self.version):
            print("✓ Version format is valid")
        else:
            self.errors.append(f"Invalid version format: {self.version}. Expected format: v1.2.3")
    
    def check_environment_files(self):
        """Check required environment files exist"""
        print("\nChecking environment files...")
        
        required_files = {
            "production": [
                ".env.production",
                "app.production.json",
                ".github/workflows/deploy-production-cloudrun.yml"
            ],
            "staging": [
                ".env.staging",
                ".github/workflows/deploy-staging.yml"
            ]
        }
        
        files_to_check = required_files.get(self.environment, required_files["production"])
        
        for file_path in files_to_check:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"✓ {file_path} exists")
            else:
                self.errors.append(f"Missing required file: {file_path}")
    
    def check_docker_build(self):
        """Validate Docker build"""
        print("\nChecking Docker configuration...")
        
        dockerfile = self.project_root / "Dockerfile"
        if not dockerfile.exists():
            self.errors.append("Dockerfile not found")
            return
            
        # Check for production optimizations
        with open(dockerfile) as f:
            content = f.read()
            
        checks = {
            "Multi-stage build": "FROM .* AS",
            "Non-root user": "USER (?!root)",
            "Health check": "HEALTHCHECK",
            "Security updates": "apt-get update.*&&.*apt-get upgrade"
        }
        
        for check_name, pattern in checks.items():
            import re
            if re.search(pattern, content, re.IGNORECASE):
                print(f"✓ {check_name} configured")
            else:
                self.warnings.append(f"Docker: {check_name} not found")
    
    def check_database_migrations(self):
        """Check database migrations are up to date"""
        print("\nChecking database migrations...")
        
        try:
            # Check if there are pending migrations
            result = subprocess.run(
                ["alembic", "check"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✓ Database migrations are up to date")
            else:
                self.warnings.append("Database migrations may need to be generated")
                
        except Exception as e:
            self.warnings.append(f"Could not check migrations: {e}")
    
    def check_test_coverage(self):
        """Verify test coverage meets requirements"""
        print("\nChecking test coverage...")
        
        coverage_file = self.project_root / "coverage.json"
        
        if coverage_file.exists():
            with open(coverage_file) as f:
                data = json.load(f)
                
            total_coverage = data.get("totals", {}).get("percent_covered", 0)
            
            if total_coverage >= 80:
                print(f"✓ Test coverage is {total_coverage:.1f}% (requirement: 80%)")
            else:
                self.errors.append(f"Test coverage is {total_coverage:.1f}% (requirement: 80%)")
        else:
            self.warnings.append("Coverage report not found. Run tests first.")
    
    def check_security_scan(self):
        """Run basic security checks"""
        print("\nChecking security...")
        
        # Check for common security issues
        security_checks = [
            ("No hardcoded secrets", ["grep", "-r", "password.*=.*['\"]", "backend/", "--include=*.py"]),
            ("No debug mode in production", ["grep", "-r", "DEBUG.*=.*True", "backend/", "--include=*.py"]),
        ]
        
        for check_name, command in security_checks:
            try:
                result = subprocess.run(
                    command,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0 or not result.stdout:
                    print(f"✓ {check_name}")
                else:
                    self.warnings.append(f"Security: {check_name} - found potential issues")
                    
            except Exception:
                pass
    
    def check_dependencies(self):
        """Check for dependency issues"""
        print("\nChecking dependencies...")
        
        # Check for outdated dependencies
        requirements_file = self.project_root / "requirements.txt"
        
        if requirements_file.exists():
            print("✓ requirements.txt exists")
            
            # Check for security vulnerabilities
            try:
                result = subprocess.run(
                    ["safety", "check", "--json"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print("✓ No known security vulnerabilities in dependencies")
                else:
                    vulnerabilities = json.loads(result.stdout)
                    if vulnerabilities:
                        self.warnings.append(f"Found {len(vulnerabilities)} dependency vulnerabilities")
                        
            except Exception:
                self.warnings.append("Could not run safety check")
        else:
            self.errors.append("requirements.txt not found")
    
    def check_feature_flags(self):
        """Verify feature flags are configured correctly"""
        print("\nChecking feature flags...")
        
        if self.environment == "production":
            # Check production feature flags
            env_file = self.project_root / ".env.production"
            
            if env_file.exists():
                with open(env_file) as f:
                    content = f.read()
                    
                critical_flags = [
                    "FEATURE_2FA=true",
                    "DEBUG=false",
                    "RATE_LIMIT_ENABLED=true"
                ]
                
                for flag in critical_flags:
                    if flag in content:
                        print(f"✓ {flag}")
                    else:
                        self.warnings.append(f"Feature flag not found: {flag}")
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        
        if self.errors:
            print("\n❌ ERRORS (must fix before deployment):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS (should review):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All checks passed!")
        elif not self.errors:
            print("\n✅ No blocking errors found. Review warnings before proceeding.")
        else:
            print("\n❌ Deployment validation FAILED")


def main():
    parser = argparse.ArgumentParser(description="Validate deployment readiness")
    parser.add_argument("--environment", required=True, choices=["production", "staging", "development"])
    parser.add_argument("--version", required=True, help="Version being deployed")
    
    args = parser.parse_args()
    
    validator = DeploymentValidator(args.environment, args.version)
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()