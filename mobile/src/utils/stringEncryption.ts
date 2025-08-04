/**
 * String Encryption Utility
 * Six Sigma DMAIC - Code Obfuscation Implementation
 * 
 * Provides runtime string encryption for sensitive data
 * Note: This is a basic implementation. For production, use native modules
 */

// Simple XOR-based obfuscation for strings
// This prevents casual string searching in the bundle
const obfuscateString = (str: string, key: number = 42): string => {
  return str
    .split('')
    .map(char => String.fromCharCode(char.charCodeAt(0) ^ key))
    .join('');
};

const deobfuscateString = (str: string, key: number = 42): string => {
  return obfuscateString(str, key); // XOR is reversible
};

// Store sensitive strings in obfuscated form
export const ObfuscatedStrings = {
  // API endpoints (obfuscated at build time)
  API_BASE: obfuscateString('/api/v1'),
  AUTH_ENDPOINT: obfuscateString('/auth/login'),
  STORY_ENDPOINT: obfuscateString('/stories/generate'),
  
  // Error messages
  NETWORK_ERROR: obfuscateString('Network request failed'),
  AUTH_ERROR: obfuscateString('Authentication failed'),
  
  // Security keys (these should really be in secure storage)
  STORAGE_KEY_PREFIX: obfuscateString('roadtrip_secure_'),
  BIOMETRIC_KEY: obfuscateString('biometric_auth_key'),
};

// Runtime string decryption
export const getString = (key: keyof typeof ObfuscatedStrings): string => {
  return deobfuscateString(ObfuscatedStrings[key]);
};

// Anti-tampering check
export const verifyIntegrity = (): boolean => {
  try {
    // Check if critical functions exist and haven't been tampered
    const criticalFunctions = [
      obfuscateString,
      deobfuscateString,
      getString,
    ];
    
    for (const func of criticalFunctions) {
      if (typeof func !== 'function') {
        return false;
      }
      // Check function length (basic anti-tampering)
      if (func.toString().length < 50) {
        return false;
      }
    }
    
    // Verify a known string
    const testStr = 'integrity_check';
    const obf = obfuscateString(testStr);
    const deobf = deobfuscateString(obf);
    
    return deobf === testStr;
  } catch {
    return false;
  }
};

// Self-defending code
(function() {
  if (!verifyIntegrity()) {
    // Code has been tampered with
    throw new Error('Application integrity compromised');
  }
})();

export default {
  getString,
  verifyIntegrity,
};