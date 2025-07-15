#!/usr/bin/env python3
"""
Automated Security Testing Suite for AI Road Trip Storyteller
Covers OWASP Top 10 and common vulnerabilities
"""

import asyncio
import httpx
import json
import time
import random
import string
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityTester:
    """Comprehensive security testing suite"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = httpx.AsyncClient(timeout=30.0)
        self.results = []
        self.auth_token = None
        
    async def run_all_tests(self):
        """Run all security tests"""
        logger.info("Starting comprehensive security audit...")
        
        # Authentication tests
        await self.test_authentication()
        
        # Injection tests
        await self.test_sql_injection()
        await self.test_xss_vulnerabilities()
        await self.test_command_injection()
        
        # Access control tests
        await self.test_broken_access_control()
        await self.test_idor_vulnerabilities()
        
        # Security misconfiguration
        await self.test_security_headers()
        await self.test_error_handling()
        
        # Sensitive data exposure
        await self.test_sensitive_data_exposure()
        
        # API security
        await self.test_api_rate_limiting()
        await self.test_api_authentication()
        
        # Generate report
        self.generate_report()
        
    async def test_authentication(self):
        """Test authentication vulnerabilities"""
        logger.info("Testing authentication vulnerabilities...")
        
        tests = []
        
        # Test 1: Weak password policy
        weak_passwords = ["password", "12345678", "qwerty123", "admin123"]
        for pwd in weak_passwords:
            result = await self._make_request(
                "POST",
                "/api/auth/register",
                json={
                    "email": f"test_{random.randint(1000,9999)}@test.com",
                    "password": pwd
                }
            )
            tests.append({
                "test": "Weak Password Policy",
                "payload": pwd,
                "vulnerable": result.status_code == 201,
                "severity": "Medium",
                "details": f"Weak password '{pwd}' was accepted" if result.status_code == 201 else "Weak password rejected"
            })
        
        # Test 2: Brute force protection
        email = "bruteforce@test.com"
        for i in range(10):
            result = await self._make_request(
                "POST",
                "/api/auth/login",
                json={"email": email, "password": "wrongpass"}
            )
            if i > 5 and result.status_code != 429:
                tests.append({
                    "test": "Brute Force Protection",
                    "payload": f"Attempt {i}",
                    "vulnerable": True,
                    "severity": "High",
                    "details": "No rate limiting on login attempts"
                })
                break
        else:
            tests.append({
                "test": "Brute Force Protection",
                "payload": "10 attempts",
                "vulnerable": False,
                "severity": "High",
                "details": "Rate limiting properly implemented"
            })
        
        # Test 3: JWT manipulation
        if self.auth_token:
            # Try to decode and modify JWT
            parts = self.auth_token.split('.')
            if len(parts) == 3:
                # Modify signature
                modified_token = f"{parts[0]}.{parts[1]}.{'A' * len(parts[2])}"
                result = await self._make_request(
                    "GET",
                    "/api/user/profile",
                    headers={"Authorization": f"Bearer {modified_token}"}
                )
                tests.append({
                    "test": "JWT Signature Verification",
                    "payload": "Modified JWT signature",
                    "vulnerable": result.status_code == 200,
                    "severity": "Critical",
                    "details": "JWT signature not properly verified" if result.status_code == 200 else "JWT signature properly verified"
                })
        
        self.results.extend(tests)
        
    async def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        logger.info("Testing SQL injection vulnerabilities...")
        
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users--",
            "' UNION SELECT * FROM users--",
            "1' AND '1'='1",
            "' OR 1=1--",
            "admin'--",
            "' OR 'a'='a",
            "'; EXEC xp_cmdshell('dir')--"
        ]
        
        endpoints = [
            ("/api/search", "GET", {"q": "PAYLOAD"}),
            ("/api/user/{user_id}", "GET", None),
            ("/api/stories", "GET", {"location": "PAYLOAD"}),
            ("/api/reservations", "GET", {"venue": "PAYLOAD"})
        ]
        
        tests = []
        for endpoint, method, params in endpoints:
            for payload in sql_payloads:
                if "{user_id}" in endpoint:
                    test_endpoint = endpoint.replace("{user_id}", payload)
                    test_params = None
                else:
                    test_endpoint = endpoint
                    test_params = {k: v.replace("PAYLOAD", payload) for k, v in params.items()} if params else None
                
                result = await self._make_request(method, test_endpoint, params=test_params)
                
                # Check for SQL error messages
                vulnerable = False
                if result.text:
                    error_indicators = ["syntax error", "mysql", "postgresql", "sql", "database error"]
                    for indicator in error_indicators:
                        if indicator in result.text.lower():
                            vulnerable = True
                            break
                
                if vulnerable or result.status_code == 500:
                    tests.append({
                        "test": "SQL Injection",
                        "endpoint": endpoint,
                        "payload": payload,
                        "vulnerable": True,
                        "severity": "Critical",
                        "details": f"Potential SQL injection on {endpoint}"
                    })
        
        # If no vulnerabilities found, add success result
        if not tests:
            tests.append({
                "test": "SQL Injection",
                "endpoint": "All tested endpoints",
                "payload": "Various SQL payloads",
                "vulnerable": False,
                "severity": "Critical",
                "details": "No SQL injection vulnerabilities detected"
            })
        
        self.results.extend(tests)
        
    async def test_xss_vulnerabilities(self):
        """Test for XSS vulnerabilities"""
        logger.info("Testing XSS vulnerabilities...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "'><script>alert('XSS')</script>",
            "\"><script>alert('XSS')</script>",
            "<body onload=alert('XSS')>"
        ]
        
        tests = []
        
        # Test reflected XSS
        for payload in xss_payloads:
            result = await self._make_request(
                "GET",
                "/api/search",
                params={"q": payload}
            )
            
            if result.text and payload in result.text:
                tests.append({
                    "test": "Reflected XSS",
                    "endpoint": "/api/search",
                    "payload": payload,
                    "vulnerable": True,
                    "severity": "High",
                    "details": "User input reflected without sanitization"
                })
        
        # Test stored XSS
        if self.auth_token:
            for payload in xss_payloads[:3]:  # Test fewer payloads for stored
                result = await self._make_request(
                    "POST",
                    "/api/stories",
                    json={
                        "title": f"Test Story {payload}",
                        "content": payload,
                        "location": "Test Location"
                    },
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
                if result.status_code == 201:
                    # Try to retrieve and check if payload is unsanitized
                    story_id = result.json().get("id")
                    if story_id:
                        get_result = await self._make_request(
                            "GET",
                            f"/api/stories/{story_id}",
                            headers={"Authorization": f"Bearer {self.auth_token}"}
                        )
                        if get_result.text and payload in get_result.text:
                            tests.append({
                                "test": "Stored XSS",
                                "endpoint": "/api/stories",
                                "payload": payload,
                                "vulnerable": True,
                                "severity": "Critical",
                                "details": "Stored XSS vulnerability detected"
                            })
        
        if not tests:
            tests.append({
                "test": "XSS",
                "endpoint": "All tested endpoints",
                "payload": "Various XSS payloads",
                "vulnerable": False,
                "severity": "High",
                "details": "No XSS vulnerabilities detected"
            })
        
        self.results.extend(tests)
        
    async def test_command_injection(self):
        """Test for command injection vulnerabilities"""
        logger.info("Testing command injection vulnerabilities...")
        
        cmd_payloads = [
            "; ls -la",
            "| whoami",
            "& dir",
            "`id`",
            "$(whoami)",
            "; cat /etc/passwd",
            "| net user",
            "; sleep 10"
        ]
        
        tests = []
        vulnerable_found = False
        
        # Test file upload endpoints
        for payload in cmd_payloads:
            # Test filename injection
            files = {
                'file': (f'test{payload}.jpg', b'fake image data', 'image/jpeg')
            }
            result = await self._make_request(
                "POST",
                "/api/upload",
                files=files
            )
            
            if result.status_code == 500 or (result.text and any(err in result.text.lower() for err in ["command", "exec", "system"])):
                tests.append({
                    "test": "Command Injection",
                    "endpoint": "/api/upload",
                    "payload": payload,
                    "vulnerable": True,
                    "severity": "Critical",
                    "details": "Potential command injection in file processing"
                })
                vulnerable_found = True
        
        # Test other input fields
        endpoints = [
            ("/api/directions", {"origin": "PAYLOAD", "destination": "New York"}),
            ("/api/weather", {"location": "PAYLOAD"})
        ]
        
        for endpoint, params_template in endpoints:
            for payload in cmd_payloads[:3]:  # Test fewer payloads
                params = {k: v.replace("PAYLOAD", payload) if v == "PAYLOAD" else v for k, v in params_template.items()}
                
                start_time = time.time()
                result = await self._make_request("GET", endpoint, params=params)
                elapsed = time.time() - start_time
                
                # Check for timing attacks (sleep payload)
                if "sleep 10" in payload and elapsed > 9:
                    tests.append({
                        "test": "Command Injection (Timing)",
                        "endpoint": endpoint,
                        "payload": payload,
                        "vulnerable": True,
                        "severity": "Critical",
                        "details": "Command injection confirmed via timing attack"
                    })
                    vulnerable_found = True
        
        if not vulnerable_found:
            tests.append({
                "test": "Command Injection",
                "endpoint": "All tested endpoints",
                "payload": "Various command payloads",
                "vulnerable": False,
                "severity": "Critical",
                "details": "No command injection vulnerabilities detected"
            })
        
        self.results.extend(tests)
        
    async def test_broken_access_control(self):
        """Test for broken access control"""
        logger.info("Testing broken access control...")
        
        tests = []
        
        # Create two test users
        user1 = await self._create_test_user("user1")
        user2 = await self._create_test_user("user2")
        
        if user1 and user2:
            # Try to access user2's data with user1's token
            result = await self._make_request(
                "GET",
                f"/api/user/{user2['id']}/profile",
                headers={"Authorization": f"Bearer {user1['token']}"}
            )
            
            tests.append({
                "test": "Horizontal Privilege Escalation",
                "endpoint": "/api/user/{id}/profile",
                "payload": f"Access user {user2['id']} with user {user1['id']} token",
                "vulnerable": result.status_code == 200,
                "severity": "High",
                "details": "User can access other users' data" if result.status_code == 200 else "Proper access control implemented"
            })
            
            # Try to access admin endpoints
            admin_endpoints = [
                "/api/admin/users",
                "/api/admin/analytics",
                "/api/admin/settings"
            ]
            
            for endpoint in admin_endpoints:
                result = await self._make_request(
                    "GET",
                    endpoint,
                    headers={"Authorization": f"Bearer {user1['token']}"}
                )
                
                if result.status_code != 403:
                    tests.append({
                        "test": "Vertical Privilege Escalation",
                        "endpoint": endpoint,
                        "payload": "Regular user accessing admin endpoint",
                        "vulnerable": True,
                        "severity": "Critical",
                        "details": f"Admin endpoint accessible to regular users: {endpoint}"
                    })
        
        # Test direct object reference
        result = await self._make_request("GET", "/api/reservations/1")
        if result.status_code == 200:
            tests.append({
                "test": "Insecure Direct Object Reference",
                "endpoint": "/api/reservations/{id}",
                "payload": "Access without authentication",
                "vulnerable": True,
                "severity": "High",
                "details": "Sensitive data accessible without authentication"
            })
        
        self.results.extend(tests)
        
    async def test_idor_vulnerabilities(self):
        """Test for Insecure Direct Object Reference vulnerabilities"""
        logger.info("Testing IDOR vulnerabilities...")
        
        tests = []
        
        # Test sequential ID enumeration
        base_endpoints = [
            "/api/stories/",
            "/api/reservations/",
            "/api/trips/",
            "/api/users/"
        ]
        
        for base in base_endpoints:
            accessible_ids = []
            for i in range(1, 10):
                result = await self._make_request("GET", f"{base}{i}")
                if result.status_code == 200:
                    accessible_ids.append(i)
            
            if len(accessible_ids) > 3:
                tests.append({
                    "test": "IDOR - Sequential ID Enumeration",
                    "endpoint": base,
                    "payload": f"IDs {accessible_ids}",
                    "vulnerable": True,
                    "severity": "Medium",
                    "details": f"Sequential IDs can be enumerated on {base}"
                })
        
        # Test UUID prediction (if UUIDs are used)
        # This is a simplified test - real UUID prediction is more complex
        
        self.results.extend(tests)
        
    async def test_security_headers(self):
        """Test for security headers"""
        logger.info("Testing security headers...")
        
        result = await self._make_request("GET", "/")
        headers = result.headers
        
        required_headers = {
            "X-Content-Type-Options": ("nosniff", "High"),
            "X-Frame-Options": (["DENY", "SAMEORIGIN"], "Medium"),
            "X-XSS-Protection": ("1; mode=block", "Medium"),
            "Strict-Transport-Security": ("max-age=31536000", "High"),
            "Content-Security-Policy": (None, "High"),  # Just check existence
            "Referrer-Policy": (["no-referrer", "strict-origin-when-cross-origin"], "Low")
        }
        
        tests = []
        for header, (expected, severity) in required_headers.items():
            if header not in headers:
                tests.append({
                    "test": "Security Headers",
                    "endpoint": "/",
                    "payload": header,
                    "vulnerable": True,
                    "severity": severity,
                    "details": f"Missing security header: {header}"
                })
            elif expected and isinstance(expected, str) and headers[header] != expected:
                tests.append({
                    "test": "Security Headers",
                    "endpoint": "/",
                    "payload": header,
                    "vulnerable": True,
                    "severity": severity,
                    "details": f"Incorrect {header}: got '{headers[header]}', expected '{expected}'"
                })
            elif expected and isinstance(expected, list) and headers[header] not in expected:
                tests.append({
                    "test": "Security Headers",
                    "endpoint": "/",
                    "payload": header,
                    "vulnerable": True,
                    "severity": severity,
                    "details": f"Incorrect {header}: got '{headers[header]}', expected one of {expected}"
                })
        
        if not tests:
            tests.append({
                "test": "Security Headers",
                "endpoint": "/",
                "payload": "All headers",
                "vulnerable": False,
                "severity": "High",
                "details": "All security headers properly configured"
            })
        
        self.results.extend(tests)
        
    async def test_error_handling(self):
        """Test error handling and information disclosure"""
        logger.info("Testing error handling...")
        
        tests = []
        
        # Test for stack traces
        error_endpoints = [
            ("/api/thisshoulnotexist", "GET"),
            ("/api/user/notanumber", "GET"),
            ("/api/stories", "POST"),  # Missing required fields
        ]
        
        for endpoint, method in error_endpoints:
            result = await self._make_request(method, endpoint)
            
            if result.text:
                # Check for sensitive information in errors
                sensitive_patterns = [
                    "traceback",
                    "stack trace",
                    "line [0-9]+",
                    "file \"",
                    "sqlalchemy",
                    "psycopg2",
                    "internal server error",
                    "/home/",
                    "/usr/",
                    "c:\\\\",
                    "database",
                    "table"
                ]
                
                for pattern in sensitive_patterns:
                    if pattern in result.text.lower():
                        tests.append({
                            "test": "Information Disclosure",
                            "endpoint": endpoint,
                            "payload": method,
                            "vulnerable": True,
                            "severity": "Medium",
                            "details": f"Sensitive information in error: {pattern}"
                        })
                        break
        
        # Test debug mode
        result = await self._make_request("GET", "/debug")
        if result.status_code == 200:
            tests.append({
                "test": "Debug Mode Enabled",
                "endpoint": "/debug",
                "payload": "GET",
                "vulnerable": True,
                "severity": "High",
                "details": "Debug endpoint accessible in production"
            })
        
        if not tests:
            tests.append({
                "test": "Error Handling",
                "endpoint": "All tested endpoints",
                "payload": "Various error conditions",
                "vulnerable": False,
                "severity": "Medium",
                "details": "Errors properly handled without information disclosure"
            })
        
        self.results.extend(tests)
        
    async def test_sensitive_data_exposure(self):
        """Test for sensitive data exposure"""
        logger.info("Testing sensitive data exposure...")
        
        tests = []
        
        # Test for exposed configuration files
        config_files = [
            "/.env",
            "/config.json",
            "/.git/config",
            "/backup.sql",
            "/phpinfo.php",
            "/web.config",
            "/.htaccess",
            "/robots.txt",
            "/sitemap.xml"
        ]
        
        for file in config_files:
            result = await self._make_request("GET", file)
            if result.status_code == 200 and file != "/robots.txt":  # robots.txt is ok
                tests.append({
                    "test": "Exposed Configuration Files",
                    "endpoint": file,
                    "payload": "GET",
                    "vulnerable": True,
                    "severity": "Critical" if file in ["/.env", "/.git/config"] else "High",
                    "details": f"Sensitive file exposed: {file}"
                })
        
        # Test API responses for sensitive data
        if self.auth_token:
            result = await self._make_request(
                "GET",
                "/api/user/profile",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
            if result.status_code == 200:
                data = result.json()
                sensitive_fields = ["password", "hashed_password", "credit_card", "ssn", "api_key"]
                
                for field in sensitive_fields:
                    if field in str(data):
                        tests.append({
                            "test": "Sensitive Data in API Response",
                            "endpoint": "/api/user/profile",
                            "payload": field,
                            "vulnerable": True,
                            "severity": "High",
                            "details": f"Sensitive field '{field}' exposed in API response"
                        })
        
        if not tests:
            tests.append({
                "test": "Sensitive Data Exposure",
                "endpoint": "All tested endpoints",
                "payload": "Various sensitive paths",
                "vulnerable": False,
                "severity": "High",
                "details": "No sensitive data exposure detected"
            })
        
        self.results.extend(tests)
        
    async def test_api_rate_limiting(self):
        """Test API rate limiting"""
        logger.info("Testing API rate limiting...")
        
        tests = []
        
        # Test rate limiting on various endpoints
        endpoints = [
            "/api/stories",
            "/api/search",
            "/api/directions"
        ]
        
        for endpoint in endpoints:
            # Make rapid requests
            hit_limit = False
            for i in range(100):
                result = await self._make_request("GET", endpoint, params={"q": "test"})
                if result.status_code == 429:
                    tests.append({
                        "test": "API Rate Limiting",
                        "endpoint": endpoint,
                        "payload": f"{i+1} requests",
                        "vulnerable": False,
                        "severity": "Medium",
                        "details": f"Rate limiting active after {i+1} requests"
                    })
                    hit_limit = True
                    break
            
            if not hit_limit:
                tests.append({
                    "test": "API Rate Limiting",
                    "endpoint": endpoint,
                    "payload": "100 requests",
                    "vulnerable": True,
                    "severity": "Medium",
                    "details": f"No rate limiting on {endpoint}"
                })
        
        self.results.extend(tests)
        
    async def test_api_authentication(self):
        """Test API authentication requirements"""
        logger.info("Testing API authentication...")
        
        tests = []
        
        # Endpoints that should require authentication
        protected_endpoints = [
            ("/api/user/profile", "GET"),
            ("/api/stories", "POST"),
            ("/api/reservations", "POST"),
            ("/api/preferences", "PUT"),
            ("/api/trips", "GET")
        ]
        
        for endpoint, method in protected_endpoints:
            # Test without auth
            result = await self._make_request(method, endpoint)
            if result.status_code not in [401, 403]:
                tests.append({
                    "test": "API Authentication",
                    "endpoint": endpoint,
                    "payload": f"{method} without auth",
                    "vulnerable": True,
                    "severity": "High",
                    "details": f"Protected endpoint accessible without authentication: {endpoint}"
                })
            
            # Test with invalid token
            result = await self._make_request(
                method,
                endpoint,
                headers={"Authorization": "Bearer invalid-token"}
            )
            if result.status_code not in [401, 403]:
                tests.append({
                    "test": "API Authentication",
                    "endpoint": endpoint,
                    "payload": f"{method} with invalid token",
                    "vulnerable": True,
                    "severity": "High",
                    "details": f"Protected endpoint accepts invalid tokens: {endpoint}"
                })
        
        if not tests:
            tests.append({
                "test": "API Authentication",
                "endpoint": "All protected endpoints",
                "payload": "Various auth tests",
                "vulnerable": False,
                "severity": "High",
                "details": "All protected endpoints properly secured"
            })
        
        self.results.extend(tests)
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            return await self.session.request(method, url, **kwargs)
        except Exception as e:
            logger.error(f"Request failed: {e}")
            # Return a mock response for error cases
            return httpx.Response(500, text=str(e))
            
    async def _create_test_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Create a test user and return credentials"""
        email = f"{username}_{random.randint(1000,9999)}@test.com"
        password = "TestPass123!"
        
        # Register
        result = await self._make_request(
            "POST",
            "/api/auth/register",
            json={"email": email, "password": password}
        )
        
        if result.status_code == 201:
            # Login
            login_result = await self._make_request(
                "POST",
                "/api/auth/login",
                json={"email": email, "password": password}
            )
            
            if login_result.status_code == 200:
                data = login_result.json()
                return {
                    "id": data.get("user_id"),
                    "email": email,
                    "token": data.get("access_token")
                }
        
        return None
        
    def generate_report(self):
        """Generate security audit report"""
        print("\n" + "="*80)
        print("SECURITY AUDIT REPORT - AI ROAD TRIP STORYTELLER")
        print("="*80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target: {self.base_url}")
        print(f"Total Tests: {len(self.results)}")
        
        # Count vulnerabilities by severity
        severity_counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0
        }
        
        vulnerabilities = []
        for result in self.results:
            if result["vulnerable"]:
                severity_counts[result["severity"]] += 1
                vulnerabilities.append(result)
        
        print(f"\nVulnerabilities Found:")
        print(f"  Critical: {severity_counts['Critical']}")
        print(f"  High: {severity_counts['High']}")
        print(f"  Medium: {severity_counts['Medium']}")
        print(f"  Low: {severity_counts['Low']}")
        
        # Calculate security score
        score = 100
        score -= severity_counts["Critical"] * 20
        score -= severity_counts["High"] * 10
        score -= severity_counts["Medium"] * 5
        score -= severity_counts["Low"] * 2
        score = max(0, score)
        
        print(f"\nSecurity Score: {score}/100")
        
        if vulnerabilities:
            print("\n" + "-"*80)
            print("VULNERABILITY DETAILS")
            print("-"*80)
            
            for vuln in sorted(vulnerabilities, key=lambda x: ["Critical", "High", "Medium", "Low"].index(x["severity"])):
                print(f"\n[{vuln['severity']}] {vuln['test']}")
                print(f"  Endpoint: {vuln.get('endpoint', 'N/A')}")
                print(f"  Payload: {vuln.get('payload', 'N/A')}")
                print(f"  Details: {vuln['details']}")
        
        # Save detailed report
        report_file = f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "date": datetime.now().isoformat(),
                "target": self.base_url,
                "score": score,
                "summary": severity_counts,
                "vulnerabilities": vulnerabilities,
                "all_results": self.results
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        # Recommendations
        print("\n" + "-"*80)
        print("RECOMMENDATIONS")
        print("-"*80)
        
        if severity_counts["Critical"] > 0:
            print("\n🚨 CRITICAL: Address critical vulnerabilities immediately!")
            print("   - Review and fix all SQL injection points")
            print("   - Implement proper access controls")
            print("   - Remove exposed sensitive files")
        
        if severity_counts["High"] > 0:
            print("\n⚠️  HIGH: Fix high-severity issues before production")
            print("   - Implement proper authentication checks")
            print("   - Add input validation and sanitization")
            print("   - Configure security headers")
        
        if score >= 85:
            print("\n✅ Overall security posture is GOOD")
        elif score >= 70:
            print("\n⚠️  Overall security posture is FAIR - improvements needed")
        else:
            print("\n🚨 Overall security posture is POOR - significant work required")
        
        print("\nNext Steps:")
        print("1. Fix all Critical and High vulnerabilities")
        print("2. Implement security headers and CSP")
        print("3. Add rate limiting where missing")
        print("4. Schedule regular security audits")
        print("5. Consider bug bounty program")
        

async def main():
    """Run security tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Testing Suite")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to test")
    parser.add_argument("--api-key", help="API key for authenticated tests")
    
    args = parser.parse_args()
    
    tester = SecurityTester(args.url, args.api_key)
    await tester.run_all_tests()
    

if __name__ == "__main__":
    asyncio.run(main())