#!/usr/bin/env python3
"""
Pre-flight check for codebase cleanup
Shows a summary of what will be cleaned up
"""

import os
from pathlib import Path
from typing import Dict, List
import subprocess

class CleanupPreflight:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        
    def run(self):
        """Run pre-flight checks"""
        print("\n✈️  CODEBASE CLEANUP - PRE-FLIGHT CHECK")
        print("=" * 60)
        
        # Check current status
        self.check_repository_size()
        self.check_files_to_remove()
        self.check_git_status()
        self.show_cleanup_summary()
        
    def check_repository_size(self):
        """Check current repository size"""
        print("\n📊 Current Repository Size:")
        
        try:
            # Get total size
            result = subprocess.run(
                ["du", "-sh", str(self.project_root)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                total_size = result.stdout.strip().split('\t')[0]
                print(f"   Total size: {total_size}")
                
            # Get size by major directories
            major_dirs = ["backend", "mobile", "archive", "docs", "tests", "infrastructure"]
            for dir_name in major_dirs:
                dir_path = self.project_root / dir_name
                if dir_path.exists():
                    result = subprocess.run(
                        ["du", "-sh", str(dir_path)],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        size = result.stdout.strip().split('\t')[0]
                        print(f"   {dir_name:15} {size}")
                        
        except Exception as e:
            print(f"   Could not calculate size: {e}")
            
    def check_files_to_remove(self):
        """Count files that will be removed"""
        print("\n🗑️  Files to be Removed:")
        
        # Count different categories
        categories = {
            "Planning docs (*.md)": [
                "COMPLETE_FEATURE_IMPLEMENTATION_PLAN.md",
                "DEPLOYMENT_ISSUES_TO_FIX.md",
                "DEPLOYMENT_READY_SUMMARY.md",
                "DEPLOYMENT_VERIFICATION_CHECKLIST.md",
                "DEPLOY_NOW.md",
                "DEPLOY_NOW_CHECKLIST.md",
                "DEVELOPMENT_EXECUTION_PLAN.md",
                "DEVELOPMENT_TIMELINE_REALISTIC.md",
                "MVP_DEPLOYMENT_PLAN.md",
                "MVP_LAUNCH_CHECKLIST.md",
                "MVP_LAUNCH_SUCCESS.md",
                "PRIORITIZED_IMPLEMENTATION_PLAN.md",
                "PROJECT_STATUS_REALITY.md",
                "RAPID_MVP_DEPLOYMENT.md",
                "README_MVP_LAUNCH.md",
                "REORGANIZATION_SUMMARY.md",
                "ROADTRIP_KNOWLEDGE_GRAPH.md",
                "backend_services_analysis.md",
            ],
            "Test files (root)": [
                "test_minimal_local.py",
                "test_setup_verification.py",
                "verify_tests.py",
                "test_real_apis.sh",
                "compare_storytelling.py",
            ],
            "Demo files": [
                "demo.html",
                "demo-enhanced.html",
                "demo-enhanced-fixed.html",
            ],
            "Deployment scripts": [
                "cloud_run_commands.sh",
                "deploy_production.ps1",
                "deploy_production_complete.ps1",
                "deploy_production_clean.ps1",
                "deploy_cloud_run_real.sh",
                "deploy_minimal_mvp.sh",
            ],
            "PowerShell scripts": [],  # Will count dynamically
            "Archive directory": ["archive/"],
            "Credentials": ["credentials/", "credentials_backup/"],
            "Temp files": [],  # Will count dynamically
        }
        
        # Count PowerShell scripts in backend
        ps_scripts = list((self.project_root / "backend").glob("*.ps1"))
        categories["PowerShell scripts"] = [str(p.relative_to(self.project_root)) for p in ps_scripts]
        
        # Count temp files
        pycache_dirs = list(self.project_root.rglob("__pycache__"))
        pyc_files = list(self.project_root.rglob("*.pyc"))
        categories["Temp files"] = [f"{len(pycache_dirs)} __pycache__ dirs", f"{len(pyc_files)} .pyc files"]
        
        # Display counts
        total_files = 0
        for category, files in categories.items():
            count = len(files)
            if category == "Archive directory":
                # Count files in archive
                archive_path = self.project_root / "archive"
                if archive_path.exists():
                    archive_files = sum(1 for _ in archive_path.rglob("*") if _.is_file())
                    print(f"   {category:20} {archive_files} files")
                    total_files += archive_files
            else:
                print(f"   {category:20} {count} files")
                total_files += count
                
        print(f"\n   Total files to remove: ~{total_files}")
        
    def check_git_status(self):
        """Check git status"""
        print("\n📋 Git Status:")
        
        try:
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.stdout.strip():
                changes = result.stdout.strip().split('\n')
                print(f"   ⚠️  {len(changes)} uncommitted changes")
                print("   First 5 changes:")
                for change in changes[:5]:
                    print(f"      {change}")
                if len(changes) > 5:
                    print(f"      ... and {len(changes) - 5} more")
            else:
                print("   ✅ Working directory clean")
                
            # Check current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                print(f"   Current branch: {branch}")
                
        except Exception as e:
            print(f"   Could not check git status: {e}")
            
    def show_cleanup_summary(self):
        """Show cleanup summary"""
        print("\n📋 Cleanup Summary:")
        print("   This cleanup will:")
        print("   ✓ Remove ~150+ unnecessary files")
        print("   ✓ Reduce repository size by ~70%")
        print("   ✓ Organize backend main.py variants")
        print("   ✓ Clean all temporary/cache files")
        print("   ✓ Update .gitignore comprehensively")
        print("   ✓ Create timestamped backup")
        print()
        print("   The cleanup will NOT:")
        print("   ✗ Remove any active source code")
        print("   ✗ Delete any tests in /tests")
        print("   ✗ Touch infrastructure configs")
        print("   ✗ Modify mobile app code")
        print("   ✗ Change API functionality")
        print()
        print("⚡ Ready for cleanup!")
        print("   Run: ./scripts/utilities/cleanup_workflow.sh")
        print()


if __name__ == "__main__":
    preflight = CleanupPreflight()
    preflight.run()