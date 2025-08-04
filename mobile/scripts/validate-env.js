#!/usr/bin/env node

/**
 * Environment Configuration Validator
 * Ensures production builds have secure configuration
 */

const fs = require('fs');
const path = require('path');

const FORBIDDEN_PATTERNS = [
  // API Keys
  /AIza[0-9A-Za-z\-_]{35}/g,  // Google API Key
  /sk-[a-zA-Z0-9]{48}/g,      // OpenAI/Stripe style
  /[a-f0-9]{32}/g,            // Generic 32-char hex (API keys)
  
  // AWS
  /AKIA[0-9A-Z]{16}/g,        // AWS Access Key
  
  // Private Keys
  /-----BEGIN (RSA |EC )?PRIVATE KEY-----/g,
  
  // Passwords
  /password\s*[:=]\s*["'][^"']+["']/gi,
  /pwd\s*[:=]\s*["'][^"']+["']/gi,
  
  // Connection Strings
  /mongodb(\+srv)?:\/\/[^/\s]+:[^@\s]+@/g,
  /postgres(ql)?:\/\/[^:]+:[^@]+@/g,
  /mysql:\/\/[^:]+:[^@]+@/g,
  /redis:\/\/[^:]*:[^@]+@/g,
];

const REQUIRED_ENV_VARS = [
  'EXPO_PUBLIC_API_URL',
  'EXPO_PUBLIC_ENVIRONMENT',
];

const ALLOWED_ENV_PREFIXES = [
  'EXPO_PUBLIC_',  // Only EXPO_PUBLIC_ vars are exposed to client
];

function validateEnvFile(filePath) {
  console.log(`\n🔍 Validating ${path.basename(filePath)}...`);
  
  if (!fs.existsSync(filePath)) {
    console.log('⚠️  File not found, skipping');
    return true;
  }
  
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');
  let hasErrors = false;
  
  // Check for forbidden patterns
  FORBIDDEN_PATTERNS.forEach((pattern, index) => {
    const matches = content.match(pattern);
    if (matches) {
      console.error(`❌ Found potential secret (pattern ${index}):`, matches[0].substring(0, 20) + '...');
      hasErrors = true;
    }
  });
  
  // Parse environment variables
  const envVars = {};
  lines.forEach((line, lineNum) => {
    if (line.trim() && !line.startsWith('#')) {
      const match = line.match(/^([A-Z_]+[A-Z0-9_]*)=(.*)$/);
      if (match) {
        const [, key, value] = match;
        envVars[key] = value;
        
        // Check if variable name is allowed
        const isAllowed = ALLOWED_ENV_PREFIXES.some(prefix => key.startsWith(prefix));
        if (!isAllowed) {
          console.error(`❌ Line ${lineNum + 1}: Variable "${key}" doesn't have allowed prefix`);
          hasErrors = true;
        }
        
        // Check for API keys in values
        if (value && value.length > 20) {
          FORBIDDEN_PATTERNS.forEach((pattern) => {
            if (pattern.test(value)) {
              console.error(`❌ Line ${lineNum + 1}: Variable "${key}" contains potential secret`);
              hasErrors = true;
            }
          });
        }
      }
    }
  });
  
  // Check required variables
  REQUIRED_ENV_VARS.forEach(varName => {
    if (!envVars[varName]) {
      console.error(`❌ Missing required variable: ${varName}`);
      hasErrors = true;
    }
  });
  
  if (!hasErrors) {
    console.log('✅ Environment file is valid');
  }
  
  return !hasErrors;
}

function validateSourceCode() {
  console.log('\n🔍 Checking source code for hardcoded secrets...');
  
  const sourceFiles = [
    path.join(__dirname, '../src/config/api.ts'),
    path.join(__dirname, '../src/config/index.ts'),
    path.join(__dirname, '../src/services/apiService.ts'),
  ];
  
  let hasErrors = false;
  
  sourceFiles.forEach(file => {
    if (fs.existsSync(file)) {
      const content = fs.readFileSync(file, 'utf8');
      
      FORBIDDEN_PATTERNS.forEach((pattern) => {
        const matches = content.match(pattern);
        if (matches) {
          console.error(`❌ Found potential secret in ${path.basename(file)}:`, matches[0].substring(0, 20) + '...');
          hasErrors = true;
        }
      });
    }
  });
  
  if (!hasErrors) {
    console.log('✅ No hardcoded secrets found in source code');
  }
  
  return !hasErrors;
}

function validateEASConfig() {
  console.log('\n🔍 Validating EAS configuration...');
  
  const easConfigPath = path.join(__dirname, '../eas.json');
  if (!fs.existsSync(easConfigPath)) {
    console.error('❌ eas.json not found');
    return false;
  }
  
  const config = JSON.parse(fs.readFileSync(easConfigPath, 'utf8'));
  let hasErrors = false;
  
  // Check production build config
  const prodConfig = config.build?.production;
  if (!prodConfig) {
    console.error('❌ No production build configuration found');
    return false;
  }
  
  // Check environment variables
  const prodEnv = prodConfig.env || {};
  Object.entries(prodEnv).forEach(([key, value]) => {
    // Check if it's a secret reference
    if (typeof value === 'string' && value.startsWith('$') && value !== '$') {
      console.log(`✅ ${key} uses EAS secret: ${value}`);
    } else if (typeof value === 'string' && value.length > 20) {
      // Check for hardcoded secrets
      FORBIDDEN_PATTERNS.forEach((pattern) => {
        if (pattern.test(value)) {
          console.error(`❌ Potential secret in eas.json env.${key}`);
          hasErrors = true;
        }
      });
    }
  });
  
  if (!hasErrors) {
    console.log('✅ EAS configuration is valid');
  }
  
  return !hasErrors;
}

function main() {
  console.log('🔐 Environment Configuration Validator');
  console.log('=====================================');
  
  const results = {
    '.env': validateEnvFile(path.join(__dirname, '../.env')),
    '.env.production': validateEnvFile(path.join(__dirname, '../.env.production')),
    'source_code': validateSourceCode(),
    'eas_config': validateEASConfig(),
  };
  
  // Summary
  console.log('\n📊 Validation Summary:');
  Object.entries(results).forEach(([name, passed]) => {
    console.log(`  ${name}: ${passed ? '✅' : '❌'}`);
  });
  
  const allPassed = Object.values(results).every(r => r);
  
  if (allPassed) {
    console.log('\n✅ All environment validations passed!');
    console.log('The app is configured securely for production.');
    process.exit(0);
  } else {
    console.log('\n❌ Environment validation failed!');
    console.log('Please fix the issues above before building for production.');
    process.exit(1);
  }
}

// Run validation
main();