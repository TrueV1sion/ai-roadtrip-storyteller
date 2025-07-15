#!/usr/bin/env python3
"""
Debug Cleanup Implementation - Six Sigma DMAIC
Removes debug artifacts from production code
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict


class DebugCleaner:
    """Automated debug artifact removal."""
    
    def __init__(self):
        # Critical files identified from analysis
        self.critical_files = [
            'backend/app/core/db_optimized.py',
            'backend/app/core/enhanced_personalization.py',
            'backend/app/startup_production.py',
            'backend/app/services/response_time_optimizer.py',
            'backend/app/services/edge_voice_processor.py'
        ]
        
        # Patterns to clean
        self.cleanup_patterns = [
            # Remove print statements (except in functions/demos)
            (r'^(\s*)print\s*\(.*\)\s*$', r'\1# DEBUG: Removed print statement'),
            
            # Remove sensitive parameter logging
            (r'logger\.debug\(f?["\'].*[Pp]arameters.*{.*}.*["\']\)', 
             'logger.debug("Query executed")'),
            
            # Clean up verbose debug logging
            (r'logger\.debug\(f?["\'].*{.*}.*["\'].*\)', 
             'logger.debug("Operation completed")'),
        ]
    
    def clean_file(self, filepath: str) -> Tuple[int, List[str]]:
        """Clean debug artifacts from a single file."""
        changes = []
        lines_modified = 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified_lines = []
            inside_demo = False
            
            for i, line in enumerate(lines):
                original_line = line
                
                # Check if we're in a demo section
                if 'if __name__ == "__main__"' in line:
                    inside_demo = True
                elif inside_demo and line.strip() == '':
                    inside_demo = False
                
                # Skip cleanup in demo sections
                if not inside_demo:
                    for pattern, replacement in self.cleanup_patterns:
                        if re.match(pattern, line):
                            line = re.sub(pattern, replacement, line)
                            if line != original_line:
                                lines_modified += 1
                                changes.append(f"Line {i+1}: {original_line.strip()} -> {line.strip()}")
                
                modified_lines.append(line)
            
            # Write back if changes were made
            if lines_modified > 0:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(modified_lines)
            
            return lines_modified, changes
            
        except Exception as e:
            return 0, [f"Error processing file: {e}"]
    
    def clean_critical_files(self) -> Dict[str, any]:
        """Clean debug artifacts from critical production files."""
        results = {
            'files_processed': 0,
            'total_changes': 0,
            'file_results': {}
        }
        
        for filepath in self.critical_files:
            full_path = f'/mnt/c/users/jared/onedrive/desktop/roadtrip/{filepath}'
            if os.path.exists(full_path):
                lines_modified, changes = self.clean_file(full_path)
                results['files_processed'] += 1
                results['total_changes'] += lines_modified
                results['file_results'][filepath] = {
                    'lines_modified': lines_modified,
                    'changes': changes[:5]  # First 5 changes
                }
        
        return results


def main():
    """Execute debug cleanup."""
    cleaner = DebugCleaner()
    print("Starting Debug Cleanup...")
    
    results = cleaner.clean_critical_files()
    
    print(f"\nFiles processed: {results['files_processed']}")
    print(f"Total changes: {results['total_changes']}")
    
    for filepath, file_results in results['file_results'].items():
        if file_results['lines_modified'] > 0:
            print(f"\n{filepath}: {file_results['lines_modified']} changes")
            for change in file_results['changes']:
                print(f"  - {change}")


if __name__ == "__main__":
    main()