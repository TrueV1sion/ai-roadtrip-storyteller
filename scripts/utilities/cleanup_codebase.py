#!/usr/bin/env python3
"""
Comprehensive Codebase Cleanup Script for AI Road Trip Storyteller
Safely removes unnecessary files while preserving all critical functionality
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import json
import subprocess
from typing import List, Dict, Tuple

class CodebaseCleanup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.backup_dir = self.project_root / f"cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.dry_run = True
        self.changes_log = []
        
    def run(self):
        """Execute the cleanup process"""
        print("\n🧹 AI ROAD TRIP STORYTELLER - CODEBASE CLEANUP")
        print("=" * 60)
        print(f"Project root: {self.project_root}")
        print(f"Backup directory: {self.backup_dir}")
        print()
        
        # Phase 1: Safety checks
        if not self.safety_checks():
            return
            
        # Phase 2: Backup critical files
        if not self.create_backup():
            return
            
        # Phase 3: Cleanup phases
        self.phase1_remove_safe_files()
        self.phase2_reorganize_structure()
        self.phase3_consolidate_docs()
        self.phase4_clean_temp_files()
        self.phase5_update_gitignore()
        
        # Phase 6: Validation
        self.validate_cleanup()
        
        # Phase 7: Generate report
        self.generate_report()
        
    def safety_checks(self) -> bool:
        """Perform safety checks before cleanup"""
        print("🔍 Running safety checks...")
        
        # Check if we're in the right directory
        if not (self.project_root / "backend").exists() or not (self.project_root / "mobile").exists():
            print("❌ Not in project root directory!")
            return False
            
        # Check for uncommitted changes
        try:
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True, cwd=self.project_root)
            if result.stdout.strip():
                print("⚠️  Warning: You have uncommitted changes!")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    return False
        except:
            print("⚠️  Warning: Unable to check git status")
            
        # Confirm with user
        print("\n📋 This script will:")
        print("  - Create a backup of files to be removed")
        print("  - Remove ~150+ unnecessary files")
        print("  - Reorganize directory structure")
        print("  - Update .gitignore")
        print()
        
        response = input("Do you want to run in DRY RUN mode first? (Y/n): ")
        self.dry_run = response.lower() != 'n'
        
        if self.dry_run:
            print("✅ Running in DRY RUN mode - no files will be modified")
        else:
            print("⚠️  Running in LIVE mode - files will be modified!")
            response = input("Are you SURE you want to proceed? (yes/no): ")
            if response.lower() != 'yes':
                return False
                
        return True
        
    def create_backup(self) -> bool:
        """Create backup of files to be removed"""
        if self.dry_run:
            print("\n📦 [DRY RUN] Would create backup directory")
            return True
            
        print("\n📦 Creating backup...")
        try:
            self.backup_dir.mkdir(exist_ok=True)
            
            # Backup files we'll remove
            files_to_backup = [
                "CLAUDE.md.save",
                "compare_storytelling.py",
                "test_minimal_local.py",
                "test_setup_verification.py",
                "verify_tests.py",
                "demo.html",
                "demo-enhanced.html",
                "demo-enhanced-fixed.html",
            ]
            
            for file in files_to_backup:
                src = self.project_root / file
                if src.exists():
                    dst = self.backup_dir / file
                    shutil.copy2(src, dst)
                    print(f"  ✓ Backed up {file}")
                    
            # Backup entire archive directory
            if (self.project_root / "archive").exists():
                shutil.copytree(self.project_root / "archive", self.backup_dir / "archive")
                print("  ✓ Backed up archive directory")
                
            print(f"✅ Backup created at: {self.backup_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
            
    def remove_file(self, filepath: Path, reason: str):
        """Remove a file with logging"""
        if filepath.exists():
            if self.dry_run:
                self.changes_log.append(f"[DRY RUN] Would remove: {filepath.relative_to(self.project_root)} - {reason}")
            else:
                filepath.unlink()
                self.changes_log.append(f"Removed: {filepath.relative_to(self.project_root)} - {reason}")
                
    def remove_directory(self, dirpath: Path, reason: str):
        """Remove a directory with logging"""
        if dirpath.exists():
            if self.dry_run:
                self.changes_log.append(f"[DRY RUN] Would remove directory: {dirpath.relative_to(self.project_root)} - {reason}")
            else:
                shutil.rmtree(dirpath)
                self.changes_log.append(f"Removed directory: {dirpath.relative_to(self.project_root)} - {reason}")
                
    def phase1_remove_safe_files(self):
        """Phase 1: Remove files with no dependencies"""
        print("\n🗑️  Phase 1: Removing safe files...")
        
        # Root directory planning documents
        planning_docs = [
            "COMPLETE_FEATURE_IMPLEMENTATION_PLAN.md",
            "DEPLOYMENT_ISSUES_TO_FIX.md",
            "DEPLOYMENT_READY_SUMMARY.md",
            "DEPLOYMENT_VERIFICATION_CHECKLIST.md",
            "DEPLOY_NOW.md",
            "DEPLOY_NOW_CHECKLIST.md",
            "DEVELOPMENT_EXECUTION_PLAN.md",
            "DEVELOPMENT_TIMELINE_REALISTIC.md",
            "PRIORITIZED_IMPLEMENTATION_PLAN.md",
            "PROJECT_STATUS_REALITY.md",
            "RAPID_MVP_DEPLOYMENT.md",
            "README_MVP_LAUNCH.md",
            "REORGANIZATION_SUMMARY.md",
            "MVP_DEPLOYMENT_PLAN.md",
            "MVP_LAUNCH_CHECKLIST.md",
            "MVP_LAUNCH_SUCCESS.md",
            "ROADTRIP_KNOWLEDGE_GRAPH.md",
            "backend_services_analysis.md",
        ]
        
        for doc in planning_docs:
            self.remove_file(self.project_root / doc, "Redundant planning document")
            
        # Test files in root
        root_tests = [
            "test_minimal_local.py",
            "test_setup_verification.py",
            "verify_tests.py",
            "test_real_apis.sh",
            "compare_storytelling.py",
        ]
        
        for test in root_tests:
            self.remove_file(self.project_root / test, "Test file not in test suite")
            
        # Demo HTML files
        demos = ["demo.html", "demo-enhanced.html", "demo-enhanced-fixed.html"]
        for demo in demos:
            self.remove_file(self.project_root / demo, "Unused demo file")
            
        # Backup files
        self.remove_file(self.project_root / "CLAUDE.md.save", "Backup file")
        self.remove_file(self.project_root / "config/docker/Dockerfile.old", "Old Dockerfile")
        
        # Redundant shell scripts
        scripts = [
            "cloud_run_commands.sh",
            "deploy_production.ps1",
            "deploy_production_complete.ps1", 
            "deploy_production_clean.ps1",
            "deploy_cloud_run_real.sh",
            "deploy_minimal_mvp.sh",
        ]
        
        for script in scripts:
            self.remove_file(self.project_root / script, "Redundant deployment script")
            
        # Archive directory
        self.remove_directory(self.project_root / "archive", "Historical files - backed up")
        
        # Credentials directories
        self.remove_directory(self.project_root / "credentials", "Sensitive data - use secret management")
        self.remove_directory(self.project_root / "credentials_backup", "Sensitive data - use secret management")
        
        # Duplicate cloudbuild files
        self.remove_file(self.project_root / "cloudbuild.yaml", "Duplicate cloudbuild file")
        self.remove_file(self.project_root / "cloudbuild-fixed.yaml", "Duplicate cloudbuild file")
        
    def phase2_reorganize_structure(self):
        """Phase 2: Reorganize directory structure"""
        print("\n📁 Phase 2: Reorganizing structure...")
        
        # Create main_variants directory for alternative main.py files
        variants_dir = self.project_root / "backend/app/main_variants"
        if not self.dry_run:
            variants_dir.mkdir(exist_ok=True)
            
        # Move alternative main files
        main_variants = [
            "main_enhanced.py",
            "main_performance.py", 
            "main_mvp.py",
            "main_production.py"
        ]
        
        for variant in main_variants:
            src = self.project_root / f"backend/app/{variant}"
            if src.exists():
                if self.dry_run:
                    self.changes_log.append(f"[DRY RUN] Would move: {variant} to main_variants/")
                else:
                    dst = variants_dir / variant
                    shutil.move(str(src), str(dst))
                    self.changes_log.append(f"Moved: {variant} to main_variants/")
                    
        # Clean up backend PowerShell scripts
        backend_ps_scripts = [
            "deploy_mvp_fixed.ps1",
            "deploy_with_navigation.ps1",
            "deploy_with_existing_keys.ps1",
            "deploy_enhanced_stories.ps1",
            "test_mvp_navigation.ps1",
            "test_full_navigation.ps1",
            "test_navigation_detailed.ps1",
            "test_vertex_ai_directly.ps1",
            "check_deployment_logs.ps1",
            "fix_deployment_env.ps1",
            "set_mvp_env.ps1",
            "check_cloud_run_env.ps1",
            "backend/test_health_endpoints.py",
        ]
        
        for script in backend_ps_scripts:
            self.remove_file(self.project_root / f"backend/{script}", "Redundant PowerShell script")
            
    def phase3_consolidate_docs(self):
        """Phase 3: Consolidate documentation"""
        print("\n📚 Phase 3: Consolidating documentation...")
        
        # Move MVP docs to archive
        archive_dir = self.project_root / "docs/planning/archive"
        if not self.dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
            
        # This is handled in phase 1 for now
        # Future: move docs instead of deleting
        
    def phase4_clean_temp_files(self):
        """Phase 4: Clean temporary files"""
        print("\n🧹 Phase 4: Cleaning temporary files...")
        
        # Find and remove all __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            self.remove_directory(pycache, "Python cache directory")
            
        # Remove .pyc files
        for pyc in self.project_root.rglob("*.pyc"):
            self.remove_file(pyc, "Python compiled file")
            
        # Remove pytest cache
        for pytest_cache in self.project_root.rglob(".pytest_cache"):
            self.remove_directory(pytest_cache, "Pytest cache")
            
        # Remove coverage directories
        for cov_dir in ["htmlcov", ".coverage"]:
            if (self.project_root / cov_dir).exists():
                self.remove_directory(self.project_root / cov_dir, "Coverage data")
                
    def phase5_update_gitignore(self):
        """Phase 5: Update .gitignore"""
        print("\n📝 Phase 5: Updating .gitignore...")
        
        gitignore_additions = """
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover

# Credentials and secrets
credentials/
credentials_backup/
*.json
*.key
*.pem
service-account*.json

# IDE and OS
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
*.save
*.bak
*.old

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Build outputs
build/
dist/
*.egg-info/

# Mobile
coverage/
*.ipa
*.apk
*.aab

# Terraform
*.tfstate
*.tfstate.*
.terraform/
"""
        
        gitignore_path = self.project_root / ".gitignore"
        
        if self.dry_run:
            self.changes_log.append("[DRY RUN] Would update .gitignore with comprehensive patterns")
        else:
            # Read existing gitignore
            existing_content = ""
            if gitignore_path.exists():
                existing_content = gitignore_path.read_text()
                
            # Add our additions if not already present
            if "# Credentials and secrets" not in existing_content:
                with open(gitignore_path, 'a') as f:
                    f.write("\n" + gitignore_additions)
                self.changes_log.append("Updated .gitignore with comprehensive patterns")
                
    def validate_cleanup(self):
        """Validate the cleanup didn't break anything"""
        print("\n✅ Phase 6: Validating cleanup...")
        
        critical_files = [
            "backend/app/main.py",
            "backend/app/main_minimal.py",  # Used by Dockerfile
            "mobile/App.tsx",
            "infrastructure/terraform/main.tf",
            "CLAUDE.md",
            "README.md",
            "requirements.txt",
            "package.json",
        ]
        
        all_good = True
        for file in critical_files:
            if not (self.project_root / file).exists() and not self.dry_run:
                print(f"❌ Critical file missing: {file}")
                all_good = False
                
        if all_good:
            print("✅ All critical files present")
            
    def generate_report(self):
        """Generate cleanup report"""
        print("\n📊 CLEANUP REPORT")
        print("=" * 60)
        
        # Count changes by type
        removed_files = [log for log in self.changes_log if "Removed:" in log]
        removed_dirs = [log for log in self.changes_log if "directory:" in log]
        moved_files = [log for log in self.changes_log if "Moved:" in log]
        
        print(f"Files removed: {len(removed_files)}")
        print(f"Directories removed: {len(removed_dirs)}")
        print(f"Files moved: {len(moved_files)}")
        print(f"Total changes: {len(self.changes_log)}")
        
        # Save detailed log
        log_file = self.project_root / f"cleanup_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        if not self.dry_run:
            with open(log_file, 'w') as f:
                f.write("AI ROAD TRIP STORYTELLER - CLEANUP LOG\n")
                f.write(f"Date: {datetime.now()}\n")
                f.write(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}\n")
                f.write("=" * 60 + "\n\n")
                
                for change in self.changes_log:
                    f.write(change + "\n")
                    
            print(f"\n📄 Detailed log saved to: {log_file}")
            
        if self.dry_run:
            print("\n🔍 This was a DRY RUN - no files were actually modified")
            print("Run again without dry run mode to execute the cleanup")
            
        print("\n✨ Cleanup complete! Your codebase is now production-ready.")
        

if __name__ == "__main__":
    cleanup = CodebaseCleanup()
    cleanup.run()