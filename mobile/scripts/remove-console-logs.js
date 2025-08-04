#!/usr/bin/env node
/**
 * Console Statement Removal Script
 * Six Sigma DMAIC - IMPROVE Phase Implementation
 * 
 * This script removes all console.* statements from the codebase
 * and replaces them with a secure logging service
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Configuration
const config = {
  rootDir: path.join(__dirname, '..'),
  includePatterns: [
    'src/**/*.ts',
    'src/**/*.tsx',
    'src/**/*.js',
    'src/**/*.jsx'
  ],
  excludePatterns: [
    '**/node_modules/**',
    '**/scripts/**',
    '**/__tests__/**',
    '**/logger.ts' // Don't modify the logger itself
  ],
  backupDir: path.join(__dirname, '../.console-backup'),
  dryRun: process.argv.includes('--dry-run'),
  verbose: process.argv.includes('--verbose')
};

// Statistics tracking
const stats = {
  filesProcessed: 0,
  consoleLogsRemoved: 0,
  consoleErrorsReplaced: 0,
  consoleWarnsReplaced: 0,
  otherConsolesRemoved: 0,
  errors: []
};

// Create logger service if it doesn't exist
const loggerServicePath = path.join(config.rootDir, 'src/services/logger.ts');
const loggerServiceContent = `/**
 * Secure Logging Service
 * Replaces console.* statements to prevent information leakage
 */

import * as Sentry from 'sentry-expo';

export interface LogContext {
  [key: string]: any;
}

class Logger {
  private isDev = __DEV__;

  debug(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.log(\`[DEBUG] \${message}\`, context);
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.info(\`[INFO] \${message}\`, context);
    }
  }

  warn(message: string, context?: LogContext): void {
    if (this.isDev) {
      console.warn(\`[WARN] \${message}\`, context);
    }
    // Send warnings to monitoring in production
    if (!this.isDev && Sentry.Native) {
      Sentry.Native.captureMessage(message, 'warning');
    }
  }

  error(message: string, error?: Error | any, context?: LogContext): void {
    if (this.isDev) {
      console.error(\`[ERROR] \${message}\`, error, context);
    }
    // Always send errors to crash reporting
    if (Sentry.Native) {
      if (error instanceof Error) {
        Sentry.Native.captureException(error, {
          contexts: { custom: context },
          tags: { component: 'logger' }
        });
      } else {
        Sentry.Native.captureMessage(\`\${message}: \${JSON.stringify(error)}\`, 'error');
      }
    }
  }

  // Network logging (only in dev)
  network(method: string, url: string, data?: any): void {
    if (this.isDev) {
      console.log(\`[NETWORK] \${method} \${url}\`, data);
    }
  }

  // Performance logging
  performance(metric: string, value: number, unit: string = 'ms'): void {
    if (this.isDev) {
      console.log(\`[PERF] \${metric}: \${value}\${unit}\`);
    }
    // Could send to analytics in production
  }
}

export const logger = new Logger();
export default logger;
`;

// Console statement patterns
const consolePatterns = [
  // Standard console methods
  /console\s*\.\s*(log|error|warn|info|debug|trace|assert|dir|dirxml|group|groupEnd|time|timeEnd|count|profile)\s*\(/g,
  // Console with square brackets
  /console\s*\[\s*['"`](\w+)['"`]\s*\]\s*\(/g,
  // Destructured console
  /const\s*{\s*(\w+)\s*}\s*=\s*console/g,
  // Console in conditionals
  /(\|\||&&)\s*console\s*\.\s*\w+\s*\(/g
];

// Create backup directory
function createBackup() {
  if (!config.dryRun && !fs.existsSync(config.backupDir)) {
    fs.mkdirSync(config.backupDir, { recursive: true });
  }
}

// Get all files to process
function getFiles() {
  const files = [];
  config.includePatterns.forEach(pattern => {
    const matches = glob.sync(pattern, {
      cwd: config.rootDir,
      ignore: config.excludePatterns
    });
    files.push(...matches.map(f => path.join(config.rootDir, f)));
  });
  return [...new Set(files)]; // Remove duplicates
}

// Process a single file
function processFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    let modified = content;
    let fileStats = {
      logs: 0,
      errors: 0,
      warns: 0,
      others: 0
    };
    let hasChanges = false;

    // Check if file already imports logger
    const hasLoggerImport = /import\s+.*logger.*from\s+['"].*logger['"]/.test(content);
    
    // Replace console statements
    consolePatterns.forEach(pattern => {
      const matches = content.match(pattern);
      if (matches) {
        hasChanges = true;
        modified = modified.replace(pattern, (match, method) => {
          // Count by type
          if (match.includes('.log')) fileStats.logs++;
          else if (match.includes('.error')) fileStats.errors++;
          else if (match.includes('.warn')) fileStats.warns++;
          else fileStats.others++;

          // In dry run, just count
          if (config.dryRun) return match;

          // Replace based on method
          if (match.includes('.log') || match.includes('.debug')) {
            return match.replace(/console\s*\.\s*(log|debug)/, 'logger.debug');
          } else if (match.includes('.error')) {
            return match.replace(/console\s*\.\s*error/, 'logger.error');
          } else if (match.includes('.warn')) {
            return match.replace(/console\s*\.\s*warn/, 'logger.warn');
          } else if (match.includes('.info')) {
            return match.replace(/console\s*\.\s*info/, 'logger.info');
          } else {
            // Remove other console methods
            return '// ' + match;
          }
        });
      }
    });

    // Add logger import if needed and file was modified
    if (!hasLoggerImport && modified !== content && !config.dryRun) {
      // Find the right place to add import
      const importMatch = modified.match(/^(import\s+.*\s+from\s+['"].*['"];?\s*\n)+/m);
      if (importMatch) {
        const lastImportEnd = importMatch.index + importMatch[0].length;
        modified = modified.slice(0, lastImportEnd) + 
                  "import { logger } from '@/services/logger';\n" +
                  modified.slice(lastImportEnd);
      } else {
        // No imports found, add at the beginning
        modified = "import { logger } from '@/services/logger';\n\n" + modified;
      }
    }

    // Save changes
    if (hasChanges) {
      stats.filesProcessed++;
      stats.consoleLogsRemoved += fileStats.logs;
      stats.consoleErrorsReplaced += fileStats.errors;
      stats.consoleWarnsReplaced += fileStats.warns;
      stats.otherConsolesRemoved += fileStats.others;

      if (!config.dryRun) {
        // Backup original
        const backupPath = path.join(config.backupDir, path.relative(config.rootDir, filePath));
        fs.mkdirSync(path.dirname(backupPath), { recursive: true });
        fs.copyFileSync(filePath, backupPath);
        
        // Write modified
        fs.writeFileSync(filePath, modified, 'utf8');
      }

      if (config.verbose) {
        console.log(`✓ ${path.relative(config.rootDir, filePath)}: ${fileStats.logs + fileStats.errors + fileStats.warns + fileStats.others} console statements`);
      }
    }
  } catch (error) {
    stats.errors.push({ file: filePath, error: error.message });
  }
}

// Main execution
function main() {
  console.log('🔒 Console Statement Removal Tool');
  console.log('================================\n');

  if (config.dryRun) {
    console.log('🏃 Running in DRY RUN mode - no files will be modified\n');
  }

  // Create logger service
  if (!config.dryRun && !fs.existsSync(loggerServicePath)) {
    fs.mkdirSync(path.dirname(loggerServicePath), { recursive: true });
    fs.writeFileSync(loggerServicePath, loggerServiceContent, 'utf8');
    console.log('✅ Created secure logging service\n');
  }

  // Create backup directory
  createBackup();

  // Get and process files
  const files = getFiles();
  console.log(`📁 Found ${files.length} files to process\n`);

  files.forEach(file => processFile(file));

  // Report results
  console.log('\n📊 Results:');
  console.log('===========');
  console.log(`Files processed: ${stats.filesProcessed}`);
  console.log(`Console.log removed: ${stats.consoleLogsRemoved}`);
  console.log(`Console.error replaced: ${stats.consoleErrorsReplaced}`);
  console.log(`Console.warn replaced: ${stats.consoleWarnsReplaced}`);
  console.log(`Other consoles removed: ${stats.otherConsolesRemoved}`);
  console.log(`Total statements: ${stats.consoleLogsRemoved + stats.consoleErrorsReplaced + stats.consoleWarnsReplaced + stats.otherConsolesRemoved}`);

  if (stats.errors.length > 0) {
    console.log(`\n❌ Errors (${stats.errors.length}):`);
    stats.errors.forEach(err => {
      console.log(`  - ${err.file}: ${err.error}`);
    });
  }

  if (!config.dryRun) {
    console.log(`\n✅ Backup created at: ${config.backupDir}`);
    console.log('\n🎯 Next steps:');
    console.log('1. Review changes with: git diff');
    console.log('2. Test the app thoroughly');
    console.log('3. Configure Metro bundler for production builds');
    console.log('4. Run: npm test');
  } else {
    console.log('\n💡 Run without --dry-run to apply changes');
  }

  process.exit(stats.errors.length > 0 ? 1 : 0);
}

// Run the script
main();