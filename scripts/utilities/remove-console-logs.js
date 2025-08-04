#!/usr/bin/env node

/**
 * Script to remove all console.log statements from production code
 * and replace them with the proper logger service
 */

const fs = require('fs');
const path = require('path');

// Paths to exclude from console.log removal
const EXCLUDE_PATHS = [
  '**/node_modules/**',
  '**/__tests__/**',
  '**/*.test.*',
  '**/*.spec.*',
  '**/setupTests.*',
  '**/logger.ts', // The logger service itself
  '**/SentryService.ts', // Sentry configuration
  '**/performancePolyfills.js',
  '**/bundleOptimizer.js'
];

// Files that need manual review (security-sensitive)
const SECURITY_FILES = [];

// Patterns to match console statements
const CONSOLE_PATTERNS = [
  /console\.(log|error|warn|debug|info)\s*\(/g,
  /console\.(time|timeEnd)\s*\(/g,
  /console\.(trace|assert|dir|table)\s*\(/g
];

// Map console methods to logger methods
const METHOD_MAP = {
  'console.log': 'logger.debug',
  'console.error': 'logger.error',
  'console.warn': 'logger.warn',
  'console.debug': 'logger.debug',
  'console.info': 'logger.info',
  'console.time': 'logger.time',
  'console.timeEnd': 'logger.timeEnd'
};

let totalReplacements = 0;
let filesModified = 0;

function shouldExclude(filePath) {
  return EXCLUDE_PATHS.some(pattern => {
    const regex = new RegExp(pattern.replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*'));
    return regex.test(filePath);
  });
}

function processFile(filePath) {
  if (shouldExclude(filePath)) {
    return;
  }

  let content = fs.readFileSync(filePath, 'utf8');
  let originalContent = content;
  let fileReplacements = 0;

  // Check if logger is already imported
  const hasLoggerImport = content.includes("from '@/services/logger'") || 
                         content.includes('from "../services/logger"') ||
                         content.includes("from './services/logger'");

  // Track if we need to add import
  let needsImport = false;

  // Replace console statements
  CONSOLE_PATTERNS.forEach(pattern => {
    content = content.replace(pattern, (match) => {
      // Special handling for console.time and console.timeEnd
      if (match.includes('console.time')) {
        fileReplacements++;
        needsImport = true;
        return match.replace('console.time', 'logger.time');
      }
      if (match.includes('console.timeEnd')) {
        fileReplacements++;
        needsImport = true;
        return match.replace('console.timeEnd', 'logger.timeEnd');
      }

      // For other console methods
      const method = match.match(/console\.\w+/)[0];
      const replacement = METHOD_MAP[method];
      
      if (replacement) {
        fileReplacements++;
        needsImport = true;
        
        // Special handling for console.error - need to extract error object if present
        if (method === 'console.error') {
          return match.replace(method, replacement);
        }
        
        return match.replace(method, replacement);
      }
      
      return match;
    });
  });

  // Add import if needed and not already present
  if (needsImport && !hasLoggerImport && fileReplacements > 0) {
    // Determine if it's a TypeScript or JavaScript file
    const isTypeScript = filePath.endsWith('.ts') || filePath.endsWith('.tsx');
    
    // Add import at the top of the file
    const importStatement = isTypeScript 
      ? "import { logger } from '@/services/logger';\n"
      : "import { logger } from '@/services/logger';\n";
    
    // Find the right place to insert the import
    const importRegex = /^(import\s+.*?\s+from\s+['"].*?['"];?\s*\n)+/m;
    const match = content.match(importRegex);
    
    if (match) {
      // Add after existing imports
      const lastImportEnd = match.index + match[0].length;
      content = content.slice(0, lastImportEnd) + importStatement + content.slice(lastImportEnd);
    } else {
      // Add at the beginning if no imports exist
      content = importStatement + '\n' + content;
    }
  }

  // Save if modified
  if (content !== originalContent) {
    fs.writeFileSync(filePath, content, 'utf8');
    filesModified++;
    totalReplacements += fileReplacements;
    
    if (SECURITY_FILES.includes(path.basename(filePath))) {
      console.log(`⚠️  SECURITY FILE MODIFIED: ${filePath} (${fileReplacements} replacements) - NEEDS REVIEW`);
    } else {
      console.log(`✓ Modified: ${filePath} (${fileReplacements} replacements)`);
    }
  }
}

function findFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      if (!shouldExclude(filePath)) {
        findFiles(filePath, fileList);
      }
    } else if (/\.(js|jsx|ts|tsx)$/.test(file)) {
      if (!shouldExclude(filePath)) {
        fileList.push(filePath);
      }
    }
  });
  
  return fileList;
}

function main() {
  console.log('🔍 Searching for console statements in mobile/src...\n');

  // Find all JavaScript and TypeScript files
  const srcPath = path.join('mobile', 'src');
  const files = findFiles(srcPath);

  console.log(`Found ${files.length} files to process\n`);

  // Process each file
  files.forEach(file => {
    processFile(file);
  });

  console.log('\n📊 Summary:');
  console.log(`Files modified: ${filesModified}`);
  console.log(`Total replacements: ${totalReplacements}`);
  
  if (filesModified > 0) {
    console.log('\n⚠️  Important:');
    console.log('1. Review the changes to ensure proper error handling');
    console.log('2. Run tests to verify functionality');
    console.log('3. Check that logger imports are correct');
    console.log('4. Some complex console statements may need manual adjustment');
  }
}

// Run the script
main();