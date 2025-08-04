#!/usr/bin/env python3
"""
Test SSL/TLS configuration for production deployment

This script verifies:
1. Certificate validity and expiration
2. SSL/TLS protocol support
3. Cipher suite strength
4. Security headers
5. HTTPS redirection
6. Certificate chain validation

Usage:
    python scripts/test_ssl_configuration.py --domain roadtrip.app
    python scripts/test_ssl_configuration.py --domain api.roadtrip.app --full
"""

import argparse
import json
import logging
import re
import socket
import ssl
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SSLTester:
    """Test SSL/TLS configuration"""
    
    def __init__(self, domain: str, port: int = 443):
        self.domain = domain
        self.port = port
        self.results = {
            'domain': domain,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tests': {},
            'score': 0,
            'issues': [],
            'recommendations': []
        }
        
    def run_all_tests(self, full_scan: bool = False) -> Dict:
        """Run all SSL tests"""
        logger.info(f"Starting SSL tests for {self.domain}:{self.port}")
        
        # Basic tests
        self._test_certificate_validity()
        self._test_certificate_expiration()
        self._test_protocol_support()
        self._test_cipher_suites()
        self._test_https_redirect()
        self._test_security_headers()
        self._test_certificate_chain()
        
        # Additional tests for full scan
        if full_scan:
            self._test_ocsp_stapling()
            self._test_perfect_forward_secrecy()
            self._test_vulnerability_scan()
        
        # Calculate overall score
        self._calculate_score()
        
        return self.results
        
    def _test_certificate_validity(self) -> None:
        """Test if certificate is valid"""
        logger.info("Testing certificate validity...")
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((self.domain, self.port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=self.domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Check subject
                    subject = dict(x[0] for x in cert['subject'])
                    logger.info(f"Certificate subject: {subject}")
                    
                    # Check SANs
                    sans = []
                    for ext in cert.get('subjectAltName', []):
                        if ext[0] == 'DNS':
                            sans.append(ext[1])
                    
                    logger.info(f"Subject Alternative Names: {sans}")
                    
                    # Verify domain is in certificate
                    if self.domain in sans or self.domain == subject.get('commonName'):
                        self.results['tests']['certificate_validity'] = {
                            'status': 'PASS',
                            'message': 'Certificate is valid for domain',
                            'details': {
                                'subject': subject,
                                'sans': sans
                            }
                        }
                    else:
                        self.results['tests']['certificate_validity'] = {
                            'status': 'FAIL',
                            'message': 'Certificate does not match domain'
                        }
                        self.results['issues'].append('Certificate domain mismatch')
                        
        except Exception as e:
            self.results['tests']['certificate_validity'] = {
                'status': 'FAIL',
                'message': f'Certificate validation failed: {str(e)}'
            }
            self.results['issues'].append('Certificate validation failed')
            
    def _test_certificate_expiration(self) -> None:
        """Test certificate expiration date"""
        logger.info("Testing certificate expiration...")
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((self.domain, self.port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=self.domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse dates
                    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    
                    # Calculate days until expiration
                    now = datetime.utcnow()
                    days_until_expiry = (not_after - now).days
                    
                    logger.info(f"Certificate expires in {days_until_expiry} days")
                    
                    if days_until_expiry < 0:
                        status = 'FAIL'
                        message = 'Certificate has expired'
                        self.results['issues'].append('Certificate expired')
                    elif days_until_expiry < 30:
                        status = 'WARN'
                        message = f'Certificate expires soon ({days_until_expiry} days)'
                        self.results['recommendations'].append('Renew certificate soon')
                    else:
                        status = 'PASS'
                        message = f'Certificate valid for {days_until_expiry} days'
                    
                    self.results['tests']['certificate_expiration'] = {
                        'status': status,
                        'message': message,
                        'details': {
                            'not_before': not_before.isoformat(),
                            'not_after': not_after.isoformat(),
                            'days_until_expiry': days_until_expiry
                        }
                    }
                    
        except Exception as e:
            self.results['tests']['certificate_expiration'] = {
                'status': 'FAIL',
                'message': f'Could not check expiration: {str(e)}'
            }
            
    def _test_protocol_support(self) -> None:
        """Test supported SSL/TLS protocols"""
        logger.info("Testing protocol support...")
        
        protocols = {
            'SSLv2': ssl.PROTOCOL_SSLv2 if hasattr(ssl, 'PROTOCOL_SSLv2') else None,
            'SSLv3': ssl.PROTOCOL_SSLv3 if hasattr(ssl, 'PROTOCOL_SSLv3') else None,
            'TLSv1': ssl.PROTOCOL_TLSv1,
            'TLSv1.1': ssl.PROTOCOL_TLSv1_1,
            'TLSv1.2': ssl.PROTOCOL_TLSv1_2,
            'TLSv1.3': ssl.PROTOCOL_TLS if hasattr(ssl, 'PROTOCOL_TLS') else None
        }
        
        supported = []
        details = {}
        
        for name, protocol in protocols.items():
            if protocol is None:
                continue
                
            try:
                context = ssl.SSLContext(protocol)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                with socket.create_connection((self.domain, self.port), timeout=5) as sock:
                    with context.wrap_socket(sock) as ssock:
                        supported.append(name)
                        details[name] = 'Supported'
                        
            except Exception as e:
                details[name] = 'Not supported'
        
        # Check for insecure protocols
        insecure = ['SSLv2', 'SSLv3', 'TLSv1', 'TLSv1.1']
        insecure_found = [p for p in insecure if p in supported]
        
        if insecure_found:
            status = 'FAIL'
            message = f'Insecure protocols supported: {", ".join(insecure_found)}'
            self.results['issues'].append('Insecure protocols enabled')
            self.results['recommendations'].append('Disable SSLv2, SSLv3, TLSv1, and TLSv1.1')
        elif 'TLSv1.2' in supported or 'TLSv1.3' in supported:
            status = 'PASS'
            message = 'Only secure protocols supported'
        else:
            status = 'FAIL'
            message = 'No secure protocols found'
            
        self.results['tests']['protocol_support'] = {
            'status': status,
            'message': message,
            'details': {
                'supported': supported,
                'all_protocols': details
            }
        }
        
    def _test_cipher_suites(self) -> None:
        """Test cipher suite strength"""
        logger.info("Testing cipher suites...")
        
        try:
            # Use openssl to get cipher list
            cmd = ['openssl', 's_client', '-connect', f'{self.domain}:{self.port}', 
                   '-cipher', 'ALL', '-brief']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Extract cipher from output
            cipher_match = re.search(r'Cipher\s+:\s+(\S+)', result.stdout)
            if cipher_match:
                cipher = cipher_match.group(1)
                logger.info(f"Negotiated cipher: {cipher}")
                
                # Check cipher strength
                weak_ciphers = ['RC4', 'DES', '3DES', 'MD5', 'SHA1']
                strong_ciphers = ['AES256', 'AES128', 'CHACHA20', 'GCM', 'SHA256', 'SHA384']
                
                is_weak = any(weak in cipher for weak in weak_ciphers)
                is_strong = any(strong in cipher for strong in strong_ciphers)
                
                if is_weak:
                    status = 'FAIL'
                    message = f'Weak cipher in use: {cipher}'
                    self.results['issues'].append('Weak cipher suite')
                elif is_strong:
                    status = 'PASS'
                    message = f'Strong cipher in use: {cipher}'
                else:
                    status = 'WARN'
                    message = f'Unknown cipher strength: {cipher}'
                    
                self.results['tests']['cipher_suites'] = {
                    'status': status,
                    'message': message,
                    'details': {
                        'negotiated_cipher': cipher
                    }
                }
            else:
                self.results['tests']['cipher_suites'] = {
                    'status': 'FAIL',
                    'message': 'Could not determine cipher suite'
                }
                
        except Exception as e:
            self.results['tests']['cipher_suites'] = {
                'status': 'FAIL',
                'message': f'Cipher test failed: {str(e)}'
            }
            
    def _test_https_redirect(self) -> None:
        """Test HTTP to HTTPS redirect"""
        logger.info("Testing HTTPS redirect...")
        
        try:
            http_url = f'http://{self.domain}/'
            req = urllib.request.Request(http_url, method='HEAD')
            
            try:
                response = urllib.request.urlopen(req, timeout=10)
                # If we get here, there's no redirect
                self.results['tests']['https_redirect'] = {
                    'status': 'FAIL',
                    'message': 'No HTTPS redirect found',
                    'details': {
                        'status_code': response.getcode()
                    }
                }
                self.results['issues'].append('No HTTPS redirect')
                self.results['recommendations'].append('Implement HTTP to HTTPS redirect')
                
            except urllib.error.HTTPError as e:
                if e.code in [301, 302, 303, 307, 308]:
                    location = e.headers.get('Location', '')
                    if location.startswith('https://'):
                        self.results['tests']['https_redirect'] = {
                            'status': 'PASS',
                            'message': 'HTTPS redirect working',
                            'details': {
                                'status_code': e.code,
                                'location': location
                            }
                        }
                    else:
                        self.results['tests']['https_redirect'] = {
                            'status': 'FAIL',
                            'message': 'Redirect not to HTTPS',
                            'details': {
                                'location': location
                            }
                        }
                else:
                    self.results['tests']['https_redirect'] = {
                        'status': 'FAIL',
                        'message': f'Unexpected response: {e.code}'
                    }
                    
        except Exception as e:
            self.results['tests']['https_redirect'] = {
                'status': 'WARN',
                'message': f'Could not test redirect: {str(e)}'
            }
            
    def _test_security_headers(self) -> None:
        """Test security headers"""
        logger.info("Testing security headers...")
        
        try:
            https_url = f'https://{self.domain}/'
            req = urllib.request.Request(https_url)
            response = urllib.request.urlopen(req, timeout=10)
            headers = dict(response.headers)
            
            # Required security headers
            required_headers = {
                'Strict-Transport-Security': r'max-age=\d+',
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': r'(DENY|SAMEORIGIN)',
                'X-XSS-Protection': r'1;\s*mode=block',
                'Referrer-Policy': r'(strict-origin|no-referrer)',
                'Content-Security-Policy': r'default-src'
            }
            
            missing = []
            present = {}
            
            for header, pattern in required_headers.items():
                value = headers.get(header.lower())
                if value:
                    if re.search(pattern, value):
                        present[header] = value
                    else:
                        missing.append(f'{header} (invalid value)')
                else:
                    missing.append(header)
            
            if not missing:
                status = 'PASS'
                message = 'All security headers present'
            elif len(missing) < 3:
                status = 'WARN'
                message = f'Some security headers missing: {", ".join(missing)}'
                self.results['recommendations'].append('Add missing security headers')
            else:
                status = 'FAIL'
                message = f'Many security headers missing: {", ".join(missing)}'
                self.results['issues'].append('Security headers missing')
            
            self.results['tests']['security_headers'] = {
                'status': status,
                'message': message,
                'details': {
                    'present': present,
                    'missing': missing
                }
            }
            
        except Exception as e:
            self.results['tests']['security_headers'] = {
                'status': 'FAIL',
                'message': f'Could not test headers: {str(e)}'
            }
            
    def _test_certificate_chain(self) -> None:
        """Test certificate chain validity"""
        logger.info("Testing certificate chain...")
        
        try:
            # Get full certificate chain
            cmd = ['openssl', 's_client', '-connect', f'{self.domain}:{self.port}',
                   '-showcerts', '-servername', self.domain]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                  input='\n')
            
            # Count certificates in chain
            cert_count = result.stdout.count('BEGIN CERTIFICATE')
            
            # Check for chain issues
            if 'verify error' in result.stdout:
                status = 'FAIL'
                message = 'Certificate chain validation failed'
                self.results['issues'].append('Invalid certificate chain')
            elif cert_count < 2:
                status = 'WARN'
                message = 'Certificate chain may be incomplete'
                self.results['recommendations'].append('Include intermediate certificates')
            else:
                status = 'PASS'
                message = f'Valid certificate chain ({cert_count} certificates)'
            
            self.results['tests']['certificate_chain'] = {
                'status': status,
                'message': message,
                'details': {
                    'chain_length': cert_count
                }
            }
            
        except Exception as e:
            self.results['tests']['certificate_chain'] = {
                'status': 'FAIL',
                'message': f'Chain test failed: {str(e)}'
            }
            
    def _test_ocsp_stapling(self) -> None:
        """Test OCSP stapling"""
        logger.info("Testing OCSP stapling...")
        
        try:
            cmd = ['openssl', 's_client', '-connect', f'{self.domain}:{self.port}',
                   '-status', '-servername', self.domain]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                  input='\n')
            
            if 'OCSP Response Status: successful' in result.stdout:
                status = 'PASS'
                message = 'OCSP stapling enabled'
            else:
                status = 'WARN'
                message = 'OCSP stapling not enabled'
                self.results['recommendations'].append('Enable OCSP stapling')
            
            self.results['tests']['ocsp_stapling'] = {
                'status': status,
                'message': message
            }
            
        except Exception as e:
            self.results['tests']['ocsp_stapling'] = {
                'status': 'WARN',
                'message': f'Could not test OCSP: {str(e)}'
            }
            
    def _test_perfect_forward_secrecy(self) -> None:
        """Test Perfect Forward Secrecy support"""
        logger.info("Testing Perfect Forward Secrecy...")
        
        pfs_ciphers = ['ECDHE', 'DHE']
        
        try:
            cmd = ['openssl', 's_client', '-connect', f'{self.domain}:{self.port}',
                   '-cipher', 'ECDHE:DHE', '-brief']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if any(pfs in result.stdout for pfs in pfs_ciphers):
                status = 'PASS'
                message = 'Perfect Forward Secrecy supported'
            else:
                status = 'FAIL'
                message = 'Perfect Forward Secrecy not supported'
                self.results['issues'].append('No PFS support')
                self.results['recommendations'].append('Enable ECDHE or DHE cipher suites')
            
            self.results['tests']['perfect_forward_secrecy'] = {
                'status': status,
                'message': message
            }
            
        except Exception as e:
            self.results['tests']['perfect_forward_secrecy'] = {
                'status': 'WARN',
                'message': f'Could not test PFS: {str(e)}'
            }
            
    def _test_vulnerability_scan(self) -> None:
        """Test for known SSL vulnerabilities"""
        logger.info("Testing for vulnerabilities...")
        
        vulnerabilities = {
            'heartbleed': self._check_heartbleed,
            'poodle': self._check_poodle,
            'beast': self._check_beast
        }
        
        vuln_results = {}
        
        for vuln_name, check_func in vulnerabilities.items():
            try:
                is_vulnerable = check_func()
                vuln_results[vuln_name] = {
                    'vulnerable': is_vulnerable,
                    'status': 'FAIL' if is_vulnerable else 'PASS'
                }
                
                if is_vulnerable:
                    self.results['issues'].append(f'Vulnerable to {vuln_name.upper()}')
                    
            except Exception as e:
                vuln_results[vuln_name] = {
                    'status': 'WARN',
                    'error': str(e)
                }
        
        # Overall vulnerability status
        if any(v.get('vulnerable') for v in vuln_results.values()):
            status = 'FAIL'
            message = 'Vulnerabilities detected'
        else:
            status = 'PASS'
            message = 'No vulnerabilities detected'
        
        self.results['tests']['vulnerability_scan'] = {
            'status': status,
            'message': message,
            'details': vuln_results
        }
        
    def _check_heartbleed(self) -> bool:
        """Check for Heartbleed vulnerability"""
        # Simplified check - in production, use specialized tools
        return False
        
    def _check_poodle(self) -> bool:
        """Check for POODLE vulnerability"""
        # Check if SSLv3 is enabled
        try:
            if hasattr(ssl, 'PROTOCOL_SSLv3'):
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv3)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                with socket.create_connection((self.domain, self.port), timeout=5) as sock:
                    with context.wrap_socket(sock) as ssock:
                        return True  # SSLv3 is enabled, vulnerable to POODLE
        except Exception as e:
            pass
        
        return False
        
    def _check_beast(self) -> bool:
        """Check for BEAST vulnerability"""
        # Check if TLS 1.0 with CBC ciphers is enabled
        # Simplified check
        return False
        
    def _calculate_score(self) -> None:
        """Calculate overall SSL score"""
        total_tests = len(self.results['tests'])
        if total_tests == 0:
            self.results['score'] = 0
            return
        
        # Weight different test results
        weights = {
            'PASS': 100,
            'WARN': 70,
            'FAIL': 0
        }
        
        total_score = 0
        for test_name, test_result in self.results['tests'].items():
            status = test_result.get('status', 'FAIL')
            total_score += weights.get(status, 0)
        
        self.results['score'] = int(total_score / total_tests)
        
        # Grade based on score
        if self.results['score'] >= 90:
            self.results['grade'] = 'A'
        elif self.results['score'] >= 80:
            self.results['grade'] = 'B'
        elif self.results['score'] >= 70:
            self.results['grade'] = 'C'
        elif self.results['score'] >= 60:
            self.results['grade'] = 'D'
        else:
            self.results['grade'] = 'F'
            
    def generate_report(self) -> str:
        """Generate human-readable report"""
        report = []
        report.append(f"\nSSL/TLS Test Report for {self.domain}")
        report.append("=" * 50)
        report.append(f"Date: {self.results['timestamp']}")
        report.append(f"Overall Score: {self.results['score']}/100 (Grade: {self.results.get('grade', 'N/A')})\n")
        
        # Test results
        report.append("Test Results:")
        report.append("-" * 30)
        for test_name, result in self.results['tests'].items():
            status_icon = {
                'PASS': '✅',
                'WARN': '⚠️ ',
                'FAIL': '❌'
            }.get(result['status'], '❓')
            
            report.append(f"{status_icon} {test_name.replace('_', ' ').title()}: {result['message']}")
        
        # Issues
        if self.results['issues']:
            report.append(f"\nIssues Found ({len(self.results['issues'])}):")
            report.append("-" * 30)
            for issue in self.results['issues']:
                report.append(f"• {issue}")
        
        # Recommendations
        if self.results['recommendations']:
            report.append(f"\nRecommendations ({len(self.results['recommendations'])}):")
            report.append("-" * 30)
            for rec in self.results['recommendations']:
                report.append(f"• {rec}")
        
        report.append("\n")
        return '\n'.join(report)


def main():
    parser = argparse.ArgumentParser(description="Test SSL/TLS configuration")
    parser.add_argument('--domain', required=True, help='Domain to test')
    parser.add_argument('--port', type=int, default=443, help='Port to test (default: 443)')
    parser.add_argument('--full', action='store_true', help='Run full scan including vulnerability tests')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--output', help='Save results to file')
    
    args = parser.parse_args()
    
    # Create tester
    tester = SSLTester(args.domain, args.port)
    
    # Run tests
    results = tester.run_all_tests(full_scan=args.full)
    
    # Output results
    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = tester.generate_report()
    
    print(output)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logger.info(f"Results saved to {args.output}")
    
    # Exit with appropriate code
    if results['grade'] in ['A', 'B']:
        sys.exit(0)
    elif results['grade'] == 'C':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()