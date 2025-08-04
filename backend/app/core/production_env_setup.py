"""
Production environment setup and validation.
Ensures all production security settings are properly configured.
"""

import os
import sys
from typing import Dict, List, Tuple, Optional
import secrets
import string

from app.core.logger import logger
from app.core.config import settings


class ProductionEnvSetup:
    """Setup and validation for production environment variables."""
    
    @staticmethod
    def generate_secure_secret(length: int = 64) -> str:
        """Generate a cryptographically secure secret."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def validate_production_environment() -> Tuple[bool, List[str]]:
        """Validate production environment configuration."""
        errors = []
        warnings = []
        
        # Critical security settings
        critical_checks = [
            ("ENVIRONMENT", "production", "Environment must be set to production"),
            ("DEBUG", "false", "Debug mode must be disabled in production"),
            ("FORCE_HTTPS", "true", "HTTPS enforcement must be enabled"),
            ("SECURE_COOKIES", "true", "Secure cookies must be enabled"),
        ]
        
        for env_var, expected, message in critical_checks:
            value = os.getenv(env_var, "").lower()
            if value != expected:
                errors.append(f"{message} (current: {value})")
        
        # Required secrets
        required_secrets = [
            "DATABASE_URL",
            "REDIS_URL", 
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "CSRF_SECRET_KEY",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_MAPS_API_KEY"
        ]
        
        for secret in required_secrets:
            if not os.getenv(secret):
                errors.append(f"Required secret {secret} is not set")
        
        # Check for insecure default values
        insecure_patterns = [
            "dev-secret-key",
            "changeme",
            "your-secret-key",
            "localhost",
            "development",
            "test"
        ]
        
        security_vars = ["SECRET_KEY", "JWT_SECRET_KEY", "CSRF_SECRET_KEY"]
        for var in security_vars:
            value = os.getenv(var, "").lower()
            if any(pattern in value for pattern in insecure_patterns):
                errors.append(f"{var} contains insecure patterns")
        
        # Database security checks
        db_url = os.getenv("DATABASE_URL", "")
        if "localhost" in db_url:
            warnings.append("Database URL contains localhost - ensure this is intentional for production")
        
        if "sslmode=require" not in db_url and "sslmode=disable" not in db_url:
            warnings.append("Database URL doesn't specify SSL mode")
        
        # CORS configuration
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        if "*" in allowed_origins:
            errors.append("CORS allows all origins - security risk")
        
        # API key validation (check for test patterns)
        api_keys = [
            "GOOGLE_MAPS_API_KEY",
            "TICKETMASTER_API_KEY", 
            "OPENWEATHERMAP_API_KEY"
        ]
        
        test_patterns = ["test", "demo", "sandbox", "development"]
        for key in api_keys:
            value = os.getenv(key, "").lower()
            if any(pattern in value for pattern in test_patterns):
                warnings.append(f"{key} appears to be a test key")
        
        return len(errors) == 0, errors + warnings
    
    @staticmethod
    def setup_production_defaults() -> Dict[str, str]:
        """Generate production-ready environment variables."""
        prod_env = {
            # Environment
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "PRODUCTION": "true",
            
            # Security
            "FORCE_HTTPS": "true",
            "SECURE_COOKIES": "true",
            "CSP_ENABLED": "true",
            "SECURITY_HSTS_ENABLED": "true",
            "SECURITY_XFO_ENABLED": "true",
            "SECURITY_CONTENT_TYPE_OPTIONS_ENABLED": "true",
            "SECURITY_REFERRER_POLICY_ENABLED": "true",
            "SECURITY_XSS_PROTECTION_ENABLED": "true",
            
            # CORS (restrictive by default)
            "ALLOWED_ORIGINS": "https://yourdomain.com,https://app.yourdomain.com",
            
            # Generate secure secrets if not provided
            "SECRET_KEY": ProductionEnvSetup.generate_secure_secret(64),
            "JWT_SECRET_KEY": ProductionEnvSetup.generate_secure_secret(64),
            "CSRF_SECRET_KEY": ProductionEnvSetup.generate_secure_secret(64),
            
            # App settings
            "APP_VERSION": "1.0.0",
            "LOG_LEVEL": "INFO",
            
            # Default AI settings
            "GOOGLE_AI_MODEL": "gemini-1.5-pro",
            "GOOGLE_AI_LOCATION": "us-central1",
            
            # Cache settings
            "REDIS_TTL": "3600",
            
            # Rate limiting
            "RATE_LIMIT_ENABLED": "true",
            "RATE_LIMIT_PER_MINUTE": "100",
            
            # TTS settings
            "TTS_PROVIDER": "google",
        }
        
        return prod_env
    
    @staticmethod
    def create_production_env_file(output_path: str = ".env.production") -> str:
        """Create a production environment file template."""
        env_vars = ProductionEnvSetup.setup_production_defaults()
        
        env_content = [
            "# AI Road Trip Storyteller - Production Environment Configuration",
            "# Generated by production setup script",
            "# IMPORTANT: Replace placeholder values with actual production values",
            "",
            "# === CRITICAL SECURITY SETTINGS ===",
            "# These MUST be properly configured before deployment",
            "",
        ]
        
        # Group environment variables
        groups = {
            "Environment Settings": [
                "ENVIRONMENT", "DEBUG", "PRODUCTION", "APP_VERSION", "LOG_LEVEL"
            ],
            "Security Settings": [
                "FORCE_HTTPS", "SECURE_COOKIES", "CSP_ENABLED", 
                "SECURITY_HSTS_ENABLED", "SECURITY_XFO_ENABLED",
                "SECURITY_CONTENT_TYPE_OPTIONS_ENABLED", "SECURITY_REFERRER_POLICY_ENABLED",
                "SECURITY_XSS_PROTECTION_ENABLED"
            ],
            "Secrets (REPLACE THESE)": [
                "SECRET_KEY", "JWT_SECRET_KEY", "CSRF_SECRET_KEY"
            ],
            "Database & Cache": [
                "DATABASE_URL", "REDIS_URL", "REDIS_TTL"
            ],
            "Google Cloud": [
                "GOOGLE_CLOUD_PROJECT", "GOOGLE_AI_PROJECT_ID", "GOOGLE_AI_MODEL", 
                "GOOGLE_AI_LOCATION", "GOOGLE_MAPS_API_KEY", "GCS_BUCKET_NAME"
            ],
            "External APIs": [
                "TICKETMASTER_API_KEY", "OPENWEATHERMAP_API_KEY", "RECREATION_GOV_API_KEY"
            ],
            "CORS & Origins": [
                "ALLOWED_ORIGINS"
            ],
            "Rate Limiting": [
                "RATE_LIMIT_ENABLED", "RATE_LIMIT_PER_MINUTE"
            ]
        }
        
        for group_name, vars_list in groups.items():
            env_content.append(f"# {group_name}")
            for var in vars_list:
                if var in env_vars:
                    if "SECRET" in var or "KEY" in var:
                        env_content.append(f"{var}=\"{env_vars[var]}\"  # GENERATED - KEEP SECURE")
                    else:
                        env_content.append(f"{var}=\"{env_vars[var]}\"")
                else:
                    env_content.append(f"# {var}=")  # Placeholder for manual input
            env_content.append("")
        
        # Add additional required variables
        env_content.extend([
            "# === VARIABLES REQUIRING MANUAL CONFIGURATION ===",
            "# These must be manually configured with actual production values:",
            "",
            "# Database URL (replace with production database)",
            "DATABASE_URL=\"postgresql://user:password@host:5432/database?sslmode=require\"",
            "",
            "# Redis URL (replace with production Redis)",
            "REDIS_URL=\"redis://password@host:6379/0\"",
            "",
            "# Google Cloud Project ID",
            "GOOGLE_CLOUD_PROJECT=\"your-production-project-id\"",
            "GOOGLE_AI_PROJECT_ID=\"your-production-project-id\"",
            "",
            "# API Keys (replace with production keys)",
            "GOOGLE_MAPS_API_KEY=\"your-production-google-maps-key\"",
            "TICKETMASTER_API_KEY=\"your-production-ticketmaster-key\"", 
            "OPENWEATHERMAP_API_KEY=\"your-production-openweather-key\"",
            "",
            "# Storage",
            "GCS_BUCKET_NAME=\"your-production-bucket\"",
            "",
            "# Domain configuration",
            "ALLOWED_ORIGINS=\"https://yourdomain.com,https://app.yourdomain.com\"",
            "",
            "# === DEPLOYMENT CHECKLIST ===",
            "# [ ] Replace all placeholder values above",
            "# [ ] Verify all secrets are unique and secure",
            "# [ ] Test database and Redis connectivity",
            "# [ ] Validate API keys are production keys (not test/sandbox)",
            "# [ ] Update ALLOWED_ORIGINS with actual domain(s)",
            "# [ ] Run security validation: python -m backend.app.core.production_env_setup",
        ])
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(env_content))
        
        return output_path
    
    @staticmethod
    def run_security_audit() -> Dict[str, any]:
        """Run comprehensive security audit."""
        audit_results = {
            "timestamp": "",
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "security_score": 0,
            "critical_issues": [],
            "warnings": [],
            "passed_checks": [],
            "recommendations": []
        }
        
        # Run validation
        is_valid, issues = ProductionEnvSetup.validate_production_environment()
        
        # Categorize issues
        for issue in issues:
            if any(keyword in issue.lower() for keyword in ["must", "required", "critical"]):
                audit_results["critical_issues"].append(issue)
            else:
                audit_results["warnings"].append(issue)
        
        # Calculate security score
        total_checks = 20  # Total number of security checks
        critical_issues = len(audit_results["critical_issues"])
        warnings = len(audit_results["warnings"])
        
        # Scoring: Critical issues are -5 points, warnings are -1 point
        score = max(0, total_checks - (critical_issues * 5) - warnings)
        audit_results["security_score"] = (score / total_checks) * 100
        
        # Add recommendations
        if critical_issues > 0:
            audit_results["recommendations"].append("Address all critical security issues before deployment")
        
        if warnings > 0:
            audit_results["recommendations"].append("Review and address security warnings")
        
        if audit_results["security_score"] < 80:
            audit_results["recommendations"].append("Security score below 80% - not recommended for production")
        
        return audit_results


def main():
    """CLI interface for production environment setup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production Environment Setup")
    parser.add_argument("--validate", action="store_true", help="Validate current environment")
    parser.add_argument("--generate", action="store_true", help="Generate production .env file")
    parser.add_argument("--audit", action="store_true", help="Run security audit")
    parser.add_argument("--output", default=".env.production", help="Output file for generated .env")
    
    args = parser.parse_args()
    
    if args.validate:
        print("🔍 Validating production environment...")
        is_valid, issues = ProductionEnvSetup.validate_production_environment()
        
        if is_valid:
            print("✅ Production environment validation passed!")
        else:
            print("❌ Production environment validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
    
    elif args.generate:
        print("🔧 Generating production environment file...")
        output_file = ProductionEnvSetup.create_production_env_file(args.output)
        print(f"✅ Production environment file created: {output_file}")
        print("⚠️  IMPORTANT: Review and update all placeholder values before deployment!")
    
    elif args.audit:
        print("🔒 Running security audit...")
        audit_results = ProductionEnvSetup.run_security_audit()
        
        print(f"\n📊 Security Score: {audit_results['security_score']:.1f}%")
        
        if audit_results["critical_issues"]:
            print(f"\n🚨 Critical Issues ({len(audit_results['critical_issues'])}):")
            for issue in audit_results["critical_issues"]:
                print(f"  - {issue}")
        
        if audit_results["warnings"]:
            print(f"\n⚠️  Warnings ({len(audit_results['warnings'])}):")
            for warning in audit_results["warnings"]:
                print(f"  - {warning}")
        
        if audit_results["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in audit_results["recommendations"]:
                print(f"  - {rec}")
        
        if audit_results["security_score"] < 80:
            print("\n❌ Environment not ready for production deployment")
            sys.exit(1)
        else:
            print("\n✅ Environment ready for production deployment")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()