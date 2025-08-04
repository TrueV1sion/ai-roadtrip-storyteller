# Certificate Pinning Setup Guide

## Status: IMPLEMENTED ✅

Certificate pinning has been implemented to prevent man-in-the-middle (MITM) attacks by ensuring the app only connects to servers with known, trusted certificates.

## Implementation Details

### 1. Certificate Pinning Service
- **Location**: `src/services/security/CertificatePinningService.ts`
- **Features**:
  - Dynamic pin management for certificate rotation
  - Support for multiple pins and backup pins
  - Wildcard domain support
  - Pin validation caching for performance
  - Automatic failure reporting
  - Emergency disable mechanism

### 2. Production Certificate Pins
The following certificate pins are configured for the production backend:

```typescript
hostname: 'roadtrip-mvp-792001900150.us-central1.run.app'
pins: [
  'f8NnEFZxQ4ExFOhSN7EiFWtiudZQVD2oY60uauV/n78=', // Google Internet Authority G3
  'Vjs8r4z+80wjNcr1YKepWQboSIRi63WsWXhIMN+eWys=', // GTS Root R1
  'QXnt2YHvdHR3tJYmQIr0Paosp6t/nggsEGD4QJZ3Q0g=', // GTS Root R2
  'sMyD5aX5fEuvxq+V4LqSpFFG3DMGqfyvJMTojfPO7n8=', // GTS Root R3
  'p9VUbDXHBDz7VIIvGzZ9d7w7KYLqnwh7x3Y6lJpJgVQ=', // GTS Root R4
]
```

### 3. Native Module Implementation

#### iOS (Swift)
- **Files**: 
  - `ios/RoadTrip/RNSecurityModule.swift`
  - `ios/RoadTrip/RNSecurityModule.m` (Bridge)
- **Features**:
  - URLSession delegate for certificate validation
  - SHA-256 public key pinning
  - Certificate chain extraction

#### Android (Java)
- **Files**:
  - `android/app/src/main/java/com/roadtrip/RNSecurityModule.java`
  - `android/app/src/main/java/com/roadtrip/RNSecurityPackage.java`
  - `android/app/src/main/res/xml/network_security_config.xml`
- **Features**:
  - OkHttp certificate pinner integration
  - Network security configuration
  - Certificate chain extraction

### 4. Integration Steps

#### App.tsx Integration
The security service is initialized during app startup:

```typescript
import EnhancedMobileSecurityService from '@/services/security/EnhancedMobileSecurityService';

// In initializeApp function:
await EnhancedMobileSecurityService.initialize();
```

#### iOS Setup (Required)
1. Add the Swift files to your Xcode project:
   - Right-click on the RoadTrip folder in Xcode
   - Select "Add Files to RoadTrip..."
   - Add `RNSecurityModule.swift` and `RNSecurityModule.m`
   - Ensure "Copy items if needed" is checked

2. Create/Update Bridging Header:
   - If prompted to create a bridging header, accept
   - Add to `RoadTrip-Bridging-Header.h`:
   ```objc
   #import <React/RCTBridgeModule.h>
   #import <CommonCrypto/CommonCrypto.h>
   ```

3. Add to Info.plist (if not already present):
   ```xml
   <key>NSAppTransportSecurity</key>
   <dict>
     <key>NSAllowsArbitraryLoads</key>
     <false/>
   </dict>
   ```

#### Android Setup (Required)
1. Register the security package in `MainApplication.java`:
   ```java
   import com.roadtrip.RNSecurityPackage;
   
   @Override
   protected List<ReactPackage> getPackages() {
     return Arrays.<ReactPackage>asList(
       new MainReactPackage(),
       new RNSecurityPackage(), // Add this line
       // ... other packages
     );
   }
   ```

2. Update `AndroidManifest.xml` to use network security config:
   ```xml
   <application
     android:networkSecurityConfig="@xml/network_security_config"
     ...>
   ```

3. Ensure minimum SDK version is 24 or higher in `build.gradle`:
   ```gradle
   minSdkVersion 24
   ```

## Testing Certificate Pinning

### 1. Positive Test (Should Succeed)
```typescript
// Make a request to the pinned domain
fetch('https://roadtrip-mvp-792001900150.us-central1.run.app/health')
  .then(response => console.log('Success:', response.status))
  .catch(error => console.error('Failed:', error));
```

### 2. Negative Test (Should Fail)
```typescript
// Try to connect through a proxy (will fail due to certificate mismatch)
// Use a tool like Charles Proxy or mitmproxy
```

### 3. Debug Mode
In development, certificate pinning is disabled to allow debugging tools:
- iOS Simulator: Certificate pinning disabled
- Android Emulator: Trust user certificates in debug builds

## Certificate Rotation

When certificates need to be rotated:

1. Add new pins to backup pins first
2. Deploy app update with both old and new pins
3. Wait for majority adoption
4. Switch primary pins in next update
5. Remove old pins after full migration

## Emergency Procedures

### Disable Certificate Pinning (Emergency Only)
```typescript
import CertificatePinningService from '@/services/security/CertificatePinningService';

// Disable pinning
await CertificatePinningService.disablePinning();

// Re-enable when issue is resolved
await CertificatePinningService.enablePinning();
```

### Update Pins Dynamically
```typescript
await CertificatePinningService.updatePins([
  {
    hostname: 'new-domain.com',
    pins: ['new-pin-hash'],
    includeSubdomains: true,
    expirationDate: '2027-12-31T23:59:59Z'
  }
]);
```

## Monitoring

Certificate pinning failures are automatically reported to:
- Sentry (as security events)
- Backend endpoint: `/api/security/pin-report`
- Local logs (in development)

## Common Issues

### iOS Build Errors
- Ensure CommonCrypto is imported in bridging header
- Check that Swift version matches project settings
- Verify RNSecurityModule files are added to correct target

### Android Build Errors
- Ensure network_security_config.xml is in correct location
- Verify minimum SDK version is 24+
- Check that RNSecurityPackage is registered

### Runtime Errors
- "Certificate pinning failed": Certificate has changed or is being intercepted
- "No pins configured": Pins not properly initialized
- "Network request failed": Could be certificate issue or network problem

## Security Considerations

1. **Pin Expiration**: Pins expire on 2026-12-31, update before then
2. **Backup Pins**: Always include backup pins for rotation
3. **Pin Storage**: Pins are hardcoded, not downloaded (prevents tampering)
4. **Wildcard Domains**: *.run.app is pinned for all Google Cloud Run services
5. **Debug Builds**: Certificate pinning is disabled in development

## Verification Commands

```bash
# Get certificate chain for domain
openssl s_client -connect roadtrip-mvp-792001900150.us-central1.run.app:443 -showcerts

# Extract public key and calculate SHA-256 pin
openssl x509 -in cert.pem -pubkey -noout | \
openssl pkey -pubin -outform der | \
openssl dgst -sha256 -binary | \
openssl enc -base64
```

## References
- [OWASP Certificate Pinning Guide](https://owasp.org/www-community/controls/Certificate_and_Public_Key_Pinning)
- [Android Network Security Configuration](https://developer.android.com/training/articles/security-config)
- [iOS App Transport Security](https://developer.apple.com/documentation/security/preventing_insecure_network_connections)