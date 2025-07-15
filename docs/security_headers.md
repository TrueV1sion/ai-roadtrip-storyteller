# Security Headers Implementation

This document describes the security headers implemented in the AI Road Trip Storyteller application to protect against various web security threats.

## Overview

Security headers are HTTP response headers that tell browsers how to behave when handling your application's content. They help to protect against common web vulnerabilities such as Cross-Site Scripting (XSS), clickjacking, and other injection attacks.

## Implemented Security Headers

### Content-Security-Policy (CSP)

The Content Security Policy header helps prevent Cross-Site Scripting (XSS) and other code injection attacks by controlling which resources the browser is allowed to load.

Our CSP implementation includes the following directives:

- `default-src 'self'`: Only allow resources from the same origin by default
- `img-src`: Controls where images can be loaded from
- `style-src`: Controls where styles can be loaded from
- `script-src`: Controls where scripts can be loaded from
- `font-src`: Controls where fonts can be loaded from
- `connect-src`: Controls which URLs the application can connect to (e.g., for fetch, WebSocket)
- `media-src`: Controls where audio and video resources can be loaded from
- `frame-src 'none'`: Prevents the page from being framed
- `object-src 'none'`: Prevents object, embed, and applet elements
- `base-uri 'self'`: Restricts the URLs that can appear in the `<base>` element
- `form-action 'self'`: Restricts where forms can be submitted to
- `frame-ancestors 'none'`: Prevents the page from being framed (similar to X-Frame-Options)
- `upgrade-insecure-requests`: Instructs browsers to upgrade HTTP requests to HTTPS

### HTTP Strict Transport Security (HSTS)

The Strict-Transport-Security header tells browsers to only access the application over HTTPS, even if the user specifies HTTP in the URL.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

This header is set with a max-age of one year (31536000 seconds) and includes all subdomains.

### X-Frame-Options

The X-Frame-Options header prevents clickjacking attacks by ensuring your application cannot be embedded in frames on other sites.

```
X-Frame-Options: DENY
```

We use the `DENY` value to prevent framing completely.

### X-Content-Type-Options

The X-Content-Type-Options header prevents browsers from MIME-sniffing a response away from the declared content type, reducing the risk of drive-by downloads.

```
X-Content-Type-Options: nosniff
```

### Referrer-Policy

The Referrer-Policy header controls how much referrer information should be included with requests.

```
Referrer-Policy: strict-origin-when-cross-origin
```

This value sends the origin, path, and query string when performing a same-origin request, but only sends the origin when performing a cross-origin request.

### X-XSS-Protection

The X-XSS-Protection header enables the browser's built-in XSS filter.

```
X-XSS-Protection: 1; mode=block
```

This value enables the filter and tells the browser to block the page rather than sanitize it when an XSS attack is detected.

### Permissions-Policy

The Permissions-Policy header (formerly Feature-Policy) controls which browser features and APIs can be used in the application.

```
Permissions-Policy: geolocation=(self), microphone=(), camera=(), payment=()
```

This policy:
- Allows geolocation only for the same origin
- Disables microphone access
- Disables camera access
- Disables payment API

## Configuration

Security headers can be configured through the application settings. The following settings are available:

- `CSP_ENABLED`: Enable or disable Content Security Policy
- `CSP_IMG_SRC`, `CSP_STYLE_SRC`, etc.: Lists of additional domains allowed for each CSP directive
- `SECURITY_HSTS_ENABLED`: Enable or disable HTTP Strict Transport Security
- `SECURITY_XFO_ENABLED`: Enable or disable X-Frame-Options
- `SECURITY_CONTENT_TYPE_OPTIONS_ENABLED`: Enable or disable X-Content-Type-Options
- `SECURITY_REFERRER_POLICY_ENABLED`: Enable or disable Referrer-Policy
- `SECURITY_XSS_PROTECTION_ENABLED`: Enable or disable X-XSS-Protection

## Implementation Details

The security headers are implemented via a middleware (`SecurityHeadersMiddleware`) in the FastAPI application. This middleware:

1. Intercepts all responses from the application
2. Adds the configured security headers to the response
3. Builds the CSP header dynamically based on configuration

## Testing Security Headers

You can verify the security headers implementation using:

1. The built-in test suite: `pytest tests/test_security_headers.py`
2. Online tools like [Security Headers](https://securityheaders.com/)
3. Browser developer tools (Network tab)

## Best Practices for Developers

When developing new features:

1. **Adding new resources**: If you need to load resources from new domains, update the CSP configuration in settings rather than using inline styles or scripts.

2. **Avoiding inline code**: Avoid using inline JavaScript or CSS where possible. If inline code is necessary, consider using nonces or hashes (not currently implemented).

3. **Third-party services**: When integrating with third-party services, ensure their domains are added to the appropriate CSP directives.

4. **Testing**: Always test new features with the security headers enabled to ensure compatibility.

## Future Improvements

1. Implement CSP nonces or hashes for inline scripts and styles
2. Add a CSP reporting endpoint to collect violations
3. Fine-tune the Permissions-Policy header based on feature usage
4. Consider implementing Subresource Integrity (SRI) for external scripts and styles