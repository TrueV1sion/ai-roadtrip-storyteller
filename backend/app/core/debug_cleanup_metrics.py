#!/usr/bin/env python3
"""
Debug Cleanup Metrics - Six Sigma DMAIC Implementation
Measures and tracks removal of debug artifacts from production code
"""

import os
import re
import json
import subprocess
from typing import Dict, List, Tuple, Any
from datetime import datetime
from pathlib import Path


class DebugCleanupMetrics:
    """Metrics collection for debug artifact cleanup."""
    
    def __init__(self):
        self.base_path = Path("/mnt/c/users/jared/onedrive/desktop/roadtrip")
        self.patterns = {
            'print_statements': r'\bprint\s*\(',
            'console_logs': r'console\.(log|debug|warn|error)\s*\(',
            'debug_logger': r'logger\.debug\s*\(',
            'debug_flags': r'DEBUG\s*=\s*True',
            'todo_fixme': r'(TODO|FIXME).*debug',
            'commented_debug': r'#.*\b(print|console\.log|debug)\b'
        }
        
        # Files to exclude from cleanup
        self.exclude_patterns = [
            '*/tests/*',
            '*/test_*',
            '*_test.py',
            '*.test.js',
            '*.test.ts',
            '*/node_modules/*',
            '*/.git/*',
            '*/venv/*',
            '*/__pycache__/*',
            '*/dmaic_*',
            '*/debug_cleanup_*'
        ]
        
        # Security-sensitive patterns
        self.security_patterns = {
            'parameter_logging': r'logger\.debug.*[Pp]arameters?.*{',
            'query_logging': r'logger\.debug.*[Qq]uery.*{',
            'user_data_logging': r'logger\.debug.*(user|User|USER)',
            'token_logging': r'logger\.debug.*(token|Token|TOKEN)',
            'password_logging': r'logger\.debug.*(password|Password|PASSWORD)'
        }
    
    def scan_codebase(self) -> Dict[str, Any]:
        """Scan codebase for debug artifacts."""
        results = {
            'scan_timestamp': datetime.now().isoformat(),
            'total_files_scanned': 0,
            'artifacts_by_type': {},
            'files_with_artifacts': [],
            'security_concerns': [],
            'metrics': {
                'total_artifacts': 0,
                'artifacts_per_file': 0,
                'security_risk_count': 0
            }
        }
        
        # Scan Python files
        python_files = list(self.base_path.glob('**/*.py'))
        
        # Scan JavaScript/TypeScript files
        js_files = list(self.base_path.glob('**/*.js'))
        ts_files = list(self.base_path.glob('**/*.ts'))
        tsx_files = list(self.base_path.glob('**/*.tsx'))
        
        all_files = python_files + js_files + ts_files + tsx_files
        
        # Filter out excluded files
        included_files = []
        for file_path in all_files:
            if not any(file_path.match(pattern) for pattern in self.exclude_patterns):
                included_files.append(file_path)
        
        results['total_files_scanned'] = len(included_files)
        
        # Initialize counters
        for pattern_name in self.patterns:
            results['artifacts_by_type'][pattern_name] = {
                'count': 0,
                'files': []
            }
        
        # Scan each file
        for file_path in included_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                file_artifacts = self._scan_file_content(
                    content, 
                    file_path, 
                    results
                )
                
                if file_artifacts > 0:
                    results['files_with_artifacts'].append({
                        'path': str(file_path.relative_to(self.base_path)),
                        'artifact_count': file_artifacts
                    })
                    
            except Exception as e:
                # Skip files that can't be read
                pass
        
        # Calculate metrics
        total_artifacts = sum(
            data['count'] for data in results['artifacts_by_type'].values()
        )
        results['metrics']['total_artifacts'] = total_artifacts
        
        if results['total_files_scanned'] > 0:
            results['metrics']['artifacts_per_file'] = (
                total_artifacts / results['total_files_scanned']
            )
        
        results['metrics']['security_risk_count'] = len(results['security_concerns'])
        
        # Calculate DPMO (Defects Per Million Opportunities)
        # Opportunity = each line of code could have a debug artifact
        total_lines = self._count_total_lines(included_files)
        if total_lines > 0:
            results['metrics']['dpmo'] = (total_artifacts / total_lines) * 1_000_000
        else:
            results['metrics']['dpmo'] = 0
        
        return results
    
    def _scan_file_content(
        self, 
        content: str, 
        file_path: Path, 
        results: Dict
    ) -> int:
        """Scan file content for debug artifacts."""
        artifact_count = 0
        lines = content.split('\n')
        
        # Check each pattern
        for pattern_name, pattern in self.patterns.items():
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            
            if matches:
                results['artifacts_by_type'][pattern_name]['count'] += len(matches)
                
                # Store file info with line numbers
                file_info = {
                    'path': str(file_path.relative_to(self.base_path)),
                    'occurrences': []
                }
                
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    file_info['occurrences'].append({
                        'line': line_num,
                        'text': lines[line_num - 1].strip()[:80]  # First 80 chars
                    })
                    artifact_count += 1
                
                results['artifacts_by_type'][pattern_name]['files'].append(file_info)
        
        # Check security patterns
        for pattern_name, pattern in self.security_patterns.items():
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            
            if matches:
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    results['security_concerns'].append({
                        'type': pattern_name,
                        'file': str(file_path.relative_to(self.base_path)),
                        'line': line_num,
                        'text': lines[line_num - 1].strip()[:80]
                    })
        
        return artifact_count
    
    def _count_total_lines(self, files: List[Path]) -> int:
        """Count total lines of code."""
        total_lines = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    total_lines += len(f.readlines())
            except:
                pass
                
        return total_lines
    
    def generate_cleanup_plan(self, scan_results: Dict) -> Dict[str, Any]:
        """Generate prioritized cleanup plan."""
        plan = {
            'generated_at': datetime.now().isoformat(),
            'priority_actions': [],
            'file_modifications': [],
            'estimated_impact': {}
        }
        
        # Priority 1: Security concerns
        if scan_results['security_concerns']:
            plan['priority_actions'].append({
                'priority': 1,
                'action': 'Remove security-sensitive debug logging',
                'count': len(scan_results['security_concerns']),
                'files': list(set(
                    c['file'] for c in scan_results['security_concerns']
                ))
            })
        
        # Priority 2: Print statements in production code
        print_data = scan_results['artifacts_by_type'].get('print_statements', {})
        if print_data['count'] > 0:
            plan['priority_actions'].append({
                'priority': 2,
                'action': 'Remove print statements',
                'count': print_data['count'],
                'files': [f['path'] for f in print_data['files']]
            })
        
        # Priority 3: Debug logger calls
        debug_data = scan_results['artifacts_by_type'].get('debug_logger', {})
        if debug_data['count'] > 0:
            plan['priority_actions'].append({
                'priority': 3,
                'action': 'Review and remove unnecessary debug logging',
                'count': debug_data['count'],
                'files': [f['path'] for f in debug_data['files']]
            })
        
        # Generate file modification list
        files_to_modify = set()
        
        for artifact_type, data in scan_results['artifacts_by_type'].items():
            for file_info in data['files']:
                files_to_modify.add(file_info['path'])
        
        plan['file_modifications'] = sorted(list(files_to_modify))
        
        # Estimate impact
        plan['estimated_impact'] = {
            'files_to_modify': len(files_to_modify),
            'artifacts_to_remove': scan_results['metrics']['total_artifacts'],
            'security_improvements': scan_results['metrics']['security_risk_count'],
            'performance_gain': 'Reduced I/O operations and log volume',
            'dpmo_improvement': f"From {scan_results['metrics']['dpmo']:.1f} to 0.0"
        }
        
        return plan
    
    def validate_cleanup(self, before_metrics: Dict, after_metrics: Dict) -> Dict:
        """Validate cleanup effectiveness."""
        validation = {
            'timestamp': datetime.now().isoformat(),
            'artifacts_removed': {
                'total': (
                    before_metrics['metrics']['total_artifacts'] - 
                    after_metrics['metrics']['total_artifacts']
                ),
                'by_type': {}
            },
            'security_improvements': (
                before_metrics['metrics']['security_risk_count'] - 
                after_metrics['metrics']['security_risk_count']
            ),
            'dpmo_improvement': {
                'before': before_metrics['metrics']['dpmo'],
                'after': after_metrics['metrics']['dpmo'],
                'reduction_percent': 0
            },
            'success_rate': 0
        }
        
        # Calculate removal by type
        for artifact_type in before_metrics['artifacts_by_type']:
            before_count = before_metrics['artifacts_by_type'][artifact_type]['count']
            after_count = after_metrics['artifacts_by_type'][artifact_type]['count']
            validation['artifacts_removed']['by_type'][artifact_type] = {
                'removed': before_count - after_count,
                'remaining': after_count
            }
        
        # Calculate DPMO improvement
        if before_metrics['metrics']['dpmo'] > 0:
            reduction = (
                (before_metrics['metrics']['dpmo'] - after_metrics['metrics']['dpmo']) / 
                before_metrics['metrics']['dpmo'] * 100
            )
            validation['dpmo_improvement']['reduction_percent'] = reduction
        
        # Calculate success rate
        if before_metrics['metrics']['total_artifacts'] > 0:
            validation['success_rate'] = (
                validation['artifacts_removed']['total'] / 
                before_metrics['metrics']['total_artifacts'] * 100
            )
        
        return validation


def main():
    """Run debug cleanup metrics."""
    metrics = DebugCleanupMetrics()
    
    print("Debug Cleanup Metrics - Six Sigma Implementation")
    print("=" * 50)
    
    # Initial scan
    print("\nScanning codebase for debug artifacts...")
    scan_results = metrics.scan_codebase()
    
    # Save results
    with open('debug_cleanup_before.json', 'w') as f:
        json.dump(scan_results, f, indent=2)
    
    print(f"\nTotal files scanned: {scan_results['total_files_scanned']}")
    print(f"Total artifacts found: {scan_results['metrics']['total_artifacts']}")
    print(f"Security concerns: {scan_results['metrics']['security_risk_count']}")
    print(f"DPMO: {scan_results['metrics']['dpmo']:.1f}")
    
    # Generate cleanup plan
    print("\nGenerating cleanup plan...")
    plan = metrics.generate_cleanup_plan(scan_results)
    
    with open('debug_cleanup_plan.json', 'w') as f:
        json.dump(plan, f, indent=2)
    
    print(f"Files to modify: {plan['estimated_impact']['files_to_modify']}")
    print(f"Artifacts to remove: {plan['estimated_impact']['artifacts_to_remove']}")
    

if __name__ == "__main__":
    main()