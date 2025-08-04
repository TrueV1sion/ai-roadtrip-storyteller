# Certificate Rotation Strategy
## Six Sigma DMAIC - CONTROL Phase Documentation

### Overview
This document outlines the certificate pinning and rotation strategy for the AI Road Trip Storyteller mobile application, ensuring continuous security without service disruption.

### Certificate Pinning Implementation

#### Current Implementation
- **Primary Pins**: SHA-256 hashes of server certificate public keys
- **Backup Pins**: Additional pins for certificate rotation
- **Subdomain Coverage**: Wildcard support for *.domain.com
- **Graceful Fallback**: Warning mode before blocking

#### Pin Configuration
```typescript
{
  hostname: 'api.roadtripstoryteller.com',
  pins: [
    'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=', // Current certificate
    'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=', // Intermediate CA
  ],
  backupPins: [
    'CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=', // Next certificate
    'DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD=', // Backup CA
  ],
  includeSubdomains: true,
  expirationDate: '2025-12-31T23:59:59Z'
}
```

### Certificate Rotation Process

#### 1. Pre-Rotation Phase (90 days before expiry)
- [ ] Generate new certificate with different key pair
- [ ] Calculate SHA-256 pin for new certificate
- [ ] Add new pin to backup pins in app configuration
- [ ] Release app update with both old and new pins

#### 2. Transition Phase (30 days before expiry)
- [ ] Deploy new certificate to staging environment
- [ ] Test with updated app version
- [ ] Monitor pin validation failures
- [ ] Ensure backup pins are working

#### 3. Rotation Phase (7 days before expiry)
- [ ] Deploy new certificate to production
- [ ] Both old and new certificates active (if possible)
- [ ] Monitor security events and failures
- [ ] Prepare emergency rollback plan

#### 4. Cleanup Phase (After rotation)
- [ ] Remove old certificate from servers
- [ ] Update app to remove old pins
- [ ] Move backup pins to primary pins
- [ ] Add new backup pins for next rotation

### Emergency Procedures

#### Certificate Compromise
1. **Immediate Actions**:
   - Revoke compromised certificate
   - Deploy new certificate immediately
   - Push emergency app update if needed

2. **Mitigation**:
   - Enable security bypass temporarily
   - Use backup pins if available
   - Monitor for security events

#### Pin Validation Failures
1. **Detection**:
   - Monitor `/api/security/pin-report` endpoint
   - Track failure rates in analytics
   - Set up alerts for > 1% failure rate

2. **Response**:
   - Investigate root cause
   - Check certificate chain changes
   - Verify pin calculations

### Pin Calculation

#### iOS (Swift)
```swift
func calculatePin(for certificate: SecCertificate) -> String? {
    guard let publicKey = SecCertificateCopyKey(certificate),
          let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, nil) as Data? else {
        return nil
    }
    
    let hash = publicKeyData.sha256()
    return hash.base64EncodedString()
}
```

#### Android (Java)
```java
public String calculatePin(X509Certificate cert) throws Exception {
    byte[] publicKey = cert.getPublicKey().getEncoded();
    MessageDigest md = MessageDigest.getInstance("SHA-256");
    byte[] digest = md.digest(publicKey);
    return Base64.encodeToString(digest, Base64.NO_WRAP);
}
```

#### Command Line
```bash
# Extract pin from certificate
openssl x509 -in certificate.crt -pubkey -noout | \
openssl pkey -pubin -outform der | \
openssl dgst -sha256 -binary | \
openssl enc -base64
```

### Monitoring and Reporting

#### Metrics to Track
1. **Pin Validation Success Rate**
   - Target: > 99.9%
   - Alert threshold: < 99%

2. **Certificate Expiry Monitoring**
   - Alert: 90, 30, 7 days before expiry
   - Dashboard: Certificate status overview

3. **Security Events**
   - Pin failures by hostname
   - Geographic distribution of failures
   - Device/OS breakdown

#### Reporting Endpoint
```typescript
POST /api/security/pin-report
{
  "hostname": "api.roadtripstoryteller.com",
  "port": 443,
  "effective-expiration-date": "2025-01-15T12:00:00Z",
  "include-subdomains": true,
  "noted-hostname": "api.roadtripstoryteller.com",
  "served-certificate-chain": ["pin1", "pin2"],
  "validated-certificate-chain": ["pin1", "pin2"],
  "known-pins": ["pinA", "pinB", "pinC", "pinD"]
}
```

### Best Practices

1. **Multiple Pins**
   - Always include at least 2 pins
   - Pin leaf certificate AND intermediate CA
   - Include backup pins for rotation

2. **Testing**
   - Test rotation in staging first
   - Use feature flags for gradual rollout
   - Have rollback plan ready

3. **Communication**
   - Notify team 90 days before rotation
   - Document rotation dates
   - Update runbooks

4. **Automation**
   - Automate pin calculation
   - Automate expiry monitoring
   - Automate update deployment

### Certificate Provider Requirements

1. **Let's Encrypt**
   - 90-day certificates
   - Automated renewal needed
   - Pin ISRG Root X1 as backup

2. **Commercial CA**
   - 1-year certificates typical
   - Pin intermediate CA
   - Ensure CA stability

3. **Google Cloud (GCP)**
   - Managed certificates available
   - Auto-rotation supported
   - Pin Google Trust Services roots

### Implementation Checklist

#### Initial Setup
- [ ] Calculate pins for current certificates
- [ ] Add pins to app configuration
- [ ] Implement pin validation
- [ ] Set up monitoring
- [ ] Document pin values

#### Per Rotation
- [ ] Generate new certificate (90 days before)
- [ ] Calculate new pins
- [ ] Update app with new pins (60 days before)
- [ ] Test in staging (30 days before)
- [ ] Deploy new certificate (7 days before)
- [ ] Remove old pins (30 days after)

#### Continuous
- [ ] Monitor validation success rate
- [ ] Check certificate expiry dates
- [ ] Review security events
- [ ] Update documentation
- [ ] Train team on procedures

### Security Considerations

1. **Pin Storage**
   - Never hardcode production pins in public repos
   - Use configuration management
   - Encrypt pins at rest

2. **Pin Distribution**
   - Use secure channels for pin updates
   - Sign configuration updates
   - Verify pin integrity

3. **Fallback Strategy**
   - Implement graceful degradation
   - Allow temporary bypass for emergencies
   - Log all bypass events

### Tools and Scripts

#### Pin Calculator Script
```bash
#!/bin/bash
# calculate_pins.sh

CERT_FILE=$1

if [ -z "$CERT_FILE" ]; then
    echo "Usage: $0 <certificate.crt>"
    exit 1
fi

echo "Certificate Pins for $CERT_FILE:"
echo "================================"

# Leaf certificate pin
LEAF_PIN=$(openssl x509 -in "$CERT_FILE" -pubkey -noout | \
           openssl pkey -pubin -outform der | \
           openssl dgst -sha256 -binary | \
           openssl enc -base64)
echo "Leaf Certificate: $LEAF_PIN"

# Full chain pins
if [ -f "${CERT_FILE}.chain" ]; then
    i=0
    while read -r cert; do
        if [[ $cert == *"BEGIN CERTIFICATE"* ]]; then
            ((i++))
            PIN=$(echo "$cert" | \
                  openssl x509 -pubkey -noout | \
                  openssl pkey -pubin -outform der | \
                  openssl dgst -sha256 -binary | \
                  openssl enc -base64)
            echo "Chain Certificate $i: $PIN"
        fi
    done < "${CERT_FILE}.chain"
fi
```

#### Monitoring Script
```typescript
// monitor_pins.ts
async function monitorCertificatePins() {
  const endpoints = [
    'https://api.roadtripstoryteller.com',
    'https://staging-api.roadtripstoryteller.com'
  ];
  
  for (const endpoint of endpoints) {
    try {
      const pins = await getCertificatePins(endpoint);
      const config = await loadPinConfiguration();
      
      const validPins = config.pins.filter(pin => 
        pins.includes(pin)
      );
      
      if (validPins.length === 0) {
        alert(`No valid pins found for ${endpoint}`);
      }
      
      // Check expiry
      const certInfo = await getCertificateInfo(endpoint);
      const daysToExpiry = Math.floor(
        (certInfo.validTo - Date.now()) / (1000 * 60 * 60 * 24)
      );
      
      if (daysToExpiry < 90) {
        alert(`Certificate expiring in ${daysToExpiry} days for ${endpoint}`);
      }
    } catch (error) {
      console.error(`Failed to monitor ${endpoint}:`, error);
    }
  }
}
```

### Appendix: Pin Values

**⚠️ SECURITY NOTICE**: Replace these example values with your actual pins!

#### Production Pins (Example)
```json
{
  "api.roadtripstoryteller.com": {
    "leaf": "REPLACE_WITH_ACTUAL_LEAF_CERT_PIN",
    "intermediate": "REPLACE_WITH_ACTUAL_INTERMEDIATE_PIN",
    "backup1": "REPLACE_WITH_BACKUP_CERT_PIN_1",
    "backup2": "REPLACE_WITH_BACKUP_CERT_PIN_2"
  }
}
```

#### Known CA Pins (for reference)
```json
{
  "Let's Encrypt": {
    "ISRG Root X1": "C5+lpZ7tcVwmwQIMcRtPbsQtWLABXhQzejna0wHFr8M=",
    "ISRG Root X2": "diGVwiVYbubAI3RW4hB9xU8e/CH2GnkuvVFZE8zmgzI="
  },
  "Google Trust Services": {
    "GTS Root R1": "Vjs8r4z+80wjNcr1YKepWQboSIRi63WsWXhIMN+eWys=",
    "GTS Root R2": "CLOmM1/OXvSPjw5UOYbAf9GKOxImEp9hhku9W90fHMk="
  }
}
```

---

**Last Updated**: January 2025  
**Next Review**: April 2025  
**Owner**: Security Team