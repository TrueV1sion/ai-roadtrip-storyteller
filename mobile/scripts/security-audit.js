#!/usr/bin/env node

/**
 * Mobile Security Audit Script
 * Performs comprehensive security checks on the mobile codebase
 * Usage: node scripts/security-audit.js
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Security patterns to detect
const securityPatterns = {
  console: {
    pattern: /console\.(log|error|warn|info|debug|trace|time|timeEnd)\s*\(/g,
    severity: 'CRITICAL',
    message: 'Console statement found - exposes sensitive data'
  },
  hardcodedSecrets: {
    pattern: /(password|secret|token|key|apikey|api_key)\s*[:=]\s*["'][^"']+["']/gi,
    severity: 'CRITICAL',
    message: 'Hardcoded secret detected'
  },
  hardcodedUrls: {
    pattern: /https?:\/\/[^\s"']+\.(com|org|net|io|app|ai|dev)/g,
    severity: 'HIGH',
    message: 'Hardcoded URL found'
  },
  processEnv: {
    pattern: /process\.env\./g,
    severity: 'MEDIUM',
    message: 'Direct environment variable access'
  },
  asyncStorage: {
    pattern: /AsyncStorage\.(setItem|getItem)\s*\(\s*["'][^"']*["']/g,
    severity: 'MEDIUM',
    message: 'Unencrypted AsyncStorage usage'
  },
  base64Secrets: {
    pattern: /[A-Za-z0-9+/]{20,}={0,2}/g,
    severity: 'HIGH',
    message: 'Potential base64 encoded secret'
  },
  dangerousEval: {
    pattern: /eval\s*\(|new\s+Function\s*\(/g,
    severity: 'CRITICAL',
    message: 'Dangerous eval usage'
  },
  unsafeHttp: {
    pattern: /http:\/\//g,
    severity: 'HIGH',
    message: 'Unsafe HTTP protocol usage'
  }
};

// Files to exclude from audit
const excludePatterns = [
  '**/node_modules/**',
  '**/coverage/**',
  '**/*.test.ts',
  '**/*.test.tsx',
  '**/setupTests.ts',
  '**/security-audit.js'
];

// Acceptable patterns (whitelist)
const acceptablePatterns = {
  testFiles: /\.(test|spec)\.(ts|tsx|js|jsx)$/,
  mockData: /mock|fake|test|example/i,
  documentation: /\.(md|txt)$/
};

class SecurityAuditor {
  constructor() {
    this.findings = [];
    this.stats = {
      filesScanned: 0,
      totalFindings: 0,
      critical: 0,
      high: 0,
      medium: 0,
      low: 0
    };
  }

  auditFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    let fileFindings = [];

    // Check each security pattern
    Object.entries(securityPatterns).forEach(([name, config]) => {
      let match;
      const regex = new RegExp(config.pattern);
      
      while ((match = regex.exec(content)) !== null) {
        const lineNumber = content.substring(0, match.index).split('\n').length;
        const line = lines[lineNumber - 1];
        
        // Skip if it's in a comment
        if (line && (line.trim().startsWith('//') || line.trim().startsWith('*'))) {
          continue;
        }

        // Skip if it's test data
        if (acceptablePatterns.testFiles.test(filePath) && 
            acceptablePatterns.mockData.test(match[0])) {
          continue;
        }

        fileFindings.push({
          file: filePath,
          line: lineNumber,
          type: name,
          severity: config.severity,
          message: config.message,
          snippet: line ? line.trim() : match[0],
          match: match[0]
        });
      }
    });

    if (fileFindings.length > 0) {
      this.findings.push(...fileFindings);
      this.stats.filesScanned++;
      fileFindings.forEach(finding => {
        this.stats.totalFindings++;
        this.stats[finding.severity.toLowerCase()]++;
      });
    }

    return fileFindings.length;
  }

  generateReport() {
    console.log('\n🔒 MOBILE SECURITY AUDIT REPORT\n');
    console.log('=' .repeat(60));
    
    // Summary statistics
    console.log('\n📊 SUMMARY STATISTICS\n');
    console.log(`   Files Scanned: ${this.stats.filesScanned}`);
    console.log(`   Total Findings: ${this.stats.totalFindings}`);
    console.log(`   Critical: ${this.stats.critical} ⛔`);
    console.log(`   High: ${this.stats.high} 🔴`);
    console.log(`   Medium: ${this.stats.medium} 🟡`);
    console.log(`   Low: ${this.stats.low} 🟢`);

    // Group findings by severity
    const findingsBySeverity = {
      CRITICAL: [],
      HIGH: [],
      MEDIUM: [],
      LOW: []
    };

    this.findings.forEach(finding => {
      findingsBySeverity[finding.severity].push(finding);
    });

    // Display findings by severity
    ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].forEach(severity => {
      const findings = findingsBySeverity[severity];
      if (findings.length > 0) {
        console.log(`\n${'='.repeat(60)}`);
        console.log(`${severity} SEVERITY FINDINGS (${findings.length})`);
        console.log('='.repeat(60));

        // Group by type
        const byType = {};
        findings.forEach(f => {
          if (!byType[f.type]) byType[f.type] = [];
          byType[f.type].push(f);
        });

        Object.entries(byType).forEach(([type, items]) => {
          console.log(`\n${type.toUpperCase()} (${items.length} instances):`);
          
          // Show first 5 examples
          items.slice(0, 5).forEach(item => {
            console.log(`  📍 ${item.file}:${item.line}`);
            console.log(`     ${item.snippet.substring(0, 80)}...`);
          });
          
          if (items.length > 5) {
            console.log(`  ... and ${items.length - 5} more`);
          }
        });
      }
    });

    // Recommendations
    console.log('\n' + '='.repeat(60));
    console.log('🛡️  RECOMMENDATIONS\n');
    
    if (this.stats.critical > 0) {
      console.log('⛔ CRITICAL ACTIONS REQUIRED:');
      console.log('   1. Remove all console statements immediately');
      console.log('   2. Replace hardcoded secrets with secure storage');
      console.log('   3. Eliminate eval() usage completely');
      console.log('   4. Run: npm run remove:console');
    }

    if (this.stats.high > 0) {
      console.log('\n🔴 HIGH PRIORITY FIXES:');
      console.log('   1. Replace HTTP with HTTPS everywhere');
      console.log('   2. Move hardcoded URLs to configuration');
      console.log('   3. Review and secure base64 encoded values');
    }

    if (this.stats.medium > 0) {
      console.log('\n🟡 MEDIUM PRIORITY IMPROVEMENTS:');
      console.log('   1. Use secure storage instead of AsyncStorage');
      console.log('   2. Access environment variables through config service');
      console.log('   3. Implement proper key management');
    }

    // Generate JSON report for CI/CD
    const jsonReport = {
      timestamp: new Date().toISOString(),
      stats: this.stats,
      findings: this.findings,
      passed: this.stats.critical === 0
    };

    fs.writeFileSync(
      path.join(process.cwd(), 'security-audit-report.json'),
      JSON.stringify(jsonReport, null, 2)
    );

    console.log('\n📄 Detailed report saved to: security-audit-report.json');

    // Exit code based on findings
    if (this.stats.critical > 0) {
      console.log('\n❌ AUDIT FAILED - Critical security issues found!\n');
      process.exit(1);
    } else if (this.stats.high > 0) {
      console.log('\n⚠️  AUDIT WARNING - High severity issues found\n');
      process.exit(0);
    } else {
      console.log('\n✅ AUDIT PASSED - No critical issues found\n');
      process.exit(0);
    }
  }
}

// Main execution
function main() {
  console.log('🔍 Starting Mobile Security Audit...\n');

  const auditor = new SecurityAuditor();
  
  // Find all source files
  const files = glob.sync('src/**/*.{ts,tsx,js,jsx}', {
    ignore: excludePatterns,
    cwd: process.cwd()
  });

  console.log(`Scanning ${files.length} files...\n`);

  // Progress bar
  let processed = 0;
  files.forEach(file => {
    try {
      auditor.auditFile(file);
      processed++;
      if (processed % 10 === 0) {
        process.stdout.write(`\rProgress: ${processed}/${files.length} files`);
      }
    } catch (error) {
      console.error(`\n❌ Error scanning ${file}:`, error.message);
    }
  });

  console.log(`\n✅ Scan complete!\n`);

  // Generate and display report
  auditor.generateReport();
}

// Run the audit
main();