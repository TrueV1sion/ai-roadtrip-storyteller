#!/usr/bin/env python3
"""
Validate credential security for production deployment
Ensures all credentials are properly secured and no sensitive data is exposed
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime

# Patterns that indicate security issues
SECURITY_PATTERNS = {
    "google_api_key": r"AIzaSy[0-9A-Za-z\-_]{33}",
    "generic_api_key": r"['\"]?[A-Za-z0-9]{32}['\"]?",
    "base64_secret": r"[A-Za-z0-9+/]{40,}={0,2}",
    "jwt_token": r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    "database_url": r"(postgres|postgresql|mysql|mongodb)://[^:]+:[^@]+@",
    "redis_url": r"redis://[^:]+:[^@]+@",
    "private_key": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"[0-9A-Za-z/+=]{40}",
    "github_token": r"gh[ps]_[A-Za-z0-9]{36}",
    "slack_token": r"xox[bp]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,34}",
    "stripe_key": r"(sk|pk)_(test|live)_[0-9A-Za-z]{24,99}"
}

# Files/directories to exclude from scanning
EXCLUDE_PATTERNS = {
    "node_modules",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "*.pyc",
    "*.log",
    "*.min.js",
    "coverage",
    "dist",
    "build"
}

# Known exposed credentials that should be rotated
KNOWN_EXPOSED = {
    "AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ": "Google Maps API Key",
    "5X13jI3ZPzAdU3kp3trYFf4VWqSVySgo": "Ticketmaster API Key",
    "d7aa0dc75ed0dae38f627ed48d3e3bf1": "OpenWeatherMap API Key"
}

class SecurityValidator:
    """Validates credential security across the codebase"""
    
    def __init__(self, project_path: Path = Path(".")):
        self.project_path = project_path
        self.findings: List[Dict] = []
        self.validated_secrets: Set[str] = set()
        
    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for security issues"""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Check each line
            for line_num, line in enumerate(content.splitlines(), 1):
                # Skip comments and empty lines
                if line.strip().startswith(('#', '//', '/*', '*')) or not line.strip():
                    continue
                
                # Check for known exposed credentials
                for exposed_value, description in KNOWN_EXPOSED.items():
                    if exposed_value in line:
                        findings.append({
                            "file": str(file_path),
                            "line": line_num,
                            "type": "CRITICAL - Known Exposed Credential",
                            "description": description,
                            "content": line.strip()[:100] + "..." if len(line) > 100 else line.strip()
                        })
                
                # Check for security patterns
                for pattern_name, pattern in SECURITY_PATTERNS.items():
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        # Skip if it's in a comment or looks like a placeholder
                        if any(placeholder in line.lower() for placeholder in 
                               ['example', 'placeholder', 'your-', 'xxx', '...', 'demo', 'test']):
                            continue
                        
                        findings.append({
                            "file": str(file_path),
                            "line": line_num,
                            "type": pattern_name,
                            "description": f"Potential {pattern_name.replace('_', ' ')}",
                            "content": line.strip()[:100] + "..." if len(line) > 100 else line.strip(),
                            "match": match.group()[:20] + "..." if len(match.group()) > 20 else match.group()
                        })
                        
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            
        return findings
    
    def should_scan_file(self, file_path: Path) -> bool:
        """Check if a file should be scanned"""
        # Skip excluded patterns
        for pattern in EXCLUDE_PATTERNS:
            if pattern in str(file_path):
                return False
        
        # Only scan certain file types
        valid_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', 
                          '.yml', '.env', '.sh', '.sql', '.tf', '.md', '.txt'}
        
        return file_path.suffix in valid_extensions or file_path.name.startswith('.')
    
    def scan_codebase(self) -> None:
        """Scan entire codebase for security issues"""
        print("Scanning codebase for credential security issues...")
        
        for file_path in self.project_path.rglob('*'):
            if file_path.is_file() and self.should_scan_file(file_path):
                findings = self.scan_file(file_path)
                self.findings.extend(findings)
        
        print(f"Scanned {len(self.findings)} potential security issues")
    
    def check_secret_manager_integration(self) -> Dict[str, bool]:
        """Verify Secret Manager is properly integrated"""
        print("\nChecking Secret Manager integration...")
        
        checks = {
            "secret_manager_imported": False,
            "config_uses_secret_manager": False,
            "no_hardcoded_secrets": True,
            "proper_error_handling": False,
            "secret_caching": False
        }
        
        # Check for secret manager imports
        config_file = self.project_path / "backend/app/core/config.py"
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
                
            if "from .secret_manager import" in content or "import secret_manager" in content:
                checks["secret_manager_imported"] = True
                
            if "secret_manager.get_secret" in content:
                checks["config_uses_secret_manager"] = True
                
            # Check for hardcoded secrets
            for pattern in SECURITY_PATTERNS.values():
                if re.search(pattern, content):
                    checks["no_hardcoded_secrets"] = False
                    break
        
        # Check secret manager implementation
        secret_manager_file = self.project_path / "backend/app/core/secret_manager.py"
        if secret_manager_file.exists():
            with open(secret_manager_file, 'r') as f:
                content = f.read()
                
            if "try:" in content and "except" in content:
                checks["proper_error_handling"] = True
                
            if "cache" in content.lower() or "lru_cache" in content:
                checks["secret_caching"] = True
        
        return checks
    
    def verify_gcp_configuration(self) -> Dict[str, bool]:
        """Verify GCP is properly configured for secrets"""
        print("\nVerifying GCP configuration...")
        
        checks = {
            "gcloud_authenticated": False,
            "secret_manager_api_enabled": False,
            "service_account_permissions": False,
            "secrets_exist": False
        }
        
        try:
            # Check gcloud authentication
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                checks["gcloud_authenticated"] = True
            
            # Check if Secret Manager API is enabled
            result = subprocess.run(
                ["gcloud", "services", "list", "--enabled", "--filter=name:secretmanager.googleapis.com"],
                capture_output=True, text=True
            )
            if "secretmanager.googleapis.com" in result.stdout:
                checks["secret_manager_api_enabled"] = True
            
            # Check service account permissions
            result = subprocess.run(
                ["gcloud", "projects", "get-iam-policy", "roadtrip-460720"],
                capture_output=True, text=True
            )
            if "secretmanager" in result.stdout:
                checks["service_account_permissions"] = True
            
            # Check if secrets exist
            result = subprocess.run(
                ["gcloud", "secrets", "list", "--project=roadtrip-460720"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and len(result.stdout.strip().split('\n')) > 1:
                checks["secrets_exist"] = True
                
        except Exception as e:
            print(f"Error checking GCP configuration: {e}")
        
        return checks
    
    def check_deployment_files(self) -> List[Dict]:
        """Check deployment files for security issues"""
        print("\nChecking deployment files...")
        
        deployment_issues = []
        
        # Check Docker files
        docker_files = list(self.project_path.glob("**/Dockerfile*"))
        for docker_file in docker_files:
            with open(docker_file, 'r') as f:
                content = f.read()
                
            # Check for secrets in Docker files
            if any(pattern in content for pattern in ["ENV.*KEY", "ENV.*SECRET", "ENV.*PASSWORD"]):
                deployment_issues.append({
                    "file": str(docker_file),
                    "issue": "Potential secrets in Dockerfile",
                    "severity": "HIGH"
                })
        
        # Check Kubernetes manifests
        k8s_files = list(self.project_path.glob("**/*.yaml")) + list(self.project_path.glob("**/*.yml"))
        for k8s_file in k8s_files:
            if "k8s" in str(k8s_file) or "kubernetes" in str(k8s_file):
                with open(k8s_file, 'r') as f:
                    content = f.read()
                    
                # Check for inline secrets
                if "value:" in content and any(word in content.lower() for word in ["key", "secret", "password"]):
                    deployment_issues.append({
                        "file": str(k8s_file),
                        "issue": "Potential inline secrets in Kubernetes manifest",
                        "severity": "HIGH"
                    })
        
        return deployment_issues
    
    def generate_report(self) -> str:
        """Generate comprehensive security report"""
        report = []
        report.append("=" * 80)
        report.append("CREDENTIAL SECURITY VALIDATION REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("=" * 80)
        
        # Critical findings
        critical_findings = [f for f in self.findings if "CRITICAL" in f.get("type", "")]
        if critical_findings:
            report.append("\n🚨 CRITICAL SECURITY ISSUES:")
            report.append(f"Found {len(critical_findings)} known exposed credentials!")
            for finding in critical_findings[:5]:  # Show first 5
                report.append(f"  - {finding['file']}:{finding['line']} - {finding['description']}")
            if len(critical_findings) > 5:
                report.append(f"  ... and {len(critical_findings) - 5} more")
        
        # Summary
        report.append(f"\n📊 SUMMARY:")
        report.append(f"  Total findings: {len(self.findings)}")
        report.append(f"  Critical issues: {len(critical_findings)}")
        report.append(f"  Files scanned: {len(set(f['file'] for f in self.findings))}")
        
        # Finding breakdown
        finding_types = {}
        for finding in self.findings:
            finding_type = finding['type']
            finding_types[finding_type] = finding_types.get(finding_type, 0) + 1
        
        report.append("\n📋 FINDINGS BY TYPE:")
        for finding_type, count in sorted(finding_types.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {finding_type}: {count}")
        
        # Secret Manager checks
        sm_checks = self.check_secret_manager_integration()
        report.append("\n🔐 SECRET MANAGER INTEGRATION:")
        for check, status in sm_checks.items():
            icon = "✅" if status else "❌"
            report.append(f"  {icon} {check.replace('_', ' ').title()}")
        
        # GCP configuration
        gcp_checks = self.verify_gcp_configuration()
        report.append("\n☁️  GCP CONFIGURATION:")
        for check, status in gcp_checks.items():
            icon = "✅" if status else "❌"
            report.append(f"  {icon} {check.replace('_', ' ').title()}")
        
        # Deployment checks
        deployment_issues = self.check_deployment_files()
        if deployment_issues:
            report.append("\n⚠️  DEPLOYMENT SECURITY ISSUES:")
            for issue in deployment_issues[:5]:
                report.append(f"  - {issue['file']}: {issue['issue']}")
        
        # Recommendations
        report.append("\n💡 RECOMMENDATIONS:")
        if critical_findings:
            report.append("  1. IMMEDIATELY rotate all exposed credentials")
            report.append("  2. Run: python scripts/security/emergency_credential_rotation.py")
        
        report.append("  3. Ensure all secrets are in Google Secret Manager")
        report.append("  4. Remove any hardcoded credentials from code")
        report.append("  5. Set up automated rotation schedules")
        report.append("  6. Enable audit logging for secret access")
        
        # Production readiness
        all_checks_passed = (
            len(critical_findings) == 0 and
            all(sm_checks.values()) and
            all(gcp_checks.values()) and
            len(deployment_issues) == 0
        )
        
        report.append("\n🚀 PRODUCTION READINESS:")
        if all_checks_passed:
            report.append("  ✅ All security checks PASSED - Ready for production")
        else:
            report.append("  ❌ Security issues found - NOT ready for production")
            report.append("  Fix all issues before deploying!")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
    
    def save_detailed_findings(self) -> None:
        """Save detailed findings to JSON file"""
        detailed_report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_findings": len(self.findings),
                "critical_findings": len([f for f in self.findings if "CRITICAL" in f.get("type", "")]),
                "files_with_issues": len(set(f['file'] for f in self.findings))
            },
            "findings": self.findings,
            "secret_manager_checks": self.check_secret_manager_integration(),
            "gcp_configuration": self.verify_gcp_configuration(),
            "deployment_issues": self.check_deployment_files()
        }
        
        with open("security_validation_report.json", "w") as f:
            json.dump(detailed_report, f, indent=2)
        
        print("\nDetailed findings saved to: security_validation_report.json")

def main():
    """Main execution"""
    validator = SecurityValidator()
    
    # Run validation
    validator.scan_codebase()
    
    # Generate report
    report = validator.generate_report()
    print("\n" + report)
    
    # Save detailed findings
    validator.save_detailed_findings()
    
    # Exit with appropriate code
    critical_count = len([f for f in validator.findings if "CRITICAL" in f.get("type", "")])
    if critical_count > 0:
        print(f"\n❌ FAILED: {critical_count} critical security issues found!")
        sys.exit(1)
    else:
        print("\n✅ Security validation complete")
        sys.exit(0)

if __name__ == "__main__":
    main()