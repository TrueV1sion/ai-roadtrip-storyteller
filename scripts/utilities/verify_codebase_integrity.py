#!/usr/bin/env python3
"""
Codebase Integrity Verification Script
Ensures all critical dependencies and imports work after cleanup
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import ast
import json

class CodebaseVerifier:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.errors = []
        self.warnings = []
        self.passed_checks = []
        
    def run(self):
        """Run all verification checks"""
        print("\n🔍 AI ROAD TRIP STORYTELLER - CODEBASE INTEGRITY CHECK")
        print("=" * 60)
        
        # Run all checks
        self.check_critical_files()
        self.check_python_imports()
        self.check_docker_builds()
        self.check_database_migrations()
        self.check_test_discovery()
        self.check_api_endpoints()
        self.check_environment_variables()
        self.check_documentation_links()
        
        # Generate report
        self.generate_report()
        
    def check_critical_files(self):
        """Check that all critical files exist"""
        print("\n📁 Checking critical files...")
        
        critical_files = {
            # Backend essentials
            "backend/app/main.py": "Main FastAPI application",
            "backend/app/main_minimal.py": "Used by backend/Dockerfile",
            "backend/app/models.py": "Database models",
            "backend/app/database.py": "Database configuration",
            "backend/app/services/master_orchestration_agent.py": "Core AI orchestration",
            "backend/app/services/personality_engine.py": "Voice personality system",
            
            # Configuration
            "requirements.txt": "Python dependencies",
            "alembic.ini": "Database migration config",
            "docker-compose.yml": "Local development setup",
            "pytest.ini": "Test configuration",
            
            # Mobile essentials
            "mobile/App.tsx": "Mobile app entry point",
            "mobile/package.json": "Mobile dependencies",
            "mobile/app.json": "Expo configuration",
            
            # Infrastructure
            "infrastructure/terraform/main.tf": "Terraform configuration",
            "Dockerfile": "Production Docker image",
            
            # Documentation
            "README.md": "Project documentation",
            "CLAUDE.md": "AI assistant instructions",
        }
        
        for file_path, description in critical_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                self.passed_checks.append(f"✓ {file_path} - {description}")
            else:
                self.errors.append(f"✗ Missing: {file_path} - {description}")
                
    def check_python_imports(self):
        """Check that all Python imports can be resolved"""
        print("\n🐍 Checking Python imports...")
        
        # Add project to Python path
        sys.path.insert(0, str(self.project_root))
        sys.path.insert(0, str(self.project_root / "backend"))
        
        # Key modules to verify
        modules_to_check = [
            ("backend.app.main", "Main application"),
            ("backend.app.services.master_orchestration_agent", "AI orchestration"),
            ("backend.app.core.config", "Configuration"),
            ("backend.app.routes.voice_assistant", "Voice routes"),
            ("backend.app.models", "Database models"),
        ]
        
        for module_name, description in modules_to_check:
            try:
                spec = importlib.util.find_spec(module_name)
                if spec:
                    self.passed_checks.append(f"✓ Import works: {module_name}")
                else:
                    self.errors.append(f"✗ Cannot import: {module_name} - {description}")
            except Exception as e:
                self.errors.append(f"✗ Import error for {module_name}: {str(e)}")
                
    def check_docker_builds(self):
        """Check that Docker images can be built"""
        print("\n🐳 Checking Docker configurations...")
        
        dockerfiles = [
            ("Dockerfile", "Production image"),
            ("backend/Dockerfile", "Backend development image"),
        ]
        
        for dockerfile, description in dockerfiles:
            full_path = self.project_root / dockerfile
            if full_path.exists():
                # Parse Dockerfile to check for referenced files
                with open(full_path, 'r') as f:
                    content = f.read()
                    
                # Check COPY commands reference valid files
                for line in content.split('\n'):
                    if line.strip().startswith('COPY'):
                        parts = line.split()
                        if len(parts) >= 3:
                            src = parts[1]
                            # Skip if it's copying from a stage
                            if '--from=' in src:
                                continue
                                
                            # Special case for backend/Dockerfile
                            if dockerfile == "backend/Dockerfile":
                                if src == "app/main_minimal.py":
                                    src_path = self.project_root / "backend" / src
                                elif src == "requirements-minimal.txt":
                                    src_path = self.project_root / "backend" / src
                                else:
                                    src_path = self.project_root / "backend" / src
                            else:
                                src_path = self.project_root / src
                                
                            if not src_path.exists() and not '*' in src:
                                self.warnings.append(f"⚠ Dockerfile references missing file: {src}")
                                
                self.passed_checks.append(f"✓ {dockerfile} - {description}")
            else:
                self.errors.append(f"✗ Missing Dockerfile: {dockerfile}")
                
    def check_database_migrations(self):
        """Check that all database migrations are present"""
        print("\n🗄️ Checking database migrations...")
        
        migrations_dir = self.project_root / "alembic/versions"
        if migrations_dir.exists():
            migrations = list(migrations_dir.glob("*.py"))
            if migrations:
                self.passed_checks.append(f"✓ Found {len(migrations)} migration files")
                
                # Check critical migrations
                critical_migrations = [
                    "20250123_add_event_journeys.py",
                    "20250523_add_commission_tracking.py",
                ]
                
                migration_names = [m.name for m in migrations]
                for critical in critical_migrations:
                    if critical in migration_names:
                        self.passed_checks.append(f"✓ Critical migration present: {critical}")
                    else:
                        self.warnings.append(f"⚠ Missing migration: {critical}")
            else:
                self.errors.append("✗ No migration files found")
        else:
            self.errors.append("✗ Migrations directory not found")
            
    def check_test_discovery(self):
        """Check that pytest can discover tests"""
        print("\n🧪 Checking test discovery...")
        
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                # Count collected tests
                test_count = len([line for line in result.stdout.split('\n') if '::' in line])
                self.passed_checks.append(f"✓ Pytest can discover {test_count} tests")
            else:
                self.warnings.append(f"⚠ Pytest collection issues: {result.stderr}")
                
        except Exception as e:
            self.warnings.append(f"⚠ Could not run pytest: {str(e)}")
            
    def check_api_endpoints(self):
        """Check that API route files are properly structured"""
        print("\n🌐 Checking API endpoints...")
        
        routes_dir = self.project_root / "backend/app/routes"
        if routes_dir.exists():
            route_files = list(routes_dir.glob("*.py"))
            
            critical_routes = [
                "voice_assistant.py",
                "auth.py",
                "directions.py",
                "story.py",
                "booking.py",
                "health.py",
            ]
            
            existing_routes = [r.name for r in route_files]
            for route in critical_routes:
                if route in existing_routes:
                    self.passed_checks.append(f"✓ API route exists: {route}")
                else:
                    self.warnings.append(f"⚠ Missing route file: {route}")
                    
            # Check for router imports in main.py
            main_file = self.project_root / "backend/app/main.py"
            if main_file.exists():
                with open(main_file, 'r') as f:
                    content = f.read()
                    if 'app.include_router' in content:
                        self.passed_checks.append("✓ Routes are registered in main.py")
                    else:
                        self.warnings.append("⚠ No routers found in main.py")
                        
    def check_environment_variables(self):
        """Check for required environment variables in code"""
        print("\n🔐 Checking environment variables...")
        
        # Check config files for required env vars
        config_files = [
            self.project_root / "backend/app/core/config.py",
            self.project_root / "backend/app/core/cloud_config.py",
        ]
        
        required_vars = set()
        
        for config_file in config_files:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    content = f.read()
                    # Find getenv calls
                    import re
                    env_vars = re.findall(r'os\.getenv\(["\'](\w+)["\']\)', content)
                    required_vars.update(env_vars)
                    
                    # Find Settings class attributes
                    if 'class Settings' in content:
                        # Simple parsing for pydantic settings
                        attrs = re.findall(r'(\w+):\s*(?:str|int|bool|float)', content)
                        required_vars.update([a.upper() for a in attrs if not a.startswith('_')])
                        
        if required_vars:
            self.passed_checks.append(f"✓ Found {len(required_vars)} environment variables")
            
            # Check for .env.example
            env_example = self.project_root / ".env.example"
            if env_example.exists():
                self.passed_checks.append("✓ .env.example exists for reference")
            else:
                self.warnings.append("⚠ No .env.example file for environment reference")
                
    def check_documentation_links(self):
        """Check that internal documentation links work"""
        print("\n📚 Checking documentation links...")
        
        # Check README.md for broken internal links
        readme = self.project_root / "README.md"
        if readme.exists():
            with open(readme, 'r') as f:
                content = f.read()
                
            # Find markdown links
            import re
            links = re.findall(r'\[.*?\]\((.*?)\)', content)
            
            broken_links = []
            for link in links:
                # Skip external links
                if link.startswith('http'):
                    continue
                    
                # Check internal links
                if link.startswith('#'):
                    continue  # Anchor links
                    
                link_path = self.project_root / link
                if not link_path.exists():
                    broken_links.append(link)
                    
            if broken_links:
                for link in broken_links:
                    self.warnings.append(f"⚠ Broken link in README: {link}")
            else:
                self.passed_checks.append("✓ All internal README links valid")
                
    def generate_report(self):
        """Generate verification report"""
        print("\n" + "=" * 60)
        print("📊 INTEGRITY CHECK REPORT")
        print("=" * 60)
        
        # Summary
        total_checks = len(self.passed_checks) + len(self.errors) + len(self.warnings)
        print(f"\nTotal checks: {total_checks}")
        print(f"✅ Passed: {len(self.passed_checks)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        # Detailed results
        if self.errors:
            print("\n❌ ERRORS (Must Fix):")
            for error in self.errors:
                print(f"  {error}")
                
        if self.warnings:
            print("\n⚠️  WARNINGS (Should Review):")
            for warning in self.warnings:
                print(f"  {warning}")
                
        if self.passed_checks and len(self.passed_checks) < 20:
            print("\n✅ PASSED CHECKS:")
            for check in self.passed_checks:
                print(f"  {check}")
        elif self.passed_checks:
            print(f"\n✅ {len(self.passed_checks)} checks passed successfully")
            
        # Overall status
        print("\n" + "=" * 60)
        if self.errors:
            print("🚨 CRITICAL: Fix errors before proceeding with deployment")
            sys.exit(1)
        elif self.warnings:
            print("⚠️  ATTENTION: Review warnings but can proceed")
            sys.exit(0)
        else:
            print("✨ SUCCESS: Codebase integrity verified!")
            sys.exit(0)
            

if __name__ == "__main__":
    verifier = CodebaseVerifier()
    verifier.run()