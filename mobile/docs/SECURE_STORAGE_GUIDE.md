# Secure Storage Implementation Guide

## Overview

This guide explains the secure storage implementation for the AI Road Trip Storyteller mobile app. All sensitive data must be stored using the SecureStorageService, which provides military-grade encryption and biometric protection.

## Quick Start

### Basic Usage

```typescript
import secureStorageService from '@/services/secureStorageService';

// Store sensitive data
await secureStorageService.setItem('user_token', 'sensitive-jwt-token');

// Retrieve sensitive data
const token = await secureStorageService.getItem('user_token');

// Remove sensitive data
await secureStorageService.removeItem('user_token');
```

### With Biometric Authentication

```typescript
// Store with biometric protection
await secureStorageService.setItem('payment_info', paymentData, {
  requireAuthentication: true,
  authenticationPrompt: 'Authenticate to save payment information',
});

// Retrieve with biometric verification
const paymentInfo = await secureStorageService.getItem('payment_info', {
  requireAuthentication: true,
  authenticationPrompt: 'Authenticate to access payment information',
});
```

## Security Architecture

### Encryption Details
- **Algorithm**: AES-256-CBC
- **Key Derivation**: PBKDF2 with 10,000 iterations
- **IV Generation**: Cryptographically secure random
- **Salt**: 32-byte random salt per encryption
- **Master Key**: Hardware-backed keychain/keystore

### Storage Tiers
1. **L1 - Keychain/Keystore**: Master encryption key
2. **L2 - SecureStore**: Encrypted sensitive data
3. **L3 - AsyncStorage**: Non-sensitive preferences only

## What to Store Securely

### MUST Use SecureStorage
- Authentication tokens (JWT, OAuth)
- Refresh tokens
- User credentials
- API keys
- Payment information
- Personal identifiable information (PII)
- Location history
- Voice recordings
- Medical/health data
- Biometric templates

### Safe for AsyncStorage
- Theme preferences
- Language settings
- Tutorial completion flags
- Non-sensitive app state
- Public content cache

## Migration from AsyncStorage

### Automatic Migration

```typescript
import SecureStorageMigration from '@/utils/secureStorageMigration';

// Check if migration needed
if (await SecureStorageMigration.isMigrationNeeded()) {
  // Perform migration
  const result = await SecureStorageMigration.performMigration();
  
  console.log(`Migrated ${result.migratedKeys.length} keys`);
  
  // Validate migration
  const isValid = await SecureStorageMigration.validateMigration();
  if (!isValid) {
    console.error('Migration validation failed');
  }
}
```

### Manual Migration

```typescript
// Migrate specific keys
await secureStorageService.migrateFromAsyncStorage([
  'access_token',
  'refresh_token',
  'user_credentials',
]);
```

## API Key Management

### Using Secure API Keys

```typescript
import secureApiKeyManager from '@/services/secureApiKeyManager';
import { API_SERVICES } from '@/services/secureApiKeyManager';

// Get API key (returns null if should use proxy)
const apiKey = await secureApiKeyManager.getApiKey(API_SERVICES.GOOGLE_MAPS);

if (apiKey) {
  // Use direct API call with key
  const response = await fetch(`https://maps.googleapis.com/maps/api?key=${apiKey}`);
} else {
  // Use proxy endpoint
  const proxyUrl = secureApiKeyManager.getProxyEndpoint(API_SERVICES.GOOGLE_MAPS);
  const response = await fetch(proxyUrl);
}
```

## Best Practices

### 1. Never Use AsyncStorage for Sensitive Data

```typescript
// ❌ NEVER DO THIS
await AsyncStorage.setItem('jwt_token', token);

// ✅ DO THIS INSTEAD
await secureStorageService.setItem('jwt_token', token);
```

### 2. Handle Errors Gracefully

```typescript
try {
  await secureStorageService.setItem('sensitive_data', data);
} catch (error) {
  if (error.message.includes('Authentication failed')) {
    // User cancelled biometric prompt
    showMessage('Authentication required to save data');
  } else {
    // Storage failure - DO NOT fallback to AsyncStorage
    showError('Unable to save data securely. Please try again.');
  }
}
```

### 3. Use Appropriate Keychain Accessibility

```typescript
import * as SecureStore from 'expo-secure-store';

// For highly sensitive data (default)
await secureStorageService.setItem('payment_data', data, {
  accessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
});

// For data needed in background
await secureStorageService.setItem('sync_token', token, {
  accessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
});
```

### 4. Clear Sensitive Data on Logout

```typescript
async function logout() {
  // Clear specific sensitive data
  await secureStorageService.removeItem('access_token');
  await secureStorageService.removeItem('refresh_token');
  await secureStorageService.removeItem('user_credentials');
  
  // Or clear all (requires authentication)
  await secureStorageService.clearAll();
}
```

## Testing

### Unit Tests

```typescript
import { secureStorageService } from '@/services/__tests__/secureStorageService.test';

describe('Secure Storage', () => {
  it('should encrypt data before storage', async () => {
    await secureStorageService.setItem('test_key', 'test_value');
    
    // Verify encryption occurred
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
      'test_key',
      expect.stringContaining('"data":'), // Encrypted data
      expect.any(Object)
    );
  });
});
```

### Security Testing

1. **Penetration Testing**: Verify no plaintext data in device storage
2. **Jailbreak Detection**: Test on rooted/jailbroken devices
3. **Backup Analysis**: Ensure backups don't contain sensitive data
4. **Memory Analysis**: Verify keys are not exposed in memory dumps

## Troubleshooting

### Common Issues

1. **"SecureStore is not available"**
   - Ensure running on physical device (not web)
   - Check Expo SDK version compatibility

2. **"Authentication failed"**
   - User cancelled biometric prompt
   - Device has no enrolled biometrics
   - Fallback to device passcode may be disabled

3. **"Failed to store secure data"**
   - Device storage may be full
   - Keychain/keystore corruption (rare)
   - App doesn't have required permissions

### Debug Mode

```typescript
// Enable debug logging (development only)
if (__DEV__) {
  secureStorageService.enableDebugLogging();
}
```

## Compliance

This implementation meets or exceeds:

- **OWASP MASVS** - All storage requirements
- **GDPR** - Encryption of personal data
- **HIPAA** - Healthcare data protection
- **PCI DSS** - Payment card data security
- **SOC 2** - Security controls

## Security Contacts

- Security Team: security@roadtripapp.com
- Report Vulnerabilities: security-reports@roadtripapp.com
- Emergency: Call security hotline

## Updates and Maintenance

- Security patches: Apply immediately
- Encryption upgrades: Follow migration guide
- Key rotation: Annual or as required
- Security audits: Quarterly

---

**Remember**: Security is everyone's responsibility. When in doubt, ask the security team!