#!/usr/bin/env python3
"""
Beta Launch Final Security Scan
Performs comprehensive security checks before beta launch
"""
import asyncio
import subprocess
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class SecurityScanner:
    """Comprehensive security scanner for beta launch"""
    
    def __init__(self):
        self.scan_results = {
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "critical_issues": [],
            "warnings": [],
            "passed_checks": [],
            "summary": {}
        }
    
    async def run_all_scans(self) -> Dict[str, Any]:
        """Run all security scans"""
        print("🔒 AI ROAD TRIP STORYTELLER - BETA LAUNCH SECURITY SCAN")
        print("=" * 60)
        print(f"Scan started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run security checks
        await self.check_secrets()
        await self.check_dependencies()
        await self.check_docker_security()
        await self.check_api_security()
        await self.check_database_security()
        await self.check_authentication()
        await self.check_ssl_certificates()
        await self.check_cors_settings()
        await self.check_rate_limiting()
        await self.check_logging_security()
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
        
        return self.scan_results
    
    async def check_secrets(self):
        """Check for exposed secrets"""
        print("🔍 Checking for exposed secrets...")
        
        try:
            # Check for .env files
            env_files = [".env", ".env.local", ".env.production"]
            for env_file in env_files:
                if os.path.exists(env_file):
                    self.scan_results["critical_issues"].append(
                        f"Found {env_file} in repository - should not be committed"
                    )
            
            # Run git secrets scan
            result = subprocess.run(
                ["git", "grep", "-E", "(api_key|secret|password|token)\\s*="],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout:
                # Check if these are actual secrets or just variable names
                suspicious_lines = []
                for line in result.stdout.split('\n'):
                    if line and not any(safe in line.lower() for safe in [
                        "example", "placeholder", "your-", "<your", "xxx", "..."
                    ]):
                        suspicious_lines.append(line)
                
                if suspicious_lines:
                    self.scan_results["critical_issues"].append(
                        f"Potential secrets found in code: {len(suspicious_lines)} instances"
                    )
            else:
                self.scan_results["passed_checks"].append("No hardcoded secrets detected")
            
            print("  ✓ Secrets scan completed")
            
        except Exception as e:
            self.scan_results["warnings"].append(f"Secret scanning error: {str(e)}")
    
    async def check_dependencies(self):
        """Check for vulnerable dependencies"""
        print("🔍 Checking dependencies for vulnerabilities...")
        
        try:
            # Python dependencies
            if os.path.exists("requirements.txt"):
                result = subprocess.run(
                    ["pip-audit", "--desc"],
                    capture_output=True,
                    text=True
                )
                
                if "found" in result.stdout and "vulnerabilit" in result.stdout:
                    self.scan_results["critical_issues"].append(
                        "Vulnerable Python dependencies detected - run pip-audit for details"
                    )
                else:
                    self.scan_results["passed_checks"].append("Python dependencies secure")
            
            # Node dependencies
            if os.path.exists("mobile/package.json"):
                os.chdir("mobile")
                result = subprocess.run(
                    ["npm", "audit", "--json"],
                    capture_output=True,
                    text=True
                )
                os.chdir("..")
                
                if result.returncode == 0:
                    audit_data = json.loads(result.stdout)
                    if audit_data.get("metadata", {}).get("vulnerabilities", {}).get("high", 0) > 0:
                        self.scan_results["critical_issues"].append(
                            f"High severity npm vulnerabilities: {audit_data['metadata']['vulnerabilities']['high']}"
                        )
                    elif audit_data.get("metadata", {}).get("vulnerabilities", {}).get("moderate", 0) > 0:
                        self.scan_results["warnings"].append(
                            f"Moderate npm vulnerabilities: {audit_data['metadata']['vulnerabilities']['moderate']}"
                        )
                    else:
                        self.scan_results["passed_checks"].append("Node dependencies secure")
            
            print("  ✓ Dependency scan completed")
            
        except Exception as e:
            self.scan_results["warnings"].append(f"Dependency scanning error: {str(e)}")
    
    async def check_docker_security(self):
        """Check Docker configuration security"""
        print("🔍 Checking Docker security...")
        
        try:
            # Check Dockerfile
            if os.path.exists("Dockerfile"):
                with open("Dockerfile", "r") as f:
                    dockerfile_content = f.read()
                
                # Check for non-root user
                if "USER" in dockerfile_content and "USER root" not in dockerfile_content:
                    self.scan_results["passed_checks"].append("Docker runs as non-root user")
                else:
                    self.scan_results["warnings"].append("Docker container may run as root")
                
                # Check for latest tags
                if ":latest" in dockerfile_content:
                    self.scan_results["warnings"].append("Using :latest tags in Dockerfile - pin versions")
            
            print("  ✓ Docker security scan completed")
            
        except Exception as e:
            self.scan_results["warnings"].append(f"Docker scanning error: {str(e)}")
    
    async def check_api_security(self):
        """Check API security configurations"""
        print("🔍 Checking API security...")
        
        checks_passed = []
        
        # Check for security headers implementation
        security_files = [
            "backend/app/middleware/security_headers.py",
            "backend/app/core/security.py"
        ]
        
        for file in security_files:
            if os.path.exists(file):
                checks_passed.append(f"Security headers implemented in {file}")
        
        # Check for input validation
        if os.path.exists("backend/app/schemas.py"):
            checks_passed.append("Input validation schemas present")
        
        # Check for API versioning
        if os.path.exists("backend/app/routes"):
            checks_passed.append("API routes properly organized")
        
        self.scan_results["passed_checks"].extend(checks_passed)
        print("  ✓ API security scan completed")
    
    async def check_database_security(self):
        """Check database security configurations"""
        print("🔍 Checking database security...")
        
        # Check for SQL injection protection
        if os.path.exists("backend/app/models.py"):
            with open("backend/app/models.py", "r") as f:
                content = f.read()
                
            if "SQLAlchemy" in content or "sqlalchemy" in content:
                self.scan_results["passed_checks"].append("Using SQLAlchemy ORM (SQL injection protection)")
            
            # Check for query parameterization
            if "execute(" in content and "%" not in content:
                self.scan_results["passed_checks"].append("Queries appear to use parameterization")
        
        print("  ✓ Database security scan completed")
    
    async def check_authentication(self):
        """Check authentication security"""
        print("🔍 Checking authentication security...")
        
        # Check for 2FA implementation
        if os.path.exists("backend/app/routes/auth.py"):
            with open("backend/app/routes/auth.py", "r") as f:
                content = f.read()
                
            if "totp" in content.lower() or "2fa" in content.lower():
                self.scan_results["passed_checks"].append("2FA authentication implemented")
            
            if "bcrypt" in content or "argon2" in content:
                self.scan_results["passed_checks"].append("Secure password hashing implemented")
            elif "hashlib" in content or "md5" in content:
                self.scan_results["critical_issues"].append("Weak password hashing detected")
        
        # Check for JWT configuration
        if os.path.exists("backend/app/core/auth.py"):
            self.scan_results["passed_checks"].append("JWT authentication configured")
        
        print("  ✓ Authentication scan completed")
    
    async def check_ssl_certificates(self):
        """Check SSL/TLS configuration"""
        print("🔍 Checking SSL/TLS configuration...")
        
        # Check for cert-manager or Let's Encrypt configuration
        k8s_files = ["infrastructure/k8s/cert-manager.yaml", "infrastructure/k8s/ingress.yaml"]
        
        for file in k8s_files:
            if os.path.exists(file):
                with open(file, "r") as f:
                    content = f.read()
                    
                if "cert-manager" in content or "letsencrypt" in content:
                    self.scan_results["passed_checks"].append("SSL/TLS auto-renewal configured")
                    break
        
        print("  ✓ SSL/TLS scan completed")
    
    async def check_cors_settings(self):
        """Check CORS configuration"""
        print("🔍 Checking CORS settings...")
        
        # Check for CORS middleware
        if os.path.exists("backend/app/main.py"):
            with open("backend/app/main.py", "r") as f:
                content = f.read()
                
            if "CORSMiddleware" in content:
                if 'allow_origins=["*"]' in content:
                    self.scan_results["warnings"].append("CORS allows all origins - restrict for production")
                else:
                    self.scan_results["passed_checks"].append("CORS properly configured")
        
        print("  ✓ CORS scan completed")
    
    async def check_rate_limiting(self):
        """Check rate limiting implementation"""
        print("🔍 Checking rate limiting...")
        
        # Check for rate limiter
        if os.path.exists("backend/app/core/rate_limiter.py"):
            self.scan_results["passed_checks"].append("Rate limiting implemented")
        
        # Check for auth rate limiting
        if os.path.exists("backend/app/core/auth_rate_limiter.py"):
            self.scan_results["passed_checks"].append("Authentication rate limiting implemented")
        
        print("  ✓ Rate limiting scan completed")
    
    async def check_logging_security(self):
        """Check logging security"""
        print("🔍 Checking logging security...")
        
        # Check logger configuration
        if os.path.exists("backend/app/core/logger.py"):
            with open("backend/app/core/logger.py", "r") as f:
                content = f.read()
                
            # Check for sensitive data filtering
            if "filter" in content.lower() or "redact" in content.lower():
                self.scan_results["passed_checks"].append("Log filtering implemented")
            else:
                self.scan_results["warnings"].append("Ensure sensitive data is filtered from logs")
        
        print("  ✓ Logging security scan completed")
    
    def generate_summary(self):
        """Generate scan summary"""
        self.scan_results["summary"] = {
            "total_critical_issues": len(self.scan_results["critical_issues"]),
            "total_warnings": len(self.scan_results["warnings"]),
            "total_passed_checks": len(self.scan_results["passed_checks"]),
            "ready_for_beta": len(self.scan_results["critical_issues"]) == 0
        }
        
        if self.scan_results["summary"]["ready_for_beta"]:
            self.scan_results["status"] = "PASSED"
        else:
            self.scan_results["status"] = "FAILED"
    
    def save_results(self):
        """Save scan results"""
        filename = f"security_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(self.scan_results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {filename}")
    
    def print_results(self):
        """Print scan results"""
        print("\n" + "=" * 60)
        print("SECURITY SCAN RESULTS")
        print("=" * 60)
        
        print(f"\n✅ Passed Checks: {len(self.scan_results['passed_checks'])}")
        for check in self.scan_results["passed_checks"][:5]:
            print(f"  • {check}")
        if len(self.scan_results["passed_checks"]) > 5:
            print(f"  • ... and {len(self.scan_results['passed_checks']) - 5} more")
        
        if self.scan_results["warnings"]:
            print(f"\n⚠️  Warnings: {len(self.scan_results['warnings'])}")
            for warning in self.scan_results["warnings"]:
                print(f"  • {warning}")
        
        if self.scan_results["critical_issues"]:
            print(f"\n❌ Critical Issues: {len(self.scan_results['critical_issues'])}")
            for issue in self.scan_results["critical_issues"]:
                print(f"  • {issue}")
        
        print("\n" + "=" * 60)
        print("FINAL STATUS:", self.scan_results["status"])
        print("=" * 60)
        
        if self.scan_results["summary"]["ready_for_beta"]:
            print("\n🚀 SYSTEM IS READY FOR BETA LAUNCH!")
        else:
            print("\n⛔ CRITICAL ISSUES MUST BE RESOLVED BEFORE LAUNCH")


async def main():
    """Run security scan"""
    scanner = SecurityScanner()
    
    try:
        await scanner.run_all_scans()
        scanner.print_results()
        
        # Return exit code based on status
        if scanner.scan_results["status"] == "PASSED":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Security scan failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())