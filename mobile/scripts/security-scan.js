#!/usr/bin/env node
/**
 * Security Scanner - Six Sigma CONTROL Phase
 * Scans codebase for hardcoded secrets and security issues
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Patterns to detect security issues
const securityPatterns = {
  hardcodedSecrets: [
    // API Keys
    /['\"](?:api[_-]?key|apikey)['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]/gi,
    /['\"](?:secret[_-]?key|secretkey)['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]/gi,
    
    // Placeholder values
    /['\"]your[_-].*[_-](?:key|id|secret)['\"]?/gi,
    /['\"]xxx+['\"]?/gi,
    /['\"]placeholder['\"]?/gi,
    
    // AWS
    /AKIA[0-9A-Z]{16}/g,
    /aws[_-]?access[_-]?key[_-]?id/gi,
    /aws[_-]?secret[_-]?access[_-]?key/gi,
    
    // Google
    /AIza[0-9A-Za-z\-_]{35}/g,
    /[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com/g,
    
    // Passwords
    /password\s*[:=]\s*['\"][^'\"]{4,}['\"](?!\s*\|\|)/gi,
    /pwd\s*[:=]\s*['\"][^'\"]{4,}['\"]/gi,
    
    // Private keys
    /-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----/g,
    /-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----/g,
  ],
  
  insecurePatterns: [
    // Hardcoded URLs with potential keys
    /https?:\/\/[^\/\s]+\/[^\/\s]*[?&](?:api[_-]?key|key|token)=[a-zA-Z0-9_\-]+/gi,
    
    // Base64 potential secrets
    /['\"](?:Basic|Bearer)\s+[A-Za-z0-9+\/]{40,}={0,2}['\"]/g,
    
    // Environment variables without validation
    /process\.env\.[A-Z_]+\s*\|\|\s*['\"][^'\"]+['\"](?!\s*===?\s*['\"]true['\"])/g,
    
    // Hardcoded IPs
    /['\"](?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)['\"](?!.*localhost)/g,
  ],
  
  testCredentials: [
    /test[_-]?(?:user|password|key|secret)/gi,
    /demo[_-]?(?:user|password|key|secret)/gi,
    /sample[_-]?(?:user|password|key|secret)/gi,
  ]
};

// Files to scan
const scanPatterns = [
  'src/**/*.{ts,tsx,js,jsx}',
  '*.{js,json}',
  '!node_modules/**',
  '!scripts/**',
  '!coverage/**',
  '!build/**',
  '!dist/**',
];

// Known false positives to ignore
const falsePositives = [
  'your_sentry_dsn_here', // Example value in .env.example
  'localhost',
  '127.0.0.1',
  '10.0.2.2', // Android emulator
];

function scanFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const issues = [];
  const lines = content.split('\n');
  
  // Check each pattern type
  Object.entries(securityPatterns).forEach(([type, patterns]) => {
    patterns.forEach(pattern => {
      const matches = content.matchAll(pattern);
      for (const match of matches) {
        // Skip false positives
        if (falsePositives.some(fp => match[0].includes(fp))) continue;
        
        // Find line number
        const lineNum = content.substring(0, match.index).split('\n').length;
        const line = lines[lineNum - 1];
        
        issues.push({
          type,
          file: path.relative(process.cwd(), filePath),
          line: lineNum,
          match: match[0],
          context: line.trim(),
          severity: type === 'hardcodedSecrets' ? 'HIGH' : 'MEDIUM'
        });
      }
    });
  });
  
  return issues;
}

function generateReport(allIssues) {
  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      total: allIssues.length,
      high: allIssues.filter(i => i.severity === 'HIGH').length,
      medium: allIssues.filter(i => i.severity === 'MEDIUM').length,
      byType: {}
    },
    issues: allIssues
  };
  
  // Count by type
  allIssues.forEach(issue => {
    report.summary.byType[issue.type] = (report.summary.byType[issue.type] || 0) + 1;
  });
  
  return report;
}

// Main execution
function main() {
  console.log('🔍 Security Scanner - Checking for hardcoded secrets...\n');
  
  const files = [];
  scanPatterns.forEach(pattern => {
    if (pattern.startsWith('!')) return;
    const matches = glob.sync(pattern);
    files.push(...matches);
  });
  
  console.log(`Scanning ${files.length} files...\n`);
  
  const allIssues = [];
  files.forEach(file => {
    const issues = scanFile(file);
    allIssues.push(...issues);
  });
  
  if (allIssues.length === 0) {
    console.log('✅ No security issues found!');
    process.exit(0);
  }
  
  // Generate report
  const report = generateReport(allIssues);
  
  // Display results
  console.log(`❌ Found ${report.summary.total} security issues:\n`);
  console.log(`🔴 HIGH severity: ${report.summary.high}`);
  console.log(`🟡 MEDIUM severity: ${report.summary.medium}\n`);
  
  console.log('Issues by type:');
  Object.entries(report.summary.byType).forEach(([type, count]) => {
    console.log(`  ${type}: ${count}`);
  });
  
  console.log('\nDetailed findings:');
  allIssues.forEach(issue => {
    console.log(`\n[${issue.severity}] ${issue.file}:${issue.line}`);
    console.log(`Type: ${issue.type}`);
    console.log(`Match: ${issue.match}`);
    console.log(`Context: ${issue.context}`);
  });
  
  // Save report
  const reportPath = 'security-scan-report.json';
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\n📄 Full report saved to: ${reportPath}`);
  
  // Exit with error if HIGH severity issues found
  process.exit(report.summary.high > 0 ? 1 : 0);
}

// Run scanner
main();