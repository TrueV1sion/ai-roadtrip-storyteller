# TTS Service Security Documentation

This document outlines the security enhancements implemented in the Text-to-Speech (TTS) service of the AI Road Trip Storyteller application.

## Overview

The TTS service generates audio content from text and serves it to users via Google Cloud Storage (GCS). Due to the nature of audio content and the costs associated with TTS processing, securing this service is critical to prevent unauthorized access, API abuse, and content theft.

## Security Enhancements

### 1. Signed URLs with Enhanced Security

The TTS service now uses Google Cloud Storage signed URLs with additional security features:

- **Time-based Expiration**: URLs expire after a designated time period, preventing indefinite access.
  - Premium users: 24 hours for permanent content, 1 hour for temporary content
  - Standard users: 1 hour for permanent content, 30 minutes for temporary content
  - Anonymous users: 30 minutes only, no permanent storage

- **IP Address Restriction**: For non-premium content, signed URLs can be restricted to the client's IP address to prevent URL sharing.

- **User-Based Access Controls**: All generated URLs are associated with user IDs for audit logging and access control.

### 2. Content Segregation

The service separates content based on its type and the user's status:

- **Folder Structure**:
  - `/premium_tts/` - For premium user temporary content
  - `/standard_tts/` - For standard user temporary content
  - `/premium_user_saved_tts/{user_id}/` - For permanent premium content, organized by user
  - `/user_saved_tts/` - For permanent standard content

- **Metadata**: Each audio file includes metadata for improved security tracking:
  - User ID
  - Creation timestamp
  - Content type (permanent/temporary)
  - Premium status
  - Source IP (for temporary content)

### 3. Rate Limiting and Feature Restrictions

The service enforces different limits based on user status:

- **Anonymous Users**:
  - Maximum text length: 500 characters
  - No permanent storage
  - Only standard voices available
  - Short URL expiration (30 minutes)

- **Standard Users**:
  - Maximum text length: 2000 characters
  - Permanent storage available
  - Only standard voices available
  - Standard URL expiration

- **Premium Users**:
  - Unlimited text length
  - Access to premium high-quality voices
  - Permanent storage with user-specific folders
  - Extended URL expiration

### 4. Content Protection

For premium content, several protection mechanisms are in place:

- **Optional Watermarking**: Premium content can include audio watermarks (text appended to the synthesized speech) for tracking purposes.

- **Enhanced Logging**: All premium content access is extensively logged for security monitoring.

- **ACL Controls**: Access control lists restrict who can access permanent premium content.

### 5. Audit Logging

The service implements comprehensive logging:

- **Request Logging**: All TTS requests are logged with user ID, IP address, and request parameters.

- **URL Generation Logging**: Each signed URL generation is logged with full context.

- **Access Logging**: Content access through signed URLs is tracked in GCS logs.

- **Error Logging**: Detailed error logs help identify potential abuse patterns.

## Implementation Details

### Key Classes and Methods

1. **TTSSynthesizer Class**:
   - `synthesize_and_upload()`: Generates and uploads temporary audio content with security parameters
   - `synthesize_and_store_permanently()`: Stores audio for long-term access with appropriate security
   - `get_signed_url_for_gcs_path()`: Creates secure signed URLs with configurable parameters

2. **TTS API Endpoints**:
   - `/api/tts/synthesize`: Main endpoint for speech synthesis with security rules
   - `/api/tts/voices`: Lists available voices with filtering based on user status

### Configuration Options

Security settings can be adjusted in the following places:

- **URL Expiration**: Modify expiration times in `get_signed_url_for_gcs_path()` and API endpoint
- **IP Restrictions**: Enable/disable in `get_signed_url_for_gcs_path()`
- **Voice Availability**: Update the premium voice list in the `/voices` endpoint
- **Text Length Limits**: Adjust in API endpoint validation

## Best Practices for Developers

1. **Always verify user authorization** before generating content
2. **Use the appropriate storage method** based on content permanence needs
3. **Include client IP address** when available for enhanced security
4. **Set watermarks for sensitive content** to trace unauthorized sharing
5. **Monitor logs for unusual patterns** that may indicate abuse

## Security Monitoring

The following patterns should be monitored for potential security issues:

- High volume of requests from a single user/IP
- Multiple failed access attempts to premium content
- Unusual geographic access patterns
- Short-lived user accounts generating large volumes of content
- Attempts to manipulate URL parameters

## Future Enhancements

1. Implement server-side tracking of content access
2. Add audio fingerprinting for premium content
3. Integrate with Cloud DLP for content scanning
4. Implement quota systems based on user tiers
5. Add geographic restrictions for content access