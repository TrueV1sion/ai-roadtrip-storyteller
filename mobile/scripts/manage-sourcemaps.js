#!/usr/bin/env node

/**
 * Source Map Management Script
 * Six Sigma DMAIC - Code Obfuscation Implementation
 * 
 * Manages source maps for production debugging while keeping them secure
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

const SOURCE_MAP_DIR = path.join(__dirname, '../.sourcemaps');
const BUILD_DIR = path.join(__dirname, '../build');

/**
 * Extract and secure source maps after build
 */
function extractSourceMaps() {
  console.log('📍 Extracting source maps...');
  
  // Create secure directory for source maps
  if (!fs.existsSync(SOURCE_MAP_DIR)) {
    fs.mkdirSync(SOURCE_MAP_DIR, { recursive: true });
  }
  
  // Find all source map files
  const sourceMapFiles = findSourceMaps(BUILD_DIR);
  
  sourceMapFiles.forEach(file => {
    const fileName = path.basename(file);
    const destPath = path.join(SOURCE_MAP_DIR, fileName);
    
    // Move source map to secure location
    fs.renameSync(file, destPath);
    console.log(`✅ Moved: ${fileName}`);
    
    // Create metadata
    createSourceMapMetadata(destPath);
  });
  
  console.log(`📦 Extracted ${sourceMapFiles.length} source maps`);
}

/**
 * Find all source map files recursively
 */
function findSourceMaps(dir) {
  const files = [];
  
  function traverse(currentDir) {
    const entries = fs.readdirSync(currentDir);
    
    entries.forEach(entry => {
      const fullPath = path.join(currentDir, entry);
      const stat = fs.statSync(fullPath);
      
      if (stat.isDirectory()) {
        traverse(fullPath);
      } else if (entry.endsWith('.map')) {
        files.push(fullPath);
      }
    });
  }
  
  traverse(dir);
  return files;
}

/**
 * Create metadata for source map
 */
function createSourceMapMetadata(sourceMapPath) {
  const content = fs.readFileSync(sourceMapPath, 'utf8');
  const hash = crypto.createHash('sha256').update(content).digest('hex');
  
  const metadata = {
    file: path.basename(sourceMapPath),
    hash,
    size: fs.statSync(sourceMapPath).size,
    created: new Date().toISOString(),
    build: process.env.BUILD_NUMBER || 'unknown',
  };
  
  const metadataPath = sourceMapPath.replace('.map', '.meta.json');
  fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));
}

/**
 * Upload source maps to secure storage (Sentry, internal server, etc.)
 */
function uploadSourceMaps() {
  console.log('☁️  Uploading source maps...');
  
  const sentryOrg = process.env.SENTRY_ORG;
  const sentryProject = process.env.SENTRY_PROJECT;
  const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN;
  
  if (!sentryOrg || !sentryProject || !sentryAuthToken) {
    console.warn('⚠️  Sentry configuration missing, skipping upload');
    return;
  }
  
  try {
    // Upload to Sentry
    execSync(
      `sentry-cli releases files ${process.env.BUILD_NUMBER || 'latest'} upload-sourcemaps ${SOURCE_MAP_DIR} --org ${sentryOrg} --project ${sentryProject}`,
      { stdio: 'inherit' }
    );
    
    console.log('✅ Source maps uploaded to Sentry');
  } catch (error) {
    console.error('❌ Failed to upload source maps:', error.message);
  }
}

/**
 * Clean up source maps after upload
 */
function cleanupSourceMaps() {
  console.log('🧹 Cleaning up source maps...');
  
  const files = fs.readdirSync(SOURCE_MAP_DIR);
  let cleaned = 0;
  
  files.forEach(file => {
    if (file.endsWith('.map')) {
      const filePath = path.join(SOURCE_MAP_DIR, file);
      const metaPath = filePath.replace('.map', '.meta.json');
      
      // Keep metadata, remove actual source map
      fs.unlinkSync(filePath);
      cleaned++;
    }
  });
  
  console.log(`✅ Cleaned ${cleaned} source map files`);
}

/**
 * Verify build has no embedded source maps
 */
function verifyNoSourceMaps() {
  console.log('🔍 Verifying no source maps in build...');
  
  const remainingMaps = findSourceMaps(BUILD_DIR);
  
  if (remainingMaps.length > 0) {
    console.error('❌ Found source maps in build directory:');
    remainingMaps.forEach(map => console.error(`   - ${map}`));
    process.exit(1);
  }
  
  console.log('✅ Build is clean of source maps');
}

/**
 * Main execution
 */
function main() {
  const command = process.argv[2];
  
  switch (command) {
    case 'extract':
      extractSourceMaps();
      break;
    case 'upload':
      uploadSourceMaps();
      break;
    case 'cleanup':
      cleanupSourceMaps();
      break;
    case 'verify':
      verifyNoSourceMaps();
      break;
    case 'all':
      extractSourceMaps();
      uploadSourceMaps();
      cleanupSourceMaps();
      verifyNoSourceMaps();
      break;
    default:
      console.log('Usage: node manage-sourcemaps.js [extract|upload|cleanup|verify|all]');
      process.exit(1);
  }
}

main();