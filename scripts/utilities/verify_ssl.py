#!/usr/bin/env python3
"""
SSL/TLS verification script to check certificate configuration and security.
"""

import ssl
import socket
import subprocess
import sys
import json
from datetime import datetime
from urllib.parse import urlparse
import requests
import OpenSSL.crypto

def check_ssl_certificate(hostname, port=443):
    """Check SSL certificate details and validity."""
    print(f"\n=== Checking SSL Certificate for {hostname}:{port} ===\n")
    
    try:
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect and get certificate
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Get certificate info
                cert = ssock.getpeercert()
                der_cert = ssock.getpeercert_binary()
                
                # Parse certificate
                x509 = OpenSSL.crypto.load_certificate(
                    OpenSSL.crypto.FILETYPE_ASN1, der_cert
                )
                
                # Basic info
                print(f"✓ Successfully connected to {hostname}")
                print(f"  Protocol: {ssock.version()}")
                print(f"  Cipher: {ssock.cipher()}")
                
                # Certificate details
                print("\nCertificate Details:")
                print(f"  Subject: {dict(x509.get_subject().get_components())}")
                print(f"  Issuer: {dict(x509.get_issuer().get_components())}")
                
                # Validity dates
                not_before = datetime.strptime(
                    x509.get_notBefore().decode('ascii'), '%Y%m%d%H%M%SZ'
                )
                not_after = datetime.strptime(
                    x509.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ'
                )
                
                days_remaining = (not_after - datetime.utcnow()).days
                
                print(f"\nValidity Period:")
                print(f"  Not Before: {not_before}")
                print(f"  Not After: {not_after}")
                print(f"  Days Remaining: {days_remaining}")
                
                if days_remaining < 30:
                    print(f"  ⚠️  WARNING: Certificate expires in {days_remaining} days!")
                elif days_remaining < 7:
                    print(f"  🚨 CRITICAL: Certificate expires in {days_remaining} days!")
                
                # SANs
                san_list = []
                for i in range(x509.get_extension_count()):
                    ext = x509.get_extension(i)
                    if ext.get_short_name() == b'subjectAltName':
                        san_list = str(ext).split(', ')
                        break
                
                if san_list:
                    print(f"\nSubject Alternative Names:")
                    for san in san_list:
                        print(f"  - {san}")
                
                # Certificate chain
                print(f"\nCertificate Chain Length: {len(cert.get('caIssuers', []))}")
                
                return {
                    "status": "valid",
                    "protocol": ssock.version(),
                    "cipher": ssock.cipher()[0],
                    "days_remaining": days_remaining,
                    "issuer": dict(x509.get_issuer().get_components()),
                    "san_list": san_list
                }
                
    except Exception as e:
        print(f"✗ SSL check failed: {e}")
        return {"status": "error", "error": str(e)}


def check_security_headers(url):
    """Check security headers on HTTPS endpoint."""
    print(f"\n=== Checking Security Headers for {url} ===\n")
    
    try:
        response = requests.get(url, timeout=10, allow_redirects=False)
        headers = response.headers
        
        # Expected security headers
        security_headers = {
            "Strict-Transport-Security": {
                "required": True,
                "check": lambda v: "max-age=" in v and int(v.split("max-age=")[1].split(";")[0]) >= 31536000
            },
            "X-Frame-Options": {
                "required": True,
                "check": lambda v: v.upper() in ["DENY", "SAMEORIGIN"]
            },
            "X-Content-Type-Options": {
                "required": True,
                "check": lambda v: v.lower() == "nosniff"
            },
            "X-XSS-Protection": {
                "required": False,  # Deprecated but still good to have
                "check": lambda v: "1" in v
            },
            "Content-Security-Policy": {
                "required": True,
                "check": lambda v: "default-src" in v
            },
            "Referrer-Policy": {
                "required": True,
                "check": lambda v: v in ["strict-origin-when-cross-origin", "no-referrer", "same-origin"]
            },
            "Permissions-Policy": {
                "required": False,
                "check": lambda v: len(v) > 0
            }
        }
        
        results = {}
        score = 0
        max_score = len([h for h in security_headers.values() if h["required"]])
        
        for header, config in security_headers.items():
            value = headers.get(header)
            if value:
                if config["check"](value):
                    print(f"✓ {header}: {value[:80]}...")
                    results[header] = "pass"
                    if config["required"]:
                        score += 1
                else:
                    print(f"⚠️  {header}: {value} (invalid value)")
                    results[header] = "invalid"
            else:
                if config["required"]:
                    print(f"✗ {header}: Missing (required)")
                    results[header] = "missing"
                else:
                    print(f"- {header}: Missing (optional)")
                    results[header] = "missing"
        
        # Additional checks
        print("\nAdditional Security Checks:")
        
        # Server header
        server = headers.get("Server", "Not disclosed")
        if server != "Not disclosed":
            print(f"⚠️  Server header exposed: {server}")
        else:
            print(f"✓ Server header: Not disclosed")
        
        # Cookies
        cookies = response.cookies
        for cookie in cookies:
            flags = []
            if cookie.secure:
                flags.append("Secure")
            if cookie.has_nonstandard_attr("HttpOnly"):
                flags.append("HttpOnly")
            if cookie.has_nonstandard_attr("SameSite"):
                flags.append(f"SameSite={cookie.get_nonstandard_attr('SameSite')}")
            
            print(f"  Cookie '{cookie.name}': {', '.join(flags) or 'No security flags'}")
        
        print(f"\nSecurity Score: {score}/{max_score}")
        
        return {
            "score": score,
            "max_score": max_score,
            "headers": results,
            "grade": "A" if score == max_score else "B" if score >= max_score * 0.8 else "C"
        }
        
    except Exception as e:
        print(f"✗ Header check failed: {e}")
        return {"status": "error", "error": str(e)}


def check_ssl_configuration(hostname):
    """Check SSL/TLS configuration and cipher suites."""
    print(f"\n=== Checking SSL Configuration for {hostname} ===\n")
    
    try:
        # Test different TLS versions
        tls_versions = {
            "TLSv1": ssl.TLSVersion.TLSv1,
            "TLSv1.1": ssl.TLSVersion.TLSv1_1,
            "TLSv1.2": ssl.TLSVersion.TLSv1_2,
            "TLSv1.3": ssl.TLSVersion.TLSv1_3 if hasattr(ssl.TLSVersion, 'TLSv1_3') else None
        }
        
        supported_versions = []
        
        for version_name, version in tls_versions.items():
            if version is None:
                continue
                
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.minimum_version = version
                context.maximum_version = version
                
                with socket.create_connection((hostname, 443), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        supported_versions.append(version_name)
                        print(f"✓ {version_name}: Supported")
            except:
                print(f"✗ {version_name}: Not supported")
        
        # Check for weak versions
        if "TLSv1" in supported_versions or "TLSv1.1" in supported_versions:
            print("\n⚠️  WARNING: Weak TLS versions supported!")
        
        # Test cipher strength
        print("\nTesting cipher strength...")
        context = ssl.create_default_context()
        
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cipher = ssock.cipher()
                print(f"  Negotiated cipher: {cipher[0]}")
                print(f"  Protocol: {ssock.version()}")
                print(f"  Bits: {cipher[2]}")
                
                # Check for forward secrecy
                if "ECDHE" in cipher[0] or "DHE" in cipher[0]:
                    print("  ✓ Perfect Forward Secrecy: Supported")
                else:
                    print("  ✗ Perfect Forward Secrecy: Not supported")
        
        return {
            "supported_versions": supported_versions,
            "recommended": "TLSv1.2" in supported_versions or "TLSv1.3" in supported_versions,
            "weak_versions": any(v in supported_versions for v in ["TLSv1", "TLSv1.1"])
        }
        
    except Exception as e:
        print(f"✗ Configuration check failed: {e}")
        return {"status": "error", "error": str(e)}


def run_ssl_labs_check(hostname):
    """Get SSL Labs grade (requires API access)."""
    print(f"\n=== SSL Labs Grade ===\n")
    print(f"Check your SSL configuration at:")
    print(f"https://www.ssllabs.com/ssltest/analyze.html?d={hostname}")
    print("\nTarget grade: A+")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python verify_ssl.py <hostname|url>")
        print("Example: python verify_ssl.py api.roadtrip.app")
        print("Example: python verify_ssl.py https://api.roadtrip.app")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    # Parse input
    if arg.startswith("http"):
        parsed = urlparse(arg)
        hostname = parsed.hostname
        url = arg
    else:
        hostname = arg
        url = f"https://{hostname}"
    
    print(f"=== SSL/TLS Verification Report ===")
    print(f"Target: {hostname}")
    print(f"URL: {url}")
    print(f"Date: {datetime.utcnow().isoformat()}")
    
    # Run checks
    cert_result = check_ssl_certificate(hostname)
    config_result = check_ssl_configuration(hostname)
    header_result = check_security_headers(url)
    
    # Summary
    print("\n=== Summary ===\n")
    
    all_good = True
    
    # Certificate status
    if cert_result.get("status") == "valid":
        days = cert_result.get("days_remaining", 0)
        if days > 30:
            print(f"✓ Certificate: Valid ({days} days remaining)")
        else:
            print(f"⚠️  Certificate: Valid but expiring soon ({days} days)")
            all_good = False
    else:
        print(f"✗ Certificate: {cert_result.get('error', 'Invalid')}")
        all_good = False
    
    # Configuration status
    if config_result.get("recommended"):
        print(f"✓ TLS Configuration: Secure")
    else:
        print(f"⚠️  TLS Configuration: Needs improvement")
        all_good = False
    
    # Security headers
    grade = header_result.get("grade", "F")
    if grade in ["A", "B"]:
        print(f"✓ Security Headers: Grade {grade}")
    else:
        print(f"⚠️  Security Headers: Grade {grade}")
        all_good = False
    
    # SSL Labs
    run_ssl_labs_check(hostname)
    
    # Final verdict
    print("\n=== Verdict ===\n")
    if all_good:
        print("✅ SSL/TLS configuration looks good!")
        print("   Continue monitoring certificate expiry and security updates.")
    else:
        print("⚠️  SSL/TLS configuration needs attention!")
        print("   Review the warnings above and update configuration.")
    
    # Save report
    report = {
        "hostname": hostname,
        "timestamp": datetime.utcnow().isoformat(),
        "certificate": cert_result,
        "configuration": config_result,
        "security_headers": header_result,
        "overall_status": "pass" if all_good else "needs_attention"
    }
    
    report_file = f"ssl_report_{hostname}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")


if __name__ == "__main__":
    main()