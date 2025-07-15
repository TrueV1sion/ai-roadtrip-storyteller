#!/usr/bin/env python3
"""
Comprehensive Debug Cleanup - Six Sigma DMAIC Implementation
Removes all debug artifacts from production code with validation
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime


class ComprehensiveDebugCleaner:
    """Production-ready debug artifact removal system."""
    
    def __init__(self):
        self.base_path = Path("/mnt/c/users/jared/onedrive/desktop/roadtrip")
        self.cleanup_stats = {
            'files_processed': 0,
            'artifacts_removed': 0,
            'security_fixes': 0,
            'errors': []
        }
        
        # Define cleanup rules
        self.cleanup_rules = [
            # Remove parameter logging (security risk)
            {
                'pattern': r'logger\.debug\(.*[Pp]arameters?[^)]*\)',
                'replacement': 'logger.debug("Query executed successfully")',
                'type': 'security',
                'description': 'Remove parameter logging'
            },
            # Remove query logging with values
            {
                'pattern': r'logger\.debug\(f?["\'].*[Qq]uery:?\s*{[^}]+}.*["\']\)',
                'replacement': 'logger.debug("Database query executed")',
                'type': 'security',
                'description': 'Remove query value logging'
            },
            # Remove user data logging
            {
                'pattern': r'logger\.debug\(.*user_id.*\)',
                'replacement': 'logger.debug("User operation completed")',
                'type': 'security',
                'description': 'Remove user data logging'
            },
            # Comment out print statements (not in demos)
            {
                'pattern': r'^(\s*)print\s*\(',
                'replacement': r'\1# print(',
                'type': 'debug',
                'description': 'Comment out print statements',
                'skip_in_demo': True
            },
            # Remove verbose debug logging
            {
                'pattern': r'logger\.debug\(f?["\'][^"\']*(\{[^}]+\})+[^"\']["\']\)',
                'replacement': 'logger.debug("Operation completed")',
                'type': 'performance',
                'description': 'Simplify verbose debug logging'
            }
        ]
    
    def should_process_file(self, filepath: Path) -> bool:
        """Check if file should be processed."""
        # Skip test files
        if 'test' in str(filepath).lower():
            return False
        
        # Skip specific directories
        skip_dirs = ['__pycache__', 'node_modules', '.git', 'venv', 'tests']
        for skip_dir in skip_dirs:
            if skip_dir in filepath.parts:
                return False
        
        # Only process Python files for now
        return filepath.suffix == '.py'
    
    def clean_file(self, filepath: Path) -> Dict[str, Any]:
        """Clean debug artifacts from a single file."""
        result = {
            'file': str(filepath.relative_to(self.base_path)),
            'changes': [],
            'errors': []
        }
        
        try:
            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Track if we're in a demo section
            in_demo = False
            modified_content = content
            
            # Check for demo section
            if 'if __name__ == "__main__"' in content:
                in_demo = True
            
            # Apply cleanup rules
            for rule in self.cleanup_rules:
                if rule.get('skip_in_demo') and in_demo:
                    continue
                
                # Count matches before replacement
                matches = len(re.findall(rule['pattern'], modified_content, re.MULTILINE))
                
                if matches > 0:
                    # Apply replacement
                    modified_content = re.sub(
                        rule['pattern'], 
                        rule['replacement'], 
                        modified_content,
                        flags=re.MULTILINE
                    )
                    
                    result['changes'].append({
                        'type': rule['type'],
                        'description': rule['description'],
                        'count': matches
                    })
                    
                    # Update stats
                    self.cleanup_stats['artifacts_removed'] += matches
                    if rule['type'] == 'security':
                        self.cleanup_stats['security_fixes'] += matches
            
            # Write back if changes were made
            if result['changes']:
                # Backup original
                backup_path = filepath.with_suffix('.py.debug_backup')
                shutil.copy2(filepath, backup_path)
                
                # Write cleaned content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                result['backup'] = str(backup_path)
            
        except Exception as e:
            result['errors'].append(str(e))
            self.cleanup_stats['errors'].append({
                'file': str(filepath),
                'error': str(e)
            })
        
        return result
    
    def clean_codebase(self) -> Dict[str, Any]:
        """Clean entire codebase."""
        results = {
            'start_time': datetime.now().isoformat(),
            'files': [],
            'summary': {}
        }
        
        # Find all Python files
        python_files = list(self.base_path.glob('**/*.py'))
        
        # Process each file
        for filepath in python_files:
            if self.should_process_file(filepath):
                self.cleanup_stats['files_processed'] += 1
                file_result = self.clean_file(filepath)
                
                if file_result['changes']:
                    results['files'].append(file_result)
        
        # Add summary
        results['end_time'] = datetime.now().isoformat()
        results['summary'] = self.cleanup_stats
        
        return results
    
    def validate_cleanup(self) -> Dict[str, Any]:
        """Validate that cleanup was successful."""
        validation = {
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'passed': True
        }
        
        # Check for remaining debug artifacts
        remaining_artifacts = {
            'print_statements': 0,
            'parameter_logging': 0,
            'verbose_debug': 0
        }
        
        python_files = list(self.base_path.glob('**/*.py'))
        
        for filepath in python_files:
            if self.should_process_file(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for print statements (not commented)
                    if re.search(r'^\s*print\s*\(', content, re.MULTILINE):
                        remaining_artifacts['print_statements'] += 1
                    
                    # Check for parameter logging
                    if re.search(r'logger\.debug.*[Pp]arameters', content):
                        remaining_artifacts['parameter_logging'] += 1
                    
                    # Check for verbose debug
                    if re.search(r'logger\.debug\(.*\{.*\}', content):
                        remaining_artifacts['verbose_debug'] += 1
                        
                except Exception:
                    pass
        
        # Add validation checks
        for artifact_type, count in remaining_artifacts.items():
            check = {
                'type': artifact_type,
                'remaining': count,
                'passed': count == 0
            }
            validation['checks'].append(check)
            if count > 0:
                validation['passed'] = False
        
        # Calculate DPMO
        total_files = self.cleanup_stats['files_processed']
        total_remaining = sum(remaining_artifacts.values())
        
        if total_files > 0:
            validation['dpmo'] = (total_remaining / total_files) * 1_000_000
        else:
            validation['dpmo'] = 0
        
        # Calculate Six Sigma level
        if validation['dpmo'] > 0:
            import math
            validation['sigma_level'] = 0.8406 + math.sqrt(29.37 - 2.221 * math.log(validation['dpmo']))
        else:
            validation['sigma_level'] = 6.0
        
        return validation


def main():
    """Execute comprehensive debug cleanup."""
    print("\n" + "=" * 60)
    print("COMPREHENSIVE DEBUG CLEANUP - SIX SIGMA IMPLEMENTATION")
    print("=" * 60 + "\n")
    
    cleaner = ComprehensiveDebugCleaner()
    
    # Phase 1: Clean codebase
    print("Phase 1: Cleaning debug artifacts...")
    cleanup_results = cleaner.clean_codebase()
    
    # Save results
    with open('debug_cleanup_results.json', 'w') as f:
        json.dump(cleanup_results, f, indent=2)
    
    print(f"\nFiles processed: {cleaner.cleanup_stats['files_processed']}")
    print(f"Artifacts removed: {cleaner.cleanup_stats['artifacts_removed']}")
    print(f"Security fixes: {cleaner.cleanup_stats['security_fixes']}")
    print(f"Errors: {len(cleaner.cleanup_stats['errors'])}")
    
    # Phase 2: Validate cleanup
    print("\nPhase 2: Validating cleanup...")
    validation = cleaner.validate_cleanup()
    
    with open('debug_cleanup_validation.json', 'w') as f:
        json.dump(validation, f, indent=2)
    
    print(f"\nValidation Results:")
    print(f"DPMO: {validation['dpmo']:.1f}")
    print(f"Sigma Level: {validation['sigma_level']:.2f}")
    print(f"Status: {'PASSED' if validation['passed'] else 'FAILED'}")
    
    if not validation['passed']:
        print("\nRemaining artifacts:")
        for check in validation['checks']:
            if not check['passed']:
                print(f"  - {check['type']}: {check['remaining']}")
    
    print("\nCleanup complete! Backup files created with .debug_backup extension.")
    

if __name__ == "__main__":
    main()